import sqlite3
import time

import pytest
from fastapi.testclient import TestClient

from app.db.sqlite import repository
from app.main import app
from app.services import settings


def _wait_status(client: TestClient, run_id: str, timeout: float = 35.0) -> str:
    deadline = time.time() + timeout
    status = "queued"
    while time.time() < deadline:
        status = client.get(f"/api/v1/runs/{run_id}/status").json()["status"]
        if status in {"completed", "failed"}:
            return status
        time.sleep(0.3)
    return status


@pytest.mark.parametrize("fail_node", ["generate_protocols", "run_simulation"])
def test_resume_after_fault_injected_node(monkeypatch: pytest.MonkeyPatch, fail_node: str) -> None:
    monkeypatch.setattr(settings, "ASTRA_FAIL_AFTER_NODE", fail_node, raising=False)

    patient_payload = {
        "age": 57,
        "sex": "male",
        "bmi": 31.4,
        "hba1c": 9.4,
        "fasting_glucose": 214,
        "systolic_bp": 140,
        "diastolic_bp": 88,
        "egfr": 76,
        "alt": 34,
        "comorbidities": ["hypertension"],
        "meds_current": ["metformin"],
    }
    with TestClient(app) as client:
        create = client.post("/api/v1/runs", json=patient_payload)
        run_id = create.json()["run_id"]
        status = _wait_status(client, run_id)
        assert status == "failed"

        checkpoint = repository.get_latest_checkpoint(run_id)
        assert checkpoint is not None
        assert checkpoint["node_name"] == fail_node

        # Resume with fault injection disabled.
        monkeypatch.setattr(settings, "ASTRA_FAIL_AFTER_NODE", None, raising=False)
        resumed = client.post(f"/api/v1/runs/{run_id}/resume")
        assert resumed.status_code == 202

        status_after_resume = _wait_status(client, run_id, timeout=50.0)
        assert status_after_resume == "completed"

        event_types = [event["event_type"] for event in repository.get_events_after(run_id, 0)]
        assert "run.resumed" in event_types
        assert "run.completed" in event_types

        if fail_node == "run_simulation":
            with sqlite3.connect(repository.db_path) as conn:
                total_rows = conn.execute(
                    "SELECT COUNT(*) FROM daily_states WHERE run_id = ?",
                    (run_id,),
                ).fetchone()[0]
                distinct_rows = conn.execute(
                    "SELECT COUNT(DISTINCT protocol_id || '-' || day) FROM daily_states WHERE run_id = ?",
                    (run_id,),
                ).fetchone()[0]
            assert total_rows == distinct_rows

