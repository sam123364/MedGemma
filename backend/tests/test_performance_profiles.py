import time

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import settings


def _patient_payload(seed: int) -> dict:
    return {
        "age": 56 + (seed % 3),
        "sex": "male" if seed % 2 == 0 else "female",
        "bmi": 31.0 + (seed * 0.2),
        "hba1c": 8.8 + (seed * 0.08),
        "fasting_glucose": 190 + (seed * 2),
        "systolic_bp": 138 + (seed % 3),
        "diastolic_bp": 84 + (seed % 2),
        "egfr": 74 - (seed % 2),
        "alt": 33 + (seed % 4),
        "comorbidities": ["hypertension"],
        "meds_current": ["metformin"],
    }


def _wait_for_completion(client: TestClient, run_id: str, timeout_s: float) -> str:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        status = client.get(f"/api/v1/runs/{run_id}/status").json()["status"]
        if status in {"completed", "failed"}:
            return status
        time.sleep(0.25)
    return "timeout"


@pytest.mark.slow
def test_demo_profile_stability_five_consecutive_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "SIM_HORIZON_DAYS", 30, raising=False)
    monkeypatch.setattr(settings, "COARSE_TRIALS", 120, raising=False)
    monkeypatch.setattr(settings, "HIGH_FIDELITY_COUNT", 2, raising=False)

    statuses: list[str] = []
    with TestClient(app) as client:
        for i in range(5):
            created = client.post("/api/v1/runs?target_count=8", json=_patient_payload(i))
            assert created.status_code == 202
            run_id = created.json()["run_id"]
            status = _wait_for_completion(client, run_id, timeout_s=35.0)
            statuses.append(status)

    assert statuses == ["completed"] * 5


@pytest.mark.slow
def test_full_profile_single_run_with_timing_events(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "SIM_HORIZON_DAYS", 180, raising=False)
    monkeypatch.setattr(settings, "COARSE_TRIALS", 1000, raising=False)
    monkeypatch.setattr(settings, "HIGH_FIDELITY_COUNT", 5, raising=False)

    with TestClient(app) as client:
        created = client.post("/api/v1/runs?target_count=10", json=_patient_payload(9))
        assert created.status_code == 202
        run_id = created.json()["run_id"]
        status = _wait_for_completion(client, run_id, timeout_s=180.0)
        assert status == "completed"

        stream = client.get(f"/api/v1/runs/{run_id}/events")
        body = stream.text
        assert "protocols.generated" in body
        assert "critic.done" in body
        assert "population_map.ready" in body
        assert "run.completed" in body
