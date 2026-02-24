# Astra-Gemma 3-Minute Demo Script

## 0:00 - 0:20 Problem framing
"Protocol selection is still a high-friction workflow. Astra-Gemma creates a synthetic patient twin and runs 1,000 in-silico trials before ranking personalized protocols."

## 0:20 - 0:55 Show patient twin builder
- Enter synthetic profile values.
- Explain key biomarkers: HbA1c, fasting glucose, eGFR, ALT.
- Click "Launch Astra-Gemma Run".

## 0:55 - 1:35 Show live agentic workflow
- Timeline events: `run.started`, `protocols.generated`, `coarse.progress`, `shortlist.ready`, `highfidelity.progress`, `critic.done`, `population_map.ready`, `run.completed`.
- Explain LangGraph nodes + checkpointing.
- Mention `run.resumed` event for crash recovery.

## 1:35 - 2:10 Show simulation divergence
- Display top 5 trajectories in chart.
- Highlight one blocked protocol due to safety rules.
- Open ranked board and point to efficacy/safety split.

## 2:10 - 2:35 Show Many Patients Map
- Scroll to “Recommendation Stability Across Patient Variants.”
- Explain 27-cell synthetic neighborhood (age x eGFR x HbA1c).
- Highlight at least one region where top protocol changes and why that matters.

## 2:35 - 2:50 Explainability Q&A
Ask:
"Why is protocol #1 safer than #2?"
Show grounded answer with cited source IDs.

## 2:50 - 3:00 Close
"Astra-Gemma transforms protocol design from static heuristics into an auditable agentic workflow powered by MedGemma."
End with disclaimer: research prototype, not medical advice.
