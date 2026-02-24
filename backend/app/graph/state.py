from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any, TypedDict

from pydantic import BaseModel


class TrialGraphState(TypedDict, total=False):
    run_id: str
    patient: dict[str, Any]
    target_count: int
    sim_horizon_days: int
    coarse_trials: int
    high_fidelity_count: int
    evidence: list[dict[str, Any]]
    protocols: list[dict[str, Any]]
    coarse: dict[str, dict[str, Any]]
    shortlist: list[str]
    trajectories: dict[str, list[dict[str, Any]]]
    calibrations: dict[str, dict[str, Any]]
    flags_by_protocol: dict[str, list[dict[str, Any]]]
    results: list[dict[str, Any]]
    recommendation: str
    population_map: dict[str, Any]
    error: str | None
    current_node: str | None
    completed_nodes: list[str]
    started_at: str
    updated_at: str


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _jsonify(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(k): _jsonify(v) for k, v in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_jsonify(item) for item in value]
    return value


def serialize_state(state: TrialGraphState) -> dict[str, Any]:
    return _jsonify(dict(state))

