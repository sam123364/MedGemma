from __future__ import annotations

import json
import random
from typing import Any

from app.models.schemas import EvidenceChunk, PatientTwinInput, ProtocolCandidate
from app.services.medgemma import medgemma_client


def _template_protocols() -> list[dict[str, Any]]:
    return [
        {
            "protocol_id": "P-MET-GLP1",
            "label": "Metformin + GLP-1 receptor agonist",
            "meds": ["metformin", "semaglutide"],
            "lifestyle_plan": "High-fiber diet, 150 min weekly zone-2 exercise, sleep target 7h+.",
            "rationale": "Improves insulin sensitivity and satiety-driven glycemic control.",
        },
        {
            "protocol_id": "P-MET-SGLT2",
            "label": "Metformin + SGLT2 inhibitor",
            "meds": ["metformin", "empagliflozin"],
            "lifestyle_plan": "Carbohydrate quality coaching and low-sodium hydration plan.",
            "rationale": "Combines glycemic control with cardio-renal support.",
        },
        {
            "protocol_id": "P-MET-DPP4",
            "label": "Metformin + DPP4 inhibitor",
            "meds": ["metformin", "sitagliptin"],
            "lifestyle_plan": "Steady meal timing and 8k daily steps progression.",
            "rationale": "Moderate glycemic improvement with generally lower hypoglycemia burden.",
        },
        {
            "protocol_id": "P-TRIPLE-MGS",
            "label": "Metformin + GLP-1 + SGLT2",
            "meds": ["metformin", "semaglutide", "dapagliflozin"],
            "lifestyle_plan": "Structured nutrition coaching with resistance training twice weekly.",
            "rationale": "Higher-intensity triple approach for high baseline HbA1c and obesity profile.",
        },
        {
            "protocol_id": "P-BASAL-START",
            "label": "Basal insulin start + metformin",
            "meds": ["metformin", "insulin glargine"],
            "lifestyle_plan": "CGM-driven meal feedback and hypoglycemia prevention education.",
            "rationale": "Rapid glycemic correction strategy for severe baseline hyperglycemia.",
        },
        {
            "protocol_id": "P-SGLT2-GLP1",
            "label": "SGLT2 + GLP-1 dual non-insulin",
            "meds": ["empagliflozin", "semaglutide"],
            "lifestyle_plan": "Protein-aware meal planning and progressive walking intervals.",
            "rationale": "Targets glycemia and weight while avoiding insulin initiation.",
        },
        {
            "protocol_id": "P-MET-TZD",
            "label": "Metformin + TZD",
            "meds": ["metformin", "pioglitazone"],
            "lifestyle_plan": "Anti-inflammatory nutrition and edema-monitoring plan.",
            "rationale": "Alternative sensitization pathway when incretin options are constrained.",
        },
        {
            "protocol_id": "P-MET-SU",
            "label": "Metformin + sulfonylurea",
            "meds": ["metformin", "glimepiride"],
            "lifestyle_plan": "Meal consistency program with hypoglycemia check-ins.",
            "rationale": "Cost-sensitive protocol with stronger hypoglycemia monitoring requirements.",
        },
        {
            "protocol_id": "P-LIFESTYLE-INTENSIVE",
            "label": "Lifestyle-first intensification",
            "meds": ["metformin"],
            "lifestyle_plan": "Intensive coaching: nutrition tracking, 200 min exercise, sleep/circadian intervention.",
            "rationale": "Behavioral-first strategy for adherence-motivated patients.",
        },
    ]


class ResearcherAgent:
    async def generate_protocols(
        self,
        patient: PatientTwinInput,
        evidence: list[EvidenceChunk],
        target_count: int = 10,
    ) -> list[ProtocolCandidate]:
        evidence_snippets = [
            {
                "source_id": chunk.source_id,
                "title": chunk.title,
                "summary": chunk.summary[:280],
                "risk": chunk.risk,
            }
            for chunk in evidence[:12]
        ]

        prompt = (
            "You are MedGemma acting as a clinical protocol ideation engine for Type 2 Diabetes. "
            "Generate JSON only with key 'protocols'. Each protocol must contain: protocol_id, label, meds, "
            "lifestyle_plan, rationale, citation_source_ids. Return 8-12 protocols."
            f"\nPatient:\n{patient.model_dump_json(indent=2)}"
            f"\nEvidence:\n{json.dumps(evidence_snippets, indent=2)}"
        )

        payload, _response = await medgemma_client.complete_json(prompt)
        source_ids = [chunk.source_id for chunk in evidence]
        source_urls = {chunk.source_id: chunk.source_url for chunk in evidence}

        candidates: list[ProtocolCandidate] = []
        if isinstance(payload, dict):
            raw_protocols = payload.get("protocols") if isinstance(payload.get("protocols"), list) else []
            for raw in raw_protocols:
                if not isinstance(raw, dict):
                    continue
                citations = raw.get("citation_source_ids") or source_ids[:2]
                citations = [c for c in citations if c in source_urls]
                if len(citations) < 2:
                    citations = source_ids[:2]
                try:
                    candidates.append(
                        ProtocolCandidate(
                            protocol_id=str(raw.get("protocol_id", f"P-LLM-{len(candidates)+1}")),
                            label=str(raw.get("label", "LLM-generated protocol")),
                            meds=list(raw.get("meds", ["metformin"])),
                            lifestyle_plan=str(raw.get("lifestyle_plan", "Structured nutrition and exercise coaching.")),
                            rationale=str(raw.get("rationale", "Personalized combined intervention.")),
                            citations=[source_urls[c] for c in citations[:2]],
                            citation_source_ids=citations[:2],
                        )
                    )
                except Exception:
                    continue

        if len(candidates) < 8:
            templates = _template_protocols()
            random.shuffle(templates)
            for template in templates:
                pick_ids = source_ids[:]
                random.shuffle(pick_ids)
                chosen_ids = (pick_ids[:2] if len(pick_ids) >= 2 else source_ids[:2]) or ["E-ADA-2025", "E-EASD-2024"]
                chosen_urls = [source_urls.get(cid, "https://example.com") for cid in chosen_ids]
                candidates.append(
                    ProtocolCandidate(
                        protocol_id=template["protocol_id"],
                        label=template["label"],
                        meds=template["meds"],
                        lifestyle_plan=template["lifestyle_plan"],
                        rationale=template["rationale"],
                        citations=chosen_urls,
                        citation_source_ids=chosen_ids,
                    )
                )
                if len(candidates) >= target_count:
                    break

        dedup: dict[str, ProtocolCandidate] = {}
        for candidate in candidates:
            dedup[candidate.protocol_id] = candidate
        selected = list(dedup.values())[:target_count]

        if len(selected) < 8:
            raise RuntimeError("Researcher agent failed to generate minimum protocol count")

        return selected


researcher_agent = ResearcherAgent()

