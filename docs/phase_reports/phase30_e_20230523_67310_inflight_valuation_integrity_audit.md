# Phase30-E 2023-05-23 / 67310 In-Flight Valuation Integrity Sentinel Audit

Task ID: `Phase30-E`

Target run:

```text
runtime-test-historical-extended-smoke-20260815T061857447380Z
```

Run handling:

```text
READ-ONLY AUDIT ONLY
NO TARGET RUN ARTIFACT MUTATION
NO STRATEGY / RUNTIME / CONFIG / THRESHOLD CHANGE
NO IMPLEMENTATION AUTHORIZED
```

## Primary Judgment

```text
PHASE30_E_20230523_LARGE_LOSS_CONFIRMED_GENUINE_NO_VALUATION_RECURRENCE
```

Measurement Integrity:

```text
PASS
```

The observed `-116,650 JPY` loss reconciles exactly from the 2023-05-22 valuation-applied equity to the 2023-05-23 valuation-applied equity:

```text
2023-05-22 valuation-applied equity: 1,071,920
2023-05-23 valuation-applied equity:   955,270
Daily change:                         -116,650
```

The loss is genuine Strategy / market PnL. The dominant component is a same-day `67310` entry loss:

```text
67310 BUY: 100 @ 3000
67310 2023-05-23 valuation: 100 @ 2000
67310 contribution: -100,000 JPY
```

No Phase29 67310 valuation/basis defect recurrence was found.

## Important Date Alignment

Persistent Current snapshots around this date have two relevant states:

- 2023-05-23 post-execution Current: `cash 247,160`, `market_value 824,560`, `equity 1,071,720`.
- 2023-05-23 current valuation refresh applies same-day close valuation and writes valuation history with `market_value 708,110`.
- The valuation-applied equity is `247,160 + 708,110 = 955,270`, which appears in the next persistent Current snapshot dated 2023-05-24.

Therefore this audit reconciles the user-observed `-116,650 JPY` as:

```text
2023-05-22 close valuation-applied equity
  -> 2023-05-23 execution
  -> 2023-05-23 close valuation-applied equity
```

## 2023-05-23 PnL Decomposition

Basis:

- Previous state: 2023-05-22 valuation history, market value `548,360`, cash `523,560`, equity `1,071,920`.
- Current state: 2023-05-23 valuation history, market value `708,110`, cash `247,160`, equity `955,270`.
- Cash movement: `-300,000` BUY `67310` + `23,600` SELL `76010` = `-276,400`.
- Market value movement: `708,110 - 548,360 = +159,750`.
- Equity movement: `-276,400 + 159,750 = -116,650`.

| Symbol | 2023-05-22 Qty | 2023-05-23 Qty | Prev valuation price | 2023-05-23 valuation / exec price | Prev value | Current value / proceeds | Execution effect | Realized PnL vs cost | Equity contribution |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `27620` | 100 | 100 | 236 | 226 | 23,600 | 22,600 | 0 | 0 | -1,000 |
| `30410` | 100 | 100 | 1444 | 1330 | 144,400 | 133,000 | 0 | 0 | -11,400 |
| `31370` | 100 | 100 | 231 | 210 | 23,100 | 21,000 | 0 | 0 | -2,100 |
| `67310` | 0 | 100 | n/a | 2000 valuation, 3000 BUY | 0 | 200,000 | -300,000 | 0 | -100,000 |
| `76470` | 4100 | 4100 | 28 | 28 | 114,800 | 114,800 | 0 | 0 | 0 |
| `94320` | 1300 | 1300 | 168.2 | 166.7 | 218,660 | 216,710 | 0 | 0 | -1,950 |
| `76010` | 100 | 0 | 238 | 236 SELL | 23,800 | 23,600 proceeds | +23,600 | -2,600 | -200 |
| **Total** |  |  |  |  | **548,360** | **732,710 gross value/proceeds** | **-276,400 net cash effect** |  | **-116,650** |

Notes:

- For continuing holdings, equity contribution equals 2023-05-23 valuation market value minus 2023-05-22 valuation market value.
- For `67310`, contribution equals `200,000 market value - 300,000 cash paid = -100,000`.
- For `76010`, contribution equals `23,600 sale proceeds - 23,800 prior valuation value = -200`. The realized PnL versus cost is `23600 - 26200 = -2600`, but prior close equity had already included `-2400` unrealized PnL.

The symbol contributions sum exactly:

```text
-1,000 -11,400 -2,100 -100,000 +0 -1,950 -200 = -116,650
```

## 67310 Valuation / Basis

### 2023-05-22

`67310` was not held on 2023-05-22.

Market evidence existed:

```text
adjusted open: 3000
adjusted close: 2000
raw/economic open: 3.0
raw/economic close: 2.0
raw_adjusted_close_ratio: 0.001
```

### 2023-05-23

Execution:

```text
side: BUY
quantity: 100
fill_price: 3000
cash_effect: -300,000
source_price_ref: raw_normalized ... 2023-05-23:67310:Open
```

Position / valuation:

```text
quantity: 100
quantity_basis: ADJUSTED
quantity_basis_provenance: runtime_execution_price_authority:adjusted_reference_price_basis
average_price: 3000
cost_basis: 300,000
valuation_price: 2000
valuation_price_basis: ADJUSTED
valuation_price_role: reconciled_adjusted_basis_valuation_price
valuation_price_authority: PASS
valuation_price_authority_reason: valuation_price_basis_matches_adjusted_quantity_basis
market_value: 200,000
unrealized_pnl: -100,000
```

Market evidence:

```text
adjusted open: 3000
adjusted high: 3000
adjusted low: 2000
adjusted close: 2000
adjusted_basis_valuation_price: 2000
raw/economic open: 3.0
raw/economic high: 3.0
raw/economic low: 2.0
raw/economic close: 2.0
economic_valuation_price: 2.0
raw_adjusted_close_ratio: 0.001
```

Conclusion:

```text
valuation_price_basis == quantity_basis == ADJUSTED
```

The `67310` 2023-05-23 loss is an entry loss from adjusted-basis `3000` to adjusted-basis `2000`, not a raw/adjusted basis mismatch.

### 2023-05-24

Execution:

```text
side: SELL
quantity: 100
sell_price: 2000
cash_effect: +200,000
gross_realized_pnl: -100,000
```

Market evidence:

```text
adjusted open: 2000
adjusted close: 3000
raw/economic open: 2.0
raw/economic close: 3.0
raw_adjusted_close_ratio: 0.001
```

`67310` was closed on 2023-05-24 and was no longer in 2023-05-24 close valuation positions.

## Phase29 Defect Recurrence

```text
PHASE29_67310_VALUATION_DEFECT_RECURRENCE = NO
```

Specific recurrence tests:

| Failure mode | Result | Evidence |
|---|---|---|
| adjusted analytical price used as economic valuation | NO | Market evidence carries both `economic_valuation_price` and `adjusted_basis_valuation_price`; valuation projection selected adjusted basis because quantity basis was adjusted. |
| raw price x adjusted-basis quantity | NO | `67310` valuation used `2000 ADJUSTED x 100 ADJUSTED = 200,000`. It did not use raw/economic `2.0 x 100`. |
| adjusted price x raw-basis quantity | NO | `quantity_basis` was `ADJUSTED`, not raw. |
| basis metadata loss | NO | Position carried `quantity_basis`, `quantity_basis_provenance`, `valuation_price_basis`, `valuation_price_role`, and `valuation_price_authority_reason`. |
| day-to-day price alternation | NO | `67310` was only held over the 2023-05-23 close valuation and sold at 2023-05-24 open. The held valuation did not alternate basis. |

## Other Symbols

The 2023-05-23 loss was not exclusively `67310`.

Other symbol contributions:

```text
30410: -11,400
31370:  -2,100
94320:  -1,950
27620:  -1,000
76010:    -200
76470:       0
```

These total `-16,650`. `67310` accounts for the remaining `-100,000`.

## Equity / Cash Reconciliation

| Valuation date | Cash | Position market value | Equity | Cash + market value | Difference |
|---|---:|---:|---:|---:|---:|
| 2023-05-22 close valuation | 523,560 | 548,360 | 1,071,920 | 1,071,920 | 0 |
| 2023-05-23 close valuation | 247,160 | 708,110 | 955,270 | 955,270 | 0 |
| 2023-05-24 close valuation | 447,160 | 505,360 | 952,520 | 952,520 | 0 |

Persistent Current snapshots:

| Snapshot | Cash | Market value | Equity | Difference |
|---|---:|---:|---:|---:|
| `.runtime/persistent_ledger/history/current/2023-05-22T0635000000.json` | 523,560 | 547,700 | 1,071,260 | 0 |
| `.runtime/persistent_ledger/history/current/2023-05-23T0635000000.json` | 247,160 | 824,560 | 1,071,720 | 0 |
| `.runtime/persistent_ledger/history/current/2023-05-24T0635000000.json` | 447,160 | 508,110 | 955,270 | 0 |

No unexplained cash mutation was found:

```text
2023-05-23 cash:
523,560 - 300,000 BUY 67310 + 23,600 SELL 76010 = 247,160

2023-05-24 cash:
247,160 + 200,000 SELL 67310 = 447,160
```

## Corporate-Action / Adjustment Evidence

`67310` has a visible raw/economic versus adjusted-basis scale difference:

```text
raw/economic close 2023-05-23: 2.0
adjusted close 2023-05-23:    2000
raw_adjusted_close_ratio:     0.001
```

This is precisely the kind of symbol that should remain a valuation sentinel. However, the runtime did not multiply raw/economic price by adjusted quantity, nor adjusted price by raw quantity. The position-level valuation carried adjusted quantity and adjusted valuation price consistently.

No separate corporate-event decision authority entry for `67310` was found in the 2023-05-23 Strategy `corporate_event.json`; the relevant adjustment evidence is in market evidence / J-Quants adjusted OHLCV fields.

## Capital Authority Contamination

```text
Capital Authority Contamination: NO
```

No valuation defect was found, so no contaminated equity reached:

- Portfolio Construction
- Position Sizing
- target weights
- Safety
- next-day Current
- 2023-05-24 decisions

2023-05-24 used the `955,270` equity state after a genuine 2023-05-23 market/Strategy loss. That is clean performance evidence, not contaminated capital authority.

## Performance Evidence Status

```text
CLEAN_FOR_CONTINUED_LONG_HORIZON_PERFORMANCE_ATTRIBUTION_WITH_67310_ENTRY_LOSS_NOTED
```

The 2023-05-23 large loss is valid Strategy / market PnL evidence. It should be interpreted as a material stock-selection / entry-risk event, dominated by `67310`, not as Phase29 valuation recurrence.

## Current Run Recommendation

```text
CONTINUE CURRENT 977BD RUN
```

Observed run state during this audit:

```text
status: RUNNING
completed_count: 195
latest_completed: 2023-05-29
next_job: 2023-05-30:market_refresh
halted_job: null
error: null
```

## Implementation

```text
NO IMPLEMENTATION AUTHORIZED
```

## Evidence Paths

Primary evidence:

- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260815T061857447380Z/daily/2023-05-23/current_valuation_refresh/valuation_projection.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260815T061857447380Z/daily/2023-05-23/current_valuation_refresh/valuation_apply_evidence.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260815T061857447380Z/daily/2023-05-23/current_valuation_refresh/valuation_input.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260815T061857447380Z/daily/2023-05-23/current_valuation_refresh/market_evidence_authority.json`
- `.runtime/persistent_ledger/history/valuation/2023-05-22/f9b254c99c482533.json`
- `.runtime/persistent_ledger/history/valuation/2023-05-23/a303d0115e004221.json`
- `.runtime/persistent_ledger/history/valuation/2023-05-24/6581331d783a6861.json`
- `.runtime/persistent_ledger/history/current/2023-05-22T0635000000.json`
- `.runtime/persistent_ledger/history/current/2023-05-23T0635000000.json`
- `.runtime/persistent_ledger/history/current/2023-05-24T0635000000.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260815T061857447380Z/daily/2023-05-23/execution/fills.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260815T061857447380Z/daily/2023-05-23/execution/realized_slices.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260815T061857447380Z/daily/2023-05-24/execution/fills.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260815T061857447380Z/daily/2023-05-24/execution/realized_slices.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260815T061857447380Z/daily/2023-05-23/positions/position_campaigns.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260815T061857447380Z/daily/2023-05-24/positions/position_campaigns.json`
- `.runtime/runtime_state/market/2023-05-22/market_evidence.json`
- `.runtime/runtime_state/market/2023-05-23/market_evidence.json`
- `.runtime/runtime_state/market/2023-05-24/market_evidence.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260815T061857447380Z/run_state.json`
