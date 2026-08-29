# Phase32-AL — Post-AI Sideways-Regime Loss / Winner-Retention Characterization Audit

## Executive Summary

This is a read-only characterization of the live Post-AI long Historical fresh-run `runtime-test-historical-extended-smoke-20260827T093649849074Z`. During inspection the run had valuation-ready artifacts through `2023-11-21`; later in-flight state is excluded.

The September-November window is genuinely sideways:

- `2023-09-01` equity: `1,681,240`
- `2023-09-07` equity: `1,699,100`
- `2023-11-17` equity: `1,701,420`
- `2023-11-21` equity: `1,684,670`
- Sideways-window return: `+0.20%`
- Sideways max drawdown: `-4.31%`
- Average exposure: `58.44%`
- Median exposure: `57.61%`

Primary cause is `MIXED`. The run was not simply failing because it could not invest; it had `86` BUY_NEW fills and `6` REENTRY fills in the sideways window. But cash/PC/MCC underdeployment was material: cash >= 40% occurred on `31` of `55` valuation-ready days, and cash >= 50% occurred on `19` days. At the same time, campaign artifacts show material short-horizon losses, mostly BUY_NEW, plus visible winner giveback. The evidence supports "defensive/cautious sideways behavior plus entry churn and some retained-winner giveback," not a single mandatory runtime defect.

## Run Identity / Coverage

- Run id: `runtime-test-historical-extended-smoke-20260827T093649849074Z`
- Run root: `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260827T093649849074Z`
- Run status at inspection: `RUNNING`
- `run_state.json` next job observed: `2023-11-21:market_refresh`
- Valuation-ready coverage used: `2022-10-03` through `2023-11-21`
- Primary AL window: `2023-09-01` through `2023-11-21`
- Baseline comparison window: `2023-07-03` through `2023-08-31`
- Constraints honored: no production/config/schema/threshold/model/runtime-state mutation; no fresh-run, resume, replay, backtest, or run stop.

## Segment Performance

| Segment | Days | Start Eq | End Eq | Return | Max Eq | Min Eq | Max DD | Avg Exp | Med Exp | Avg Cash | Avg Pos | BUY_NEW | REENTRY | BUY_ADD | SELL |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2023-07-03 to 2023-08-31 | 42 | 1,643,470 | 1,667,350 | +1.45% | 1,672,770 | 1,529,430 | -7.44% | 79.27% | 79.11% | 329,820 | 11.8 | 72 | 2 | 0 | 70 |
| 2023-09-01 to 2023-11-21 | 55 | 1,681,240 | 1,684,670 | +0.20% | 1,703,130 | 1,625,840 | -4.31% | 58.44% | 57.61% | 695,703 | 10.1 | 86 | 6 | 0 | 108 |
| September | 20 | 1,681,240 | 1,676,800 | -0.26% | 1,699,100 | 1,665,430 | -1.98% | 70.25% | 72.41% | 499,394 | 12.8 | 40 | 2 | 0 | 58 |
| October | 21 | 1,670,100 | 1,653,340 | -1.00% | 1,697,880 | 1,625,840 | -4.24% | 52.33% | 53.65% | 793,994 | 9.0 | 36 | 2 | 0 | 32 |
| November through 2023-11-21 | 14 | 1,676,800 | 1,684,670 | +0.47% | 1,703,130 | 1,664,130 | -2.29% | 50.75% | 49.50% | 828,708 | 7.9 | 10 | 2 | 0 | 18 |

Interpretation: September starts invested, then the system de-risks. October/November are flatter but with much lower exposure and higher average cash. The window is not a pure market-loss period; the system repeatedly alternates sell-down, cautious cash retention, and limited redeployment.

## Daily Loss Distribution

Sideways window daily PnL distribution:

- Negative days: `27`
- Positive days: `28`
- Average loss day: `-11,151`
- Average gain day: `+11,372`
- Sum of loss days: `-301,090`
- Sum of gain days: `+318,410`

Worst 20 daily PnL days:

| Date | PnL | Equity | Exposure | Cash | Pos | BUY_NEW | REENTRY | SELL | PC/PS winner |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 2023-10-04 | -45,970 | 1,651,910 | 57.6% | 42.4% | 7 | 2 | 0 | 1 | CASH/CASH |
| 2023-10-13 | -34,100 | 1,658,830 | 33.9% | 66.1% | 8 | 2 | 0 | 1 | CASH/CASH |
| 2023-10-26 | -30,210 | 1,625,840 | 39.3% | 60.7% | 9 | 1 | 0 | 2 | CASH/CASH |
| 2023-09-11 | -23,310 | 1,675,690 | 68.9% | 31.1% | 14 | 1 | 0 | 3 | CASH/CASH |
| 2023-11-08 | -20,080 | 1,669,730 | 49.3% | 50.7% | 11 | 1 | 0 | 3 | CASH/CASH |
| 2023-10-19 | -17,880 | 1,654,100 | 48.1% | 51.9% | 11 | 2 | 0 | 3 | CASH/CASH |
| 2023-10-06 | -17,780 | 1,674,170 | 54.1% | 45.9% | 5 | 1 | 0 | 2 | CASH/CASH |
| 2023-11-07 | -13,320 | 1,689,810 | 63.1% | 36.9% | 13 | 2 | 0 | 1 | CASH/CASH |
| 2023-09-20 | -12,070 | 1,669,920 | 75.6% | 24.4% | 14 | 5 | 0 | 2 | CASH/CASH |
| 2023-11-20 | -11,880 | 1,689,540 | 65.2% | 34.8% | 6 | 1 | 0 | 0 | CASH/CASH |
| 2023-10-16 | -11,210 | 1,647,620 | 47.2% | 52.8% | 9 | 3 | 0 | 2 | CASH/CASH |
| 2023-10-24 | -10,800 | 1,661,250 | 50.9% | 49.1% | 11 | 2 | 0 | 3 | CASH/CASH |
| 2023-11-10 | -8,240 | 1,664,130 | 32.7% | 67.3% | 7 | 0 | 0 | 1 | CASH/CASH |
| 2023-09-25 | -7,170 | 1,665,430 | 60.3% | 39.7% | 9 | 0 | 0 | 5 | CASH/CASH |
| 2023-10-02 | -6,700 | 1,670,100 | 55.0% | 45.0% | 7 | 1 | 1 | 1 | CASH/CASH |
| 2023-09-28 | -5,370 | 1,674,240 | 44.7% | 55.3% | 8 | 2 | 0 | 1 | CASH/CASH |
| 2023-10-25 | -5,200 | 1,656,050 | 45.8% | 54.2% | 10 | 1 | 0 | 2 | CASH/CASH |
| 2023-11-21 | -4,870 | 1,684,670 | 68.9% | 31.1% | 7 | 0 | 1 | 0 | NEW/NEW |
| 2023-09-06 | -3,640 | 1,689,610 | 86.1% | 13.9% | 19 | 0 | 2 | 0 | NEW/NEW |
| 2023-11-15 | -3,380 | 1,684,780 | 41.7% | 58.3% | 4 | 0 | 0 | 1 | CASH/CASH |

Best days are comparable in size, with the largest positive day `+40,040` on `2023-10-05` and `+27,780` on `2023-10-03`. Losses are not one catastrophic event; they are a cluster of mid-sized losses and sell/mark transitions that are mostly offset by gains.

## Avoidable-Loss Taxonomy

Using campaign lifecycle evidence available in `positions/position_campaigns.json` as of `2023-11-21`, side-window relevant campaigns are:

- Relevant campaigns: `73`
- Side-window entries: `57`
- Side-window closes: `67`
- Losing campaigns: `31`
- Winning campaigns: `37`
- Campaigns with observed giveback: `43`

Loss taxonomy from observed lifecycle fields:

| Classification | Count | Evidence pattern |
| --- | ---: | --- |
| `EARLY_FAILURE` | 24 | Closed within 0-5 business days after entry, negative current campaign return |
| `LATE_EXIT_OR_WEAK_HOLD` | 6 | Longer hold, prior weak/reduce evidence, exit after lag or after profit/giveback transition |
| `UNRESOLVED_OPEN_LOSS` | 1 | Still open/lossy at coverage end |
| `SYSTEM_CAUSED` | 0 | No artifact evidence of runtime/schema/valuation defect causing the loss |

Top losing campaigns:

| Symbol | Campaign | Open | Close | Return | MFE | Giveback | Type | Entry evidence |
| --- | --- | --- | --- | ---: | ---: | ---: | --- | --- |
| 50100 | `pc-3ce8867868a4c7eb-50100-0001` | 2023-09-28 | 2023-10-03 | -15.35% | -6.93% | 8.42% | BUY_NEW | rank 29, caution entry |
| 74770 | `pc-5dc7c17238a605c2-74770-0001` | 2023-10-02 | 2023-10-05 | -13.67% | -6.47% | 7.19% | BUY_NEW | rank 24, caution entry, target 20.28% |
| 43340 | `pc-21953aa3f9d1c0fd-43340-0001` | 2023-10-10 | 2023-10-13 | -11.65% | 0.19% | 11.84% | BUY_NEW | rank 42, caution entry |
| 89180 | `pc-dd510c90667fb1bb-89180-0002` | 2023-09-06 | 2023-09-08 | -11.11% | -11.11% | 0.00% | REENTRY | rank 8, full allocation eligible |
| 72680 | `pc-d6fdec6085c678c3-72680-0001` | 2023-09-20 | 2023-09-22 | -9.75% | -9.75% | 0.00% | BUY_NEW | rank 14, caution entry |
| 48820 | `pc-d3d03196c3ea3d8d-48820-0001` | 2023-09-21 | 2023-09-25 | -8.41% | -8.41% | 0.00% | BUY_NEW | rank 45, caution entry |
| 75850 | `pc-16d980bfd560c841-75850-0001` | 2023-09-08 | 2023-09-12 | -6.52% | -6.52% | 0.00% | BUY_NEW | rank 32, caution entry |
| 92460 | `pc-ccb9b7c60669d037-92460-0001` | 2023-10-06 | 2023-10-11 | -6.20% | -6.20% | 0.00% | BUY_NEW | rank 27, caution entry |
| 72560 | `pc-ddc2ba23021fd9b6-72560-0001` | 2023-08-28 | 2023-09-05 | -5.76% | 5.76% | 11.52% | BUY_NEW | rank 14, caution entry |
| 52770 | `pc-9deaa2de6eb414b3-52770-0001` | 2023-09-13 | 2023-09-19 | -4.51% | 1.39% | 5.90% | BUY_NEW | rank 27, caution entry |

Avoidable loss is material enough to research, but not established as a mandatory defect. Most loss entries passed existing quality/safety and were explicitly classified as `CONTINUATION_WITH_CAUTION`, so the issue is more "caution entries still fail often in sideways conditions" than a broken admission contract.

## Entry Quality

Losing entries are mostly BUY_NEW, not REENTRY. They generally have:

- `quality_status=PASS`
- `entry_admission_state=CONTINUATION_WITH_CAUTION`
- `entry_admission_action=BUY_NEW_REDUCED_ONLY`
- `reentry_safety_restriction_status=PASS`
- non-top ranks in many cases, such as 24, 27, 29, 32, 38, 42, 45

Winner contrast matters. Some caution entries also become winners, so a simplistic "remove caution entries" hypothesis would likely discard profitable campaigns too. The correct research framing is avoided loss minus lost winner profit.

Entry quality defect judgment: `PARTIAL`. There is no contract violation, but the sideways regime exposes that existing caution-admitted BUY_NEW entries are a large source of short failures.

## Early Failure

Early failure is material:

- `24` losing campaigns closed within 0-5 business days.
- Most are BUY_NEW.
- Two notable REENTRY early failures exist: `24020` and `89180`, both opened `2023-09-06` and closed `2023-09-08`.

Examples:

- `89180`: REENTRY, rank 8, full allocation eligible, `reentry_recovery_status=PASS`, `reentry_safety_restriction_status=PASS`, return `-11.11%`.
- `24020`: REENTRY, rank 9, reduced allocation, recovery/safety PASS, return `-3.59%`.
- `74770`: BUY_NEW, rank 24, target `20.28%`, return `-13.67%`.
- `43340`: BUY_NEW, rank 42, return `-11.65%`.

This is not a measurement anomaly. It is actual campaign behavior under a sideways/cautious deployment period.

## Winner Retention / Giveback

Winner giveback is also material, but it is mixed rather than plainly defective. The largest giveback cases still retain large profits:

| Symbol | Campaign | Open | Close | Final return | MFE | Giveback | Type |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| 23750 | `pc-86d6c5dc5b09d853-23750-0002` | 2023-10-02 | 2023-11-08 | +111.87% | +190.15% | 115.15% | REENTRY |
| 65730 | `pc-aaf5a539a76e4072-65730-0002` | 2023-08-14 | 2023-09-04 | +156.64% | +170.81% | 58.10% | REENTRY |
| 98120 | `pc-ae921796f7dbae23-98120-0002` | 2023-11-01 | 2023-11-14 | +29.45% | +41.98% | 24.49% | REENTRY |
| 44150 | `pc-17629a6e3512b7ea-44150-0001` | 2023-08-23 | 2023-09-12 | +9.71% | +26.48% | 16.77% | BUY_NEW |
| 39970 | `pc-1cb5cf7513ca1a11-39970-0001` | 2023-10-27 | 2023-11-15 | +5.98% | +22.06% | 16.08% | BUY_NEW |
| 23450 | `pc-5bbeb299f0840195-23450-0001` | 2023-10-12 | 2023-10-24 | -1.34% | +10.16% | 16.04% | BUY_NEW |

The tradeoff is visible: earlier REDUCE/EXIT might save giveback on some campaigns, but the strongest REENTRY winners (`23750`, `65730`) also show why cutting winners too soon can destroy a major profit source.

## Topping / Deceleration Evidence

PM artifacts show decision-time warning/exit evidence before many closes:

- `REDUCE_BY_PEAK_DRAWDOWN_WARNING`
- `REDUCE_BY_WEAK_HOLD_SCORE`
- `EXIT_BY_PEAK_DRAWDOWN`
- `EXIT_BY_TREND_AND_EDGE_BREAK`
- `EXIT_BY_HARD_STOP`
- `profit_retention_break`
- `trend_and_opportunity_broken`
- `weak_hold_score`

This means the system is not blind to deterioration. The research question is not "add a sell trigger immediately"; it is whether REDUCE can act earlier or with better granularity without cutting high-MFE winners prematurely.

## Late EXIT Lag

For side-window closes with PM REDUCE/EXIT evidence, lag from first observed weakening action to close:

| Lag bucket | Count |
| --- | ---: |
| same-day | 8 |
| 1BD | 44 |
| 2-3BD | 5 |
| 4BD+ | 10 |

Late exit is therefore `PARTIAL`: most responses occur same-day or next-day, but the `4BD+` tail is material enough to examine, especially for winner giveback and weak-hold persistence.

Examples of longer lags:

- `70140`: first peak drawdown warning `2023-09-01`, exit `2023-09-20`.
- `60540`: peak drawdown warning `2023-09-13`, exit `2023-09-21`.
- `92710`: weak-hold reduce `2023-09-01`, exit `2023-09-08`.

## Concentration

Concentration is material on some days but not the whole story.

Worst-day contributor checks show large single-symbol transitions:

- `2023-10-04`: large negative contribution from `53800` removal and `59660`/`74770` price declines, partly offset by new positions.
- `2023-10-13`: `43340` close/removal and `23750` mark decline dominate.
- `2023-10-26`: `93480`/`23510` exits plus `23750` mark decline dominate.
- `2023-11-08`: `92700`, `23750`, and `55270` exits/removals dominate.

The single-name safety cap was not shown as violated. The concentration concern is practical PnL concentration in a small number of active positions during low-exposure periods, not an observed hard-cap defect.

## REENTRY Quality

Side-window REENTRY-related campaigns:

| Symbol | Campaign | Open | Close | Status | Return | MFE | Giveback |
| --- | --- | --- | --- | --- | ---: | ---: | ---: |
| 94320 | `pc-091f6fd4e6c166be-94320-0002` | 2023-01-23 | open | OPEN | +14.56% | +20.69% | 11.66% |
| 65730 | `pc-aaf5a539a76e4072-65730-0002` | 2023-08-14 | 2023-09-04 | CLOSED | +156.64% | +170.81% | 58.10% |
| 24020 | `pc-5060a5a5ff8bd409-24020-0002` | 2023-09-06 | 2023-09-08 | CLOSED | -3.59% | -3.59% | 0.00% |
| 89180 | `pc-dd510c90667fb1bb-89180-0002` | 2023-09-06 | 2023-09-08 | CLOSED | -11.11% | -11.11% | 0.00% |
| 23750 | `pc-86d6c5dc5b09d853-23750-0002` | 2023-10-02 | 2023-11-08 | CLOSED | +111.87% | +190.15% | 115.15% |
| 92630 | `pc-fb4e7da4f5743e61-92630-0002` | 2023-10-12 | 2023-11-07 | CLOSED | 0.00% | +0.50% | 0.50% |
| 98120 | `pc-ae921796f7dbae23-98120-0002` | 2023-11-01 | 2023-11-14 | CLOSED | +29.45% | +41.98% | 24.49% |

REENTRY is not the primary churn cause. It has two quick losers, but it also supplies the largest winners and several positive campaigns. Judgment: REENTRY is mixed-to-positive in this window, not the sideways primary cause.

## Cash / Exposure Behavior

Cash thresholds in `2023-09-01` through `2023-11-21`:

- Cash >= 30%: `44` days
- Cash >= 40%: `31` days
- Cash >= 50%: `19` days
- Cash >= 60%: `4` days

High-cash artifacts repeatedly show:

- `CASH_PRE_FINAL_INTERACTION_WINNER`
- `CAUTIOUS_MARKET_OPTIONALITY_ELEVATED`
- `MARGINAL_OPPORTUNITY_SET`
- `NO_VALID_COMPETITOR`
- occasionally `RECOVERY_INCOMPLETE_OPTIONALITY_ELEVATED`
- occasionally `CONCENTRATION_BLOCK` / `CONCENTRATION_OPTIONALITY`
- occasionally `LOT_RESIDUAL_OPTIONALITY`

This is underdeployment relative to July-August and relative to the strong-exposure periods in AK. It is not total paralysis: many BUY_NEW fills still occur. It is also not purely defensive success: lower exposure likely dampened both losses and gains, contributing to sideways rather than recovery.

## Attack / Defense Alignment

Judgment: `PARTIAL`.

Aligned evidence:

- The system reduces exposure after deterioration and sell signals.
- It keeps cash high during repeated `NO_VALID_COMPETITOR`/cautious optionality states.
- It does re-enter selectively, including REENTRY winners.

Misalignment or unresolved evidence:

- Cash remains high through many sideways days even when some positive/executable candidates exist.
- Many BUY_NEW entries fail within 0-5BD despite PASS/caution admission.
- Winner giveback is visible, and the current PM response sometimes trails initial warnings by 4BD+.

## Avoidable Loss vs Lost Winner Profit

Any improvement research should compare avoided loss against lost winner profit. The same broad signals that identify failed caution entries or topping risk also appear near large winners:

- REENTRY `23750` gave back materially but still finished +111.87%.
- REENTRY `65730` gave back but still finished +156.64%.
- BUY_NEW caution entries include both short failures and profitable campaigns.

Therefore, a loss-only filter is not acceptable. Research should evaluate symmetric cohorts: failed early entries, profitable caution entries, winners with drawdown warnings, and winners that would have been prematurely cut.

## Defects

No new mandatory production defect is established by this read-only audit.

Residual risks:

- BUY_NEW caution-entry quality may be too permissive in sideways conditions.
- PM REDUCE/EXIT response has a material 4BD+ lag tail.
- PC/MCC cash optionality may underdeploy through sideways recoveries.
- REENTRY has occasional quick failures, but it is not the main churn driver and also produces major winners.

## Improvement Hypotheses

These are research hypotheses only, not production changes:

- Study caution-entry cohorts by rank and early deterioration evidence; compare avoided early losses against winners that would be filtered.
- Study PM warning-to-exit lag for `REDUCE_BY_PEAK_DRAWDOWN_WARNING` and `REDUCE_BY_WEAK_HOLD_SCORE`; compare giveback saved against high-MFE winners cut too early.
- Study PC/MCC high-cash days where positive/executable candidates existed but cash won with `NO_VALID_COMPETITOR`.
- Study whether lower exposure after sell clusters is defensive alpha or missed recovery participation.

## Next Monitoring Point

Continue the long run. The next useful monitoring point is after a completed post-`2023-11-21` recovery/decline cycle or another 50-100 valuation-ready business days, with special focus on BUY_NEW caution-entry outcomes, PM lag tail, PC/MCC cash optionality, and REENTRY repeat-campaign behavior.

## Final Judgments

PHASE32_AL_RUN_ID = runtime-test-historical-extended-smoke-20260827T093649849074Z

PHASE32_AL_COVERAGE_END = 2023-11-21

PHASE32_AL_SIDEWAYS_WINDOW_RETURN = +0.20%

PHASE32_AL_SIDEWAYS_MAX_DRAWDOWN = -4.31%

PHASE32_AL_AVERAGE_EXPOSURE = 58.44%

PHASE32_AL_PRIMARY_SIDEWAYS_CAUSE = MIXED

PHASE32_AL_AVOIDABLE_LOSS_MATERIAL = PARTIAL

PHASE32_AL_WINNER_GIVEBACK_MATERIAL = PARTIAL

PHASE32_AL_ENTRY_QUALITY_DEFECT = PARTIAL

PHASE32_AL_EARLY_FAILURE_MATERIAL = YES

PHASE32_AL_LATE_EXIT_MATERIAL = PARTIAL

PHASE32_AL_CONCENTRATION_LOSS_MATERIAL = PARTIAL

PHASE32_AL_REENTRY_CAUSING_CHURN = NO

PHASE32_AL_CASH_UNDERDEPLOYMENT_PRIMARY = PARTIAL

PHASE32_AL_ATTACK_DEFENSE_ALIGNMENT = PARTIAL

PHASE32_AL_NEW_MANDATORY_DEFECT_FOUND = NO

PHASE32_AL_PRODUCTION_REPAIR_JUSTIFIED_NOW = NO

PHASE32_AL_IMPROVEMENT_RESEARCH_PRIORITY = BUY_NEW_CAUTION_ENTRY_EARLY_FAILURE_AND_PM_WINNER_RETENTION_LAG_WITH_AVOIDED_LOSS_MINUS_LOST_WINNER_PROFIT_CONTROL

PHASE32_AL_LONG_RUN_CONTINUE = YES

PHASE32_AL_NEXT_STEP = Continue user-operated long run; next read-only audit after another completed market cycle or 50-100 valuation-ready business days.
