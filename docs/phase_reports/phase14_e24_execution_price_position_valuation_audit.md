# Phase14-E24 Execution Price / Position Valuation Audit

## Summary

Phase14-E24 audited the price and valuation path after the E22/E23 accepted and filled Demo BUY operation.

Final judgment: `PHASE14E24_POSITION_VALUATION_BUG_FOUND`

Findings:

1. Broker Position evidence contains average prices, market prices, market values, quantities, and unrealized PnL.
2. Runtime v2 Ledger Position records preserve those Broker Position values correctly.
3. Runtime Current SoT does not reflect the filled positions or their valuation.
4. Public Report reads Current SoT only, so it shows `positions=[]` and `market_value=0`.
5. Capital Allocation / Morning Planning reads Runtime Current SoT and therefore still sees no current exposure.
6. Morning Pending estimated price was `1000.0` for all five symbols because feature inputs did not include a price column and the fallback `per_order_budget / 100` was used.

The suspected `100円固定` acquisition value is not introduced inside the Runtime v2 Ledger projection. The saved Broker Position evidence itself contains `average_price=102.0000` for the five newly accepted symbols. Runtime v2 copies that value into Ledger Position records as `102.0`.

However, because raw Broker responses are intentionally not saved, the audit cannot prove whether `102.0000` came from Tachibana Demo's true response, a Demo fixture/mock layer, or a Broker adapter default. The saved evidence has `source=mock`, which makes provenance ambiguous and should be cleaned up in a later fix.

## Prohibited Actions

| Action | Result |
| --- | --- |
| Additional Submit | Not executed |
| Production order | Not executed |
| Production Broker API Write | Not executed |
| Notification actual send | Not executed |
| launchd change | Not executed |
| Code change | Not executed |

## Evidence Sources

Read-only local artifacts only:

- `.runtime/runtime_state/broker_readonly/2026-07-08/tachibana_snapshot.json`
- `.runtime/persistent_ledger/orders.jsonl`
- `.runtime/persistent_ledger/positions.jsonl`
- `.runtime/persistent_ledger/cash.jsonl`
- `.runtime/persistent_ledger/executions.jsonl`
- `.runtime/persistent_ledger/state.json`
- `.runtime/pending_order_plan/pending_order_plan.json`
- `reports/runtime_v2/2026-07-08/runtime_report.json`
- `reports/public/runtime_v2/latest.md`
- `.runtime/operations/feature_artifacts/2026-07-07/*.parquet`

No Broker API call was made during E24.

## Broker Position Evidence

E22/E23 Broker Position evidence for the five accepted BUY symbols:

| Symbol | Quantity | Average Price | Market Price | Market Value | Unrealized PnL |
| --- | ---: | ---: | ---: | ---: | ---: |
| `4591` | 100 | 102.0000 | 77.0000 | 7,700 | -2,500 |
| `6327` | 100 | 102.0000 | 5,140.0000 | 514,000 | 503,800 |
| `6897` | 100 | 102.0000 | 677.0000 | 67,700 | 57,500 |
| `7878` | 100 | 102.0000 | 1,554.0000 | 155,400 | 145,200 |
| `6522` | 100 | 102.0000 | 2,350.0000 | 235,000 | 224,800 |

Aggregates from Broker Position evidence:

- position market value: `979,800`
- acquisition basis from average_price: `51,000`
- unrealized PnL: `928,800`

Broker cash / buying power evidence:

- cash_available: `19,949,120`
- buying_power: `19,949,120`

This supports that Tachibana Demo account evidence changed after the filled orders. It does not imply those values should overwrite Runtime Current SoT directly in demo mode.

## OrderList Evidence

Broker OrderList does not provide execution price for these market orders:

| Symbol | Order Price | Quantity | Executed Quantity | Remaining Quantity | Status |
| --- | ---: | ---: | ---: | ---: | --- |
| `4591` | 0.0000 | 100 | 100 | 0 | 全部約定 |
| `6327` | 0.0000 | 100 | 100 | 0 | 全部約定 |
| `6897` | 0.0000 | 100 | 100 | 0 | 全部約定 |
| `7878` | 0.0000 | 100 | 100 | 0 | 全部約定 |
| `6522` | 0.0000 | 100 | 100 | 0 | 全部約定 |

Because `CLMOrderListDetail` failed, execution price is not available from Execution detail. Current valuation must therefore be based on Position evidence, not OrderList price.

## Runtime Ledger Position

Runtime Ledger Position records match Broker Position values:

| Symbol | Ledger Quantity | Ledger Average Price | Ledger Market Value | Source |
| --- | ---: | ---: | ---: | --- |
| `4591` | 100 | 102.0 | 7,700 | `runtime_v2_execution_readonly` |
| `6327` | 100 | 102.0 | 514,000 | `runtime_v2_execution_readonly` |
| `6897` | 100 | 102.0 | 67,700 | `runtime_v2_execution_readonly` |
| `7878` | 100 | 102.0 | 155,400 | `runtime_v2_execution_readonly` |
| `6522` | 100 | 102.0 | 235,000 | `runtime_v2_execution_readonly` |

Conclusion:

`Broker Position -> Runtime normalizer -> Ledger Position` is preserving price and valuation fields.

The normalizer maps:

- issue code: `issue_code`, `sIssueCode`, `sOrderIssueCode`, `sMeigaraCode`, `860`
- quantity: `quantity`, `sQuantity`, `sZanKabuSuu`, `864`
- average price: `average_price`, `sAveragePrice`, `sBokaTanka`, `sHeikinTanka`, `855`
- market price: `market_price`, `sMarketPrice`, `sGenzaine`, `sGenzaichi`, `859`
- market value: `market_value`, `sMarketValue`, `sHyokaGaku`, `sHyoukaGaku`, `858`
- unrealized PnL: `unrealized_pnl`, `sUnrealizedPnl`, `sHyokaSoneki`, `sHyoukaSoneki`, `856`

## Runtime Current SoT

Runtime Current SoT still shows the Phase14-E8 initial demo operation state:

| Field | Value |
| --- | --- |
| cash | 1,000,000 |
| buying_power | 1,000,000 |
| market_value | 0 |
| total_equity | 1,000,000 |
| positions | `[]` |
| source | `phase14e8_demo_operation_initial_state` |

This means filled positions and their valuation are not reflected into Current SoT.

This behavior partly follows the E8 Demo Broker Capability rule that broker cash / reset positions must not automatically overwrite Runtime Current SoT. But after Runtime v2 itself submitted and accepted orders, there must be a separate Demo Operation asset projection that reflects Runtime-owned fills into Current without treating the whole Demo account reset as SoT. That projection is not connected.

## Public Report

Public Report reads Current SoT, not Ledger Position evidence:

- Cash: `JPY 1,000,000`
- Buying power: `JPY 1,000,000`
- Market value: `JPY 0`
- Total equity: `JPY 1,000,000`
- Holdings: no active positions

Therefore Public Report does not show the five accepted and filled positions or their valuation.

This fails the E24 acceptance requirement that Broker Position -> Runtime -> Ledger -> Current -> Public Report valuation must match.

## Morning Planning / Capital Allocation

The consumed Pending plan used:

| Symbol | Quantity | Estimated Price | Estimated Amount |
| --- | ---: | ---: | ---: |
| `65220` | 100 | 1,000 | 100,000 |
| `78780` | 100 | 1,000 | 100,000 |
| `68970` | 100 | 1,000 | 100,000 |
| `63270` | 100 | 1,000 | 100,000 |
| `45910` | 100 | 1,000 | 100,000 |

The feature files for 2026-07-07 show:

- `candidate_features.parquet`: no `current_price`, `close`, `Close`, `adjusted_close`, or `close_price` column.
- `position_feature_input.parquet`: zero rows.
- `capital_policy_input.parquet`: policy placeholder row only.

Runtime v2 Morning Planning uses:

- `evaluation_capital = capability.default_evaluation_capital = 1,000,000`
- `per_order_budget = min(evaluation_capital / max_orders, 100,000) = 100,000`
- `_estimated_price(row, fallback_budget)` returns `fallback_budget / 100 = 1,000` when no price column exists.

Conclusion:

The fixed `1000` estimated price is a fallback caused by missing price features, not Broker execution evidence. It affects order sizing and capital allocation assumptions.

## Where The Bug Occurs

| Stage | Price / Valuation State | Judgment |
| --- | --- | --- |
| Broker OrderList | filled quantity/status present, execution price absent (`price=0`) | Expected for market order list |
| Broker Position | average_price, market_price, market_value present | Present, but provenance says `source=mock` |
| Runtime normalizer | maps Broker Position price/value fields | PASS |
| Ledger Position | matches Broker Position values | PASS |
| Asset / Current SoT | remains cash 1M, positions empty, market_value 0 | BUG |
| Public Report | reads Current SoT only, positions empty | BUG |
| Capital Allocation / next Planning | reads Current SoT/evaluation capital, not filled exposure | BUG |
| Morning estimated price | 1000 fallback because candidate features lack price columns | BUG / DESIGN GAP |

## Root Cause Classification

Primary bug:

`Ledger Position valuation is not promoted into Runtime Current SoT for Runtime-owned Demo fills.`

Secondary bug:

`Public Report and Capital Allocation read Current SoT only, so they miss filled positions that exist in Ledger Position evidence.`

Secondary design gap:

`Morning Planning lacks a reliable price source for order sizing when candidate feature inputs do not contain current_price/close columns; it falls back to per_order_budget / 100.`

Provenance gap:

`Broker Position evidence has source=mock and raw response is not saved, so 102.0000 cannot be independently verified as raw Tachibana Demo output from local artifacts.`

## Acceptance Review

| Acceptance Item | Result |
| --- | --- |
| Broker Position price / quantity / valuation audited | PASS |
| Runtime Ledger values compared | PASS |
| Current SoT compared | PASS |
| Public Report compared | PASS |
| Capital Allocation input path reviewed | PASS |
| Fixed 100 / 1000 source investigated | PASS |
| Broker -> Ledger valuation matches | PASS |
| Ledger -> Current valuation matches | FAIL |
| Current -> Public Report valuation matches | FAIL |
| Current -> Capital Allocation exposure matches | FAIL |
| No additional Submit | PASS |
| No Production order | PASS |
| No Notification actual send | PASS |
| No launchd change | PASS |
| Code unchanged | PASS |

## Required Follow-up

1. Define Demo Operation Asset projection for Runtime-owned fills:
   - accepted Runtime Submit
   - filled OrderList
   - matching Position evidence
   - cash / buying power evidence
   - without copying unrelated Demo reset positions into Current SoT.
2. Add a Current SoT valuation writer path that updates:
   - positions
   - market_value
   - total_equity
   - unrealized PnL if modeled
   - source evidence refs
3. Update Public Report to show Current SoT positions after projection.
4. Ensure next Morning/Capital Allocation subtracts current exposure from the 1,000,000 JPY evaluation capital.
5. Add a price-source contract for Morning Planning so `estimated_price=1000` fallback is explicit and REVIEW_REQUIRED or blocked unless an accepted price source is available.
6. Clarify `source=mock` in Broker normalized evidence so live Demo evidence is not mislabeled as mock.

## Final Judgment

`PHASE14E24_POSITION_VALUATION_BUG_FOUND`

