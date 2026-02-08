from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException

from app.db.sqlite import repository
from app.models.schemas import ChatExplainRequest, ChatExplainResponse
from app.services.medgemma import medgemma_client


router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


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
        protocol = item.get("protocol", {})
        score = item.get("score", {})
        flags = item.get("flags", [])
        top_context.append(
            {
                "protocol_id": protocol.get("protocol_id"),
                "label": protocol.get("label"),
                "score": score,
                "flags": flags[:4],
                "rationale": protocol.get("rationale"),
            }
        )
        grounded_source_ids.extend(protocol.get("citation_source_ids", []))

    prompt = (
        "You are MedGemma answering a question strictly from provided Astra-Gemma run artifacts. "
        "If answer is unsupported, say that clearly."
        f"\nQuestion: {payload.question}"
        f"\nRun context: {json.dumps(top_context, indent=2)}"
        "\nReturn a concise answer in under 120 words."
    )

    response = await medgemma_client.complete_text(prompt)
    answer = response.text.strip() or "Insufficient grounded evidence in this run artifact to answer confidently."
    answer += "\n\nResearch prototype disclaimer: this is not medical advice."

    repository.save_chat_log(payload.run_id, payload.question, answer)

    deduped_ids = list(dict.fromkeys(grounded_source_ids))[:8]
    return ChatExplainResponse(run_id=payload.run_id, answer=answer, grounded_source_ids=deduped_ids)

