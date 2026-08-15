# Phase29-L21T-Q2 Ledger / Current Transactional Commit Repair

## Scope

IMPLEMENTATION + FOCUSED REGRESSION.

Q2 builds on Q1 pre-commit execution cash feasibility and repairs the Execution
persistent mutation boundary.  Codex did not run fresh-run, resume-run, 20BD,
100BD, or long Historical validation.  Codex did not mutate the existing
2023-06-08 target run partial Ledger, Current, Pending, run state, backup, or
recovery artifacts.

Q2 does not perform Q3 existing partial-state recovery and does not change
Strategy, PM, Buy Quality, Ranking, Safety caps, or Historical execution price
authority.

## Primary Judgment

`PHASE29_L21T_Q2_LEDGER_CURRENT_TRANSACTIONAL_COMMIT_REPAIRED_FOCUSED_REGRESSION_PASS`

Required continuation state:

```text
VALIDATE_BEFORE_COMMIT_IMPLEMENTED = YES
CASH_FAILURE_PREVENTS_PERSISTENT_MUTATION = YES
PROJECTION_FAILURE_PREVENTS_PERSISTENT_MUTATION = YES
LEDGER_CURRENT_LOGICAL_TRANSACTION_ESTABLISHED = YES
PENDING_TERMINALIZATION_ORDER_SAFE = YES
RETRY_DEDUP_SAFE = YES
BUY_NEW_REGRESSION = NO
BUY_ADD_REGRESSION = NO
REENTRY_REGRESSION = NO
SELL_REGRESSION = NO
ONE_LOT_REGRESSION = NO
BUY_SELL_INDEPENDENCE_REGRESSION = NO
PRODUCTION_PARITY_PRESERVED = YES
HISTORICAL_SPECIFIC_LOGIC_ADDED = NO
Q3_RECOVERY_STILL_REQUIRED = YES
RESUME_SAFE_NOW = NO
```

## Repair Summary

Execution now validates the candidate transaction before persistent mutation:

```text
read authoritative state
resolve submitted orders / fills
build candidate ledger records
run Q1 candidate cash feasibility
run runtime-owned Current projection with candidate records and write=False
PASS
append Ledger records
write projected Current
apply Current to runtime state
then classify Pending terminalization requirement
```

`project_runtime_owned_fills_to_current` now accepts candidate order,
execution, and position records.  It merges those records with existing
persistent ledger rows in memory and keeps `write=False` side-effect free, so
Execution can reuse the canonical projection logic without duplicating cash,
quantity, cost basis, dedup, and applied-execution checks.

Execution result evidence now exposes:

- `transaction_validation_status`
- `transaction_validation_reason`
- `source_current_hash`
- `candidate_current_hash`
- `candidate_cash`
- `candidate_position_count`
- `candidate_execution_count`
- `persistent_commit_started`
- `persistent_commit_completed`
- `ledger_commit_status`
- `current_commit_status`
- `transaction_consistency_status`
- `execution_transaction_id`

Validation failures return `REVIEW_REQUIRED` with all Execution persistent append
counts at zero, `asset_current_written=false`, `current_apply_status=NOT_EXECUTED`,
and `pending_terminalization_status=NOT_EXECUTED`.

## Regression Evidence

Focused Execution transaction regression:

```text
python3 -m pytest tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py -q

13 passed in 1.95s
```

This includes:

- Q1 negative cash failure prevents persistent mutation
- Q2 projection failure prevents persistent mutation
- normal Historical BUY commit succeeds
- same Execution retry dedups committed records and Current apply returns NOOP

Broader focused Runtime regression:

```text
python3 -m pytest \
  tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py \
  tests/runtime_v2/test_phase14e23_execution_acceptance_policy.py \
  tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py \
  tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py \
  tests/runtime_v2/test_phase23_i_strategy_planning_authority.py \
  tests/runtime_v2/test_phase26_step4_position_sizing_authority.py \
  -q

86 passed in 42.41s
```

BUY_ADD / REENTRY / SELL continuation / one-lot protection:

```text
python3 -m pytest \
  tests/runtime_v2/test_phase26_step4_position_sizing_authority.py::test_phase29_l21t_h_position_sizing_consumes_authorized_one_lot_buy_add_and_reentry \
  tests/strategy/test_phase22_j_position_sizing.py::test_phase29_l21t_c_ps_materializes_buy_add_one_lot_increment_when_continuous_delta_floors_to_zero \
  tests/strategy/test_phase22_j_position_sizing.py::test_phase29_l21t_c_ps_preserves_reentry_semantics_for_one_lot_quantity_authority \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase29_l21s_buy_add_one_lot_fallback_preserves_add_semantics \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase29_l21s_reentry_pass_keeps_semantic_when_one_lot_fallback_applies \
  tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py::test_phase29_l21t_m_buy_item_scoped_review_composes_valid_reduce_sell \
  tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py::test_phase29_l21t_m_buy_item_scoped_review_composes_valid_exit_sell_and_submit_filters_buy \
  -q

8 passed in 2.13s
```

Execution dedup / Current apply legacy focused regression:

```text
python3 -m pytest \
  tests/runtime_v2/test_phase15bv_execution_normalization_current_apply.py \
  tests/runtime_v2/test_phase15bw_runtime_end_to_end_daily_system_test_review.py::test_phase15bw_ledger_dedup_and_demo_only_flags_remain \
  -q

7 passed in 0.08s
```

Static checks:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache-q2 python3 -m py_compile \
  src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py \
  src/ai_fund_lab_v2/runtime_v2/asset/runtime_owned_fill_projection.py \
  tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py

PASS

git diff --check
PASS
```

## User Fresh-Run Command

Codex did not execute this command.  After Q3 recovery is complete, the focused
fresh-run window requested for user-side validation remains:

```text
python3 scripts/runtime_test.py --mode historical --start-date 2022-08-23 --end-date 2022-09-16
```
