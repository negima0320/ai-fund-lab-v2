# Phase17-BV13 Historical Missing Quote Lifecycle and Market Authority Investigation

## Executive Summary

Phase17-BV13 investigated why canonical Runtime symbol `36810` had Historical OHLCV through `2026-06-30` but no quote on `2026-07-01`.

Conclusion:

```text
PHASE17_BV13_POSITION_LIFECYCLE_TRANSITION_REQUIRED
```

This is not a Current Valuation stale-price fallback case and not a raw-to-normalized filtering bug. Local J-Quants listed snapshots, local OHLCV stores, and public exchange/company disclosures all indicate that `36810` is V-cube, Inc. / ブイキューブ (`3681`) and was delisted from TSE Prime as of `2026-07-01`.

The correct Runtime boundary is therefore a position lifecycle contract. A Runtime-owned active position in `36810` must not be valued as an ordinary active listed equity on and after the delisting date. It should transition to a formal lifecycle state such as:

```text
DELISTED_PENDING_SETTLEMENT
```

or a more precise corporate-action settlement state once the settlement mechanics are modeled.

Fresh rerun status:

```text
FRESH_RERUN_NOT_SAFE_POSITION_LIFECYCLE_REQUIRED
```

## Public Authority

JPX published that V-cube, Inc. stock, code `3681`, Prime Market, would be delisted on `2026-07-01` under the exchange listing rules. It also notes the delisting date remained `2026-07-01` after a schedule update rather than being changed to `2026-06-26`.

Source:

```text
https://www.jpx.co.jp/news/1023/20260519-13.html
```

V-cube IR also states that common stock was delisted from the Prime Market of the Tokyo Stock Exchange as of `2026-07-01`.

Source:

```text
https://ir.vcube.com/gl/
```

## Listed Info / Master Data

Local J-Quants Historical Listed Issues snapshots show:

```text
2026-06-26: 36810 present
2026-06-29: 36810 present
2026-06-30: 36810 present
2026-07-01: 36810 absent
2026-07-02: 36810 absent
```

The 2026-06-30 record:

```json
{
  "Date": "2026-06-30",
  "Code": "36810",
  "CoName": "ブイキューブ",
  "CoNameEn": "V-cube,Inc.",
  "S17": "10",
  "S17Nm": "情報通信・サービスその他",
  "S33": "5250",
  "S33Nm": "情報･通信業",
  "Mkt": "0111",
  "MktNm": "プライム",
  "ProdCat": "011"
}
```

Local evidence paths:

```text
.runtime/operations/jquants/historical_snapshots/listed_issues/snapshots/2026-06-30/data.parquet
.runtime/operations/jquants/historical_snapshots/listed_issues/snapshots/2026-07-01/data.parquet
```

Interpretation:

`36810` is listed on `2026-06-30` and no longer in the listed issue universe on `2026-07-01`. That matches the public delisting authority.

## Corporate Action / Lifecycle

Confirmed lifecycle:

```text
company: ブイキューブ / V-cube, Inc.
canonical J-Quants code: 36810
display / TSE code: 3681
market before delisting: TSE Prime
product category: 011
sector: 情報･通信業
listed through: 2026-06-30
delisted as of: 2026-07-01
```

The investigated sources support delisting rather than a no-trade day. No evidence was found that `36810` transitioned to a new listed symbol on `2026-07-01` in the local J-Quants snapshots.

## Raw / Normalized / Canonical OHLCV Comparison

Compared read-only:

```text
.runtime/operations/jquants/raw/jquants/equities_bars_daily/data.parquet
.runtime/operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet
.runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet
```

Results for `36810` / `3681`:

```text
raw rows: 91
raw min_date: 2026-02-16
raw max_date: 2026-06-30

normalized rows: 91
normalized min_date: 2026-02-16
normalized max_date: 2026-06-30
normalized 2026-06-30 close: 9.0

phase9 canonical rows: 1232
phase9 canonical min_date: 2021-06-14
phase9 canonical max_date: 2026-06-26
```

On `2026-07-01`, local raw and normalized stores contain other held symbols:

```text
33500
186A0
31340
70630
```

but not:

```text
36810
3681
```

Interpretation:

The missing quote is already absent in raw OHLCV, not lost by normalization, canonical conversion, historical_asof filtering, or Current Valuation quote extraction.

## Historical Market Refresh

The `2026-07-01` Historical ASOF view is `PASS`.

Relevant authority:

```text
normalized_ohlcv physical_source_path:
.runtime/operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet

logical_cutoff: 2026-07-01
logical_max_date: 2026-07-01
status: PASS
```

Listed Issues authority:

```text
selected_snapshot_date: 2026-07-01
physical_source_path:
.runtime/operations/jquants/historical_snapshots/listed_issues/snapshots/2026-07-01/data.parquet
status: PASS
```

The market refresh path did not drop a 2026-07-01 `36810` row. The row was not present in the raw OHLCV authority for that date.

## Current Valuation Evidence

Frozen Run:

```text
runtime-test-historical-extended-smoke-20260716T213021655422Z
```

Stop:

```text
2026-07-01:current_valuation_refresh
exit_code=20
```

The BV12 pre-fix Evidence reported:

```text
missing_symbols=["3681"]
projection_status=REVIEW_REQUIRED
apply_status=NOT_EXECUTED
valued_position_count=0
```

After BV12, the identity would remain canonical:

```text
missing_symbols=["36810"]
```

but the underlying lifecycle issue remains because `36810` is no longer listed and no 2026-07-01 OHLCV quote exists.

## Correct Runtime Position State

The position should not remain an ordinary active listed equity position after `2026-07-01`.

Recommended lifecycle classification:

```text
DELISTED_PENDING_SETTLEMENT
```

Potential future refinements:

```text
CORPORATE_ACTION_PENDING
POSITION_LIFECYCLE_TRANSITION_REQUIRED
VALUATION_UNAVAILABLE_REVIEW_REQUIRED
```

depending on whether the eventual Runtime contract models cash settlement, stock consolidation, forced sale, broker statement reconciliation, or a delisting-specific terminal position.

## Stale-Price Fallback Assessment

Stale-price fallback is not permitted for this case.

Reason:

- `36810` was absent from the `2026-07-01` listed universe.
- Public authority confirms delisting as of `2026-07-01`.
- This is not a normal no-trade day for an actively listed symbol.
- Using `2026-06-30` close as a normal active valuation would hide a lifecycle transition.
- Cost basis / average price fallback would be even less authoritative.

Allowed future policy, if implemented, must be explicit and lifecycle-aware, for example:

```text
delisted_pending_settlement_value_policy
```

and not a general missing quote fallback.

## Required Correction Boundary

Next implementation phase should add a shared Runtime position lifecycle resolver used by:

- Current Valuation
- Data Readiness
- Sell Planning
- Execution / Current refresh
- Persistent Ledger projection

The resolver should inspect point-in-time Listed Issues authority and classify held positions on the business date:

```text
ACTIVE_LISTED
DELISTED_PENDING_SETTLEMENT
SYMBOL_TRANSITION_REQUIRED
CORPORATE_ACTION_PENDING
NO_TRADE_MARKET_STATE
UNKNOWN_REVIEW_REQUIRED
```

For `DELISTED_PENDING_SETTLEMENT`, Current Valuation must not demand a normal same-day OHLCV quote as if the position were active listed equity.

## Tests

No Runtime code fix was applied in BV13, so no new lifecycle tests were added in this phase.

Required tests for the next implementation phase:

- delisted symbol is not valued as normal active listed equity
- 2026-06-30 listed / 2026-07-01 delisted transition is detected
- stale-price fallback is rejected for delisted symbols
- genuine data gap for an active listed symbol remains fail-closed
- no-trade carry-forward only applies with official listed/no-trade authority
- BV9/BV10/BV11/BV12 regressions remain passing
- Demo/Production Current Valuation remains fail-closed without equivalent lifecycle authority

## Commands Executed

Read-only commands only:

```text
find .runtime -path '*listed*' -type f
find reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260716T213021655422Z/daily/2026-07-01 -maxdepth 3 -type f
rg listed/delist/corporate/halt/quote_status
python pandas read-only parquet inspection for listed snapshots and OHLCV stores
web search/open for JPX and V-cube public delisting authority
```

No Runtime Test mutation commands were executed.

## Prohibited Operations Audit

The following were not executed:

- `runtime_test.py run`
- `runtime_test.py resume`
- `runtime_test.py reset`
- `runtime_test.py rollback`
- `runtime_test.py close`
- Frozen Run edits
- `.runtime` manual edits
- Ledger/Pending manual edits
- Broker write
- J-Quants API fetch
- External notification

## Final Judgment

```text
PHASE17_BV13_POSITION_LIFECYCLE_TRANSITION_REQUIRED
```

Fresh rerun is not safe until the delisted-position lifecycle contract is implemented and verified.
