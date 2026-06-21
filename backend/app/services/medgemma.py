from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import httpx

from app.services import settings


_JSON_BLOCK = re.compile(r"\{[\s\S]*\}|\[[\s\S]*\]")


@dataclass
class MedGemmaResponse:
    text: str
    raw: dict[str, Any] | None = None


class MedGemmaClient:
    def __init__(self) -> None:
        self.runtime = settings.MEDGEMMA_RUNTIME
        self.model = settings.MEDGEMMA_MODEL
        self._http = httpx.AsyncClient(timeout=settings.MEDGEMMA_TIMEOUT_SECONDS)

    async def warmup(self) -> None:
        try:
            await self.complete_text("Return exactly the word READY.")
        except Exception:
            # Warmup failure should not crash the API process.
            return

    async def complete_text(self, prompt: str) -> MedGemmaResponse:
        if self.runtime == "mlx":
            return await self._complete_mlx(prompt)
        if self.runtime == "ollama":
            return await self._complete_ollama(prompt)
        return self._complete_mock(prompt)

    async def complete_json(self, prompt: str) -> tuple[dict[str, Any] | list[Any] | None, MedGemmaResponse]:
        response = await self.complete_text(prompt)
        payload = self._extract_json(response.text)
        return payload, response

    async def _complete_mlx(self, prompt: str) -> MedGemmaResponse:
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are MedGemma. Return concise clinical reasoning."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": settings.MEDGEMMA_MAX_TOKENS,
        }
        try:
            resp = await self._http.post(settings.MEDGEMMA_MLX_ENDPOINT, json=body)
            resp.raise_for_status()
        except httpx.TimeoutException as exc:
            raise RuntimeError(
                "MedGemma request timed out "
                f"after {settings.MEDGEMMA_TIMEOUT_SECONDS:.0f}s "
                f"(endpoint={settings.MEDGEMMA_MLX_ENDPOINT}, model={self.model}). "
                "Increase MEDGEMMA_TIMEOUT_SECONDS or reduce prompt/token load."
            ) from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code if exc.response is not None else "unknown"
            body_preview = ""
            if exc.response is not None:
                body_preview = exc.response.text[:220]
            raise RuntimeError(
                f"MedGemma endpoint returned HTTP {status}. Response preview: {body_preview}"
            ) from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"MedGemma transport error: {exc}") from exc

        data = resp.json()
        text = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        return MedGemmaResponse(text=text, raw=data)

    async def _complete_ollama(self, prompt: str) -> MedGemmaResponse:
        body = {
            "model": settings.MEDGEMMA_OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_predict": 900,
            },
        }
        resp = await self._http.post(settings.MEDGEMMA_OLLAMA_URL, json=body)
        resp.raise_for_status()
        data = resp.json()
        text = data.get("response", "")
        return MedGemmaResponse(text=text, raw=data)

    def _complete_mock(self, prompt: str) -> MedGemmaResponse:
        prompt_lower = prompt.lower()
        if "READY" in prompt:
            return MedGemmaResponse(text="READY")
        if "json" in prompt_lower and "protocols" in prompt_lower:
            mock_payload = {
                "protocols": [
                    {
                        "protocol_id": "P-GLP1-MET",
                        "label": "Metformin + GLP-1 base protocol",
                        "meds": ["metformin", "semaglutide"],
                        "lifestyle_plan": "Mediterranean-style diet and 150 min weekly aerobic exercise.",
                        "rationale": "Combines insulin sensitization and appetite-mediated glycemic control.",
                        "citation_source_ids": ["E-ADA-2025", "E-PUBMED-001"],
                    }
                ]
            }
            return MedGemmaResponse(text=json.dumps(mock_payload))
        if "coefficient" in prompt_lower or "calibrat" in prompt_lower:
            return MedGemmaResponse(
                text=json.dumps(
                    {
                        "efficacy_multiplier": 1.02,
                        "safety_adjustment": -0.02,
                        "adherence_adjustment": 0.01,
                        "reasoning": "Protocol expected to improve glycemic control with moderate safety burden.",
                    }
                )
            )
        if "top-ranked" in prompt_lower or "top candidates" in prompt_lower or "explain the top" in prompt_lower or "why #1" in prompt_lower or "recommendation" in prompt_lower:
            return MedGemmaResponse(
                text=(
                    "The top-ranked regimen is preferred due to its superior pharmacodynamic profiling. "
                    "Combining metformin (which limits hepatic gluconeogenesis via AMPK pathway activation) with a "
                    "GLP-1 receptor agonist (which enhances glucose-dependent insulin secretion and suppresses glucagon "
                    "release) provides synergistic glycemic control. This dual-pathway mechanism targets multiple components "
                    "of the pathological cascade in Type 2 Diabetes, optimizing glycemic trajectory while mitigating "
                    "the safety penalty associated with hypoglycemia."
                )
            )
        if "safety" in prompt_lower or "contraindication" in prompt_lower or "warning" in prompt_lower:
            return MedGemmaResponse(
                text=(
                    "The primary safety guardrails target renal function thresholds and cardiorenal overlap. "
                    "Metformin is contraindicated when the estimated Glomerular Filtration Rate (eGFR) falls below "
                    "30 mL/min/1.73m² due to the elevated risk of systemic accumulation and metformin-associated lactic acidosis (MALA). "
                    "SGLT-2 inhibitors are favored for eGFR between 30 and 60 for renal protective hemodynamics, but they "
                    "require monitoring for volume depletion and euglycemic diabetic ketoacidosis (DKA)."
                )
            )
        if "renal" in prompt_lower or "egfr" in prompt_lower or "lactic" in prompt_lower or "kidney" in prompt_lower:
            return MedGemmaResponse(
                text=(
                    "Renal risk assessment centers on drug clearance capacity. Metformin is excreted unchanged "
                    "by the kidneys via glomerular filtration and active tubular secretion. Under impaired renal perfusion "
                    "(eGFR < 30), metformin clearance drops exponentially, resulting in increased blood lactate levels. "
                    "Conversely, SGLT2 inhibitors block sodium-glucose cotransporter 2 in the proximal convoluted tubule, "
                    "reducing intraglomerular pressure, which initially drops eGFR slightly before stabilizing to offer long-term nephroprotection."
                )
            )
        if "astra-gemma" in prompt_lower or "run" in prompt_lower or "answer" in prompt_lower:
            return MedGemmaResponse(
                text=(
                    "Analysis of the 180-day simulated trajectories shows that the leading protocol (Metformin + GLP-1 RA) "
                    "achieved a mean HbA1c reduction of 1.8%, outperforming the Metformin + DPP-4 inhibitor regimen by 0.6% "
                    "without worsening the safety risk profile. The GLP-1 RA component additionally provides a cardiovascular "
                    "risk reduction benefit, making it highly suitable for patients with underlying atherosclerotic cardiovascular disease."
                )
            )
        return MedGemmaResponse(text="MedGemma clinical simulation model initialized: ready to resolve pharmacotherapy queries.")

    @staticmethod
    def _extract_json(text: str) -> dict[str, Any] | list[Any] | None:
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = _JSON_BLOCK.search(text)
            if not match:
                return None
            candidate = match.group(0)
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                return None


medgemma_client = MedGemmaClient()
