# Simulation Math

## Coarse stage
- Monte Carlo across `N=1000` trajectories.
- State updates include efficacy coefficients, adherence drift, and stochastic risk noise.
- Outputs include expected HbA1c delta, glucose delta, adverse-event rate, robustness index.

## High-fidelity stage
- MedGemma proposes protocol-specific coefficient adjustments.
- Daily state rollout over 180 days tracks glycemic, cardio-metabolic, and safety signals.

## Final score
`total = 0.45*efficacy + 0.25*safety + 0.15*adherence + 0.15*robustness`

Hard-stop safety rules can disqualify a protocol regardless of score.
