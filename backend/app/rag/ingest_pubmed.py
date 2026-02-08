from __future__ import annotations

import argparse
import json
from pathlib import Path

import chromadb
import httpx

from app.services import settings


def load_seed(path: Path) -> list[dict]:
    return json.loads(path.read_text())


def fetch_pubmed_abstracts(query: str, page_size: int = 50, max_records: int = 300) -> list[dict]:
    records: list[dict] = []
    cursor = 0
    with httpx.Client(timeout=30.0) as client:
        while len(records) < max_records:
            resp = client.get(
                "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
                params={
                    "query": query,
                    "format": "json",
                    "pageSize": page_size,
                    "resultType": "core",
                    "cursorMark": cursor,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            hits = data.get("resultList", {}).get("result", [])
            if not hits:
                break
            for hit in hits:
                abstract = (hit.get("abstractText") or "").strip()
                if not abstract:
                    continue
                records.append(
                    {
                        "source_id": f"PMID-{hit.get('pmid', hit.get('id', 'unknown'))}",
                        "title": hit.get("title", "Untitled"),
                        "summary": abstract,
                        "year": int(hit.get("pubYear", 0)) if hit.get("pubYear") else None,
                        "source_url": f"https://pubmed.ncbi.nlm.nih.gov/{hit.get('pmid')}/" if hit.get("pmid") else "https://pubmed.ncbi.nlm.nih.gov/",
                        "condition": "type-2-diabetes",
                        "intervention": None,
                        "outcome": None,
                        "risk": None,
                    }
                )
                if len(records) >= max_records:
                    break
            cursor = data.get("nextCursorMark")
            if cursor is None:
                break
    return records


def ingest(records: list[dict]) -> int:
    settings.CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(settings.CHROMA_PATH))
    collection = client.get_or_create_collection("t2d_evidence")

    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict] = []

    for idx, row in enumerate(records):
        source_id = row.get("source_id") or f"E-{idx}"
        ids.append(source_id)
        documents.append(row.get("summary", ""))
        metadatas.append(
            {
                "source_id": source_id,
                "title": row.get("title", "Untitled"),
                "year": row.get("year"),
                "source_url": row.get("source_url", "https://example.com"),
                "condition": row.get("condition", "type-2-diabetes"),
                "intervention": row.get("intervention"),
                "outcome": row.get("outcome"),
                "risk": row.get("risk"),
            }
        )

    if ids:
        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
    return len(ids)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest T2D evidence into ChromaDB")
    parser.add_argument("--seed", type=Path, default=Path("../../data/guidelines/t2d_seed_evidence.json"))
    parser.add_argument("--query", type=str, default="type 2 diabetes pharmacotherapy randomized trial")
    parser.add_argument("--max-records", type=int, default=400)
    parser.add_argument("--seed-only", action="store_true")
    args = parser.parse_args()

    seed_records = load_seed(args.seed.resolve())
    all_records = list(seed_records)
    if not args.seed_only:
        all_records.extend(fetch_pubmed_abstracts(args.query, max_records=args.max_records))

    inserted = ingest(all_records)
    print(f"Ingested {inserted} evidence chunks into {settings.CHROMA_PATH}")


if __name__ == "__main__":
    main()

