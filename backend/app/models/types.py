from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.models.schemas import (
    CoarseSummary,
    EvidenceChunk,
    PatientTwinInput,
    ProtocolCandidate,
    ProtocolResult,
    SafetyFlag,
)


@dataclass
class WorkflowState:
    run_id: str
    patient: PatientTwinInput
    evidence: list[EvidenceChunk] = field(default_factory=list)
    protocols: list[ProtocolCandidate] = field(default_factory=list)
    coarse: dict[str, CoarseSummary] = field(default_factory=dict)
    shortlist: list[str] = field(default_factory=list)
    trajectories: dict[str, Any] = field(default_factory=dict)
    flags: dict[str, list[SafetyFlag]] = field(default_factory=dict)
    results: list[ProtocolResult] = field(default_factory=list)

