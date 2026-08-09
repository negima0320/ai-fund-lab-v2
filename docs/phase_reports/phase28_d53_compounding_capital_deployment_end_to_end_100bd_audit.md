# Phase28-D53: Compounding / Capital Deployment End-to-End 100BD Audit

## Primary Judgment

```text
PHASE28_D53_CAPITAL_BASE_CORRECT_DEPLOYMENT_CONVERSION_GAP_CONFIRMED
```

D53 was read-only. No production code, config, schema, threshold, strategy logic, PM logic, Portfolio Construction, Position Sizing, Runtime Planning, Submit Guard, Broker logic, fresh run, resume, long historical, or runtime-mutating command was executed.

## Run Validity

```text
run_id = runtime-test-historical-smoke-20260808T015847315534Z
period = 2023-04-03 through 2023-08-25
completed_business_days = 100
runtime_status = COMPLETED
final_runtime_judgment = PASS
operational_status = PASS
halt_status = NOT_HALTED
```

The top-level REVIEW_REQUIRED is the accepted non-blocking `strategy_shadow_review_required_non_blocking` condition and is not treated as runtime failure.

## Compounding

```text
classification = FULL_COMPOUNDING_CONFIRMED
current_total_equity used as active authority = YES_WITH_NEXT_DAY_VALUATION_LAG
active fixed 1,000,000 capital authority = NO
```

Current total equity rises above 1,000,000 and reaches 1,179,240.0. Position Sizing uses varying `portfolio_value`, not fixed initial capital. It normally uses the latest runtime current state available at planning time, which is previous-day post-valuation equity; same-day valuation becomes available for the next business day. Submit manifests retain `evaluation_capital=1000000` as metadata, but `buy_notional_policy=derived_from_capital_allocation_and_constraints`, `max_buy_order_amount=null`, and submitted BUY amounts are inherited from PS/runtime planning rather than recomputed from fixed capital.

## Exposure Gap

```text
average_actual_gross_exposure = 0.504346
average_target_gross_exposure = 0.7303
average_gap = 0.225954
gap_days_ge_10pp = 88
gap_days_ge_20pp = 56
gap_days_ge_30pp = 27
largest_gap_date = 2023-04-14
largest_gap = 0.493716
```

A positive gap is not itself a defect. The largest early gaps are mostly opportunity-shortage days: for example 2023-04-14 has 49 REJECT and 1 REDUCED_ALLOCATION_ONLY BUY Quality decisions, with no PC BUY_NEW positive target.

## Conversion Funnels

ADD funnel:

```text
PM ADD = 191
PC positive increment = 0
PS positive quantity delta = 0
Runtime BUY_ADD = 0
Pending BUY_ADD = 0
Submitted BUY_ADD = 0
Filled BUY_ADD = 0
```

All 191 ADD rows fail PC ADD eligibility with `ADD_CAMPAIGN_CONTINUATION_FAIL`, `ADD_EXPECTED_EDGE_UNKNOWN_FAIL_CLOSED`, and `ADD_INCREMENTAL_VALUE_UNKNOWN`. This is a BUY_ADD conversion gap before Position Sizing.

BUY_NEW funnel:

```text
PC BUY_NEW members = 153
PC positive BUY_NEW weights = 132
PS positive BUY_NEW quantities = 22
Runtime BUY_NEW = 22
Submitted BUY_NEW = 22
Filled BUY_NEW = 22
PS zero quantity = 131
lot/min-notional blocks = 110
```

BUY_NEW capital allocation reaches PC, but many PC-positive candidates do not become executable quantities because the target notional is below lot/minimum meaningful notional.

## Final Day

```text
business_date = 2023-08-25
current_total_equity = 1179240.0
cash = 586610.0
market_value = 592630.0
cash_ratio = 0.497448
actual_gross_exposure = 0.502552
target_gross_exposure = 0.72
deployable_cash = 256422.8
position_count = 5
available_new_opportunities = 1
available_add_opportunities = 0
```

Final-day cash is partly policy buffer and partly unused capacity. One PC-positive BUY_NEW opportunity exists, but PS does not convert it to quantity because of lot/min-notional constraints; available ADD opportunities are zero.

## DD / PF Observability

```text
maximum_drawdown = DERIVABLE_NOW (9.209%)
gross_profit_factor = DERIVABLE_NOW (1.951941)
net_profit_factor = NOT_VALIDLY_DERIVABLE
lot_level_realized_pnl = REQUIRES_NEW_RUNTIME_EVIDENCE
```

Daily equity exists in authoritative current valuation evidence. Gross slice PnL exists in `realized_slices.json`. Net PF is not valid because fees/tax/net realized PnL are unavailable.

## Next Phase

```text
Phase28-D54
DESIGN_ONLY repair design for BUY_ADD eligibility evidence availability and lot-size-aware capital conversion.
```

D53 does not approve threshold or exposure-policy optimization. Any performance claim after repair requires a fresh controlled run.
