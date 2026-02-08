from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import JSONResponse, StreamingResponse

from app.db.sqlite import repository
from app.graph.workflow import workflow_service
from app.models.schemas import PatientTwinInput, RunStartResponse, SCHEMA_VERSION
from app.services import settings


router = APIRouter(prefix="/api/v1", tags=["runs"])


def _sse_line(event_id: int, event_type: str, data: dict) -> str:
    return f"id: {event_id}\nevent: {event_type}\ndata: {json.dumps(data)}\n\n"


@router.post("/runs", response_model=RunStartResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_run(
    patient: PatientTwinInput,
    target_count: int = Query(default=10, ge=8, le=12),
) -> RunStartResponse:
    run_id = workflow_service.create_run_id()
    repository.create_run(run_id, model_runtime=settings.MEDGEMMA_RUNTIME)
    workflow_service.start_run(run_id, patient, target_count=target_count)
    return RunStartResponse(run_id=run_id, status="queued")


@router.get("/runs/{run_id}/events")
async def stream_events(run_id: str, last_event_id: int = Query(default=0, ge=0)) -> StreamingResponse:
    if repository.get_run_status(run_id) is None:
        raise HTTPException(status_code=404, detail="run_id not found")

    async def event_generator() -> AsyncIterator[str]:
        current_event_id = last_event_id
        idle_cycles = 0
        while True:
            events = repository.get_events_after(run_id, current_event_id)
            if events:
                idle_cycles = 0
                for event in events:
                    current_event_id = event["event_id"]
                    payload = {
                        "schema_version": SCHEMA_VERSION,
                        "run_id": run_id,
                        "timestamp": event["timestamp"],
                        **event["payload"],
                    }
                    yield _sse_line(event["event_id"], event["event_type"], payload)
            else:
                idle_cycles += 1

            status_value = repository.get_run_status(run_id)
            if status_value in {"completed", "failed"} and idle_cycles >= 2:
                if status_value == "failed":
                    error_message = repository.get_run_error(run_id)
                    current_event_id += 1
                    yield _sse_line(
                        current_event_id,
                        "run.failed",
                        {
                            "schema_version": SCHEMA_VERSION,
                            "run_id": run_id,
                            "error": error_message,
                        },
                    )
                break

            await asyncio.sleep(0.4)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/runs/{run_id}/result")
async def get_result(run_id: str) -> JSONResponse:
    status_value = repository.get_run_status(run_id)
    if status_value is None:
        raise HTTPException(status_code=404, detail="run_id not found")

    artifact = repository.get_run_result(run_id)
    if artifact is None:
        return JSONResponse(status_code=202, content={"schema_version": SCHEMA_VERSION, "run_id": run_id, "status": status_value})

    return JSONResponse(status_code=200, content=artifact)


@router.get("/runs/{run_id}/status")
async def get_status(run_id: str) -> JSONResponse:
    status_value = repository.get_run_status(run_id)
    if status_value is None:
        raise HTTPException(status_code=404, detail="run_id not found")

    return JSONResponse(
        {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "status": status_value,
            "error": repository.get_run_error(run_id),
        }
    )

