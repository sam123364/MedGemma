from __future__ import annotations

import math
from collections.abc import Callable

import numpy as np

from app.models.schemas import CoarseSummary, PatientTwinInput, ProtocolCandidate


def _protocol_coefficients(meds: list[str]) -> tuple[float, float]:
    efficacy = 0.8
    risk = 0.08
    med_set = {m.lower() for m in meds}

    if "metformin" in med_set:
        efficacy += 0.25
        risk -= 0.01
    if "semaglutide" in med_set:
        efficacy += 0.45
        risk += 0.02
    if "empagliflozin" in med_set or "dapagliflozin" in med_set:
        efficacy += 0.30
        risk += 0.015
    if "insulin glargine" in med_set:
        efficacy += 0.55
        risk += 0.09
    if "glimepiride" in med_set:
        efficacy += 0.25
        risk += 0.10
    if "pioglitazone" in med_set:
        efficacy += 0.18
        risk += 0.05

    return efficacy, max(0.02, risk)


def run_coarse_trials(
    patient: PatientTwinInput,
    protocols: list[ProtocolCandidate],
    total_trials: int,
    horizon_days: int,
    progress_callback: Callable[[dict], None] | None = None,
) -> dict[str, CoarseSummary]:
    if not protocols:
        return {}

    trials_per_protocol = max(40, math.floor(total_trials / len(protocols)))
    summaries: dict[str, CoarseSummary] = {}

    for idx, protocol in enumerate(protocols):
        efficacy_base, risk_base = _protocol_coefficients(protocol.meds)
        rng = np.random.default_rng(abs(hash(protocol.protocol_id)) % (2**32))

        hba1c_end = []
        glucose_end = []
        adverse_events = 0
        mortality_events = 0

        for _ in range(trials_per_protocol):
            hba1c = patient.hba1c
            glucose = patient.fasting_glucose
            adherence = np.clip(patient.adherence_probability + rng.normal(0, 0.12), 0.2, 1.0)
            trial_adverse = 0
            severe_streak = 0

            for day in range(1, horizon_days + 1):
                waning = max(0.7, 1.0 - day / (horizon_days * 1.8))
                daily_effect = efficacy_base * adherence * waning

                hba1c = max(5.3, hba1c - (daily_effect * 1.8 / horizon_days) + rng.normal(0, 0.01))
                glucose = max(60.0, glucose - (daily_effect * 120 / horizon_days) + rng.normal(0, 1.2))

                hypoglycemia_risk = 0.0
                if "insulin glargine" in protocol.meds or "glimepiride" in protocol.meds:
                    hypoglycemia_risk += max(0.0, (95 - glucose) / 500)

                event_risk = risk_base + hypoglycemia_risk + (1 - adherence) * 0.05
                if rng.random() < event_risk:
                    trial_adverse += 1

                if glucose < 65 or event_risk > 0.23:
                    severe_streak += 1
                else:
                    severe_streak = 0

                if severe_streak >= 5:
                    mortality_events += 1
                    break

            hba1c_end.append(float(hba1c))
            glucose_end.append(float(glucose))
            adverse_events += trial_adverse

        mean_hba1c_end = float(np.mean(hba1c_end))
        mean_glucose_end = float(np.mean(glucose_end))
        expected_hba1c_delta = float(patient.hba1c - mean_hba1c_end)
        expected_glucose_delta = float(patient.fasting_glucose - mean_glucose_end)

        hba1c_std = float(np.std(hba1c_end))
        robustness = float(np.clip(1.0 - (hba1c_std / 2.0), 0.0, 1.0))

        adverse_rate = float(adverse_events / max(1, trials_per_protocol * horizon_days))
        mortality_proxy_rate = float(mortality_events / max(1, trials_per_protocol))
        safety_risk = float(np.clip((adverse_rate * 5.0) + (mortality_proxy_rate * 2.0), 0.0, 1.0))

        summaries[protocol.protocol_id] = CoarseSummary(
            protocol_id=protocol.protocol_id,
            trials=trials_per_protocol,
            expected_hba1c_delta=round(expected_hba1c_delta, 3),
            expected_glucose_delta=round(expected_glucose_delta, 3),
            adverse_event_rate=round(adverse_rate, 5),
            robustness_index=round(robustness, 4),
            mortality_proxy_rate=round(mortality_proxy_rate, 5),
            safety_risk_index=round(safety_risk, 4),
        )

        if progress_callback:
            progress_callback(
                {
                    "completed_protocols": idx + 1,
                    "total_protocols": len(protocols),
                    "protocol_id": protocol.protocol_id,
                }
            )

    return summaries

