from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

from app.agents.critic import critic_agent
from app.agents.researcher import researcher_agent
from app.agents.simulator import simulator_agent
from app.db.sqlite import repository
from app.models.schemas import PatientTwinInput, RunArtifact
from app.rag.retriever import retriever
from app.safety.rules_engine import evaluate_safety
from app.services import settings


DISCLAIMER = (
    "Astra-Gemma is a research prototype for simulation and education. "
    "It does not provide medical advice, diagnosis, or treatment recommendations."
)


class TrialWorkflowService:
    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task] = {}

    def create_run_id(self) -> str:
        return f"run-{uuid4().hex[:12]}"

    def start_run(self, run_id: str, patient: PatientTwinInput, target_count: int = 10) -> None:
        task = asyncio.create_task(self._execute_run(run_id, patient, target_count))
        self._tasks[run_id] = task

    async def _execute_run(self, run_id: str, patient: PatientTwinInput, target_count: int) -> None:
        try:
            repository.update_run_status(run_id, "running")
            self._emit(run_id, "run.started", {"run_id": run_id, "status": "running"})

            repository.save_patient(run_id, patient.model_dump())

            evidence = retriever.retrieve(
                query=(
                    f"type 2 diabetes protocol design for patient age {patient.age}, "
                    f"HbA1c {patient.hba1c}, eGFR {patient.egfr}, objective: {patient.objective}"
                ),
                k=12,
            )
            repository.save_evidence(run_id, [item.model_dump() for item in evidence])

            protocols = await researcher_agent.generate_protocols(patient, evidence, target_count=target_count)
            repository.save_protocols(run_id, [protocol.model_dump() for protocol in protocols])
            self._emit(
                run_id,
                "protocols.generated",
                {
                    "count": len(protocols),
                    "protocols": [
                        {
                            "protocol_id": p.protocol_id,
                            "label": p.label,
                            "meds": p.meds,
                            "citations": p.citations,
                        }
                        for p in protocols
                    ],
                },
            )

            def coarse_progress(payload: dict) -> None:
                self._emit(run_id, "coarse.progress", payload)

            def high_progress(payload: dict) -> None:
                self._emit(run_id, "highfidelity.progress", payload)

            coarse, shortlist, trajectories, calibrations = await simulator_agent.run(
                patient=patient,
                protocols=protocols,
                evidence=evidence,
                total_trials=settings.COARSE_TRIALS,
                horizon_days=settings.SIM_HORIZON_DAYS,
                high_fidelity_count=settings.HIGH_FIDELITY_COUNT,
                coarse_progress_callback=coarse_progress,
                high_progress_callback=high_progress,
            )

            for protocol_id, summary in coarse.items():
                repository.save_coarse_result(run_id, protocol_id, summary.model_dump())

            self._emit(run_id, "shortlist.ready", {"protocol_ids": shortlist})

            flags_by_protocol = {}
            for protocol in protocols:
                trajectory = trajectories[protocol.protocol_id]
                repository.save_daily_states(
                    run_id,
                    protocol.protocol_id,
                    [state.model_dump() for state in trajectory],
                )
                flags = evaluate_safety(patient, protocol, trajectory)
                flags_by_protocol[protocol.protocol_id] = flags
                repository.save_safety_flags(run_id, [flag.model_dump() for flag in flags])

            results, recommendation = await critic_agent.evaluate(
                protocols=protocols,
                coarse_by_protocol=coarse,
                trajectories=trajectories,
                flags_by_protocol=flags_by_protocol,
            )

            for protocol_result in results:
                repository.save_score(
                    run_id,
                    protocol_result.protocol.protocol_id,
                    protocol_result.score.model_dump(),
                )
                citations = [
                    {
                        "source_id": source_id,
                        "source_url": source_url,
                    }
                    for source_id, source_url in zip(
                        protocol_result.protocol.citation_source_ids,
                        protocol_result.protocol.citations,
                        strict=False,
                    )
                ]
                repository.save_citations(run_id, protocol_result.protocol.protocol_id, citations)

            artifact = RunArtifact(
                run_id=run_id,
                created_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
                status="completed",
                patient=patient,
                evidence=evidence,
                results=results,
                final_recommendation=recommendation,
                disclaimer=DISCLAIMER,
            )

            serialized = artifact.model_dump(mode="json")
            serialized["calibrations"] = calibrations
            repository.save_run_result(run_id, serialized)

            repository.update_run_status(run_id, "completed")
            black_box_warnings = [
                {
                    "protocol_id": item.protocol.protocol_id,
                    "label": item.protocol.label,
                    "warning": item.black_box_warning,
                    "code": item.black_box_code,
                }
                for item in results
                if item.black_box_warning
            ]
            self._emit(
                run_id,
                "critic.done",
                {
                    "top_protocol_id": results[0].protocol.protocol_id if results else None,
                    "recommendation": recommendation,
                    "black_box_warnings": black_box_warnings,
                },
            )
            self._emit(
                run_id,
                "run.completed",
                {
                    "status": "completed",
                    "top_protocol_id": results[0].protocol.protocol_id if results else None,
                    "result_count": len(results),
                },
            )
        except Exception as exc:
            repository.update_run_status(run_id, "failed", error_message=str(exc))
            self._emit(run_id, "run.failed", {"status": "failed", "error": str(exc)})
            raise

    def _emit(self, run_id: str, event_type: str, payload: dict) -> None:
        repository.append_event(run_id, event_type, payload)


workflow_service = TrialWorkflowService()
