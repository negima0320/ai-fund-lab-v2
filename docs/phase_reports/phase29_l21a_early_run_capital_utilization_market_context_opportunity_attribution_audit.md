# Phase29-L21A - Early-Run Capital Utilization / Market Context / Opportunity Attribution Audit

Task ID: `Phase29-L21A`

Mode:

```text
READ-ONLY PERFORMANCE ROOT CAUSE / EFFECT ATTRIBUTION AUDIT
NO IMPLEMENTATION
NO CURRENT RUN MUTATION
NO RESUME / FRESH-RUN / RUN / PENDING_LIFECYCLE / REPAIR
NO LONG HISTORICAL EXECUTION
```

Target run:

```text
reports/runtime_tests/runs/runtime-test-historical-smoke-20260811T113809030985Z
```

## 1. Primary Judgment

```text
PHASE29_L21A_HIGH_CASH_IS_PARTIALLY_JUSTIFIED_BY_THIN_QUALITY_SUPPLY_AND_MARKET_CONTEXT_BUT_NOT_POLICY_ZERO_DEPLOYMENT
```

The current high cash is not explained by a runtime lifecycle defect, a hidden fixed cash reserve, or a Phase24-style Portfolio Policy zero-deployment override. Across all materialized completed days, Portfolio Policy allowed deployment every day:

```text
completed_business_days = 46
target_position_count zero days = 0
resolved_opportunity_capacity = 50 on 46 / 46 days
target_gross_exposure_ratio range = 0.74 to 1.00
```

The primary retained-cash source is upstream opportunity quality and executable allocation scarcity:

```text
BUY Quality decisions = 2,300
BUY Quality REJECT = 2,178
BUY Quality PASS = 122
Runtime BUY_NEW plans = 19
Runtime BUY_ADD plans = 0
BUY fills = 10
SELL fills = 16
```

L19 is active and helps when lots are executable, but it cannot force deployment after the eligible opportunity set is exhausted or when the minimum executable lot breaches the concentration boundary:

```text
L19 CAP_CONSTRAINED_LOT_EXECUTABLE = 20
L19 DISCRETE_LOT_EXCEEDS_STRATEGY_CAP_WITHIN_SAFETY_HARD_MAX = 22
L19 MINIMUM_EXECUTABLE_LOT_EXCEEDS_SAFETY_HARD_MAX = 17
EXHAUSTED_TO_CASH days = 18
```

Therefore the attribution is:

```text
Market context: MATERIAL SECONDARY
Portfolio Policy zero deployment: NOT OBSERVED
BUY Quality / opportunity supply: PRIMARY
Lot / concentration boundary: MATERIAL SECONDARY
ADD conversion: MATERIAL GAP, because no BUY_ADD runtime plan or fill was observed
Runtime lifecycle / submit / execution: NOT PRIMARY
```

## 2. Evidence Window

Run state at read time:

```text
status = RUNNING
next_job = 2022-10-19:market_refresh
completed_business_days = 46
first_completed_day = 2022-08-10
last_completed_day = 2022-10-18
halted_at = null
```

The user-provided snapshot was earlier than the latest materialized state inspected in this audit. This report uses only completed days present under the target run directory at read time.

## 3. Current Performance Snapshot

Latest direct valuation evidence:

```text
date = 2022-10-18
cash = 538,520 JPY
new_total_market_value = 458,420 JPY
reconstructed_total_equity = 996,940 JPY
cash_ratio = 54.02%
invested_ratio = 45.98%
position_count = 3
```

Run-to-date valuation pattern:

```text
average cash ratio = 60.22%
minimum cash ratio = 19.46%
maximum cash ratio = 86.71%
```

Monthly cash ratio:

| Month | Days | Average cash ratio | Last cash / market value / equity |
|---|---:|---:|---|
| 2022-08 | 15 | 73.14% | 521,920 / 469,920 / 991,840 |
| 2022-09 | 20 | 49.69% | 675,720 / 314,220 / 989,940 |
| 2022-10 | 11 | 61.74% | 538,520 / 458,420 / 996,940 |

## 4. Market Context Distribution

Trend regime distribution:

| Trend regime | Days |
|---|---:|
| BEAR | 12 |
| RANGE | 12 |
| BULL | 11 |
| RECOVERY | 6 |
| CORRECTION | 5 |

Breadth distribution:

| Breadth | Days |
|---|---:|
| WEAK | 20 |
| NEUTRAL | 20 |
| STRONG | 6 |

Volatility:

```text
NORMAL = 46 / 46 days
```

Month-level pattern:

| Month | Trend mix |
|---|---|
| 2022-08 | BULL 11, RECOVERY 2, RANGE 2 |
| 2022-09 | RANGE 6, BEAR 5, CORRECTION 5, RECOVERY 4 |
| 2022-10 | BEAR 7, RANGE 4 |

Answer:

```text
Was the period predominantly risk-off?
PARTIAL. September and October were materially risk-off, but August was mostly BULL/RECOVERY/RANGE.

Was cash retention consistent with Market Context?
PARTIAL. Higher October cash is consistent with BEAR/WEAK context, but August high cash cannot be attributed to risk-off context alone.

Did Market Context itself constrain capital materially?
YES as a secondary modifier, but not as a hard zero-deployment authority in this run.
```

## 5. Portfolio Policy Distribution

Policy distribution:

| Field | Distribution |
|---|---|
| `target_position_count` | 1: 21 days, 2: 8, 5: 6, 9: 5, 10: 6 |
| `target_gross_exposure_ratio` | 1.00: 25 days, 0.92: 4, 0.90: 1, 0.82: 4, 0.74: 12 |
| `resolved_opportunity_capacity` | 50 on 46 / 46 days |
| `risk_posture` | BALANCED on 46 / 46 days |
| `entry_posture` | MAINTAIN on 46 / 46 days |
| `deployment_posture` | DEPLOY 34 days, BALANCED_DEPLOYMENT 12 days |

Policy-low-deployment days:

```text
target_position_count <= 0 days = 0
target_gross_exposure_ratio < 0.50 days = 0
```

This differs from Phase24-B/C, where BEAR/WEAK drove `target_position_count = 0`. In L21A evidence, Policy generally allowed exposure and left downstream stages to decide whether quality, lot, concentration, and quantity conversion could actually deploy capital.

## 6. Opportunity Supply

BUY Quality observed 50 decisions per day:

```text
46 days * 50 = 2,300 decisions
```

Action distribution:

| Action | Count |
|---|---:|
| REJECT | 2,178 |
| REDUCED_ALLOCATION_ONLY | 86 |
| FULL_ALLOCATION_ELIGIBLE | 36 |

Band distribution:

| Band | Count |
|---|---:|
| UNUSABLE | 2,178 |
| MEDIUM | 63 |
| HIGH | 59 |

Top rejection drivers included:

```text
non_positive_or_missing_raw_opportunity_score = 2,156
below_opportunity_top20 / non_positive_expected_edge_score = 1,340
non_positive_expected_edge_score = 727
```

Conclusion:

```text
The canonical capacity field says 50 opportunities were inspectable every day,
but economically acceptable BUY Quality supply was thin.
```

## 7. BUY_NEW Funnel

Observed aggregate funnel:

| Stage | Count |
|---|---:|
| BUY Quality decisions | 2,300 |
| BUY Quality PASS | 122 |
| Positive target-weight members average | 2.85 per day |
| Runtime BUY_NEW plans | 19 |
| BUY fills | 10 |

BUY fills by day:

```text
2022-08-10 94320 BUY 900
2022-08-23 23880 BUY 1200
2022-08-26 93180 BUY 29900
2022-08-29 36600 BUY 300
2022-09-01 23880 BUY 1300
2022-09-05 37820 BUY 1700
2022-09-15 94340 BUY 1200
2022-09-26 96100 BUY 700
2022-09-26 41650 BUY 200
2022-10-12 65500 BUY 700
```

The gap is not that Policy refused all entries. The gap is that few candidates survived BUY Quality and then fewer survived executable quantity, concentration, and pending/CA continuation.

## 8. BUY_ADD Funnel

Runtime Planning observed:

```text
BUY_ADD plans = 0
BUY_ADD fills = 0
```

Position Sizing evidence still showed ADD-like candidates:

```text
lot_feasibility_preflight BUY_ADD = 22
positive quantity among ADD_CANDIDATE rows = 19
ADD_TARGET_WEIGHT_UNCHANGED zero reasons = 24
```

This is a material strategy attribution gap: existing-position ADD intent/candidate evidence is not converting into canonical Runtime BUY_ADD plans in this window. It should not be treated as a runtime execution failure because the final observed planning taxonomy contains no BUY_ADD plan.

## 9. L19 Lot Resolution Effect

L19 evidence is present in Portfolio Construction / Position Sizing:

| L19 classification | Count |
|---|---:|
| CAP_CONSTRAINED_LOT_EXECUTABLE | 20 |
| DISCRETE_LOT_EXCEEDS_STRATEGY_CAP_WITHIN_SAFETY_HARD_MAX | 22 |
| MINIMUM_EXECUTABLE_LOT_EXCEEDS_SAFETY_HARD_MAX | 17 |

Lot preflight:

| Classification | Count |
|---|---:|
| EXECUTABLE_NOW | 20 |
| CONCENTRATION_BLOCKED | 39 |

Interpretation:

```text
L19 is active and beneficial where executable.
It also makes the remaining cash reason explicit instead of silently losing capital.
It does not and should not override Strategy cap or Safety hard cap.
```

## 10. Residual Capital Reallocation Effect

Residual / exhaustion evidence:

| Field | Distribution |
|---|---:|
| `ALLOCATED_OR_NOT_APPLICABLE` | 28 days |
| `EXHAUSTED_TO_CASH` | 18 days |
| min L19 iterations | 0 |
| max L19 iterations | 4 |
| average L19 iterations | 1.28 |

Residual cash reasons:

| Reason | Count |
|---|---:|
| CONCENTRATION_LIMIT | 30 |
| NO_ELIGIBLE_OPPORTUNITY | 11 |
| COMPETITION_EXHAUSTED | 4 |
| CAPITAL_BELOW_NEXT_LOT | 1 |

Residual reallocation is therefore working as an evidence-producing allocator, but it often exhausts because the next deployable candidate is blocked or absent.

## 11. Cash Retention Attribution

Top attribution:

1. BUY Quality / opportunity supply: primary. 2,178 / 2,300 candidates were rejected.
2. Lot / concentration boundary: material. 39 preflight cases were concentration-blocked.
3. Market context: secondary. 17 / 46 days were BEAR or CORRECTION, 20 / 46 breadth WEAK.
4. ADD conversion: material gap. No Runtime BUY_ADD plans or fills were observed.
5. Runtime lifecycle: not primary. The run is currently RUNNING and progressed beyond prior L20H halt area.

## 12. L16 Guard Activation

The inspected evidence does not support L16 as the primary cause.

Observed:

```text
low_price_risk_allocation_authority.status = PASS on inspected BUY Quality/PC rows
liquidity_capacity_status commonly UNKNOWN, not an active cap
semantic reentry authority usually NOT_APPLICABLE for BUY_NEW rows
cooldown/recovery hurdle not the dominant zero-weight reason
```

Dominant zero-weight reasons were instead:

```text
buy_quality_rejected = 2,148 PC rows
minimum_lot_exceeds_concentration_cap = 17 PC rows
minimum_lot_exceeds_remaining_budget = 1 PC row
```

## 13. Compound Capital Verification

Position Sizing used the prior current/equity state, not a fixed 1,000,000 JPY evaluation capital after day 1:

| Date | Position Sizing equity | EOD reconstructed equity |
|---|---:|---:|
| 2022-08-10 | 1,000,000 | 1,000,540 |
| 2022-08-12 | 1,000,540 | 998,830 |
| 2022-08-15 | 998,830 | 999,550 |
| 2022-10-12 | 994,680 | 993,380 |
| 2022-10-13 | 993,380 | 987,340 |
| 2022-10-18 | 991,600 | 996,940 |

Portfolio Construction low-price allocation authority carried the same current authoritative equity as Position Sizing on sampled dates. No evidence was found that downstream sizing used fixed initial capital as current capital.

## 14. Legacy Constraint Regression Check

No evidence was found for the old fixed cash reserve / fixed exposure ceiling path:

```text
minimum_cash_ratio = 0.0
maximum_cash_ratio = 1.0
maximum_gross_exposure_ratio = 1.0
target_gross_exposure_ratio = 1.0 on 25 / 46 days
legacy_authority_active did not explain the observed retention
```

The observed cap bottleneck is single-name Strategy/Safety concentration and lot granularity, not the removed fixed cash reserve.

## 15. Market vs Strategy Attribution

```text
Market-only explanation: NO
Strategy/downstream-only explanation: NO
Mixed attribution: YES
```

August had mostly favorable Market Context but still high cash early because only one or two names survived BUY Quality and lot boundaries. September/October had more risk-off context, but Policy still allowed deployment and the remaining gap came from candidate quality, concentration, SELL churn, and missing BUY_ADD conversion.

## 16. Top 5 Root Causes

1. Thin BUY Quality pass-through: only 122 / 2,300 decisions passed.
2. Non-positive expected edge / below-top20 rejection dominated rejected supply.
3. Lot and concentration boundary blocked 39 lot-preflight cases.
4. Runtime BUY_ADD conversion was absent despite ADD-like preflight evidence.
5. Market Context turned materially weaker in September/October, reducing natural deployment pressure but not creating zero capacity.

## 17. Evidence Gaps

Evidence gaps that remain read-only:

```text
BUY_ADD semantic bridge needs a focused trace from PM decision -> PC target increase -> PS quantity -> Runtime Planning.
Some submitted/pending evidence is plan-level and not a clean count of actually submitted BUY_NEW vs no-order candidates.
The audit reconstructs equity as cash + new_total_market_value because valuation_projection does not expose total_equity directly.
```

These gaps do not invalidate the primary judgment because the dominant counts are visible in Strategy and Execution evidence.

## 18. Strategy Regression Assessment

Regression is not proven.

L19/L20H did not create the high-cash pattern. L19 makes lot-boundary retention explicit and sometimes executable. L20H is order lifecycle authority and the run has continued beyond 2022-09-30 into 2022-10-18. The remaining issue is performance/strategy attribution, especially BUY Quality scarcity and ADD conversion.

## 19. Current Run Mutation

```text
NO
```

This audit used read-only inspection only.

## 20. Long Historical Executed

```text
NO
```

No `resume`, `fresh-run`, `pending_lifecycle`, `morning`, `sell_planning`, `submit`, `execution`, `repair`, or long Historical command was executed.

## 21. Recommended Next Task

Recommended next task:

```text
Phase29-L21B - BUY_ADD Canonical Conversion Trace Audit
```

Scope:

```text
READ-ONLY first.
Trace PM ADD / ADD_CANDIDATE / lot preflight positive quantity evidence into
Portfolio Construction target-weight authority, Position Sizing quantity,
Runtime Planning BUY_ADD taxonomy, Pending generation, Submit, and Execution.
```

Reason:

```text
L21A shows BUY_NEW is sparse but functioning.
The clearest unresolved deployment gap is that ADD-like evidence exists while Runtime BUY_ADD plans remain zero.
```
