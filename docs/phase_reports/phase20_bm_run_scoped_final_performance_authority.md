# Phase20-BM Run-Scoped Final Performance Authority Audit and Fix

## Status

```text
PHASE20_BM_RUN_SCOPED_FINAL_PERFORMANCE_AUTHORITY_COMPLETE
```

Supporting judgments:

```text
RUN_SCOPED_SUMMARY_AUTHORITY_PASS
CURRENT_RUNTIME_ROOT_MISMATCH_NON_BLOCKING_FOR_PAST_RUN_PASS
LEGACY_BULL_PERFORMANCE_RECOVERED_FROM_RUN_SCOPED_EVIDENCE
LEGACY_BEAR_PERFORMANCE_RECOVERED_FROM_RUN_SCOPED_EVIDENCE
RANGE_NO_TRADE_PERFORMANCE_REMAINS_ZERO
PM_LIFECYCLE_LINKAGE_RECOVERED_FROM_RUN_SCOPED_FILL_OBSERVABILITY
FINAL_STATE_SNAPSHOT_AUTHORITY_ADDED_FOR_FUTURE_CLOSE
LONG_RUNNING_HISTORICAL_TEST_NOT_EXECUTED
```

## Scope

This phase audited and fixed `scripts/runtime_test.py summarize` for completed historical runs whose current `.runtime` no longer matches the run's `final_state_hashes`.

No Runtime, AI, Opportunity, PM, Risk, Capital Allocation, Broker, Accepted Generation, Training, Calibration, Validation, resume, or 20BD fresh-run logic was changed.

## Root Cause

`summarize` correctly compared the current `.runtime` hashes to the run's `final_state_hashes`, but incorrectly treated mismatch as a blocking condition for all past-run summary evidence.

Effects:

- `runtime_judgment` became `BLOCKED`.
- final equity became unavailable.
- order plans, executions, trade attribution, and lifecycle checks were zeroed or unresolved.
- run-scoped `fills.json`, `realized_slices.json`, `position_campaigns.json`, and `pm_decisions.json` were not used as the primary past-run performance authority.

Classification:

```text
SUMMARY_READER_AUTHORITY_BUG
CURRENT_RUNTIME_ROOT_FALSE_PRIMARY_FOR_PAST_RUN
```

## Fix

Implemented:

- Current root hash mismatch is now informational for past-run performance when run-scoped evidence exists.
- `summarize` now loads run-scoped performance observability before trading/performance/lifecycle aggregation.
- When current `.runtime` does not match, execution and execution-equivalent plan counts are reconstructed from run-scoped fill observability.
- Final performance for legacy Phase20-J+ runs is derived from deduplicated latest `position_campaigns.json` snapshots.
- No-trade runs with retained run-scoped evidence derive zero return without inference.
- Lifecycle consistency can pass from run-scoped position campaign authority for past-run summaries.
- Future `close` / `abandon` writes a run-scoped `final_state_snapshot` manifest, and `summarize` can use a verified snapshot ahead of derived evidence.

## Authority Priority

`summarize` now follows:

```text
1. Verified run-scoped final state snapshot
2. Current .runtime only when current hashes equal final_state_hashes
3. Run-scoped position campaign / fill derivation
4. Run-scoped no-trade derivation
5. NOT_AVAILABLE / REVIEW_REQUIRED
```

Legacy Bull/Bear runs did not retain final state snapshots, so they use `DERIVABLE_EXACT_FROM_RUN_SCOPED_POSITION_CAMPAIGNS`.

## Probe Results

Artifact:

```text
reports/phase20_bm_run_scoped_final_performance_authority/probe_summary.json
```

| Regime | Run | Runtime root detail | Final equity | Return | Realized | Unrealized | Executions | Lifecycle |
|---|---|---|---:|---:|---:|---:|---|---|
| BULL | `runtime-test-historical-extended-smoke-20260723T215847198556Z` | `CURRENT_RUNTIME_ROOT_FINAL_HASH_MISMATCH` | 954880.0 | -45120.0 (-4.512%) | -45420.0 | 300.0 | BUY 5 / SELL 10 | PASS |
| BEAR | `runtime-test-historical-extended-smoke-20260723T225746889854Z` | `CURRENT_RUNTIME_ROOT_FINAL_HASH_MISMATCH` | 1088280.0 | 88280.0 (8.828%) | 88280.0 | 0.0 | BUY 5 / SELL 11 | PASS |
| RANGE | `runtime-test-historical-extended-smoke-20260724T030527368584Z` | `CURRENT_RUNTIME_ROOT_FINAL_HASH_MATCH` | 1000000.0 | 0.0 (0.0%) | 0.0 | 0.0 | none | PASS |

Bull/Bear findings are informational only:

```text
RUN_FINAL_STATE_HASH_MISMATCH
CURRENT_RUNTIME_ROOT_LEDGER_NOT_USED_FOR_PAST_RUN
```

## Changed Files

```text
scripts/runtime_test.py
tests/runtime_v2/test_phase20_bm_run_scoped_final_performance_authority.py
docs/phase_reports/phase20_bm_run_scoped_final_performance_authority.md
reports/phase_reports/phase20_bm_run_scoped_final_performance_authority.json
reports/phase20_bm_run_scoped_final_performance_authority/probe_summary.json
```

## Validation

Executed:

```text
PYTHONPYCACHEPREFIX=/private/tmp/pycache PYTHONPATH=src:. python3 -m py_compile scripts/runtime_test.py
PYTHONPYCACHEPREFIX=/private/tmp/pycache PYTHONPATH=src:. python3 -m pytest -q tests/runtime_v2/test_phase20_bm_run_scoped_final_performance_authority.py
PYTHONPYCACHEPREFIX=/private/tmp/pycache PYTHONPATH=src:. python3 -m pytest -q tests/runtime_v2/test_phase20_bm_run_scoped_final_performance_authority.py tests/runtime_v2/test_phase20_j_performance_observability.py tests/runtime_v2/test_phase20_k_performance_observability_consumer.py tests/runtime_v2/test_phase19_bv_runtime_test_summarize.py
```

Short `summarize` probes were executed for Bull, Bear, and Range. Long Historical, Broker, Training, Calibration, Validation, resume, and Accepted Generation changes were not executed.
