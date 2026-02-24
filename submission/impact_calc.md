# Impact Calculation Framework (Prototype)

## Metric 1: Time-to-shortlist
- Baseline (manual review): 25-40 min for 8-10 candidates.
- Astra-Gemma measured (demo profile): shortlist event in ~`0.125s` mean from run start.
- Astra-Gemma measured (full profile): shortlist event in ~`0.347s`.
- Proxy impact statement: workflow compression from tens of minutes to sub-second shortlist generation in simulation mode.

## Metric 2: Safety-flag recall
- Test suite includes explicit contraindication scenarios.
- Measured: deterministic blocking for encoded hard-stop rules in automated tests (`EGFR_METFORMIN_CONTRAINDICATION`, `LOW_EGFR_SGLT2_RISK`, `ALT_TZD_RISK`, `SEVERE_EVENT_BURDEN`).

## Metric 3: Decision transparency
- Every protocol carries >=2 citation links and explicit score decomposition.
- Measured: run artifact stores citations, score components, safety flags, timeline events, and checkpoint lineage per run.

## Metric 4: Workflow consistency
- Standardized scoring prevents drift in ad-hoc rationale quality.
- Measured benchmark stability (demo profile): `5/5` completed, `0` failures, mean E2E `0.514s`, stddev `0.013s`.
- Full profile completion: `1/1` with E2E `3.078s`.

## Metric 5: Evidence scale quality
- Target corpus size: `500` curated records.
- Measured: collection count `500`, duplicate rate `0.0%`, missing year count `0`, duplicate budget (<5%) satisfied.

## Metric 6: Recommendation robustness across nearby phenotypes
- Many Patients Map evaluates `27` neighboring synthetic twins per run (3 age bins x 3 eGFR bins x 3 HbA1c bins).
- Output: protocol-winner map + confidence margin per cell, enabling judges to inspect recommendation stability instead of a single-point answer.

These are prototype-level impact proxies and not claims of clinical efficacy.
