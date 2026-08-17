# Phase30-AF - 60BD Selection / Winner Quality / Capital Utilization / Regime Attribution Audit

Task ID: `Phase30-AF`

Target run:

```text
runtime-test-historical-extended-smoke-20260816T061732506648Z
```

Boundary:

```text
READ_ONLY
NO_STRATEGY_CHANGE
NO_RUNTIME_CHANGE
NO_CONFIG_OR_THRESHOLD_CHANGE
NO_TARGET_RUN_MUTATION
NO_HISTORICAL_OUTCOME_FIT
```

The user's observation was at 2022-11-04. During this audit the run continued
to progress. This report uses only `run_state.completed_business_days` available
at audit time, ending at 2022-11-16. Partial 2022-11-17 work was not included.

Evidence files:

```text
reports/phase_reports/phase30_af_60bd_selection_winner_capital_regime_attribution_audit.json
reports/phase_reports/phase30_af/daily_performance.json
reports/phase_reports/phase30_af/daily_opportunity_coverage.json
reports/phase_reports/phase30_af/campaign_ranking.json
reports/phase_reports/phase30_af/capital_utilization.json
reports/phase_reports/phase30_af/regime_attribution.json
reports/phase_reports/phase30_af/94320_deep_dive.json
```

## Primary Judgment

```text
KNOWN_RUNTIME_OR_AUTHORITY_DEFECT = NO
SELECTION_QUALITY = MIXED
SELECTION_COVERAGE = PARTIAL
WINNER_AMPLIFICATION = MIXED
CAPITAL_UTILIZATION = MIXED
PAYOFF_ASYMMETRY = MIXED
PHASE30_AE1_ADD_CONVERSION_REPAIRED_IN_REAL_RUN = YES
BEAR_CONVICTION_HYPOTHESIS = NOT_SUPPORTED
PHASE30_AF_STRATEGY_DIRECTION = MIXED
```

The current evidence does not show a confirmed Runtime or authority regression.
The weaker result is better explained as multi-causal Strategy behavior: partial
selection coverage, high cash caused mostly by risk caution and some unused
opportunity cash, a narrow winner pool, and payoff asymmetry that has not yet
turned favorable.

## Runtime / Authority Integrity

No confirmed production authority defect was found.

ADD conversion after Phase30-AE1 worked in the real run:

```text
PM_ADD = 56
PC_POSITIVE_ADD_TARGET = 5
PS_POSITIVE_ADD_QUANTITY = 5
RUNTIME_BUY_ADD = 5
BUY_ADD_FILLS_MATCHED_BY_DATE_SYMBOL = 5
BUY_ADD_NOTIONAL_MATCHED_BY_DATE_SYMBOL = 150,580 JPY
```

The five real ADD conversions were the 94320 additions on 2022-08-19,
2022-08-22, 2022-08-23, 2022-08-24, and 2022-09-01.

PC ADD campaign identity mismatches:

```text
pc_add_identity_mismatch_count = 0
```

An observability caveat remains: early 94320 execution fills carry an execution
campaign id that differs from the latest canonical position campaign id. This
did not block PM -> PC -> PS -> Runtime BUY_ADD conversion and is not classified
as a confirmed authority defect in this audit.

## 60BD Performance Structure

Completed audit window:

```text
completed_business_days = 66
first_completed_day = 2022-08-10
last_completed_day = 2022-11-16
run_status = RUNNING
next_job = 2022-11-17:market_refresh
```

Portfolio structure:

```text
final_equity = 972,820
final_return_from_1m = -2.718%
final_cash = 571,150
final_exposure = 41.2892%
final_positions = 5
peak_equity = 1,014,780 on 2022-09-09
trough_equity = 967,020 on 2022-11-14
max_drawdown = -4.7064%
longest_underwater_duration = 44BD
average_cash_ratio = 68.0262%
average_exposure = 31.9738%
average_positions = 4.288
```

Exposure quartiles:

```text
q0 = 13.2313%
q25 = 26.7369%
q50 = 29.0443%
q75 = 34.5990%
q100 = 64.7865%
```

Prior-day exposure vs next-day return was weakly negative:

```text
correlation = -0.146786
highest prior-exposure quartile avg next daily return = -0.240358%
```

This does not prove that exposure is bad. It does show that, in this sample,
raising exposure did not reliably improve the portfolio return path.

## Top Winners / Losers

Campaign PnL is a proxy derived from canonical campaign average price, campaign
quantity basis, and `current_campaign_relative_return`. Fill records are used
for ADD/reduce counts and quantity path, not as sole realized PnL authority.

Top winners:

| Symbol | PnL proxy | Status | BUY_NEW date | MFE | Giveback |
|---|---:|---|---|---:|---:|
| 27880 | 7,500 | CLOSED | 2022-08-29 | 40.40% | 15.15% |
| 78860 | 4,200 | OPEN | 2022-11-15 | 4.03% | 0.00% |
| 73590 | 4,050 | CLOSED | 2022-09-30 | 5.98% | 3.06% |
| 83060 | 3,460 | OPEN | 2022-10-18 | 5.49% | 3.30% |
| 66190 | 3,200 | CLOSED | 2022-10-19 | 2.03% | 0.00% |
| 36600 | 2,900 | CLOSED | 2022-08-25 | 14.42% | 8.85% |
| 47600 | 2,400 | CLOSED | 2022-09-07 | 9.71% | 8.01% |
| 78590 | 1,600 | CLOSED | 2022-08-15 | 7.97% | 1.59% |
| 36640 | 1,500 | CLOSED | 2022-08-12 | 4.00% | 0.00% |
| 23700 | 1,200 | CLOSED | 2022-08-10 | 4.17% | 1.39% |

Top losers:

| Symbol | PnL proxy | Status | BUY_NEW date | MFE | Giveback |
|---|---:|---|---|---:|---:|
| 92540 | -12,900 | CLOSED | 2022-10-14 | 3.69% | 10.79% |
| 67860 | -4,200 | CLOSED | 2022-09-06 | -17.65% | 0.00% |
| 60540 | -2,900 | CLOSED | 2022-08-24 | 0.33% | 9.84% |
| 33580 | -2,600 | CLOSED | 2022-10-14 | -5.60% | 11.73% |
| 60850 | -2,340 | CLOSED | 2022-09-16 | -6.18% | 3.86% |
| 48330 | -1,500 | CLOSED | 2022-10-20 | -10.00% | 0.00% |
| 65500 | -1,400 | CLOSED | 2022-10-06 | -2.42% | 4.35% |
| 23230 | -900 | CLOSED | 2022-08-16 | 2.11% | 4.37% |
| 21640 | -660 | CLOSED | 2022-09-13 | -0.76% | 2.58% |
| 60480 | -500 | CLOSED | 2022-10-27 | 0.96% | 3.37% |

Closed-campaign payoff:

```text
closed_campaign_count = 23
winner_count = 11
loser_count = 10
win_rate = 47.8261%
avg_winner = 2,370
avg_loser = -2,990
payoff_ratio = 0.792642
profit_factor = 0.871906
average_winner_duration = 10.545BD
average_loser_duration = 6.4BD
```

This is not yet the desired `small loss < winner gain` structure.

## 94320

94320 was the only clear amplified campaign:

| Date | Pre qty | ADD qty | Post qty | PM | Entry action | CQ | Risk | Return at evidence | Runtime |
|---|---:|---:|---:|---|---|---|---|---:|---|
| 2022-08-10 | 0 | 200 | 200 | n/a | BUY_NEW_REDUCED_ONLY | PASS | PASS | n/a | BUY_NEW |
| 2022-08-19 | 200 | 200 | 400 | ADD | ADD_REDUCED_ONLY | PASS | PASS | 0.2011% | BUY_ADD |
| 2022-08-22 | 400 | 300 | 700 | ADD | ADD_REDUCED_ONLY | PASS | PASS | 0.8381% | BUY_ADD |
| 2022-08-23 | 700 | 200 | 900 | ADD | ADD_REDUCED_ONLY | PASS | PASS | 1.1630% | BUY_ADD |
| 2022-08-24 | 900 | 200 | 1100 | ADD | ADD_REDUCED_ONLY | PASS | PASS | 0.9389% | BUY_ADD |
| 2022-09-01 | 1100 | 100 | 1200 | ADD | ADD_REDUCED_ONLY | PASS | PASS | 0.2417% | BUY_ADD |

```text
94320_AMPLIFICATION_QUALITY = MIXED
```

The ADD chain itself is healthy: canonical ADD evidence reached PC, PS, Runtime,
and fills. The quality judgment is mixed because the adds were PIT-supported but
mostly `ADD_REDUCED_ONLY`, the later campaign return compressed materially, and
the portfolio did not build a broader set of amplified winners.

## Selection Quality

Average daily opportunity structure:

```text
candidate_count = 50.5
cq_healthy = 50.5
risk_contained = 50.5
pc_positive = 10.955
ps_positive = 1.136
market_wide_healthy_proxy_count = 416.545
```

Selection is not empty, and the production path is not dropping every candidate.
However, the effective conversion from broad PIT healthy-continuation supply to
concrete PS-positive quantity remains narrow.

```text
SELECTION_QUALITY = MIXED
```

## Market-Wide Opportunity Coverage

The offline market-wide proxy used only existing PIT technical features:

```text
eligible allowed fresh rows
price_momentum_return_5d > 0
price_momentum_return_20d > 0
trend_close_over_ma_20d > 1.0
trend_ma_5_20_ratio > 1.0
momentum_5d_vs_20d_delta >= -0.02
```

This is an audit proxy, not a new Strategy rule. It was not fitted to future
outcomes.

Average market-wide healthy proxy count was about 416.5 rows per day, while
Strategy Intelligence consumed about 50.5 candidates per day and PS positive
quantity averaged only 1.136 rows per day.

```text
SELECTION_COVERAGE = PARTIAL
```

## Capital Utilization

Cash classification across the 66 completed days:

```text
RISK_CAUTION_CASH = 54 days
UNUSED_OPPORTUNITY_CASH = 12 days
```

The cash level is not automatically a defect. Most high-cash days were tied to
risk/entry caution. Still, the 12 unused-opportunity days show that the system
sometimes had PC-positive opportunity while conversion to deployable PS quantity
remained too narrow relative to the market-wide proxy.

```text
CAPITAL_UTILIZATION = MIXED
```

## ADD Conversion

```text
PHASE30_AE1_ADD_CONVERSION_REPAIRED_IN_REAL_RUN = YES
```

The AE1 repair is validated in this real run. Correct NO_ADD behavior also
remained present, including 94320 `REVERSAL_RISK_ENTRY / NO_ADD` on 2022-08-31
and overheated/decelerating NO_ADD days in September.

## BULL / BEAR / NEUTRAL Attribution

| Regime | Days | Avg exposure | Avg cash | BUY_NEW | ADD | Starts | Portfolio PnL | Payoff ratio |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BULL | 18 | 26.4552% | 73.5448% | 30 | 2 | 13 | -18,260 | 2.673529 |
| NEUTRAL | 36 | 35.1690% | 64.8310% | 33 | 3 | 11 | -7,480 | 1.356923 |
| BEAR | 12 | 30.6660% | 69.3340% | 7 | 0 | 4 | 4,560 | 0.484516 |

BEAR had positive portfolio PnL in this sample, but the campaign payoff ratio
was weaker and ADD count was zero. The evidence does not support increasing BEAR
conviction from this sample.

```text
BEAR_CONVICTION_HYPOTHESIS = NOT_SUPPORTED
```

## Root Cause Ranking

1. `SELECTION_COVERAGE_GAP` - MEDIUM
   The PIT market-wide healthy continuation proxy is broader than effective
   SI/PC/PS conversion.

2. `CAPITAL_UTILIZATION_GAP` - MEDIUM
   Most high cash is risk-caution cash, but 12 days classify as unused
   opportunity cash.

3. `PAYOFF_ASYMMETRY_GAP` - MEDIUM
   Average loser magnitude exceeds average winner magnitude.

4. `WINNER_AMPLIFICATION_GAP` - MEDIUM
   94320 was amplified correctly, but the winner pool remains narrow.

## Leakage

```text
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_AS_RUNTIME_INPUT = FALSE
HISTORICAL_OUTCOME_USED_FOR_PRODUCTION_PARAMETER_SELECTION = FALSE
TEST_RESULT_USED_AS_STRATEGY_INPUT = FALSE
```

## Implementation Authorization

```text
NO IMPLEMENTATION AUTHORIZED BY PHASE30-AF
```

## 100BD Run Decision

```text
CONTINUE_CURRENT_100BD_RUN
```

No confirmed Runtime or authority defect justifies stopping the user-operated
100BD run. Performance weakness should be analyzed after completion unless a
separate confirmed defect appears.

## Recommended Next Task

```text
Phase30-AG - Selection Coverage / Capital Utilization Design Audit
```

Recommended scope: design-only, no parameter fitting. Focus on why broad
market-wide PIT continuation supply is narrowed to low PS-positive deployment,
and whether capital utilization should distinguish risk-caution cash from
unused opportunity cash more explicitly.
