from __future__ import annotations

import re
from typing import Any

from app.models.schemas import (
    CoarseSummary,
    DailyState,
    PatientTwinInput,
    ProtocolCandidate,
    ProtocolResult,
    ProtocolScore,
    SafetyFlag,
)
from app.safety.comorbidity_policy import assess_protocol_against_profile
from app.safety.rules_engine import has_disqualifying_flag
from app.services.medgemma import medgemma_client


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


class CriticAgent:
    @staticmethod
    def _clean_recommendation_text(text: str) -> str:
        cleaned = text.strip()
        if not cleaned:
            return ""

        # Remove LM Studio/Gemma reasoning artifact blocks.
        cleaned = re.sub(r"<unused\d+>thought[\s\S]*?<unused\d+>", "", cleaned, flags=re.IGNORECASE)
        # Remove any remaining pseudo-token tags.
        cleaned = re.sub(r"</?unused\d+>", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"<[^>\n]+>", "", cleaned)

        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        # Keep the recommendation concise for UI readability.
        parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", cleaned) if part.strip()]
        if len(parts) > 4:
            cleaned = " ".join(parts[:4]).strip()

        return cleaned

    async def evaluate(
        self,
        patient: PatientTwinInput,
        protocols: list[ProtocolCandidate],
        coarse_by_protocol: dict[str, CoarseSummary],
        trajectories: dict[str, list[DailyState]],
        flags_by_protocol: dict[str, list[SafetyFlag]],
    ) -> tuple[list[ProtocolResult], str]:
        results: list[ProtocolResult] = []

        for protocol in protocols:
            coarse = coarse_by_protocol[protocol.protocol_id]
            trajectory = trajectories[protocol.protocol_id]
            flags = flags_by_protocol.get(protocol.protocol_id, [])
            guideline_assessment = assess_protocol_against_profile(patient, protocol)

            first = trajectory[0]
            last = trajectory[-1]

            efficacy_gain = max(0.0, first.hba1c_est - last.hba1c_est)
            efficacy_score = _clamp((efficacy_gain / 2.6) + guideline_assessment.efficacy_bonus)

            high_flags = sum(1 for flag in flags if flag.severity in {"high", "critical"})
            safety_penalty = min(0.85, high_flags * 0.12 + coarse.safety_risk_index * 0.55)
            safety_score = _clamp(1.0 - safety_penalty - guideline_assessment.safety_penalty)

            mean_adherence = sum(item.adherence_est for item in trajectory) / max(1, len(trajectory))
            adherence_score = _clamp(mean_adherence - guideline_assessment.adherence_penalty)

            robustness_score = _clamp(coarse.robustness_index - coarse.mortality_proxy_rate)

            total_score = (
                0.45 * efficacy_score
                + 0.25 * safety_score
                + 0.15 * adherence_score
                + 0.15 * robustness_score
            )

            disqualified = has_disqualifying_flag(flags)
            if disqualified:
                total_score = 0.0

            score = ProtocolScore(
                protocol_id=protocol.protocol_id,
                efficacy_score=round(efficacy_score, 4),
                safety_score=round(safety_score, 4),
                adherence_score=round(adherence_score, 4),
                robustness_score=round(robustness_score, 4),
                total_score=round(total_score, 4),
                disqualified=disqualified,
            )

            black_box_warning, black_box_code = self._build_black_box_warning(protocol, score, flags)
            explanation = self._build_explanation(protocol, score, flags, guideline_assessment.rationale)
            results.append(
                ProtocolResult(
                    protocol=protocol,
                    coarse_summary=coarse,
                    trajectory=trajectory,
                    flags=flags,
                    score=score,
                    explanation=explanation,
                    guideline_reasons=guideline_assessment.rationale,
                    black_box_warning=black_box_warning,
                    black_box_code=black_box_code,
                )
            )

        results.sort(key=lambda item: item.score.total_score, reverse=True)
        final_recommendation = await self._final_recommendation(results)
        return results, final_recommendation

    @staticmethod
    def _build_explanation(
        protocol: ProtocolCandidate,
        score: ProtocolScore,
        flags: list[SafetyFlag],
        guideline_reasons: list[str] | None = None,
    ) -> str:
        if score.disqualified:
            reason = next((flag.message for flag in flags if flag.disqualifying), "Disqualified by safety rules")
            return f"{protocol.label} was disqualified by the critic due to safety constraints: {reason}."
        explanation = (
            f"{protocol.label} scored {score.total_score:.2f} with efficacy {score.efficacy_score:.2f}, "
            f"safety {score.safety_score:.2f}, adherence {score.adherence_score:.2f}, "
            f"and robustness {score.robustness_score:.2f}."
        )
        if guideline_reasons:
            explanation += f" Comorbidity fit: {guideline_reasons[0]}"
        return explanation

    @staticmethod
    def _build_black_box_warning(
        protocol: ProtocolCandidate,
        score: ProtocolScore,
        flags: list[SafetyFlag],
    ) -> tuple[str | None, str | None]:
        if not score.disqualified:
            return None, None

        disqualifying = next((flag for flag in flags if flag.disqualifying), None)
        if disqualifying is None:
            return (
                "PROTOCOL REJECTED: Contraindication found (Safety disqualification).",
                "SAFETY_DISQUALIFICATION",
            )

        code = disqualifying.code
        pretty_reason = {
            "EGFR_METFORMIN_CONTRAINDICATION": "Metformin + Kidney Failure",
            "LOW_EGFR_SGLT2_RISK": "SGLT2 + Severe Kidney Dysfunction",
            "ALT_TZD_RISK": "Pioglitazone + Liver Stress",
            "HF_TZD_CONTRAINDICATION": "Pioglitazone + Heart Failure",
            "SEVERE_EVENT_BURDEN": "Severe Predicted Toxicity Burden",
        }.get(code, disqualifying.message)

        warning = f"PROTOCOL REJECTED: Contraindication found ({pretty_reason})."
        return warning, code

    async def _final_recommendation(self, ranked_results: list[ProtocolResult]) -> str:
        if not ranked_results:
            return "No protocol recommendation available."

        top = ranked_results[0]
        shortlist = [
            {
                "protocol_id": item.protocol.protocol_id,
                "label": item.protocol.label,
                "total_score": item.score.total_score,
                "disqualified": item.score.disqualified,
            }
            for item in ranked_results[:3]
        ]
        prompt = (
            "You are MedGemma. Explain the top-ranked diabetes protocol in 4 concise sentences. "
            "Mention safety and efficacy tradeoff.\n"
            f"Top candidates: {shortlist}"
        )
        response = await medgemma_client.complete_text(prompt)
        answer = self._clean_recommendation_text(response.text)
        if not answer:
            answer = (
                f"Recommended protocol is {top.protocol.label} because it achieved the highest weighted "
                "benefit-to-risk score in this simulation."
            )
        return answer


critic_agent = CriticAgent()
