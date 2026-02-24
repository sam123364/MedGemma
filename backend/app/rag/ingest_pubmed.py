from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import chromadb
import httpx

from app.services import settings


EUROPE_PMC_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


def load_seed(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text())
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def load_queries(query_file: Path | None, fallback_query: str) -> list[str]:
    if query_file is None or not query_file.exists():
        return [fallback_query]
    payload = json.loads(query_file.read_text())
    if isinstance(payload, list):
        queries = [str(item).strip() for item in payload if str(item).strip()]
        return queries or [fallback_query]
    return [fallback_query]


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_source_url(pmid: str | None, fallback: str = "https://pubmed.ncbi.nlm.nih.gov/") -> str:
    if pmid:
        return f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
    return fallback


def _record_key(record: dict[str, Any]) -> str:
    pmid = str(record.get("pmid") or record.get("source_id") or "").strip().lower()
    source_url = str(record.get("source_url") or "").strip().lower()
    title = normalize_text(str(record.get("title") or "")).lower()
    if pmid:
        return f"pmid:{pmid}"
    if source_url:
        return f"url:{source_url}"
    return f"title:{title}"


def dedupe_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[str, dict[str, Any]] = {}
    for record in records:
        key = _record_key(record)
        existing = deduped.get(key)
        if existing is None:
            deduped[key] = record
            continue
        # Prefer entries with longer abstracts and newer year.
        existing_len = len(str(existing.get("summary") or ""))
        new_len = len(str(record.get("summary") or ""))
        existing_year = int(existing.get("year") or 0)
        new_year = int(record.get("year") or 0)
        if (new_len, new_year) > (existing_len, existing_year):
            deduped[key] = record
    return list(deduped.values())


def fetch_pubmed_abstracts(
    query: str,
    page_size: int = 50,
    max_records: int = 300,
    min_year: int = 2010,
    max_year: int | None = None,
    min_abstract_chars: int = 180,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    cursor_mark = "*"

    with httpx.Client(timeout=40.0) as client:
        while len(records) < max_records:
            resp = client.get(
                EUROPE_PMC_URL,
                params={
                    "query": query,
                    "format": "json",
                    "pageSize": page_size,
                    "resultType": "core",
                    "cursorMark": cursor_mark,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            hits = data.get("resultList", {}).get("result", [])
            if not hits:
                break

            for hit in hits:
                abstract = normalize_text(str(hit.get("abstractText") or ""))
                if len(abstract) < min_abstract_chars:
                    continue
                pub_year_raw = hit.get("pubYear")
                pub_year = int(pub_year_raw) if pub_year_raw else None
                if pub_year is not None and pub_year < min_year:
                    continue
                if max_year is not None and pub_year is not None and pub_year > max_year:
                    continue

                pmid = str(hit.get("pmid") or "").strip() or None
                records.append(
                    {
                        "source_id": f"PMID-{pmid}" if pmid else f"EPMC-{hit.get('id', 'unknown')}",
                        "title": normalize_text(str(hit.get("title") or "Untitled")),
                        "summary": abstract,
                        "year": pub_year,
                        "source_url": normalize_source_url(pmid),
                        "condition": "type-2-diabetes",
                        "intervention": normalize_text(str(hit.get("keywordList") or "")) or None,
                        "outcome": None,
                        "risk": None,
                        "pmid": pmid,
                    }
                )
                if len(records) >= max_records:
                    break

            next_cursor = data.get("nextCursorMark")
            if not next_cursor or next_cursor == cursor_mark:
                break
            cursor_mark = next_cursor

    return records


def _prepare_for_index(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prepared: list[dict[str, Any]] = []
    for idx, row in enumerate(records):
        source_id = str(row.get("source_id") or f"E-{idx}")
        prepared.append(
            {
                "source_id": source_id,
                "title": normalize_text(str(row.get("title") or "Untitled")),
                "summary": normalize_text(str(row.get("summary") or "")),
                "year": row.get("year"),
                "source_url": str(row.get("source_url") or "https://example.com"),
                "condition": str(row.get("condition") or "type-2-diabetes"),
                "intervention": row.get("intervention"),
                "outcome": row.get("outcome"),
                "risk": row.get("risk"),
            }
        )
    return prepared


def ingest(records: list[dict[str, Any]], reset_collection: bool = True) -> int:
    settings.CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(settings.CHROMA_PATH))
    if reset_collection:
        try:
            client.delete_collection("t2d_evidence")
        except Exception:
            pass
    collection = client.get_or_create_collection("t2d_evidence")

    prepared = _prepare_for_index(records)
    if not prepared:
        return 0

    collection.upsert(
        ids=[row["source_id"] for row in prepared],
        documents=[row["summary"] for row in prepared],
        metadatas=[
            {
                "source_id": row["source_id"],
                "title": row["title"],
                "year": row.get("year"),
                "source_url": row["source_url"],
                "condition": row.get("condition"),
                "intervention": row.get("intervention"),
                "outcome": row.get("outcome"),
                "risk": row.get("risk"),
            }
            for row in prepared
        ],
    )
    return len(prepared)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest T2D evidence into ChromaDB")
    parser.add_argument("--seed", type=Path, default=Path("../../data/guidelines/t2d_seed_evidence.json"))
    parser.add_argument("--query-file", type=Path, default=Path("../../data/guidelines/t2d_queries.json"))
    parser.add_argument("--query", type=str, default="type 2 diabetes pharmacotherapy randomized trial")
    parser.add_argument("--target-count", type=int, default=500)
    parser.add_argument("--per-query-max", type=int, default=220)
    parser.add_argument("--min-year", type=int, default=2010)
    parser.add_argument("--max-year", type=int, default=None)
    parser.add_argument("--min-abstract-chars", type=int, default=180)
    parser.add_argument("--seed-only", action="store_true")
    parser.add_argument("--no-reset-collection", action="store_true")
    args = parser.parse_args()

    seed_records = load_seed(args.seed.resolve())
    combined = list(seed_records)

    if not args.seed_only:
        queries = load_queries(args.query_file.resolve() if args.query_file else None, args.query)
        for query in queries:
            combined.extend(
                fetch_pubmed_abstracts(
                    query=query,
                    max_records=args.per_query_max,
                    min_year=args.min_year,
                    max_year=args.max_year,
                    min_abstract_chars=args.min_abstract_chars,
                )
            )

    deduped = dedupe_records(combined)
    deduped.sort(key=lambda item: (item.get("year") or 0, len(str(item.get("summary") or ""))), reverse=True)
    trimmed = deduped[: args.target_count]
    inserted = ingest(trimmed, reset_collection=not args.no_reset_collection)
    print(
        json.dumps(
            {
                "target_count": args.target_count,
                "source_records": len(combined),
                "deduped_records": len(deduped),
                "inserted_records": inserted,
                "chroma_path": str(settings.CHROMA_PATH),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
