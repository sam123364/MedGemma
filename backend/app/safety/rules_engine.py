from __future__ import annotations

from app.models.schemas import DailyState, PatientTwinInput, ProtocolCandidate, SafetyFlag
from app.safety.comorbidity_policy import assess_protocol_against_profile


def evaluate_safety(
    patient: PatientTwinInput,
    protocol: ProtocolCandidate,
    trajectory: list[DailyState],
) -> list[SafetyFlag]:
    flags: list[SafetyFlag] = []
    meds = {m.lower() for m in protocol.meds}

    profile_assessment = assess_protocol_against_profile(patient, protocol)
    flags.extend(profile_assessment.soft_flags)
    flags.extend(profile_assessment.hard_flags)

    if "metformin" in meds and patient.egfr < 30:
        flags.append(
            SafetyFlag(
                protocol_id=protocol.protocol_id,
                day=0,
                severity="critical",
                code="EGFR_METFORMIN_CONTRAINDICATION",
                message="Metformin contraindicated for baseline eGFR < 30.",
                disqualifying=True,
            )
        )

    if ("empagliflozin" in meds or "dapagliflozin" in meds) and patient.egfr < 20:
        flags.append(
            SafetyFlag(
                protocol_id=protocol.protocol_id,
                day=0,
                severity="high",
                code="LOW_EGFR_SGLT2_RISK",
                message="SGLT2 therapy has elevated risk at very low baseline eGFR.",
                disqualifying=True,
            )
        )

    if "pioglitazone" in meds and patient.alt > 120:
        flags.append(
            SafetyFlag(
                protocol_id=protocol.protocol_id,
                day=0,
                severity="high",
                code="ALT_TZD_RISK",
                message="Elevated baseline ALT increases concern for TZD protocol.",
                disqualifying=True,
            )
        )

    severe_count = 0
    for state in trajectory:
        if state.fasting_glucose_est < 65:
            flags.append(
                SafetyFlag(
                    protocol_id=protocol.protocol_id,
                    day=state.day,
                    severity="high",
                    code="HYPOGLYCEMIA",
                    message="Predicted fasting glucose under 65 mg/dL.",
                    disqualifying=False,
                )
            )
        if state.alt_est > 160:
            flags.append(
                SafetyFlag(
                    protocol_id=protocol.protocol_id,
                    day=state.day,
                    severity="medium",
                    code="LIVER_SIGNAL",
                    message="Predicted ALT crossing 160 U/L threshold.",
                    disqualifying=False,
                )
            )
        if state.severe_event:
            severe_count += 1

    if severe_count >= 8:
        flags.append(
            SafetyFlag(
                protocol_id=protocol.protocol_id,
                day=trajectory[-1].day if trajectory else 0,
                severity="critical",
                code="SEVERE_EVENT_BURDEN",
                message="Repeated severe event burden exceeds safety envelope.",
                disqualifying=True,
            )
        )

    return flags


def has_disqualifying_flag(flags: list[SafetyFlag]) -> bool:
    return any(flag.disqualifying for flag in flags)
