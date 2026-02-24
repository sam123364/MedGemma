import time

from fastapi.testclient import TestClient

from app.main import app


def test_full_run_completes_and_returns_result(monkeypatch) -> None:
    monkeypatch.setattr("app.services.settings.SIM_HORIZON_DAYS", 30, raising=False)
    monkeypatch.setattr("app.services.settings.COARSE_TRIALS", 120, raising=False)
    monkeypatch.setattr("app.services.settings.HIGH_FIDELITY_COUNT", 2, raising=False)
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

        deadline = time.time() + 90
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
        assert "population_map" in body
        assert len(body["population_map"]["cells"]) == 27

        pop = client.get(f"/api/v1/runs/{run_id}/population-map")
        assert pop.status_code == 200
        assert len(pop.json()["cells"]) == 27
