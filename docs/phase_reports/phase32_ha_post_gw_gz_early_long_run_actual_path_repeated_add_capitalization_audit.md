# Phase32-HA — Post-GW/GZ Early Long-Run Actual-Path BUY / Repeated-ADD / Capitalization READ-ONLY Audit

Date: 2026-09-05

Run:

```text
runtime-test-historical-extended-smoke-20260905T014831357810Z
```

Window:

```text
2022-10-03 through 2022-12-20
```

Scope: READ-ONLY. No run stop, resume, replay, recover, source edit, config edit, runtime mutation, Pending mutation, Ledger mutation, or accepted generation mutation was performed.

## Executive Summary

The early long-run actual path supports both post-GW and post-GZ acceptance:

- GW MCV priority is class-first and rank-second on actual `portfolio_construction` capital competition rows.
- GZ ADD count hard-cap removal is active on actual runtime path.
- Count-over-five ADDs occurred, reached capital competition, sized to one lot, reached Runtime, and filled.
- No count-only PM ADD-to-HOLD downgrade was found.
- No unsafe repeated ADD, G129 regression, Cash optionality regression, SELL regression, Winner regression, or Recent Exit Guard bypass was found in this window.

PnL/equity trajectory is reported only as context. It was not used to justify BUY/ADD design semantics.

## Window Summary

| Metric | Value |
|---|---:|
| Completed business days | 54 |
| Start equity | 1,012,350 JPY |
| End equity | 1,130,980 JPY |
| Window return | +11.72% |
| Max equity | 1,163,580 JPY |
| Max drawdown from observed equity snapshots | -3.97% |
| Average Cash | 217,900 JPY |
| Average Exposure | 79.92% |
| Average positions | 11.69 |
| BUY fills | 107 |
| BUY_NEW fills | 91 |
| BUY_ADD fills | 16 |
| SELL fills | 111 |

Key equity points:

| Date | Equity | Cash | Exposure | Regime |
|---|---:|---:|---:|---|
| 2022-10-03 | 1,012,350 | 495,530 | 51.05% | BEAR |
| 2022-11-24 | 1,155,660 | 46,860 | 95.95% | BULL |
| 2022-12-06 | 1,163,580 | 187,820 | 83.86% | RANGE |
| 2022-12-20 | 1,130,980 | 416,490 | 63.17% | BEAR |

## GW Comparator Actual Path

Actual-path capital competition rows checked: 1,126.

MCV comparison class ordering:

```text
class inversion count = 0
MCV_CLASS_FIRST_PRIORITY_ACTUAL_PATH_PASS = YES
```

Within each MCV comparison class:

```text
rank-order checks = 1,011
rank-order passes = 1,011
WITHIN_CLASS_RANK_ORDER_PRESERVATION_RATE = 100%
```

Accepted-increment independence:

```text
priority rows with accepted_weight = 0: 896
ACCEPTED_INCREMENT_PRIORITY_DEPENDENCY_COUNT = 0
```

History-neutrality search found no actual priority evidence using old ownership, old campaign, prior ADD count, average cost, realized PnL, or prior EXIT outside the Recent Exit Guard.

NEW / ADD parity:

```text
mixed NEW/ADD same-class day groups observed = 23
NEW_ADD_PRIORITY_PARITY_VIOLATION_COUNT = 0
```

Interpretation: relationship/action type was observable after priority, but no action-type-only bonus or penalty was detected.

## BUY_ADD Inventory

Total BUY_ADD fills in the window: 16.

| Symbol | Campaign | Date | ADD # | Quantity | Cumulative campaign quantity |
|---|---|---:|---:|---:|---:|
| 94340 | pc-bb3781c0298197bf-94340-0001 | 2022-10-06 | 1 | 100 | 300 |
| 94340 | pc-bb3781c0298197bf-94340-0001 | 2022-10-12 | 2 | 100 | 400 |
| 94340 | pc-bb3781c0298197bf-94340-0001 | 2022-10-13 | 3 | 100 | 500 |
| 94320 | pc-e903826142cc4360-94320-0001 | 2022-10-28 | 1 | 100 | 300 |
| 94320 | pc-e903826142cc4360-94320-0001 | 2022-11-01 | 2 | 100 | 400 |
| 76470 | pc-980b2da0b4ab0d6c-76470-0001 | 2022-11-25 | 1 | 100 | 1700 |
| 45940 | pc-38343215d3b95631-45940-0001 | 2022-11-28 | 1 | 100 | 300 |
| 76470 | pc-980b2da0b4ab0d6c-76470-0001 | 2022-11-28 | 2 | 100 | 1800 |
| 76470 | pc-980b2da0b4ab0d6c-76470-0001 | 2022-11-29 | 3 | 100 | 1900 |
| 76470 | pc-980b2da0b4ab0d6c-76470-0001 | 2022-11-30 | 4 | 100 | 2000 |
| 45940 | pc-38343215d3b95631-45940-0001 | 2022-11-30 | 2 | 100 | 400 |
| 76470 | pc-980b2da0b4ab0d6c-76470-0001 | 2022-12-01 | 5 | 100 | 2100 |
| 45940 | pc-38343215d3b95631-45940-0001 | 2022-12-01 | 3 | 100 | 500 |
| 76470 | pc-980b2da0b4ab0d6c-76470-0001 | 2022-12-02 | 6 | 100 | 2200 |
| 76470 | pc-980b2da0b4ab0d6c-76470-0001 | 2022-12-06 | 7 | 100 | 2300 |
| 76470 | pc-980b2da0b4ab0d6c-76470-0001 | 2022-12-16 | 8 | 100 | 2400 |

## GZ Count-Over-Five Actual Path

Actual count-over-five cases are defined as same open campaign `BUY_ADD` fills where the ADD ordinal is `#6+`.

| Date | Symbol | ADD # | PM | PM ADD evidence | PC ADD state | MCV class | Rank | Priority | Competition | Sizing | Runtime | Fill |
|---|---:|---:|---|---|---|---|---:|---:|---|---:|---:|---:|
| 2022-12-02 | 76470 | 6 | ADD | PASS | ADD_REDUCED_ONLY | COMPARABLE_MARGINAL | 2 | 3 | SELECTED / PASS | +100 | 1 plan | 100 |
| 2022-12-06 | 76470 | 7 | ADD | PASS | ADD_REDUCED_ONLY | COMPARABLE_MARGINAL | 2 | 5 | SELECTED / PASS | +100 | 1 plan | 100 |
| 2022-12-16 | 76470 | 8 | ADD | PASS | ADD_REDUCED_ONLY | COMPARABLE_MARGINAL | 1 | 4 | SELECTED / PASS | +100 | 1 plan | 100 |

Counts:

```text
COUNT_OVER_5_ACTUAL_CASE_COUNT = 3
COUNT_OVER_5_PM_HOLD_DOWNGRADE_BY_COUNT = 0
COUNT_OVER_5_CAPITAL_COMPETITION_REACHED_COUNT = 3
COUNT_OVER_5_FILL_COUNT = 3
COUNT_OVER_5_WINNER_CAPITALIZATION_COUNT = 3
UNSAFE_REPEATED_ADD_COUNT = 0
G129_REGRESSION_COUNT = 0
```

No count-over-five case had observed no-loss, continuation, downside-risk, liquidity, lot, cap/headroom, or sizing bypass evidence.

## 76470 Deep Trace

The prompt-listed quantity path is confirmed for the active campaign `pc-980b2da0b4ab0d6c-76470-0001`. The run also had earlier 76470 BUY_NEW events in prior campaigns on 2022-10-12 and 2022-10-20; those are separate campaign-lineage context, not ADD-count continuation in the active 2022-11-07 campaign.

Active campaign trace:

| Date | Type | ADD # | Quantity | Cumulative quantity | SI ADD count | CQ | Risk | MCV class | Rank | Priority | Lot | Competition |
|---|---|---:|---:|---:|---:|---|---|---|---:|---:|---|---|
| 2022-11-07 | BUY_NEW | n/a | 1600 | 1600 | 0 | PASS | PASS | COMPARABLE_MARGINAL | 3 | 1 | EXECUTABLE_NOW | SELECTED |
| 2022-11-25 | BUY_ADD | 1 | 100 | 1700 | 0 | PASS | PASS | COMPARABLE_MARGINAL | 2 | 3 | EXECUTABLE_NOW | SELECTED |
| 2022-11-28 | BUY_ADD | 2 | 100 | 1800 | 1 | PASS | PASS | COMPARABLE_MARGINAL | 2 | 1 | EXECUTABLE_NOW | SELECTED |
| 2022-11-29 | BUY_ADD | 3 | 100 | 1900 | 2 | PASS | PASS | COMPARABLE_MARGINAL | 3 | 3 | EXECUTABLE_NOW | SELECTED |
| 2022-11-30 | BUY_ADD | 4 | 100 | 2000 | 3 | PASS | PASS | COMPARABLE_MARGINAL | 2 | 1 | EXECUTABLE_NOW | SELECTED |
| 2022-12-01 | BUY_ADD | 5 | 100 | 2100 | 4 | PASS | PASS | COMPARABLE_MARGINAL | 2 | 1 | EXECUTABLE_NOW | SELECTED |
| 2022-12-02 | BUY_ADD | 6 | 100 | 2200 | 5 | PASS | PASS | COMPARABLE_MARGINAL | 2 | 3 | EXECUTABLE_NOW | SELECTED |
| 2022-12-06 | BUY_ADD | 7 | 100 | 2300 | 6 | PASS | PASS | COMPARABLE_MARGINAL | 2 | 5 | EXECUTABLE_NOW | SELECTED |
| 2022-12-16 | BUY_ADD | 8 | 100 | 2400 | 7 | PASS | PASS | COMPARABLE_MARGINAL | 1 | 4 | EXECUTABLE_NOW | SELECTED |

Result:

```text
76470_COUNT_OVER_5_ADD_CONFIRMED = YES
76470_TRACE_COMPLETE = YES
```

## Runaway Pyramiding Check

Repeated 76470 ADD did not behave as "count > 5 means unlimited ADD":

- PM ADD evidence remained `PASS`.
- PC member remained ADD-valid through existing ADD state.
- MCV class/rank/priority was recalculated per day.
- Capital competition had a selected ADD competitor each time.
- Sizing produced only one-lot increments.
- Runtime materialized one plan per count-over-five case.
- Lot status remained `EXECUTABLE_NOW`.
- Unsafe repeated ADD count was 0.

## Cash Optionality / Regime Characterization

| Regime | Days | Avg exposure | Avg cash | BUY | ADD | NEW |
|---|---:|---:|---:|---:|---:|---:|
| BEAR | 8 | 58.28% | 436,944 | 18 | 2 | 16 |
| RANGE | 15 | 77.58% | 243,921 | 33 | 3 | 30 |
| RECOVERY | 10 | 80.89% | 210,926 | 18 | 1 | 17 |
| BULL | 19 | 89.67% | 116,066 | 36 | 10 | 26 |
| CORRECTION | 2 | 86.67% | 148,860 | 2 | 0 | 2 |

Cash optionality remained active. On 2022-12-20, after the correction/equity pullback context, valuation exposure was 63.17% with 416,490 JPY cash. This is not consistent with GZ creating forced ADD deployment.

## SELL / Winner / Churn

SELL/Winner:

- GZ touched PM ADD worthiness and PC ADD lifecycle mirror only.
- Actual SELL fills occurred normally in the window.
- No count-over-five case showed SELL-side authority mutation.
- No Winner Protection / Profit Retention regression evidence was found in the inspected artifacts.

Churn:

| Metric | Count |
|---|---:|
| EXIT -> later BUY_NEW same symbol | 24 |
| BUY_NEW -> EXIT -> later BUY_NEW same symbol | 24 |
| Recent Exit Guard bypass | 0 |

The repeated ADD capitalization cases are not BUY_NEW churn cycles. They are same open campaign ADDs with campaign identity preserved.

## Mandatory Answers

- COMPLETED_BD_COUNT: `54`
- WINDOW_END_RETURN: `+11.72%`
- AVG_EXPOSURE: `79.92%`
- AVG_CASH: `217,900 JPY`
- MCV_CLASS_FIRST_PRIORITY_ACTUAL_PATH_PASS: `YES`
- WITHIN_CLASS_RANK_ORDER_PRESERVATION_RATE: `100%`
- HISTORY_PRIORITY_REINTRODUCTION_COUNT: `0`
- NEW_ADD_PRIORITY_PARITY_VIOLATION_COUNT: `0`
- ACCEPTED_INCREMENT_PRIORITY_DEPENDENCY_COUNT: `0`
- TOTAL_BUY_ADD_COUNT: `16`
- COUNT_OVER_5_ACTUAL_CASE_COUNT: `3`
- COUNT_OVER_5_PM_HOLD_DOWNGRADE_BY_COUNT: `0`
- COUNT_OVER_5_CAPITAL_COMPETITION_REACHED_COUNT: `3`
- COUNT_OVER_5_FILL_COUNT: `3`
- 76470_COUNT_OVER_5_ADD_CONFIRMED: `YES`
- 76470_TRACE_COMPLETE: `YES`
- COUNT_OVER_5_WINNER_CAPITALIZATION_COUNT: `3`
- UNSAFE_REPEATED_ADD_COUNT: `0`
- RUNAWAY_PYRAMIDING_FOUND: `NO`
- NEW_ADD_COMPETITION_PRESERVED: `YES`
- CASH_OPTIONALITY_PRESERVED: `YES`
- G129_REGRESSION_COUNT: `0`
- SELL_REGRESSION_FOUND: `NO`
- WINNER_REGRESSION_FOUND: `NO`
- REENTRY_GUARD_BYPASS_COUNT: `0`
- REGIME_CHARACTERIZATION_COMPLETE: `YES`
- PNL_USED_FOR_DESIGN_JUDGMENT: `NO`
- GW_ACTUAL_PATH_ACCEPTED: `YES`
- GZ_ACTUAL_PATH_ACCEPTED: `YES`
- CONTINUE_LONG_RUN_SAFE: `YES`
- LONG_HORIZON_VALIDATION_STILL_VALID: `YES`
- NEXT_STEP: `Continue the current long run without interruption, then repeat the same actual-path audit at the next milestone with count-over-five ADD, Cash optionality, G129, SELL/Winner, and Recent Exit Guard metrics fixed as regression gates.`

## Final Judgment

GWの既存Current-PIT BUY判断復元とGZのADD count hard-cap除去は、2022-10-03〜12-20 actual pathでhistory-neutrality・Safety・Cash・SELL/Winnerを壊さず、強いWinnerへの6回目以降ADDを安全にcapital competitionへ戻せている。
