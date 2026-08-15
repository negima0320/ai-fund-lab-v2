# Phase29-L20F - Historical Pending Lifecycle Runner Day Completion Repair

Task ID: Phase29-L20F

Mode:

```text
DESIGN + IMPLEMENTATION + RUNNER INTEGRATION TEST + SHORT REGRESSION + CONTINUATION ASSESSMENT
NO CURRENT HALTED RUN MUTATION
NO RESUME / FRESH-RUN / RUN / CURRENT-RUN PENDING_LIFECYCLE COMMAND
NO LONG HISTORICAL EXECUTION
```

## Primary Judgment

```text
PHASE29_L20F_HISTORICAL_PENDING_LIFECYCLE_RUNNER_INTEGRATION_AND_DAY_COMPLETION_CONTRACT_IMPLEMENTED_SHORT_REGRESSION_PASS_FRESH_RUN_RECOMMENDED
```

## Root Cause Carried Forward

L20E root cause remains correct:

```text
HISTORICAL_RUNTIME_RUNNER_DOES_NOT_INVOKE_REQUIRED_PENDING_LIFECYCLE_AFTER_CA_QUARANTINE_EXECUTION
```

L20F repairs the runner integration gap. The Pending lifecycle transition logic
from L20D remains the state mutation authority.

## Final Runner Design

Detection producer:

```text
Execution / execution/pending_terminalization_evidence.json
status = PENDING_LIFECYCLE_REQUIRED
```

Invocation owner:

```text
Historical Runtime Test runner / end-of-day orchestration
```

Lifecycle state owner:

```text
src/ai_fund_lab_v2/runtime_v2/pending/lifecycle_runner.py
```

Day Completion owner:

```text
scripts/runtime_test.py
```

Execution remains detector-only. Data Readiness remains a strict checker and
does not mutate Pending.

## Actual Final Job Ordering

Post-repair Historical daily order:

```text
market_refresh
data_readiness
morning
sell_planning
submit
execution
conditional pending_lifecycle
current_valuation_refresh
runtime_state_refresh
strategy_shadow_generation
day_completion_gate
completed_business_days append
```

`pending_lifecycle` is not added blindly to the static profile sequence. It is
runner-invoked only when the formal Execution evidence requires it.

## Lifecycle Trigger

Automatic Pending lifecycle runs only when:

```text
reports/runtime_tests/runs/<run_id>/daily/<business_date>/execution/pending_terminalization_evidence.json
status == PENDING_LIFECYCLE_REQUIRED
```

The runner invokes the existing Runtime v2 CLI:

```text
--job pending_lifecycle
--pending-action review
```

for the same run and business date, preserving run-scoped evidence.

## Day Completion Contract

Before appending a date to `completed_business_days`, the runner writes:

```text
reports/runtime_tests/runs/<run_id>/daily/<business_date>/day_completion/day_completion_evidence.json
```

Post-conditions:

```text
1. If no lifecycle marker exists, existing ordinary-day semantics continue.
2. If PENDING_LIFECYCLE_REQUIRED exists, pending_lifecycle evidence must exist.
3. Required lifecycle result must be EXPIRED / CANCELLED / SUPERSEDED / NOOP.
4. Required lifecycle must not leave active APPROVED Pending for the same business date.
5. Required lifecycle must not mask POST_SEND_UNKNOWN or REVIEW_REQUIRED active Pending.
6. Only PASS day_completion evidence allows completed_business_days append.
```

## Failure Semantics

If required Pending lifecycle returns `REVIEW_REQUIRED`, missing evidence, an
invalid status, or non-zero exit:

```text
runner HALTs
business date is not appended to completed_business_days
explicit pending_lifecycle job_record is retained in run_state.completed_jobs
day does not proceed to next business date
```

If the Day Completion Gate itself detects unresolved lifecycle work:

```text
runner records day_completion_gate HALT evidence
completed_business_days append is blocked
```

## Changed Files

L20F changed:

```text
scripts/runtime_test.py
tests/runtime_v2/test_phase17_k_runtime_test_runner.py
docs/phase_reports/phase29_l20f_historical_pending_lifecycle_runner_day_completion_repair.md
```

Pre-existing L20B/L20D worktree changes remain present in:

```text
src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py
src/ai_fund_lab_v2/runtime_v2/pending/lifecycle_runner.py
tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py
tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py
```

## CA Quarantine BUY Result

Runner-level fixture verifies:

```text
Execution emits PENDING_LIFECYCLE_REQUIRED
runner invokes pending_lifecycle
pending_lifecycle returns EXPIRED
Pending slot becomes EMPTY
Day Completion PASS
```

## CA Quarantine SELL Result

L20D direct lifecycle tests still cover strict BUY and SELL terminalization.
L20F runner trigger is side-agnostic because it consumes only formal Execution
status, not symbol or side strings. SELL fail-open behavior was not introduced.

## Multi-day Integration Result

Added runner-level test:

```text
test_phase29_l20f_runner_invokes_pending_lifecycle_before_next_day_readiness
```

It simulates:

```text
Day D execution -> PENDING_LIFECYCLE_REQUIRED
runner pending_lifecycle -> EXPIRED / EMPTY
Day D completion -> PASS
Day D+1 data_readiness observes EMPTY, not stale APPROVED
```

The test also asserts pending_lifecycle runs before:

```text
current_valuation_refresh
next-day data_readiness
```

## Ordinary NO_ACTION Result

Ordinary no-action days do not create `PENDING_LIFECYCLE_REQUIRED`; therefore
the runner does not invoke `pending_lifecycle`. Existing no-action execution
semantics remain `ALREADY_TERMINAL` / no mutation.

## Submitted Order Result

Submitted-order execution remains on the normal execution/orderlist path. The
runner trigger is not submit count, symbol, or text reason; it is only the
formal `PENDING_LIFECYCLE_REQUIRED` evidence. Existing execution submitted-order
tests remain PASS.

## Unknown Submit Risk Result

Unknown submit risk remains fail-closed. L20D tests still assert unknown submit
does not become `EMPTY`. L20F additionally halts the runner when required
pending lifecycle returns `REVIEW_REQUIRED`.

## Generic REVIEW_REQUIRED Result

Generic Data Readiness stale Pending remains `REVIEW_REQUIRED`. L20F does not
weaken Data Readiness and does not turn generic review into automatic
terminalization.

## Mixed Case Result

Mixed quarantine + executable behavior is not flattened. Execution does not
emit quarantine-only NO_ACTION when `submitted_count > 0`, and L20D keeps mixed
whole-plan terminalization fail-closed. L20F does not redesign item-scoped mixed
Pending lifecycle.

## Production / Demo Safety

Production/Demo unresolved Corporate Action remains fail-closed. L20F changes
the Historical Runtime Test runner orchestration and does not change Production
or Demo Submit, Execution, Safety, or Data Readiness rules.

## Strategy Impact

```text
NO STRATEGY SEMANTIC CHANGE
```

Explicitly unchanged:

```text
L19 = unchanged
ADD = unchanged
BUY_NEW / BUY_ADD = unchanged
SELL / REDUCE / EXIT = unchanged
Portfolio Construction = unchanged
Position Sizing = unchanged
Market Context = unchanged
```

## Regression Results

Runner L20F focused:

```text
PYTHONPATH=src:. python3 -m pytest -q tests/runtime_v2/test_phase17_k_runtime_test_runner.py -k 'phase29_l20f or run_marks_execution_success_when_runtime_cli_jobs_pass or run_invokes_normal_runtime_cli_and_stops_on_nonzero'
4 passed, 26 deselected
```

Runner full file:

```text
PYTHONPATH=src:. python3 -m pytest -q tests/runtime_v2/test_phase17_k_runtime_test_runner.py
30 passed
```

L20D focused:

```text
PYTHONPATH=src:. python3 -m pytest -q tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py -k 'phase29_l20d or phase15ar_stale_approved_pending_expires_to_history_and_empty_slot or phase15ar_unknown_submit_attempt_moves_to_review_required_not_empty or phase15ar_data_readiness_pending_ready_after_expiration'
8 passed, 8 deselected
```

L20D full file:

```text
PYTHONPATH=src:. python3 -m pytest -q tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py
16 passed
```

L20B focused:

```text
PYTHONPATH=src:. python3 -m pytest -q tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py -k 'phase29_l20b or phase17_bg_empty_no_action_execution_is_terminal_pass_without_writes or active_pending_with_missing_orderlist or real_order_with_missing_orderlist or real_order_execution_path_still_passes'
8 passed, 5 deselected
```

Execution full file:

```text
PYTHONPATH=src:. python3 -m pytest -q tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py
13 passed
```

CA quarantine + execution:

```text
PYTHONPATH=src:. python3 -m pytest -q tests/runtime_v2/test_phase29_l9_historical_ca_quarantine_continuation.py tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py
21 passed
```

Data Readiness stale Pending:

```text
PYTHONPATH=src:. python3 -m pytest -q tests/runtime_v2/test_phase15aq_runtime_data_readiness_gate.py -k stale_approved_pending_is_review_required
1 passed, 8 deselected
```

L19 Strategy:

```text
PYTHONPATH=src:. python3 -m pytest -q tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py -k phase29_l19
6 passed, 143 deselected
```

Compile/checks:

```text
PYTHONPATH=src:. PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m py_compile scripts/runtime_test.py src/ai_fund_lab_v2/runtime_v2/pending/lifecycle_runner.py src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py
PASS

git diff --check
PASS
```

## Current Run Mutation

```text
NO
```

Read-only inspection confirmed the current halted run remains:

```text
status = HALT
next_job = 2022-09-29:data_readiness
completed tail = 2022-09-26, 2022-09-27, 2022-09-28
```

No `pending_lifecycle` evidence was created under:

```text
reports/runtime_tests/runs/runtime-test-historical-smoke-20260811T090301298165Z/daily
```

## Long Historical Executed

```text
NO
```

No 20BD, 100BD, 1-year, 4-year, resume, fresh-run, or actual Historical run
was executed by Codex.

## Continuation Assessment

```text
FRESH_RUN_RECOMMENDED
```

Rationale:

```text
L20F changes runner semantics after the current run already marked 2022-09-28
complete without required lifecycle work. The cleanest provenance-safe
validation is a new Historical fresh-run from the requested start date.
```

Existing run continuation would require resuming a run whose completion history
was produced under the pre-L20F contract, with an active stale Pending already
present at the halted point.

## User Next Step

User-operated command, not executed by Codex:

```bash
PYTHONPATH=src:. python3 scripts/runtime_test.py fresh-run \
  --profile historical-smoke \
  --start-date 2022-08-10 \
  --end-date 2026-08-09 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state \
  --json
```
