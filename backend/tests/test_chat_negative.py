import time

from fastapi.testclient import TestClient

from app.db.sqlite import repository
from app.main import app


def test_chat_returns_404_for_unknown_run() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/chat/explain",
            json={"run_id": "run-does-not-exist", "question": "Why is protocol #1 preferred?"},
        )
        assert response.status_code == 404


def test_chat_returns_400_when_run_has_no_protocol_results() -> None:
    run_id = "run-empty-artifact"
    repository.create_run(run_id, model_runtime="mock")
    repository.save_run_result(run_id, {"run_id": run_id, "results": []})

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/chat/explain",
            json={"run_id": run_id, "question": "Why is protocol #1 safer?"},
        )
        assert response.status_code == 400


def test_chat_unsupported_claim_still_stays_grounded() -> None:
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
        run = client.post("/api/v1/runs", json=patient_payload).json()
        run_id = run["run_id"]

        # Wait for completion.
        for _ in range(80):
            status = client.get(f"/api/v1/runs/{run_id}/status").json()["status"]
            if status in {"completed", "failed"}:
                break
            time.sleep(0.2)

        response = client.post(
            "/api/v1/chat/explain",
            json={"run_id": run_id, "question": "What was the patient's brain MRI finding?"},
        )
        assert response.status_code == 200
        body = response.json()
        assert "Research prototype disclaimer" in body["answer"]
        assert isinstance(body["grounded_source_ids"], list)
