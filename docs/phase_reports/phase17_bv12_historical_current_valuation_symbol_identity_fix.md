# Phase17-BV12 Historical Current Valuation Symbol Identity Normalization Fix

## Executive Summary

Phase17-BV12 fixed the Current Valuation symbol identity bug that converted canonical Runtime symbols ending in `0` from 5 digits to 4 digits.

The direct root cause was:

```text
src/ai_fund_lab_v2/runtime_v2/current_state/valuation.py::_normalize_symbol
```

Before the fix, `_normalize_symbol("36810")` returned `3681`, and `_normalize_symbol("186A0")` would return `186A`. That function was used for both Runtime position symbols and Historical normalized OHLCV quote symbols. This mixed provider/display normalization with Runtime-owned canonical identity.

After the fix, Current Valuation canonical normalization only trims whitespace and removes the `.T` suffix. It no longer strips the trailing `0` from 5-character issue codes.

Symbol identity fix judgment:

```text
PHASE17_BV12_HISTORICAL_CURRENT_VALUATION_SYMBOL_IDENTITY_ACCEPTED
```

Fresh rerun safety judgment:

```text
FRESH_RERUN_REVIEW_REQUIRED_ACTUAL_36810_QUOTE_ABSENT
```

Reason: the identity bug is fixed, but read-only inspection of current Historical OHLCV data showed `36810` exists through `2026-06-30` and is absent for `2026-07-01`. A fresh rerun may therefore progress from the old incorrect `missing_symbols=["3681"]` to a fail-closed genuine missing quote for canonical `36810`. This is not solved by symbol normalization and must not be hidden by a stale-price fallback.

## Halt Evidence

Target Run:

```text
runtime-test-historical-extended-smoke-20260716T213021655422Z
```

Stop boundary:

```text
2026-07-01:current_valuation_refresh
exit_code=20
```

Observed Run Evidence:

```text
position_count=4
projection_status=REVIEW_REQUIRED
apply_status=NOT_EXECUTED
valued_position_count=0
missing_symbols=["3681"]
missing_evidence=["3681", "current_valuation_quote_missing", "quote_status_not_allowed"]
```

Execution immediately before Current Valuation was healthy:

```text
fill_count=1
ledger_executions_appended=1
ledger_positions_appended=1
reconcile_status=PASS
current_apply_status=APPLIED
projected_position_count=4
projected_cash=411300.0
realized_pnl=-10000.0
```

BV9 SELL quantity authority and BV10 SELL execution projection are not the root cause.

## Root Cause

The code path was:

```text
build_current_valuation_candidate
  -> runtime_positions required_symbols={_symbol(position)}
  -> _symbol
  -> _normalize_symbol
  -> "36810" -> "3681"

_market_evidence_from_historical_asof_view
  -> _quotes_from_parquet
  -> _normalize_symbol(row["Code"])
  -> quote_payload keyed by normalized symbol
```

The problematic code was:

```python
if text.endswith("0") and len(text) == 5:
    text = text[:-1]
```

This was an ambiguous display/provider conversion embedded inside Current Valuation identity handling. It also would corrupt alpha-containing symbols such as `186A0`.

## Canonical Runtime Symbol Contract

Runtime-owned state continues to use canonical Runtime symbols:

```text
33500
36810
186A0
31340
70630
```

The following artifacts must not rewrite those identities:

- Current
- Persistent Ledger
- Pending
- Order
- Execution
- Current Valuation candidate positions
- Current Valuation missing_symbols

Provider-specific lookup conversion, if ever needed, must remain at a provider adapter boundary and must be explicit. BV12 does not introduce a broad fallback from `36810` to `3681`.

## Provider Lookup Symbol Contract

Historical normalized OHLCV quotes are now read into Current Valuation with their canonical code preserved, except for `.T` suffix cleanup.

Allowed Current Valuation symbol cleanup:

```text
"7203.T" -> "7203"
"36810" -> "36810"
"186A0" -> "186A0"
```

Disallowed:

```text
"36810" -> "3681"
"186A0" -> "186A"
int(symbol)
symbol.rstrip("0")
symbol[:-1]
```

Existing lookup support for a 4-digit Runtime symbol finding a 5-digit quote key via `symbol + "0"` was not expanded and was not used to weaken missing quote checks.

## Fix

Changed:

```text
src/ai_fund_lab_v2/runtime_v2/current_state/valuation.py
```

`_normalize_symbol()` no longer strips the final `0` from 5-character symbols. Runtime position identity and Historical quote identity now stay aligned when the market evidence carries 5-character J-Quants codes.

BV9 and BV10 code paths were not modified.

## Before / After Projection

Before:

```text
position symbol=36810
required_symbols includes 3681
missing_symbols=["3681"]
projection_status=REVIEW_REQUIRED
apply_status=NOT_EXECUTED
```

After, with Historical market evidence containing `36810`:

```text
position symbol=36810
quote key=36810
missing_symbols=[]
projection_status=PASS
apply_status=APPLIED
valued_position_count=1
candidate symbol=36810
```

After, with Historical market evidence containing `186A0`:

```text
position symbol=186A0
quote key=186A0
missing_symbols=[]
projection_status=PASS
apply_status=APPLIED
candidate symbol=186A0
```

After, with genuine missing quote:

```text
position symbol=36810
quote absent
missing_symbols=["36810"]
projection_status=REVIEW_REQUIRED
apply_status=NOT_EXECUTED
```

## Actual Data Audit

Read-only inspection of:

```text
.runtime/operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet
.runtime/operations/jquants/raw/jquants/equities_bars_daily/data.parquet
```

found:

```text
36810 rows=91
min_date=2026-02-16
max_date=2026-06-30
2026-07-01 36810 row absent
```

For `2026-07-01`, the inspected normalized OHLCV rows included:

```text
186A0
31340
33500
70630
```

but not:

```text
36810
3681
```

Therefore, a fresh rerun of the existing HALT scenario may still stop at Current Valuation, now for the correct canonical missing symbol `36810`. That would be a distinct market quote authority issue, not the BV12 identity normalization issue.

## Tests

Targeted BV12:

```text
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_bv12_current_valuation_symbol_identity.py
4 passed
```

Current Valuation + BV9/BV10/BV11 regression:

```text
PYTHONPATH=src python3 -m pytest -q \
  tests/runtime_v2/test_phase17_bv12_current_valuation_symbol_identity.py \
  tests/runtime_v2/test_phase15az_current_valuation_no_fill_producer.py \
  tests/runtime_v2/test_phase17_aa_historical_current_valuation_authority.py \
  tests/runtime_v2/test_phase17_bh_current_valuation_refresh_temporal_contract.py \
  tests/runtime_v2/test_phase17_bv9_historical_sell_quantity_authority.py \
  tests/runtime_v2/test_phase17_bv10_historical_sell_execution_projection.py \
  tests/runtime_v2/test_phase17_bv11_runtime_test_plan_persistence.py

46 passed
```

Static checks:

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase17_bv12_pycache PYTHONPATH=src python3 -m py_compile \
  src/ai_fund_lab_v2/runtime_v2/current_state/valuation.py \
  tests/runtime_v2/test_phase17_bv12_current_valuation_symbol_identity.py \
  tests/runtime_v2/test_phase17_bv11_runtime_test_plan_persistence.py

git diff --check
```

Both passed.

Full Runtime v2 regression:

```text
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2
931 passed, 5 failed
```

The 5 failures are PM sell planning CLI/report tests:

- `tests/runtime_v2/test_phase14e50_sell_planning_runtime_connection.py::test_phase14e50_sell_planning_cli_writes_sell_pending_from_pm_ai_artifact`
- `tests/runtime_v2/test_phase15af_position_management_runtime_connection.py::test_phase15af_cli_sell_planning_uses_pm_artifact_not_current_liquidation`
- `tests/runtime_v2/test_phase15af_position_management_runtime_connection.py::test_phase15af_exit_flows_to_sell_pending`
- `tests/runtime_v2/test_phase15af_position_management_runtime_connection.py::test_phase15af_report_and_notification_include_position_management_summary`
- `tests/runtime_v2/test_phase15h_capital_deployment_policy.py::test_phase15h_cli_manifest_emits_explicit_policy_fields`

These failures are not in Current Valuation, BV9, BV10, or BV11 paths.

## Prohibited Operations Audit

The following were not executed:

- `runtime_test.py run`
- `runtime_test.py resume`
- `runtime_test.py reset`
- `runtime_test.py rollback`
- `runtime_test.py close`
- Frozen Run evidence edits
- `.runtime` manual edits
- Persistent Ledger manual edits
- Pending manual edits
- Broker write
- J-Quants fetch
- External notification

## Recommended Next Boundary

Do not resume the existing HALT Run.

For a fresh replay, first decide whether the absence of `36810` on `2026-07-01` is:

- a genuine missing quote that must remain fail-closed,
- a corporate-action/listing lifecycle issue that should have removed or transformed the position before valuation,
- or a Historical market authority acquisition gap.

That decision is separate from BV12 and should not be solved by restoring `36810 -> 3681` normalization or by falling back to cost basis / average price / stale valuation.
