# Speaker Notes (Slide-by-Slide)

## Slide 1
- Astra-Gemma is a MedGemma-only research prototype for autonomous protocol simulation.
- State clearly: synthetic data only, not medical advice.

## Slide 2
- Emphasize current workflow pain: time, inconsistency, and implicit tradeoffs.
- Judges should feel this is a workflow redesign problem, not just an LLM wrapper.

## Slide 3
- Explain the digital twin framing: we test many protocol paths before ranking.
- Mention 1,000 coarse trajectories + high-fidelity reruns for top candidates.

## Slide 4
- Call out LangGraph explicitly.
- Mention each node is checkpointed and observable through SSE events.

## Slide 5
- Show one blocked protocol.
- Say: “The model can recommend text, but deterministic rules can still veto it.”
- Read the Black Box warning line exactly once for impact.

## Slide 6
- Introduce Many Patients Map as the differentiator.
- “We don’t just answer for one point; we map recommendation stability nearby.”
- Point to one region where recommendation flips.

## Slide 7
- Explain crash-safe resume in one sentence.
- Mention Alembic and revision checks to show production-minded engineering.

## Slide 8
- Read measured metrics directly from artifacts.
- Keep it concise: completion rate, latency, corpus quality.

## Slide 9
- Walk through UI in order:
1. patient profile
2. timeline
3. leaderboard
4. chat
5. population map
- Mention grounded citations in chat answer.

## Slide 10
- Close with impact statement and responsible framing.
- End with: “Astra-Gemma upgrades protocol design from intuition-first to simulation-first.”
