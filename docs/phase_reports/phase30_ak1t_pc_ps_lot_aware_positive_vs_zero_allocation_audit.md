# Phase30-AK1T - PC/PS Positive-vs-Zero Allocation Audit

## Scope

Task ID: `Phase30-AK1T`

Task type: `READ_ONLY_AUDIT`

Target run:

```text
runtime-test-historical-extended-smoke-20260816T121454359538Z
```

The run was not stopped, resumed, replayed, repaired, or mutated. No
implementation, threshold, Candidate, model, cap, lot size, forced BUY, forced
exposure, fresh run, or historical outcome fitting was performed.

Audit freeze from run state at AK1T audit start:

```text
AUDIT_CUTOFF_DATE = 2023-10-10
COMPLETED_BUSINESS_DAYS = 287
```

## Primary Judgment

```text
PC_PS_ALLOCATION_PRIMARY_ROOT_CAUSE = LOT_ECONOMICS_FRICTION
PC_PS_ALLOCATION_SECONDARY_ROOT_CAUSES = [
  RESIDUAL_RECYCLING_GAP,
  GENUINE_EXECUTION_CONSTRAINT
]
```

The main BUY-vs-zero discriminator is not CAUTION presence. Actual BUY and
zero rows both carry caution. The dominant discriminator is whether the PC
incremental target is large enough relative to one executable lot and whether
lot-aware residual priority still materializes a final quantity.

```text
PRIMARY_BUY_VS_ZERO_DISCRIMINATOR =
TARGET_TO_ONE_LOT_RATIO_AND_LOT_AWARE_RESIDUAL_PRIORITY
```

No strict suspicious allocation was found:

```text
STRICT_SUSPICIOUS_ALLOCATION_COUNT = 0
MEANINGFUL_TARGET_EXECUTABLE_BUT_ZERO_COUNT = 0
```

That means no case satisfied the strict set of meaningful target, one-lot
executable, cash sufficient, both caps clear, entry/lifecycle clear, no pending
conflict, and final quantity zero.

## Canonical Population

BUY_NEW / REENTRY PC-positive rows through cutoff:

```text
ALLOCATION_SUCCESS_COUNT = 170
PC_POSITIVE_FINAL_ZERO_COUNT = 4,076
```

Success definition:

```text
PC positive target
PS final quantity > 0
Runtime BUY intent > 0
```

Zero definition:

```text
PC positive target
PS final quantity = 0
```

## Target / One-Lot Curve

```text
TARGET_TO_ONE_LOT_SUCCESS_CURVE = {
  "<0.5":       total 1873, success 0,   zero 1873, success_rate 0.0000
  "0.5-<0.75": total 252,  success 0,   zero 252,  success_rate 0.0000
  "0.75-<1.0": total 880,  success 3,   zero 877,  success_rate 0.0034
  "1.0-<1.5":  total 1015, success 43,  zero 972,  success_rate 0.0424
  ">=1.5":     total 226,  success 124, zero 102,  success_rate 0.5487
}
```

The curve is decisive. Below one executable lot of target notional, BUY success
is essentially absent. Success rises materially only when the PC target is at
least 1.5 lots.

## One-Lot Bias

```text
LOW_NOTIONAL_LOT_BIAS_CONFIRMED = YES
ONE_LOT_NOTIONAL_IS_MAJOR_DISCRIMINATOR = YES
MEDIAN_ONE_LOT_NOTIONAL_SUCCESS = 18,860 JPY
MEDIAN_ONE_LOT_NOTIONAL_ZERO = 98,065 JPY
```

Cheaper one-lot names are much more likely to become executable quantity.
Higher one-lot notional names often remain zero even after PC-positive
allocation direction.

## Lot-Aware Priority Contract

Producer:

```text
LOT_AWARE_PRIORITY_PRODUCER =
src/ai_fund_lab_v2/strategy/portfolio_construction.py::apply_lot_aware_final_reallocation
src/ai_fund_lab_v2/strategy/portfolio_construction.py::_quality_adjusted_reallocation_order
src/ai_fund_lab_v2/strategy/portfolio_construction.py::_quality_adjusted_one_lot_admission
```

Consumed by:

```text
src/ai_fund_lab_v2/strategy/position_sizing.py
```

Inputs:

```text
Selection Quality
Candidate Surface
Entry Admission
Downside / Risk evidence
Opportunity rank / order
PC target / increment
target_to_one_lot_ratio
one-lot overshoot
remaining / residual capital
Strategy cap
Safety hard cap
concentration / current weight
broker / lot feasibility
```

Form:

```text
LOT_AWARE_PRIORITY_FORM = MIXED
```

It is a rule chain plus lexicographic/quality-adjusted priority and numeric lot
feasibility. It is not a single transparent numeric score.

## CAUTION Action Effect

```text
CAUTION_PC_PS_ACTION_EFFECT =
CAUTION can lower quality-adjusted priority, block/defer one-lot admission for
overheated/reversal/BUY_WAIT/reject semantics, reduce accepted lot increment,
and route residual to Cash; CAUTION exists is not reject.
```

This preserves the AK1S finding: CAUTION appears in both BUY and Cash cases.
CAUTION is action-effective only through PC/PS priority, one-lot admission, and
residual allocation.

## Same-Day Pair Audit

```text
SAME_DAY_BUY_VS_ZERO_PRIMARY_DISCRIMINATOR =
BUY rows have materially higher target/one-lot ratio and survive lot-aware
residual priority within the same cash/portfolio context.
```

Same-day pairs are saved in:

```text
reports/phase_reports/phase30_ak1t/same_day_buy_vs_zero_pairs.json
```

## Residual Capital Recycling

```text
RESIDUAL_CAPITAL_RECYCLING_ACTION_EFFECTIVE = PARTIAL
DAYS_WITH_CASH_BEFORE_EXECUTABLE_CANDIDATE_EXHAUSTION = 287
```

Residual recycling does allocate to many later candidates, but residual cash can
remain while some one-lot feasible PC-positive candidates still exist. This is
not automatically wrong because the lot-aware priority may prefer Cash over
weak marginal concentration. It is, however, an observability and design-review
candidate.

## Existing Baseline Effect

```text
ALLOCATION_LAYER_INCUMBENCY_BIAS = PARTIAL
PM_HOLD_BASELINE_INDIRECT_NEW_ALLOCATION_EFFECT = PARTIAL
```

AK1S did not confirm direct incumbency bias. AK1T confirms an indirect layer:
retained existing HOLD / ADD baseline consumes gross exposure first, and new
BUY_NEW / REENTRY candidates compete only for remaining incremental budget.
The artifacts do not prove a full new-vs-existing rotation comparison.

```text
FULL_PORTFOLIO_NEW_OPPORTUNITY_ROTATION_CONTRACT =
PC preserves retained existing HOLD/ADD baseline and allocates only remaining
incremental budget to BUY_NEW/REENTRY. New candidates compete for incremental
budget; full rotation against existing HOLD is not proven as an active
relative-capital comparison in these artifacts.

NEW_VS_EXISTING_RELATIVE_CAPITAL_COMPARISON = PARTIAL
```

## Position Slot / Rotation

```text
POSITION_SLOT_LIMIT_BLOCK_COUNT = 0
```

The only matched reason text was `portfolio_fit_not_position_count_gate`, so no
actual position-slot block was found.

## Root-Cause Distribution

```text
PC_PS_ZERO_ROOT_CAUSE_DISTRIBUTION = {
  LOT_ECONOMICS_FRICTION: 2,250
  RESIDUAL_RECYCLING_GAP: 1,074
  GENUINE_EXECUTION_CONSTRAINT: 752
}
```

Interpretation:

- `LOT_ECONOMICS_FRICTION`: PC increment is positive but below or barely near
  executable one-lot economics.
- `RESIDUAL_RECYCLING_GAP`: lot/cash/cap appear possible but residual priority
  still routes to another candidate or Cash; needs clearer evidence.
- `GENUINE_EXECUTION_CONSTRAINT`: lot, cap, or broker feasibility does not pass.

## Philosophy Conformance

```text
PC_PS_ALLOCATION_CONFORMS_TO_INVESTMENT_PHILOSOPHY = PARTIAL
```

The behavior preserves:

```text
FORCED_INVESTMENT_REQUIRED = NO
FIXED_EXPOSURE_TARGET_REQUIRED = NO
FIXED_POSITION_COUNT_REQUIRED = NO
WINNER_CONCENTRATION_POLICY_CHANGE_PROPOSED = NO
```

Partial conformance reflects that strict suspicious cases are zero, but
residual recycling / rotation / target-to-lot explainability is still not
sufficiently crisp for repair design.

## Runtime / Authority Integrity

```text
PC_PS_RUNTIME_DEFECT = NO
PC_PS_AUTHORITY_DEFECT = YES
```

This is not a Runtime execution defect. The authority issue is that PC-positive
does not carry enough machine-readable explanation of why lot-aware priority
materializes one candidate but routes another to zero/Cash.

## Leakage

```text
PERFORMANCE_USED_FOR_ALLOCATION_PARAMETER_SELECTION = FALSE
FUTURE_RETURN_USED_FOR_ALLOCATION_JUDGMENT = FALSE
```

## Deliverables

Summary:

```text
reports/phase_reports/phase30_ak1t_pc_ps_lot_aware_positive_vs_zero_allocation_audit.json
```

Detailed evidence:

```text
reports/phase_reports/phase30_ak1t/
```

Generated files include:

```text
canonical_comparison_population.json
allocation_success_rows.json
pc_positive_final_zero_rows.json
target_to_one_lot_success_curve.json
meaningful_target_executable_but_zero.json
lot_aware_priority_contract.json
buy_vs_zero_cross_tab.json
same_day_buy_vs_zero_pairs.json
one_lot_bias_analysis.json
residual_capital_recycling_analysis.json
baseline_effect_analysis.json
position_slot_rotation_analysis.json
strict_suspicious_allocation.json
pc_ps_zero_root_cause_distribution.json
```

## Implementation Authorization

```text
NO_IMPLEMENTATION_AUTHORIZED_BY_PHASE30_AK1T
```

## Recommended Next Task

```text
Phase30-AK2 - PC/PS Lot-Aware Allocation Explainability and Residual Recycling Design
```

Design only. Do not start with threshold loosening, forced BUY, fixed exposure,
or cap changes.
