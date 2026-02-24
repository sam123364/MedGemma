from __future__ import annotations

from app.models.schemas import PatientTwinInput, ProtocolCandidate
from app.services.population_map import generate_population_map


def _protocol(protocol_id: str, label: str, meds: list[str]) -> ProtocolCandidate:
    return ProtocolCandidate(
        protocol_id=protocol_id,
        label=label,
        meds=meds,
        lifestyle_plan="Lifestyle",
        rationale="Reason",
        citations=["https://example.com/1", "https://example.com/2"],
        citation_source_ids=["E-1", "E-2"],
    )


def test_population_map_respects_forced_disqualifications() -> None:
    patient = PatientTwinInput(
        age=52,
        sex="male",
        bmi=31.0,
        hba1c=9.2,
        fasting_glucose=210.0,
        systolic_bp=142,
        diastolic_bp=88,
        egfr=70.0,
        alt=32.0,
        comorbidities=["hypertension"],
        meds_current=["metformin"],
    )
    protocols = [
        _protocol("P-FORCED-BLOCK", "Forced Block Protocol", ["metformin", "semaglutide", "dapagliflozin"]),
        _protocol("P-ALLOWED", "Allowed Protocol", ["metformin", "empagliflozin"]),
    ]

    artifact = generate_population_map(
        run_id="run-test",
        patient=patient,
        protocols=protocols,
        horizon_days=30,
        force_disqualified_protocol_ids={"P-FORCED-BLOCK"},
    )

    assert len(artifact.cells) == 27
    assert all(cell.top_protocol_id != "P-FORCED-BLOCK" for cell in artifact.cells)

