# Architecture Explained

## Pipeline
1. Input synthetic patient twin.
2. Execute LangGraph node `retrieve_evidence` against Chroma-guideline corpus.
3. Execute LangGraph node `generate_protocols` with MedGemma + evidence context.
4. Execute LangGraph node `run_simulation` for 1,000 coarse trajectories + high-fidelity reruns.
5. Execute LangGraph node `evaluate_safety` with deterministic contraindication rules.
6. Execute LangGraph node `score_and_rank` for weighted ranking + black-box warnings.
7. Execute LangGraph node `persist_artifact`, including 27-cell Many Patients Map.
8. Execute LangGraph node `finalize_run`; stream all events to UI via SSE.

## Why this architecture
- Coarse layer gives scale.
- High-fidelity layer gives depth.
- Deterministic critic gives control and guardrails.
- LangGraph checkpointing enables crash-safe resume.
- SSE gives transparent live execution narrative.
