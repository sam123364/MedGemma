from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.models.schemas import (
    CoarseSummary,
    DailyState,
    PatientTwinInput,
    PopulationMapArtifact,
    PopulationMapCell,
    ProtocolCandidate,
)
from app.safety.comorbidity_policy import assess_protocol_against_profile
from app.safety.rules_engine import evaluate_safety, has_disqualifying_flag
from app.sim.coarse_engine import run_coarse_trials
from app.services import settings


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _three_point_window(value: float, minimum: float, maximum: float, delta: float) -> tuple[float, float, float]:
    start = value - delta
    end = value + delta
    if start < minimum:
        start = minimum
        end = minimum + (2 * delta)
    if end > maximum:
        end = maximum
        start = maximum - (2 * delta)
    middle = start + delta
    return start, middle, end


def _coarse_to_trajectory(patient: PatientTwinInput, coarse: CoarseSummary, horizon_days: int) -> list[DailyState]:
    hba1c_end = max(5.3, patient.hba1c - coarse.expected_hba1c_delta)
    glucose_end = max(60.0, patient.fasting_glucose - coarse.expected_glucose_delta)

    states: list[DailyState] = []
    for day in range(1, horizon_days + 1):
        fade = day / max(1, horizon_days)
        states.append(
            DailyState(
                day=day,
                hba1c_est=round(patient.hba1c - (patient.hba1c - hba1c_end) * fade, 3),
                fasting_glucose_est=round(patient.fasting_glucose - (patient.fasting_glucose - glucose_end) * fade, 3),
                bmi_est=patient.bmi,
                systolic_bp_est=patient.systolic_bp,
                diastolic_bp_est=patient.diastolic_bp,
                egfr_est=patient.egfr,
                alt_est=patient.alt,
                adherence_est=patient.adherence_probability,
                adverse_events=[],
                severe_event=False,
                alive=True,
            )
        )
    return states


def _score_protocol(
    patient: PatientTwinInput,
    protocol: ProtocolCandidate,
    coarse: CoarseSummary,
    trajectory: list[DailyState],
    force_disqualified: bool = False,
) -> tuple[float, bool]:
    guideline_assessment = assess_protocol_against_profile(patient, protocol)
    flags = evaluate_safety(patient, protocol, trajectory)
    disqualified = force_disqualified or has_disqualifying_flag(flags)

    efficacy_score = _clamp((coarse.expected_hba1c_delta / 2.6) + guideline_assessment.efficacy_bonus)
    high_flags = sum(1 for flag in flags if flag.severity in {"high", "critical"})
    safety_penalty = min(0.85, high_flags * 0.12 + coarse.safety_risk_index * 0.55)
    safety_score = _clamp(1.0 - safety_penalty - guideline_assessment.safety_penalty)
    adherence_score = _clamp(patient.adherence_probability - guideline_assessment.adherence_penalty)
    robustness_score = _clamp(coarse.robustness_index - coarse.mortality_proxy_rate)

    total_score = (
        0.45 * efficacy_score
        + 0.25 * safety_score
        + 0.15 * adherence_score
        + 0.15 * robustness_score
    )
    if disqualified:
        total_score = 0.0
    return round(total_score, 4), disqualified


def generate_population_map(
    run_id: str,
    patient: PatientTwinInput,
    protocols: list[ProtocolCandidate],
    horizon_days: int,
    force_disqualified_protocol_ids: set[str] | None = None,
) -> PopulationMapArtifact:
    if not protocols:
        return PopulationMapArtifact(run_id=run_id, axes={"age": [], "egfr": [], "hba1c": []}, cells=[], generated_at=datetime.now(UTC))

    age_window = _three_point_window(float(patient.age), minimum=18.0, maximum=100.0, delta=8.0)
    egfr_window = _three_point_window(float(patient.egfr), minimum=5.0, maximum=180.0, delta=20.0)
    hba1c_window = _three_point_window(float(patient.hba1c), minimum=4.5, maximum=15.0, delta=1.2)

    age_values = [int(round(value)) for value in age_window]
    egfr_values = [round(value, 1) for value in egfr_window]
    hba1c_values = [round(value, 1) for value in hba1c_window]

    forced_blocked = force_disqualified_protocol_ids or set()

    cells: list[PopulationMapCell] = []
    for age in age_values:
        for egfr in egfr_values:
            for hba1c in hba1c_values:
                twin = patient.model_copy(update={"age": age, "egfr": egfr, "hba1c": hba1c})
                coarse = run_coarse_trials(
                    patient=twin,
                    protocols=protocols,
                    total_trials=settings.POPULATION_MAP_TRIALS,
                    horizon_days=horizon_days,
                )

                ranking: list[dict[str, Any]] = []
                disqualified_count = 0
                for protocol in protocols:
                    summary = coarse[protocol.protocol_id]
                    trajectory = _coarse_to_trajectory(twin, summary, horizon_days)
                    score, disqualified = _score_protocol(
                        twin,
                        protocol,
                        summary,
                        trajectory,
                        force_disqualified=protocol.protocol_id in forced_blocked,
                    )
                    if disqualified:
                        disqualified_count += 1
                    ranking.append(
                        {
                            "protocol_id": protocol.protocol_id,
                            "label": protocol.label,
                            "score": score,
                        }
                    )

                ranking.sort(key=lambda item: item["score"], reverse=True)
                top = ranking[0]
                runner_up = ranking[1] if len(ranking) > 1 else None
                margin = top["score"] - (runner_up["score"] if runner_up else 0.0)

                cell_id = f"age-{age}_egfr-{egfr:.1f}_hba1c-{hba1c:.1f}"
                cells.append(
                    PopulationMapCell(
                        cell_id=cell_id,
                        age=age,
                        egfr=egfr,
                        hba1c=hba1c,
                        top_protocol_id=top["protocol_id"],
                        top_protocol_label=top["label"],
                        top_score=top["score"],
                        runner_up_protocol_id=(runner_up["protocol_id"] if runner_up else None),
                        runner_up_score=(runner_up["score"] if runner_up else None),
                        confidence_margin=round(margin, 4),
                        disqualified_count=disqualified_count,
                    )
                )

    return PopulationMapArtifact(
        run_id=run_id,
        axes={"age": [float(v) for v in age_values], "egfr": egfr_values, "hba1c": hba1c_values},
        cells=cells,
        generated_at=datetime.now(UTC),
    )
