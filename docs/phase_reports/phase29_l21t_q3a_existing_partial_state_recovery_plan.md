# Phase29-L21T-Q3A Existing 2023-06-08 Partial-State Recovery Plan

## Scope

READ-ONLY RECOVERY AUDIT / DESIGN ONLY.

Codex did not execute recovery, restore, rollback, fresh-run, resume, 20BD,
100BD, or long Historical validation.  Codex did not mutate the target run's
Ledger, Current, Pending, run_state, backup, or runtime artifacts.

Target run:

`runtime-test-historical-smoke-20260812T083943290963Z`

Failure point:

`2023-06-08:execution`

## Primary Judgment

`PHASE29_L21T_Q3A_2023_06_08_PARTIAL_STATE_RECOVERY_PLAN_READY_RESUME_STILL_BLOCKED`

Required judgments:

```text
AUTHORITATIVE_RECOVERY_POINT_CONFIRMED = YES
LEDGER_PARTIAL_MUTATION_SCOPE_CONFIRMED = YES
CURRENT_MUTATION_SCOPE_CONFIRMED = YES
PENDING_STATE_CONFIRMED = YES
DEDUP_STATE_CONFIRMED = YES
RUN_STATE_CONFIRMED = YES
Q1_REQUIRES_2023_06_08_REPLANNING = YES
EXECUTION_ONLY_RETRY_SAFE = NO
FULL_DAY_REPLAY_REQUIRED = NO
OFFICIAL_RECOVERY_MECHANISM_AVAILABLE = NO
MANUAL_FILE_EDIT_REQUIRED = NO
PRODUCTION_COMMON_RECOVERY_POSSIBLE = YES
Q3B_RECOVERY_PLAN_READY = YES
RESUME_SAFE_NOW = NO
```

`OFFICIAL_RECOVERY_MECHANISM_AVAILABLE=NO` means no existing official scoped
mechanism was found for this exact recovery.  The existing official rollback
command exists, but it restores the full resettable Trading State bundle and is
not the right recovery authority for this 2023-06-08 partial transaction.

## Authoritative Recovery Point

The authoritative recovery point is the last coherent Runtime Current after
2023-06-07 completion:

```text
business_date/as_of = 2023-06-07
cash = 437,870 JPY
buying_power = 437,870 JPY
market_value = 512,760 JPY
positions = 5
current semantic hash = sha256:e57f60f8cbbea230495ac5f9936720e5a280f25b5329bbb6b344c67078b705c1
current_version = current-e57f60f8cbbea230
```

Positions:

| Symbol | Quantity | Average Price | Market Value |
| --- | ---: | ---: | ---: |
| 94320 | 1,200 | 158.4166666667 | 197,160 |
| 76470 | 2,700 | 25.0256410256 | 81,000 |
| 24350 | 200 | 267 | 54,000 |
| 21340 | 1,500 | 13.2413793103 | 33,000 |
| 40520 | 100 | 1,451 | 147,600 |

The current `.runtime/persistent_ledger/state.json` is coherent at 2023-06-07
and did not absorb the failed 2023-06-08 negative cash projection.

## Run State

`run_state.json`:

```text
status = HALT
next_job = 2023-06-08:execution
completed_business_day_count = 45
last_completed_business_day = 2023-06-07
completed_jobs_count = 411
failed execution record = 2023-06-08 execution exit_code=20
```

The final jobs recorded before HALT:

```text
2023-06-08 market_refresh = 0
2023-06-08 data_readiness = 0
2023-06-08 morning = 0
2023-06-08 sell_planning = 0
2023-06-08 submit = 0
2023-06-08 execution = 20
```

`fresh_run_summary.json` says:

```text
status = HALT
failed_step = run
error = Runtime CLI stopped at 2023-06-08:execution with exit code 20
backup_id = backup-historical-smoke-20260812T083932466210Z
resume_possible = true
rollback_possible = true
```

However, existing `resume` skips successful completed jobs.  With the current
run_state, resume would retry only `2023-06-08:execution`, not regenerate
morning/sell_planning/submit under Q1 semantics.

## Mutation Inventory

Authoritative mutable state:

| Area | 2023-06-08 State | Classification |
| --- | --- | --- |
| `persistent_ledger/state.json` | remains 2023-06-07 coherent | NOT_MUTATED |
| `runtime_state/current_state.json` | business_date 2023-06-08, state `CURRENT_STATE_LOADED`, no current hash/version | MUTATED metadata only / not applied |
| `pending_order_plan/pending_order_plan.json` | plan `pending-order-plan-pending-composite-2023-06-08-9f82a489fae9`, top and item states `CONSUMED` | MUTATED |
| `persistent_ledger/orders.jsonl` | 4 submit accepted rows and 4 execution readonly simulation rows containing 2023-06-08 | MUTATED |
| `persistent_ledger/executions.jsonl` | 4 execution-equivalent rows for 2023-06-08 | MUTATED |
| `persistent_ledger/positions.jsonl` | 8 rows for 2023-06-08, including 7 broker/current positions and 1 historical SELL transition | MUTATED |
| `persistent_ledger/cash.jsonl` | 1 row with cash/buying_power `-46,930` | MUTATED |
| `persistent_ledger/events.jsonl` | 1 `order_detail_optional_missing` event | MUTATED |
| realized slices | run-scoped `execution/realized_slices.json`, not `.runtime` authority | OBSERVABILITY_ONLY |
| run evidence under `reports/runtime_tests/runs/.../daily/2023-06-08` | failure evidence | OBSERVABILITY_ONLY |

Execution append evidence confirms:

```text
ledger_orders_appended = 4
ledger_executions_appended = 4
ledger_positions_appended = 8
ledger_cash_appended = 1
ledger_events_appended = 1
```

Current apply evidence confirms:

```text
runtime_owned_projection_status = REVIEW_REQUIRED
runtime_owned_projection_reason = runtime owned cash projection negative: -46930.0
asset_current_written = false
current_apply_status = NOT_EXECUTED
```

## Four 2023-06-08 Executions

| Symbol | Side | Quantity | Execution Price | Cash Effect | Execution Dedup Key |
| --- | --- | ---: | ---: | ---: | --- |
| 24350 | SELL | 200 | 269 | +53,800 | `runtime_v2_execution_equivalent:sha256:d9ba742c52f10f95197c91dde9bf8bf4ea5398adf0a7cbb8c4edc82cfaee8eaf` |
| 67310 | BUY | 100 | 3,000 | -300,000 | `runtime_v2_execution_equivalent:sha256:e5f90364f8ebc8c602403db9610e6b37cb628d31701e0ab3457f8d732a4b96b5` |
| 30410 | BUY | 100 | 1,275 | -127,500 | `runtime_v2_execution_equivalent:sha256:88d375b7d45387f3d6865cd3e3e3a0cf8ef0fd5c09778fa9bbea0791834bd1b6` |
| 59550 | BUY | 1,100 | 101 | -111,100 | `runtime_v2_execution_equivalent:sha256:7a684d54673a1ecb969534c50d13f224adc542a18bc0658fee1e0b8db6ebd0a0` |

These keys are present in Ledger but absent from Current applied execution keys,
because Current was not written.  A recovery must keep Ledger rows and dedup
keys aligned; removing one without the other would create retry corruption.

## Pending State

Current Pending is already consumed:

```text
pending_plan_id = pending-order-plan-pending-composite-2023-06-08-9f82a489fae9
state = CONSUMED
plan_created_date = 2023-06-08
target_session_date = 2023-06-08
approved_item_ids =
  strategy-a6b6078330771c35ed8c
  strategy-d3fa60bc9fc3ccc7b3d6
  strategy-41ed66908c5c1dd4e695
  strategy-d2825eebf7c04286885b
```

All four items are `CONSUMED`.  Execution evidence says
`pending_consumed=false` and `pending_mutated=false`, so the consumed Pending
state likely came from Submit / lifecycle before the failed Current apply.

Recovery cannot safely retry execution while Pending remains consumed and old
Submit dedup keys remain present.

## Q1 Reservation Impact

The 2023-06-08 Submit artifact and current Pending predate Q1.  Submit guard
item evidence has:

```text
reference_price = None
reservation_price = None
reserved_notional = None
reservation_price_authority = None
```

The current Pending items also have those fields missing.  Therefore old
2023-06-08 Pending/Submit must not be reused as the recovery execution input if
the goal is to validate Q1/Q2 repaired behavior.  The 2023-06-08 day must be
replayed from at least `morning` so Planning/Pending/Submit are regenerated with
Q1 reservation semantics before Q2 Execution.

## Backup Analysis

Run-start backup:

`backup-historical-smoke-20260812T083932466210Z`

Scope:

```text
scope = resettable_trading_state_only
file_count = 8
runtime_root = .runtime
```

The backup restores the full resettable Trading State bundle.  Partial restore
is prohibited by `docs/03_operations/runtime_test_command_guide.md` and
`scripts/runtime_test.py`.

The backup content is not the desired 2023-06-07 checkpoint:

```text
backup state as_of = 2022-09-16
backup cash = 424,580
backup positions = 4
backup pending = 2022-09-16 CONSUMED one-item plan
```

Using this backup would discard the current run's 45 completed 2023 business
days and restore an older trading state.  It is valid as a pre-run preservation
artifact, but not as the Q3B primary recovery point.

## Existing Recovery Mechanism Assessment

Found:

- `backup`: copies `RESETTABLE_RELATIVE_PATHS`
- `rollback`: restores all `RESETTABLE_RELATIVE_PATHS`
- `resume`: replays jobs not recorded as successful in `run_state.json`
- `abandon`: evidence-only finalization

Not found:

- scoped business-date rollback
- execution transaction quarantine/supersede command
- official run_state rewind from a named day/job boundary
- official Pending retry restore for a consumed failed execution attempt
- official Ledger-ahead-of-Current repair for a single failed transaction

Therefore Q3B should not use manual JSONL deletion or ad hoc file edits.  It
should implement or use a formal production-common recovery mechanism that can
preserve the failed attempt while restoring/superseding only the failed
2023-06-08 attempt boundary.

## Recovery Options

| Option | Assessment |
| --- | --- |
| 1. Official Scoped Restore | Preferred shape, but no existing mechanism was found. Q3B should create/use this formally if implemented. |
| 2. Transaction-Aware Supersede / Reconcile | Viable and production-common if it records failed 6/8 Ledger rows as superseded/quarantined and restores retry authority without manual row deletion. Needs Q3B implementation. |
| 3. Previous Coherent Checkpoint Restore + Day Replay | Best target semantics: restore/supersede to 2023-06-07 coherent state, then replay 2023-06-08 from morning under Q1/Q2. Needs scoped mechanism. |
| 4. Full Run-Start Restore | Not recommended. Existing official rollback would restore 2022-09-16 state and lose the 45 completed days. |

## Q3B Recovery Plan

Recommended Q3B sequence:

1. Create a new pre-recovery safety backup of the current broken-but-evidenced
   `.runtime` state with the official backup command.
2. Verify the current broken state hashes and the 2023-06-08 mutation inventory
   before mutation.
3. Use a formal Q3B recovery mechanism, not manual edits, to mark the failed
   2023-06-08 execution transaction as superseded/quarantined or to restore a
   scoped 2023-06-07 coherent authority point.
4. The recovery mechanism must remove or supersede, as one logical unit, the
   2023-06-08 execution readonly Ledger rows, negative cash row, event row,
   consumed Pending state, and runtime current metadata that blocks replay.
5. Preserve 2023-06-08 failed attempt evidence under the run directory and write
   recovery lineage identifying it as failed/superseded.
6. Set retry authority through the official mechanism so `run_state` resumes at
   `2023-06-08:morning`, not `2023-06-08:execution`.
7. Re-run 2023-06-08 morning, sell_planning, submit, and execution under Q1/Q2
   code.  `market_refresh` and `data_readiness` do not need full replay unless
   the recovery mechanism invalidates their materialized authority.
8. Verify post-recovery invariants: Current/Ledger business date consistency,
   cash non-negative, positions consistent, Pending retry/terminal state valid,
   no duplicate execution keys, failed attempt retained as evidence, Q1
   reservation fields present, Q2 transaction evidence present.
9. Only after those checks should `RESUME_SAFE_NOW` be reconsidered.

## Post-Recovery Invariants Required

Q3B must prove:

```text
Current coherent
Ledger coherent
Current/Ledger business date consistent
cash consistent and non-negative
positions consistent
Pending retry state valid before replay and terminal state valid after replay
dedup state valid
no duplicate committed execution
failed 2023-06-08 attempt retained as evidence
run_state points to 2023-06-08:morning before replay
Q1 reservation fields present in regenerated 2023-06-08 Pending/Submit
Q2 transaction evidence present in regenerated 2023-06-08 Execution
```

## Validation

```text
Implementation changes = NONE
Runtime mutation = NONE
Recovery mutation = NONE
fresh-run = NOT RUN
resume = NOT RUN
long Historical = NOT RUN
RESUME_SAFE_NOW = NO
```
