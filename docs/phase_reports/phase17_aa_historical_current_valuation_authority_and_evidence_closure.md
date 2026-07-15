# Phase17-AA Historical Current Valuation Authority and Evidence Closure

## Judgment

`PHASE17_AA_HISTORICAL_CURRENT_VALUATION_ACCEPTED`

This phase did not rerun, resume, reset, rollback, or mutate the Frozen Evidence run
`runtime-test-historical-smoke-20260715T003301564910Z`.

## Scope

Phase17-AA investigated the Historical Runtime stop at `current_valuation_refresh` for
`2026-07-06`. The target run had already passed execution simulation and then stopped with:

- `current_valuation_refresh_status`: `REVIEW_REQUIRED`
- `current_valuation_position_count`: `5`
- `current_valuation_valued_position_count`: `0`
- `current_valuation_new_total_market_value`: `808400.0`
- `current_valuation_market_date`: empty
- `current_valuation_market_evidence_path`: empty
- `safety_status`: `SAFETY_MISSING`

The run-scoped historical market authority existed and was PASS:

- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260715T003301564910Z/daily/2026-07-06/market_refresh/historical_asof_view.json`
- `business_date`: `2026-07-06`
- `latest_available_market_date`: `2026-07-06`
- `normalized_ohlcv`: `PASS`

## Root Cause Classification

1. Runtime Bug: `valued_position_count` was coupled to final `READY` status. A review-required artifact could therefore report zero valued rows even when candidate valuation totals existed.
2. Authority Bug: current valuation only loaded `.runtime/runtime_state/market` evidence and did not accept run-scoped `historical_asof_view.json`.
3. Temporal Authority Bug: current valuation ran before historical Data Readiness safety authority propagation, so it consumed missing latest safety evidence.
4. Integration Bug: Runtime Test evidence was not written under `daily/<date>/current_valuation_refresh/`.

No Historical-only relaxation was added. The fixes are Production Runtime requirements: valuation counts must reflect actual evidence, market evidence must be explicit, safety authority must gate apply, and run-scoped evidence must be inspectable.

## Implementation

Updated `src/ai_fund_lab_v2/runtime_v2/current_state/valuation.py`:

- Added explicit `market_evidence_path` support.
- Converted `phase17_l_historical_asof_view_v1` normalized OHLCV authority into quote evidence.
- Added runtime-test/environment/safety authority review checks.
- Made apply readiness require complete valuation evidence without changing valuation count semantics.
- Preserved cash, buying power, realized PnL, and quantities in valuation-only refresh.

Updated `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`:

- Runs Historical current valuation after Data Readiness safety propagation.
- Passes run-scoped historical as-of market evidence into current valuation.
- Writes current valuation Runtime Test evidence files for manifest, environment, safety, market, projection, apply, and external-effect audit.

Added `tests/runtime_v2/test_phase17_aa_historical_current_valuation_authority.py`.

## Evidence

Evidence directory:

`reports/phase17_aa_historical_current_valuation_authority_and_evidence_closure/`

Files:

- `frozen_run_observation.json`
- `root_cause_classification.json`
- `valuation_count_inconsistency.json`
- `market_evidence_authority_decision.json`
- `historical_safety_authority_decision.json`
- `apply_contract.json`
- `external_effect_audit.json`
- `test_summary.json`

Machine-readable summary:

`reports/phase_reports/phase17_aa_historical_current_valuation_authority_and_evidence_closure.json`

## Verification

Passed:

```bash
python3 -m pytest tests/runtime_v2/test_phase17_aa_historical_current_valuation_authority.py tests/runtime_v2/test_phase15az_current_valuation_no_fill_producer.py -q
```

Result: `20 passed`

Passed:

```bash
python3 -m pytest tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py tests/runtime_v2/test_phase17_k_runtime_test_runner.py -q
```

Result: `20 passed`

Passed:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/phase17aa_pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/current_state/valuation.py src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py scripts/runtime_test.py tests/runtime_v2/test_phase17_aa_historical_current_valuation_authority.py
```

The first `py_compile` attempt without `PYTHONPYCACHEPREFIX` failed because the sandbox could not write to `/Users/negishi/Library/Caches`; rerunning with an allowed cache directory passed.

## External Effects

- Frozen Run changed: no
- Runtime rerun/resume/reset/rollback: no
- Demo write: no
- Production access: no
- Broker order API calls: 0
- Notification delivery calls: 0
- J-Quants API fetch calls: 0
- Registry mutation: no
- Model retraining: no
