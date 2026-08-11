# Phase29-L4-D Dry-Run Request Conformance Root Cause Repair

## Status

COMPLETE

ROOT CAUSE AUDIT COMPLETE

NARROW PRODUCTION-COMMON REPAIR COMPLETE

SHORT REGRESSION PASS

NO CONFIG CHANGE

NO SCHEMA CHANGE

NO STRATEGY CHANGE

NO RUNTIME CANONICAL DATA MUTATION

NO HISTORICAL EXECUTION

## Primary Judgment

PHASE29_L4_D_DRY_RUN_REQUEST_CONFORMANCE_CONTRACT_REPAIRED_SHORT_REGRESSION_PASS_L4_C2_READY

## Root Cause

Phase29-L4-C found this inconsistency:

```text
planner request_conformance_status = PASS
fresh-run top-level request_conformance_status = NOT_PASS
independent_acceptance.requested_window_conformance_judgment = NOT_PASS
```

The root cause was not stale 979 semantics, not a literal requested-end mismatch, and not legacy calendar authority.

The defect was in `scripts/runtime_test.py` fresh-run summary conformance logic:

```text
requested_business_days == resolved_business_day_count == completed_business_day_count
```

That is valid for an executed run, but invalid for `--dry-run`, where
`completed_business_day_count = 0` by design. The dry-run planner had already
resolved the canonical trading window and produced `request_conformance_status =
PASS`, but the top-level summary and independent acceptance recomputed
conformance using completed days and overwrote it to `NOT_PASS`.

Classification:

```text
D-B fresh-run admission contract defect
INDEPENDENT_ACCEPTANCE_STALE_CONTRACT
```

## Repair

Added shared fresh-run conformance helper semantics:

```text
dry-run:
  consume canonical planner request_conformance_status

actual run:
  require requested_business_days == resolved_business_day_count ==
  completed_business_day_count and window_resolution_status == PASS
```

This keeps real execution acceptance strict while making dry-run conformance
reflect canonical request-to-trading-calendar resolution.

No 977-specific or date-specific exception was introduced.

## Verification

Re-run dry-run:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-smoke \
  --date-from 2022-08-10 \
  --date-to 2026-08-09 \
  --initial-cash 1000000 \
  --dry-run \
  --json
```

After repair:

```text
resolved_date_from = 2022-08-10
resolved_date_to = 2026-08-07
resolved_business_day_count = 977
planner request_conformance_status = PASS
independent_acceptance requested_window_conformance_judgment = PASS
top-level request_conformance_status = PASS
window_resolution_status = PASS
dry_run_no_mutation = true
historical_executed = NO
```

## Regression

Focused:

```bash
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase29_l4_d_dry_run_conformance.py
```

Result:

```text
6 passed
```

Broader bounded:

```bash
PYTHONPATH=src python3 -m pytest -q \
  tests/runtime_v2/test_phase29_l4_b_authority_materialization.py \
  tests/runtime_v2/test_phase17_bv6_historical_replay_operator_range.py \
  tests/runtime_v2/test_phase17_k_runtime_test_runner.py
```

Result:

```text
34 passed
```

Compile:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache \
PYTHONPATH=src python3 -m py_compile scripts/runtime_test.py
```

Result:

```text
PASS
```

## Non-Regression

L4-A post-commit warmup authority preserved: YES.

L4-B Listed PIT preserved: YES.

L4-B Calendar 977 preserved: YES.

Quote/calendar ambiguity: 0.

ADD semantics unchanged: YES.

Strategy changed: NO.

Config changed: NO.

Runtime canonical data mutated: NO.

Historical executed: NO.

## Evidence

Evidence root:

`reports/phase29_l4_d_dry_run_request_conformance_root_cause_repair/`

Files:

- `root_cause.json`
- `planner_vs_top_level_flow.json`
- `independent_acceptance_audit.json`
- `implementation_summary.json`
- `dry_run_before_after.json`
- `regression_results.json`
- `non_regression_matrix.json`
- `phase29_l4_c2_entry_gate.json`

## Gate

Phase29-L4-C2 entry gate: READY.

Fresh 977BD Ready: NO pending L4-C2.

Recommended next action:

```text
Run Phase29-L4-C2 read-only final gate. Do not execute the 977BD long Historical
fresh-run from L4-D.
```
