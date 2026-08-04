# Phase26-B Post-Fill Cash / Valuation Authority Divergence Repair

## Primary Judgment

PHASE26_B_POST_FILL_CASH_VALUATION_AUTHORITY_REPAIRED

## Primary Root Cause

The 2023-01-18 execution job used different post-fill authorities for reconciliation:

- Historical broker snapshot cash was produced independently from Runtime-owned Current.
- Runtime-owned Current applied accepted fills to cash, but existing positions could retain older valuation rows.
- Reconciliation checked position quantity and cash/buying_power, but did not assert position market_value or total_equity consistency.

Evidence run:

- Run ID: `runtime-test-historical-smoke-20260803T223052578559Z`
- Failure date: `2023-01-18`
- Stage: `execution`
- Exit code: `20`
- Root reason: `reconciliation findings=2`

## Broken Edge

`HistoricalExecutionSnapshotProvider -> broker_readonly snapshot -> ledger position/cash records -> project_runtime_owned_fills_to_current -> run_reconciliation`

The broken edge was not a Submit, Strategy, Safety, or Guard problem. Submit produced two accepted filled orders and current apply was marked `APPLIED`; the mismatch appeared after execution evidence was normalized into broker snapshot and Runtime-owned Current.

## Canonical Authority

Cash authority:

- Runtime-owned Current cash plus accepted execution cash effects.
- No runtime_evaluation_capital fallback is used as current cash.

Valuation authority:

- Target business-date broker/market position evidence recorded through execution readonly ledger positions.
- Existing holdings and new holdings are projected into Current with the same business-date valuation source.

## Implementation

Changed:

- `src/ai_fund_lab_v2/runtime_v2/historical_support/environment.py`
  - Historical cash snapshot now requires current cash and records a date-scoped `cash_ref`.
  - BUY position projection skips already-applied execution evidence, matching cash and SELL idempotency.
  - Historical position snapshot refs are date-scoped so business-date valuation records are not deduped against stale prior-day records.

- `src/ai_fund_lab_v2/runtime_v2/asset/runtime_owned_fill_projection.py`
  - Runtime-owned open cost projection is seeded from current open cost before applying accepted fills.
  - Cash projection requires current cash and does not fall back to evaluation capital.

- `src/ai_fund_lab_v2/runtime_v2/reconcile/checks.py`
  - Added `POSITION_MARKET_VALUE_MISMATCH`.
  - Added `TOTAL_EQUITY_MISMATCH`.

- `src/ai_fund_lab_v2/runtime_v2/reconcile/reconciler.py`
  - Wires total equity reconciliation into the canonical reconciliation aggregate.

- `tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py`
  - Added PF26-B mixed SELL+BUY fixture covering post-fill cash, target-date valuation, total equity, and zero reconciliation findings.
  - Added negative reconciliation test for market value and total equity mismatch detection.

## Guard / Runtime Boundary

- Guard weakening: false
- Fallback added: false
- Historical-only suppression: false
- Strategy behavior changed: false
- Submit behavior changed: false
- Safety behavior changed: false
- `target_position_count` reintroduced: false

## Regression

- Compile: PASS
- Targeted unit: PASS
- Reconciliation regression: PASS
- Fresh-run/resume/3BD/10BD: not executed

Commands:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/historical_support/environment.py src/ai_fund_lab_v2/runtime_v2/asset/runtime_owned_fill_projection.py src/ai_fund_lab_v2/runtime_v2/reconcile/checks.py src/ai_fund_lab_v2/runtime_v2/reconcile/reconciler.py tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py
PYTHONPATH=src python3 -m pytest tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py::test_phase17_g_execution_snapshot_provider_emits_runtime_schema tests/runtime_v2/test_phase17_bv10_historical_sell_execution_projection.py
PYTHONPATH=src python3 -m pytest tests/runtime_v2/test_phase13_r_reconcile_positions_vs_asset.py tests/runtime_v2/test_phase13_q_ledger_projection.py tests/runtime_v2/test_phase13_q_broker_readonly_normalizer.py
```

## User Rerun Readiness

READY for user-run fresh 3BD rerun from a clean runtime-test root. Do not resume the failed run because it already applied Current/Ledger execution state and may create idempotency ambiguity.
