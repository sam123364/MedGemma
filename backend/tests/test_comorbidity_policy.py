from __future__ import annotations

from app.models.schemas import PatientTwinInput, ProtocolCandidate
from app.safety.comorbidity_policy import assess_protocol_against_profile


def _patient(**overrides) -> PatientTwinInput:
    payload = {
        "age": 62,
        "sex": "male",
        "bmi": 32.0,
        "hba1c": 8.9,
        "fasting_glucose": 180.0,
        "systolic_bp": 148,
        "diastolic_bp": 92,
        "egfr": 48.0,
        "alt": 35.0,
        "comorbidities": ["hypertension", "chronic kidney disease"],
        "meds_current": ["metformin"],
    }
    payload.update(overrides)
    return PatientTwinInput(**payload)


def _protocol(protocol_id: str, meds: list[str]) -> ProtocolCandidate:
    return ProtocolCandidate(
        protocol_id=protocol_id,
        label=protocol_id,
        meds=meds,
        lifestyle_plan="Lifestyle",
        rationale="Rationale",
        citations=["https://example.com/1", "https://example.com/2"],
        citation_source_ids=["E-1", "E-2"],
    )


def test_heart_failure_blocks_tzd_protocol() -> None:
    patient = _patient(comorbidities=["heart failure", "hypertension"])
    protocol = _protocol("P-MET-TZD", ["metformin", "pioglitazone"])

    assessment = assess_protocol_against_profile(patient, protocol)

    assert any(flag.code == "HF_TZD_CONTRAINDICATION" and flag.disqualifying for flag in assessment.hard_flags)


def test_hypertension_ckd_profile_rewards_sglt2() -> None:
    patient = _patient()
    protocol = _protocol("P-MET-SGLT2", ["metformin", "empagliflozin"])

    assessment = assess_protocol_against_profile(patient, protocol)

    assert assessment.efficacy_bonus >= 0.08
    assert assessment.safety_penalty == 0.0


def test_ckd_profile_penalizes_missing_cardiorenal_agent() -> None:
    patient = _patient()
    protocol = _protocol("P-MET-DPP4", ["metformin", "sitagliptin"])

    assessment = assess_protocol_against_profile(patient, protocol)

    assert assessment.safety_penalty >= 0.08
    assert any("CKD profile" in reason for reason in assessment.rationale)


def test_current_dpp4_with_protocol_glp1_is_penalized() -> None:
    patient = _patient(meds_current=["metformin", "sitagliptin"])
    protocol = _protocol("P-MET-GLP1", ["metformin", "semaglutide"])

    assessment = assess_protocol_against_profile(patient, protocol)

    assert assessment.safety_penalty >= 0.08
    assert any(flag.code == "DPP4_GLP1_OVERLAP" for flag in assessment.soft_flags)
    assert any("DPP-4" in reason for reason in assessment.rationale)


def test_current_insulin_plus_protocol_su_adds_hypoglycemia_penalty() -> None:
    patient = _patient(meds_current=["insulin glargine"])
    protocol = _protocol("P-MET-SU", ["metformin", "glimepiride"])

    assessment = assess_protocol_against_profile(patient, protocol)

    assert assessment.safety_penalty >= 0.07
    assert assessment.adherence_penalty >= 0.03
    assert any(flag.code == "HYPOGLYCEMIA_STACK_RISK" for flag in assessment.soft_flags)


def test_current_medication_overlap_improves_adherence_fit() -> None:
    patient = _patient(meds_current=["metformin"])
    protocol = _protocol("P-MET-SGLT2", ["metformin", "empagliflozin"])

    assessment = assess_protocol_against_profile(patient, protocol)

    assert assessment.adherence_penalty < 0.0
    assert any("Medication continuity" in reason for reason in assessment.rationale)
