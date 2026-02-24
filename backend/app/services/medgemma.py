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
        if "READY" in prompt:
            return MedGemmaResponse(text="READY")
        if "JSON" in prompt.upper() and "protocols" in prompt.lower():
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
        if "coefficient" in prompt.lower():
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
        if "answer the question" in prompt.lower():
            return MedGemmaResponse(
                text="Based on run artifacts, protocol #1 balances HbA1c reduction and safety better than alternatives."
            )
        return MedGemmaResponse(text="MedGemma mock response.")

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
