# Phase29-L15 - Cross-Period Low-Price / Liquidity / REENTRY / Allocation Calibration

## 0. Task ID

Phase29-L15

## 1. Primary Judgment

```text
PHASE29_L15_CROSS_PERIOD_LOW_PRICE_LIQUIDITY_REENTRY_ALLOCATION_CALIBRATION_READY_FOR_L16_WITH_CANDIDATE_RANGES_AND_OPERATOR_ACCEPTANCE_REQUIRED
```

L15 expands L14 from a readiness audit into a cross-period calibration artifact.
It supports L16 implementation of Production-common low-price / liquidity /
REENTRY evidence and allocation guard logic with candidate ranges. It does not
approve a hard low-price exclusion, a Historical-only strategy, or any
93180-specific rule.

## 2. Scope and Non-Mutation Statement

```text
Task type: READ_ONLY / CALIBRATION / DESIGN REVISION / IMPLEMENTATION READINESS
Production code changed: NO
Strategy code changed: NO
Runtime code changed: NO
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
Future leakage: NO
```

Generated read-only calibration outputs:

```text
reports/phase29_l15_cross_period_low_price_liquidity_reentry_allocation_calibration/calibration_summary.json
reports/phase29_l15_cross_period_low_price_liquidity_reentry_allocation_calibration/bucket_summary.csv
reports/phase29_l15_cross_period_low_price_liquidity_reentry_allocation_calibration/allocation_cap_simulated_diagnostics.csv
reports/phase29_l15_cross_period_low_price_liquidity_reentry_allocation_calibration/reentry_cases.csv
```

## 3. Calibration Coverage

Opportunity / OHLCV coverage:

```text
Opportunity rows: 19,150
Opportunity dates: 383
Opportunity date range: 2022-07-01 through 2026-07-17
Opportunity symbols: 763
Raw OHLCV authority: 2022-05-17 through 2026-08-07
```

Real artifact coverage:

```text
BQ real-artifact rows: 2,700
BQ real-artifact dates: 54
BQ real-artifact symbols: 193
PC real-artifact rows: 2,704
PC real-artifact dates: 54
PC real-artifact symbols: 193
REENTRY cases from existing fills: 4
REENTRY symbols: 2
```

Evidence classification:

```text
Opportunity rankings: REAL ARTIFACT
Raw OHLCV: REAL ARTIFACT / PIT authority
Listed issue metadata: REAL ARTIFACT / PIT snapshot lookup
BQ distribution: REAL ARTIFACT where available
PC target weights: REAL ARTIFACT where available
Broad allocation cap effects: SIMULATED CALIBRATION OUTPUT
REENTRY: REAL ARTIFACT from past fills in available run
```

## 4. Price / Tick Distribution

Diagnostic buckets are not adopted price thresholds.

| Bucket | Rows | Symbols | BUY-eligible rows | BUY-eligible symbols | BUY-eligible median rank | BUY-eligible median rolling Va20 | Single-tick pct median |
|---|---:|---:|---:|---:|---:|---:|---:|
| <10 | 677 | 9 | 197 | 4 | 3 | 41,742,500 | 20.00% |
| 10-20 | 317 | 10 | 59 | 4 | 2 | 2,316,531,850 | 10.00% |
| 20-50 | 818 | 23 | 311 | 10 | 3 | 2,836,007,600 | 3.70% |
| 50-100 | 762 | 50 | 108 | 13 | 6.5 | 388,149,375 | 1.35% |
| 100-300 | 2,726 | 170 | 465 | 32 | 4 | 1,273,019,300 | 0.52% |
| 300-1000 | 5,009 | 327 | 198 | 24 | 6 | 23,735,008,572.5 | 0.18% |
| >=1000 | 8,841 | 418 | 1,065 | 59 | 4 | 15,643,522,025 | 0.05% |

Price authority decision:

```text
Price itself should be SECONDARY RISK SIGNAL.
```

Reason:

```text
Nominal price is useful because single-tick percentage sensitivity rises sharply below 100 JPY.
But nominal price alone would over-exclude multi-year, multi-sector Opportunity population.
```

Candidate risk tiers for L16:

```text
watch: single_tick_pct >= 1.0%    approximately price <= 100 JPY
elevated: single_tick_pct >= 2.0% approximately price <= 50 JPY
severe: single_tick_pct >= 5.0%   approximately price <= 20 JPY
extreme: single_tick_pct >= 10.0% approximately price <= 10 JPY
```

These are candidate ranges, not final investment bans.

## 5. Liquidity / Execution Capacity

Liquidity capacity authority:

```text
READY_WITH_CANDIDATE_RANGE
```

Recommended formula:

```text
capacity_ratio = target_notional / rolling_median_traded_value_20
estimated_liquidation_days = target_notional / (participation_rate * rolling_median_traded_value_20)
```

Participation rates are calibration assumptions, not Strategy truth:

```text
5%, 10%, 20% participation can be evaluated in L16 tests.
```

Observed diagnostic:

```text
BUY-eligible low-price rows often have substantial liquidity.
For price <100, 363 of 675 simulated affected BUY-eligible rows had rolling Va20 >= 1B JPY.
Pure liquidity filter would not solve the issue.
```

Candidate capacity range:

```text
normal: capacity_ratio <= 0.5%
watch: 0.5% < capacity_ratio <= 1.0%
review/cap: 1.0% < capacity_ratio <= 3.0%
severe cap/review: capacity_ratio > 3.0%
```

Do not use liquidity alone. Combine with price/tick risk, volatility, and PC
allocation cap.

## 6. Allocation Cap Calibration

Allocation cap formula:

```text
READY
```

Recommended PC-owned formula:

```text
low_price_adjusted_target_weight_cap =
  min(
    normal_strategy_single_name_cap,
    liquidity_capacity_cap,
    price_tick_risk_cap,
    volatility_cap,
    opportunity_confidence_adjusted_cap
  )
```

Candidate allocation cap range:

```text
READY_WITH_CANDIDATE_RANGE
```

Candidate PC cap weights for L16:

```text
watch tier: 0.10 to 0.12
elevated tier: 0.08 to 0.10
severe tier: 0.05 to 0.08
extreme tier: 0.03 to 0.05
```

Simulated structural effect using BUY-eligible price <100 opportunity rows and
normal 0.18 target weight / 1,000,000 JPY equity assumption:

| Simulated cap | Affected rows | Affected symbols | Affected dates | Release per row vs 0.18 | High-rank <=5 affected | High-edge >=0.2 affected | High-liquidity Va20 >=1B affected |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.03 | 675 | 23 | 295 | 150,000 JPY | 485 | 376 | 363 |
| 0.05 | 675 | 23 | 295 | 130,000 JPY | 485 | 376 | 363 |
| 0.08 | 675 | 23 | 295 | 100,000 JPY | 485 | 376 | 363 |
| 0.10 | 675 | 23 | 295 | 80,000 JPY | 485 | 376 | 363 |
| 0.12 | 675 | 23 | 295 | 60,000 JPY | 485 | 376 | 363 |

Interpretation:

```text
Caps must reduce notional rather than exclude all low-price opportunities.
Because many affected rows are high-rank/high-edge/high-liquidity, hard exclusion would create high false-exclusion risk.
```

## 7. Real BQ / PC Evidence

Real BQ artifact coverage confirms that low-price rows can pass:

```text
<10 bucket: 66 BQ rows, 4 FULL_ALLOCATION_ELIGIBLE, 5 REDUCED_ALLOCATION_ONLY
20-50 bucket: 91 BQ rows, 1 FULL_ALLOCATION_ELIGIBLE, 3 REDUCED_ALLOCATION_ONLY
50-100 bucket: 97 BQ rows, 1 FULL_ALLOCATION_ELIGIBLE, 4 REDUCED_ALLOCATION_ONLY
```

Real PC artifact coverage confirms ordinary target weights:

```text
<10 positive PC target rows: 15, median target_weight 0.180097, P95 0.182099
20-50 positive PC target rows: 4, median target_weight 0.162446, P95 0.166060
50-100 positive PC target rows: 9, median target_weight 0.110681, P95 0.166242
```

PC remains the correct owner of economic allocation caps. Position Sizing must
remain a target materializer, not the low-price economic authority.

## 8. Capital Reallocation Contract

Capital reallocation ordering:

```text
READY
```

Required L16 order:

```text
1. Strong canonical ADD opportunities
2. Higher-quality uncapped BUY_NEW opportunities
3. Other eligible Strategy opportunities
4. Cash
```

Cash remains valid when no sufficiently eligible alternative exists. The cap
must not force deployment merely to reduce cash. It also must not strand capital
when contemporaneous strong ADD or higher-quality BUY_NEW opportunities exist.

Opportunity Cost, Dynamic Capital, and Cash Exposure Authority are preserved.

## 9. Semantic REENTRY and Cooldown

REENTRY semantic:

```text
READY
```

Definition:

```text
current_quantity == 0
AND prior same-symbol EXIT is known from past runtime state before current decision date
```

Observed cases in available fills:

| Symbol | Prior EXIT | Candidate date | Calendar days | Price |
|---|---|---|---:|---:|
| 23880 | 2022-08-30 | 2022-09-01 | 2 | 136 |
| 93180 | 2022-09-12 | 2022-10-21 | 39 | 5 |
| 93180 | 2022-10-24 | 2022-10-25 | 1 | 5 |
| 93180 | 2022-10-27 | 2022-10-28 | 1 | 4 |

Minimum cooldown:

```text
READY_WITH_CANDIDATE_RANGE
```

Candidate range:

```text
1BD to 5BD for immediate churn suppression.
10BD and 20BD remain diagnostic only and require operator approval because they can suppress broader momentum re-entry.
```

Recovery hurdle formula:

```text
READY_WITH_CANDIDATE_RANGE
```

Candidate hurdle components:

```text
Corporate Action status must be resolved.
Opportunity rank must be high, candidate range rank <= 5 to <= 10.
Expected edge must be positive and preferably above low-price bucket median, candidate range 0.10 to 0.20.
Buy Quality must be REDUCED_ALLOCATION_ONLY or FULL_ALLOCATION_ELIGIBLE.
Momentum/trend must be recovered, candidate range trend_close_over_ma_20d >= 1.0 or price_momentum_return_20d >= 0.
Liquidity capacity must not be severe.
Price/tick tier controls allocation cap even when recovery passes.
```

Time-only cooldown remains rejected. Recovery hurdle is required because a 1BD
to 5BD cooldown catches immediate churn but not the 39-day 93180 re-entry.

## 10. False-Exclusion and Cash-Creation Risk

False-exclusion risk is material:

```text
BUY-eligible price <100 rows: 675
Affected symbols: 23
Affected dates: 295
High-rank <=5 affected: 485
High-edge >=0.2 affected: 376
High-liquidity Va20 >=1B affected: 363
```

Therefore:

```text
Price-only hard exclusion recommended: NO
Pure liquidity filter sufficient: NO
Allocation cap preferred over exclusion: YES
```

Cash-creation risk:

```text
Any cap can release 60,000 to 150,000 JPY per low-price candidate under the 1M/0.18 simulation.
Released capital must remain in PC incremental allocation authority and recycle to ADD / better BUY_NEW before cash.
```

## 11. ADD / BUY_ADD Non-Regression

```text
ADD semantics weakened: NO
BUY_ADD preserved: YES
LOW_PRICE => ADD BLOCK: forbidden
```

Future low-price treatment of an existing position may only apply an incremental
risk multiplier after canonical ADD passes. It must preserve:

```text
expected edge improvement
incremental investment value
opportunity cost
campaign continuation
no-loss averaging
capital availability
execution feasibility
```

## 12. SELL / REDUCE / EXIT Non-Regression

```text
SELL semantics changed: NO
REDUCE semantics changed: NO
EXIT semantics changed: NO
L7 quantity contract preserved: YES
```

Low-price / liquidity / REENTRY logic is BUY-side risk allocation logic. It
must not block risk-reducing orders. L7 SELL quantity materialization remains
the authority for REDUCE/EXIT SELL quantities.

## 13. Corporate Action Separation

```text
Corporate Action authority preserved: YES
Production fail-closed preserved: YES
Historical-only Strategy introduced: NO
```

L16 must not infer split/reverse split from low nominal price or discontinuity.
Price/tick calculations must use PIT raw/adjusted OHLCV and existing Corporate
Action authority. Historical-only quarantine from L9-L11 must not become a
Strategy eligibility mechanism.

## 14. Implementation Readiness Gate

| Authority | Status |
|---|---|
| Price/tick risk authority | READY_WITH_CANDIDATE_RANGE |
| Liquidity capacity authority | READY_WITH_CANDIDATE_RANGE |
| Allocation-cap formula | READY |
| Allocation-cap numerical threshold/range | READY_WITH_CANDIDATE_RANGE |
| REENTRY semantic | READY |
| Minimum cooldown | READY_WITH_CANDIDATE_RANGE |
| Recovery hurdle formula | READY_WITH_CANDIDATE_RANGE |
| Recovery hurdle threshold/range | READY_WITH_CANDIDATE_RANGE |
| Capital reallocation ordering | READY |
| ADD non-regression contract | READY |
| SELL independence contract | READY |
| Corporate Action separation | READY |

Implementation readiness:

```text
READY_FOR_L16_WITH_CANDIDATE_RANGES_AND_OPERATOR_ACCEPTANCE_REQUIRED
```

L16 should implement the common Strategy authority and tests using candidate
ranges as explicit configuration/evidence. Final production acceptance still
requires focused regression and operator review. No threshold should be hidden
or 93180-specific.

## 15. Future L16 Regression Matrix

```text
1. Normal-price BUY_NEW preserved
2. Strong momentum BUY_NEW preserved
3. Low-price + strong-liquidity BUY remains conditionally possible
4. Structurally excessive low-price allocation capped
5. Semantic REENTRY detected
6. Non-REENTRY BUY_NEW not mislabeled
7. Cooldown enforced only if approved
8. Recovery hurdle enforced only for REENTRY
9. Strong canonical ADD preserved
10. BUY_ADD preserved
11. SELL independent
12. REDUCE independent
13. EXIT independent
14. L7 quantity contract preserved
15. Opportunity Cost preserved
16. Capital reallocation preserved
17. Dynamic Capital preserved
18. Cash Exposure Authority preserved
19. Corporate Action fail-closed preserved
20. Production/Demo/Historical common Strategy preserved
21. No Historical-only Strategy branch
22. No future leakage
23. No PnL/backtest-result Strategy input
24. No 93180-specific logic
```

## 16. Mandatory Final Fields

```text
Primary Judgment:
PHASE29_L15_CROSS_PERIOD_LOW_PRICE_LIQUIDITY_REENTRY_ALLOCATION_CALIBRATION_READY_FOR_L16_WITH_CANDIDATE_RANGES_AND_OPERATOR_ACCEPTANCE_REQUIRED

Calibration coverage:
Cross-period Opportunity + OHLCV + listed snapshots, plus available real BQ/PC/fill artifacts.

Opportunity dates:
383

Opportunity symbols:
763

BQ real-artifact coverage:
2,700 rows / 54 dates / 193 symbols

PC real-artifact coverage:
2,704 rows / 54 dates / 193 symbols

REENTRY cases identified:
4

REENTRY symbols identified:
2

Price-only hard exclusion recommended:
NO

Price/tick risk authority:
READY_WITH_CANDIDATE_RANGE

Liquidity capacity authority:
READY_WITH_CANDIDATE_RANGE

Pure liquidity filter sufficient:
NO

Allocation-cap formula:
READY

Allocation-cap threshold/range:
READY_WITH_CANDIDATE_RANGE; watch 0.10-0.12, elevated 0.08-0.10, severe 0.05-0.08, extreme 0.03-0.05

Capital reallocation ordering:
READY; strong ADD, higher-quality uncapped BUY_NEW, other eligible Strategy opportunities, then Cash

REENTRY semantic:
READY

Minimum cooldown:
READY_WITH_CANDIDATE_RANGE; 1BD-5BD candidate for immediate churn, 10BD/20BD diagnostic only

Recovery hurdle formula:
READY_WITH_CANDIDATE_RANGE

Recovery hurdle threshold/range:
READY_WITH_CANDIDATE_RANGE; rank <=5..10, edge 0.10..0.20, BQ REDUCED/FULL, trend/momentum recovered, CA resolved, capacity non-severe

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

BUY_ADD preserved:
YES

BUY_NEW change required:
YES

SELL semantics changed:
NO

REDUCE semantics changed:
NO

EXIT semantics changed:
NO

L7 quantity contract preserved:
YES

Opportunity Cost preserved:
YES

Dynamic Capital preserved:
YES

Cash Exposure Authority preserved:
YES

Capital reallocation preserved:
YES

Corporate Action authority preserved:
YES

Production fail-closed preserved:
YES

Historical-only Strategy introduced:
NO

Production code changed:
NO

Strategy code changed:
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

Fresh-run executed:
NO

Resume executed:
NO

Implementation readiness:
READY_FOR_L16_WITH_CANDIDATE_RANGES_AND_OPERATOR_ACCEPTANCE_REQUIRED

Recommended next task:
Phase29-L16 - Low-Price Risk Allocation / Semantic REENTRY Guard Implementation
```
