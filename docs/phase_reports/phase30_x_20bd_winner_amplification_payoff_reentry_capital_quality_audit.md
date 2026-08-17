# Phase30-X - 20BD Winner Amplification / Payoff / Re-entry / Capital Quality Audit

Task ID: `Phase30-X`

Target run:

```text
runtime-test-historical-extended-smoke-20260816T023934342407Z
```

Boundary:

```text
READ_ONLY_AUDIT
NO_IMPLEMENTATION_AUTHORIZED_BY_PHASE30_X
TARGET_RUN_ARTIFACTS_NOT_MUTATED
```

## Primary Judgment

```text
PHASE30_X_20BD_STRATEGY_DIRECTION = MIXED
100BD_ENTRY_GATE = USER_OPERATED_FRESH_100BD_READY
```

The 20BD run is not a performance proof, but it is clean enough to continue to
user-operated 100BD validation. The run shows meaningful loss containment and
some winner preservation / ADD behavior, but payoff quality and re-entry quality
remain mixed. The final +0.05% result was rescued mainly by a large same-day
winner on 2022-09-07, not by broad closed-campaign payoff superiority.

## 20BD Performance

Initial capital was `1,000,000 JPY`.

| Date | Equity | Cash | Market value | Exposure | Daily PnL |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2022-08-10 | 994,000 | 688,580 | 305,420 | 30.73% | -6,000 |
| 2022-08-12 | 998,740 | 762,780 | 235,960 | 23.63% | +4,740 |
| 2022-08-15 | 1,001,660 | 733,580 | 268,080 | 26.76% | +2,920 |
| 2022-08-16 | 989,880 | 786,000 | 203,880 | 20.60% | -11,780 |
| 2022-08-17 | 993,590 | 693,820 | 299,770 | 30.17% | +3,710 |
| 2022-08-18 | 987,300 | 816,600 | 170,700 | 17.29% | -6,290 |
| 2022-08-19 | 988,260 | 857,500 | 130,760 | 13.23% | +960 |
| 2022-08-22 | 988,200 | 808,460 | 179,740 | 18.19% | -60 |
| 2022-08-23 | 994,530 | 746,600 | 247,930 | 24.93% | +6,330 |
| 2022-08-24 | 994,370 | 716,240 | 278,130 | 27.97% | -160 |
| 2022-08-25 | 988,270 | 747,740 | 240,530 | 24.34% | -6,100 |
| 2022-08-26 | 986,530 | 543,840 | 442,690 | 44.87% | -1,740 |
| 2022-08-29 | 979,050 | 651,640 | 327,410 | 33.44% | -7,480 |
| 2022-08-30 | 981,580 | 694,040 | 287,540 | 29.29% | +2,530 |
| 2022-08-31 | 982,710 | 602,030 | 380,680 | 38.74% | +1,130 |
| 2022-09-01 | 982,410 | 587,090 | 395,320 | 40.24% | -300 |
| 2022-09-02 | 984,480 | 587,090 | 397,390 | 40.37% | +2,070 |
| 2022-09-05 | 981,460 | 599,890 | 381,570 | 38.88% | -3,020 |
| 2022-09-06 | 973,880 | 521,490 | 452,390 | 46.45% | -7,580 |
| 2022-09-07 | 1,000,490 | 434,990 | 565,500 | 56.52% | +26,610 |

Peak equity: `1,001,660` on 2022-08-15.

Trough equity: `973,880` on 2022-09-06.

Final equity: `1,000,490`, return `+0.049%`.

Max drawdown from peak: `-2.77%`. Drawdown from initial capital at trough was
`-2.61%`, matching the observed rough drawdown basis.

Recovery: the trough occurred on 2022-09-06 and the next day recovered
`26,610 JPY`; the run ended `1,170 JPY` below the prior equity peak.

## 2022-09-07 PnL Decomposition

The `+26,610 JPY` daily gain reconciles exactly by symbol using:

```text
symbol contribution = end market value + sell proceeds - prior market value - buy notional
```

| Symbol | Contribution | Qty after 2022-09-07 | Status | Notes |
| --- | ---: | ---: | --- | --- |
| 47600 | +29,700 | 100 | BUY_NEW / OPEN | Bought at 1,411, closed at 1,708. Dominant one-day winner. |
| 94320 | +1,800 | 1,200 | HOLD | Long-running campaign preserved; final unrealized +300. |
| 27880 | +1,900 | 100 | HOLD | Open winner, unrealized +5,200. |
| 37820 | +1,500 | 0 | EXIT | Sold at 96 after prior close weakness; campaign realized -5,700. |
| 93180 | 0 | 7,700 | HOLD | Flat at 6.0. |
| 23880 | 0 | 0 | EXIT | Sold at 129; realized -1,400, no incremental daily mark effect. |
| 94340 | -90 | 300 | HOLD | Small mark-to-market loss. |
| 32710 | -900 | 100 | REDUCE candidate / HOLD after no fill | Small open loss. |
| 36600 | -3,500 | 100 | HOLD | Open loss expanded. |
| 67860 | -3,800 | 200 | HOLD | Largest remaining open loser. |

Judgment:

```text
2022_09_07_WINNER_AMPLIFICATION = PARTIAL_WINNER_AMPLIFICATION
```

The day was not a pure random spike because 94320 and 27880 were preserved, but
the gain was dominated by new 47600 same-day mark-to-market PnL.

## Payoff Ratio

Closed campaigns through 2022-09-07:

| Metric | Value |
| --- | ---: |
| Closed campaigns | 23 |
| Winners | 6 |
| Losers | 14 |
| Flat | 3 |
| Win rate | 26.09% |
| Average winner | +1,580 |
| Average loser | -2,675.71 |
| Median winner | +1,250 |
| Median loser | -2,400 |
| Largest winner | +4,800 |
| Largest loser | -6,200 |
| Payoff ratio | 0.59 |
| Profit factor | 0.25 |

Closed-campaign payoff quality is not yet good. The run survived because losses
were mostly cut before becoming large and because open winners existed at close.

## Winner Preservation

Notable winner evidence:

| Symbol | Opened | Status | ADD count | Max qty | Final / realized PnL | Judgment |
| --- | --- | --- | ---: | ---: | ---: | --- |
| 94320 | 2022-08-10 | OPEN | 5 | 1,200 | +300 unrealized | Preserved and repeatedly ADDed; final gain small after giveback. |
| 27880 | 2022-08-29 | OPEN | 0 | 100 | +5,200 unrealized | Preserved. |
| 47600 | 2022-09-07 | OPEN | 0 | 100 | +29,700 unrealized | Strong same-day winner; too young to prove preservation. |
| 37770-0002 | 2022-08-26 | CLOSED | 0 | 1,600 | +4,800 realized | Winner exited on profit-retention break. |
| 78590 | 2022-08-15 | CLOSED | 0 | 100 | +1,700 realized | Winner realized quickly. |

Winner preservation is improving but not conclusive. 94320 was held through the
window and accumulated, while 37770-0002 was profit-protected.

## ADD Quality

ADD executions were concentrated in 94320:

| Date | Symbol | Pre qty | Added qty | Entry / ADD Admission | PM evidence | Resulting quality |
| --- | --- | ---: | ---: | --- | --- | --- |
| 2022-08-19 | 94320 | 200 | 200 | CONTINUATION_WITH_CAUTION / ADD_REDUCED_ONLY | ADD_BY_STRONG_TREND_AND_RANK | Good process |
| 2022-08-22 | 94320 | 400 | 300 | CONTINUATION_WITH_CAUTION / ADD_REDUCED_ONLY | ADD_BY_STRONG_TREND_AND_RANK | Good process |
| 2022-08-23 | 94320 | 700 | 200 | CONTINUATION_WITH_CAUTION / ADD_REDUCED_ONLY | ADD_BY_STRONG_TREND_AND_RANK | Good process |
| 2022-08-24 | 94320 | 900 | 200 | CONTINUATION_WITH_CAUTION / ADD_REDUCED_ONLY | ADD_BY_STRONG_TREND_AND_RANK | Good process |
| 2022-09-01 | 94320 | 1,100 | 100 | CONTINUATION_WITH_CAUTION / ADD_REDUCED_ONLY | ADD_BY_STRONG_TREND_AND_RANK | Mixed, later only small final PnL |

One important non-execution: on 2022-08-31, 94320 had `REVERSAL_RISK_ENTRY /
NO_ADD`, and the one-lot admission was `FAIL_CLOSED` for ADD overshoot. This is
positive evidence that ADD gating can stop a weak-timing ADD.

93180 was not ADD-amplified; it was exited, re-entered, exited, then re-entered
again and ended flat.

```text
ADD_QUALITY = MIXED
```

## Re-entry Churn

Multi-campaign symbols:

| Symbol | Re-entry result | Classification |
| --- | ---: | --- |
| 23880 | -4,200 then -1,400 after initial -4,600 | Repeated bad timing / churn |
| 37770 | -2,000 then +4,800 | Genuine recovery after first failure |
| 37820 | -2,800 then -5,700 | Repeated bad timing |
| 89180 | +1,300 then 0 | Mostly neutral, but capital occupied |
| 93180 | -6,000 then 0 then 0 open | Churn / unresolved continuation |
| 94340 | +80 then -630 open | Mixed |

Aggregate re-entry campaigns excluding first campaigns: 8. Profitable: 1.
Losing: 3 closed plus 1 open loser. Flat / near-flat: 3. Re-entry quality is
not strong enough to call improved.

```text
REENTRY_QUALITY = MIXED_TO_POOR
```

## Entry Admission Effectiveness

Across the 20BD Strategy Intelligence artifacts:

| Entry state / action | Count |
| --- | ---: |
| CONTINUATION_WITH_CAUTION / BUY_NEW_REDUCED_ONLY | 754 |
| CONTINUATION_WITH_CAUTION / ADD_REDUCED_ONLY | 103 |
| OVERHEATED_DECELERATING_ENTRY / BUY_WAIT | 94 |
| HEALTHY_CONTINUATION_ENTRY / BUY_NEW_ALLOWED | 42 |
| HEALTHY_CONTINUATION_ENTRY / ADD_ALLOWED | 4 |
| OVERHEATED_DECELERATING_ENTRY / NO_ADD | 5 |
| REVERSAL_RISK_ENTRY / BUY_WAIT | 1 |
| REVERSAL_RISK_ENTRY / NO_ADD | 1 |

Actual BUY fills were all `CONTINUATION_WITH_CAUTION / BUY_NEW_REDUCED_ONLY` or
`CONTINUATION_WITH_CAUTION / ADD_REDUCED_ONLY`. No actual BUY fill was found in
`OVERHEATED_DECELERATING_ENTRY / BUY_WAIT` or `REVERSAL_RISK_ENTRY / BUY_WAIT`.

This supports the Phase30-W entry gate, but it also means the run was still
driven by cautious entries rather than a large number of clearly healthy entries.

## One-Lot Admission Effectiveness

Observed one-lot admission outcomes across PC artifacts:

| Outcome | Count |
| --- | ---: |
| skipped / PASS / BUY_NEW_REDUCED_ONLY / PASS | 88 |
| skipped / PASS / BUY_NEW_REDUCED_ONLY / NOT_REQUIRED | 8 |
| promoted / PASS / BUY_NEW_REDUCED_ONLY / PASS | 119 |
| promoted / PASS / BUY_NEW_ALLOWED / PASS | 7 |
| promoted / PASS / ADD_REDUCED_ONLY / PASS | 1 |
| skipped / FAIL_CLOSED / NO_ADD / FAIL | 1 |

Critical recurrence check:

```text
PHASE30_W_ONE_LOT_DEFECT_RECURRENCE = NO
```

The 2022-08-31 94320 ADD overshoot was blocked with `FAIL_CLOSED`, showing that
Safety pass alone did not authorize a weak ADD.

## Capital Quality

Final capital was concentrated in:

| Symbol | Weight approx. | Campaign PnL | Entry Admission at close | Quality read |
| --- | ---: | ---: | --- | --- |
| 94320 | 18.1% | +300 | CONTINUATION_WITH_CAUTION / ADD_REDUCED_ONLY | Large but modest final edge |
| 47600 | 17.1% | +29,700 | CONTINUATION_WITH_CAUTION / BUY_NEW_REDUCED_ONLY | Strong same-day winner, young |
| 36600 | 4.9% | -1,300 | CONTINUATION_WITH_CAUTION / ADD_REDUCED_ONLY | Weak open result |
| 93180 | 4.6% | 0 | CONTINUATION_WITH_CAUTION / ADD_REDUCED_ONLY | Flat re-entry |
| 94340 | 4.5% | -630 | CONTINUATION_WITH_CAUTION / ADD_REDUCED_ONLY | Small open loser |
| 27880 | 3.5% | +5,200 | CONTINUATION_WITH_CAUTION / ADD_REDUCED_ONLY | Good preserved winner |
| 67860 | 2.0% | -4,200 | CONTINUATION_WITH_CAUTION / ADD_REDUCED_ONLY | Weak open loser |
| 32710 | 1.9% | -600 | CONTINUATION_WITH_CAUTION / ADD_REDUCED_ONLY | Small open loser |

```text
CAPITAL_QUALITY = MIXED
```

Capital concentration was not obviously broken, but the book still held several
small losing or flat positions.

## Loss Containment

Largest realized losses:

| Symbol / campaign | PnL | Classification |
| --- | ---: | --- |
| 99840-0001 | -6,200 | Bad entry / fast exit contained |
| 93180-0001 | -6,000 | Delayed exit after reduce; contained at small notional |
| 37820-0002 | -5,700 | Bad re-entry / fast exit contained |
| 23880-0001 | -4,600 | Bad entry / hard stop |
| 23880-0002 | -4,200 | Re-entry churn / hard stop |
| 60540-0001 | -2,800 | Normal adverse move or bad entry |
| 37820-0001 | -2,800 | Bad entry / fast exit |
| 37770-0001 | -2,000 | Bad entry / hard stop |

The sell side is doing useful damage control. The remaining issue is not delayed
catastrophic exit; it is too many mediocre entries / re-entries that require the
sell side to clean up.

## Close REVIEW_REQUIRED

```text
CLOSE_REVIEW_CLASSIFICATION = CLOSE_REVIEW_OPERATIONAL
```

Evidence:

```text
accounting_state_judgment = PASS
trading_state_judgment = PASS
production_planning_judgment = PASS
block_rule = NO_BLOCKING_CLOSE_RULE_TRIGGERED
strategy_shadow_close_classification = NON_MUTATING_STRATEGY_SHADOW_REVIEW_NON_BLOCKING
review_reasons = strategy_shadow_review_required_non_blocking
```

This is not classified as a Runtime defect or authority gap for Phase30-X.

## Production Integrity

```text
PHASE30_P_STRATEGY_MIGRATION_PRESERVED = YES
ONE_PRODUCTION_STRATEGY_AUTHORITY_PATH = YES
LEGACY_STRATEGY_PATH_REINTRODUCED = NO
PHASE30_S_HANDOFF_DEFECT_RECURRENCE = NO
PHASE30_W_ONE_LOT_DEFECT_RECURRENCE = NO
EXPECTED_EDGE_STATUS = UNCALIBRATED
```

Supporting evidence includes:

```text
Strategy Intelligence semantic_version = 1.3.0
producer_version = phase30_w_entry_admission_one_lot_design.v1
production_consumer_connected = true
active_runtime_consumer_eligibility = YES
legacy_authority_active = false
legacy_formal_planning_authority_active = false
current_state_leakage_detected = false
latest_fallback_used = false
future_information_used = false
```

## Direction Flags

```text
ENTRY_QUALITY_DIRECTION = MIXED
SELL_REDUCE_DIRECTION = IMPROVING
WINNER_PRESERVATION_DIRECTION = IMPROVING
WINNER_AMPLIFICATION_DIRECTION = MIXED
REENTRY_DIRECTION = NOT_IMPROVING
CAPITAL_QUALITY_DIRECTION = MIXED
LOSS_CONTAINMENT_DIRECTION = IMPROVING
PHASE30_20BD_STRATEGY_DIRECTION = MIXED
```

## 100BD Entry Gate

```text
USER_OPERATED_FRESH_100BD_READY
```

Rationale: no blocking Runtime / authority / one-lot recurrence defect was
found. The known weak areas, especially re-entry churn and closed-campaign
payoff ratio, should be tracked over 100BD rather than tuned from this 20BD
window.

Recommended next task:

```text
Phase30-Y - Fresh 100BD Long-Horizon Validation
```
