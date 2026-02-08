import pytest

from app.agents.critic import critic_agent
from app.models.schemas import CoarseSummary, DailyState, ProtocolCandidate, SafetyFlag


@pytest.mark.asyncio
async def test_critic_emits_black_box_warning_for_disqualified_protocol() -> None:
    protocol = ProtocolCandidate(
        protocol_id="P-MET-TEST",
        label="Metformin protocol",
        meds=["metformin"],
        lifestyle_plan="Plan",
        rationale="Reason",
        citations=["https://a", "https://b"],
        citation_source_ids=["A", "B"],
    )
    coarse = CoarseSummary(
        protocol_id=protocol.protocol_id,
        trials=100,
        expected_hba1c_delta=1.1,
        expected_glucose_delta=22.0,
        adverse_event_rate=0.01,
        robustness_index=0.8,
        mortality_proxy_rate=0.0,
        safety_risk_index=0.1,
    )
    trajectory = [
        DailyState(
            day=1,
            hba1c_est=9.0,
            fasting_glucose_est=180,
            bmi_est=30,
            systolic_bp_est=130,
            diastolic_bp_est=80,
            egfr_est=20,
            alt_est=30,
            adherence_est=0.7,
            adverse_events=[],
            severe_event=False,
            alive=True,
        ),
        DailyState(
            day=2,
            hba1c_est=8.9,
            fasting_glucose_est=176,
            bmi_est=30,
            systolic_bp_est=129,
            diastolic_bp_est=79,
            egfr_est=19,
            alt_est=32,
            adherence_est=0.7,
            adverse_events=[],
            severe_event=False,
            alive=True,
        ),
    ]
    flags = [
        SafetyFlag(
            protocol_id=protocol.protocol_id,
            day=0,
            severity="critical",
            code="EGFR_METFORMIN_CONTRAINDICATION",
            message="Metformin contraindicated for baseline eGFR < 30.",
            disqualifying=True,
        )
    ]

    results, _ = await critic_agent.evaluate(
        protocols=[protocol],
        coarse_by_protocol={protocol.protocol_id: coarse},
        trajectories={protocol.protocol_id: trajectory},
        flags_by_protocol={protocol.protocol_id: flags},
    )

    assert len(results) == 1
    assert results[0].score.disqualified is True
    assert results[0].black_box_code == "EGFR_METFORMIN_CONTRAINDICATION"
    assert results[0].black_box_warning is not None
    assert "PROTOCOL REJECTED" in results[0].black_box_warning
    assert "Metformin + Kidney Failure" in results[0].black_box_warning
