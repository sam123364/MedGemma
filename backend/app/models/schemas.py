from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, conlist


SCHEMA_VERSION = "1.0.0"


class SchemaVersioned(BaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)


class EvidenceChunk(SchemaVersioned):
    source_id: str
    title: str
    summary: str
    year: int | None = None
    source_url: str
    condition: str = "type-2-diabetes"
    intervention: str | None = None
    outcome: str | None = None
    risk: str | None = None


class PatientTwinInput(SchemaVersioned):
    patient_id: str = Field(default="synthetic-patient")
    age: int = Field(ge=18, le=100)
    sex: Literal["female", "male", "other"] = "other"
    bmi: float = Field(ge=10.0, le=90.0)
    hba1c: float = Field(ge=4.0, le=20.0)
    fasting_glucose: float = Field(ge=40.0, le=500.0)
    systolic_bp: int = Field(ge=70, le=250)
    diastolic_bp: int = Field(ge=40, le=180)
    egfr: float = Field(ge=0.0, le=180.0)
    alt: float = Field(ge=0.0, le=2000.0)
    adherence_probability: float = Field(ge=0.0, le=1.0, default=0.72)
    comorbidities: list[str] = Field(default_factory=list)
    meds_current: list[str] = Field(default_factory=list)
    objective: str = Field(default="maximize glycemic control while minimizing risk")


class ProtocolCandidate(SchemaVersioned):
    protocol_id: str
    label: str
    meds: conlist(str, min_length=1)
    lifestyle_plan: str
    rationale: str
    citations: conlist(str, min_length=2)
    citation_source_ids: conlist(str, min_length=2)


class CoarseSummary(SchemaVersioned):
    protocol_id: str
    trials: int
    expected_hba1c_delta: float
    expected_glucose_delta: float
    adverse_event_rate: float
    robustness_index: float
    mortality_proxy_rate: float
    safety_risk_index: float


class DailyState(SchemaVersioned):
    day: int
    hba1c_est: float
    fasting_glucose_est: float
    bmi_est: float
    systolic_bp_est: float
    diastolic_bp_est: float
    egfr_est: float
    alt_est: float
    adherence_est: float
    adverse_events: list[str] = Field(default_factory=list)
    severe_event: bool = False
    alive: bool = True


class SafetyFlag(SchemaVersioned):
    protocol_id: str
    day: int
    severity: Literal["low", "medium", "high", "critical"]
    code: str
    message: str
    disqualifying: bool = False


class ProtocolScore(SchemaVersioned):
    protocol_id: str
    efficacy_score: float
    safety_score: float
    adherence_score: float
    robustness_score: float
    total_score: float
    disqualified: bool = False


class ProtocolResult(SchemaVersioned):
    protocol: ProtocolCandidate
    coarse_summary: CoarseSummary
    trajectory: list[DailyState]
    flags: list[SafetyFlag]
    score: ProtocolScore
    explanation: str
    guideline_reasons: list[str] = Field(default_factory=list)
    black_box_warning: str | None = None
    black_box_code: str | None = None


class PopulationMapCell(SchemaVersioned):
    cell_id: str
    age: int
    egfr: float
    hba1c: float
    top_protocol_id: str
    top_protocol_label: str
    top_score: float
    runner_up_protocol_id: str | None = None
    runner_up_score: float | None = None
    confidence_margin: float
    disqualified_count: int = 0


class PopulationMapArtifact(SchemaVersioned):
    run_id: str
    axes: dict[str, list[float]]
    cells: list[PopulationMapCell]
    generated_at: datetime


class RunArtifact(SchemaVersioned):
    run_id: str
    created_at: datetime
    completed_at: datetime | None = None
    status: Literal["queued", "running", "completed", "failed"]
    patient: PatientTwinInput
    evidence: list[EvidenceChunk]
    results: list[ProtocolResult]
    final_recommendation: str
    disclaimer: str
    population_map: PopulationMapArtifact | None = None


class RunStartResponse(SchemaVersioned):
    run_id: str
    status: Literal["queued", "running"]


class EventEnvelope(SchemaVersioned):
    event_id: int
    run_id: str
    event_type: str
    timestamp: datetime
    payload: dict[str, Any]


class RunCheckpoint(SchemaVersioned):
    id: int
    run_id: str
    node_name: str
    state_json: dict[str, Any]
    status: str
    created_at: datetime


class ChatExplainRequest(SchemaVersioned):
    run_id: str
    question: str = Field(min_length=3, max_length=1000)


class ChatExplainResponse(SchemaVersioned):
    run_id: str
    answer: str
    grounded_source_ids: list[str]
