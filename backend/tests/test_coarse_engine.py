from app.models.schemas import PatientTwinInput, ProtocolCandidate
from app.sim.coarse_engine import run_coarse_trials


def test_coarse_engine_outputs_bounded_values() -> None:
    patient = PatientTwinInput(
        age=58,
        sex="female",
        bmi=33.1,
        hba1c=9.6,
        fasting_glucose=208,
        systolic_bp=138,
        diastolic_bp=86,
        egfr=74,
        alt=31,
    )
    protocols = [
        ProtocolCandidate(
            protocol_id="P1",
            label="Test Protocol",
            meds=["metformin", "semaglutide"],
            lifestyle_plan="Structured lifestyle",
            rationale="Test",
            citations=["https://a", "https://b"],
            citation_source_ids=["A", "B"],
        )
    ]

    summaries = run_coarse_trials(patient, protocols, total_trials=200, horizon_days=60)
    summary = summaries["P1"]

    assert -0.5 <= summary.expected_hba1c_delta <= 6.0
    assert -30 <= summary.expected_glucose_delta <= 250
    assert 0.0 <= summary.adverse_event_rate <= 1.0
    assert 0.0 <= summary.robustness_index <= 1.0
    assert 0.0 <= summary.safety_risk_index <= 1.0
