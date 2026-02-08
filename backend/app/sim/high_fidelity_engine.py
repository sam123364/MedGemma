from __future__ import annotations

import json
from dataclasses import dataclass

import numpy as np

from app.models.schemas import CoarseSummary, DailyState, EvidenceChunk, PatientTwinInput, ProtocolCandidate
from app.services.medgemma import medgemma_client


@dataclass
class HighFidelityOutput:
    trajectory: list[DailyState]
    calibration: dict


def _default_calibration() -> dict:
    return {
        "efficacy_multiplier": 1.0,
        "safety_adjustment": 0.0,
        "adherence_adjustment": 0.0,
        "reasoning": "Baseline deterministic calibration.",
    }


async def _calibrate_protocol(
    patient: PatientTwinInput,
    protocol: ProtocolCandidate,
    coarse: CoarseSummary,
    evidence: list[EvidenceChunk],
) -> dict:
    prompt = (
        "You are MedGemma calibrating simulation coefficients for a Type 2 Diabetes digital twin. "
        "Return JSON only with keys: efficacy_multiplier, safety_adjustment, adherence_adjustment, reasoning."
        f"\nPatient:\n{patient.model_dump_json(indent=2)}"
        f"\nProtocol:\n{protocol.model_dump_json(indent=2)}"
        f"\nCoarse summary:\n{coarse.model_dump_json(indent=2)}"
        f"\nEvidence snippets:\n{json.dumps([e.model_dump() for e in evidence[:4]], indent=2)}"
    )
    payload, _response = await medgemma_client.complete_json(prompt)
    if not isinstance(payload, dict):
        return _default_calibration()

    try:
        return {
            "efficacy_multiplier": float(payload.get("efficacy_multiplier", 1.0)),
            "safety_adjustment": float(payload.get("safety_adjustment", 0.0)),
            "adherence_adjustment": float(payload.get("adherence_adjustment", 0.0)),
            "reasoning": str(payload.get("reasoning", "Model-provided calibration.")),
        }
    except Exception:
        return _default_calibration()


def _base_med_effect(protocol: ProtocolCandidate) -> tuple[float, float]:
    meds = {m.lower() for m in protocol.meds}
    efficacy = 0.95
    risk = 0.05
    if "metformin" in meds:
        efficacy += 0.18
    if "semaglutide" in meds:
        efficacy += 0.30
        risk += 0.02
    if "empagliflozin" in meds or "dapagliflozin" in meds:
        efficacy += 0.22
        risk += 0.015
    if "insulin glargine" in meds:
        efficacy += 0.35
        risk += 0.08
    if "glimepiride" in meds:
        efficacy += 0.16
        risk += 0.09
    if "pioglitazone" in meds:
        efficacy += 0.12
        risk += 0.045
    return efficacy, risk


async def simulate_high_fidelity(
    patient: PatientTwinInput,
    protocol: ProtocolCandidate,
    coarse: CoarseSummary,
    evidence: list[EvidenceChunk],
    horizon_days: int,
) -> HighFidelityOutput:
    calibration = await _calibrate_protocol(patient, protocol, coarse, evidence)
    efficacy_base, risk_base = _base_med_effect(protocol)

    efficacy = efficacy_base * calibration["efficacy_multiplier"]
    risk = max(0.01, risk_base + calibration["safety_adjustment"])
    adherence_bias = calibration["adherence_adjustment"]

    rng = np.random.default_rng(abs(hash(f"{patient.patient_id}-{protocol.protocol_id}")) % (2**32))

    hba1c = patient.hba1c
    glucose = patient.fasting_glucose
    bmi = patient.bmi
    sbp = float(patient.systolic_bp)
    dbp = float(patient.diastolic_bp)
    egfr = patient.egfr
    alt = patient.alt
    adherence = np.clip(patient.adherence_probability + adherence_bias, 0.2, 1.0)

    trajectory: list[DailyState] = []

    for day in range(1, horizon_days + 1):
        day_effect = efficacy * max(0.68, 1.0 - day / (horizon_days * 1.6))

        hba1c = max(5.2, hba1c - (day_effect * 1.7 / horizon_days) + rng.normal(0, 0.007))
        glucose = max(58.0, glucose - (day_effect * 115 / horizon_days) + rng.normal(0, 0.95))
        bmi = max(18.5, bmi - (day_effect * 0.9 / horizon_days) + rng.normal(0, 0.01))
        sbp = max(95.0, sbp - (day_effect * 5.5 / horizon_days) + rng.normal(0, 0.12))
        dbp = max(60.0, dbp - (day_effect * 3.2 / horizon_days) + rng.normal(0, 0.08))

        egfr = max(10.0, egfr + (0.03 if "empagliflozin" in protocol.meds or "dapagliflozin" in protocol.meds else 0.0) - risk * 0.02)
        alt = max(5.0, alt + risk * 0.08 + rng.normal(0, 0.03))

        adherence = float(np.clip(adherence + rng.normal(0, 0.004) - 0.0006, 0.15, 1.0))

        events: list[str] = []
        severe = False
        if glucose < 70:
            events.append("hypoglycemia_signal")
            severe = severe or glucose < 62
        if alt > 120:
            events.append("liver_stress_signal")
            severe = severe or alt > 160
        if risk > 0.20 and rng.random() < risk * 0.25:
            events.append("treatment_toxicity_signal")
            severe = severe or risk > 0.28

        trajectory.append(
            DailyState(
                day=day,
                hba1c_est=round(hba1c, 3),
                fasting_glucose_est=round(glucose, 3),
                bmi_est=round(bmi, 3),
                systolic_bp_est=round(sbp, 3),
                diastolic_bp_est=round(dbp, 3),
                egfr_est=round(egfr, 3),
                alt_est=round(alt, 3),
                adherence_est=round(adherence, 3),
                adverse_events=events,
                severe_event=severe,
                alive=True,
            )
        )

    return HighFidelityOutput(trajectory=trajectory, calibration=calibration)

