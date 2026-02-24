from __future__ import annotations

import json
import re

from fastapi import APIRouter, HTTPException

from app.db.sqlite import repository
from app.models.schemas import ChatExplainRequest, ChatExplainResponse
from app.services.medgemma import medgemma_client


router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


def _clean_answer(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"<unused\d+>thought[\s\S]*?<unused\d+>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"</?unused\d+>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<[^>\n]+>", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _is_grounded_question(question: str, context_blob: str) -> bool:
    question_tokens = set(re.findall(r"[a-zA-Z0-9\-]{4,}", question.lower()))
    context_tokens = set(re.findall(r"[a-zA-Z0-9\-]{4,}", context_blob.lower()))
    if not question_tokens:
        return True
    overlap = len(question_tokens & context_tokens) / max(1, len(question_tokens))
    return overlap >= 0.12


def _protocol_summary(item: dict) -> dict:
    protocol = item.get("protocol", {})
    score = item.get("score", {})
    flags = item.get("flags", []) or []
    guideline_reasons = item.get("guideline_reasons", []) or []
    trajectory = item.get("trajectory", []) or []
    coarse = item.get("coarse_summary", {}) or {}

    high_or_critical = [f for f in flags if f.get("severity") in {"high", "critical"}]
    disqualifying = [f for f in flags if f.get("disqualifying")]
    severe_days = sum(1 for day in trajectory if day.get("severe_event"))
    adverse_days = sum(1 for day in trajectory if (day.get("adverse_events") or []))

    first = trajectory[0] if trajectory else {}
    last = trajectory[-1] if trajectory else {}
    hba1c_drop = None
    egfr_change = None
    alt_change = None
    if first and last:
        hba1c_drop = round(float(first.get("hba1c_est", 0.0)) - float(last.get("hba1c_est", 0.0)), 3)
        egfr_change = round(float(last.get("egfr_est", 0.0)) - float(first.get("egfr_est", 0.0)), 3)
        alt_change = round(float(last.get("alt_est", 0.0)) - float(first.get("alt_est", 0.0)), 3)

    return {
        "protocol_id": protocol.get("protocol_id"),
        "label": protocol.get("label"),
        "meds": protocol.get("meds", []),
        "rationale": protocol.get("rationale"),
        "disqualified": bool(score.get("disqualified", False)),
        "score_components": {
            "efficacy": score.get("efficacy_score"),
            "safety": score.get("safety_score"),
            "adherence": score.get("adherence_score"),
            "robustness": score.get("robustness_score"),
        },
        "risk_profile": {
            "high_or_critical_flag_count": len(high_or_critical),
            "disqualifying_flags": [{"code": f.get("code"), "message": f.get("message")} for f in disqualifying[:3]],
            "high_or_critical_examples": [{"code": f.get("code"), "message": f.get("message")} for f in high_or_critical[:3]],
            "severe_event_days": severe_days,
            "days_with_any_adverse_event": adverse_days,
            "safety_risk_index": coarse.get("safety_risk_index"),
            "mortality_proxy_rate": coarse.get("mortality_proxy_rate"),
        },
        "trajectory_deltas": {
            "hba1c_drop_est": hba1c_drop,
            "egfr_change_est": egfr_change,
            "alt_change_est": alt_change,
        },
        "guideline_reasons": guideline_reasons[:4],
        "citation_source_ids": protocol.get("citation_source_ids", []),
    }


@router.post("/explain", response_model=ChatExplainResponse)
async def explain_question(payload: ChatExplainRequest) -> ChatExplainResponse:
    artifact = repository.get_run_result(payload.run_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="Run result not found")

    results = artifact.get("results", [])
    if not results:
        raise HTTPException(status_code=400, detail="Run has no completed protocol results")

    top_context = []
    grounded_source_ids: list[str] = []
    for item in results[:3]:
        summary = _protocol_summary(item)
        top_context.append(summary)
        grounded_source_ids.extend(summary.get("citation_source_ids", []))

    compare_focus = {}
    if len(top_context) >= 2:
        compare_focus = {
            "rank_1": top_context[0],
            "rank_2": top_context[1],
            "instruction": (
                "If the user asks why #1 is preferred over #2, explain concrete clinical drivers: "
                "which adverse events or contraindication risks are higher in #2, what likely happens if #2 is chosen, "
                "and the efficacy-vs-safety tradeoff. Include comorbidity-fit differences when present. "
                "Do not only restate numeric score superiority."
            ),
        }

    prompt = (
        "You are MedGemma answering a question strictly from provided Astra-Gemma run artifacts. "
        "If answer is unsupported, say that clearly."
        f"\nQuestion: {payload.question}"
        f"\nRun context: {json.dumps(top_context, indent=2)}"
        f"\nComparison focus: {json.dumps(compare_focus, indent=2)}"
        "\nWrite 4-6 sentences. Prioritize causal explanation over numeric repetition."
        "\nIf discussing #1 vs #2, include: (1) why safety differs, (2) what risk increases with #2, "
        "(3) what benefit #2 may still offer, (4) practical monitoring implications."
    )
    context_blob = json.dumps(top_context)
    if not _is_grounded_question(payload.question, context_blob):
        answer = (
            "Insufficient grounded evidence in this run artifact to answer that question. "
            "Ask about protocol ranking, safety flags, trajectory changes, or cited evidence."
        )
    else:
        response = await medgemma_client.complete_text(prompt)
        answer = _clean_answer(response.text) or "Insufficient grounded evidence in this run artifact to answer confidently."
    answer += "\n\nResearch prototype disclaimer: this is not medical advice."

    repository.save_chat_log(payload.run_id, payload.question, answer)

    deduped_ids = list(dict.fromkeys(grounded_source_ids))[:8]
    return ChatExplainResponse(run_id=payload.run_id, answer=answer, grounded_source_ids=deduped_ids)
