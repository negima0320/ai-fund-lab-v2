# Phase31-G0 — Clean 100BD Strategy Performance Causal Decomposition Audit

## Scope

Task type: READ-ONLY PERFORMANCE CHARACTERIZATION / CAUSAL DECOMPOSITION.

Target run:

`reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260821T095536206137Z`

No Strategy mutation, threshold change, weight change, config tuning, feature addition, model retraining, Runtime mutation, Pending mutation, fixture mutation, fresh-run, resume, replay, or Historical rerun was performed.

## Evidence Acceptance

The target run completed 100 business days from 2022-08-15 through 2023-01-11. The final close result is `REVIEW_REQUIRED`, but the blocking rule is `NO_BLOCKING_CLOSE_RULE_TRIGGERED`; the review reason is `strategy_shadow_review_required_non_blocking`. `final_summary.json` reports accounting state `PASS`, trading state `PASS`, runtime execution judgment `PASS`, PnL reconciliation `PASS`, and `performance_metrics_used = false`.

Canonical PnL authority is `run_scoped_realized_slices_plus_current_valuation_unrealized_pnl`.

Performance evidence is accepted with a non-performance review caveat.

`PERFORMANCE_EVIDENCE_ACCEPTANCE = PASS_WITH_NON_PERFORMANCE_REVIEW`

Important lineage caveat: all 166 BUY fills in this pre-repair artifact are marked `REVIEW_REQUIRED_PRE_REPAIR_ARTIFACT` for missing `pending_item_id`, `order_plan_item_id`, and `quality_decision_id`. Therefore portfolio-level PnL, realized slices, current valuation, regime attribution, and symbol-level campaign economics are usable; exact BUY candidate rank / quality-decision attribution is partial.

## Portfolio Performance

| Metric | Value |
| --- | ---: |
| Initial equity | 1,000,000 |
| Final equity | 1,171,580 |
| Total PnL | +171,580 |
| Total return | +17.158% |
| Peak equity | 1,199,010 |
| Peak date | 2022-12-15 |
| Peak-to-final giveback | 27,430 |
| Peak-to-final giveback / peak profit | 13.78% |
| Max drawdown | 5.59% |
| Max drawdown window | 2022-09-12 -> 2022-09-28 |
| Positive / negative days | 51 / 49 |
| Average daily PnL | +1,715.8 |
| Median daily PnL | +310 |
| Best day | 2022-10-04, +43,510, RANGE |
| Worst day | 2022-08-31, -30,760, BULL |
| Average exposure | 76.72% |
| Average cash | 254,312 |
| Average position count | 9.14 |

Current valuation evidence had 95 `READY` days and 5 `VALID_CARRYOVER` days. No future quote date was observed. Five open-position quote rows were non-`FRESH_CURRENT_QUOTE`, but the final PnL reconciliation still passed under the run-scoped authority.

## Regime Attribution

| Regime | Days | PnL | Avg Daily PnL | Avg Exposure | Avg Cash | Avg Pos | BUY | ADD | REDUCE | EXIT/SELL | BUY Notional | SELL Notional |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BULL | 28 | +107,600 | +3,842.9 | 87.02% | 139,644 | 11.04 | 61 | 0 | 16 | 32 | 3,564,130 | 1,811,870 |
| RECOVERY | 16 | +89,590 | +5,599.4 | 82.40% | 193,069 | 10.06 | 26 | 0 | 2 | 34 | 1,943,440 | 2,124,710 |
| RANGE | 23 | +37,610 | +1,635.2 | 79.54% | 220,761 | 9.09 | 34 | 0 | 2 | 37 | 2,256,400 | 2,731,200 |
| CORRECTION | 7 | -44,570 | -6,367.1 | 73.36% | 283,676 | 8.71 | 9 | 0 | 1 | 9 | 462,360 | 420,260 |
| BEAR | 26 | -18,650 | -717.3 | 60.54% | 437,262 | 6.69 | 36 | 0 | 3 | 40 | 2,103,710 | 2,603,610 |

Performance was primarily generated in BULL and RECOVERY (+197,190 combined). RANGE was net positive (+37,610), so the degradation is not simply "lost in RANGE"; the largest regime drag was CORRECTION (-44,570). BEAR was mildly negative while exposure and position count were materially lower, suggesting defensive cash helped contain losses.

Peak-to-final daily giveback after 2022-12-15:

| Regime | PnL |
| --- | ---: |
| RANGE | -17,760 |
| CORRECTION | -19,870 |
| BEAR | +10,200 |

Worst transition windows were RANGE -> CORRECTION on 2022-09-16 (-36,250), CORRECTION -> BEAR on 2022-09-26 (-30,590), BULL -> RANGE on 2022-08-29 (-24,860), BULL -> RECOVERY on 2022-11-14 (-24,530), and CORRECTION -> BEAR on 2022-12-20 (-23,350). These are adaptation-quality candidates for later design, not parameter recommendations.

## Campaign Distribution

Symbol-level campaign reconstruction used canonical fills, realized slices, and final current valuation positions. This reconciles exactly to canonical total PnL:

`145,740 realized + 25,840 unrealized = 171,580`.

The final position-campaign artifact contains metadata for 117 symbols, while canonical fill/realized/current valuation evidence covers 161 bought symbols. Therefore MFE/giveback analysis is complete only for the metadata-covered subset; total PnL and top/worst PnL distribution use the reconciled symbol-level authority.

| Metric | Value |
| --- | ---: |
| Total symbol campaigns | 161 |
| Completed symbol campaigns | 152 |
| Open symbol campaigns | 9 |
| Winning completed campaigns | 71 |
| Losing completed campaigns | 72 |
| Flat completed campaigns | 9 |
| Completed win rate | 46.71% |
| Completed avg PnL | +958.8 |
| Completed median PnL | 0 |
| Gross profit | +383,240 |
| Gross loss | -211,660 |

Top 5 winners:

| Symbol | Status | Open | Close | Duration | PnL | Entry Regime | Exit Regime |
| --- | --- | --- | --- | ---: | ---: | --- | --- |
| 62490 | CLOSED | 2022-10-21 | 2022-12-12 | 35 | +43,200 | RANGE | RECOVERY |
| 92270 | CLOSED | 2022-10-24 | 2022-11-07 | 10 | +31,300 | RANGE | RANGE |
| 69730 | CLOSED | 2022-10-25 | 2022-12-05 | 28 | +28,500 | RECOVERY | BULL |
| 78860 | CLOSED | 2022-11-15 | 2022-12-07 | 16 | +23,900 | BULL | RANGE |
| 40800 | CLOSED | 2022-08-16 | 2022-08-22 | 5 | +20,400 | BULL | RECOVERY |

Worst 5 losers:

| Symbol | Status | Open | Close | Duration | PnL | Entry Regime | Exit Regime |
| --- | --- | --- | --- | ---: | ---: | --- | --- |
| 21950 | CLOSED | 2022-08-31 | 2022-09-01 | 2 | -18,670 | BULL | RANGE |
| 21380 | CLOSED | 2022-10-04 | 2022-10-06 | 3 | -12,700 | RANGE | RANGE |
| 65790 | CLOSED | 2022-10-27 | 2022-11-02 | 5 | -9,700 | BULL | RANGE |
| 44220 | CLOSED | 2022-09-26 | 2022-09-29 | 4 | -9,100 | BEAR | BEAR |
| 96100 | CLOSED | 2022-08-31 | 2022-09-01 | 2 | -9,000 | BULL | RANGE |

Concentration:

| Metric | Value |
| --- | ---: |
| Top 1 / gross profit | 11.27% |
| Top 3 / gross profit | 26.88% |
| Top 5 / gross profit | 38.44% |
| Worst 1 / gross loss | 8.82% |
| Worst 3 / gross loss | 19.40% |
| Worst 5 / gross loss | 27.96% |

The +17.16% result is not a single-name jackpot. It is a broad positive distribution with meaningful contribution from the top 5 winners, offset by many short losing cycles.

## Loss Classification

Diagnostic classification only; not counterfactual savings.

| Class | Count | Loss Yen | Median Loss | Avg Duration | Entry Regime Mix |
| --- | ---: | ---: | ---: | ---: | --- |
| LEGITIMATE_STOP | 49 | 166,380 | 2,000 | 2.82BD | BULL 16, BEAR 13, RANGE 9, RECOVERY 7, CORRECTION 4 |
| LATE_EXIT_OR_PROFIT_GIVEBACK_LOSS | 18 | 29,860 | 910 | 6.06BD | BULL 5, RECOVERY 5, RANGE 4, BEAR 3, CORRECTION 1 |
| UNRESOLVED_LOSS | 5 | 9,660 | 1,200 | 7.80BD | BULL 2, RECOVERY 2, RANGE 1 |

`AVOIDABLE_LOSS_YEN = 29,860`

`LEGITIMATE_LOSS_YEN = 166,380`

`SYSTEM_CAUSED_LOSS_YEN = 0`

`UNRESOLVED_LOSS_YEN = 9,660`

The largest reducible bucket visible from existing evidence is not catastrophic single-name failure. It is small-to-medium loss accumulation plus a smaller set of campaigns that first had positive MFE and then closed negative.

## Early Failure Detectability

BUY quality-decision lineage is incomplete in this run, so entry-rank / entry-feature separability cannot be cleanly asserted.

| Detectability Bucket | Campaign Count | Loss Yen | Interpretation |
| --- | ---: | ---: | --- |
| AT_ENTRY | UNRESOLVED | UNRESOLVED | BUY fills lack `quality_decision_id`; do not infer entry weakness from hindsight alone. |
| +1BD / +2BD / +3_TO_5BD | 49 | 166,380 | Short-duration losses with no favorable MFE where metadata is available, plus short realized losers from canonical slices. Focus area is post-entry PM / quick failure confirmation, not a tuned entry filter. |
| LATER | 18 | 29,860 | Positive MFE existed before final loss; this is the clearest avoidable-loss / giveback-loss bucket. |
| NOT_DETECTABLE | 0 asserted | 0 asserted | Not claimed because PIT event completeness is partial. |
| UNRESOLVED | 5 | 9,660 | Insufficient chronology or metadata for a confident class. |

Potential benefit from the clearest avoidable-loss bucket is 29,860 yen. Potential winner damage cannot be selected from this run without thresholding; winner control group shows 52 metadata-covered winning campaigns also experienced material MFE/giveback dynamics, so any future rule must measure removed winner profit before adoption.

## Winner Retention

For the 52 metadata-covered winning campaigns:

| Metric | Value |
| --- | ---: |
| Total winner peak profit | 532,480 |
| Total winner final profit | 333,240 |
| Total winner giveback | 199,240 |
| Winner profit retention ratio | 62.58% |

This is the strongest G0 performance constraint. The system creates winners, but a large amount of peak profit is surrendered before exit. Because this uses post-hoc MFE, it is diagnostic only; no production threshold is authorized from this window.

## SELL, ADD, Churn, Reentry

SELL activity was high: 24 `REDUCE`, 96 explicit `EXIT`, plus 56 SELL fills with missing source decision type in the observability artifact. Runtime/accounting reconciliation still passes, but SELL semantic attribution is partial for the missing-source subset.

No `BUY_ADD` fills were observed in this run.

| Duration Bucket | Completed Count | Net PnL | Gross Loss | Gross Profit |
| --- | ---: | ---: | ---: | ---: |
| same-day / 1BD | 0 | 0 | 0 | 0 |
| 2-5BD | 105 | -107,790 | 183,480 | 75,690 |
| 6-10BD | 23 | +55,650 | 20,600 | 76,250 |
| 11BD+ | 24 | +197,880 | 1,820 | 199,700 |

`CHURN_LOSS_YEN = 183,480`

`CHURN_PROFIT_YEN = 75,690`

`ADD_NET_CONTRIBUTION = 0`

`REENTRY_NET_CONTRIBUTION = 0`

Short 2-5BD turnover is net negative and is a cleaner next design target than broad entry filtering. Longer holds are strongly positive in this window.

## Capital Deployment

Average exposure was 76.72% with average cash 254,312. Cash rose materially in BEAR (average 437,262, exposure 60.54%) and was lowest in BULL (average 139,644, exposure 87.02%). This looks partly intentional and protective in defensive regimes, not simply idle cash drag.

The run still bought actively in BEAR (36 BUY fills, 2,103,710 notional) while selling more than buying in BEAR (2,603,610 SELL notional). That suggests the capital issue is not "too much cash everywhere"; it is timing and quality of rotation around regime transitions.

## Long-Lived Position: 94320

94320 was open for the full 100BD window:

| Metric | Value |
| --- | ---: |
| Open date | 2022-08-15 |
| Final status | OPEN |
| Buy dates | 2022-08-15, 2022-08-22, 2022-08-23, 2022-09-06, 2022-09-15, 2022-09-16 |
| Invested notional / final cost basis | 195,810 |
| Final market value | 193,830 |
| Final unrealized PnL | -1,980 |
| Observed MFE | 9.01% |
| Approx peak profit | 17,650 |

94320 consumed persistent capital but did not behave as a final genuine winner. It is a useful case study for position concentration and opportunity cost, but this report does not assert that long holding itself is wrong.

## Peak-To-Final Giveback

Peak was 2022-12-15 at 1,199,010. Final equity was 1,171,580, for 27,430 giveback.

Daily regime decomposition after peak:

| Bucket | PnL |
| --- | ---: |
| RANGE after peak | -17,760 |
| CORRECTION after peak | -19,870 |
| BEAR after peak | +10,200 |
| Net | -27,430 |

The post-peak giveback is mostly RANGE/CORRECTION deterioration before BEAR de-risking/defense added back some PnL.

## Primary Judgment

`PRIMARY_JUDGMENT = PHASE31_G0_PERFORMANCE_DIAGNOSIS_COMPLETE_NEXT_DESIGN_SHOULD_PRIORITIZE_PM_CHURN_AND_WINNER_RETENTION`

This run produced a real +17.16% canonical return, and the evidence is acceptable for performance characterization. The highest-signal constraints are:

1. Winner profit retention: metadata-covered winners retained only 62.58% of approximate peak profit.
2. Short-cycle churn: 2-5BD completed campaigns lost net -107,790 and generated 183,480 gross loss.
3. Regime transition adaptation: the largest losses clustered around RANGE/CORRECTION and CORRECTION/BEAR transitions, not static BEAR exposure alone.
4. Entry-quality audit is limited by missing BUY `quality_decision_id` lineage; do not design entry filters from hindsight.

## Required Summary Output

`PRIMARY_JUDGMENT = PHASE31_G0_PERFORMANCE_DIAGNOSIS_COMPLETE_NEXT_DESIGN_SHOULD_PRIORITIZE_PM_CHURN_AND_WINNER_RETENTION`

`PERFORMANCE_EVIDENCE_ACCEPTANCE = PASS_WITH_NON_PERFORMANCE_REVIEW`

`INITIAL_EQUITY = 1,000,000`

`FINAL_EQUITY = 1,171,580`

`TOTAL_RETURN_PCT = 17.158`

`PEAK_EQUITY = 1,199,010`

`PEAK_DATE = 2022-12-15`

`MAX_DRAWDOWN_PCT = 5.591`

`PEAK_TO_FINAL_GIVEBACK_YEN = 27,430`

`TOTAL_COMPLETED_CAMPAIGNS = 152`

`WINNING_CAMPAIGNS = 71`

`LOSING_CAMPAIGNS = 72`

`WIN_RATE = 46.71%`

`TOP_5_WINNER_PNL = 62490 +43,200; 92270 +31,300; 69730 +28,500; 78860 +23,900; 40800 +20,400`

`WORST_5_LOSER_PNL = 21950 -18,670; 21380 -12,700; 65790 -9,700; 44220 -9,100; 96100 -9,000`

`AVOIDABLE_LOSS_YEN = 29,860`

`LEGITIMATE_LOSS_YEN = 166,380`

`SYSTEM_CAUSED_LOSS_YEN = 0`

`WINNER_GIVEBACK_YEN = 199,240`

`WINNER_PROFIT_RETENTION_RATIO = 62.58%`

`CHURN_LOSS_YEN = 183,480`

`ADD_NET_CONTRIBUTION = 0`

`REENTRY_NET_CONTRIBUTION = 0`

`AVERAGE_EXPOSURE = 76.72%`

`AVERAGE_CASH = 254,312`

`REGIME_PNL_TABLE = BULL +107,600; RECOVERY +89,590; RANGE +37,610; CORRECTION -44,570; BEAR -18,650`

`EARLY_FAILURE_DETECTABILITY_TABLE = AT_ENTRY UNRESOLVED; +1BD/+2BD/+3_TO_5BD 49 campaigns / 166,380 loss; LATER 18 campaigns / 29,860 loss; UNRESOLVED 5 campaigns / 9,660 loss`

`PEAK_TO_FINAL_GIVEBACK_DECOMPOSITION = RANGE -17,760; CORRECTION -19,870; BEAR +10,200; NET -27,430`

`TOP_PERFORMANCE_CONSTRAINTS = winner profit giveback; 2-5BD churn loss; regime transition adaptation; incomplete BUY quality lineage`

`EXISTING_FEATURES_SUFFICIENT_FOR_NEXT_DESIGN = PARTIAL`

`NEW_FEATURE_REQUIRED_NOW = NO`

`PRODUCTION_PARAMETER_CHANGE_AUTHORIZED = NO`

`STRATEGY_MUTATION_AUTHORIZED = NO`

`FUTURE_INFORMATION_USED_AS_PRODUCTION_INPUT = NO`

`IMPLEMENTATION_CHANGED = NO`

`FRESH_RUN_EXECUTED = NO`

`RESUME_EXECUTED = NO`

`LONG_HISTORICAL_EXECUTED = NO`

`NEXT_TASK_RECOMMENDATION = design a PIT-safe PM/churn/winner-retention contract; do not tune thresholds on this 100BD window`

