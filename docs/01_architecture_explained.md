# Architecture Explained

## Pipeline
1. Input synthetic patient twin.
2. Retrieve evidence chunks from Chroma fallback corpus.
3. Generate protocol candidates with MedGemma + evidence context.
4. Run 1,000 coarse trajectories for broad protocol search.
5. Re-simulate top protocols with MedGemma-calibrated high-fidelity loop.
6. Apply deterministic safety critic.
7. Rank, explain, and stream results to UI.

## Why this architecture
- Coarse layer gives scale.
- High-fidelity layer gives depth.
- Deterministic critic gives control and guardrails.
- SSE gives transparent live execution narrative.
