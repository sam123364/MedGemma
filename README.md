# Astra-Gemma

Astra-Gemma is an agentic in-silico clinical trial engine for synthetic Type 2 Diabetes patient twins.
It runs 1,000 coarse simulation trajectories, re-simulates top protocols with MedGemma-guided calibration,
and returns ranked treatment hypotheses with safety flags, evidence citations, and explainable rationale.

## Why this project

This project is built for the MedGemma Impact Challenge with explicit alignment to:

- Effective HAI-DEF usage (MedGemma-centric reasoning loop)
- Product feasibility (fully local stack on M4 Air constraints)
- Agentic workflow redesign (Researcher -> Simulator -> Critic)
- Execution quality (streaming UI, reproducible code, submission artifacts)

## Stack

- Backend: FastAPI + asyncio + SQLite + ChromaDB
- Agent orchestration: modular multi-agent pipeline (`Researcher`, `Simulator`, `Critic`)
- Model runtime: MedGemma via `mlx` or `ollama` (mock runtime supported for local scaffolding)
- Frontend: Next.js app router + live SSE dashboard

## Quick start

Requires Python 3.11+ (bootstrap prefers Python 3.12 if available).

```bash
./scripts/bootstrap.sh
cp backend/.env.example backend/.env
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
- `GET /api/v1/runs/{run_id}/events` -> SSE event stream
- `GET /api/v1/runs/{run_id}/result` -> final run artifact
- `POST /api/v1/chat/explain` -> grounded run Q&A

## Evidence ingestion

Seed evidence is provided in `data/guidelines/t2d_seed_evidence.json`.
To ingest seed + PubMed-like records into Chroma:

```bash
source .venv/bin/activate
cd backend
python -m app.rag.ingest_pubmed --seed ../../data/guidelines/t2d_seed_evidence.json --max-records 500
```

## Testing

```bash
source .venv/bin/activate
cd backend
pytest
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
