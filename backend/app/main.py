from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_chat import router as chat_router
from app.api.routes_runs import router as runs_router
from app.db.sqlite import repository
from app.services import settings
from app.services.medgemma import medgemma_client


app = FastAPI(
    title="Astra-Gemma API",
    version="0.1.0",
    description="Agentic in-silico trial engine for synthetic Type 2 Diabetes personalization.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup() -> None:
    repository.init_db()
    await medgemma_client.warmup()


app.include_router(runs_router)
app.include_router(chat_router)


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "service": "astra-gemma-backend",
        "medgemma_runtime": settings.MEDGEMMA_RUNTIME,
        "medgemma_model": settings.MEDGEMMA_MODEL,
    }

