from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.models.schemas import EvidenceChunk
from app.services import settings


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9\-]{3,}", text.lower()))


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

    @staticmethod
    def _expand_queries(query: str) -> list[str]:
        return [
            query,
            f"{query} guideline evidence",
            f"{query} contraindication safety",
            f"{query} adherence metabolic outcome",
        ]

    @staticmethod
    def _matches_filters(chunk: EvidenceChunk, filters: dict[str, Any] | None) -> bool:
        if not filters:
            return True
        if "condition" in filters and chunk.condition != filters["condition"]:
            return False
        min_year = filters.get("min_year")
        if min_year is not None and chunk.year is not None and chunk.year < int(min_year):
            return False
        return True

    @staticmethod
    def _rerank(query: str, items: list[tuple[EvidenceChunk, float | None]]) -> list[EvidenceChunk]:
        query_tokens = _tokenize(query)

        def score(entry: tuple[EvidenceChunk, float | None]) -> float:
            chunk, distance = entry
            corpus_tokens = _tokenize(f"{chunk.title} {chunk.summary} {chunk.intervention or ''} {chunk.risk or ''}")
            overlap = len(query_tokens & corpus_tokens) / max(1, len(query_tokens))
            recency = (chunk.year or 2010) / 2100.0
            vector_component = 1.0 / (1.0 + float(distance or 1.0))
            return (0.55 * overlap) + (0.25 * vector_component) + (0.20 * recency)

        ranked = sorted(items, key=score, reverse=True)
        return [chunk for chunk, _ in ranked]

    def retrieve(self, query: str, k: int = 12, filters: dict[str, Any] | None = None) -> list[EvidenceChunk]:
        if self._collection is not None:
            try:
                count = self._collection.count()
                if count > 0:
                    expanded_queries = self._expand_queries(query)
                    n_results = min(max(k * 4, k), count)
                    result = self._collection.query(
                        query_texts=expanded_queries,
                        n_results=n_results,
                        include=["documents", "metadatas", "distances"],
                    )
                    docs_lists = result.get("documents", [])
                    metadata_lists = result.get("metadatas", [])
                    distance_lists = result.get("distances", [])

                    dedup: dict[str, tuple[EvidenceChunk, float | None]] = {}
                    for docs, metadatas, distances in zip(docs_lists, metadata_lists, distance_lists):
                        for doc, metadata, distance in zip(docs, metadatas, distances):
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
                            chunk = EvidenceChunk(**payload)
                            if not self._matches_filters(chunk, filters):
                                continue
                            existing = dedup.get(chunk.source_id)
                            if existing is None or float(distance or 10.0) < float(existing[1] or 10.0):
                                dedup[chunk.source_id] = (chunk, distance)

                    ranked = self._rerank(query, list(dedup.values()))
                    if ranked:
                        return ranked[:k]
            except Exception:
                pass

        filtered = [item for item in self._fallback_data if self._matches_filters(item, filters)]
        if filtered:
            return filtered[:k]
        return [
            EvidenceChunk(
                source_id="E-FALLBACK-001",
                title="Fallback Diabetes Guidance",
                summary="Personalized glucose control requires balancing efficacy, safety, and adherence.",
                source_url="https://example.com/fallback",
            )
        ]


retriever = EvidenceRetriever()
