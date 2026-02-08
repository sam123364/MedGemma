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

MedGemma is used in high-value cognitive steps: protocol ideation, mechanistic coefficient calibration, and grounded explanation.

# Technical details
- Backend: FastAPI, asyncio orchestration, SQLite event sourcing, Chroma evidence retrieval.
- Frontend: Next.js streaming dashboard with trajectory divergence, workflow timeline, and grounded Q&A.
- Scoring: `0.45 efficacy + 0.25 safety + 0.15 adherence + 0.15 robustness`.
- Guardrails: hard-stop contraindications, disqualification logic, and non-diagnostic disclaimer at every recommendation surface.
- Reproducibility: one-command bootstrap, local run, and documented environment configuration.

# Impact potential
If used as a clinician-side triage assistant for protocol exploration, this workflow can reduce protocol-shortlisting time and
improve transparency by forcing citation-backed rationale and explicit safety tradeoffs.

This is a research prototype and does not provide clinical recommendations.
