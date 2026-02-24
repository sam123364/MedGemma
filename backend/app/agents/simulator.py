from __future__ import annotations

from collections.abc import Callable

from app.models.schemas import CoarseSummary, DailyState, EvidenceChunk, PatientTwinInput, ProtocolCandidate
from app.sim.coarse_engine import run_coarse_trials
from app.sim.high_fidelity_engine import simulate_high_fidelity


class SimulatorAgent:
    async def run(
        self,
        patient: PatientTwinInput,
        protocols: list[ProtocolCandidate],
        evidence: list[EvidenceChunk],
        total_trials: int,
        horizon_days: int,
        high_fidelity_count: int,
        coarse_progress_callback: Callable[[dict], None] | None = None,
        high_progress_callback: Callable[[dict], None] | None = None,
        shortlist_callback: Callable[[list[str]], None] | None = None,
    ) -> tuple[dict[str, CoarseSummary], list[str], dict[str, list[DailyState]], dict[str, dict]]:
        coarse = run_coarse_trials(
            patient=patient,
            protocols=protocols,
            total_trials=total_trials,
            horizon_days=horizon_days,
            progress_callback=coarse_progress_callback,
        )

        ranked = sorted(
            protocols,
            key=lambda protocol: (
                coarse[protocol.protocol_id].expected_hba1c_delta * 0.6
                + coarse[protocol.protocol_id].expected_glucose_delta * 0.2
                + coarse[protocol.protocol_id].robustness_index * 0.2
                - coarse[protocol.protocol_id].safety_risk_index * 0.5
            ),
            reverse=True,
        )

        shortlist = [item.protocol_id for item in ranked[:high_fidelity_count]]
        if shortlist_callback:
            shortlist_callback(shortlist)

        trajectories: dict[str, list[DailyState]] = {}
        calibrations: dict[str, dict] = {}

        for index, protocol_id in enumerate(shortlist):
            protocol = next(item for item in protocols if item.protocol_id == protocol_id)
            result = await simulate_high_fidelity(
                patient=patient,
                protocol=protocol,
                coarse=coarse[protocol_id],
                evidence=evidence,
                horizon_days=horizon_days,
            )
            trajectories[protocol_id] = result.trajectory
            calibrations[protocol_id] = result.calibration
            if high_progress_callback:
                high_progress_callback(
                    {
                        "completed": index + 1,
                        "total": len(shortlist),
                        "protocol_id": protocol_id,
                    }
                )

        # Keep non-shortlisted protocols with a lightweight pseudo-trajectory for comparability in UI.
        for protocol in protocols:
            if protocol.protocol_id in trajectories:
                continue
            base = coarse[protocol.protocol_id]
            day_states: list[DailyState] = []
            hba1c = max(5.5, patient.hba1c - base.expected_hba1c_delta)
            glucose = max(60.0, patient.fasting_glucose - base.expected_glucose_delta)
            for day in range(1, horizon_days + 1):
                fade = day / horizon_days
                day_states.append(
                    DailyState(
                        day=day,
                        hba1c_est=round(patient.hba1c - (patient.hba1c - hba1c) * fade, 3),
                        fasting_glucose_est=round(patient.fasting_glucose - (patient.fasting_glucose - glucose) * fade, 3),
                        bmi_est=patient.bmi,
                        systolic_bp_est=patient.systolic_bp,
                        diastolic_bp_est=patient.diastolic_bp,
                        egfr_est=patient.egfr,
                        alt_est=patient.alt,
                        adherence_est=patient.adherence_probability,
                        adverse_events=[],
                        severe_event=False,
                        alive=True,
                    )
                )
            trajectories[protocol.protocol_id] = day_states
            calibrations[protocol.protocol_id] = {
                "reasoning": "Coarse-mode extrapolated trajectory",
                "efficacy_multiplier": 1.0,
                "safety_adjustment": 0.0,
                "adherence_adjustment": 0.0,
            }

        return coarse, shortlist, trajectories, calibrations


simulator_agent = SimulatorAgent()
