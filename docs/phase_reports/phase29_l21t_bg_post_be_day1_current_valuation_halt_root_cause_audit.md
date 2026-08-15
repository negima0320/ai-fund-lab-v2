# Phase29-L21T-BG — Post-BE Day1 Current Valuation HALT Root Cause Audit

## Task

- Task ID: Phase29-L21T-BG
- Mode: READ-ONLY audit
- Target run: `runtime-test-historical-extended-smoke-20260815T013038707969Z`
- HALT date: `2022-08-10`
- HALT stage: `current_valuation_refresh`
- Runtime CLI exit code: `20`
- Runtime Test exit code: `30`
- Completed days: `0`

Phase29 was continued. Phase30 was not entered. No fresh-run, resume, replay, recovery, Strategy change, Runtime change, Config change, Model change, Threshold change, or target run mutation was performed.

## Primary Judgment

`BE_FAIL_CLOSED_CORRECT_PRODUCER_INTEGRATION_GAP_CONFIRMED`

The Day1 HALT is the expected BE fail-closed behavior. It is not a BE semantic regression. BE correctly rejected adjusted normalized quotes because none of the held-symbol quotes carried:

- `economic_price_reconciliation_status=PASS`
- non-empty `economic_price_provenance`
- positive `economic_valuation_price`

The remaining defect is an integration gap: the actual Historical current valuation path loads `historical_asof_view.json`, synthesizes quote evidence from `normalized_ohlcv`, and supplies adjusted analytical `Close` without producing or propagating explicit economic valuation reconciliation.

## Direct Evidence

`valuation_projection.json`:

- `status`: `REVIEW_REQUIRED`
- `projection_status`: `REVIEW_REQUIRED`
- `reason`: `current_valuation_review_required`
- `position_count`: `9`
- `valued_position_count`: `0`
- `valuation_refresh_precondition_status`: `PASS`
- `valuation_refresh_action`: `APPLY`
- `execution_reached`: `true`

`current_valuation_manifest.json`:

- `missing_symbols`: `[]`
- `missing_evidence`:
  - `current_valuation_quote_invalid:23700`
  - `current_valuation_quote_invalid:23880`
  - `current_valuation_quote_invalid:45710`
  - `current_valuation_quote_invalid:66590`
  - `current_valuation_quote_invalid:76470`
  - `current_valuation_quote_invalid:89180`
  - `current_valuation_quote_invalid:93180`
  - `current_valuation_quote_invalid:94320`
  - `current_valuation_quote_invalid:94340`

## Symbol-Level Rejection

All 9 held symbols had quotes, but all were rejected for the same reason:

`adjusted_price_missing_economic_valuation_reconciliation`

| Symbol | Qty | Normalized Close | PriceSource | Raw C | Raw AdjC | Accepted |
| --- | ---: | ---: | --- | ---: | ---: | --- |
| 23700 | 500 | 71.0 | adjusted | 71.0 | 71.0 | false |
| 23880 | 100 | 151.0 | adjusted | 151.0 | 151.0 | false |
| 45710 | 100 | 199.0 | adjusted | 199.0 | 199.0 | false |
| 66590 | 400 | 98.0 | adjusted | 98.0 | 98.0 | false |
| 76470 | 1100 | 26.0 | adjusted | 26.0 | 26.0 | false |
| 89180 | 2700 | 10.0 | adjusted | 10.0 | 10.0 | false |
| 93180 | 6600 | 6.0 | adjusted | 6.0 | 6.0 | false |
| 94320 | 200 | 149.8 | adjusted | 3744.0 | 149.8 | false |
| 94340 | 100 | 151.8 | adjusted | 1517.5 | 151.8 | false |

The raw/economic source exists for all 9 symbols, including clear raw-vs-adjusted divergence for `94320` and `94340`. The problem is not quote absence. The problem is that no producer materialized the economic valuation authority into the evidence consumed by Current valuation.

## Producer Trace

| Stage | Status | Finding |
| --- | --- | --- |
| `market_refresh` | PASS | `historical_asof_view.json` materialized normalized and raw OHLCV paths |
| `current_valuation_refresh` | REVIEW_REQUIRED | current valuation loaded `historical_asof_view.json` and synthesized quotes from normalized OHLCV only |
| `raw_ohlcv_source` | AVAILABLE | raw `C` / `AdjC` columns exist for target symbols, but are not propagated as economic valuation evidence |

The relevant source paths from `historical_asof_view.json` are:

- normalized: `.runtime/operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet`
- raw: `.runtime/operations/jquants/raw/jquants/equities_bars_daily/data.parquet`

## Required Judgment

- BE fail-closed correctly triggered: YES
- BE regression: NO
- Economic price source exists: YES
- Economic price producer exists: NO
- Producer invoked in Historical: NO
- Reconciliation evidence propagated: NO
- Producer integration gap: YES
- Source data gap: NO
- Reconciliation propagation gap: YES
- Quote source selection defect: YES
- Implementation repair required: YES

## Root Cause

BE made Current valuation correctly fail closed for adjusted analytical prices. The post-BE Day1 HALT occurs because the actual Historical current valuation producer path still supplies adjusted normalized `Close` as the quote payload and does not produce a reconciled economic valuation price from available raw/economic source evidence.

This is a production-common producer integration gap, not a reason to weaken BE fail-closed semantics.

## Artifacts

- `reports/phase29_l21t_bg_post_be_day1_current_valuation_halt_root_cause_audit/summary.json`
- `reports/phase29_l21t_bg_post_be_day1_current_valuation_halt_root_cause_audit/valuation_rejection_trace.csv`
- `reports/phase29_l21t_bg_post_be_day1_current_valuation_halt_root_cause_audit/economic_price_producer_trace.csv`

## Validation

- `summary.json` parse: PASS
- `valuation_rejection_trace.csv` materialized: PASS
- `economic_price_producer_trace.csv` materialized: PASS
- Runtime mutation: none
- Strategy mutation: none
- Fresh-run / resume / replay / recovery: not executed by Codex

## Recommended Next Action

Implement a minimal production-common repair:

`Phase29-L21T-BH — Current Valuation Economic Price Producer / Reconciliation Propagation Repair`

The repair should connect raw/economic valuation authority into market quote evidence / current valuation consumer without allowing adjusted analytical prices by default, without zero-fill, without stale fallback, without Historical-only logic, and without weakening BE fail-closed behavior.
