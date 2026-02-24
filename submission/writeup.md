# Project name
Astra-Gemma: Autonomous In-Silico Clinical Trial Engine

# Your team
- Solo build: Rachit (product, ML systems, backend, frontend, storytelling)

# Problem statement
Protocol personalization is often constrained by sparse time, fragmented evidence, and heuristic decision chains.
In Type 2 Diabetes, clinicians must balance efficacy, safety, and adherence under uncertainty.
Astra-Gemma reframes this from one-shot protocol choice to a simulation-first workflow where candidate protocols are generated,
run across 1,000 synthetic trial trajectories, and safety-gated before recommendation.

# Overall solution
Astra-Gemma uses a MedGemma-only multi-agent architecture:
1. Researcher Agent retrieves evidence and proposes protocol hypotheses.
2. Simulator Agent runs a two-stage experiment loop: 1,000 coarse trajectories, then high-fidelity reruns for top candidates.
3. Critic Agent applies deterministic contraindication logic, computes weighted scorecards, and surfaces explainable ranking.
4. Many Patients Map generates 27 synthetic neighboring twins to visualize where recommendation shifts across phenotype space.

MedGemma is used in high-value cognitive steps: protocol ideation, mechanistic coefficient calibration, and grounded explanation.

# Technical details
- Backend: FastAPI + LangGraph state graph with explicit nodes and conditional error edges.
- Resume reliability: per-node checkpoint snapshots in SQLite (`run_checkpoints`) and `POST /api/v1/runs/{run_id}/resume`.
- Data: Chroma corpus scaled and validated to 500 curated records (`output/evidence/evidence_report.json`).
- Frontend: Next.js streaming dashboard with trajectory divergence, workflow timeline, black-box warnings, grounded Q&A, and Many Patients Map.
- Scoring: `0.45 efficacy + 0.25 safety + 0.15 adherence + 0.15 robustness`.
- Guardrails: hard-stop contraindications, disqualification logic, and non-diagnostic disclaimer at every recommendation surface.
- Reproducibility: one-command bootstrap, Alembic migration baseline, benchmark runner, Playwright E2E tests.

# Measured execution evidence
- Demo profile benchmark (30-day, 120 coarse, top-2 high fidelity): 5/5 completed, 0 failures, mean E2E `0.514s`, stddev `0.013s`.
- Full profile benchmark (180-day, 1000 coarse, top-5 high fidelity): 1/1 completed, E2E `3.078s`.
- Evidence corpus quality: target count `500`, actual `500`, duplicate rate `0.0%`, missing year count `0`.
- UI automation: Playwright E2E passes for run creation, timeline, black-box warning, grounded chat, and population map rendering.

# Impact potential
If used as a clinician-side triage assistant for protocol exploration, this workflow can reduce protocol-shortlisting time and
improve transparency by forcing citation-backed rationale and explicit safety tradeoffs.

This is a research prototype and does not provide clinical recommendations.
