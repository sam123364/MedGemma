import pytest

from app.agents.researcher import researcher_agent
from app.models.schemas import EvidenceChunk, PatientTwinInput


@pytest.mark.asyncio
async def test_researcher_protocols_have_citations() -> None:
    patient = PatientTwinInput(
        age=45,
        sex="female",
        bmi=29,
        hba1c=8.7,
        fasting_glucose=180,
        systolic_bp=128,
        diastolic_bp=78,
        egfr=88,
        alt=22,
    )
    evidence = [
        EvidenceChunk(
            source_id="E1",
            title="Evidence 1",
            summary="Summary 1",
            source_url="https://e1",
        ),
        EvidenceChunk(
            source_id="E2",
            title="Evidence 2",
            summary="Summary 2",
            source_url="https://e2",
        ),
        EvidenceChunk(
            source_id="E3",
            title="Evidence 3",
            summary="Summary 3",
            source_url="https://e3",
        ),
    ]

    protocols = await researcher_agent.generate_protocols(patient, evidence, target_count=8)

    assert len(protocols) >= 8
    for protocol in protocols:
        assert len(protocol.citations) >= 2
        assert len(protocol.citation_source_ids) >= 2
