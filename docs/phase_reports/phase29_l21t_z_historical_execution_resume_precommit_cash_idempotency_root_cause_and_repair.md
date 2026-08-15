# Phase29-L21T-Z Historical Execution Resume Pre-Commit Cash Idempotency Root Cause and Repair

## Primary Judgment

`PHASE29_L21T_Z_PRE_COMMIT_EXECUTION_CASH_IDEMPOTENCY_REPAIRED_FOCUSED_REGRESSION_PASS`

## Scope

READ-ONLY ROOT-CAUSE INVESTIGATION FIRST, followed by a minimal
Production-common Runtime repair after the root cause was proven.

Codex did not run target resume, fresh-run, replay, recovery, or long
Historical.  Codex did not manually edit Pending, Ledger, Current, runtime
state, or target run evidence.

Target run:

```text
runtime-test-historical-smoke-20260812T212155604711Z
```

Target date:

```text
2023-06-23
```

## Root Cause

`PRE_COMMIT_PROJECTION_REAPPLIES_ALREADY_COMMITTED_EXECUTIONS`

The 2023-06-23 resume Execution generated the same three logical
execution-equivalent records that were already committed to Persistent Ledger
and already represented in Current.  The downstream runtime-owned Current
projection already had idempotency authority through
`runtime_owned_projection.applied_execution_ids` and
`runtime_owned_projection.applied_execution_dedup_keys`, but the pre-commit cash
feasibility guard ran before that projection and did not consult those applied
execution identities.

As a result, pre-commit cash feasibility subtracted/added already-applied
executions from the already-post-execution cash balance and halted before the
existing projection idempotency could no-op the retry.

This is not an L21T-X reconciliation failure.  L21T-X removed the earlier
reconciliation findings; the latest manifest shows:

```text
reconcile_status = NOT_EXECUTED
reconcile_findings = 0
```

## Exact Candidate Cash Arithmetic

Latest failed resume manifest:

```text
pre_commit_starting_cash = 129889.99999999999
aggregate_candidate_sell_notional = 4900.0
aggregate_candidate_buy_notional = 145440.0
candidate_projected_cash = -10650.000000000015
```

The full arithmetic is:

```text
129889.99999999999
+ 4900.0
- 23200.0
- 122240.00000000001
= -10650.000000000015
```

Candidate executions:

| Symbol | Side | Quantity | Price | Cash effect | Execution id | Already in Ledger | Already in Current |
| --- | --- | ---: | ---: | ---: | --- | --- | --- |
| `37820` | `SELL` | `100` | `49.0` | `+4,900` | `execution-equivalent:sha256:04e6194ff59cbea8f256ab15aad9016b7e37e34908cbd057b315e03ba5d9d6bb` | YES | YES |
| `76470` | `BUY` | `800` | `29.0` | `-23,200` | `execution-equivalent:sha256:d829d408ce8323e1dfa01c9ceca25ba186fab62c4eb90910d4d4ced8bbf8387b` | YES | YES |
| `94340` | `BUY` | `800` | `152.8` | `-122,240.00000000001` | `execution-equivalent:sha256:0117737d9885286c80d015c627b09a653b621e138a554c715a0ba1dcffb4f9bb` | YES | YES |

All three candidate execution ids and dedup keys were found in
`.runtime/persistent_ledger/state.json` under Current
`runtime_owned_projection.applied_execution_ids` and
`applied_execution_dedup_keys`.

## Previous Execution Attempt vs Resumed Attempt

Previous committed attempt, as represented by Persistent Current:

```text
cash = 129889.99999999999
buying_power = 129889.99999999999
market_value = 947170.0
total_equity = 1077060.0
positions = 8
```

The same 2023-06-23 executions are already reflected in Current:

```text
37820 quantity = 500
76470 quantity = 3700
94340 quantity = 800
```

Latest resumed attempt:

```text
runtime run_id = runtime-v2-execution-2023-06-23-20260813T220945.987104+0000
orders_count = 3
executions_count = 3
fill_count = 3
execution_equivalent_count = 3
persistent_commit_started = false
persistent_commit_completed = false
```

The resumed attempt regenerated the same logical execution-equivalent ids for
the same order set.  Before this repair, pre-commit cash feasibility selected
all three into candidate cash projection despite their already-applied Current
identity.

## Already-Applied Execution Detection Status

Before:

```text
Runtime-owned Current projection: checks applied_execution_ids/dedup_keys
Pre-commit cash feasibility: does not check applied_execution_ids/dedup_keys
```

After:

```text
Pre-commit cash feasibility:
  reads Current applied_execution_ids
  reads Current applied_execution_dedup_keys
  excludes already-applied candidate executions from cash arithmetic
  still validates side and still fails closed for real new cash insufficiency
```

The repair does not delete candidate evidence.  Each pre-commit item now records
whether it was already applied and whether it was selected into candidate cash
projection.

## Idempotency Authority

The idempotency authority is the logical execution identity already persisted in
Current:

```text
runtime_owned_projection.applied_execution_ids
runtime_owned_projection.applied_execution_dedup_keys
top-level applied_execution_ids / applied_execution_dedup_keys when present
execution_references when present
```

For execution-equivalent records, the dedup key has the form:

```text
runtime_v2_execution_equivalent:<order_ref_hash>
```

This is Production-common runtime identity.  The repair is not Historical-only
and does not hardcode run id, business date, symbol, or execution id.

## Pending Lifecycle Status

Current pending:

```text
pending_plan_id = pending-order-plan-pending-composite-2023-06-23-7ead15f5b4c7
state = CONSUMED
plan_overall_status = APPROVED
consume.consumed = true
consume_reason = runtime_v2 submit accepted; automatic resubmit forbidden
approved_item_ids =
  strategy-89303368cacd90a268c6
  strategy-86ecd0d63340ec83fb45
  opi-sell-reduce-pm-37820-001
```

The repair does not make a consumed Pending resubmittable.  It only prevents
already-applied executions from being re-counted by the Execution pre-commit
cash guard.

## Ledger Mutation Status

Latest failed resume attempt did not append additional Ledger records:

```text
ledger_orders_appended = 0
ledger_executions_appended = 0
ledger_positions_appended = 0
ledger_cash_appended = 0
persistent_commit_started = false
persistent_commit_completed = false
```

Read-only record counts/hashes observed during this task:

| File | Count | SHA-256 |
| --- | ---: | --- |
| `.runtime/persistent_ledger/state.json` | `1` | `c279145d456a79acbfb0f85999724fcdd67e8ebb8fda1fd09470cb5e0901ddf7` |
| `.runtime/persistent_ledger/orders.jsonl` | `290` | `9d15d23d14df8fbc3a84635f9fb1fa847864fefd569f804052fd8321d17a39f0` |
| `.runtime/persistent_ledger/executions.jsonl` | `145` | `1786e15d62cc4f0dfaca058091fe6ad96f79622e35ebe98dfbeb432319d6187e` |
| `.runtime/persistent_ledger/positions.jsonl` | `457` | `cd8bccb3b835c99a34df0de389bfe0aadf442c86ef3400f05c11f720fed68f1d` |
| `.runtime/persistent_ledger/cash.jsonl` | `100` | `3630ae820304e80f74ac3304f63f588bab90185b9f6a27b7481deb1447aedd25` |

No manual repair or rollback was performed.

## Current Mutation Status

The latest failed resume attempt reported:

```text
current_apply_status = NOT_EXECUTED
current_apply_reason = pre-commit execution cash feasibility failed
asset_current_written = false
```

Therefore the latest failed resume did not apply a new Current projection.

## SELL Independence Impact

SELL independence is preserved.  A valid SELL/REDUCE execution remains eligible
when it is new.  An already-applied SELL/REDUCE execution is not re-applied on
resume and therefore does not double-add cash.

This separates:

```text
SELL continuation authority
```

from:

```text
SELL duplicate execution prevention
```

## Production / Demo / Historical Architecture Impact

The repair is Production-common in the Execution pre-commit cash feasibility
guard.  It applies to all modes that use runtime-owned Current projection
identity and does not bypass cash feasibility for Historical.

Real new BUY overspend remains fail-closed:

```text
candidate execution cash projection negative -> REVIEW_REQUIRED
```

## Files Changed

- `src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py`
- `tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py`
- `docs/phase_reports/phase29_l21t_z_historical_execution_resume_precommit_cash_idempotency_root_cause_and_repair.md`

## Tests

Focused regression:

```text
PYTHONPATH=src python3 -m pytest tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py -k "l21t_z or l21t_q1 or l21t_q2"
6 passed
```

Execution suite:

```text
PYTHONPATH=src python3 -m pytest tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py
16 passed
```

Runtime-owned fill projection / Current apply:

```text
PYTHONPATH=src python3 -m pytest tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py tests/runtime_v2/test_phase15bv_execution_normalization_current_apply.py
20 passed
```

Pending lifecycle / runtime runner:

```text
PYTHONPATH=src python3 -m pytest tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py tests/runtime_v2/test_phase17_k_runtime_test_runner.py
64 passed
```

Compile:

```text
PYTHONPYCACHEPREFIX=/private/tmp/pycache-l21tz python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py
PASS
```

## Regression Result

The new regression proves:

- already-applied BUY and SELL candidates are excluded from pre-commit cash
  arithmetic;
- mixed already-applied and unapplied candidates apply only the unapplied cash
  effect;
- retry after a committed BUY with low remaining cash does not create an
  artificial negative candidate cash;
- duplicate ledger/order/execution/position/cash append remains zero on retry;
- real new cash-insufficient BUY remains `REVIEW_REQUIRED`.

## Safety Decisions

Direct Resume Safe:

```text
YES_AFTER_L21T_Z_PATCH_AND_SHORT_REGRESSION
```

Recovery Required:

```text
NO
```

Manual Pending Edit Required:

```text
NO
```

Long Historical Executed By Codex:

```text
NO
```

## Remaining Risks

The target run was not resumed by Codex, so the exact target resume result must
still be operator-observed.  Based on code path and focused regression, the
same already-applied 2023-06-23 executions should be excluded from pre-commit
cash projection and should not double-apply Ledger or Current effects.
