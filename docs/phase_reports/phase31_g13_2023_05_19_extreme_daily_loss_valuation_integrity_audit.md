# Phase31-G13 - 2023-05-19 Extreme Daily Loss Valuation Integrity Audit

## Scope

Task type: READ-ONLY EXTREME LOSS / VALUATION INTEGRITY AUDIT.

No implementation, Strategy change, PM change, BUY/SELL tuning, threshold tuning, parameter tuning, config change, fresh-run, resume, replay, or Historical rerun was performed.

Target run:

`runtime-test-historical-extended-smoke-20260822T174358377089Z`

Target dates:

- Prior date: `2023-05-18`
- Extreme loss date: `2023-05-19`
- Added bridge date: `2023-05-22`

## Primary Judgment

`PRIMARY_JUDGMENT = PHASE31_G13_LOSS_VALID_MARK_TO_MARKET_SINGLE_SYMBOL_67310_WITH_20230522_EXECUTION_REVERSAL`

The reported `2023-05-19` daily loss is exactly reconciled by canonical valuation evidence. It is not caused by cash mutation, fill side effects, stale price fallback, missing price fallback, basis metadata loss, quantity mismatch, or a corporate-action application defect.

The loss is single-symbol dominated:

- `67310` canonical valuation price moved from `3,000` on `2023-05-18` to `2,000` on `2023-05-19`.
- Quantity stayed `100`.
- Market value moved from `300,000` to `200,000`.
- Contribution = `-100,000`, offset by `+5,800` from the other four holdings.
- Net daily equity change = `-94,200`.

The added `2023-05-22` bridge shows the loss was materially reversed by the same symbol, but not because the closing valuation price returned. `67310` remained `2,000` on canonical `2023-05-22` close, while Runtime executed an EXIT at `3,000`, producing a +100,000 equity/cash reversal relative to the 5/19 marked value.

## Evidence Sources

Daily valuation:

- `.runtime/runtime_state/current_valuation/2023-05-18/current_valuation_refresh.json`
- `.runtime/runtime_state/current_valuation/2023-05-19/current_valuation_refresh.json`
- `.runtime/runtime_state/current_valuation/2023-05-22/current_valuation_refresh.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260822T174358377089Z/daily/<date>/current_valuation_refresh/valuation_projection.json`

Market evidence:

- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260822T174358377089Z/daily/<date>/market_refresh/inputs/historical_asof/<date>/raw/jquants/equities_bars_daily/data.parquet`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260822T174358377089Z/daily/<date>/market_refresh/inputs/historical_asof/<date>/raw_normalized/jquants/equities_bars_daily/data.parquet`

Corporate action evidence:

- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260822T174358377089Z/daily/<date>/strategy/corporate_event.json`

Execution evidence:

- `daily/2023-05-19/execution/*`
- `daily/2023-05-22/execution/*`

## Exact Equity Reconciliation

| Date | Cash | Market Value | Reconstructed Equity | Recorded Equity | Delta |
|---|---:|---:|---:|---:|---:|
| 2023-05-18 | 587,330 | 565,300 | 1,152,630 | 1,152,630 | 0 |
| 2023-05-19 | 587,330 | 471,100 | 1,058,430 | 1,058,430 | 0 |
| 2023-05-22 | 754,730 | 408,900 | 1,163,630 | 1,163,630 | 0 |

`EQUITY_20230518_RECONSTRUCTED = 1,152,630`

`EQUITY_20230518_RECORDED = 1,152,630`

`EQUITY_20230518_DELTA = 0`

`EQUITY_20230519_RECONSTRUCTED = 1,058,430`

`EQUITY_20230519_RECORDED = 1,058,430`

`EQUITY_20230519_DELTA = 0`

`EQUITY_RECONCILIATION = PASS`

## Three-Day Valuation Bridge

Canonical position valuation bridge:

| Symbol | Qty 5/18 | Price 5/18 | MV 5/18 | Qty 5/19 | Price 5/19 | MV 5/19 | Delta 5/18->5/19 | Qty 5/22 | Price 5/22 | MV 5/22 | Delta 5/19->5/22 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 27620 | 200 | 254 | 50,800 | 200 | 245 | 49,000 | -1,800 | 200 | 236 | 47,200 | -1,800 |
| 31920 | 100 | 510 | 51,000 | 100 | 486 | 48,600 | -2,400 | 100 | 448 | 44,800 | -3,800 |
| 45830 | 300 | 212 | 63,600 | 300 | 217 | 65,100 | +1,500 | 300 | 219 | 65,700 | +600 |
| 67310 | 100 | 3,000 | 300,000 | 100 | 2,000 | 200,000 | -100,000 | 0 | n/a | 0 | -200,000 MV / +300,000 cash via EXIT |
| 72140 | 0 | n/a | 0 | 0 | n/a | 0 | 0 | 100 | 1,468 | 146,800 | +146,800 MV / -132,600 cash via BUY |
| 73510 | 100 | 999 | 99,900 | 100 | 1,084 | 108,400 | +8,500 | 100 | 1,044 | 104,400 | -4,000 |

Bridge arithmetic:

| Period | Cash Delta | Market Value Delta | Equity Delta |
|---|---:|---:|---:|
| 2023-05-18 -> 2023-05-19 | 0 | -94,200 | -94,200 |
| 2023-05-19 -> 2023-05-22 | +167,400 | -62,200 | +105,200 |

5/18 -> 5/19 per-symbol market value deltas sum to `-94,200`.

5/19 -> 5/22 decomposition:

- Continuing holdings: `27620 -1,800`, `31920 -3,800`, `45830 +600`, `73510 -4,000` = `-9,000`
- `67310` removed from market value: `-200,000`
- `72140` added to market value: `+146,800`
- Cash effect from 5/22 fills: `+300,000` from `67310` EXIT and `-132,600` from `72140` BUY = `+167,400`
- Net = `-9,000 - 200,000 + 146,800 + 167,400 = +105,200`

`THREE_DAY_VALUATION_BRIDGE = PASS`

`20230519_LOSS_REVERSED_BY_20230522 = PARTIAL`

The same symbol `67310` explains the economic round trip of the large loss contribution, but the reversal came through a 5/22 EXIT execution at `3,000`, not through a 5/22 close valuation price returning to `3,000`.

## Loss Contribution

5/19 loss contribution:

| Rank | Symbol | Contribution | Contribution vs Reported -94,200 |
|---:|---|---:|---:|
| 1 | 67310 | -100,000 | 106.16% |
| 2 | 31920 | -2,400 | 2.55% |
| 3 | 27620 | -1,800 | 1.91% |
| Offset | 45830 | +1,500 | -1.59% |
| Offset | 73510 | +8,500 | -9.02% |

`TOP_LOSS_CONTRIBUTOR = 67310`

`TOP_LOSS_CONTRIBUTION_YEN = -100,000`

`TOP_LOSS_CONTRIBUTION_PCT = 106.16%`

`LOSS_CONCENTRATION_CLASS = SINGLE_SYMBOL_DOMINATED`

`LOSS_REVERSAL_CONCENTRATION = SINGLE_SYMBOL`

## Raw Market Data Integrity

J-Quants raw and normalized rows were available for every target symbol on all three dates. No duplicate `(Date, Code)` rows were found for the inspected symbol/date set.

Raw / adjusted price bridge:

| Date | Symbol | Raw O | Raw H | Raw L | Raw C | AdjFactor | AdjO | AdjH | AdjL | AdjC | Normalized Close |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2023-05-18 | 67310 | 3 | 3 | 2 | 3 | 1.0 | 3,000 | 3,000 | 2,000 | 3,000 | 3,000 |
| 2023-05-19 | 67310 | 3 | 3 | 2 | 2 | 1.0 | 3,000 | 3,000 | 2,000 | 2,000 | 2,000 |
| 2023-05-22 | 67310 | 3 | 3 | 2 | 2 | 1.0 | 3,000 | 3,000 | 2,000 | 2,000 | 2,000 |

For all inspected rows:

- `RAW_MARKET_DATA_AVAILABLE = YES`
- `RAW_MARKET_DATA_DUPLICATE_COUNT = 0`
- `STALE_PRICE_USED = NO`
- `MISSING_PRICE_FALLBACK_USED = NO`

The `67310` adjusted close discontinuity is present in both raw `AdjC` and normalized adjusted `Close`. It is not a valuation-only artifact absent from market evidence.

`ONE_DAY_VALUATION_DISCONTINUITY = NO`

The `67310` close changed from `3,000` to `2,000` on 5/19 and stayed `2,000` on 5/22. The 5/22 recovery came from EXIT execution price, not from a one-day valuation price snapback.

## Price / Quantity Basis Contract

For all held symbols on 5/18 and 5/19:

- `valuation_price_basis = ADJUSTED`
- `quantity_basis = ADJUSTED`
- `valuation_price_authority = PASS`
- `valuation_price_authority_reason = valuation_price_basis_matches_adjusted_quantity_basis`
- `valuation_adjusted = true`
- `valuation_quote_status = FRESH_CURRENT_QUOTE`
- `staleness_business_days = 0`
- `corporate_action_ambiguity_status = CLEAR`

For continuing symbols on 5/22, the same basis metadata remains unchanged. `67310` is no longer held after the 5/22 EXIT. `72140` enters with `ADJUSTED / ADJUSTED` basis.

`PRICE_QUANTITY_BASIS_CONTRACT = PASS`

`BASIS_MISMATCH_SYMBOLS = []`

`BASIS_AMBIGUITY_SYMBOLS = []`

No 5/19 -> 5/22 basis metadata change was found for continuing holdings.

## Corporate Action Audit

Corporate-event facts for all inspected symbols (`27620`, `31920`, `45830`, `67310`, `72140`, `73510`) on 5/18, 5/19, and 5/22 report:

- `coverage_status = AVAILABLE`
- `event_status = KNOWN_NO_EVENT`
- `event_dates = []`
- `event_types = []`

`CORPORATE_ACTION_INVOLVED = NO`

`CORPORATE_ACTION_SYMBOLS = []`

`CORPORATE_ACTION_APPLICATION_STATUS = NOT_APPLICABLE`

No stock split, reverse split, merger, allocation, rights event, symbol change, or supported corporate-action transformation was present in the canonical corporate-event evidence.

## Quantity Continuity

5/18 -> 5/19:

| Symbol | Qty 5/18 | Qty 5/19 |
|---|---:|---:|
| 27620 | 200 | 200 |
| 31920 | 100 | 100 |
| 45830 | 300 | 300 |
| 67310 | 100 | 100 |
| 73510 | 100 | 100 |

`QUANTITY_0518_0519_UNCHANGED = YES`

5/19 -> 5/22 quantity changed because of actual execution effects:

- `67310 SELL EXIT 100`
- `72140 BUY 100`

These are not corporate-action quantity mutations.

## Cash Continuity

5/18 -> 5/19:

- `cash = 587,330` on both dates
- no fills
- no realized slices
- no ledger orders/executions/cash/positions appended
- execution action = `NO_ACTION`

`CASH_CONTINUITY = PASS`

`UNEXPLAINED_CASH_MUTATION = NO`

5/22 cash changed to `754,730`, explained by:

- `67310 SELL 100 @ 3,000 = +300,000`
- `72140 BUY 100 @ 1,326 = -132,600`
- net cash effect = `+167,400`

## Order / Fill / Execution Side Effects

2023-05-19:

- `BUY_FILL_COUNT_20230519 = 0`
- `SELL_FILL_COUNT_20230519 = 0`
- `EXECUTION_LEDGER_MUTATION_COUNT = 0`
- `POSITION_QUANTITY_MUTATION_COUNT = 0`
- `CASH_MUTATION_COUNT = 0`
- Submit action = `NO_ACTION`
- Execution action = `NO_ACTION`

2023-05-22:

- BUY fills = 1 (`72140 BUY 100 @ 1,326`)
- SELL fills = 1 (`67310 SELL EXIT 100 @ 3,000`)
- realized slice for `67310` = `gross_realized_pnl 0`, cost basis `300,000`, sell notional `300,000`
- ledger orders appended = 2
- ledger executions appended = 2
- ledger cash appended = 1
- ledger positions appended = 6

The 5/19 loss must be attributed to mark-to-market valuation. The 5/22 rebound must not be attributed to unchanged-holding valuation; it includes real execution side effects.

## Prior Measurement-Defect Regression Check

Checked defect classes:

1. adjusted analytical price used for valuation: no regression; adjusted valuation is explicitly authorized.
2. raw price x adjusted quantity: no regression; valuation uses adjusted `AdjC` / normalized adjusted `Close`.
3. basis metadata lost after BUY: no evidence.
4. basis metadata lost after ADD: no evidence.
5. basis metadata lost after REDUCE: no evidence.
6. basis metadata lost after partial SELL: no evidence.
7. basis metadata lost after EXIT/re-entry: no evidence in inspected bridge; 72140 enters with basis metadata.
8. stale raw price: no evidence; quotes are fresh with staleness 0.
9. duplicated corporate-action adjustment: no evidence; corporate action says known no event.

`PRIOR_MEASUREMENT_DEFECT_REGRESSION = NO`

## Market-Move Plausibility

Using only run/repository evidence:

- `67310` raw row on 2023-05-19 has `O=3`, `H=3`, `L=2`, `C=2`.
- raw `AdjC=2,000`.
- normalized adjusted `Close=2,000`.
- 2023-05-22 raw row still has `C=2`, `AdjC=2,000`.
- The 5/22 EXIT price `3,000` is consistent with the same day's raw/adjusted open/high at `3` / `3,000`, not with the closing valuation.

`GENUINE_MARKET_MOVE_SUPPORTED = YES`

This is a valid close-to-close mark-to-market loss for 5/19 based on canonical available market evidence. It was later offset by an execution at a higher intraday price.

## Performance Evidence Impact

`PERFORMANCE_EVIDENCE_DECISION = LOSS_VALID_AND_PERFORMANCE_EVIDENCE_VALID`

`PERFORMANCE_EVIDENCE_VALID_THROUGH = 2023-05-22`

`PERFORMANCE_EVIDENCE_QUARANTINE_REQUIRED = NO`

The 5/19 loss is valid as close-based mark-to-market evidence. The 5/22 recovery is also valid but includes execution side effects and should not be described as a pure valuation reversal.

## Current Run Safety

`CURRENT_RUN_RECOMMENDATION = CONTINUE_RUNNING`

No measurement-integrity defect requiring stop or quarantine was identified.

`PERFORMANCE_TUNING_RECOMMENDED = NO`

No Strategy, PM, BUY, SELL, exposure, position cap, regime, stop-loss, re-entry, threshold, filter, or feature recommendation is made.

## Required Summary Output

`PRIMARY_JUDGMENT = PHASE31_G13_LOSS_VALID_MARK_TO_MARKET_SINGLE_SYMBOL_67310_WITH_20230522_EXECUTION_REVERSAL`

`TARGET_RUN_ID = runtime-test-historical-extended-smoke-20260822T174358377089Z`

`TARGET_DATE = 2023-05-19`

`PRIOR_DATE = 2023-05-18`

`EQUITY_20230518_RECORDED = 1,152,630`

`EQUITY_20230519_RECORDED = 1,058,430`

`REPORTED_DAILY_PNL = -94,200`

`EQUITY_RECONCILIATION = PASS`

`PER_SYMBOL_VALUATION_RECONCILIATION = PASS`

`THREE_DAY_VALUATION_BRIDGE = PASS`

`TOP_LOSS_CONTRIBUTOR = 67310`

`TOP_LOSS_CONTRIBUTION_YEN = -100,000`

`TOP_LOSS_CONTRIBUTION_PCT = 106.16%`

`LOSS_CONCENTRATION_CLASS = SINGLE_SYMBOL_DOMINATED`

`LOSS_REVERSAL_CONCENTRATION = SINGLE_SYMBOL`

`ONE_DAY_VALUATION_DISCONTINUITY = NO`

`20230519_LOSS_REVERSED_BY_20230522 = PARTIAL`

`RAW_MARKET_DATA_AVAILABLE = YES`

`RAW_MARKET_DATA_DUPLICATE_COUNT = 0`

`STALE_PRICE_USED = NO`

`MISSING_PRICE_FALLBACK_USED = NO`

`PRICE_QUANTITY_BASIS_CONTRACT = PASS`

`BASIS_MISMATCH_SYMBOLS = []`

`BASIS_AMBIGUITY_SYMBOLS = []`

`CORPORATE_ACTION_INVOLVED = NO`

`CORPORATE_ACTION_SYMBOLS = []`

`CORPORATE_ACTION_APPLICATION_STATUS = NOT_APPLICABLE`

`QUANTITY_0518_0519_UNCHANGED = YES`

`CASH_CONTINUITY = PASS`

`BUY_FILL_COUNT_20230519 = 0`

`SELL_FILL_COUNT_20230519 = 0`

`POSITION_QUANTITY_MUTATION_COUNT = 0`

`CASH_MUTATION_COUNT = 0`

`PRIOR_MEASUREMENT_DEFECT_REGRESSION = NO`

`GENUINE_MARKET_MOVE_SUPPORTED = YES`

`PERFORMANCE_EVIDENCE_VALID_THROUGH = 2023-05-22`

`PERFORMANCE_EVIDENCE_QUARANTINE_REQUIRED = NO`

`CURRENT_RUN_RECOMMENDATION = CONTINUE_RUNNING`

`PERFORMANCE_TUNING_RECOMMENDED = NO`

`IMPLEMENTATION_CHANGED = NO`

`FRESH_RUN_EXECUTED = NO`

`RESUME_EXECUTED = NO`

`REPLAY_EXECUTED = NO`

`LONG_HISTORICAL_EXECUTED = NO`

`GIT_DIFF_CHECK = PASS`

`NEXT_TASK_RECOMMENDATION = Continue the existing long-horizon run unchanged. Track 67310 as a documented valid close-to-close mark-to-market loss with next-session execution reversal, not as a valuation quarantine item.`
