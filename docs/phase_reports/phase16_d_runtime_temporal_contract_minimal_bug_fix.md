# Phase16-D Runtime v2 Temporal Contract Minimal Bug Fix

Prefix: `Phase16-D`  
Work name: `Runtime v2 Temporal Contract Minimal Bug Fix`  
Date: `2026-07-13`  
Final judgment: `PHASE16_D_RUNTIME_TEMPORAL_BUG_FIX_ACCEPTED`

## Root Cause

Phase16-C correctly identified that Runtime v2 had explicit `--business-date` and `--evaluation-time`, but not all normal-mainline components received the explicit evaluation time.

Root causes fixed in this phase:

- Pending lifecycle accepted `now`, but CLI did not pass `evaluation_time`.
- Pending lifecycle compared timezone-aware expiry timestamps as strings.
- Submit Pipeline did not accept `now` and wrote real UTC into Pending `updated_at` and Ledger order `created_at` / `recorded_at`.
- Several CLI-called components already accepted `now`, but the CLI did not pass `evaluation_time`.

This is not a Historical-only Runtime path. Defaults still use current time when `now` / `evaluation_time` is omitted.

## Changed Files

Runtime code:

- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/pending/lifecycle_runner.py`
- `src/ai_fund_lab_v2/runtime_v2/market_refresh/pipeline.py`

Tests:

- `tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py`
- `tests/runtime_v2/test_phase14e17_submit_pipeline_connection.py`

Reports:

- `docs/phase_reports/phase16_d_runtime_temporal_contract_minimal_bug_fix.md`
- `reports/phase_reports/phase16_d_runtime_temporal_contract_minimal_bug_fix.json`

## Unchanged Contracts

Unchanged:

- Runtime root policy.
- Current / Ledger / Pending authority boundaries.
- Submit source, Pending selection, Approval validation, Order conditions, Broker capability validation, Submit Guard, Broker write authority.
- Execution Processor.
- Current Apply.
- AI decision logic.
- Policy and Safety semantics.
- Physical audit timestamps for CLI run id, log timestamp, stage `created_at`, manifest `started_at` / `finished_at`.

## Clock Propagation Matrix

| Component | Change | Result |
|---|---|---|
| Pending lifecycle | CLI now passes `now=evaluation_time` | Explicit evaluation time controls `transitioned_at` and expiration. |
| Data Readiness | CLI now passes `now=evaluation_time` | Existing `now` path is used. |
| Market Refresh / Market Evidence | Market refresh pipeline now accepts `now`; CLI passes `evaluation_time` | Market evidence freshness can use explicit evaluation time. |
| Candidate / Opportunity BUY producer | CLI now passes `now=evaluation_time` | Existing `now` path is used for generated metadata/runtime id. |
| Position Management producer | CLI now passes `now=evaluation_time` | Existing `now` path is used. |
| Sell/Hold review-only producer | CLI now passes `now=evaluation_time` | Existing `now` path is used. |
| Submit Pipeline | Added optional `now` | Pending and Ledger submit timestamps can be deterministic. |

## Pending Lifecycle Fix

Changes:

- `run_daily_operation.py` now calls `run_pending_lifecycle_review(..., now=evaluation_time)`.
- `pending/lifecycle_runner.py` now parses `approval_expires_at` and `transitioned_at` as timezone-aware datetimes before comparison.

Effect:

- A 2021 Pending with `approval_expires_at=2021-07-05T15:00:00+09:00` does not expire at `evaluation_time=2021-07-05T09:00:00+09:00`.
- The same Pending expires correctly at `evaluation_time=2021-07-05T16:00:00+09:00`.
- `transitioned_at` records the explicit evaluation time normalized to UTC.

## Submit Pipeline Fix

Changes:

- `run_submit_pipeline(..., now: datetime | None = None)` was added.
- When `now` is provided, the normalized UTC timestamp is used for:
  - Pending `updated_at`
  - Ledger order `created_at`
  - Ledger order `recorded_at` through the existing ledger writer
- When `now` is omitted, the pipeline still uses current UTC as before.

Unchanged:

- Submit Guard.
- Broker adapter behavior.
- Ledger dedup key.
- Pending consume conditions.
- Approval / policy consistency checks.
- Broker capability checks.

## Normal Operation Compatibility

Normal operation remains compatible because all new time parameters are optional.

`now=None` behavior still falls back to `datetime.now(timezone.utc)` in Submit Pipeline and to existing fallback behavior in components that already had `now`.

## Historical Determinism

Added deterministic Submit test:

- Same Pending, Current, Policy, Safety, business date, and `evaluation_time`.
- Pending `updated_at` is identical.
- Ledger order `created_at` is identical.
- Ledger order `recorded_at` is identical.
- Semantic ledger order record is identical across isolated runs.

## Idempotency Regression

Regression passed:

- No double Submit.
- No double Ledger.
- No Pending double consume.
- No double PnL in round-trip acceptance.
- Current Apply second run remains `NOOP_ALREADY_APPLIED`.

## Current Hash Review

Classification: `CURRENT_HASH_REPRODUCIBILITY_PASS`

Evidence:

- This phase did not change Current-producing semantic fields or Current hash exclusions.
- Existing Current temporal and valuation tests with fixed time passed.
- Current Apply / round-trip idempotency regression passed.

Remaining note:

- Phase16-C noted that generic Current metadata is not globally excluded from Current hash. No new instability evidence was produced by this phase, so no hash exclusion change was made.

## Test Results

Targeted tests:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPYCACHEPREFIX=/private/tmp/pycache python3 -m pytest tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py tests/runtime_v2/test_phase14e17_submit_pipeline_connection.py
```

Result:

```text
17 passed
```

Phase15 regression:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPYCACHEPREFIX=/private/tmp/pycache python3 -m pytest tests/runtime_v2/test_phase15by2_authority_cleanup.py tests/runtime_v2/test_phase15bz_round_trip_acceptance.py tests/runtime_v2/test_phase15bo_isolated_submit_simulation.py tests/runtime_v2/test_phase15bm_safety_blocked_submit_path.py
```

Result:

```text
15 passed
```

Current hash / Current producer regression:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPYCACHEPREFIX=/private/tmp/pycache python3 -m pytest tests/runtime_v2/test_phase15ay_current_temporal_schema_migration.py tests/runtime_v2/test_phase15az_current_valuation_no_fill_producer.py
```

Result:

```text
31 passed
```

## Known Remaining Time Dependencies

Known remaining, intentionally unchanged:

- CLI physical audit metadata: run id, `started_at`, `finished_at`, stage `created_at`, log timestamp.
- Report `date.today()` fallback when report is called outside the normal CLI without `business_date`.
- Execution ReadOnly historical timing remains tied to the future Historical Simulated Broker prerequisite.

These are not blockers for the fixed items in Phase16-D.

## Active Runtime Mutation

`active .runtime mutation`: `NONE_OBSERVED`

All tests used pytest temporary roots. No Reset, Historical Simulation, 5 business day test, 2021 replay, AI retraining, active Current mutation, active Ledger mutation, or active Pending mutation was performed.

## Final Judgment

`PHASE16_D_RUNTIME_TEMPORAL_BUG_FIX_ACCEPTED`

Recommended next step:

- Re-audit Phase16 prerequisites after this fix.
- Do not start Reset, Historical Simulated Broker implementation, or 5 business day Historical Simulation from this prefix.
