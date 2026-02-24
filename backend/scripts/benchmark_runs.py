from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

from app.db.sqlite import repository
from app.graph.workflow import workflow_service
from app.models.schemas import PatientTwinInput
from app.services import settings


@dataclass
class ProfileConfig:
    name: str
    sim_horizon_days: int
    coarse_trials: int
    high_fidelity_count: int
    target_count: int
    runs: int
    timeout_seconds: int


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    return datetime.fromisoformat(ts)


def _stage_durations(run_id: str) -> dict[str, float | None]:
    events = repository.get_events_after(run_id, 0)
    by_type: dict[str, datetime] = {}
    for event in events:
        if event["event_type"] not in by_type:
            parsed = _parse_iso(event.get("timestamp"))
            if parsed:
                by_type[event["event_type"]] = parsed

    started = by_type.get("run.started")
    completed = by_type.get("run.completed") or by_type.get("run.failed")

    def delta(event_type: str) -> float | None:
        if started is None:
            return None
        marker = by_type.get(event_type)
        if marker is None:
            return None
        return round((marker - started).total_seconds(), 3)

    end_to_end = None
    if started and completed:
        end_to_end = round((completed - started).total_seconds(), 3)

    return {
        "run.started": 0.0 if started else None,
        "protocols.generated": delta("protocols.generated"),
        "shortlist.ready": delta("shortlist.ready"),
        "critic.done": delta("critic.done"),
        "population_map.ready": delta("population_map.ready"),
        "run.completed": delta("run.completed"),
        "end_to_end_seconds": end_to_end,
    }


async def _wait_for_run(run_id: str, timeout_seconds: int) -> str:
    deadline = asyncio.get_event_loop().time() + timeout_seconds
    while asyncio.get_event_loop().time() < deadline:
        status = repository.get_run_status(run_id)
        if status in {"completed", "failed"}:
            return status
        await asyncio.sleep(0.4)
    return "timeout"


def _patient_payload(index: int) -> PatientTwinInput:
    return PatientTwinInput(
        patient_id=f"bench-{index}",
        age=56 + (index % 4),
        sex="male" if index % 2 == 0 else "female",
        bmi=31.2 + (index * 0.2),
        hba1c=8.8 + (index * 0.1),
        fasting_glucose=186 + (index * 3),
        systolic_bp=138 + (index % 3),
        diastolic_bp=84 + (index % 2),
        egfr=72 - (index % 3),
        alt=34 + (index % 4),
        adherence_probability=0.73,
        comorbidities=["hypertension"],
        meds_current=["metformin"],
        objective="maximize glycemic control while minimizing risk",
    )


async def run_profile(profile: ProfileConfig, start_index: int) -> dict[str, Any]:
    run_rows: list[dict[str, Any]] = []
    for i in range(profile.runs):
        patient = _patient_payload(start_index + i)
        run_id = workflow_service.create_run_id()
        repository.create_run(run_id, model_runtime=settings.MEDGEMMA_RUNTIME)
        workflow_service.start_run(
            run_id=run_id,
            patient=patient,
            target_count=profile.target_count,
            sim_horizon_days=profile.sim_horizon_days,
            coarse_trials=profile.coarse_trials,
            high_fidelity_count=profile.high_fidelity_count,
        )

        status = await _wait_for_run(run_id, profile.timeout_seconds)
        run_rows.append(
            {
                "run_id": run_id,
                "status": status,
                "error": repository.get_run_error(run_id),
                "stages": _stage_durations(run_id),
            }
        )

    completion = [row for row in run_rows if row["status"] == "completed"]
    e2e_values = [row["stages"]["end_to_end_seconds"] for row in completion if row["stages"]["end_to_end_seconds"] is not None]
    return {
        "profile": asdict(profile),
        "total_runs": len(run_rows),
        "completed_runs": len(completion),
        "failed_runs": len([row for row in run_rows if row["status"] == "failed"]),
        "timeout_runs": len([row for row in run_rows if row["status"] == "timeout"]),
        "completion_rate": round((len(completion) / max(1, len(run_rows))) * 100.0, 2),
        "end_to_end_mean_seconds": round(mean(e2e_values), 3) if e2e_values else None,
        "end_to_end_std_seconds": round(pstdev(e2e_values), 3) if len(e2e_values) > 1 else 0.0 if e2e_values else None,
        "runs": run_rows,
    }


def _markdown_summary(raw: dict[str, Any]) -> str:
    lines = [
        "# Astra-Gemma Benchmark Summary",
        "",
        f"- Runtime: `{settings.MEDGEMMA_RUNTIME}` / model `{settings.MEDGEMMA_MODEL}`",
        f"- Generated: `{datetime.utcnow().isoformat()}Z`",
        "",
    ]
    for section in raw.get("profiles", []):
        profile = section.get("profile", {})
        lines.extend(
            [
                f"## {profile.get('name', 'profile')}",
                f"- Runs: `{section.get('total_runs')}`",
                f"- Completed: `{section.get('completed_runs')}`",
                f"- Failed: `{section.get('failed_runs')}`",
                f"- Timeouts: `{section.get('timeout_runs')}`",
                f"- Completion rate: `{section.get('completion_rate')}%`",
                f"- Mean E2E latency: `{section.get('end_to_end_mean_seconds')}` seconds",
                f"- Stddev E2E latency: `{section.get('end_to_end_std_seconds')}` seconds",
                "",
            ]
        )
    return "\n".join(lines)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run benchmark profiles for Astra-Gemma")
    parser.add_argument("--out-json", type=Path, default=Path("../output/benchmarks/benchmark_raw.json"))
    parser.add_argument("--out-md", type=Path, default=Path("../output/benchmarks/benchmark_summary.md"))
    parser.add_argument("--demo-runs", type=int, default=5)
    parser.add_argument("--full-runs", type=int, default=1)
    parser.add_argument("--timeout-seconds", type=int, default=900)
    args = parser.parse_args()

    repository.init_db()
    profiles = [
        ProfileConfig(
            name="demo",
            sim_horizon_days=30,
            coarse_trials=120,
            high_fidelity_count=2,
            target_count=8,
            runs=args.demo_runs,
            timeout_seconds=args.timeout_seconds,
        ),
        ProfileConfig(
            name="full",
            sim_horizon_days=180,
            coarse_trials=1000,
            high_fidelity_count=5,
            target_count=10,
            runs=args.full_runs,
            timeout_seconds=args.timeout_seconds,
        ),
    ]

    sections: list[dict[str, Any]] = []
    offset = 0
    for profile in profiles:
        section = await run_profile(profile, offset)
        offset += profile.runs
        sections.append(section)

    output = {
        "runtime": settings.MEDGEMMA_RUNTIME,
        "model": settings.MEDGEMMA_MODEL,
        "profiles": sections,
    }

    out_json = args.out_json.resolve()
    out_md = args.out_md.resolve()
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(output, indent=2))
    out_md.write_text(_markdown_summary(output))

    print(json.dumps(output, indent=2))
    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")


if __name__ == "__main__":
    asyncio.run(main())
