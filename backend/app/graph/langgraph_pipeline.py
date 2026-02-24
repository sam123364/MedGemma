from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agents.critic import critic_agent
from app.agents.researcher import researcher_agent
from app.agents.simulator import simulator_agent
from app.db.sqlite import repository
from app.graph.state import TrialGraphState, now_iso, serialize_state
from app.models.schemas import CoarseSummary, DailyState, EvidenceChunk, PatientTwinInput, ProtocolCandidate, RunArtifact, SafetyFlag
from app.rag.retriever import retriever
from app.safety.rules_engine import evaluate_safety
from app.services import settings
from app.services.population_map import generate_population_map


DISCLAIMER = (
    "Astra-Gemma is a research prototype for simulation and education. "
    "It does not provide medical advice, diagnosis, or treatment recommendations."
)


class LangGraphTrialEngine:
    def __init__(self) -> None:
        self._graph = self._build_graph()

    @staticmethod
    def _emit(run_id: str, event_type: str, payload: dict[str, Any]) -> None:
        repository.append_event(run_id, event_type, payload)

    @staticmethod
    def _route(state: TrialGraphState) -> str:
        return "error" if state.get("error") else "ok"

    @staticmethod
    def _with_defaults(state: TrialGraphState) -> TrialGraphState:
        state.setdefault("error", None)
        state.setdefault("current_node", None)
        state.setdefault("completed_nodes", [])
        state.setdefault("evidence", [])
        state.setdefault("protocols", [])
        state.setdefault("coarse", {})
        state.setdefault("shortlist", [])
        state.setdefault("trajectories", {})
        state.setdefault("calibrations", {})
        state.setdefault("flags_by_protocol", {})
        state.setdefault("results", [])
        state.setdefault("recommendation", "")
        state.setdefault("population_map", {})
        state.setdefault("started_at", now_iso())
        state["updated_at"] = now_iso()
        return state

    def _mark_completed(self, state: TrialGraphState, node_name: str) -> TrialGraphState:
        completed = list(state.get("completed_nodes", []))
        if node_name not in completed:
            completed.append(node_name)
        state["completed_nodes"] = completed
        state["current_node"] = node_name
        state["updated_at"] = now_iso()
        repository.save_checkpoint(
            run_id=state["run_id"],
            node_name=node_name,
            state_json=serialize_state(state),
            status="saved",
        )
        if settings.ASTRA_FAIL_AFTER_NODE == node_name:
            raise RuntimeError(f"Fault injection after node '{node_name}'")
        return state

    async def _run_node(self, state: TrialGraphState, node_name: str, fn: Any) -> TrialGraphState:
        state = self._with_defaults(state)
        if node_name in state.get("completed_nodes", []):
            state["current_node"] = node_name
            state["updated_at"] = now_iso()
            return state
        try:
            next_state = await fn(state)
            return self._mark_completed(next_state, node_name)
        except Exception as exc:  # pragma: no cover - error routing verified at integration level
            state["current_node"] = node_name
            state["updated_at"] = now_iso()
            state["error"] = str(exc).strip() or exc.__class__.__name__
            return state

    @staticmethod
    def _patient(state: TrialGraphState) -> PatientTwinInput:
        return PatientTwinInput(**state["patient"])

    @staticmethod
    def _evidence(state: TrialGraphState) -> list[EvidenceChunk]:
        return [EvidenceChunk(**item) for item in state.get("evidence", [])]

    @staticmethod
    def _protocols(state: TrialGraphState) -> list[ProtocolCandidate]:
        return [ProtocolCandidate(**item) for item in state.get("protocols", [])]

    @staticmethod
    def _coarse(state: TrialGraphState) -> dict[str, CoarseSummary]:
        return {protocol_id: CoarseSummary(**summary) for protocol_id, summary in state.get("coarse", {}).items()}

    @staticmethod
    def _trajectories(state: TrialGraphState) -> dict[str, list[DailyState]]:
        output: dict[str, list[DailyState]] = {}
        for protocol_id, items in state.get("trajectories", {}).items():
            output[protocol_id] = [DailyState(**day) for day in items]
        return output

    @staticmethod
    def _flags_by_protocol(state: TrialGraphState) -> dict[str, list[SafetyFlag]]:
        output: dict[str, list[SafetyFlag]] = {}
        for protocol_id, items in state.get("flags_by_protocol", {}).items():
            output[protocol_id] = [SafetyFlag(**flag) for flag in items]
        return output

    async def _init_run(self, state: TrialGraphState) -> TrialGraphState:
        repository.update_run_status(state["run_id"], "running")
        self._emit(state["run_id"], "run.started", {"run_id": state["run_id"], "status": "running"})
        repository.save_patient(state["run_id"], state["patient"])
        return state

    async def _retrieve_evidence(self, state: TrialGraphState) -> TrialGraphState:
        patient = self._patient(state)
        evidence = retriever.retrieve(
            query=(
                f"type 2 diabetes protocol design for patient age {patient.age}, "
                f"HbA1c {patient.hba1c}, eGFR {patient.egfr}, objective: {patient.objective}, "
                f"comorbidities: {', '.join(patient.comorbidities) if patient.comorbidities else 'none'}"
            ),
            k=12,
            filters={
                "condition": "type-2-diabetes",
                "min_year": 2010,
            },
        )
        serialized = [item.model_dump(mode="json") for item in evidence]
        repository.save_evidence(state["run_id"], serialized)
        state["evidence"] = serialized
        return state

    async def _generate_protocols(self, state: TrialGraphState) -> TrialGraphState:
        patient = self._patient(state)
        evidence = self._evidence(state)
        protocols = await researcher_agent.generate_protocols(
            patient,
            evidence,
            target_count=state.get("target_count", 10),
        )
        serialized = [item.model_dump(mode="json") for item in protocols]
        repository.save_protocols(state["run_id"], serialized)
        self._emit(
            state["run_id"],
            "protocols.generated",
            {
                "count": len(protocols),
                "protocols": [
                    {
                        "protocol_id": item.protocol_id,
                        "label": item.label,
                        "meds": item.meds,
                        "citations": item.citations,
                    }
                    for item in protocols
                ],
            },
        )
        state["protocols"] = serialized
        return state

    async def _run_simulation(self, state: TrialGraphState) -> TrialGraphState:
        patient = self._patient(state)
        protocols = self._protocols(state)
        evidence = self._evidence(state)

        def coarse_progress(payload: dict[str, Any]) -> None:
            self._emit(state["run_id"], "coarse.progress", payload)

        def high_progress(payload: dict[str, Any]) -> None:
            self._emit(state["run_id"], "highfidelity.progress", payload)

        def shortlist_callback(protocol_ids: list[str]) -> None:
            self._emit(state["run_id"], "shortlist.ready", {"protocol_ids": protocol_ids})

        coarse, shortlist, trajectories, calibrations = await simulator_agent.run(
            patient=patient,
            protocols=protocols,
            evidence=evidence,
            total_trials=state.get("coarse_trials", settings.COARSE_TRIALS),
            horizon_days=state.get("sim_horizon_days", settings.SIM_HORIZON_DAYS),
            high_fidelity_count=state.get("high_fidelity_count", settings.HIGH_FIDELITY_COUNT),
            coarse_progress_callback=coarse_progress,
            high_progress_callback=high_progress,
            shortlist_callback=shortlist_callback,
        )

        coarse_serialized = {protocol_id: summary.model_dump(mode="json") for protocol_id, summary in coarse.items()}
        for protocol_id, summary in coarse_serialized.items():
            repository.save_coarse_result(state["run_id"], protocol_id, summary)

        state["coarse"] = coarse_serialized
        state["shortlist"] = shortlist
        state["trajectories"] = {
            protocol_id: [day.model_dump(mode="json") for day in items]
            for protocol_id, items in trajectories.items()
        }
        state["calibrations"] = calibrations
        return state

    async def _evaluate_safety(self, state: TrialGraphState) -> TrialGraphState:
        patient = self._patient(state)
        protocols = self._protocols(state)
        trajectories = self._trajectories(state)

        flags_by_protocol: dict[str, list[dict[str, Any]]] = {}
        for protocol in protocols:
            trajectory = trajectories[protocol.protocol_id]
            repository.save_daily_states(
                state["run_id"],
                protocol.protocol_id,
                [item.model_dump(mode="json") for item in trajectory],
            )
            flags = evaluate_safety(patient, protocol, trajectory)
            serialized_flags = [item.model_dump(mode="json") for item in flags]
            repository.save_safety_flags(state["run_id"], serialized_flags)
            flags_by_protocol[protocol.protocol_id] = serialized_flags

        state["flags_by_protocol"] = flags_by_protocol
        return state

    async def _score_and_rank(self, state: TrialGraphState) -> TrialGraphState:
        patient = self._patient(state)
        protocols = self._protocols(state)
        coarse = self._coarse(state)
        trajectories = self._trajectories(state)
        flags_by_protocol = self._flags_by_protocol(state)

        results, recommendation = await critic_agent.evaluate(
            patient=patient,
            protocols=protocols,
            coarse_by_protocol=coarse,
            trajectories=trajectories,
            flags_by_protocol=flags_by_protocol,
        )

        serialized_results = [item.model_dump(mode="json") for item in results]
        for result in results:
            protocol_id = result.protocol.protocol_id
            repository.save_score(
                state["run_id"],
                protocol_id,
                result.score.model_dump(mode="json"),
            )
            citations = [
                {
                    "source_id": source_id,
                    "source_url": source_url,
                }
                for source_id, source_url in zip(
                    result.protocol.citation_source_ids,
                    result.protocol.citations,
                    strict=False,
                )
            ]
            repository.save_citations(state["run_id"], protocol_id, citations)

        black_box_warnings = [
            {
                "protocol_id": item["protocol"]["protocol_id"],
                "label": item["protocol"]["label"],
                "warning": item.get("black_box_warning"),
                "code": item.get("black_box_code"),
            }
            for item in serialized_results
            if item.get("black_box_warning")
        ]

        self._emit(
            state["run_id"],
            "critic.done",
            {
                "top_protocol_id": serialized_results[0]["protocol"]["protocol_id"] if serialized_results else None,
                "recommendation": recommendation,
                "black_box_warnings": black_box_warnings,
            },
        )
        state["results"] = serialized_results
        state["recommendation"] = recommendation
        return state

    async def _persist_artifact(self, state: TrialGraphState) -> TrialGraphState:
        patient = self._patient(state)
        evidence = self._evidence(state)
        protocols = self._protocols(state)
        artifact = RunArtifact(
            run_id=state["run_id"],
            created_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            status="completed",
            patient=patient,
            evidence=evidence,
            results=state.get("results", []),  # type: ignore[arg-type]
            final_recommendation=state.get("recommendation", ""),
            disclaimer=DISCLAIMER,
        )
        force_disqualified_protocol_ids = {
            item["protocol"]["protocol_id"]
            for item in state.get("results", [])
            if item.get("score", {}).get("disqualified")
        }
        population_map = generate_population_map(
            run_id=state["run_id"],
            patient=patient,
            protocols=protocols,
            horizon_days=state.get("sim_horizon_days", settings.SIM_HORIZON_DAYS),
            force_disqualified_protocol_ids=force_disqualified_protocol_ids,
        )
        self._emit(
            state["run_id"],
            "population_map.ready",
            {
                "cells": len(population_map.cells),
                "run_id": state["run_id"],
            },
        )

        serialized = artifact.model_dump(mode="json")
        serialized["calibrations"] = state.get("calibrations", {})
        serialized["population_map"] = population_map.model_dump(mode="json")
        repository.save_run_result(state["run_id"], serialized)
        state["population_map"] = population_map.model_dump(mode="json")
        return state

    async def _finalize_run(self, state: TrialGraphState) -> TrialGraphState:
        repository.update_run_status(state["run_id"], "completed")
        top_protocol = None
        if state.get("results"):
            top_protocol = state["results"][0]["protocol"]["protocol_id"]
        self._emit(
            state["run_id"],
            "run.completed",
            {
                "status": "completed",
                "top_protocol_id": top_protocol,
                "result_count": len(state.get("results", [])),
            },
        )
        return state

    async def _fail_run(self, state: TrialGraphState) -> TrialGraphState:
        error_message = state.get("error") or "Unknown workflow failure"
        repository.update_run_status(state["run_id"], "failed", error_message=error_message)
        self._emit(
            state["run_id"],
            "run.failed",
            {
                "status": "failed",
                "error": error_message,
            },
        )
        return state

    async def _node_init_run(self, state: TrialGraphState) -> TrialGraphState:
        return await self._run_node(state, "init_run", self._init_run)

    async def _node_retrieve_evidence(self, state: TrialGraphState) -> TrialGraphState:
        return await self._run_node(state, "retrieve_evidence", self._retrieve_evidence)

    async def _node_generate_protocols(self, state: TrialGraphState) -> TrialGraphState:
        return await self._run_node(state, "generate_protocols", self._generate_protocols)

    async def _node_run_simulation(self, state: TrialGraphState) -> TrialGraphState:
        return await self._run_node(state, "run_simulation", self._run_simulation)

    async def _node_evaluate_safety(self, state: TrialGraphState) -> TrialGraphState:
        return await self._run_node(state, "evaluate_safety", self._evaluate_safety)

    async def _node_score_and_rank(self, state: TrialGraphState) -> TrialGraphState:
        return await self._run_node(state, "score_and_rank", self._score_and_rank)

    async def _node_persist_artifact(self, state: TrialGraphState) -> TrialGraphState:
        return await self._run_node(state, "persist_artifact", self._persist_artifact)

    async def _node_finalize_run(self, state: TrialGraphState) -> TrialGraphState:
        return await self._run_node(state, "finalize_run", self._finalize_run)

    async def _node_fail_run(self, state: TrialGraphState) -> TrialGraphState:
        return await self._fail_run(state)

    def _build_graph(self) -> Any:
        graph = StateGraph(TrialGraphState)
        graph.add_node("init_run", self._node_init_run)
        graph.add_node("retrieve_evidence", self._node_retrieve_evidence)
        graph.add_node("generate_protocols", self._node_generate_protocols)
        graph.add_node("run_simulation", self._node_run_simulation)
        graph.add_node("evaluate_safety", self._node_evaluate_safety)
        graph.add_node("score_and_rank", self._node_score_and_rank)
        graph.add_node("persist_artifact", self._node_persist_artifact)
        graph.add_node("finalize_run", self._node_finalize_run)
        graph.add_node("fail_run", self._node_fail_run)

        graph.add_edge(START, "init_run")
        graph.add_conditional_edges("init_run", self._route, {"ok": "retrieve_evidence", "error": "fail_run"})
        graph.add_conditional_edges("retrieve_evidence", self._route, {"ok": "generate_protocols", "error": "fail_run"})
        graph.add_conditional_edges("generate_protocols", self._route, {"ok": "run_simulation", "error": "fail_run"})
        graph.add_conditional_edges("run_simulation", self._route, {"ok": "evaluate_safety", "error": "fail_run"})
        graph.add_conditional_edges("evaluate_safety", self._route, {"ok": "score_and_rank", "error": "fail_run"})
        graph.add_conditional_edges("score_and_rank", self._route, {"ok": "persist_artifact", "error": "fail_run"})
        graph.add_conditional_edges("persist_artifact", self._route, {"ok": "finalize_run", "error": "fail_run"})
        graph.add_conditional_edges("finalize_run", self._route, {"ok": END, "error": "fail_run"})
        graph.add_edge("fail_run", END)
        return graph.compile()

    async def run(self, state: TrialGraphState) -> TrialGraphState:
        prepared = self._with_defaults(state)
        return await self._graph.ainvoke(prepared)
