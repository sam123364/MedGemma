from app.models.schemas import DailyState, PatientTwinInput, ProtocolCandidate
from app.safety.rules_engine import evaluate_safety


def test_metformin_low_egfr_is_disqualifying() -> None:
    patient = PatientTwinInput(
        age=63,
        sex="male",
        bmi=30.0,
        hba1c=9.2,
        fasting_glucose=200,
        systolic_bp=132,
        diastolic_bp=82,
        egfr=24,
        alt=35,
    )
    protocol = ProtocolCandidate(
        protocol_id="P-MET",
        label="Metformin heavy",
        meds=["metformin", "empagliflozin"],
        lifestyle_plan="Plan",
        rationale="Plan",
        citations=["https://a", "https://b"],
        citation_source_ids=["A", "B"],
    )
    trajectory = [
        DailyState(
            day=1,
            hba1c_est=9.1,
            fasting_glucose_est=188,
            bmi_est=30,
            systolic_bp_est=130,
            diastolic_bp_est=80,
            egfr_est=23,
            alt_est=36,
            adherence_est=0.7,
            adverse_events=[],
        )
    ]

    flags = evaluate_safety(patient, protocol, trajectory)

    assert any(flag.code == "EGFR_METFORMIN_CONTRAINDICATION" for flag in flags)
    assert any(flag.disqualifying for flag in flags)
