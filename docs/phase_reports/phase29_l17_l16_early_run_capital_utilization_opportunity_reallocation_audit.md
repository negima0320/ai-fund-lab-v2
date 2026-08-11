# Phase29-L17 - L16 Early-Run Capital Utilization / Opportunity Reallocation Audit

## 0. Summary

Task ID: Phase29-L17

Run:

```text
runtime-test-historical-smoke-20260811T024356531918Z
```

Audit scope:

```text
2022-08-10 through 2022-08-24
10 completed business days
```

Primary Judgment:

```text
PHASE29_L17_L16_EARLY_RUN_CAPITAL_UTILIZATION_AUDIT_PASS_NO_STRATEGY_REGRESSION
```

Secondary Judgment:

```text
PHASE29_L17_CAPITAL_ALLOCATION_GAP_REMAINS_PRE_L16_STYLE_NOT_L16_REGRESSION
```

This was a READ-ONLY evidence audit. No Production, Strategy, Runtime, Config,
Schema, Model, Threshold, Accepted Generation, Runtime state, Pending, Ledger,
Artifact Registry, quarantine state, or Historical run state was changed.

## 1. Primary Findings

The high cash ratio observed on 2022-08-24 is real:

```text
cash = 688,120
market_value = 304,170
total_equity = 992,290
cash_ratio = 69.346663%
invested_ratio = 30.653337%
positions_count = 2
```

The evidence does not support an L16-caused BUY_NEW over-suppression regression
in the first 10BD. Across Top20 opportunity rows for the audited dates:

```text
L16 low-price guard activated: NO
L16 liquidity cap activated: NO
L16 reentry guard activated: NO
L16 affected candidates: 0
```

The cash remained unallocated primarily because candidate supply was thin after
Buy Quality / opportunity rejection, and later because minimum lot / concentration
constraints prevented ADD or BUY_NEW rebatching:

```text
Main unallocated-capital reason: NO_ELIGIBLE_OPPORTUNITY
Secondary reason: CONCENTRATION_LIMIT
```

## 2. Daily Capital Utilization

Authority:

```text
reports/runtime_tests/runs/runtime-test-historical-smoke-20260811T024356531918Z/daily/<date>/current_valuation_refresh/valuation_projection.json
reports/runtime_tests/runs/runtime-test-historical-smoke-20260811T024356531918Z/daily/<date>/execution/fills.json
```

Reconstructed 10BD summary:

```text
Average cash ratio: 83.084136%
Minimum cash ratio: 68.987919%
Maximum cash ratio: 86.712474%
Average invested ratio: 16.915864%
```

Daily execution was limited to two BUY_NEW fills:

```text
2022-08-10: BUY 94320, gross notional 134,280
2022-08-23: BUY 23880, gross notional 177,600
SELL notional: 0 across audited dates
```

Detailed reconstruction:

```text
reports/phase29_l17_l16_early_run_capital_utilization_opportunity_reallocation_audit/daily_capital_utilization.csv
```

## 3. Opportunity Funnel

Top20 opportunity funnel rows:

```text
BUY_NEW_EXECUTED: 2
OTHER_BUY_QUALITY_REJECTED: 188
POSITION_SIZING_ZERO_DELTA: 10
```

BUY_NEW counts:

```text
BUY_NEW candidate count: 190
BUY_NEW eligible count: 5
BUY_NEW positive target count: 2
BUY_NEW positive sizing count: 2
BUY_NEW submitted count: 2
BUY_NEW filled count: 2
```

The evidence indicates that eligible BUY_NEW opportunities were scarce. The two
rows that became positive sizing were submitted and filled. The remaining BUY_NEW
rows were dominated by Buy Quality / non-positive edge rejection, not L16 caps.

Detailed funnel:

```text
reports/phase29_l17_l16_early_run_capital_utilization_opportunity_reallocation_audit/opportunity_funnel.csv
reports/phase29_l17_l16_early_run_capital_utilization_opportunity_reallocation_audit/buy_new_audit.csv
reports/phase29_l17_l16_early_run_capital_utilization_opportunity_reallocation_audit/daily_top_opportunities.csv
```

## 4. L16 Impact Isolation

No L16-affected Top20 candidate was observed in the audited 10BD:

```text
L16 low-price guard activated: NO
L16 liquidity cap activated: NO
L16 reentry guard activated: NO
```

Therefore, there is no evidence that L16 suppressed capital that should have
been reallocated during this early window. No counterfactual PnL was computed.

Detailed file:

```text
reports/phase29_l17_l16_early_run_capital_utilization_opportunity_reallocation_audit/l16_affected_candidates.csv
```

## 5. Capital Reallocation

Capital reallocation priority was audited as:

```text
ADD -> uncapped BUY_NEW -> other Strategy opportunity -> Cash
```

Observed result:

```text
Suppressed capital reallocated: NO_L16_SUPPRESSED_CAPITAL_OBSERVED
Suppressed capital remained Cash: NO_L16_SUPPRESSED_CAPITAL_OBSERVED
Main unallocated-capital reason: NO_ELIGIBLE_OPPORTUNITY
```

On 2022-08-24, Portfolio Construction requested:

```text
accepted_add_increment = 0.043121
accepted_buy_new_weight = 0.18
available_incremental_budget = 0.689879
```

But lot-aware final reallocation kept final target weight at existing exposure:

```text
final_target_weight_sum = 0.310121
remaining_cash_weight = 0.689879
residual_cash_reason = CONCENTRATION_LIMIT
skipped 94320: minimum_lot_exceeds_concentration_cap
skipped 78780: minimum_lot_exceeds_concentration_cap
```

This is a capital allocation / lot concentration bottleneck, not an L16 low-price
guard regression.

Detailed files:

```text
reports/phase29_l17_l16_early_run_capital_utilization_opportunity_reallocation_audit/capital_reallocation.csv
reports/phase29_l17_l16_early_run_capital_utilization_opportunity_reallocation_audit/unallocated_capital_reason.csv
```

## 6. BUY_ADD Preservation

BUY_ADD path evidence:

```text
ADD intent count: 5
BUY_ADD eligible count: 4
BUY_ADD quantity-positive count: 0
BUY_ADD submitted count: 0
BUY_ADD filled count: 0
```

ADD was not weakened by L16:

```text
ADD weakened by L16: NO
BUY_ADD blocked by reentry cooldown: 0
BUY_ADD blocked by BUY_NEW low-price guard: 0
```

The ADD rows stayed on canonical BUY_ADD semantics, but lot/minimum-notional and
concentration feasibility kept quantity_delta_candidate at zero. Example
2022-08-24 for 94320:

```text
pm_action = ADD
semantic_buy_type = BUY_ADD
accepted_incremental_weight = 0.043121
lot_aware_accepted_incremental_weight = 0.0
quantity_delta_candidate = 0
reason = ADD_INCREMENT_NOT_EXECUTABLE_BELOW_MINIMUM_OR_LOT / ADD_TARGET_NOTIONAL_DELTA_ZERO
```

Detailed file:

```text
reports/phase29_l17_l16_early_run_capital_utilization_opportunity_reallocation_audit/buy_add_audit.csv
```

## 7. 93180 Verification

93180 appeared in the Top20 opportunity evidence on every audited date, but was
not rejected by a 93180-specific rule and was not blocked by L16 in this window.

Observed 93180 pattern:

```text
membership_intent = EXCLUDE
quality_action = REJECT
allocation_cap_reason = NONE
price_tick_risk_tier = UNKNOWN
liquidity_capacity_status = UNKNOWN
reason includes opportunity_no_buy_reason_present:non_positive_expected_edge_score
```

93180-specific rule present:

```text
NO
```

## 8. Holdings Evidence

2022-08-24 valuation:

```text
cash = 688,120
market_value = 304,170
total_equity = 992,290
positions_count = 2
```

Holdings:

```text
94320: qty 900, market value 136,170
23880: qty 1200, market value 168,000
```

The two holdings came from BUY_NEW fills on 2022-08-10 and 2022-08-23.

## 9. Dynamic / Compound Capital Authority

Compound capital evidence:

```text
evaluation_capital fixed at 1M: BASELINE_NOT_STRATEGY_AUTHORITY
evaluation_capital used as Strategy capital authority: NO
Current equity used by PC: WEIGHT_AUTHORITY_ONLY; L16 notional liquidity-cap path not activated in audited 10BD
Current equity used by Position Sizing: YES
Position Sizing portfolio_total_equity min: 997,450
Position Sizing portfolio_total_equity max: 1,002,160
Compound-capital path confirmed: YES
Compound-capital gap: NO
```

Detailed file:

```text
reports/phase29_l17_l16_early_run_capital_utilization_opportunity_reallocation_audit/compound_capital_authority_audit.json
```

## 10. Non-Regression

```text
SELL semantics changed: NO
REDUCE semantics changed: NO
EXIT semantics changed: NO
L7 SELL quantity contract preserved: YES
```

This audit did not identify any SELL / REDUCE / EXIT mutation. No SELL execution
was observed in the audited dates, and no code/runtime mutation was performed.

## 11. Final Required Fields

```text
Primary Judgment:
PHASE29_L17_L16_EARLY_RUN_CAPITAL_UTILIZATION_AUDIT_PASS_NO_STRATEGY_REGRESSION

10BD completed:
YES
Current cash ratio:
69.346663%
Current invested ratio:
30.653337%

L16 low-price guard activated:
NO
L16 liquidity cap activated:
NO
L16 reentry guard activated:
NO

BUY_NEW candidate count:
190
BUY_NEW eligible count:
5
BUY_NEW positive target count:
2
BUY_NEW positive sizing count:
2
BUY_NEW submitted count:
2
BUY_NEW filled count:
2

ADD intent count:
5
BUY_ADD eligible count:
4
BUY_ADD quantity-positive count:
0
BUY_ADD submitted count:
0
BUY_ADD filled count:
0

ADD weakened by L16:
NO
BUY_ADD blocked by reentry cooldown:
0
BUY_ADD blocked by BUY_NEW low-price guard:
0

SELL semantics changed:
NO
REDUCE semantics changed:
NO
EXIT semantics changed:
NO
L7 SELL quantity contract preserved:
YES

Suppressed capital reallocated:
NO_L16_SUPPRESSED_CAPITAL_OBSERVED
Suppressed capital remained Cash:
NO_L16_SUPPRESSED_CAPITAL_OBSERVED
Main unallocated-capital reason:
NO_ELIGIBLE_OPPORTUNITY

Opportunity Cost functioning:
YES_FOR_OBSERVED_ELIGIBLE_BUY_NEW; NO_L16_SUPPRESSED_CAPITAL_TO_REALLOCATE
Dynamic Capital functioning:
YES
Cash Exposure Authority functioning:
YES

evaluation_capital fixed at 1M:
BASELINE_NOT_STRATEGY_AUTHORITY
evaluation_capital used as Strategy capital authority:
NO
Current equity used by PC:
WEIGHT_AUTHORITY_ONLY; L16_LIQUIDITY_NOTIONAL_PATH_NOT_ACTIVATED_IN_10BD
Current equity used by Position Sizing:
YES
Compound-capital path confirmed:
YES
Compound-capital gap:
NO

93180 low-price risk handling:
GENERAL_RULE_READY_BUT_NOT_TRIGGERED; 93180_REJECTED_BY_NON_POSITIVE_EXPECTED_EDGE
93180-specific rule present:
NO

Production defect:
NO
Strategy regression:
NO
Capital allocation gap:
YES_PRE_EXISTING_LOT_CONCENTRATION_ELIGIBLE_SUPPLY_GAP

Production code changed: NO
Strategy code changed: NO
Runtime code changed: NO
Config changed: NO
Schema changed: NO
Runtime mutated: NO
Pending mutated: NO
Ledger mutated: NO
Historical executed: NO
Fresh-run executed: NO
Resume executed: NO

Recommended next task:
Phase29-L18 - Lot / Concentration Feasibility Capital Deployment Bottleneck Audit and Repair Design
```

## 12. Deliverables

```text
docs/phase_reports/phase29_l17_l16_early_run_capital_utilization_opportunity_reallocation_audit.md
reports/phase29_l17_l16_early_run_capital_utilization_opportunity_reallocation_audit/evidence_manifest.md
reports/phase29_l17_l16_early_run_capital_utilization_opportunity_reallocation_audit/daily_capital_utilization.csv
reports/phase29_l17_l16_early_run_capital_utilization_opportunity_reallocation_audit/opportunity_funnel.csv
reports/phase29_l17_l16_early_run_capital_utilization_opportunity_reallocation_audit/l16_affected_candidates.csv
reports/phase29_l17_l16_early_run_capital_utilization_opportunity_reallocation_audit/capital_reallocation.csv
reports/phase29_l17_l16_early_run_capital_utilization_opportunity_reallocation_audit/buy_add_audit.csv
reports/phase29_l17_l16_early_run_capital_utilization_opportunity_reallocation_audit/buy_new_audit.csv
reports/phase29_l17_l16_early_run_capital_utilization_opportunity_reallocation_audit/compound_capital_authority_audit.json
reports/phase29_l17_l16_early_run_capital_utilization_opportunity_reallocation_audit/daily_top_opportunities.csv
reports/phase29_l17_l16_early_run_capital_utilization_opportunity_reallocation_audit/unallocated_capital_reason.csv
reports/phase29_l17_l16_early_run_capital_utilization_opportunity_reallocation_audit/summary_metrics.json
```
