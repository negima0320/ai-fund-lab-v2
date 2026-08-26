# Phase31-G70 — Current Long-Run Performance Characterization

## PRIMARY_JUDGMENT

PHASE31_G70_CURRENT_LONG_RUN_PERFORMANCE_CHARACTERIZED

The running long Historical run was audited READ-ONLY using completed business
dates only. No run operation, replay, resume, code change, config change,
threshold change, or parameter tuning was performed.

```text
RUN_ID = runtime-test-historical-extended-smoke-20260823T140946562431Z
RUN_STATUS_AT_SNAPSHOT = RUNNING
RUN_NEXT_JOB_AT_SNAPSHOT = 2023-06-30:market_refresh
COMPLETED_BUSINESS_DATES = 183
AUDIT_WINDOW = 2022-10-03 through 2023-06-29
COMPLETION_EVIDENCE = daily/<date>/day_completion/day_completion_evidence.json status PASS
INITIAL_EQUITY_BASIS = 1,000,000
```

## Required Output

```text
CURRENT_PERFORMANCE_QUALITY = STRONG_ABSOLUTE_RETURN_WITH_POST_PEAK_DRAWDOWN
TOTAL_RETURN = +66.44%
ANNUALIZED_RETURN = +99.12% calendar-day CAGR over completed duration
PROFIT_FACTOR = 1.763
MAX_DRAWDOWN = -16.27%
CURRENT_DRAWDOWN = -12.72%
WIN_RATE = 43.20% realized-slice / 46.51% campaign-derived
PAYOFF_RATIO = 2.005
EXPECTANCY = +1,682.93 yen per realized slice
AVERAGE_EXPOSURE = 70.49%
PEAK_RETURN = +90.69%
PROFIT_ENGINE_CONCENTRATION = top 10 positive campaigns = 49.76% of positive campaign profit
MEASUREMENT_INTEGRITY = PASS_WITH_LARGE_MOVE_REVIEW_TARGETS
MARKET_QUALITY_VERSION_OUTPERFORMS_OLD_REFERENCE_TO_DATE = YES
FUTURE_INFORMATION_USED = NO
HISTORICAL_OUTCOME_USED_FOR_PARAMETER_SELECTION = NO
FRESH_RUN_EXECUTED = NO
RESUME_EXECUTED = NO
REPLAY_EXECUTED = NO
CODE_OR_CONFIG_CHANGED = NO
```

## Return / Equity

```text
INITIAL_EQUITY = 1,000,000
CURRENT_EQUITY = 1,664,400
TOTAL_RETURN = +66.44%
PEAK_EQUITY = 1,906,910
PEAK_DATE = 2023-04-06
PEAK_RETURN = +90.69%
CURRENT_DRAWDOWN_FROM_ATH = -12.72%
```

Monthly return breakdown:

```text
2022-10  +6.22%
2022-11  +6.66%
2022-12  -0.17%
2023-01  +3.52%
2023-02  +3.34%
2023-03 +36.06%
2023-04  -1.25%
2023-05  +6.59%
2023-06  -3.95% through 2023-06-29
```

Old Strategy reference comparison:

```text
2023-03-23 old reference return = +29.57%
2023-03-23 current run return   = +46.77%

2023-06-20 old reference return = +16.35%
2023-06-20 current run return   = +68.25%
```

## Drawdown

```text
MAX_DRAWDOWN = -16.27%
MDD_PEAK_DATE = 2023-04-06
MDD_TROUGH_DATE = 2023-04-21
MDD_RECOVERY_DATE = NOT_RECOVERED_AS_OF_2023-06-29
UNDERWATER_DAYS = 144 completed business dates
```

Top drawdown episodes:

```text
PEAK        TROUGH      RECOVERY    DRAWDOWN   DURATION
2023-04-06  2023-04-21  -           -16.27%    57 BD active
2023-03-28  2023-03-29  2023-03-31   -5.75%     3 BD
2022-12-15  2022-12-20  2023-01-23   -5.25%    24 BD
2022-11-08  2022-11-14  2022-11-21   -4.98%     9 BD
2023-03-09  2023-03-14  2023-03-16   -4.59%     5 BD
```

The main weakness is therefore not lack of profit generation; it is retention
after the 2023-04-06 peak.

## Profit Factor / Trading

Realized slice evidence:

```text
REALIZED_SLICE_COUNT = 338
GROSS_PROFIT = 1,314,190
GROSS_LOSS = -745,360
REALIZED_PNL = +568,830
PROFIT_FACTOR = 1.763
WINNING_SLICES = 146
LOSING_SLICES = 166
WIN_RATE = 43.20%
AVERAGE_WINNER = +9,001
AVERAGE_LOSER = -4,490
MEDIAN_WINNER = +2,300
MEDIAN_LOSER = -1,200
LARGEST_WINNER = +213,200
LARGEST_LOSER = -47,750
PAYOFF_RATIO = 2.005
EXPECTANCY = +1,683
```

Latest open-campaign unrealized PnL, derived from latest canonical campaign
quantity / average price / valuation price:

```text
OPEN_CAMPAIGN_UNREALIZED_PNL = +96,400
OPEN_CAMPAIGN_COUNT = 5
REALIZED_PLUS_OPEN_UNREALIZED = +665,230
EQUITY_TOTAL_PNL = +664,400
RECONCILIATION_DIFFERENCE = -830
```

The realized-slice evidence shows a lower win rate but a strong payoff ratio.
This is a classic profit-engine shape: many small losses are offset by fewer,
larger winners.

## Campaign Contribution

Campaign-derived count:

```text
CAMPAIGNS_WITH_PNL = 301
WINNING_CAMPAIGNS = 140
LOSING_CAMPAIGNS = 142
CAMPAIGN_WIN_RATE = 46.51%
AVERAGE_HOLDING_DURATION = 7.79 BD
MEDIAN_HOLDING_DURATION = 5 BD
```

Top positive contributors:

```text
59350 +213,200
67310 +100,000
44440  +84,000
70720  +61,400
71160  +44,600
64240  +41,300
49370  +41,200
72140  +39,900
93410  +37,900
40520  +37,400
```

Top negative contributors:

```text
51890 -47,750
60220 -45,500
78780 -44,500
30410 -38,900
41660 -38,400
62310 -32,700
43880 -31,900
36670 -27,800
92410 -27,000
70460 -24,500
```

Short-hold distribution:

```text
2-5 BD   135
6-20 BD   92
>20 BD    15
```

No 1BD campaign appeared in the latest campaign snapshot. The high count in
2-5BD confirms that churn / short-hold loss remains an important diagnostic
axis, but G70 does not tune or redesign it.

## Capital / Exposure

```text
AVERAGE_EXPOSURE = 70.49%
MEDIAN_EXPOSURE = 74.20%
MAX_EXPOSURE = 98.42%
MIN_EXPOSURE = 12.17%
AVERAGE_CASH = 414,008
MEDIAN_CASH = 352,710
AVERAGE_POSITIONS = 9.34
MAX_POSITIONS = 17
TIME_AT_GT_80_EXPOSURE = 61 BD
TIME_AT_LT_30_EXPOSURE = 8 BD
```

The system is not stuck in Cash. It participates materially, with enough cash
variation to show pacing rather than full-time maximum deployment.

## BUY / ADD / SELL

Execution fills:

```text
TOTAL_FILLS = 649
BUY_FILLS = 311
SELL_FILLS = 338
SUBMITTED_ORDER_TOTAL = 649
```

Runtime planning intents:

```text
BUY_NEW = 601
BUY_ADD = 10
SELL_EXIT = 300
NO_ACTION = 1121
NO_ORDER = 3786
RUNTIME_BUY_OR_ADD_PLAN_COUNT = 611
```

NO_ORDER reason distribution:

```text
zero_quantity_delta                         3,515
REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT      229
REDUCE_UNEXECUTABLE_DUE_TO_MINIMUM_NOTIONAL   42
```

ADD exists but is still small relative to BUY_NEW. That makes ADD contribution
and add-after-winner behavior a high-value follow-up, not a G70 repair target.

## Regime / Market Quality

Canonical Market Context regime counts:

```text
BULL        87
RANGE       31
RECOVERY    31
BEAR        28
CORRECTION   6
```

Regime characterization by daily return:

```text
REGIME      DATES AVG_DAILY_RETURN MEDIAN_DAILY_RETURN
RANGE          31          +1.036%             +0.709%
RECOVERY       31          +0.306%             +0.228%
BEAR           28          +0.171%             -0.015%
BULL           87          +0.136%             +0.282%
CORRECTION      6          -0.678%             -0.854%
```

Market Quality state counts:

```text
CONFLICTED_MARKET_STRUCTURE                65
SHORT_TERM_BREADTH_BREAKDOWN               39
HEALTHY_EXPANSION                          38
RECOVERY_CONFIRMATION_INCOMPLETE           30
SHORT_TERM_NARROWING_WITH_MEDIUM_STRENGTH  10
HEALTHY_RECOVERY                            1
```

Risk Pacing counts:

```text
CAUTIOUS_DEPLOYMENT    114
NORMAL_DEPLOYMENT       39
GRADUAL_REDEPLOYMENT    30
```

Pacing / participation evidence:

```text
MARKET_QUALITY_TRANSITIONS = 71
RISK_PACING_TRANSITIONS = 47
VALID_OPPORTUNITY_DATES = 183
ZERO_SECURITY_ALLOCATION_DATES = 9
CASH_AND_SECURITIES_COEXISTENCE_DATES = 174
ADD_PARTICIPATION_DATES = 9
STRONG_STOCK_WEAK_MARKET_PARTICIPATION = 41
MARKET_QUALITY_HARD_GATE_COUNT = 0
CANDIDATE_AUTHORITY_MUTATION_COUNT = 0
RUNTIME_PRIORITY_REDECISION_COUNT = 0
```

This supports the G69 conclusion: Market Quality is acting as capital pacing
context, not as security admission authority.

## Measurement Integrity

Checks performed:

```text
EQUITY_RECONCILIATION_BAD_DATES = 0
VALUATION_NOT_READY_DATES = 0
CURRENT_VALUATION_APPLY_POSTCONDITION = PASS on inspected large-move dates
CORPORATE_EVENT_COUNT_ON_2023-03-29 = 0
CORPORATE_EVENT_COUNT_ON_2023-04-06 = 0
CORPORATE_EVENT_COUNT_ON_2023-04-07 = 0
```

Largest absolute daily moves:

```text
2023-04-06 +169,950  +9.78%
2023-03-30  +85,420  +5.78%
2023-03-29  -90,180  -5.75%
2023-03-31  +83,210  +5.32%
2023-04-17  +79,650  +4.95%
2023-04-12  -86,160  -4.91%
2023-04-07  -90,800  -4.76%
2023-04-03  +72,180  +4.38%
2023-04-11  -79,940  -4.36%
2023-03-16  +52,340  +4.21%
```

2023-03-29 through 2023-04-07 bridge:

```text
DATE        EQUITY    DAILY_PNL RETURN%  CASH     MARKET_VALUE POS
2023-03-29 1,477,680  -90,180   -5.75   334,160  1,143,520     8
2023-03-30 1,563,100  +85,420   +5.78   425,110  1,137,990     6
2023-03-31 1,646,310  +83,210   +5.32   361,810  1,284,500     8
2023-04-03 1,718,490  +72,180   +4.38   403,410  1,315,080     7
2023-04-04 1,770,490  +52,000   +3.03   159,410  1,611,080     7
2023-04-05 1,736,960  -33,530   -1.89   480,410  1,256,550     5
2023-04-06 1,906,910 +169,950   +9.78   838,610  1,068,300     3
2023-04-07 1,816,110  -90,800   -4.76 1,147,620    668,490     4
```

These moves are internally reconciled at the equity/cash/market-value level.
They should not be treated as measurement-invalid in G70, but the 2023-03-29
through 2023-04-07 cluster remains a priority follow-up for causal
decomposition because it drives both the peak and the subsequent drawdown
profile.

## Strengths

- Absolute return is strong: +66.44% through 2023-06-29, with +99.12% annualized
  calendar-day CAGR over the completed window.
- Profit factor is positive at 1.763 despite a sub-50% win rate, showing that
  payoff asymmetry is working.
- The system materially outperforms the old reference points to date:
  +46.77% vs +29.57% on 2023-03-23 and +68.25% vs +16.35% on 2023-06-20.
- Market Quality / Risk Pacing are not suppressing the Profit Engine: zero
  security allocation is sparse, Cash + securities coexist on 174 dates, and
  strong-stock / weak-market participation is present.
- Exposure is active but not binary: average exposure 70.49%, max 98.42%,
  min 12.17%.

## Weaknesses

- Profit retention is weak after the 2023-04-06 ATH: the run remains -12.72%
  below peak as of 2023-06-29.
- Maximum drawdown is meaningful at -16.27% and has not recovered by the
  snapshot date.
- Loss frequency is high: realized-slice win rate is 43.20%, with 166 losing
  slices against 146 winning slices.
- Short-hold churn is material: 135 campaigns closed in 2-5 business days.
- ADD participation is low relative to BUY_NEW: 10 BUY_ADD runtime plans against
  601 BUY_NEW plans.
- The 2023-03-29 through 2023-04-07 region contains very large daily equity
  moves and should be decomposed before treating peak-to-trough behavior as
  fully explained by ordinary market exposure.

## Highest-Value Investigation Targets

1. Post-peak profit retention after 2023-04-06.
   Evidence: ATH 1,906,910, current drawdown -12.72%, active MDD -16.27%.

2. 2023-03-29 through 2023-04-07 large-move bridge.
   Evidence: multiple +/-5% to +9.78% daily moves, internally reconciled but
   dominant in the equity curve.

3. Short-hold churn and loser frequency.
   Evidence: 166 losing realized slices, 135 campaigns in the 2-5BD holding
   bucket, median loser -1,200.

4. ADD / winner amplification contribution.
   Evidence: only 10 BUY_ADD runtime plans and 9 ADD participation dates in a
   run where top winners drive almost half of positive campaign profit.

5. Correction-regime behavior.
   Evidence: CORRECTION has 6 dates with average daily return -0.678% and
   median -0.854%, while other regimes remain positive or mixed.

No fix, parameter change, or optimization recommendation is made in G70.
