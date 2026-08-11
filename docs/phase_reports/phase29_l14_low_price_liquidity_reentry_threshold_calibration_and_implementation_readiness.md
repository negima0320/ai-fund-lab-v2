# Phase29-L14 - Low-Price Liquidity / REENTRY Threshold Calibration and Implementation Readiness

## 0. Task ID

Phase29-L14

## 1. Primary Judgment

```text
PHASE29_L14_LOW_PRICE_LIQUIDITY_REENTRY_CALIBRATION_COMPLETE_IMPLEMENTATION_NOT_READY_ADDITIONAL_CALIBRATION_REQUIRED
```

L14 confirms the L13 architecture direction, but does not approve immediate
implementation of numerical thresholds. The available evidence is sufficient
to define the required authorities and formulas, and sufficient to confirm that
93180 is not the only low-price Opportunity population. It is not sufficient to
activate concrete price, liquidity, allocation-cap, cooldown, or recovery-hurdle
thresholds without risking 93180-specific overfit or excessive cash creation.

## 2. Scope and Non-Mutation Statement

```text
Task type: READ_ONLY / CALIBRATION / IMPLEMENTATION READINESS
Production code changed: NO
Strategy code changed: NO
Config changed: NO
Existing schema changed: NO
Runtime state mutated: NO
Pending mutated: NO
Ledger mutated: NO
Accepted Generation mutated: NO
Historical executed: NO
Fresh-run executed: NO
Resume executed: NO
PnL used as Strategy input: NO
Backtest result used as Strategy input: NO
Future leakage introduced: NO
```

## 3. Source Review Summary

Mandatory sources reviewed:

```text
L13 design SoT:
docs/phase_reports/phase29_l13_low_price_reentry_allocation_guard_design.md

L12 root cause:
docs/phase_reports/phase29_l12_93180_universe_eligibility_low_price_opportunity_root_cause_audit.md

SELL quantity non-regression authority:
docs/phase_reports/phase29_l7_sell_quantity_contract_materialization_repair.md

Roadmap:
docs/01_requirements/phase_roadmap.md

Current implementation:
Opportunity eligibility, Buy Quality, Portfolio Construction, Position Sizing,
Portfolio Management cooldown/reentry config, Planning, Corporate Action
adjustment authority, J-Quants raw OHLCV authority.
```

Current architecture findings:

```text
Opportunity BUY eligibility: positive expected_edge and no no_buy_reason; no low-price/traded-value/reentry authority.
Buy Quality: liquidity/execution feasibility is soft, not a hard traded-value floor.
Portfolio Construction: owns target_weight / target_notional economic allocation.
Position Sizing: materializes PC target weight into lot/quantity; should not own low-price economic cap.
PM: has existing-position cooldown/reentry concepts, but zero-quantity BUY_NEW does not currently consume prior EXIT semantic state.
Corporate Action: unresolved adjustment remains separate fail-closed authority; low-price guard must not reuse Historical-only quarantine semantics.
```

## 4. Calibration Dataset

Read-only datasets used:

```text
.runtime/runtime_state/buy_ai/*/opportunity_rankings.json
.runtime/operations/jquants/raw/jquants/equities_bars_daily/data.parquet
.runtime/operations/jquants/historical_snapshots/listed_issues/snapshots/*/data.parquet
reports/runtime_tests/runs/runtime-test-historical-smoke-20260810T232622909184Z/daily/*/strategy/buy_quality_decisions.json
reports/runtime_tests/runs/runtime-test-historical-smoke-20260810T232622909184Z/daily/*/strategy/portfolio_construction.json
reports/runtime_tests/runs/runtime-test-historical-smoke-20260810T232622909184Z/daily/*/execution/fills.json
```

Opportunity calibration coverage:

```text
Opportunity rows: 19,150
Opportunity dates: 383
Opportunity date range: 2022-07-01 through 2026-07-17
Opportunity symbols: 763
Raw OHLCV authority: 2022-05-17 through 2026-08-07
Raw OHLCV symbols: 4,939
```

Buy Quality / Portfolio Construction execution-artifact coverage:

```text
Buy Quality rows: 2,700
Buy Quality dates: 2022-08-10 through 2022-10-28
Buy Quality symbols: 193
Portfolio Construction rows: 2,704
Portfolio Construction dates: 2022-08-10 through 2022-10-28
Portfolio Construction symbols: 193
```

This is enough for multi-year Opportunity/price/liquidity distribution, but not
enough for production-ready PC allocation-cap thresholds across regimes.

## 5. Low-Price Distribution

Price buckets are diagnostic buckets, not adopted thresholds.

All Opportunity rows:

| Bucket | Rows | Symbols | Dates | BUY-eligible rows | BUY-eligible symbols | Median rank | Median edge | P90 edge | Median daily Va | Median rolling Va 20 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| <10 | 677 | 9 | 355 | 197 | 4 | 6 | 0.014415 | 0.221388 | 35,874,864 | 33,796,550 |
| <20 | 317 | 10 | 229 | 59 | 4 | 20 | -0.321646 | 0.560308 | 124,622,700 | 121,292,700 |
| <50 | 818 | 23 | 383 | 311 | 10 | 14 | -0.160398 | 0.360754 | 822,752,200 | 901,585,900 |
| <100 | 762 | 50 | 270 | 108 | 13 | 21 | -0.203819 | 0.107707 | 110,032,900 | 88,757,475 |
| >=100 | 16,576 | 735 | 383 | 1,728 | 102 | 27 | -0.385542 | 0.022459 | 359,043,500 | 263,643,350 |

BUY-eligible only:

| Bucket | Rows | Symbols | Rank min/median/P90 | Edge median/P90 | Rolling Va20 P10/P50/P90 |
|---|---:|---:|---|---|---|
| <10 | 197 | 4 | 1 / 3 / 6 | 0.181980 / 0.429823 | 5,756,750 / 41,742,500 / 864,553,520 |
| <20 | 59 | 4 | 1 / 2 / 3 | 0.567204 / 0.656074 | 1,663,687,590 / 2,316,531,850 / 3,353,537,790 |
| <50 | 311 | 10 | 1 / 3 / 10 | 0.261156 / 0.441092 | 47,582,700 / 2,836,007,600 / 3,849,215,300 |
| <100 | 108 | 13 | 1 / 6.5 / 12 | 0.148511 / 0.728309 | 56,932,080 / 388,149,375 / 9,879,891,030 |
| >=100 | 1,728 | 102 | 1 / 4 / 13 | 0.172132 / 0.426681 | 51,533,500 / 12,199,503,525 / 149,391,713,210 |

Per-year coverage:

| Year | Rows | Dates | Symbols | BUY-eligible | Low-price rows <100 | Low-price symbols | Low-price BUY-eligible |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2022 | 6,200 | 124 | 332 | 536 | 719 | 29 | 92 |
| 2023 | 9,350 | 187 | 469 | 868 | 1,143 | 30 | 291 |
| 2024 | 500 | 10 | 83 | 59 | 83 | 11 | 19 |
| 2026 | 3,100 | 62 | 195 | 940 | 629 | 34 | 273 |

Market / sector distribution for low-price Opportunity rows:

```text
Markets:
スタンダード 1,867
グロース 551
プライム 156

Top sectors:
情報･通信業 481
不動産業 397
小売業 385
電気機器 373
サービス業 230
証券･商品先物取引業 203
医薬品 203
```

Interpretation:

```text
93180 is not the only low-price Opportunity population.
Low-price candidates span multiple years, markets, and sectors.
Hard price exclusion would affect a real Opportunity population, not one isolated symbol.
```

## 6. Liquidity / Traded-Value Calibration

PIT-safe liquidity authority can be built from J-Quants raw OHLCV:

```text
Va: daily traded value
Vo: volume
AdjVo: adjusted volume
C / AdjC: close / adjusted close
AdjFactor: adjustment factor
MktCap: available in acquisition raw evidence, not always in canonical raw columns
```

Candidate formulas evaluated conceptually and against distributions:

```text
1. target_notional / rolling_median_traded_value_20
2. estimated_liquidation_days = target_notional / (participation_rate * rolling_median_traded_value_20)
3. price_tier + traded_value capacity tier
4. price/tick sensitivity = minimum_tick / price
5. combined cap = min(price_tier_cap, liquidity_capacity_cap, tick_sensitivity_cap)
```

Diagnostic capacity ratios for BUY-eligible rows:

For target_notional / rolling_median_va_20:

```text
Target 200,000 JPY, P95 ratio:
<10: 0.0379
<20: 0.0322
<50: 0.0116
<100: 0.0075
>=100: 0.0160
```

Interpretation:

```text
Pure liquidity threshold is insufficient.
Many low-price BUY-eligible rows have high rolling traded value and would pass a simple traded-value filter.
93180 itself had Va around 53M to 63M JPY on audited BUY dates.
Liquidity authority is required, but must combine with price/tick sensitivity and allocation cap.
```

Liquidity threshold calibration:

```text
NOT_READY
```

The formula is ready. The numerical threshold is not ready because a pure
target_notional / Va threshold would not identify the structural low-price
allocation risk by itself.

## 7. Buy Quality and Portfolio Construction Calibration

Available 2022 run Buy Quality distribution by price bucket:

| Bucket | Rows | Symbols | Median quality score | FULL | REDUCED | REJECT |
|---|---:|---:|---:|---:|---:|---:|
| <10 | 66 | 3 | 0.0 | 4 | 5 | 57 |
| <20 | 61 | 3 | 0.0 | 0 | 0 | 61 |
| <50 | 91 | 3 | 0.0 | 1 | 3 | 87 |
| <100 | 97 | 9 | 0.0 | 1 | 4 | 92 |
| >=100 | 2,385 | 181 | 0.0 | 39 | 103 | 2,243 |

Available 2022 PC positive target-weight distribution:

| Bucket | Positive rows | Symbols | Median target weight | P90 target weight | Max target weight | BUY_NEW-like rows | ADD-like rows |
|---|---:|---:|---:|---:|---:|---:|---:|
| <10 | 15 | 1 | 0.180097 | 0.181563 | 0.183015 | 4 | 0 |
| <50 | 4 | 1 | 0.162446 | 0.165452 | 0.166667 | 1 | 0 |
| <100 | 9 | 1 | 0.110681 | 0.161824 | 0.170660 | 0 | 4 |
| >=100 | 145 | 10 | 0.152410 | 0.181644 | 0.272972 | 11 | 50 |

Interpretation:

```text
PC evidence confirms the structural issue: low-price positive targets can receive normal target weights.
But the available PC positive low-price sample is too narrow for activation thresholds.
Allocation cap calibration is NOT_READY.
```

## 8. Semantic REENTRY Calibration

Definition readiness:

```text
REENTRY = current_quantity == 0 AND prior same-symbol EXIT is known from past runtime state before current decision date
```

This semantic is ready as an authority definition because it uses past runtime
state, not PnL, future return, or backtest result.

Observed existing-run re-entry events from fills:

```text
23880: BUY after EXIT, 2 calendar days
93180: BUY after EXIT, 39 calendar days
93180: BUY after EXIT, 1 calendar day
93180: BUY after EXIT, 1 calendar day
```

Interpretation:

```text
REENTRY semantic: READY
Cooldown threshold: NOT_READY
Recovery hurdle threshold: NOT_READY
```

The existing sample confirms the semantic gap and short-cycle churn risk, but
does not provide enough non-PnL, multi-symbol evidence to activate cooldown days
or recovery threshold values.

## 9. Hybrid Cooldown + Recovery Hurdle

Time-only cooldown remains rejected.

Recommended future contract remains:

```text
minimum cooldown + recovery hurdle
```

Candidate recovery evidence:

```text
expected edge
opportunity rank
quality score/action
momentum recovery
trend_close_over_ma_20d
liquidity capacity
low-price risk evidence
Corporate Action resolved status
```

Calibration status:

```text
Cooldown calibration: NOT_READY
Recovery hurdle calibration: NOT_READY
```

Reason:

```text
A 10BD cooldown would block 1-day 93180 churn but not the 39-calendar-day 2022-10-21 re-entry.
A longer cooldown cannot be justified from the current non-PnL evidence without false-rejection analysis.
Recovery hurdle values need more re-entry candidate cases and non-reentry BUY_NEW controls.
```

## 10. Allocation Guard Candidate

The PC-owned allocation cap formula from L13 remains the recommended structure:

```text
low_price_adjusted_target_weight_cap =
  min(
    normal_strategy_single_name_cap,
    liquidity_capacity_cap,
    price_tier_cap,
    volatility_tick_sensitivity_cap,
    opportunity_confidence_adjusted_cap
  )
```

Implementation readiness:

```text
Formula: READY
Numerical caps: NOT_READY
```

Reasons:

```text
1. Price-only cap would overfit nominal price and corporate-action sensitivity.
2. Liquidity-only cap would not catch high-Va low-price names.
3. PC low-price positive target evidence is too narrow for cap values.
4. Capital reallocation impact needs a broader PC/lot-aware simulation before activation.
```

## 11. ADD Non-Regression

Canonical ADD must remain unchanged.

```text
ADD semantics weakened: NO
LOW PRICE => ADD BLOCK: forbidden
Strong ADD remains first capital reallocation destination: YES by design
```

L14 confirms current ADD has separate PC evidence:

```text
expected edge improvement
incremental investment value
opportunity cost
campaign continuation
no-loss averaging
concentration
capital availability
execution feasibility
```

Future low-price handling for existing positions may use only an incremental
risk multiplier after ADD passes. It must not blanket-block ADD.

## 12. SELL / REDUCE / EXIT Independence

SELL / REDUCE / EXIT independence is preserved by design and by L7 contract.

```text
SELL semantics changed: NO
REDUCE semantics changed: NO
EXIT semantics changed: NO
Low-price BUY guard blocks risk-reducing orders: NO
Corporate Action safety remains separate authority: YES
```

L7 repaired SELL quantity materialization so REDUCE/EXIT SELL quantities consume
the authoritative quantity contract. L14 does not alter that path.

## 13. Regression Plan for Future Implementation

Required L15/L16 regression plan:

```text
1. Normal-price BUY_NEW preserved
2. Strong momentum BUY preserved
3. Low-price but strong-liquidity BUY conditionally possible
4. Extreme-risk BUY symbol-level fail-closed
5. Semantic REENTRY identified
6. REENTRY recovery hurdle enforced
7. Canonical ADD preserved
8. Strong BUY_ADD preserved
9. SELL independent
10. REDUCE independent
11. EXIT independent
12. Opportunity Cost preserved
13. Capital reallocation preserved
14. Dynamic Capital preserved
15. Cash Exposure Authority preserved
16. Corporate Action fail-closed preserved
17. Production / Demo / Historical common Strategy
18. No Historical-only Strategy branch
19. No future leakage
20. No PnL / backtest-result Strategy input
```

## 14. Implementation Readiness Decision

```text
Implementation readiness: NOT_READY
```

Rationale:

```text
Multi-year Opportunity + OHLCV evidence is enough to reject blanket hard exclusion and pure liquidity-only policy.
It is not enough to activate numerical thresholds because BQ/PC/re-entry calibration evidence is limited.
Threshold activation now would risk either 93180-specific overfit or excessive cash creation.
```

Recommended next task:

```text
Phase29-L15 - Additional Calibration / Design Revision
```

Required L15 scope:

```text
1. Build read-only calibration artifact joining Opportunity, BQ-like quality, PC target simulation, raw OHLCV, listed snapshots, and past EXIT semantic state across 2022-2026.
2. Evaluate candidate thresholds without PnL/future returns.
3. Simulate capital reallocation order: strong ADD, higher-quality BUY_NEW, then cash.
4. Produce threshold candidates only if false exclusion and cash-creation risk are bounded.
5. Keep implementation blocked until thresholds are generalizable.
```

## 15. Mandatory Final Fields

```text
Primary Judgment:
PHASE29_L14_LOW_PRICE_LIQUIDITY_REENTRY_CALIBRATION_COMPLETE_IMPLEMENTATION_NOT_READY_ADDITIONAL_CALIBRATION_REQUIRED

Low-price threshold calibration:
NOT_READY

Liquidity threshold calibration:
NOT_READY

Allocation cap calibration:
NOT_READY

REENTRY semantic:
READY

Cooldown calibration:
NOT_READY

Recovery hurdle calibration:
NOT_READY

93180-specific optimization used:
NO

Multiple symbols used:
YES

Multiple periods used:
YES

PnL used as Strategy input:
NO

Backtest result used as Strategy input:
NO

Future leakage:
NO

ADD semantics weakened:
NO

BUY_NEW semantics implementation required:
YES

SELL semantics changed:
NO

REDUCE semantics changed:
NO

EXIT semantics changed:
NO

Opportunity Cost preserved:
YES

Capital reallocation preserved:
YES

Production fail-closed preserved:
YES

Historical-only Strategy introduced:
NO

Production code changed:
NO

Config changed:
NO

Existing schema changed:
NO

Runtime mutated:
NO

Pending mutated:
NO

Ledger mutated:
NO

Historical executed:
NO

Fresh-run required now:
NO

Implementation readiness:
NOT_READY

Recommended next task:
Phase29-L15 - Additional Calibration / Design Revision
```
