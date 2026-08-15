# Phase29-L21T-D - Post-L21T-C Capital Utilization / Compounding Effect Attribution

Task ID: `Phase29-L21T-D`

Mode: READ-ONLY audit. No implementation, config, threshold, schema, Runtime/Pending mutation, fresh-run, resume, long Historical run, Production fail-closed relaxation, Historical-only Strategy path, model change, Buy Quality change, REENTRY redesign, or Corporate Action policy change was performed.

## Primary Judgment

`PHASE29_L21T_D_CAPITAL_UTILIZATION_IMPROVED_RESIDUAL_DEPLOYMENT_GAPS_REMAIN`

More precise sub-judgment:

```text
DISCRETE_QUANTITY_REPAIR_CONFIRMED
PS_RP_PLANNING_CONVERSION_IMPROVED
VALUATION_LEVEL_CAPITAL_UTILIZATION_UNCHANGED_DUE_TO_DOWNSTREAM_PENDING_SUBMIT_EXECUTION_GAP
COMPOUNDING_MECHANICS_CONFIRMED
L21T_E_REQUIRED
```

## Scope

Compared runs:

| Run | ID | Window | Initial cash | Status |
|---|---|---:|---:|---|
| Before | `runtime-test-historical-smoke-20260812T015430837714Z` | 2022-08-23 to 2022-09-16 | 1,000,000 JPY | REVIEW_REQUIRED |
| After | `runtime-test-historical-smoke-20260812T023424133327Z` | 2022-08-23 to 2022-09-16 | 1,000,000 JPY | REVIEW_REQUIRED |

Both runs completed all 19 requested business days.

## Audit A - 78780 Materialization

After run evidence for `2022-08-24 / 78780`:

| Layer | Evidence |
|---|---|
| PC target | `target_weight=0.243189` |
| PC one lot | `one_lot_quantity=100`, `one_lot_notional=242000.0` |
| PC feasibility | `one_lot_feasibility_status=PASS` |
| Strategy overshoot | `strategy_cap_overshoot_applied=true` |
| Safety hard cap | `safety_hard_cap_weight=0.25`, `safety_margin_after_trade=0.006811` |
| PS continuous notional | `target_notional=241999.81` |
| PS discrete quantity | `target_quantity_candidate=100`, `quantity_delta_candidate=100` |
| PS authority | `discrete_authorized_quantity=100`, `one_lot_authority_consumed=true` |
| RP | `planning_intent=BUY_NEW`, `planned_quantity=100`, `quantity_status=RESOLVED_EXECUTABLE` |
| Strategy Planning Authority | `status=PASS`, `pending_item_count=1`, `pending_commit_status=COMMITTED_CURRENT` |

Result:

```text
L21T-C discrete quantity repair effective = YES
78780 one-lot quantity materialized = YES
Regression condition target positive + one-lot PASS + PS/RP zero = NOT PRESENT
```

## Audit B - Buy Conversion Funnel

| Metric | Before | After | Delta |
|---|---:|---:|---:|
| PC positive target count | 65 | 65 | 0 |
| PS positive quantity count | 10 | 12 | +2 |
| Runtime BUY_NEW count | 7 | 8 | +1 |
| Runtime BUY_ADD count | 3 | 4 | +1 |
| Runtime REENTRY count | 0 | 0 | 0 |
| BUY fill count | 10 | 10 | 0 |
| All fill count | 22 | 22 | 0 |
| Runtime BUY planned notional | 1,023,860 JPY | 1,281,370 JPY | +257,510 JPY |
| Runtime BUY_NEW planned notional | 969,050 JPY | 1,211,050 JPY | +242,000 JPY |
| Runtime BUY_ADD planned notional | 54,810 JPY | 70,320 JPY | +15,510 JPY |
| REENTRY planned notional | 0 JPY | 0 JPY | 0 |
| Positive target zero PS quantity | 55 | 53 | -2 |
| one-lot fallback count | 3 | 3 | 0 |
| one-lot fallback positive quantity | 1 | 3 | +2 |
| Strategy soft-cap one-lot overshoot count | 3 | 3 | 0 |
| Safety hard-cap blocked count | 5 | 5 | 0 |
| minimum meaningful diagnostic count | 2 | 2 | 0 |

The intended L21T-C effect is visible at PS/RP:

- `78780 / 2022-08-24` moved from zero to `BUY_NEW 100`.
- `94320 / 2022-09-14` moved from zero to `BUY_ADD 100`.
- Existing `94320 / 2022-09-15` remained positive.

## Audit C - Capital Utilization

Valuation-level invested ratio was unchanged between Before and After:

| Metric | Before | After | Delta |
|---|---:|---:|---:|
| Average invested ratio | 43.51% | 43.51% | 0.00pp |
| Median invested ratio | 40.29% | 40.29% | 0.00pp |
| Min invested ratio | 30.73% | 30.73% | 0.00pp |
| Max invested ratio | 65.05% | 65.05% | 0.00pp |
| Final invested ratio | 56.83% | 56.83% | 0.00pp |
| Average cash ratio | 56.49% | 56.49% | 0.00pp |
| Final cash ratio | 43.17% | 43.17% | 0.00pp |

Interpretation:

L21T-C improved Strategy-to-Planning conversion, but the fresh run's valuation/cash/equity path did not reflect the additional planned orders as additional executed holdings. Therefore capital utilization did not improve at the run-level invested-ratio metric.

This is not an 80% target failure. It is a downstream execution-materialization / pending handoff attribution gap for newly recovered orders.

## Audit D - Residual Cash Root Cause

After run zero / residual explanation buckets across PC members and downstream positive-target rows:

| Bucket | Count |
|---|---:|
| NO_ELIGIBLE_OPPORTUNITY | 723 |
| BUY_QUALITY_REJECT | 150 |
| REENTRY_GUARD | 7 |
| SAFETY_HARD_CAP | 5 |
| OTHER_EXPLAINED | 3 |
| POSITIVE_TARGET_ZERO_PS | 0 |
| POSITIVE_PS_ZERO_RUNTIME | 0 |
| UNEXPLAINED | 0 |

Required special filter:

```text
PC positive target > 0
+ one lot feasible
+ Safety within 25%
+ BQ/REENTRY/CA not blocking
+ final planned_quantity = 0
```

After result:

```text
PS/RP-level lost count = 0
```

However, a later boundary still matters:

```text
2022-08-24 / 78780:
Morning pending_generation_evidence = PASS, pending_item_count=1
Submit runtime_manifest = pending_classification=EMPTY, pending_item_count=0
Execution pending_terminalization = EMPTY / ALREADY_TERMINAL
fills = []
```

This is not an L21T-C PS/RP regression. It is a Planning/Pending-to-Submit/Execution continuity gap and is the strongest L21T-E candidate.

## Audit E - Compounding Mechanics

Compounding mechanics are confirmed.

Position Sizing uses current equity as allocation base, not the fixed `initial_cash=1,000,000` every day. Daily checks:

| Date | Previous end equity | PS portfolio_value | Difference |
|---|---:|---:|---:|
| 2022-08-24 | 995,110 | 995,110 | 0 |
| 2022-08-25 | 989,950 | 989,950 | 0 |
| 2022-08-31 | 990,040 | 990,040 | 0 |
| 2022-09-08 | 975,320 | 975,320 | 0 |
| 2022-09-14 | 997,910 | 997,910 | 0 |
| 2022-09-15 | 1,002,170 | 1,002,170 | 0 |
| 2022-09-16 | 1,003,370 | 1,003,370 | 0 |

Case traces:

| Case | Previous/current capital base | Target | Quantity |
|---|---:|---:|---:|
| BUY after loss, `2022-08-24 / 78780` | 995,110 | `target_weight=0.243189`, `target_notional=241999.81` | planned 100 |
| ADD after current base, `2022-08-31 / 94320` | 990,040 | `target_weight=0.18`, `target_notional=178207.20` | planned 200 |
| ADD after equity increase, `2022-09-15 / 94320` | 1,002,170 | `target_weight=0.185658`, `target_notional=186060.88` | planned 100 |

Conclusion:

```text
Current equity is allocation authority = YES
Daily compounding chain = CONFIRMED
Stale initial capital authority in PS/PC allocation base = NOT FOUND
```

## Audit F - Winner ADD / Capital Recycling

BUY_ADD improved at PS/RP:

| Metric | Before | After | Delta |
|---|---:|---:|---:|
| Runtime BUY_ADD count | 3 | 4 | +1 |
| Runtime BUY_ADD planned notional | 54,810 JPY | 70,320 JPY | +15,510 JPY |
| one-lot BUY_ADD fallback positive | 1/2 | 2/2 | +1 |

The key repaired case is:

```text
2022-09-14 / 94320
semantic_buy_type=BUY_ADD
one_lot_quantity=100
PS quantity_delta_candidate=100
RP planning_intent=BUY_ADD
planned_quantity=100
```

Winner ADD capital recycling is functioning through PS/RP. Run-level cash did not improve because valuation-level fills did not increase over Before.

## Audit G - Profit / Return Sanity

After run valuation/equity metrics:

| Metric | Value |
|---|---:|
| Initial equity | 1,000,000 JPY |
| Final equity | 986,550 JPY |
| Total return | -1.345% |
| Max equity | 1,003,370 JPY |
| Min equity | 975,320 JPY |
| Approx max drawdown | -2.071% |
| BUY fill count | 10 |
| BUY fill notional | same as Before at executed-fill level |

Performance sanity check:

```text
No abnormal performance degradation attributable to L21T-C is established.
No performance optimization judgment should be made from this 19BD window.
78780 future movement was not used to judge L21T-C correctness.
```

## Audit H - REVIEW_REQUIRED Close Reason

After `final_summary.json` classifies close as:

```text
close_authority_judgment = REVIEW_REQUIRED
final_runtime_judgment = PASS
runtime_execution_judgment = PASS
trading_state_judgment = PASS
accounting_state_judgment = PASS
block_rule = NO_BLOCKING_CLOSE_RULE_TRIGGERED
review_reasons = ['strategy_shadow_review_required_non_blocking']
strategy_shadow_close_classification = NON_MUTATING_STRATEGY_SHADOW_REVIEW_NON_BLOCKING
```

Review-required dates:

```text
2022-08-30
2022-09-07
2022-09-12
```

Classification:

```text
Model / Strategy Shadow review-only
```

This close status is not causal to L21T-C capital deployment. The run completed all 19 days and runtime execution judgment is PASS.

## Required Judgment Answers

| Question | Judgment |
|---|---|
| L21T-C discrete quantity repair effective? | YES |
| 78780 one-lot quantity materialized? | YES |
| one-lot positive conversion improved? | YES, 1/3 to 3/3 |
| Capital utilization improved? | NO at valuation-level invested ratio |
| Residual cash fully explained? | YES at PC/PS/RP level; downstream pending/submit gap remains |
| Positive executable opportunities still lost? | YES, after RP: 78780 pending generated but submit/execution saw EMPTY |
| Compounding mechanics confirmed? | YES |
| Current equity is allocation authority? | YES |
| Winner ADD capital recycling functioning? | YES through PS/RP |
| Performance sanity check passed? | YES |
| REVIEW_REQUIRED causal to capital deployment? | NO |
| Further implementation required? | YES, if run-level capital utilization improvement is required |
| L21T-E required? | YES |
| 100BD validation ready? | NO, not until Planning/Pending-to-Submit/Execution continuity is reconciled |

## L21T-E Recommendation

Recommended next task:

```text
Phase29-L21T-E - Pending/Submit/Execution Continuity for Newly Materialized One-Lot Orders
```

Focused root case:

```text
2022-08-24 / 78780
Strategy Planning Authority PASS, pending_item_count=1
pending_generation_evidence pending_path_written=true
submit runtime_manifest pending_classification=EMPTY, pending_item_count=0
execution fills=[]
```

This should be audited before a 100BD validation, because otherwise the repaired PS/RP quantity can be real in planning evidence but absent from executed capital deployment.
