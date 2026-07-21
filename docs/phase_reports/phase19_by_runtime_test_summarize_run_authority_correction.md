# Phase19-BY Runtime Test Summarize Run Authority Correction

## Summary

`runtime_test.py summarize --run-id <RUN_ID>` was corrected so event aggregation is bounded to the requested Runtime Test Run.

Final judgment:

```text
PHASE19_BY_SUMMARIZE_RUN_AUTHORITY_CORRECTION_PASS
```

## Problem

The confirmed 1BD run was:

```text
runtime-test-historical-smoke-20260721T224645728185Z
```

Its completed business days were:

```text
["2026-07-14"]
```

Runtime execution itself completed normally:

- PM decision count: 0
- PM status: NO_POSITION
- SELL Planning: NO_POSITION
- SELL execution count: 0
- BUY execution count: 5
- final positions: 5

Before this correction, `summarize` scanned shared `.runtime` Runtime State directories and incorrectly included old SELL artifacts outside the requested Run period, such as:

- `.runtime/runtime_state/sell_pipeline/2026-06-18/order_plan.json`
- `.runtime/runtime_state/sell_pipeline/2026-06-19/order_plan.json`
- `.runtime/runtime_state/sell_pipeline/2026-06-22/order_plan.json`
- `.runtime/runtime_state/sell_pipeline/2026-06-30/order_plan.json`

That made the summary report unrelated historical SELL plans for a 1BD no-position run.

## Root Cause

The defect was in the summarize command's event aggregation authority, not in Runtime execution.

Old behavior:

- PM decisions were collected from `.runtime/runtime_state/position_management/*`.
- BUY plans were collected from `.runtime/runtime_state/morning_pipeline/*`.
- SELL plans were collected from `.runtime/runtime_state/sell_pipeline/*`.
- Ledger orders/executions were read from the current persistent ledger without Run-day filtering.

This violated the Run Authority Contract because shared `.runtime` can contain artifacts from other runs or prior dates.

## Run Authority Contract

The corrected summarize authority is:

1. Use `reports/runtime_tests/runs/<RUN_ID>/daily/<DATE>/<JOB>/` Run-scoped evidence whenever it exists.
2. Use `run_state.json` to determine `completed_business_days`.
3. Use `final_summary.json` to verify final Runtime State hash consistency.
4. Use current `.runtime` only for final state and event details when final hashes match and event `business_date` is inside `completed_business_days`.

Event aggregation must not use shared `.runtime` solely because an artifact exists there.

For SELL Plan and PM Decision aggregation:

- `business_date` must be in `completed_business_days`.
- Run-scoped evidence with the requested `runtime_test_run_id` or matching evidence root is preferred.
- For a Run-scoped PM no-position day, same-day stale SELL plans are excluded from the summary.

## Code Changes

Updated:

- `scripts/runtime_test.py`
- `tests/runtime_v2/test_phase19_bv_runtime_test_summarize.py`

Main changes:

- Added `completed_business_days` filtering to PM decisions, BUY plans, SELL plans, orders, and executions.
- Added Run-scoped PM evidence reading from `daily/<DATE>/sell_planning/position_management_evidence.json`.
- Added Run-scoped sell planning manifest checks for no-position / zero PM decision days.
- Added `event_collection_authority` to the summary payload.
- Kept final `.runtime` state usage limited by final hash match.
- Updated lifecycle consistency semantics so zero upstream and zero downstream events pass.
- Expanded pending consistency so consumed, terminalized, empty, or execution-explained pending state is accepted.

## Before / After

| Field | Before | After |
|---|---:|---:|
| completed_business_days | `["2026-07-14"]` | `["2026-07-14"]` |
| PM decisions | 0 | 0 |
| PM EXIT | incorrectly influenced by old SELL plans | 0 |
| PM REDUCE | incorrectly influenced by old SELL plans | 0 |
| SELL Plan | 7 | 0 |
| SELL Submit | 0 | 0 |
| SELL Execution | 0 | 0 |
| Runtime judgment | REVIEW_REQUIRED | PASS |

## Target Run Re-Summary

Command executed:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py summarize \
  --run-id runtime-test-historical-smoke-20260721T224645728185Z \
  --write-evidence --json
```

Generated evidence:

```text
reports/runtime_tests/summaries/runtime-test-summary-runtime-test-historical-smoke-20260721T224645728185Z-20260721T230200658392Z
```

Observed result:

| Metric | Value |
|---|---:|
| business_days | 1 |
| completed date | 2026-07-14 |
| PM decisions | 0 |
| PM EXIT | 0 |
| PM REDUCE | 0 |
| BUY Plan | 5 |
| BUY Submit | 5 |
| BUY Execution | 5 |
| SELL Plan | 0 |
| SELL Submit | 0 |
| SELL Execution | 0 |
| Current Positions | 5 |
| Final Equity | 1,011,400 |
| Return | +11,400 |
| Return Percent | +1.14% |

Judgments:

| Judgment | Value |
|---|---|
| Runtime execution status | PASS |
| Summarize status | PASS |
| Run Authority status | PASS |
| Lifecycle consistency status | PASS |
| Performance judgment | NOT_EVALUATED |
| Strategy judgment | NOT_EVALUATED |
| Phase19 closure readiness | READY |

Lifecycle consistency:

| Check | Result |
|---|---|
| PM_EXIT_TO_SELL_PLAN | PASS |
| PM_REDUCE_TO_PARTIAL_SELL_PLAN | PASS |
| SELL_PLAN_TO_SUBMIT | PASS |
| SELL_SUBMIT_TO_EXECUTION | PASS |
| LEDGER_TO_CURRENT | PASS |
| PENDING_EMPTY_OR_EXPLAINED | PASS |

## Regression Tests

Executed:

```bash
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase19_bv_runtime_test_summarize.py
```

Result:

```text
8 passed in 1.68s
```

Syntax check:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m py_compile scripts/runtime_test.py
```

Result:

```text
PASS
```

Coverage added or preserved:

- 1BD no-position run produces PM 0 / SELL 0 and Runtime PASS.
- Shared `.runtime` old SELL plans outside the Run period are excluded.
- Valid in-period REDUCE/EXIT SELL chain remains PASS.
- Missing in-period SELL linkage remains REVIEW_REQUIRED.
- Zero-event lifecycle checks are not treated as false.

## Impact

Runtime execution behavior was not changed.

No changes were made to:

- Runtime BUY logic
- Runtime SELL logic
- Position Management policy
- Accepted Generation
- Training
- Calibration
- Validation
- Historical execution behavior
- Broker behavior
- Safety behavior
- fresh-run/reset behavior

The correction is limited to `runtime_test.py summarize` aggregation and consistency reporting.

## Final Judgment

```text
PHASE19_BY_SUMMARIZE_RUN_AUTHORITY_CORRECTION_PASS
```

Phase19 closure remains ready. This fix improves evidence truthfulness and prevents a Runtime Test summary from attributing shared `.runtime` artifacts from other dates or runs to the requested Run.
