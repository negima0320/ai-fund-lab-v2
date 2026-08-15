# Phase30-A0V — Repeating 100k Daily Valuation Swing Root Cause Audit

## Task

Phase30-A0V

Mode: READ-ONLY audit.

Strategy, Runtime, Config, Model, and Threshold were not changed. No fresh-run, resume, replay, or recovery was executed. The running 4-year Historical run was not mutated.

## Target

- Run: `runtime-test-historical-extended-smoke-20260814T131647480030Z`
- Focus dates: `2023-09-05`, `2023-09-06`, `2023-09-07`, `2023-09-08`

## Primary Judgment

`PRICE_NORMALIZATION_DEFECT_CONFIRMED`

The repeated +/-100k equity swing is driven almost entirely by `67310`, held at `100` shares, whose valuation price repeatedly flips between `2000.0` and `3000.0`.

Because the position quantity is `100`, each 1000 price-point flip creates exactly +/-100,000 yen of market value movement.

This is internally reconciled by DAILY_PNL arithmetic, but it is not credible as ordinary portfolio economics. The source row is `PriceSource=adjusted`, yet valuation consumes `Close=2000/3000` directly as yen price with no explicit adjustment factor / adjusted-vs-raw reconciliation evidence.

## DAILY_PNL Reconciliation

| Date | Equity Delta | Symbol Contribution Sum | Diff | Top Contributor |
| --- | ---: | ---: | ---: | --- |
| 2023-09-05 | +100,230 | +100,230 | ~0 | `67310` |
| 2023-09-06 | -94,860 | -94,860 | 0 | `67310` |
| 2023-09-07 | +100,040 | +100,040 | 0 | `67310` |
| 2023-09-08 | -100,210 | -100,210 | ~0 | `67310` |

The DAILY_PNL series is arithmetically consistent with valuation state. The defect is upstream of PnL arithmetic: the valuation price accepted for `67310`.

## Focus Symbol Evidence

`67310` focus price series:

| Date | Previous Price | Current Price | Change | Quantity | Contribution | Execution | Corporate Action |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 2023-09-05 | 2000.0 | 3000.0 | +50.00% | 100 | +100,000 | none | none |
| 2023-09-06 | 3000.0 | 2000.0 | -33.33% | 100 | -100,000 | none | none |
| 2023-09-07 | 2000.0 | 3000.0 | +50.00% | 100 | +100,000 | none | none |
| 2023-09-08 | 3000.0 | 2000.0 | -33.33% | 100 | -100,000 | none | none |

Raw source rows for `67310`:

| Date | Open | High | Low | Close | Volume | PriceSource |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 2023-09-05 | 2000.0 | 3000.0 | 2000.0 | 3000.0 | 3645.4 | adjusted |
| 2023-09-06 | 3000.0 | 3000.0 | 2000.0 | 2000.0 | 4281.2 | adjusted |
| 2023-09-07 | 3000.0 | 3000.0 | 2000.0 | 3000.0 | 3737.1 | adjusted |
| 2023-09-08 | 3000.0 | 3000.0 | 2000.0 | 2000.0 | 4288.8 | adjusted |

Source artifact pattern:

`daily/<date>/market_refresh/inputs/historical_asof/<date>/raw_normalized/jquants/equities_bars_daily/data.parquet`

The parquet carries `PriceSource=adjusted` and `SchemaVersion=2`. No explicit `AdjustmentFactor` or `AdjustmentClose` field was present in the valuation rows inspected.

## Repeating Pattern

The same `67310` close flip appears beyond the focus window:

- 2023-08-02: `2000 -> 3000`, +100,000 contribution
- 2023-08-04: `3000 -> 2000`, -100,000 contribution
- 2023-08-07: `2000 -> 3000`, +100,000 contribution
- 2023-08-08: `3000 -> 2000`, -100,000 contribution
- 2023-09-14: `3000 -> 2000`, -100,000 contribution
- 2023-09-15: `2000 -> 3000`, +100,000 contribution
- 2023-09-21: `3000 -> 2000`, -100,000 contribution
- 2023-09-26: `2000 -> 3000`, +100,000 contribution
- 2023-09-27: `3000 -> 2000`, -100,000 contribution
- 2023-10-03: `2000 -> 3000`, +100,000 contribution
- 2023-10-05: `3000 -> 2000`, -100,000 contribution
- 2023-10-10: `2000 -> 3000`, +100,000 contribution
- 2023-10-11: `3000 -> 2000`, -100,000 contribution

This repeating exact 100k pattern is the dominant explanation for the observed equity swings.

## Other Symbols / Trades

Other focus-window contributions are small by comparison:

- `94320`: aggregate absolute contribution about `6,760`
- `89180`: aggregate absolute contribution about `6,000`
- `76470`: aggregate absolute contribution about `3,800`
- `83060`: aggregate absolute contribution about `3,350`

Focus-date executions:

- 2023-09-05: no fills
- 2023-09-06: BUY `76470`, 100 shares at 28.0, not the swing driver
- 2023-09-07: no fills
- 2023-09-08: SELL `89180`, 3000 shares at 9.0, not the swing driver

`67310` had no quantity change and no execution on the focus dates.

## Corporate Action

Corporate event artifacts for the focus dates show:

- `event_count = 0`
- `known_event_symbols = []`
- `67310` not flagged as a corporate action symbol

Therefore the observed +/-100k swings are not explained by a recorded split, reverse split, or corporate-action quantity adjustment in the current runtime evidence.

## Authority Assessment

- Market move confirmed: NO
- Concentration-driven volatility: PARTIAL, because the inflated/unstable valuation is concentrated in one 100-share position.
- Corporate Action issue: NO evidence in current artifacts
- Price normalization issue: YES
- Valuation authority issue: YES, because valuation accepts the adjusted normalized `Close` as current yen price without adjustment reconciliation evidence
- Quantity adjustment issue: NO evidence; `67310` quantity stayed `100`
- Stale / alternating price source: YES, alternating price values repeatedly appear in the valuation source

## Artifacts

Created:

- `reports/phase30_a0v_repeating_100k_daily_valuation_swing_root_cause_audit/summary.json`
- `reports/phase30_a0v_repeating_100k_daily_valuation_swing_root_cause_audit/daily_symbol_contribution.csv`
- `reports/phase30_a0v_repeating_100k_daily_valuation_swing_root_cause_audit/daily_reconciliation.csv`
- `reports/phase30_a0v_repeating_100k_daily_valuation_swing_root_cause_audit/suspicious_price_transitions.csv`
- `reports/phase30_a0v_repeating_100k_daily_valuation_swing_root_cause_audit/corporate_action_trace.csv`
- `reports/phase30_a0v_repeating_100k_daily_valuation_swing_root_cause_audit/price_series_suspicious_symbols.csv`

## Validation

- DAILY_PNL reconciliation: PASS
- `summary.json` parse: PASS
- `git diff --check`: PASS
- Runtime mutation: NO
- Strategy change: NO
- Phase30 implementation entered: NO

## Recommended Next Action

`Phase30-A0W — Valuation Price Normalization / Stale Alternating Source Repair Design`

The next task should be a focused design/repair task for valuation price authority:

- distinguish adjusted analytical prices from executable/economic valuation prices,
- require adjustment factor evidence for adjusted rows,
- fail closed on unresolved raw/adjusted ambiguity for current valuation,
- add regression around `67310`-type low-price adjusted rows,
- preserve runtime transactionality and avoid Historical-only workarounds.
