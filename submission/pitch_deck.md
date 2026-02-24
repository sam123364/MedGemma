# Slide 1 - Astra-Gemma
## Autonomous In-Silico Trial Engine for Type 2 Diabetes
- MedGemma-powered agentic workflow
- Personalized protocol search with deterministic safety guardrails
- Research prototype (synthetic patients only)

# Slide 2 - Problem
## Why protocol design is still slow
- Manual protocol selection is heuristic-heavy and inconsistent
- Hard to balance efficacy, toxicity, adherence, and comorbidities together
- Clinicians need auditable reasoning, not black-box suggestions

# Slide 3 - Core Idea
## From single recommendation to simulation-first workflow
- Build a patient digital twin
- Generate protocol candidates
- Run large in-silico trajectories
- Rank with explicit safety disqualification and evidence traceability

# Slide 4 - Agentic Architecture
## LangGraph multi-agent pipeline
- `init_run -> retrieve_evidence -> generate_protocols -> run_simulation -> evaluate_safety -> score_and_rank -> persist_artifact -> finalize_run`
- Conditional error routing to `fail_run`
- SSE timeline for live observability

# Slide 5 - Safety as First-Class
## Deterministic critic + Black Box Warning UI
- Contraindication rules block risky protocols
- Bright red “PROTOCOL REJECTED” warning with code/reason
- LLM explains tradeoffs, but safety blocking stays deterministic

# Slide 6 - Groundbreaking Feature
## Many Patients Map (27 neighboring twins)
- Age x eGFR x HbA1c grid around current patient
- Shows where top protocol changes across nearby phenotypes
- Converts single-point recommendation into stability analysis

# Slide 7 - Reliability Engineering
## Checkpoints, resume, and migrations
- Per-node SQLite checkpoints (`run_checkpoints`)
- `POST /api/v1/runs/{run_id}/resume` resumes from last node after failure
- Alembic baseline migration + startup schema revision check

# Slide 8 - Evidence + Benchmark Results
## Measured outputs
- Evidence corpus validated to 500 records, 0.0% duplicate rate
- Demo profile: 5/5 completed, 0 failures, mean E2E 0.514s
- Full profile: 1/1 completed, E2E 3.078s

# Slide 9 - Product Experience
## What judges see live
- Patient Twin Builder
- Real-time trajectory divergence and workflow timeline
- Ranked protocol board + grounded Dr. MedGemma chat
- Many Patients Map + Black Box warnings

# Slide 10 - Impact + Ask
## Why this matters
- Compresses protocol exploration from manual review to automated simulation loops
- Makes tradeoffs explicit, inspectable, and reproducible
- Future: richer disease tracks, stronger mechanistic models, and prospective validation
