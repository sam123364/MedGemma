import time

from fastapi.testclient import TestClient

from app.main import app


def _extract_events(raw_body: str) -> tuple[list[int], list[str]]:
    event_ids: list[int] = []
    event_types: list[str] = []
    for chunk in raw_body.split("\n\n"):
        if not chunk.strip():
            continue
        event_id = None
        event_type = None
        for line in chunk.splitlines():
            if line.startswith("id: "):
                event_id = int(line.replace("id: ", "").strip())
            if line.startswith("event: "):
                event_type = line.replace("event: ", "").strip()
        if event_id is not None:
            event_ids.append(event_id)
        if event_type:
            event_types.append(event_type)
    return event_ids, event_types


def test_sse_events_are_ordered_and_monotonic() -> None:
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

        deadline = time.time() + 30
        status = "queued"
        while time.time() < deadline:
            status = client.get(f"/api/v1/runs/{run_id}/status").json()["status"]
            if status in {"completed", "failed"}:
                break
            time.sleep(0.4)
        assert status == "completed"

        stream = client.get(f"/api/v1/runs/{run_id}/events")
        assert stream.status_code == 200
        event_ids, event_types = _extract_events(stream.text)

        assert event_ids == sorted(event_ids)
        assert len(event_ids) == len(set(event_ids))

        expected_order = [
            "run.started",
            "protocols.generated",
            "coarse.progress",
            "shortlist.ready",
            "highfidelity.progress",
            "critic.done",
            "population_map.ready",
            "run.completed",
        ]
        for expected in expected_order:
            assert expected in event_types

        positions = [event_types.index(expected) for expected in expected_order]
        assert positions == sorted(positions)

