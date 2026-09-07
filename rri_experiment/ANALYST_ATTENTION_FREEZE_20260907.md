# RRI × Analyst Attention — Pre-result Freeze

Freeze timestamp: 2026-09-07. This design is committed before opening any RRI coefficient for this outcome.

## Status and role
This is a theory-driven secondary information-intermediary test added only after the pre-frozen analyst-dispersion design failed its public-data coverage gate. It is not a substitute for analyst forecast dispersion and will not be relabeled as the original primary test.

## Economic question
Does higher-quality regulatory inquiry response reduce information-processing frictions enough to increase subsequent sell-side analyst coverage?

## Hypothesis
Expected sign: beta > 0. Inference will use two-sided p-values. The mechanism is lower information acquisition/processing cost for analysts after a more precise, requirement-responsive regulatory disclosure.

## Outcome
AnaAttention = number of analysts / analyst teams that track the firm during a fiscal year. Transform before estimation as ln(1 + AnaAttention).

Primary outcome: ln(1 + AnaAttention_{t+1}).
Pre-period control: ln(1 + AnaAttention_{t-1}).

## Primary specification AA1
ln(1 + AnaAttention_{t+1}) = alpha + beta * RRI10_t + delta * ln(1 + AnaAttention_{t-1}) + controls_t + Year FE + Industry FE + InquiryType FE + error.

Controls_t are frozen as:
- Size_t
- Leverage_t
- ROA_t
- ln(1 + total_questions_t)

SEs clustered by firm.
Financial firms excluded using the public annual financial panel's IS_FINANCE flag.

## Supporting specifications
- AA0: RRI10 only (descriptive benchmark).
- AA1: primary ANCOVA specification above.
- AA2: AA1 restricted to the first RRI firm-year per firm.
- AA3: change form, Delta ln(1+AnaAttention) = post minus pre, with the same t controls and fixed effects as AA1 except the lagged dependent variable.

No alternative windows, cutoffs, transformations, or outcome variants will be searched after seeing coefficients.

## Coverage gate
Before coefficient interpretation, require at least 120 nonfinancial RRI firm-years with both t-1 and t+1 AnaAttention observed. If the gate fails, this public-data route is NO-GO and the threshold will not be lowered after seeing results.

## Governance
Two-sided p-values are reported even though the expected sign is positive. A null or negative result is retained as such. This experiment is exploratory/secondary relative to the analyst-dispersion hypothesis because it was designed after the public analyst-detail data route failed coverage.
