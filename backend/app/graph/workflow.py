from __future__ import annotations

import asyncio
from typing import Any
from uuid import uuid4

from app.db.sqlite import repository
from app.graph.langgraph_pipeline import LangGraphTrialEngine
from app.graph.state import TrialGraphState, now_iso
from app.models.schemas import PatientTwinInput
from app.services import settings


class TrialWorkflowService:
    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task] = {}
        self._engine = LangGraphTrialEngine()

    def create_run_id(self) -> str:
        return f"run-{uuid4().hex[:12]}"

    @staticmethod
    def _base_state(
        run_id: str,
        patient: PatientTwinInput,
        target_count: int,
        sim_horizon_days: int,
        coarse_trials: int,
        high_fidelity_count: int,
    ) -> TrialGraphState:
        ts = now_iso()
        return {
            "run_id": run_id,
            "patient": patient.model_dump(mode="json"),
            "target_count": target_count,
            "sim_horizon_days": sim_horizon_days,
            "coarse_trials": coarse_trials,
            "high_fidelity_count": high_fidelity_count,
            "error": None,
            "current_node": None,
            "completed_nodes": [],
            "started_at": ts,
            "updated_at": ts,
        }

    def start_run(
        self,
        run_id: str,
        patient: PatientTwinInput,
        target_count: int = 10,
        sim_horizon_days: int | None = None,
        coarse_trials: int | None = None,
        high_fidelity_count: int | None = None,
    ) -> None:
        state = self._base_state(
            run_id=run_id,
            patient=patient,
            target_count=target_count,
            sim_horizon_days=sim_horizon_days or settings.SIM_HORIZON_DAYS,
            coarse_trials=coarse_trials or settings.COARSE_TRIALS,
            high_fidelity_count=high_fidelity_count or settings.HIGH_FIDELITY_COUNT,
        )
        self._launch_state(run_id, state)

    def _launch_state(self, run_id: str, state: TrialGraphState) -> None:
        existing = self._tasks.get(run_id)
        if existing is not None:
            if not existing.done():
                existing.cancel()
            self._tasks.pop(run_id, None)
        task = asyncio.create_task(self._execute(run_id, state))
        self._tasks[run_id] = task

    async def _execute(self, run_id: str, state: TrialGraphState) -> None:
        try:
            await self._engine.run(state)
        finally:
            self._tasks.pop(run_id, None)

    def resume_run(self, run_id: str) -> TrialGraphState:
        checkpoint = repository.get_latest_checkpoint(run_id)
        if checkpoint is None:
            patient_payload = repository.get_patient(run_id)
            if patient_payload is None:
                raise ValueError("No checkpoint or patient payload found for run")
            patient = PatientTwinInput(**patient_payload)
            state = self._base_state(
                run_id=run_id,
                patient=patient,
                target_count=10,
                sim_horizon_days=settings.SIM_HORIZON_DAYS,
                coarse_trials=settings.COARSE_TRIALS,
                high_fidelity_count=settings.HIGH_FIDELITY_COUNT,
            )
            repository.update_run_status(run_id, "running", error_message=None)
            repository.append_event(
                run_id,
                "run.resumed",
                {
                    "run_id": run_id,
                    "from_node": "none",
                    "status": "running",
                },
            )
            self._launch_state(run_id, state)
            return state

        state = checkpoint["state_json"]
        if not isinstance(state, dict):
            raise ValueError("Checkpoint state malformed")

        state = dict(state)
        state["error"] = None
        state["updated_at"] = now_iso()
        repository.update_run_status(run_id, "running", error_message=None)
        repository.mark_checkpoint_resumed(checkpoint["id"])
        repository.append_event(
            run_id,
            "run.resumed",
            {
                "run_id": run_id,
                "from_node": checkpoint["node_name"],
                "status": "running",
            },
        )
        self._launch_state(run_id, state)  # type: ignore[arg-type]
        return state  # type: ignore[return-value]

    def auto_resume_incomplete_runs(self) -> list[str]:
        resumed: list[str] = []
        for run_id in repository.get_incomplete_runs():
            if run_id in self._tasks and not self._tasks[run_id].done():
                continue
            try:
                self.resume_run(run_id)
                resumed.append(run_id)
            except Exception:
                continue
        return resumed

    def run_is_active(self, run_id: str) -> bool:
        task = self._tasks.get(run_id)
        return bool(task and not task.done())


workflow_service = TrialWorkflowService()
