# Astra-Gemma

Astra-Gemma is an agentic in-silico clinical trial engine for synthetic Type 2 Diabetes patient twins.
It runs 1,000 coarse simulation trajectories, re-simulates top protocols with MedGemma-guided calibration,
and returns ranked treatment hypotheses with safety flags, evidence citations, explainable rationale,
and a population-stability map across nearby synthetic patient variants.

## Why this project

This project is built for the MedGemma Impact Challenge with explicit alignment to:

- Effective HAI-DEF usage (MedGemma-centric reasoning loop)
- Product feasibility (fully local stack on M4 Air constraints)
- Agentic workflow redesign (Researcher -> Simulator -> Critic)
- Execution quality (streaming UI, reproducible code, submission artifacts)

## Stack

- Backend: FastAPI + LangGraph + SQLite + ChromaDB
- Agent orchestration: LangGraph state machine (`Researcher -> Simulator -> Critic`) with per-node checkpoints
- Model runtime: MedGemma via `mlx` or `ollama` (mock runtime supported for local scaffolding)
- Frontend: Next.js app router + live SSE dashboard + population stability map

## Quick start

Requires Python 3.11+ (bootstrap prefers Python 3.12 if available).

```bash
./scripts/bootstrap.sh
cp backend/.env.example backend/.env
make migrate
./scripts/dev.sh
```

Then open:

- Frontend: `http://localhost:3000`
- Backend health: `http://localhost:8000/health`

## MedGemma runtime setup

Set `backend/.env`:

```bash
MEDGEMMA_RUNTIME=mlx
MEDGEMMA_MODEL=google/medgemma-27b-it
MEDGEMMA_MLX_ENDPOINT=http://127.0.0.1:8080/v1/chat/completions
```

If using Ollama:

```bash
MEDGEMMA_RUNTIME=ollama
MEDGEMMA_OLLAMA_MODEL=medgemma
```

For local scaffolding without model runtime:

```bash
MEDGEMMA_RUNTIME=mock
```

## Core APIs

- `POST /api/v1/runs` -> start a run from `PatientTwinInput`
- `POST /api/v1/runs/{run_id}/resume` -> resume from latest node checkpoint
- `GET /api/v1/runs/{run_id}/events` -> SSE event stream
- `GET /api/v1/runs/{run_id}/result` -> final run artifact
- `GET /api/v1/runs/{run_id}/population-map` -> 27-cell recommendation stability map
- `POST /api/v1/chat/explain` -> grounded run Q&A

## Evidence ingestion

Seed evidence is provided in `data/guidelines/t2d_seed_evidence.json`.
To ingest and validate a 500-record curated corpus:

```bash
source .venv312/bin/activate
cd backend
python -m app.rag.ingest_pubmed --seed ../data/guidelines/t2d_seed_evidence.json --query-file ../data/guidelines/t2d_queries.json --target-count 500
python -m app.rag.validate_corpus --target-count 500
```

Validation report: `output/evidence/evidence_report.json`.

## Benchmarks

```bash
source .venv312/bin/activate
cd backend
MEDGEMMA_RUNTIME=mock ENFORCE_ALEMBIC_HEAD=false python scripts/benchmark_runs.py
```

Outputs:
- `output/benchmarks/benchmark_raw.json`
- `output/benchmarks/benchmark_summary.md`

## Testing

```bash
source .venv312/bin/activate
cd backend
pytest
```

Frontend E2E:

```bash
cd frontend
npx playwright test
```

Deterministic screenshots:

```bash
./scripts/capture_screenshots.sh
```

## Submission artifacts

See `submission/` for:

- `writeup.md`
- `video_script.md`
- `judge_qa.md`
- `impact_calc.md`

## Safety disclaimer

Astra-Gemma is a research prototype for simulation and education only.
It does not provide medical advice, diagnosis, or treatment recommendations.
