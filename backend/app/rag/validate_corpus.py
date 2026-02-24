from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import chromadb

from app.services import settings


def _normalized_key(metadata: dict[str, Any], document: str) -> str:
    source_url = str(metadata.get("source_url") or "").strip().lower()
    title = str(metadata.get("title") or "").strip().lower()
    prefix = document[:120].strip().lower()
    if source_url:
        return f"url:{source_url}"
    if title:
        return f"title:{title}"
    return f"doc:{prefix}"


def validate(target_count: int, output_path: Path) -> dict[str, Any]:
    client = chromadb.PersistentClient(path=str(settings.CHROMA_PATH))
    collection = client.get_or_create_collection("t2d_evidence")
    count = collection.count()

    docs_batch = collection.get(limit=max(count, 1), include=["documents", "metadatas"])
    documents = docs_batch.get("documents", []) or []
    metadatas = docs_batch.get("metadatas", []) or []

    keys = [_normalized_key(metadata or {}, document or "") for metadata, document in zip(metadatas, documents)]
    duplicates = len(keys) - len(set(keys))
    duplicate_rate = (duplicates / max(1, len(keys))) * 100.0

    years = Counter()
    missing_year = 0
    for metadata in metadatas:
        year = (metadata or {}).get("year")
        if year is None:
            missing_year += 1
            continue
        years[str(year)] += 1

    report = {
        "target_count": target_count,
        "collection_count": count,
        "duplicates": duplicates,
        "duplicate_rate_percent": round(duplicate_rate, 3),
        "missing_year_count": missing_year,
        "year_distribution_top20": dict(years.most_common(20)),
        "meets_target_count": count == target_count,
        "meets_duplicate_budget": duplicate_rate < 5.0,
        "chroma_path": str(settings.CHROMA_PATH),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate indexed evidence corpus quality")
    parser.add_argument("--target-count", type=int, default=500)
    parser.add_argument("--output", type=Path, default=Path("../output/evidence/evidence_report.json"))
    args = parser.parse_args()

    report = validate(args.target_count, args.output.resolve())
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
