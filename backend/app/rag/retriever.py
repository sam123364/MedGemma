from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.models.schemas import EvidenceChunk
from app.services import settings


class EvidenceRetriever:
    def __init__(self) -> None:
        self._fallback_data = self._load_fallback_data()
        self._chroma_client = None
        self._collection = None
        try:
            import chromadb

            settings.CHROMA_PATH.mkdir(parents=True, exist_ok=True)
            self._chroma_client = chromadb.PersistentClient(path=str(settings.CHROMA_PATH))
            self._collection = self._chroma_client.get_or_create_collection("t2d_evidence")
        except Exception:
            self._chroma_client = None
            self._collection = None

    def _load_fallback_data(self) -> list[EvidenceChunk]:
        seed_path = Path(__file__).resolve().parents[3] / "data" / "guidelines" / "t2d_seed_evidence.json"
        if not seed_path.exists():
            return []
        raw = json.loads(seed_path.read_text())
        return [EvidenceChunk(**row) for row in raw]

    def retrieve(self, query: str, k: int = 12) -> list[EvidenceChunk]:
        if self._collection is not None:
            try:
                count = self._collection.count()
                if count > 0:
                    result = self._collection.query(query_texts=[query], n_results=min(k, count))
                    docs = result.get("documents", [[]])[0]
                    metadatas = result.get("metadatas", [[]])[0]
                    chunks: list[EvidenceChunk] = []
                    for doc, metadata in zip(docs, metadatas):
                        payload: dict[str, Any] = {
                            "source_id": metadata.get("source_id", "E-UNKNOWN"),
                            "title": metadata.get("title", "Untitled"),
                            "summary": doc,
                            "year": metadata.get("year"),
                            "source_url": metadata.get("source_url", "https://example.com"),
                            "condition": metadata.get("condition", "type-2-diabetes"),
                            "intervention": metadata.get("intervention"),
                            "outcome": metadata.get("outcome"),
                            "risk": metadata.get("risk"),
                        }
                        chunks.append(EvidenceChunk(**payload))
                    if chunks:
                        return chunks
            except Exception:
                pass

        if not self._fallback_data:
            return [
                EvidenceChunk(
                    source_id="E-FALLBACK-001",
                    title="Fallback Diabetes Guidance",
                    summary="Personalized glucose control requires balancing efficacy, safety, and adherence.",
                    source_url="https://example.com/fallback",
                )
            ]
        return self._fallback_data[:k]


retriever = EvidenceRetriever()

