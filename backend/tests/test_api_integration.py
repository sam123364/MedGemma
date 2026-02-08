import time

from fastapi.testclient import TestClient

from app.main import app


def test_full_run_completes_and_returns_result() -> None:
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
        assert create.status_code == 202
        run_id = create.json()["run_id"]

        deadline = time.time() + 25
        status = "queued"
        while time.time() < deadline:
            status_resp = client.get(f"/api/v1/runs/{run_id}/status")
            assert status_resp.status_code == 200
            status = status_resp.json()["status"]
            if status in {"completed", "failed"}:
                break
            time.sleep(0.4)

        assert status == "completed"

        result = client.get(f"/api/v1/runs/{run_id}/result")
        assert result.status_code == 200
        body = result.json()
        assert body["status"] == "completed"
        assert len(body["results"]) >= 1
        assert "final_recommendation" in body
