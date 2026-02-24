# Astra-Gemma Backend

## Run locally

```bash
python3 -m venv ../.venv
source ../.venv/bin/activate
pip install -e .[dev]
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

## Key environment variables

- `MEDGEMMA_RUNTIME`: `mock`, `mlx`, or `ollama`
- `MEDGEMMA_MODEL`: model identifier
- `MEDGEMMA_MLX_ENDPOINT`: OpenAI-compatible endpoint for mlx server
- `MEDGEMMA_TIMEOUT_SECONDS`: request timeout for MedGemma API calls
- `MEDGEMMA_MAX_TOKENS`: completion token budget per call
- `ASTRA_DB_PATH`: sqlite path
- `ASTRA_CHROMA_PATH`: chroma persistence path
- `AUTO_RESUME_INCOMPLETE_RUNS`: resume queued/running/failed checkpointed runs at startup
- `ASTRA_FAIL_AFTER_NODE`: fault injection node name (for resume tests)
- `ENFORCE_ALEMBIC_HEAD`: verify DB revision before serving requests

## API summary

- `POST /api/v1/runs`
- `POST /api/v1/runs/{run_id}/resume`
- `GET /api/v1/runs/{run_id}/events`
- `GET /api/v1/runs/{run_id}/result`
- `GET /api/v1/runs/{run_id}/population-map`
- `POST /api/v1/chat/explain`

## Migrations

```bash
source ../.venv/bin/activate
alembic upgrade head
```
