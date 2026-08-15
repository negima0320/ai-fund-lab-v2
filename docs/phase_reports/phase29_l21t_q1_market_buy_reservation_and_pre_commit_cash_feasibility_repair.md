# Phase29-L21T-Q1 MARKET BUY Reservation and Pre-Commit Cash Feasibility Repair

## Scope

IMPLEMENTATION + FOCUSED REGRESSION.

This repair is Production/Demo/Historical common Runtime v2 work only.  Codex
did not start a fresh-run, resume-run, 20BD, 100BD, or long Historical run.
Codex did not mutate the existing 2023-06-08 target run partial state, Pending,
Current, Ledger JSONL, run state, backups, or recovery artifacts.

Q1 addressed only:

- explicit Planning/Submit MARKET BUY reservation semantics
- pre-commit execution cash feasibility after actual fill authority is known
  and before persistent execution mutation

Q1 did not implement Q2 Ledger/Current transactional commit architecture, Q3
existing partial-state recovery, or any separate Q4 Historical Execution Safety
authority alignment.

## Primary Judgment

`PHASE29_L21T_Q1_MARKET_BUY_RESERVATION_AND_PRE_COMMIT_CASH_FEASIBILITY_REPAIRED_FOCUSED_REGRESSION_PASS`

Required continuation state remains:

```text
RESUME_SAFE_NOW = NO
Q2_TRANSACTIONAL_COMMIT_STILL_REQUIRED = YES
Q3_EXISTING_PARTIAL_STATE_RECOVERY_STILL_REQUIRED = YES
Q4_HISTORICAL_EXECUTION_SAFETY_AUTHORITY = SEPARATE
```

## Repair Summary

Planning/Pending now carries explicit BUY reservation evidence:

- `reference_price`
- `reference_price_authority`
- `reservation_price`
- `reservation_price_authority`
- `reservation_reason`
- `reserved_notional`

Strategy Planning and the morning Runtime order plan materialize these fields
from their existing point-in-time planning reference authority.  The reservation
contract is explicit that future execution price is not used at Planning time.

Planning/Submit feasibility now evaluates BUY cash affordability using
`reserved_notional`, with a legacy fallback to the prior `estimated_amount`
semantics for older pending payloads.  The aggregate sequential reservation also
uses `reserved_notional`, so a set of MARKET BUY items cannot pass merely
because planned reference amounts are lower than the authorized cash reservation
amount.

Submit guard item evidence now exposes the same reservation fields while
preserving existing `estimated_price` and `estimated_amount` observability.

Execution now performs a pre-commit cash feasibility check from the persistent
ledger current cash and the candidate execution-equivalent records.  If the
candidate BUY/SELL fill set would project negative cash, execution returns
`REVIEW_REQUIRED` before appending orders, executions, positions, cash, events,
or writing Current.

## Files Changed by Q1

- `src/ai_fund_lab_v2/runtime_v2/pending/models.py`
- `src/ai_fund_lab_v2/runtime_v2/pending/reader.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/approval/policy.py`
- `src/ai_fund_lab_v2/runtime_v2/planning_submit_feasibility.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py`
- `tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py`
- `tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py`

The worktree contained unrelated prior phase changes before Q1; those were not
reverted or normalized by this task.

## Regression Evidence

Focused Q1 tests:

```text
python3 -m pytest \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py::test_phase29_l21t_q1_market_buy_uses_reserved_notional_for_aggregate_cash \
  tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py::test_phase29_l21t_q1_execution_pre_commit_blocks_negative_candidate_cash \
  tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py::test_phase17_g_execution_processor_accepts_historical_provider_fixture \
  -q

3 passed in 1.79s
```

Broader focused Runtime regression:

```text
python3 -m pytest \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py \
  tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py \
  tests/runtime_v2/test_phase14e23_execution_acceptance_policy.py \
  tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py \
  tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py \
  tests/runtime_v2/test_phase23_i_strategy_planning_authority.py \
  tests/runtime_v2/test_phase26_step4_position_sizing_authority.py \
  -q

84 passed in 43.89s
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

8 passed in 1.92s
```

Compile and whitespace checks:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m py_compile ...
PASS

git diff --check
PASS
```

The initial direct `pytest` command was unavailable in this shell, so regression
was run through `python3 -m pytest`.  Direct `python3 -m py_compile` first tried
to write bytecode under the user Library cache outside the sandbox; the compile
check was rerun with `PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache`
and passed.

## User Fresh-Run Command

Codex did not execute this command.  After Q2 and Q3 are complete, the focused
fresh-run window requested for user-side validation remains:

```text
python3 scripts/runtime_test.py --mode historical --start-date 2022-08-23 --end-date 2022-09-16
```
