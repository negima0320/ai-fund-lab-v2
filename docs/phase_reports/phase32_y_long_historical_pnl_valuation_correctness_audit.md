# Phase32-Y Long Historical PnL / Valuation Correctness Audit

## Objective

Determine whether the reported Equity / DAILY_PNL / Return in the long Historical run can be treated as trustworthy performance measurement under the current canonical valuation and accounting contracts.

This was a READ-ONLY correctness audit. No source code, configuration, strategy parameter, valuation logic, accounting logic, ledger artifact, or run evidence was changed.

## Target Run

- Run ID: `runtime-test-historical-extended-smoke-20260830T081425790243Z`
- Profile: `historical-extended-smoke`
- Requested business days: 650
- Initial cash: 1,000,000 JPY
- Source commit recorded in `plan.json`: `4ff63ba05a0012c60fce50741a946eed672f8990`
- Historical Evaluation Authority: `PASS`
- Completed valuation coverage: 252 business days, `2022-10-03` through `2023-10-10`
- Run terminal state: `HALT`
- Terminal error: `Runtime CLI stopped at 2023-10-11:submit with exit code 20`

The 2023-10-11 submit halt is outside the completed valuation window audited here. The measurement audit covers committed EOD Current after execution and valuation refresh through 2023-10-10.

## Canonical Measurement Contract

The Phase25-A1 capital authority trace defines EOD Current after execution and valuation refresh as the official daily equity authority:

```text
Current equity/cash
  -> Strategy portfolio policy
  -> Position sizing capital base
  -> Planning/capital deployment constraints
  -> Submit/Safety constraints
  -> Execution-equivalent fills
  -> Current after execution and valuation refresh
  -> Daily evaluation evidence
```

The active valuation implementation computes:

```text
position.market_value = quantity * valuation_price
total_equity = cash + market_value
```

For adjusted J-Quants quote rows, current valuation resolves a basis-compatible valuation price. When the position quantity basis is `ADJUSTED`, valuation uses `adjusted_basis_valuation_price` with reconciliation status `PASS`.

## Run Integrity

Completed stages:

- `market_refresh`: 253 successful days, including 2023-10-11
- `morning`: 253 successful days, including 2023-10-11
- `sell_planning`: 253 successful days, including 2023-10-11
- `runtime_state_refresh`: 252 successful completed valuation days
- `current_valuation_refresh`: 252 successful completed valuation days
- `submit`: 252 successful completed days plus one 2023-10-11 exit-code-20 halt
- `execution`: 252 successful completed days

No failed CLI stage was observed inside the completed EOD valuation window through 2023-10-10.

## Equity Arithmetic

Result: PASS.

Across all 252 completed valuation days:

- `total_equity == cash + market_value`: 0 mismatches
- Sum of position `market_value` equals portfolio `market_value`: 0 mismatches
- Per-position `market_value == quantity * current_price`: 0 mismatches

Final completed valuation day:

| Date | Cash | Market Value | Total Equity | Return vs initial cash |
|---|---:|---:|---:|---:|
| 2023-10-10 | 816,580 | 837,970 | 1,654,550 | +65.455% |

## Fill / Cash / Ledger Reconciliation

Result: PASS.

Across all 252 completed execution days:

- Fill rows: 835
- BUY_NEW fills: 395
- BUY_ADD fills: 9
- SELL_EXIT fills: 391
- REDUCE fills: 40
- `gross_notional == quantity * execution_price`: 0 mismatches
- BUY cash effect equals negative gross notional: 0 mismatches
- SELL cash effect equals positive gross notional: 0 mismatches
- Daily cash delta equals summed fill cash effect: 0 mismatches

Aggregate fill totals:

- Total BUY gross notional: 31,541,430 JPY
- Total SELL gross notional: 31,358,010 JPY
- Net fill cash effect: -183,420 JPY

Final cash is therefore consistent with initial cash and cumulative fill cash effects:

```text
1,000,000 - 183,420 = 816,580
```

## Quantity Basis

Result: PASS for internal canonical basis consistency.

Across all valued position rows:

- `quantity_basis = ADJUSTED`
- `valuation_price_basis = ADJUSTED`
- Count: 2,752 / 2,752
- `valuation_price_authority = PASS`: 2,752 / 2,752

No RAW / ADJUSTED day-to-day alternation was observed in the completed valuation artifacts. The run is internally an adjusted-basis Historical accounting run, not a raw brokerage cash replay.

## Price Basis

Result: PASS under the current canonical adjusted-basis valuation contract.

Representative high-impact symbol `67310` was checked against actual J-Quants PIT parquet evidence. The large price jumps in the valuation artifacts match the same-day J-Quants raw and normalized evidence:

| Date | Raw C | Raw AdjC | Normalized Close | Valuation Price |
|---|---:|---:|---:|---:|
| 2023-04-28 | 2.0 | 2000.0 | 2000.0 | 2000.0 |
| 2023-05-01 | 3.0 | 3000.0 | 3000.0 | 3000.0 |
| 2023-05-11 | 2.0 | 2000.0 | 2000.0 | 2000.0 |
| 2023-06-09 | 3.0 | 3000.0 | 3000.0 | 3000.0 |
| 2023-06-20 | 2.0 | 2000.0 | 2000.0 | 2000.0 |
| 2023-08-17 | 1.0 | 1000.0 | 1000.0 | 1000.0 |

This explains the repeated +/-100,000 JPY contribution for a 100-share adjusted-basis position. It is not a hidden valuation arithmetic defect and not a price-basis alternation inside the current contract.

Important limitation: because the run uses adjusted-basis execution, position, and valuation prices consistently, the +65.455% return is trustworthy as canonical adjusted-basis Historical Runtime accounting. It should not be described as a raw broker-executable cash replay without a separate raw-basis execution and quantity reconciliation contract.

## Corporate Action

Result: PASS for the audited false-PnL question.

For the representative large-move symbol `67310`, all inspected large-move dates reported:

- `coverage_status = AVAILABLE`
- `event_status = KNOWN_NO_EVENT`
- `event_dates = []`
- `event_types = []`
- `reason_codes = []`

Current valuation artifacts also reported `corporate_action_ambiguity_status = CLEAR` for the corresponding held-position rows.

No concrete corporate-action artifact was found that explains or creates false PnL in the completed valuation window.

## Large PnL Day Inventory

Daily PnL is defined here as current EOD `total_equity` minus previous completed EOD `total_equity`, with the first day compared to initial cash.

Counts:

- `abs(DAILY_PNL) >= 50,000`: 48 days
- `abs(DAILY_PNL) >= 80,000`: 34 days
- `abs(DAILY_PNL) >= 100,000`: 15 days

Largest positive days:

| Date | DAILY_PNL | Equity | Cash | Market Value | Positions |
|---|---:|---:|---:|---:|---:|
| 2023-06-09 | +123,900 | 1,614,180 | 345,380 | 1,268,800 | 9 |
| 2023-07-03 | +113,600 | 1,646,220 | 492,820 | 1,153,400 | 8 |
| 2023-05-01 | +108,630 | 1,557,090 | 259,060 | 1,298,030 | 10 |
| 2023-05-26 | +100,900 | 1,548,890 | 400,290 | 1,148,600 | 8 |
| 2023-06-21 | +100,700 | 1,664,880 | 554,380 | 1,110,500 | 8 |

Largest negative days:

| Date | DAILY_PNL | Equity | Cash | Market Value | Positions |
|---|---:|---:|---:|---:|---:|
| 2023-06-20 | -124,200 | 1,564,180 | 486,880 | 1,077,300 | 10 |
| 2023-08-17 | -123,280 | 1,455,190 | 209,650 | 1,245,540 | 11 |
| 2023-05-11 | -120,270 | 1,490,090 | 180,690 | 1,309,400 | 14 |
| 2023-06-08 | -116,600 | 1,490,280 | 193,680 | 1,296,600 | 10 |
| 2023-07-18 | -108,800 | 1,530,390 | 356,690 | 1,173,700 | 9 |

## Symbol-Level Reconciliation

Representative large-move days reconcile to position and fill effects:

### 2023-05-01

- DAILY_PNL: +108,630
- Cash delta: 0
- Market-value delta: +108,630
- Dominant contributor: `67310`, 100 shares, price `2000 -> 3000`, market-value delta +100,000
- No fills

### 2023-05-11

- DAILY_PNL: -120,270
- Cash delta: -97,970
- Market-value delta: -22,300
- Fill cash effect: -97,970
- Dominant valuation contributor: `67310`, 100 shares, price `3000 -> 2000`, market-value delta -100,000
- Major fills: BUY `73510`, BUY `76020`, SELL_EXIT `60160`, BUY `93800`

### 2023-06-09

- DAILY_PNL: +123,900
- Cash delta: +151,700
- Market-value delta: -27,800
- Fill cash effect: +151,700
- Dominant contributors: SELL_EXIT `43950`, `67310` price `2000 -> 3000`, BUY `36670`

### 2023-06-20

- DAILY_PNL: -124,200
- Cash delta: +123,300
- Market-value delta: -247,500
- Fill cash effect: +123,300
- Dominant contributors: BUY `40750`, SELL_EXIT `92410`, `67310` price `3000 -> 2000`, SELL_EXIT `50250`, SELL_EXIT `33230`

### 2023-08-17

- DAILY_PNL: -123,280
- Cash delta: -36,500
- Market-value delta: -86,780
- Fill cash effect: -36,500
- Dominant contributor: `67310`, 100 shares, price `2000 -> 1000`, market-value delta -100,000
- Major fill: BUY `44770`

These days are large, but they are arithmetically explained by recorded fills and PIT valuation prices.

## Alternation Analysis

Result: no price/quantity basis alternation detected.

Observed alternation-like behavior is concentrated in volatile same-symbol valuation prices, especially `67310`. The artifacts show:

- quantity basis remains `ADJUSTED`
- valuation price basis remains `ADJUSTED`
- valuation authority remains `PASS`
- raw and normalized J-Quants PIT evidence contain the same adjusted close values used by valuation
- corporate action evidence for the inspected symbol/date pairs is `KNOWN_NO_EVENT`

Therefore the observed large day-to-day PnL swings are not caused by alternating RAW and ADJUSTED valuation bases.

## Authorized Stale Valuation

22 position rows used `AUTHORIZED_STALE_VALUATION` rather than `FRESH_CURRENT_QUOTE`.

Symbols:

- `61440`: 15 rows
- `46450`: 3 rows
- `74860`: 2 rows
- `79460`: 1 row
- `59730`: 1 row

Reason was consistently `listed_held_position_no_valid_close_ca_clear`. These rows did not create equity arithmetic mismatches, did not create price/quantity basis mismatches, and did not match the large `67310` PnL driver.

## Prior Measurement Regression Check

Result: no regression reproduced in the completed valuation window.

Prior measurement concerns included:

- fixed `runtime_evaluation_capital` being confused with official equity
- missing daily evaluation artifact producer
- valuation REVIEW_REQUIRED boundaries for held-position missing quote / corporate-action ambiguity
- price/quantity basis mismatch
- unresolved current valuation authority leaking into later days

Current findings:

- Official performance measurement was derived from EOD Current `total_equity`, not fixed `runtime_evaluation_capital`.
- Current valuation refresh applied successfully through 2023-10-10.
- No `total_equity`, market value, or per-position arithmetic mismatch was found.
- No RAW / ADJUSTED mismatch was found.
- Authorized stale valuation rows were explicit and did not silently create unresolved Current state.

## Contamination Scope

No evidence was found that a measurement defect contaminated the completed valuation series through 2023-10-10.

The 2023-10-11 submit halt prevents treating the 650-day request as a completed long run, but it does not invalidate the arithmetic correctness of the completed 252-day valuation window.

## Performance Trust Classification

Classification: `TRUSTED_AS_CANONICAL_ADJUSTED_BASIS_HISTORICAL_ACCOUNTING`.

The current +65.455% return can be trusted for Strategy performance characterization only in that scope:

- trusted: canonical Historical Runtime accounting with adjusted-basis execution/position/valuation consistency
- not yet claimed: raw brokerage-executable cash replay or live broker-equivalent notional accounting

## Repair Required

Correctness repair required before using completed-window adjusted-basis Strategy performance characterization: NO.

Conditional future work, outside Phase32-Y:

- If the project wants live broker-equivalent performance claims, define and validate a separate raw-basis execution / adjusted-quantity reconciliation contract.
- The 2023-10-11 submit halt should be investigated separately before extending this same run further.

## Long Run May Continue

The completed valuation measurement does not require abandoning the run. However, the run is currently halted at 2023-10-11 submit, so continuation requires a separate root-cause audit/repair of that submit REVIEW_REQUIRED boundary.

Codex did not fresh-run, resume, replay, or run long Historical validation.

## Strategy Evaluation Allowed

YES, for the completed 2022-10-03 through 2023-10-10 window and with the adjusted-basis Historical accounting scope stated above.

Do not characterize the unfinished 650-business-day run as completed.

## NO CODE CHANGE

Confirmed. No code was changed in Phase32-Y.

## NO Strategy / Parameter / Threshold / Weight Change

Confirmed. No Strategy semantics, parameters, thresholds, weights, cash policy, risk pacing, retention rules, or ADD behavior were changed.

## NO Future-Information Use

Confirmed. The audit used completed run artifacts, current source contracts, EOD accounting artifacts, same-day/adjacent-day valuation reconciliation, and J-Quants PIT parquet evidence for the valuation dates being audited. It did not use future price, future return, future regime, later outcome, MFE/MAE, or hindsight for Strategy evaluation.

## Final Judgment Answers

1. `IS_REPORTED_EQUITY_ARITHMETICALLY_CONSISTENT`: YES.
2. `ARE_LARGE_DAILY_PNL_MOVES_EXPLAINED_BY_REAL_PRICE_AND_POSITION_CHANGES`: YES, under current J-Quants adjusted-basis Historical accounting evidence.
3. `IS_ANY_PRICE_QUANTITY_BASIS_ALTERNATION_PRESENT`: NO.
4. `IS_ANY_CORPORATE_ACTION_CREATING_FALSE_PNL`: NO concrete evidence found.
5. `DO_FILLS_LEDGER_CASH_AND_POSITIONS_RECONCILE`: YES.
6. `HAS_ANY_PRIOR_MEASUREMENT_DEFECT_REGRESSED`: NO.
7. `CAN_THE_CURRENT_PLUS_60_TO_70_PERCENT_RETURN_BE_TRUSTED`: YES, as canonical adjusted-basis Historical Runtime accounting for the completed window; not as raw broker-executable cash replay.
8. `IS_ANY_CORRECTNESS_REPAIR_REQUIRED`: NO for completed-window measurement correctness.
9. `MAY_THE_LONG_HISTORICAL_RUN_CONTINUE`: YES from a measurement-correctness perspective, but the separate 2023-10-11 submit halt must be handled first.
10. `MAY_STRATEGY_PERFORMANCE_CHARACTERIZATION_PROCEED`: YES for the completed 252-day adjusted-basis window, with scope limitation explicitly stated.

Final Judgment:

`PHASE32_Y_LONG_HISTORICAL_PERFORMANCE_MEASUREMENT_TRUSTED`
