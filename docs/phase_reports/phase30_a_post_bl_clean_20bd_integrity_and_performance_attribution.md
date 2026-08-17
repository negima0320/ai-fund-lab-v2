# Phase30-A Post-BL Clean 20BD Integrity and Performance Attribution

## Primary Judgment

`PHASE30_A_CLEAN_20BD_MEASUREMENT_INTEGRITY_CONFIRMED_VALID_FOR_PHASE30_PERFORMANCE_ATTRIBUTION_WITH_ATTRIBUTION_LIMITATIONS`

Task ID: `Phase30-A`

Target run:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260815T030154161245Z
```

Period: `2022-08-10` through `2022-09-07`, 20 business days.

This was a read-only audit. No Strategy, Runtime, threshold, config, schema,
model, Accepted Generation, Safety, valuation, basis, BUY_WAIT, REENTRY, ADD,
SELL, REDUCE, or EXIT behavior was changed. No fresh Historical, resume,
replay, recovery, or long Historical run was executed.

## Gate A - Measurement Integrity

Gate A result:

```text
PASS
```

Clean evidence authority:

```text
VALID_FOR_PHASE30_PERFORMANCE_ATTRIBUTION
```

Evidence:

- `final_summary.json` reports `accounting_state_judgment = PASS`,
  `runtime_execution_judgment = PASS`, `trading_state_judgment = PASS`,
  and `pnl_reconciliation.status = PASS`.
- Independent daily reconciliation confirmed `Equity = Cash + sum(position
  market_value)` for all 20 days with zero reconciliation difference.
- All valued positions across all 20 daily `current_valuation_refresh`
  manifests had `valuation_price_authority = PASS`.
- All valued positions with basis metadata had
  `valuation_price_basis == quantity_basis`; no raw-price x adjusted-quantity
  or inverse mismatch was found.
- No suspicious day-to-day held-position price jump resembling the prior
  x2/x2.5/x5/x10 or inverse contamination pattern was found.
- `historical_evaluation_authority.status = PASS`; it fixes the run-start
  Accepted Generation authority and reports no latest fallback use. Its
  training overlap status means this run is not strict OOS AI performance, but
  it does not contaminate run-scoped runtime/PnL measurement.

Attribution limitation:

- `final_summary.json` reports `buy_fill_lineage_validation` as
  `REVIEW_REQUIRED_PRE_REPAIR_ARTIFACT` with 39 BUY fills missing one or more
  of `pending_item_id`, `order_plan_item_id`, or `quality_decision_id`.
  Execution, cash, Current, valuation, and PnL still reconcile. The limitation
  affects deep Candidate -> Buy Quality -> Pending lineage for some BUY fills,
  not the portfolio accounting.

## Final REVIEW_REQUIRED

Direct cause:

```text
strategy_shadow_review_required_non_blocking
```

Responsible component:

```text
runtime test close authority classification
```

Causal chain:

```text
strategy_shadow_judgment = REVIEW_REQUIRED
strategy_shadow_review_required = true
strategy_review_status = REVIEW_REQUIRED
strategy_shadow_close_classification =
  NON_MUTATING_STRATEGY_SHADOW_REVIEW_NON_BLOCKING
close_authority_judgment = REVIEW_REQUIRED
final_judgment = REVIEW_REQUIRED
```

The review dates were:

```text
2022-08-12, 2022-08-15, 2022-08-16, 2022-08-19, 2022-08-22,
2022-08-23, 2022-08-24, 2022-08-25, 2022-08-29, 2022-09-01,
2022-09-07
```

Classification:

```text
expected review behavior / benign close-finalization issue
```

It did not invalidate the completed 20BD performance:

- `block_rule = NO_BLOCKING_CLOSE_RULE_TRIGGERED`
- `blocking_reasons = []`
- `final_runtime_judgment = PASS`
- `operational_status = PASS`
- `runtime_execution_judgment = PASS`
- `trading_state_judgment = PASS`

The REVIEW_REQUIRED condition did not cause a halt, order suppression,
phantom fill, Current mutation error, Ledger error, cash error, equity error,
PnL error, or Strategy decision contamination. It is a non-mutating review
signal surfaced at close.

## 20BD Performance

| Metric | Value |
| --- | ---: |
| Initial Equity | 1,000,000 JPY |
| Final Equity | 972,510 JPY |
| Total PnL | -27,490 JPY |
| Total Return | -2.749% |
| Daily Volatility | 1.316% |
| Max Drawdown | -5.745% |
| MDD Start / Trough | 2022-08-12 / 2022-08-24 |
| Average Cash | 683,009 JPY |
| Final Cash | 431,770 JPY |
| Average Cash Ratio | 70.12% |
| Final Cash Ratio | 44.40% |
| Average Gross Exposure | 29.88% |
| Final Gross Exposure | 55.60% |
| Average Position Count | 5.95 |
| Maximum Position Count | 9 |
| BUY Notional | 1,739,660 JPY |
| SELL Notional | 1,171,430 JPY |
| Gross Turnover Notional | 2,911,090 JPY |
| Gross Turnover / Average Equity | 2.99x |
| Realized PnL, run-scoped slices | -50,190 JPY |
| Final Unrealized PnL | +22,700 JPY |

Run-scoped PnL equation:

```text
-27,490 = -50,190 realized + 22,700 unrealized + 0 cash adjustment + rounding
```

## Daily Attribution

| Date | Equity | Daily Chg | Cash | Invested MV | Exposure | Pos | BUY | SELL | Realized | Unrealized | Recon Diff |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2022-08-10 | 995,860 | -4,140 | 745,820 | 250,040 | 25.11% | 9 | 254,180 | 0 | 0 | -4,140 | 0 |
| 2022-08-12 | 1,000,700 | +4,840 | 696,190 | 304,510 | 30.43% | 8 | 159,530 | 109,900 | -2,700 | +3,400 | 0 |
| 2022-08-15 | 998,660 | -2,040 | 678,790 | 319,870 | 32.03% | 9 | 64,100 | 46,700 | -600 | +1,960 | 0 |
| 2022-08-16 | 986,500 | -12,160 | 819,050 | 167,450 | 16.97% | 7 | 26,520 | 166,780 | -13,550 | +3,350 | 0 |
| 2022-08-17 | 989,170 | +2,670 | 830,200 | 158,970 | 16.07% | 7 | 0 | 11,150 | +520 | +5,500 | 0 |
| 2022-08-18 | 988,830 | -340 | 794,070 | 194,760 | 19.70% | 8 | 60,630 | 24,500 | +1,000 | +4,160 | 0 |
| 2022-08-19 | 988,350 | -480 | 799,590 | 188,760 | 19.10% | 6 | 58,620 | 64,140 | -250 | +3,930 | 0 |
| 2022-08-22 | 989,430 | +1,080 | 792,110 | 197,320 | 19.94% | 4 | 92,160 | 84,680 | +3,450 | +1,560 | 0 |
| 2022-08-23 | 986,610 | -2,820 | 702,850 | 283,760 | 28.76% | 6 | 89,260 | 0 | 0 | -1,260 | 0 |
| 2022-08-24 | 943,210 | -43,400 | 458,210 | 485,000 | 51.42% | 5 | 316,220 | 71,580 | -5,560 | -39,100 | 0 |
| 2022-08-25 | 965,610 | +22,400 | 754,710 | 210,900 | 21.84% | 3 | 0 | 296,500 | -16,000 | -700 | 0 |
| 2022-08-26 | 963,640 | -1,970 | 565,610 | 398,030 | 41.30% | 6 | 189,100 | 0 | 0 | -2,670 | 0 |
| 2022-08-29 | 955,610 | -8,030 | 731,110 | 224,500 | 23.49% | 4 | 0 | 165,500 | -10,600 | -100 | 0 |
| 2022-08-30 | 957,910 | +2,300 | 726,610 | 231,300 | 24.15% | 3 | 49,900 | 45,400 | -2,400 | +4,600 | 0 |
| 2022-08-31 | 956,690 | -1,220 | 646,810 | 309,880 | 32.39% | 5 | 79,800 | 0 | 0 | +3,380 | 0 |
| 2022-09-01 | 954,830 | -1,860 | 631,870 | 322,960 | 33.82% | 5 | 14,940 | 0 | 0 | +1,520 | 0 |
| 2022-09-02 | 957,750 | +2,920 | 631,870 | 325,880 | 34.03% | 5 | 0 | 0 | 0 | +4,440 | 0 |
| 2022-09-05 | 954,910 | -2,840 | 634,670 | 320,240 | 33.54% | 5 | 27,200 | 30,000 | +3,600 | -2,000 | 0 |
| 2022-09-06 | 948,470 | -6,440 | 588,270 | 360,200 | 37.98% | 7 | 46,400 | 0 | 0 | -8,440 | 0 |
| 2022-09-07 | 972,510 | +24,040 | 431,770 | 540,740 | 55.60% | 7 | 211,100 | 54,600 | -7,100 | +22,700 | 0 |

### 2022-08-24

The `-43,400` JPY day is the main drawdown trough. It reconciles as:

```text
realized slice PnL -5,560
unrealized PnL change -37,840
total equity change -43,400
```

Primary driver: `78780` was opened on 2022-08-24 with 286,000 JPY notional
and ended the day at a `-44,000` campaign PnL / unrealized loss. This was a
new-entry immediate adverse move, not a valuation-basis anomaly.

Other material same-day effects:

- `36600` closed at `-5,600` realized PnL.
- `94320` received an ADD on the same date; the campaign remained open and
  did not explain the large same-day loss.
- No benchmark return was available in `benchmark_snapshot.json`; broad market
  causality cannot be proven from this run's benchmark artifact.

PIT evidence before/at decision time showed `2022-08-24` trend regime was
`RANGE`, breadth was `NEUTRAL`, and volatility regime was `NORMAL`. This is
enough to support a future entry-quality / regime-transition research question,
but not enough to claim the runtime "should have known" the 78780 next-day
outcome.

### 2022-09-07

The `+24,040` JPY recovery reconciles as:

```text
realized slice PnL -7,100
unrealized PnL change +31,140
total equity change +24,040
```

Primary recovery driver: `47600` was opened on 2022-09-07 with 141,100 JPY
notional and ended the day at `+29,700` unrealized PnL. Secondary positive
effect: `94320` increased by about `+1,800` in market value. Offsets included
EXIT losses in `23880` and `37820`, and open unrealized losses in `41650`,
`36600`, and `67860`.

This recovery was mainly a new-entry winner, not prior-loser recovery and not
an ADD-driven recovery.

## Symbol Contribution

Contribution uses run-scoped realized slices plus final unrealized PnL.

Worst contributors:

| Symbol | Realized | Final Unrealized | Total |
| --- | ---: | ---: | ---: |
| 78780 | -16,000 | 0 | -16,000 |
| 37820 | -7,700 | 0 | -7,700 |
| 36600 | -5,600 | -1,300 | -6,900 |
| 91070 | -6,550 | 0 | -6,550 |
| 99840 | -6,200 | 0 | -6,200 |
| 23880 | -6,100 | 0 | -6,100 |
| 93180 | -5,000 | 0 | -5,000 |
| 60540 | -4,400 | 0 | -4,400 |
| 41650 | 0 | -3,500 | -3,500 |
| 67860 | 0 | -2,100 | -2,100 |

Best contributors:

| Symbol | Realized | Final Unrealized | Total |
| --- | ---: | ---: | ---: |
| 47600 | 0 | +29,700 | +29,700 |
| 70800 | +2,650 | 0 | +2,650 |
| 78590 | +1,700 | 0 | +1,700 |
| 37770 | +1,600 | 0 | +1,600 |
| 89180 | +1,100 | 0 | +1,100 |
| 23700 | +1,000 | 0 | +1,000 |
| 36640 | +500 | 0 | +500 |
| 94320 | 0 | +320 | +320 |
| 76470 | 0 | 0 | 0 |
| 23230 | -30 | 0 | -30 |

The largest single loser, `78780`, explains 58.2% of the total loss by itself
in absolute terms. The top six negative symbols total `-49,450` JPY, more than
the full portfolio loss, and were partly offset by `47600`.

## BUY_NEW

Observed counts:

| Item | Count |
| --- | ---: |
| Buy Quality decisions | 1,000 |
| BUY_NEW runtime plans with positive quantity | 33 |
| BUY_NEW campaign events | 33 |
| Total BUY-side fills, including ADD | 39 |
| BUY fill notional | 1,739,660 JPY |

The execution fill field `source_decision_type` records BUY-side fills as
`BUY`; the BUY_NEW versus ADD split is therefore taken from
`positions/position_campaigns.json` event stage. That split is 33 BUY_NEW
events and 6 ADD events.

Forward outcome, observed only inside this 20BD window:

| Horizon | N | Avg | Win Rate | Median |
| --- | ---: | ---: | ---: | ---: |
| 1BD | 37 | -1.00% | 35.1% | 0.00% |
| 3BD | 34 | -1.17% | 29.4% | -0.50% |
| 5BD | 33 | -0.86% | 36.4% | -0.13% |
| 10BD | 26 | -0.76% | 34.6% | -0.36% |

Worst immediate executed BUY examples included `67860` on 2022-09-06
(-16.24% 1BD), `37820` on 2022-08-15 (-14.12% 1BD), `23880` on 2022-08-10
(-12.58% 1BD), and `36600` on 2022-08-22 (-11.22% 1BD). This supports
Entry Quality as a clean Phase30 research topic.

## BUY_WAIT

Observed counts:

| Item | Count |
| --- | ---: |
| BUY_WAIT decisions | 244 |
| FADING_PRIOR_WINNER BUY_WAIT | 186 |
| RECENT_ACCELERATION_OVERHEAT BUY_WAIT | 58 |

BUY_WAIT forward outcome, observed only inside this 20BD window:

| Horizon | N | Avg | Win Rate | Median |
| --- | ---: | ---: | ---: | ---: |
| 1BD | 222 | +0.64% | 43.7% | -0.25% |
| 3BD | 198 | +1.49% | 43.9% | -0.40% |
| 5BD | 172 | -0.24% | 40.1% | -1.38% |
| 10BD | 112 | -1.27% | 31.2% | -4.12% |

BUY_WAIT appears mixed. It avoided some severe 5BD losers such as `79460`,
`96100`, `21640`, and `71380`, but it also missed strong short-term moves such
as `60540`, `70800`, `36600`, and `13820`. Twenty business days is too small
for a BUY_WAIT policy conclusion.

## ADD

Observed counts:

| Item | Count |
| --- | ---: |
| PM ADD decisions | 11 |
| Runtime BUY_ADD plans | 6 |
| ADD campaign events | 6 |
| ADD notional | 150,560 JPY |

All observed ADD events were to `94320`:

| Date | Quantity | Price | Notional |
| --- | ---: | ---: | ---: |
| 2022-08-19 | 200 | 149.1 | 29,820 |
| 2022-08-22 | 200 | 150.8 | 30,160 |
| 2022-08-23 | 200 | 151.8 | 30,360 |
| 2022-08-24 | 200 | 151.1 | 30,220 |
| 2022-08-31 | 100 | 150.6 | 15,060 |
| 2022-09-01 | 100 | 149.4 | 14,940 |

`94320` ended with only `+320` unrealized PnL after total campaign buy notional
of `180,400` JPY and observed MFE of `+2,000` JPY. This does not prove ADD is
bad, but this 20BD window provides weak evidence for ADD accretion.

Non-conversion reasons were mostly legitimate zero-delta and existing pending
states. Frequent no-order reasons included `no_order_zero_quantity_delta` and
`portfolio_add_candidate_maps_to_buy_new`; REDUCE non-conversion was explained
by discrete lot and minimum notional semantics.

## HOLD / Winner Continuation and Profit Retention

Campaign evidence shows a few small retained winners and one large open winner:

| Campaign / Symbol | Status | Entry | Final PnL | MFE | MFE Date | Retention |
| --- | --- | --- | ---: | ---: | --- | ---: |
| 47600 | OPEN | 2022-09-07 | +29,700 | +29,700 | 2022-09-07 | 100.0% |
| 37770 | CLOSED | 2022-08-26 | +3,600 | +3,600 | 2022-09-02 | 100.0% |
| 70800 | CLOSED | 2022-08-18 | +2,650 | +3,800 | 2022-08-18 | 69.7% |
| 78590 | CLOSED | 2022-08-15 | +1,700 | +2,000 | 2022-08-17 | 85.0% |
| 89180 | CLOSED | 2022-08-10 | +1,100 | +1,700 | 2022-08-15 | 64.7% |
| 94320 | OPEN | 2022-08-10 | +320 | +2,000 | 2022-08-30 | 16.0% |

Material giveback candidates:

- `94320`: MFE `+2,000`, final `+320`, giveback `1,680`, retention 16.0%.
- `93180` second campaign: MFE `+5,300`, final `0`, retention 0.0%.
- `36600` second campaign: MFE `+2,200`, final `-1,300`.

The objective is not peak selling. The clean evidence supports a future
winner-retention / topping-risk read-only deep dive, not an immediate
profit-taking threshold.

## REDUCE / EXIT

Observed Position Management actions:

| Action | Count |
| --- | ---: |
| HOLD | 55 |
| ADD | 11 |
| REDUCE | 20 |
| EXIT | 26 |

Execution fills had 10 `REDUCE` and 26 `EXIT` source decisions. REDUCE
non-execution was explained by intentional discrete-lot/minimum-notional
semantics:

```text
REDUCE_UNEXECUTABLE_DUE_TO_MINIMUM_NOTIONAL
REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT
```

Notable delayed/late exit or adverse-entry cases for future research:

- `78780`: large immediate adverse move, exited next day at `-16,000`.
- `91070`: small early MFE, exited at `-6,550`.
- `36600` first campaign: small initial MFE, exited at `-5,600`.
- `37820` first campaign: strong intraday/short MFE was not retained, closed
  at `-2,000`.

These are research candidates, not implementation conclusions.

## Market Context / Regime

Available market context was `trend_regime`, `volatility_regime`, and
`market_breadth`. Benchmark snapshots were present but missing TOPIX values,
so broad-market return attribution is not available from this run.

Trend regime distribution:

| Trend Regime | Days |
| --- | ---: |
| BULL | 11 |
| RANGE | 6 |
| RECOVERY | 2 |
| CORRECTION | 1 |
| BEAR | 0 |

The largest loss day, 2022-08-24, occurred under `RANGE` / `NEUTRAL` breadth.
The final recovery day, 2022-09-07, occurred under `CORRECTION` / `NEUTRAL`
breadth. This clean 20BD run does not support a claim that BULL itself causes
poor performance. It supports a weaker hypothesis: entry quality and
profit-retention may be sensitive to transition from BULL/RECOVERY into RANGE
or CORRECTION, but sample size is too small.

## Capital Deployment

Average cash was high at 683,009 JPY / 70.12%, and final cash remained
431,770 JPY / 44.40%. This is not automatically a defect.

Evidence-based decomposition:

- BUY Quality evaluated 1,000 rows; 187 were REJECT and 244 were BUY_WAIT.
- Runtime planning produced 467 `NO_ORDER`, 60 `NO_ACTION`, 33 positive
  `BUY_NEW`, and 6 `BUY_ADD` plans.
- Dominant non-conversion reason was `no_order_zero_quantity_delta`, not a
  failed cash mutation.
- REDUCE non-conversion was explained by known discrete lot / minimum notional
  semantics.
- Final-day pending state was `CONSUMED`; no stale Pending quantity remained.

No real capital-conversion defect was proven in this 20BD audit. The stronger
performance question is whether deployed capital had enough edge. In this
window, deployed BUY entries had negative average forward outcomes.

## Re-entry

Re-entry evidence appeared mainly as guard reason codes such as
`reentry_minimum_cooldown_not_satisfied` and
`reentry_opportunity_not_requalified`. No obvious churn loop was found, and
REENTRY was not confused with BUY_ADD in the observed ADD campaign (`94320`).
The sample is insufficient for REENTRY quality conclusions.

## Root Performance Diagnosis

1. Primary cause: poor deployed-capital return from a small number of adverse
   entries, especially `78780` on 2022-08-24.
2. Secondary cause: realized losses accumulated across short-lived campaigns
   (`91070`, `99840`, `36600`, `23880`, `37820`, `93180`, `60540`).
3. Tertiary cause: profit retention was weak in some campaigns; `94320`,
   `93180` second campaign, and `36600` second campaign gave back positive MFE.
4. Not supported: measurement contamination, price/quantity basis mismatch,
   stale Pending contamination, or broad-market benchmark causality.
5. Insufficient evidence: robust regime profitability, long-term BUY_WAIT
   value, long-term ADD quality, REENTRY quality, and formal Expected Edge
   calibration.

## Phase30 Research Implications

Clean evidence supports further investigation of:

- Entry Quality: strong support.
- SELL Timing / Exit Outcome Separability: strong support.
- Winner Continuation / Profit Retention: moderate support.
- ADD Quality: moderate support, centered on `94320`.
- BUY_WAIT: mixed support; both avoided losses and missed winners are visible.
- Market Regime Transition: preliminary support only.
- Capital Deployment: focus on deployed-capital quality, not forced exposure.
- Re-entry: low support in this 20BD window.
- Expected Edge Calibration: still relevant, but not specifically proven by
  this short window.

## Evidence Limitations

Strong evidence:

- Measurement, valuation, basis, cash/equity reconciliation.
- Direct daily and symbol/campaign PnL reconstruction.

Preliminary evidence:

- Entry quality, ADD quality, SELL timing, and profit retention.

Insufficient evidence:

- Annualized Strategy quality.
- Long-horizon regime behavior.
- Long-term BUY_WAIT / ADD / REENTRY effectiveness.
- Formal Expected Edge economic calibration.

## Recommended Next Task

`Phase30-B Clean Long-Horizon Baseline Preparation`

Reason: Gate A confirmed the 20BD run is clean enough for attribution, and
Gate B found plausible Strategy research directions. The next required step is
to prepare the user-operated clean long-horizon baseline so Phase30 does not
overfit a single 20BD diagnostic window.
