# Phase32-BQ Post-BO 2022-10-11 Morning HALT Exact Trace

## Executive Summary

Run `runtime-test-historical-extended-smoke-20260828T161503510098Z` completed
`2022-10-03` through `2022-10-07`, then halted at `2022-10-11:morning`.

The HALT was caused by morning review-required handling:

```text
morning/cli_result.exit_code = 20
morning/runtime_manifest.reason =
  morning pipeline review required: strategy_planning_authority_unresolved
```

The first failing strategy boundary is:

```text
canonical_marginal_capital_frontier_authority.v1
-> pc_to_ps_consumer_switch_boundary
```

Core marginal authority, Cash, budget, and capital conservation are healthy on
`2022-10-11`:

```text
authority_result.status = PASS
authority_result.accepted_target_count = 7
starting_cash_notional = 247220.0
available_incremental_budget_notional = 116238.724159
capital_conservation.status = PASS
```

But BF/PC-to-PS aggregation fails closed:

```text
pc_to_ps_consumer_switch_boundary.status = REVIEW_REQUIRED
pc_to_ps_consumer_switch_boundary.review_reasons = [bf_pc_to_ps_boundary_not_pass]
aggregated_ps_target_count = 0
production_consumer_enabled = false
```

Position Sizing then correctly refuses legacy fallback:

```text
producer_result_status = REVIEW_REQUIRED
reason_codes =
  BG_BF_BOUNDARY_NOT_PASS
  BG_MARGINAL_CAPITAL_AUTHORITY_CONSUMER_NOT_ENABLED
  BG_PRODUCTION_CONSUMER_SWITCH_NOT_PASS
legacy_zero_fallback_used = false
```

Exact underlying BF predicate, verified by read-only re-validating the saved
authority payload with the current validator:

```text
ps_final_quantity_delta_inconsistent
```

The failed target is the `94340` multi-lot ADD sequence. On `2022-10-11`, three
accepted ADD lots each carry `accepted_incremental_quantity=200`, but the
hypothetical repeated-lot pre-state advances by only one `trading_unit=100`.
Aggregating those rows gives:

```text
current_quantity = 700
sum(accepted_incremental_quantity) = 600
last target_quantity = 1100
700 + 600 != 1100
```

This is not the Phase32-BO PIT flag regression. It is a separate ADD multi-lot
quantity materialization inconsistency exposed by the active BG/BF production
consumer boundary.

## Run Identity

| Field | Value |
| --- | --- |
| Run id | `runtime-test-historical-extended-smoke-20260828T161503510098Z` |
| Evidence path | `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260828T161503510098Z` |
| Completed days | `2022-10-03`, `2022-10-04`, `2022-10-05`, `2022-10-06`, `2022-10-07` |
| Halt point | `2022-10-11:morning` |
| CLI exit | `20` |
| Fresh summary error | `Runtime CLI stopped at 2022-10-11:morning with exit code 20` |
| Audit mode | READ-ONLY artifact trace |
| Production changes | None |
| Resume/replay/fresh-run/backtest | Not executed |

## 10/11 Stage Trace

| Stage | Artifact | Status | Evidence |
| --- | --- | --- | --- |
| Strategy / PC | `strategy/portfolio_construction.json` | Produced | Includes `94340` ADD, NEW candidates, and current holdings. |
| Marginal authority | `strategy/marginal_capital_frontier_authority.json#authority_result` | `PASS` | `candidate_count_total=46`; accepted targets `7`: ADD `3`, NEW `4`. |
| Cash / budget | `allocation_budget_authority` | `PASS` | Cash `247220.0`; budget weight `0.114583`; budget notional `116238.724159`. |
| Capital conservation | `capital_conservation` | `PASS` | Security allocation `112270.0`; residual Cash allocation `3968.724159`. |
| BF boundary | `pc_to_ps_consumer_switch_boundary` | `REVIEW_REQUIRED` | `bf_pc_to_ps_boundary_not_pass`; `aggregated_ps_target_count=0`. |
| Production switch | `production_consumer_switch` | `REVIEW_REQUIRED` | `bf_only_target_authority=false`; `production_consumer_enabled=false`. |
| Position Sizing | `strategy/position_sizing.json` | `REVIEW_REQUIRED` | All `52` rows `UPSTREAM_REVIEW_REQUIRED`; no legacy fallback. |
| Runtime Planning | `strategy/runtime_planning.json` | `REVIEW_REQUIRED` | `23` plans `REVIEW_REQUIRED_AUTHORITY_UNRESOLVED`; `5` plans `NOT_REQUIRED`. |
| Morning planning | `morning/planning_evidence.json` | `REVIEW_REQUIRED` | `strategy_planning_authority_unresolved`; `pending_item_count=0`. |
| Pending | `morning/pending_generation_evidence.json` | `REVIEW_REQUIRED` | Pending path written, but no executable pending items. |
| Submit / Safety | Not reached in daily artifacts | N/A | Halt occurs at morning due `--stop-on-review-required`. |

## Authority / Target Counts

`2022-10-11` marginal authority:

```text
authority_result.status = PASS
candidate_count_by_type =
  ADD_NEXT_LOT: 3
  CASH_OPTIONALITY: 1
  NEW_FIRST_LOT: 29
  REENTRY_FIRST_LOT: 13
accepted_target_count = 7
accepted targets =
  ADD_NEXT_LOT: 3
  NEW_FIRST_LOT: 4
```

Accepted targets:

| Symbol | Type | Lot index | Accepted qty | Pre qty | Target qty | Notional |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `94340` | `ADD_NEXT_LOT` | 1 | 200 | 700 | 900 | 29160.0 |
| `94340` | `ADD_NEXT_LOT` | 2 | 200 | 800 | 1000 | 29160.0 |
| `94340` | `ADD_NEXT_LOT` | 3 | 200 | 900 | 1100 | 29160.0 |
| `76920` | `NEW_FIRST_LOT` | 1 | 100 | 0 | 100 | 13330.0 |
| `33580` | `NEW_FIRST_LOT` | 1 | 100 | 0 | 100 | 8960.0 |
| `17570` | `NEW_FIRST_LOT` | 1 | 100 | 0 | 100 | 2100.0 |
| `93180` | `NEW_FIRST_LOT` | 1 | 100 | 0 | 100 | 400.0 |

The ADD rows are internally inconsistent as an aggregated net target:

```text
first pre_quantity = 700
sum accepted_incremental_quantity = 200 + 200 + 200 = 600
last target_quantity = 1100
expected final target by BF contract = 700 + 600 = 1300
actual last target_quantity = 1100
```

The common frontier had enough Cash and budget. The block is not an
insufficient Cash decision.

## Comparison To Completed Days

| Day | Authority targets | ADD targets | BF status | BF targets | PS status | Pending items | Submit |
| --- | ---: | ---: | --- | ---: | --- | ---: | --- |
| `2022-10-03` | 20 | 0 | `PASS` | 20 | `PASS` | 11 | 11 submitted |
| `2022-10-04` | 10 | 0 | `PASS` | 10 | `PASS` | 10 | 10 submitted |
| `2022-10-05` | 9 | 3 | `PASS` | 7 | `PASS` | 11 | 9 submitted |
| `2022-10-06` | 9 | 3 | `PASS` | 7 | `PASS` | 8 | 8 submitted |
| `2022-10-07` | 9 | 6 | `PASS` | 5 | `PASS` | 6 | 4 submitted |
| `2022-10-11` | 7 | 3 | `REVIEW_REQUIRED` | 0 | `REVIEW_REQUIRED` | 0 | not reached |

The first material difference is the `94340` ADD lot quantity source.

Prior successful ADD days:

```text
2022-10-05 94340 ADD lots: accepted_incremental_quantity = 100 each
2022-10-06 94340 ADD lots: accepted_incremental_quantity = 100 each
2022-10-07 94340 ADD lots: accepted_incremental_quantity = 100 each
```

On `2022-10-11`:

```text
portfolio_construction.94340 current_quantity = 700
position_sizing_preflight.94340 transaction_quantity_candidate = 200
trading_unit = 100
```

The ADD candidate generator uses the PS preflight `transaction_quantity_candidate`
as each marginal candidate's `increment_quantity`, while repeated-lot
`pre_quantity` advances by one `trading_unit` per lot:

```text
increment_quantity = ps_row.transaction_quantity_candidate = 200
pre_quantity sequence = 700, 800, 900
post_quantity sequence = 900, 1000, 1100
```

This creates a non-additive sequence for BF net quantity aggregation.

## BO Provenance Check

The BO `future_information_used=false` repair is not the 10/11 blocker.

Evidence:

```text
2022-10-03 through 2022-10-07 selected switched PS rows contain
future_information_used=false and pass through submit-feasibility.

2022-10-11 has no switched PS rows because BF activation fails first.
pc_discrete_quantity_authority_future_information_flag_invalid count = 0
```

Thus Phase32-BO did not regress. The new blocker is a separate multi-lot ADD
quantity consistency defect in the marginal frontier / BF boundary path.

## Review / Halt Source

Stored artifact chain:

```text
marginal_capital_frontier_authority.review_reasons =
  [bf_pc_to_ps_boundary_not_pass]

position_sizing.reason_codes =
  [BG_BF_BOUNDARY_NOT_PASS,
   BG_MARGINAL_CAPITAL_AUTHORITY_CONSUMER_NOT_ENABLED,
   BG_PRODUCTION_CONSUMER_SWITCH_NOT_PASS]

runtime_planning.reason_codes =
  review_required_quantity_authority:<symbol>:REVIEW_REQUIRED_AUTHORITY_UNRESOLVED

morning/planning_evidence.reason =
  strategy_planning_authority_unresolved

morning/runtime_manifest.reason =
  morning pipeline review required: strategy_planning_authority_unresolved
```

The exact lower-level validator predicate is not preserved in the stored 10/11
boundary artifact, which reports only `bf_pc_to_ps_boundary_not_pass`.
Read-only re-validation of the saved authority payload with
`build_pc_to_ps_switch_boundary_validation()` returns:

```text
review_reasons = [ps_final_quantity_delta_inconsistent]
```

## Defect Classification

| Candidate | Judgment | Evidence |
| --- | --- | --- |
| Cash / budget defect | No | Cash `247220.0`; budget `116238.724159`; capital conservation `PASS`. |
| BO PIT flag regression | No | No `pc_discrete_quantity_authority_future_information_flag_invalid`; 10/11 fails before switched PS rows are produced. |
| Legacy fallback usage | No | `legacy_zero_fallback_used=false`; `legacy_target_gap_fallback_used=false`. |
| Authority generation defect | Partial | Authority accepts targets, but accepted ADD target quantities are inconsistent for BF aggregation. |
| BF boundary defect | Yes | Boundary is `REVIEW_REQUIRED` / zero aggregated PS targets. |
| PS consumer defect | No | PS correctly fail-closes when BF boundary is not pass. |
| Runtime/Pending defect | No | Runtime and pending propagate upstream review-required. |
| Existing unrelated review | No | AI lifecycle review exists but is review-only / non-blocking; HALT reason is strategy planning unresolved. |

## Repair Readiness

Repair should be narrow and upstream of BF activation:

```text
Make ADD next-lot candidate materialization use a consistent per-lot quantity
contract.
```

The likely minimal boundary is:

```text
common_marginal_capital_frontier_shadow._add_next_lot_candidates()
common_marginal_capital_frontier_shadow._security_candidate()
```

The repair should ensure one of these contracts holds for every repeated ADD
sequence:

```text
pre_quantity for lot N+1 = post_quantity for lot N
final_target_quantity = first_pre_quantity + sum(accepted_incremental_quantity)
```

No change is indicated for Cash, budget, PM, Runtime mapping, submit-feasibility,
Risk Pacing, REDUCE/EXIT, or BO PIT flags.

Resume readiness:

```text
Resume is not ready before repair because the current halt is a deterministic
BF boundary REVIEW_REQUIRED on the same 10/11 artifact path.
```

## Final Judgments

```text
PHASE32_BQ_HALT_ROOT_CAUSE = BF/PC-to-PS boundary REVIEW_REQUIRED because 94340 ADD multi-lot accepted targets have inconsistent quantity progression: accepted_incremental_quantity sums to +600 from current 700, but last target_quantity is 1100; exact validator predicate ps_final_quantity_delta_inconsistent, stored outer reason bf_pc_to_ps_boundary_not_pass.
PHASE32_BQ_FIRST_FAILING_STAGE = MARGINAL_CAPITAL_AUTHORITY_TO_BF_PC_TO_PS_SWITCH_BOUNDARY
PHASE32_BQ_REVIEW_REQUIRED_SOURCE = strategy/marginal_capital_frontier_authority.json#pc_to_ps_consumer_switch_boundary.review_reasons=bf_pc_to_ps_boundary_not_pass; recomputed validator predicate=ps_final_quantity_delta_inconsistent
PHASE32_BQ_BG_BL_BO_RELATED = PARTIAL
PHASE32_BQ_AUTHORITY_PATH_HEALTH = FAIL
PHASE32_BQ_LEGACY_FALLBACK_USED = NO
PHASE32_BQ_REPAIR_REQUIRED = YES
PHASE32_BQ_RESUME_READY_AFTER_REPAIR = YES
PHASE32_BQ_NEXT_STEP = Narrow BQ follow-up repair of ADD repeated-lot quantity materialization so each lot's pre/post quantity sequence and accepted_incremental_quantity aggregate consistently before BF activation; then user-operated resume or short fresh validation.
```
