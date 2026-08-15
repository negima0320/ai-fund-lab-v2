# Phase29-L21T-T 2023-06-12 Scoped Pending Regeneration / Replay Readiness

## Scope

READ-ONLY CLI / RECOVERY CAPABILITY AUDIT + MINIMAL IMPLEMENTATION + FOCUSED
REGRESSION.

Codex did not execute backup, apply recovery, replay, resume, fresh-run, long
Historical validation, manual Pending approval, or target runtime mutation.
Only dry-run commands were executed against the target run.

Target run:

```text
runtime-test-historical-smoke-20260812T083943290963Z
```

Target date:

```text
2023-06-12
```

## Primary Judgment

`PHASE29_L21T_T_STALE_PENDING_SCOPED_REGENERATION_RECOVERY_PATH_IMPLEMENTED_DRY_RUN_READY`

Required judgments:

```text
EXISTING_SCOPED_RECOVERY_CAN_HANDLE_2023_06_12_STALE_PENDING = NO
REQUIRED_REWIND_BOUNDARY = 2023-06-12:morning
PRE_RECOVERY_BACKUP_REQUIRED = YES
PENDING_MANUAL_EDIT_REQUIRED = NO
DIRECT_RESUME_SAFE = NO
RECOVERY_IMPLEMENTATION_REQUIRED = YES
USER_EXECUTION_COMMAND_READY = YES
```

## Existing Capability Audit

Existing scoped recovery before L21T-T:

```text
recover-failed-execution
replay-recovered-day
```

`recover-failed-execution` is intentionally scoped to Q3B execution failure /
submit-only precommit halt shapes.  Its preconditions require:

```text
run_state.next_job = <date>:execution
current Pending state = CONSUMED
target-date failed execution rows or submit-only precommit rows
```

The 2023-06-12 halt is different:

```text
run_state.status = HALT
run_state.next_job = 2023-06-12:sell_planning
halted_at.job = sell_planning
current Pending state = REVIEW_REQUIRED
pending_plan_id = pending-strategy-plan-historical-2023-06-12-c5095866647c8ae8
review_scope = BUY_ITEM_SCOPED_REVIEW
target ledger rows for 2023-06-12 = none
```

Dry-run evidence from the existing Q3B command:

```text
PYTHONPATH=src python3 scripts/runtime_test.py recover-failed-execution \
  --profile historical-smoke \
  --runtime-root .runtime \
  --evidence-root reports/runtime_tests \
  --run-id runtime-test-historical-smoke-20260812T083943290963Z \
  --business-date 2023-06-12 \
  --rewind-to-job morning \
  --dry-run \
  --json
```

Result:

```text
status = PRECONDITION_FAILURE
errors =
  run_state next_job is not failed execution boundary
  pending is not consumed failed-attempt state
  expected four failed execution rows or submit-only precommit halt rows
```

Therefore Q3B execution recovery must not be reused for this case by relaxing
conditions.

## Implementation

Added Production-common Runtime Test command:

```text
recover-stale-pending
```

The command:

- verifies the run is halted at target-date `sell_planning`
- verifies persistent Current is at the last completed coherent business day
- verifies the current Pending is same-day `REVIEW_REQUIRED`
- verifies the target date has no Ledger rows
- optionally verifies the expected Pending plan id
- preserves stale Pending and daily evidence under run-scoped recovery evidence
- retires the stale current Pending slot to `EMPTY`
- rewinds run_state to the requested replay job
- removes target-date replay jobs from `completed_jobs`
- does not edit Ledger, Current, accepted generation, Strategy artifacts, or
  broker evidence

Changed files:

- `scripts/runtime_test.py`
- `tests/runtime_v2/test_phase17_k_runtime_test_runner.py`
- `docs/phase_reports/phase29_l21t_t_2023_06_12_scoped_pending_regeneration_replay_readiness.md`

## Target Dry-Run Evidence

Command:

```text
PYTHONPATH=src python3 scripts/runtime_test.py recover-stale-pending \
  --profile historical-smoke \
  --runtime-root .runtime \
  --evidence-root reports/runtime_tests \
  --run-id runtime-test-historical-smoke-20260812T083943290963Z \
  --business-date 2023-06-12 \
  --rewind-to-job morning \
  --expected-pending-plan-id pending-strategy-plan-historical-2023-06-12-c5095866647c8ae8 \
  --dry-run \
  --json
```

Result:

```text
status = DRY_RUN
errors = []
recovery_classification = STALE_REVIEW_REQUIRED_PENDING_REPLAY
recovery_id = scoped-stale-pending-59c30dccbd59148c
source_recovery_point.business_date = 2023-06-09
source_recovery_point.cash = 609670.0
source_recovery_point.buying_power = 609670.0
source_recovery_point.position_count = 3
stale_pending.pending_plan_id = pending-strategy-plan-historical-2023-06-12-c5095866647c8ae8
stale_pending.state = REVIEW_REQUIRED
stale_pending.review_scope = BUY_ITEM_SCOPED_REVIEW
target_ledger_rows = empty for orders/executions/positions/cash/events
manual_file_edit_required = false
ledger_current_recovery_required = false
production_common_recovery = true
```

## Replay Dry-Run Evidence

Command:

```text
PYTHONPATH=src python3 scripts/runtime_test.py replay-recovered-day \
  --profile historical-smoke \
  --runtime-root .runtime \
  --evidence-root reports/runtime_tests \
  --run-id runtime-test-historical-smoke-20260812T083943290963Z \
  --business-date 2023-06-12 \
  --jobs morning,sell_planning,submit,execution \
  --dry-run \
  --json
```

Result:

```text
status = DRY_RUN
jobs = morning,sell_planning,submit,execution
dry_run_no_mutation = true
```

This dry-run only proves the replay command is callable.  It should be executed
after `recover-stale-pending` has rewound run_state to `2023-06-12:morning`.

## User Execution Commands

1. Pre-recovery backup:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py backup \
  --profile historical-smoke \
  --runtime-root .runtime \
  --evidence-root reports/runtime_tests \
  --confirm \
  --yes-i-understand-this-mutates-trading-state \
  --json
```

2. Scoped stale Pending recovery dry-run:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py recover-stale-pending \
  --profile historical-smoke \
  --runtime-root .runtime \
  --evidence-root reports/runtime_tests \
  --run-id runtime-test-historical-smoke-20260812T083943290963Z \
  --business-date 2023-06-12 \
  --rewind-to-job morning \
  --expected-pending-plan-id pending-strategy-plan-historical-2023-06-12-c5095866647c8ae8 \
  --dry-run \
  --json
```

3. Scoped stale Pending recovery apply:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py recover-stale-pending \
  --profile historical-smoke \
  --runtime-root .runtime \
  --evidence-root reports/runtime_tests \
  --run-id runtime-test-historical-smoke-20260812T083943290963Z \
  --business-date 2023-06-12 \
  --rewind-to-job morning \
  --expected-pending-plan-id pending-strategy-plan-historical-2023-06-12-c5095866647c8ae8 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state \
  --json
```

4. Replay dry-run:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py replay-recovered-day \
  --profile historical-smoke \
  --runtime-root .runtime \
  --evidence-root reports/runtime_tests \
  --run-id runtime-test-historical-smoke-20260812T083943290963Z \
  --business-date 2023-06-12 \
  --jobs morning,sell_planning,submit,execution \
  --dry-run \
  --json
```

5. Replay apply:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py replay-recovered-day \
  --profile historical-smoke \
  --runtime-root .runtime \
  --evidence-root reports/runtime_tests \
  --run-id runtime-test-historical-smoke-20260812T083943290963Z \
  --business-date 2023-06-12 \
  --jobs morning,sell_planning,submit,execution \
  --confirm \
  --yes-i-understand-this-mutates-trading-state \
  --json
```

6. Post-replay inspection:

```bash
jq '{
  state,
  pending_plan_id,
  approved_item_ids,
  approved_buy_item_ids,
  review_required_buy_item_ids,
  review_scope,
  sell_continuation_allowed,
  feasibility_statuses: [.items[]? | {
    pending_item_id,
    symbol,
    side,
    quantity,
    state,
    approved,
    feasibility_status,
    item_review_reason,
    estimated_amount,
    strategy_executable_notional,
    selected_position_amount,
    reserved_notional,
    cash,
    buying_power
  }],
  planning_submit_feasibility
}' .runtime/pending_order_plan/pending_order_plan.json
```

Additional targeted evidence query:

```bash
rg -n "strategy_executable_notional|reserved notional exceeds selected_position_amount|strategy-333b4929b4bedbe3e52d|59550" \
  reports/runtime_tests/runs/runtime-test-historical-smoke-20260812T083943290963Z/daily/2023-06-12 \
  .runtime/pending_order_plan/pending_order_plan.json
```

7. Resume dry-run only after replay PASS and inspection:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py resume \
  --profile historical-smoke \
  --runtime-root .runtime \
  --evidence-root reports/runtime_tests \
  --run-id runtime-test-historical-smoke-20260812T083943290963Z \
  --dry-run \
  --json
```

Do not use direct resume before the scoped recovery and replay apply steps.

## Post-Replay Acceptance

Expected 2023-06-12 / `59550` evidence after replay:

```text
strategy_executable_notional = 108000.0
selected_position_amount = 115253.75
reserved_notional = 152000.0
cash / buying_power = 609670.0
Strategy sizing = PASS
cash reservation = PASS
reserved notional exceeds selected_position_amount = absent
BUY_ITEM_SCOPED_REVIEW solely from reserved_notional > selected_position_amount = absent
Pending regenerated under L21T-S semantics = YES
```

If SELL has no executable signal, `sell_planning` should preserve the existing
NO_SIGNAL composition contract.  It must not revive the old stale
REVIEW_REQUIRED reason.

## Regression

Focused recovery tests:

```text
python3 -m pytest tests/runtime_v2/test_phase17_k_runtime_test_runner.py -k 'q3b or q1b_recovery or stale_pending' -q
7 passed, 31 deselected in 2.08s
```

Focused Runtime regression:

```text
python3 -m pytest \
  tests/runtime_v2/test_phase17_k_runtime_test_runner.py \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py \
  tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py \
  tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py \
  tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py \
  -q
99 passed in 14.63s
```

Compile:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-l21t-t-pycache python3 -m py_compile \
  scripts/runtime_test.py \
  tests/runtime_v2/test_phase17_k_runtime_test_runner.py
PASS
```

Whitespace:

```text
git diff --check
PASS
```

## Resume Decision

`DIRECT_RESUME_SAFE = NO`.

The current run still contains the pre-L21T-S stale REVIEW_REQUIRED Pending
until the user applies `recover-stale-pending`.  Generic `resume --dry-run`
currently reports command-level resumability, but it does not supersede the
stale Pending or regenerate 2023-06-12 morning Planning.  For this target case,
direct resume is operationally unsafe.

## Next Step

User should run the backup, `recover-stale-pending`, and replay sequence above.
Only after post-replay evidence confirms the L21T-S semantics for 2023-06-12 /
`59550` should the next resume decision for the broader 100BD/longer run be
made.

