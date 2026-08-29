# Phase32-BN Post-BL Fresh Zero-Buy Actual-Path Delta Audit

## Executive Summary

The Phase32-BN actual fresh artifact does not reproduce the Phase32-BK
cash/budget-notional defect.

For `2022-10-03`, the active BG authority now resolves:

```text
starting_cash_notional = 1000000.0
available_incremental_budget_weight = 0.74
available_incremental_budget_notional = 740000.0
authority accepted_target_count = 20
BF aggregated_ps_target_count = 20
PS nonzero final_quantity_delta rows = 11
Runtime executable BUY_NEW plans = 11
Planning pending_item_count = 11
```

Therefore the BL cash resolver repair is active on the actual fresh path.

The fresh run still ends day 0 with zero fills because all 11 executable BUY
plans are converted into review-required pending items before submit:

```text
source_submit_feasibility_status = REVIEW_REQUIRED
reason = pc_discrete_quantity_authority_future_information_flag_invalid
decision = INCLUDE_REVIEW_REQUIRED
```

The first divergence from the BL in-memory reproduction is after BF and PS, at:

```text
Runtime Planning -> Strategy Planning Pending Batch Submit-Feasibility
```

Exact root cause:

```text
BF/BG PS rows materialize a
PORTFOLIO_CONSTRUCTION_DISCRETE_EXECUTABLE_QUANTITY_AUTHORITY with status PASS
and quantity 100, but the nested authority payload omits future_information_used=false.
planning_submit_feasibility._canonical_discrete_quantity_submit_authority()
requires that field to be explicitly false, so every otherwise executable BUY
item becomes REVIEW_REQUIRED and no order is submitted.
```

This is not a legitimate Cash/no-deployment decision, not the BK
weight-as-notional bug, and not a stale alternate cash resolver.

## Run Identity

| Field | Value |
| --- | --- |
| Target run id | `runtime-test-historical-extended-smoke-20260828T155631867966Z` |
| Target date | `2022-10-03` |
| Evidence path | `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260828T155631867966Z` |
| Audit mode | READ-ONLY artifact trace |
| Production changes | None |
| Fresh/resume/replay/backtest | Not executed |

Run summary artifacts show `2022-10-03` completed, then the run was later
interrupted:

```text
fresh_run_summary.status = HALT
fresh_run_summary.completed_days = ["2022-10-03"]
fresh_run_summary.exit_code = 130
fresh_run_summary.error = fresh-run interrupted by operator
```

## BL vs BN Delta

| Boundary | BL in-memory BK reproduction | BN actual fresh artifact |
| --- | ---: | ---: |
| `starting_cash_notional` | `1000000.0` | `1000000.0` |
| `available_incremental_budget_weight` | `0.74` | `0.74` |
| `available_incremental_budget_notional` | `740000.0` | `740000.0` |
| Authority accepted security targets | `20` | `20` |
| BF aggregated PS targets | `20` | `20` |
| PS nonzero quantity rows | fixture-confirmed `>0` | `11` |
| Runtime executable BUY plans | not covered by BL reproduction | `11` |
| Planning pending items | not covered by BL reproduction | `11`, all `INCLUDE_REVIEW_REQUIRED` |
| Submitted orders | not covered by BL reproduction | `0` |
| Fills | not covered by BL reproduction | `0` |

The first actual-path divergence from the BL reproduction scope is not Cash,
authority generation, BF aggregation, or PS consumption. It is the next
submit-feasibility contract used while constructing the pending batch.

## Cash Payload / Resolver Trace

Decision-time Cash evidence exists in both runtime valuation and Portfolio
Policy artifacts.

| Artifact | Field | Value |
| --- | --- | ---: |
| `current_valuation_refresh/valuation_projection.json` | `cash` | `1000000.0` |
| `current_valuation_refresh/valuation_projection.json` | `buying_power` | `1000000.0` |
| `strategy/portfolio_policy.json` | `incremental_capital_budget_envelope.available_cash_context.cash_available` | `1000000.0` |
| `strategy/portfolio_policy.json` | `incremental_capital_budget_envelope.cash_context.cash_available` | `1000000.0` |
| `strategy/portfolio_policy.json` | `incremental_capital_budget_envelope.cash_context.net_available_cash` | `1000000.0` |

The actual authority artifact records:

```text
artifact_mode = PRODUCTION_PC_TO_PS_CONSUMER_ENABLED
production_consumer_enabled = true
production_consumer_count = 1
feeds_position_sizing = true
cash_source_status = PASS
source_artifacts.cash = runtime_current_asset_snapshot
```

The artifact does not preserve a detailed `cash_source_lineage` row, but the
materialized values prove the repaired resolver was used:

```text
starting_cash_notional = 1000000.0
available_incremental_budget_notional = 740000.0
```

The stale BK failure values are absent:

```text
starting_cash_notional != 0.74
available_incremental_budget_notional != 0.74
```

## Authority / BF / PS Trace

Authority:

```text
schema_version = canonical_marginal_capital_frontier_authority.v1
status = PASS
candidate_count_total = 51
candidate_count_by_type = NEW_FIRST_LOT: 50, CASH_OPTIONALITY: 1
accepted_target_count = 20
review_reasons = []
```

Budget:

```text
budget_source_role = portfolio_construction.available_incremental_budget
available_incremental_budget_weight = 0.74
available_incremental_budget_notional = 740000.0
portfolio_value_basis = 1000000.0
starting_cash_notional = 1000000.0
```

BF boundary:

```text
status = PASS
accepted_incremental_target_count = 20
aggregated_ps_target_count = 20
production_consumer_enabled = true
feeds_position_sizing = true
legacy_target_gap_input_used = false
legacy_target_gap_fallback_allowed = false
legacy_zero_fallback_allowed = false
```

Position Sizing:

```text
producer_result_status = PASS
production_consumer_connected = true
legacy_authority_active = false
accepted_boundary_target_count = 20
consumed_position_count = 11
nonzero final_quantity_delta rows = 11
quantity_status = RESOLVED_CANDIDATE: 11, RESOLVED_ZERO_DELTA: 39
```

Representative selected PS rows:

| Symbol | Target weight | Final quantity delta | Status |
| --- | ---: | ---: | --- |
| `94340` | `0.01441` | `100` | `RESOLVED_CANDIDATE` |
| `37820` | `0.0068` | `100` | `RESOLVED_CANDIDATE` |
| `33700` | `0.0341` | `100` | `RESOLVED_CANDIDATE` |
| `83060` | `0.0648` | `100` | `RESOLVED_CANDIDATE` |
| `41920` | accepted by BG/BF | `100` | `RESOLVED_CANDIDATE` |
| `89180` | accepted by BG/BF | `100` | `RESOLVED_CANDIDATE` |
| `76470` | accepted by BG/BF | `100` | `RESOLVED_CANDIDATE` |
| `45750` | accepted by BG/BF | `100` | `RESOLVED_CANDIDATE` |
| `33500` | accepted by BG/BF | `100` | `RESOLVED_CANDIDATE` |
| `82540` | accepted by BG/BF | `100` | `RESOLVED_CANDIDATE` |
| `67860` | accepted by BG/BF | `100` | `RESOLVED_CANDIDATE` |

## Runtime / Pending / Submit Trace

Runtime Planning:

```text
producer_result_status = PASS
plan_count = 22
quantity_status = RESOLVED_EXECUTABLE: 11, RESOLVED_ZERO_DELTA: 11
reason_codes include position_sizing_positive_quantity_delta_maps_to_buy_new
```

Morning planning:

```text
status = PASS
plan_count = 22
pending_item_count = 11
pending_path_written = true
atomic_commit_decision = COMMIT
broker_write_allowed = false
broker_write_performed = false
```

Pending batch evidence:

```text
candidate_buy_count = 11
included_buy_count = 0
cash_pruned_count = 0
final_reserved_notional_total = 0.0
decision = INCLUDE_REVIEW_REQUIRED: 11
source_submit_feasibility_status = REVIEW_REQUIRED: 11
source_violated_policy = position_sizing: 11
reason = pc_discrete_quantity_authority_future_information_flag_invalid: 11
```

Submit / execution:

```text
submitted_order_authority.status = PASS
submitted_order_authority.reason = no_submitted_orders
submit_action = NO_SUBMISSION_REQUIRED
execution_action = NO_ACTION
orders_count = 0
submitted_order_count = 0
historical_fill_authority.fill_count = 0
```

Pending lifecycle then expires the review-required pending plan:

```text
pending_lifecycle_requirement.status = PENDING_LIFECYCLE_REQUIRED
pending_lifecycle_requirement.pending_item_count = 11
pending_lifecycle_result.previous_state = REVIEW_REQUIRED
pending_lifecycle_result.new_state = EXPIRED
pending_post_state.state = EMPTY
```

## Exact Failing Contract

The failing contract is:

```text
runtime_v2.planning_submit_feasibility._canonical_discrete_quantity_submit_authority
```

It requires the nested
`pc_positive_executable_quantity_authority.future_information_used` value to be
explicitly `false`.

The actual PS row contains the BG/BF quantity authority:

```text
phase29_l19_lot_resolution.authority_type =
  PHASE32_BG_BF_AGGREGATED_TARGET_LOT_RESOLUTION

phase29_l19_lot_resolution.pc_positive_executable_quantity_authority = {
  authority_type: PORTFOLIO_CONSTRUCTION_DISCRETE_EXECUTABLE_QUANTITY_AUTHORITY,
  status: PASS,
  discrete_authorized_quantity: 100,
  final_allocated_quantity: 100,
  final_target_quantity: 100,
  ps_must_consume_canonical_quantity: true,
  semantic_type: BUY_NEW,
  legacy_target_gap_fallback_allowed: false,
  legacy_zero_fallback_allowed: false
}
```

But the same nested authority omits:

```text
future_information_used = false
historical_outcome_used = false
```

Because the field is missing, the submit-feasibility function returns:

```text
status = REVIEW_REQUIRED
reason = pc_discrete_quantity_authority_future_information_flag_invalid
```

for every one of the 11 nonzero BUY items.

## Defect Classification

| Candidate cause | Judgment | Evidence |
| --- | --- | --- |
| BL cash resolver inactive | No | Actual authority has `starting_cash_notional=1000000.0` and `budget_notional=740000.0`. |
| Nested runtime Cash not passed | No | Authority source is `runtime_current_asset_snapshot`; Cash status is `PASS`; values are corrected. |
| Stale alternate cash resolver | No | BK `0.74` Cash-notional collapse is absent. |
| Authority materialization zero | No | Authority accepts 20 targets. |
| BF aggregation zero | No | BF emits 20 aggregated PS targets. |
| PS consumer defect / zero quantity | No | PS consumes BG authority and emits 11 nonzero quantity deltas. |
| Runtime mapping zero | No | Runtime emits 11 `RESOLVED_EXECUTABLE` BUY_NEW plans. |
| Planning submit-feasibility review defect | Yes | All 11 pending items are `INCLUDE_REVIEW_REQUIRED` due missing explicit PIT flag in nested PC quantity authority. |
| Legitimate Cash/no-deployment | No | Cash and budget are sufficient, and no item was cash-pruned. |

## Repair Readiness

Repair should stay narrow:

```text
Materialize explicit PIT/provenance flags on the BF/BG
pc_positive_executable_quantity_authority payload consumed by
planning_submit_feasibility.
```

Minimum expected fields:

```text
future_information_used = false
historical_outcome_used = false
```

The repair should not change:

```text
Cash resolver
allocation budget
marginal value weights / thresholds
PM
PS quantity arithmetic
Runtime mapping
REDUCE / EXIT
Risk Pacing
legacy fallback policy
```

After repair, the same `2022-10-03` focused reproduction should show:

```text
source_submit_feasibility_status = PASS
decision = INCLUDE
included_buy_count > 0
submitted/fill path eligible in a user-operated fresh validation
```

## Final Judgments

```text
PHASE32_BN_ZERO_BUY_REGRESSION = YES
PHASE32_BN_BL_REPAIR_ACTIVE_ON_ACTUAL_PATH = YES
PHASE32_BN_ACTUAL_CASH_SOURCE_PATH = runtime_current_asset_snapshot
PHASE32_BN_ACTUAL_STARTING_CASH_NOTIONAL = 1000000.0
PHASE32_BN_ACTUAL_BUDGET_NOTIONAL = 740000.0
PHASE32_BN_FIRST_BL_REPRODUCTION_DIVERGENCE_STAGE = RUNTIME_PLANNING_TO_STRATEGY_PLANNING_PENDING_BATCH_SUBMIT_FEASIBILITY
PHASE32_BN_EXACT_ROOT_CAUSE = BF/BG pc_positive_executable_quantity_authority omits explicit future_information_used=false, so planning_submit_feasibility marks all 11 executable BUY items REVIEW_REQUIRED with pc_discrete_quantity_authority_future_information_flag_invalid; submit then has no submitted orders.
PHASE32_BN_REPAIR_REQUIRED = YES
PHASE32_BN_LONGER_VALIDATION_READY = NO
PHASE32_BN_NEXT_STEP = Narrow Phase32-BO repair to materialize explicit PIT/provenance flags on the BF/BG PC discrete executable quantity authority payload, then rerun focused non-fresh reproduction and user-operated short fresh validation.
```
