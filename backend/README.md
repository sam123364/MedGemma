# Astra-Gemma Backend

## Run locally

```bash
python3 -m venv ../.venv
source ../.venv/bin/activate
pip install -e .[dev]
uvicorn app.main:app --reload --port 8000
```

## Key environment variables

- `MEDGEMMA_RUNTIME`: `mock`, `mlx`, or `ollama`
- `MEDGEMMA_MODEL`: model identifier
- `MEDGEMMA_MLX_ENDPOINT`: OpenAI-compatible endpoint for mlx server
- `ASTRA_DB_PATH`: sqlite path
- `ASTRA_CHROMA_PATH`: chroma persistence path

## API summary

- `POST /api/v1/runs`
- `GET /api/v1/runs/{run_id}/events`
- `GET /api/v1/runs/{run_id}/result`
- `POST /api/v1/chat/explain`

