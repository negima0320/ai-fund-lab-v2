# Phase26-E Historical Trade Price Integrity and PnL Authority Audit

## Primary Judgment

`PHASE26_E_EXECUTION_PRICE_VALID_PNL_SUMMARY_AUTHORITY_DEFECT_CONFIRMED`

## Scope

This was a read-only audit of run:

`runtime-test-historical-smoke-20260804T005103762479Z`

No Runtime, Strategy, Submit, Safety, Candidate, Opportunity, Corporate Action, or validation code was changed.

## Primary Root Cause

The 138,590 yen difference is caused by an authority mismatch in realized PnL reporting:

- Final equity is correct from Runtime-owned Current cash plus final market value.
- Run-scoped realized PnL from `execution/realized_slices.json` is `-91,390`.
- Final unrealized PnL from final Current positions is `+23,700`.
- `-91,390 + 23,700 = -67,690`, which exactly equals final equity return.
- Final Current `realized_pnl` is `+47,200`, which is not the run-scoped cumulative realized PnL.
- The difference `47,200 - (-91,390) = 138,590` exactly explains the originally unexplained amount.

First divergence:

`2023-01-18`

On that date cumulative realized slices were `-1,700`, while retained Current history showed `realized_pnl = 45,900`. That value matches the SELL notional-style daily projection shape, not cumulative acquisition-cost realized PnL.

## 30410 Price Integrity

30410 execution prices match the Runtime-used J-Quants normalized OHLCV `Open` values:

| Date | Side | Qty | Execution | Normalized Open | Normalized Close | PriceSource | Corporate Event |
|---|---:|---:|---:|---:|---:|---|---|
| 2023-05-15 | BUY | 100 | 1074 | 1074 | 1074 | adjusted | KNOWN_NO_EVENT |
| 2023-05-16 | SELL | 100 | 2274 | 2274 | 2274 | adjusted | KNOWN_NO_EVENT |
| 2023-05-19 | BUY | 100 | 1697 | 1697 | 1420 | adjusted | KNOWN_NO_EVENT |
| 2023-05-22 | SELL | 100 | 1426 | 1426 | 1444 | adjusted | KNOWN_NO_EVENT |
| 2023-05-23 | BUY | 100 | 1391 | 1391 | 1330 | adjusted | KNOWN_NO_EVENT |

Raw J-Quants rows show `AdjFactor = 1.0` for the target rows, and normalized rows use `PriceSource = adjusted`.

The listed issues authority identifies `30410` as `ビューティ花壇 / Beauty Kadan Co.,Ltd.`, Standard market, Wholesale sector, with no symbol mix-up found in the target artifacts.

## Authority Findings

- Execution Price Authority: `HistoricalSubmitAdapter` resolves target-session `Open` from historical-asof normalized J-Quants OHLCV.
- Raw Market Price Authority: daily `raw/jquants/equities_bars_daily/data.parquet`.
- Adjusted Price Authority: daily `raw_normalized/jquants/equities_bars_daily/data.parquet`, `PriceSource=adjusted`.
- Corporate Action Authority: daily `strategy/corporate_event.json`, target dates `KNOWN_NO_EVENT`.
- Position Quantity Authority: Runtime-owned fill projection Current positions.
- Acquisition Cost / Cost Basis Authority: realized slices and Runtime-owned average cost.
- Realized PnL Authority: run-scoped `execution/realized_slices.json`, not final Current `realized_pnl`.
- Unrealized PnL Authority: final Current positions and `new_unrealized_pnl`.
- Cash Authority: final Current cash, independently matching execution cash effects.
- Market Value Authority: final Current target-date valuation.
- Total Equity Authority: final Current `cash + market_value`.
- Summary Aggregation Authority: `runtime_test.py` currently prefers `current_state.realized_pnl` when present, even though reconciliation evidence can identify a mismatch.

## Evidence

Generated under:

`reports/phase26_e_historical_trade_price_integrity_and_pnl_authority_audit/`

Key artifacts:

- `trade_price_trace_30410.json`
- `symbol_30410_price_trace.csv`
- `realized_pnl_recomputation.json`
- `all_trade_pnl_reconciliation.csv`
- `unrealized_pnl_recomputation.json`
- `final_equity_recomputation.json`
- `pnl_difference_breakdown.json`
- `authority_trace.json`
- `fixed_sizing_residual_audit.json`
- `summary.json`

## Fixed Sizing Residual Audit

BUY notionals remain clustered around 106,000 to 182,400 yen in the audited run. Phase26-E did not repair or tune sizing. No `target_position_count` reintroduction was found as a Phase26-E change.

## Runtime Boundary

- Validation weakened: false
- Fallback added: false
- Historical-only branch added: false
- Runtime behavior changed: false
- Strategy behavior changed: false
- `target_position_count` reintroduced: false

## Recommended Next Task

Repair the Runtime-owned realized PnL producer / summary authority:

- Current `realized_pnl` must not be overwritten by daily pending SELL projection values.
- Run-scoped cumulative realized slices should be the canonical realized PnL authority for historical run performance.
- Summary aggregation must not silently prefer unreconciled `current_state.realized_pnl` over run-scoped realized slice evidence.
