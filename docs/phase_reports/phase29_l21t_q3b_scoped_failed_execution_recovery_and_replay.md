# Phase29-L21T-Q3B Scoped Failed-Execution Recovery and 2023-06-08 Replay

## Scope

IMPLEMENTATION + SCOPED RECOVERY + FOCUSED REGRESSION.

Codex implemented a Production-common Runtime Test scoped failed-execution
recovery command and applied it only to target run:

`runtime-test-historical-smoke-20260812T083943290963Z`

Allowed replay was limited to:

```text
2023-06-08:morning
2023-06-08:sell_planning
2023-06-08:submit
2023-06-08:execution
```

Codex did not run fresh-run, 20BD, 100BD, full resume, or long Historical
validation.

## Primary Judgment

`PHASE29_L21T_Q3B_SCOPED_FAILED_EXECUTION_RECOVERY_APPLIED_Q1_Q2_REPLAY_FAIL_CLOSED_RESUME_STILL_BLOCKED`

Required judgments:

```text
PRODUCTION_COMMON_RECOVERY_MECHANISM_IMPLEMENTED = YES
BUSINESS_DATE_HARDCODE_ADDED = NO
MANUAL_JSONL_EDIT_PERFORMED = NO
PRE_RECOVERY_BACKUP_CREATED = YES
Q3A_PRECONDITIONS_MATCHED_BEFORE_MUTATION = YES
FAILED_EVIDENCE_PRESERVED = YES
SCOPED_RECOVERY_APPLIED = YES
RUN_REWOUND_TO_2023_06_08_MORNING = YES
Q1_PENDING_SUBMIT_RESERVATION_FIELDS_REGENERATED = YES
Q2_VALIDATE_BEFORE_COMMIT_ENFORCED = YES
EXECUTION_PARTIAL_LEDGER_MUTATION_RECURRED = NO
REPLAY_EXECUTION_RESULT = REVIEW_REQUIRED_FAIL_CLOSED
RESUME_SAFE_NOW = NO
```

## Implementation

Added Runtime Test commands in `scripts/runtime_test.py`:

```text
recover-failed-execution
replay-recovered-day
```

The recovery command:

- derives the coherent recovery boundary from `run_state.completed_business_days`
- optionally checks operator-supplied expected preconditions
- identifies failed transaction rows by business date and execution dedup keys
- preserves failed Ledger/Pending/Broker/evidence artifacts under run-scoped
  recovery evidence
- removes failed active Ledger rows through formal JSONL reconstruction
- retires the consumed Pending slot to EMPTY
- retires active historical broker evidence for the failed day
- restores runtime current metadata to the last completed coherent day
- rewinds run_state to the requested replay job

No `business_date == 2023-06-08` generic branch was added.  The Q3A target
values were supplied as command preconditions:

```text
--expected-recovery-date 2023-06-07
--expected-cash 437870
--expected-position-count 5
--expected-negative-cash -46930
```

## Pre-Recovery Backup

Official backup command:

```text
PYTHONPATH=src python3 scripts/runtime_test.py backup --profile historical-smoke --runtime-root .runtime --evidence-root reports/runtime_tests --confirm --yes-i-understand-this-mutates-trading-state --json
```

Result:

```text
backup_id = backup-historical-smoke-20260812T121433984819Z
scope = resettable_trading_state_only
bundle_hash = ec478964930a3f82fd0ca740e33db446a1dbd72319ee6304225272c89497630a
file_count = 8
state.json sha256 = 762abff6c36736393039cf68275d339b6d784a95171b140f4295e540a86796fd
```

## Recovery

Dry-run precondition check:

```text
status = DRY_RUN
errors = []
source_recovery_point.business_date = 2023-06-07
source_recovery_point.cash = 437870
source_recovery_point.position_count = 5
observed_negative_cash_values = [-46930]
failed_execution_dedup_key_count = 4
superseded_pending_plan_id = pending-order-plan-pending-composite-2023-06-08-9f82a489fae9
```

Applied recovery:

```text
status = PASS
recovery_id = scoped-recovery-96a7b287218359a2
run_state_rewind_from = 2023-06-08:execution
run_state_rewind_to = 2023-06-08:morning
```

Post-recovery invariant:

```text
run_state.status = HALT
run_state.next_job = 2023-06-08:morning
persistent state business_date/as_of = 2023-06-07
cash = 437870
buying_power = 437870
positions = 5
pending state = EMPTY
historical_broker/2023-06-08 active path = removed
active Ledger rows containing 2023-06-08 = 0
```

Failed evidence was preserved at:

`reports/runtime_tests/runs/runtime-test-historical-smoke-20260812T083943290963Z/recovery/scoped-recovery-96a7b287218359a2/`

## Scoped Replay Result

Dry-run:

```text
status = DRY_RUN
next_job = 2023-06-08:morning
jobs = morning,sell_planning,submit,execution
```

Actual scoped replay:

```text
morning = 0
sell_planning = 0
submit = 0
execution = 20
status = HALT
stopped_at = 2023-06-08:execution
```

Execution direct reason:

```text
pre-commit execution cash feasibility failed:
candidate execution cash projection negative: -46930.0
```

Q1 reservation evidence regenerated in Pending/Submit:

```text
30410 BUY qty 100 reservation_price 1203 reserved_notional 120300
59550 BUY qty 1100 reservation_price 101 reserved_notional 111100
67310 BUY qty 100 reservation_price 2000 reserved_notional 200000
24350 SELL qty 200 reservation_price 248 reserved_notional 49600
reservation_price_authority.runtime_path = Production/Demo/Historical common runtime_v2
future_execution_price_used = false
```

Q2 transaction boundary evidence:

```text
transaction_validation_status = REVIEW_REQUIRED
transaction_validation_reason = candidate execution cash projection negative: -46930.0
candidate_cash = -46930.0
pre_commit_starting_cash = 437870.0
aggregate_candidate_buy_notional = 538600.0
aggregate_candidate_sell_notional = 53800.0
persistent_commit_started = false
persistent_commit_completed = false
ledger_commit_status = NOT_EXECUTED
current_commit_status = NOT_EXECUTED
transaction_consistency_status = NOT_EXECUTED
ledger_orders_appended = 0
ledger_executions_appended = 0
ledger_positions_appended = 0
ledger_cash_appended = 0
ledger_events_appended = 0
pending_terminalization_status = NOT_EXECUTED
pending_consumed = false
pending_mutated = false
```

After replay, active Ledger has the regenerated 2023-06-08 Submit accepted
order rows only.  No 2023-06-08 execution, position, cash, or event rows were
appended by the failed execution retry.  Persistent `state.json` remains
coherent at 2023-06-07.

## Resume Safety

`RESUME_SAFE_NOW = NO`.

Reason:

- scoped recovery succeeded
- Q1/Q2 replay reached execution
- execution correctly failed closed before persistent commit
- submit already regenerated accepted rows and consumed Pending for 2023-06-08
- run_state is halted again at `2023-06-08:execution`

Continuing with plain resume would retry execution against a consumed submit
state.  A separate policy/repair decision is required for the remaining
negative-cash feasibility condition.

## Regression

Focused Q3B recovery tests:

```text
python3 -m pytest \
  tests/runtime_v2/test_phase17_k_runtime_test_runner.py::test_phase29_l21t_q3b_failed_execution_recovery_dry_run_detects_scope \
  tests/runtime_v2/test_phase17_k_runtime_test_runner.py::test_phase29_l21t_q3b_failed_execution_recovery_rewinds_and_preserves_prior_ledger \
  tests/runtime_v2/test_phase17_k_runtime_test_runner.py::test_phase29_l21t_q3b_failed_execution_recovery_refuses_coherent_state \
  -q

3 passed in 1.68s
```

Broad focused Runtime regression:

```text
python3 -m pytest \
  tests/runtime_v2/test_phase17_k_runtime_test_runner.py \
  tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py \
  tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py \
  tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py \
  -q

89 passed in 13.75s
```

BUY_ADD / REENTRY / SELL continuation focused regression:

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

8 passed in 1.89s
```

Compile:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-q3b-pycache python3 -m py_compile scripts/runtime_test.py tests/runtime_v2/test_phase17_k_runtime_test_runner.py

PASS
```

## User Focused Fresh-Run Command

Codex did not execute this command.  For later operator validation after the
remaining negative-cash policy decision:

```text
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run --profile historical-smoke --runtime-root .runtime --evidence-root reports/runtime_tests --start-date 2022-08-23 --end-date 2022-09-16 --confirm --yes-i-understand-this-mutates-trading-state
```
