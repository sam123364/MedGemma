# Judge Q&A Prep

## Why MedGemma and not a generic model?
Kaggle requires HAI-DEF usage. MedGemma is used in protocol ideation, mechanism calibration, and grounded explanation.

## Is this truly agentic orchestration or just sequential code?
It is implemented as an explicit LangGraph state graph with named nodes, directed edges, and conditional error routing. Node state is checkpointed after each successful step.

## How does crash recovery work?
Every completed node writes a serialized checkpoint to SQLite (`run_checkpoints`). `POST /api/v1/runs/{run_id}/resume` loads the latest checkpoint and resumes from the next pending node.

## How do you avoid hallucinated recommendations?
Deterministic safety rules can disqualify protocols regardless of LLM text. Recommendations are traceable to stored run artifacts and citations.

## Is this clinically deployable today?
No. This is a research simulation prototype for workflow exploration and decision support experimentation.

## Why 1,000 trials + high-fidelity reruns?
This keeps scale computationally feasible while preserving deeper reasoning where it matters most.

## What is novel here?
The novelty is workflow-level redesign: retrieval + simulation + deterministic safety + grounded explanation in one auditable loop, plus a Many Patients Map that visualizes recommendation shifts across 27 nearby synthetic twins.

## What happens if MedGemma runtime is unavailable?
The system can run in mock mode for development, but challenge submission uses MedGemma runtime and logs model config.

## How is impact estimated?
From proxy metrics: time-to-shortlist, safety-flag recall on contraindication scenarios, and score separation between top protocol candidates.

## What measured reliability evidence do you have?
Benchmark runner logs demo (5/5 completed, 0 failures, 0.514s mean E2E) and full profile (1/1 completed, 3.078s E2E) in `output/benchmarks/benchmark_raw.json`.

## How is database evolution handled?
Alembic baseline migration is included; startup verifies expected schema revision (configurable via `ENFORCE_ALEMBIC_HEAD`).
