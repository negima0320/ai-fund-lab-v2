# Phase14-E26 Submit Parameter & Valuation Self-Audit

## Summary

Phase14-E26 audited the E22/E25 BUY submit, sizing, fill price, and valuation path.

Final judgment: `PHASE14E26_PRICE_AND_SIZING_ROOT_CAUSE_IDENTIFIED`

Root cause:

1. The Broker request did not carry `100` or `1000` as an order price. Runtime v2 submitted market orders with `sOrderPrice=0` and `sOrderSuryou=100`.
2. The order quantity was created by Morning Planning from a price fallback, not from a real market price. Candidate feature inputs lacked `current_price`, `close`, `Close`, `adjusted_close`, and `close_price`, so `_estimated_price()` returned `per_order_budget / 100 = 1000`.
3. With `evaluation_capital=1,000,000`, `max_orders=5`, and the cap `per_order_budget=100,000`, the fallback produced `quantity=100` for every order.
4. Tachibana Demo then filled the five market orders with Position evidence showing `average_price=102.0` for each symbol. This made Runtime-owned cost basis only `51,000`, not the planned `500,000`.
5. E25 projected Current SoT as `cash=949,000`, `market_value=979,800`, `total_equity=1,928,800` by combining Runtime-owned cost basis with Broker Position market values. The arithmetic is internally traceable, but the result should not be treated as production-equivalent valuation without a real price-source / execution-price policy.

No code was changed. No additional Submit was executed. No Broker API Write, Production order, Notification send, or launchd change was performed.

## Evidence Sources

Read-only local artifacts:

- `.runtime/runtime_state/run_manifest/2026-07-08/runtime-v2-submit-2026-07-08-20260708T062328.649239+0000.json`
- `.runtime/runtime_state/morning_pipeline/2026-07-08/order_plan.json`
- `.runtime/pending_order_plan/pending_order_plan.json`
- `.runtime/runtime_state/broker_readonly/2026-07-08/tachibana_snapshot.json`
- `.runtime/persistent_ledger/orders.jsonl`
- `.runtime/persistent_ledger/positions.jsonl`
- `.runtime/persistent_ledger/state.json`
- `reports/public/runtime_v2/latest.md`
- `.runtime/operations/feature_artifacts/2026-07-07/candidate_features.parquet`

Code inspected without modification:

- `src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py`
- `src/ai_fund_lab_v2/broker/tachibana_order_request.py`
- `src/ai_fund_lab_v2/runtime_v2/asset/runtime_owned_fill_projection.py`

## Submit Parameter Audit

E22 submit manifest:

| Field | Value |
| --- | --- |
| demo_submit_executed | `true` |
| submitted_count | `5` |
| accepted_count | `5` |
| rejected_count | `0` |
| unknown_count | `0` |
| blocked_count | `0` |
| pending_plan_id | `pending-order-plan-c395bc29294719ec` |

Submitted symbols:

| Internal Symbol | Broker Issue Code | Side | Quantity | Status |
| --- | --- | --- | ---: | --- |
| `65220` | `6522` | BUY | 100 | ACCEPTED |
| `78780` | `7878` | BUY | 100 | ACCEPTED |
| `68970` | `6897` | BUY | 100 | ACCEPTED |
| `63270` | `6327` | BUY | 100 | ACCEPTED |
| `45910` | `4591` | BUY | 100 | ACCEPTED |

The manifest records issue-code normalization and response classification, but does not persist a full safe request summary for E22. The request builder implementation establishes the request shape:

| Broker Request Field | Runtime v2 Value / Source |
| --- | --- |
| `sCLMID` | `CLMKabuNewOrder` |
| `sIssueCode` | normalized broker issue code, e.g. `6522` |
| `sSizyouC` | `00` |
| `sBaibaiKubun` | `3` for BUY |
| `sCondition` | `0` |
| `sOrderPrice` | `0` for market order |
| `sOrderSuryou` | `100` |
| `sGenkinShinyouKubun` | `0` |
| `sOrderExpireDay` | `0` |

Conclusion:

- `estimated_price=1000` was not sent as `sOrderPrice`.
- `100` appeared as share quantity, not order price.
- The Broker-side fill price around 100 yen did not come from Runtime setting `sOrderPrice=100`.

## Planning / Sizing Audit

Morning Planning created:

| Symbol | Quantity | Estimated Price | Estimated Amount | Order Type |
| --- | ---: | ---: | ---: | --- |
| `65220` | 100 | 1,000 | 100,000 | MARKET |
| `78780` | 100 | 1,000 | 100,000 | MARKET |
| `68970` | 100 | 1,000 | 100,000 | MARKET |
| `63270` | 100 | 1,000 | 100,000 | MARKET |
| `45910` | 100 | 1,000 | 100,000 | MARKET |

The sizing path is:

1. `evaluation_capital = 1,000,000`
2. `per_order_budget = min(evaluation_capital / max_orders, 100,000) = 100,000`
3. Feature row has no valid price column.
4. `_estimated_price(row, fallback_budget)` returns `fallback_budget / 100 = 1,000`
5. `_round_lot_quantity(100,000, 1,000)` returns `100`
6. `estimated_amount = 100 * 1,000 = 100,000`

Feature evidence:

| Feature Artifact | Rows | Price Columns |
| --- | ---: | --- |
| `candidate_features.parquet` | 4,370 | none of `current_price`, `close`, `Close`, `adjusted_close`, `close_price` |
| `position_feature_input.parquet` | 0 | schema has `current_price`, but no rows |
| `capital_policy_input.parquet` | 1 | no price column |

Conclusion:

`quantity=100` is explained by the fallback price algorithm and 100-share lot rounding. This is a Runtime planning/sizing policy gap: price-source absence should have stopped planning or produced `NO_SIGNAL` / `REVIEW_REQUIRED`, not normal approved MARKET orders.

## Broker Evidence Audit

Broker OrderList evidence:

| Symbol | Status | Order Price | Order Type | Quantity | Executed Quantity | Remaining Quantity |
| --- | --- | ---: | --- | ---: | ---: | ---: |
| `6522` | 全部約定 | 0.0000 | 1 | 100 | 100 | 0 |
| `7878` | 全部約定 | 0.0000 | 1 | 100 | 100 | 0 |
| `6897` | 全部約定 | 0.0000 | 1 | 100 | 100 | 0 |
| `6327` | 全部約定 | 0.0000 | 1 | 100 | 100 | 0 |
| `4591` | 全部約定 | 0.0000 | 1 | 100 | 100 | 0 |

Broker Position evidence:

| Symbol | Quantity | Average Price | Market Price | Market Value | Unrealized PnL |
| --- | ---: | ---: | ---: | ---: | ---: |
| `6522` | 100 | 102 | 2,350 | 235,000 | 224,800 |
| `7878` | 100 | 102 | 1,554 | 155,400 | 145,200 |
| `6897` | 100 | 102 | 677 | 67,700 | 57,500 |
| `6327` | 100 | 102 | 5,140 | 514,000 | 503,800 |
| `4591` | 100 | 102 | 77 | 7,700 | -2,500 |

Aggregates:

- Runtime-owned cost basis: `102 * 100 * 5 = 51,000`
- Broker Position market value sum: `979,800`
- Broker Position unrealized PnL sum: `928,800`

This explains why the Tachibana screen can show approximate consideration around `10,176` per order: the filled acquisition price evidence is around 102 yen for 100 shares. Runtime did not request this price; it is Broker Demo execution evidence.

## Current SoT / Public Report Audit

Current SoT after E25:

| Field | Value |
| --- | ---: |
| cash | 949,000 |
| buying_power | 949,000 |
| market_value | 979,800 |
| total_equity | 1,928,800 |
| source | `runtime_v2_runtime_owned_fill_projection` |

E25 projection formula:

```text
projected_cost_basis = sum(quantity * average_price)
                     = 5 * 100 * 102
                     = 51,000

projected_cash = runtime_evaluation_capital - projected_cost_basis
               = 1,000,000 - 51,000
               = 949,000

projected_market_value = 235,000 + 155,400 + 67,700 + 514,000 + 7,700
                       = 979,800

projected_total_equity = projected_cash + projected_market_value
                       = 949,000 + 979,800
                       = 1,928,800
```

Public Report reflects the same values:

- Cash: `JPY 949,000`
- Buying power: `JPY 949,000`
- Market value: `JPY 979,800`
- Total equity: `JPY 1,928,800`
- Positions: `6522`, `7878`, `6897`, `6327`, `4591`

Conclusion:

The E25 projection is mechanically consistent with Ledger Position evidence, but the valuation is not suitable as a trusted production-equivalent asset state because fill price and market price evidence are inconsistent for a real market context. In demo mode, it should be flagged as requiring price-source review before the next Planning cycle uses it for allocation.

## Root Cause Classification

| Area | Finding | Classification |
| --- | --- | --- |
| Runtime Submit parameters | MARKET order, `sOrderPrice=0`, `sOrderSuryou=100`; no 100/1000 price sent | PASS |
| Issue code normalization | 5-digit internal code normalized to 4-digit Broker code | PASS |
| Quantity calculation | `estimated_price=1000` fallback produced 100 shares | BUG / DESIGN GAP |
| Feature input | Candidate features lack executable price columns | BUG / DATA CONTRACT GAP |
| Broker execution | Demo filled all orders around 102 average price according to Position evidence | DEMO EVIDENCE |
| Ledger position | Preserves Broker Position average price and market value | PASS |
| Current projection | Formula is traceable but can create unrealistic total equity | REVIEW_REQUIRED FOR NEXT PLANNING |
| Public Report | Displays Current SoT correctly | PASS |
| Capital Allocation next run | Would likely see `total_equity=1,928,800` / exposure unless guarded | BLOCKER BEFORE NEXT SUBMIT |

## Required Follow-up

Before the next submit-enabled Morning/Open cycle:

1. Add a price-source contract for Morning Planning.
2. Treat missing executable price as `REVIEW_REQUIRED`, `BLOCKED`, or `NO_SIGNAL`; do not silently use `per_order_budget / 100`.
3. Record `price_source` and `price_confidence` in OrderPlan, Pending, Submit manifest, Ledger, and Report.
4. For MARKET orders, require a sizing reference price from J-Quants latest close, broker quote, or an explicitly approved fallback.
5. Prevent next Planning from using demo-derived `total_equity=1,928,800` as free capital without a valuation review.
6. Keep Broker Demo cash out of Runtime Current SoT, but distinguish Runtime-owned demo fills whose price evidence is demo-specific and not production-equivalent.

## Acceptance Review

| Acceptance Item | Result |
| --- | --- |
| Broker order parameters audited | PASS |
| `sIssueCode`, `sSizyouC`, `sBaibaiKubun`, `sCondition`, `sOrderPrice`, `sOrderSuryou`, `sGenkinShinyouKubun`, `sOrderExpireDay` reviewed | PASS |
| Request contains no 100 yen order price | PASS |
| `estimated_price=1000` did not enter Broker request as order price | PASS |
| Quantity 100 fixed reason identified | PASS |
| Missing price source identified | PASS |
| 100万円運用なのに約5万円しか約定していない理由 identified | PASS |
| Broker OrderList / Position fields compared | PASS |
| E25 total_equity formula identified | PASS |
| Suitability for Runtime asset valuation assessed | PASS |
| Next Planning risk assessed | PASS |
| No code change | PASS |
| No additional Submit | PASS |
| No Production order | PASS |
| No Notification actual send | PASS |
| No launchd change | PASS |

## Final Judgment

`PHASE14E26_PRICE_AND_SIZING_ROOT_CAUSE_IDENTIFIED`
