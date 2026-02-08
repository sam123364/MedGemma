# Judge Q&A Prep

## Why MedGemma and not a generic model?
Kaggle requires HAI-DEF usage. MedGemma is used in protocol ideation, mechanism calibration, and grounded explanation.

## How do you avoid hallucinated recommendations?
Deterministic safety rules can disqualify protocols regardless of LLM text. Recommendations are traceable to stored run artifacts and citations.

## Is this clinically deployable today?
No. This is a research simulation prototype for workflow exploration and decision support experimentation.

## Why 1,000 trials + high-fidelity reruns?
This keeps scale computationally feasible while preserving deeper reasoning where it matters most.

## What is novel here?
The novelty is workflow-level redesign: retrieval + simulation + deterministic safety + grounded explanation in one auditable loop.

## What happens if MedGemma runtime is unavailable?
The system can run in mock mode for development, but challenge submission uses MedGemma runtime and logs model config.

## How is impact estimated?
From proxy metrics: time-to-shortlist, safety-flag recall on contraindication scenarios, and score separation between top protocol candidates.
