# Phase32-AM — BUY_NEW Early Failure vs Winner PIT Divergence Deep Audit

## Executive Summary

This is a read-only audit of the live Post-AI long Historical fresh-run `runtime-test-historical-extended-smoke-20260827T093649849074Z`. During this audit the latest valuation-ready coverage advanced to `2023-12-04`, so AM uses `2023-09-01` through `2023-12-04` for cohort construction, while preserving the Phase32-AL September-November framing.

Primary conclusion: BUY_NEW early failures are not cleanly separable from BUY_NEW caution winners at T0 using the existing PIT fields. The cohorts overlap heavily on rank, quality score, entry admission state/action, momentum, trend, continuation, downside, and market posture. The first material divergence appears after entry, strongest by T+2BD, when PM weak/reduce evidence and trend deterioration are much more visible in the early-failure cohort.

The likely research direction is therefore not a broad T0 caution-entry ban. It is a mixed Option B/C path: study T+1/T+2 early-failure detection and PM response mechanics, while protecting caution winners from premature cuts.

## Run Identity / Coverage

- Run id: `runtime-test-historical-extended-smoke-20260827T093649849074Z`
- Run root: `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260827T093649849074Z`
- Primary source: `docs/phase_reports/phase32_al_post_ai_sideways_regime_avoidable_loss_and_winner_retention_characterization_audit.md`
- Latest valuation-ready coverage observed for AM: `2023-12-04`
- Campaign lifecycle artifact used: `daily/2023-12-04/positions/position_campaigns.json`
- Primary AM cohort window: BUY_NEW campaigns opened from `2023-09-01` through `2023-12-04`
- Constraints honored: no production/config/schema/threshold/model/runtime-state mutation; no fresh-run, resume, replay, backtest, or run stop.

## Cohort Construction

BUY_NEW campaigns opened in the AM window: `55`.

| Cohort | Definition | Count |
| --- | --- | ---: |
| A. Early Failure | BUY_NEW, closed within 0-5BD, campaign return < 0 | 22 |
| B. Caution Winner Control | BUY_NEW, caution/reduced-only entry, final return > 0 | 26 |
| C. Strong Winner Control | BUY_NEW, stronger full admission/evidence, final return > 0 | 0 |
| Neutral/Other | open, flat, longer loser, or not fitting A/B/C | 7 |

Important artifact finding: all BUY_NEW entries in the AM window are effectively caution/reduced-only in the available PC taxonomy. Even three rows with `HEALTHY_CONTINUATION_ENTRY` still carried `quality_action=REDUCED_ALLOCATION_ONLY`, so there is no clean strong BUY_NEW winner control cohort in this window.

## T0 Separability

T0 separability judgment: `NOT_SEPARABLE`.

T0 numeric distributions:

| Field | Early Failure mean / median / range | Caution Winner mean / median / range |
| --- | --- | --- |
| Rank | 30.59 / 31.0 / 14-45 | 32.08 / 36.5 / 9-45 |
| Runtime opportunity score | -0.400 / -0.432 / -0.546 to -0.238 | -0.440 / -0.438 / -0.710 to -0.096 |
| Quality score | 0.582 / 0.576 / 0.457-0.719 | 0.564 / 0.536 / 0.456-0.754 |
| Risk vote count | 2.50 / 3.0 / 1-4 | 2.04 / 2.0 / 0-4 |
| 1D momentum | 0.017 / 0.005 / -0.057 to 0.125 | 0.037 / 0.019 / -0.055 to 0.225 |
| 5D momentum | 0.030 / -0.016 / -0.296 to 0.688 | 0.056 / -0.001 / -0.131 to 0.893 |
| 20D momentum | 0.309 / 0.320 / -0.258 to 0.874 | 0.260 / 0.238 / -0.357 to 0.874 |
| 5D vs 20D delta | -0.279 / -0.356 / -0.696 to 0.446 | -0.204 / -0.231 / -0.767 to 0.493 |
| MA5/MA20 | 1.130 / 1.135 / 0.950-1.393 | 1.106 / 1.089 / 0.747-1.428 |
| Close/MA20 | 1.140 / 1.120 / 0.905-1.583 | 1.140 / 1.131 / 0.766-1.701 |
| Target weight | 0.063 / 0.034 / 0.012-0.203 | 0.064 / 0.058 / 0.015-0.163 |

T0 categorical overlap:

| Field | Early Failure | Caution Winner |
| --- | --- | --- |
| Entry state | `CONTINUATION_WITH_CAUTION`: 22/22 | `CONTINUATION_WITH_CAUTION`: 23/26, `HEALTHY_CONTINUATION_ENTRY`: 3/26 |
| Entry action | `BUY_NEW_REDUCED_ONLY`: 22/22 | `BUY_NEW_REDUCED_ONLY`: 23/26, `BUY_NEW_ALLOWED`: 3/26 |
| Quality action | `REDUCED_ALLOCATION_ONLY`: 22/22 | `REDUCED_ALLOCATION_ONLY`: 26/26 |
| Quality band | LOW 7, MEDIUM 15 | LOW 15, MEDIUM 10, HIGH 1 |
| Momentum class | `MIXED_OR_UNRESOLVED`: 20, `HEALTHY_CONTINUATION`: 2 | `MIXED_OR_UNRESOLVED`: 21, `HEALTHY_CONTINUATION`: 5 |
| Continuation | PASS 22/22 | PASS 26/26 |
| Downside | PASS 22/22 | PASS 26/26 |

There are weak directional hints, such as early failures having slightly higher risk votes and fewer manageable reversal states. But the overlap is too high to support an evidence-safe T0 production filter from the current artifacts.

## Rank Analysis

Rank is not a separable signal.

Early-failure ranks include:

`14, 14, 16, 18, 19, 19, 24, 27, 27, 29, 30, 32, 36, 37, 37, 38, 39, 41, 42, 44, 45, 45`

Caution-winner ranks include:

`9, 15, 15, 16, 16, 23, 24, 25, 25, 28, 30, 36, 36, 37, 40, 40, 40, 41, 41, 41, 41, 42, 42, 42, 44, 45`

The same rank bands contain both quick failures and winners. Rank may be a correlate, but it is not a sufficient separator.

## +1/+2/+3-5BD Divergence

Mean change from T0:

| Horizon | Cohort | PM warning rate | Rank change | Quality change | 5D momentum change | MA5/MA20 change | Close/MA20 change |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| T+1 | Early Failure | 68.2% | -0.28 | -0.075 | -0.024 | -0.024 | -0.060 |
| T+1 | Caution Winner | 46.2% | -2.05 | -0.078 | +0.013 | -0.003 | -0.005 |
| T+2 | Early Failure | 95.5% | -1.33 | -0.031 | -0.050 | -0.050 | -0.094 |
| T+2 | Caution Winner | 50.0% | -2.09 | -0.067 | -0.014 | -0.010 | -0.039 |
| T+3 | Early Failure | 36.4% | -2.39 | -0.028 | -0.108 | -0.074 | -0.119 |
| T+3 | Caution Winner | 11.5% | -2.62 | -0.048 | -0.017 | -0.014 | -0.039 |
| T+5 | Early Failure | 4.5% | -5.76 | +0.030 | -0.080 | -0.137 | -0.143 |
| T+5 | Caution Winner | 24.0% | -4.37 | -0.023 | -0.049 | -0.022 | -0.047 |

The strongest divergence is T+2BD:

- Early failures show PM warnings on 95.5% of rows.
- Caution winners show PM warnings on 50.0% of rows.
- Early failures show much larger deterioration in close/MA20 and MA5/MA20.
- The difference remains descriptive only; no threshold was selected.

## Named Early-Failure Traces

| Symbol | Open | Close | Return | T0 rank | T0 quality | T0 5D momentum | T0 MA5/MA20 | First warning | Warning-to-close |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 50100 | 2023-09-28 | 2023-10-03 | -15.35% | 29 | 0.579 | +0.600 | 1.393 | 2023-10-02 `REDUCE_BY_REDUCE_SCORE_THRESHOLD` | 1BD |
| 74770 | 2023-10-02 | 2023-10-05 | -13.67% | 24 | 0.611 | +0.063 | 1.253 | 2023-10-04 `REDUCE_BY_WEAK_HOLD_SCORE` | 1BD |
| 43340 | 2023-10-10 | 2023-10-13 | -11.65% | 42 | 0.489 | +0.115 | 1.056 | 2023-10-12 `REDUCE_BY_WEAK_HOLD_SCORE` | 1BD |
| 72680 | 2023-09-20 | 2023-09-22 | -9.75% | 14 | 0.719 | -0.006 | 1.243 | 2023-09-21 `REDUCE_BY_WEAK_HOLD_SCORE` | 1BD |
| 48820 | 2023-09-21 | 2023-09-25 | -8.41% | 45 | 0.491 | +0.688 | 1.295 | 2023-09-25 `EXIT_BY_HARD_STOP` | same-day |
| 75850 | 2023-09-08 | 2023-09-12 | -6.52% | 32 | 0.572 | -0.169 | 1.189 | 2023-09-11 `REDUCE_BY_WEAK_HOLD_SCORE` | 1BD |
| 92460 | 2023-10-06 | 2023-10-11 | -6.20% | 27 | 0.581 | -0.023 | 1.178 | 2023-10-10 `REDUCE_BY_WEAK_HOLD_SCORE` | 1BD |

These examples are not T0-obvious failures. Several entered with positive short/medium momentum and MA ratios above 1.0. They become clearer after entry as PM warning evidence appears.

## Warning Lead Time

For the 22 BUY_NEW early failures:

| Warning-to-close bucket | Count |
| --- | ---: |
| same-day | 1 |
| 1BD | 19 |
| 2BD | 1 |
| 3-5BD | 1 |
| no-warning-before-close | 0 |

PM early warning availability is strong. PM response lag is not the dominant issue: most failures are warned and closed within one business day. The unresolved research question is whether action should occur at first warning or whether that would cut too many winners.

## PM Awareness

The PM layer recognized deterioration in the failure cohort through:

- `REDUCE_BY_WEAK_HOLD_SCORE`
- `REDUCE_BY_REDUCE_SCORE_THRESHOLD`
- `EXIT_BY_HARD_STOP`
- `EXIT_BY_TREND_AND_EDGE_BREAK`
- `peak_drawdown_warning` on related broader cohorts

This separates AM from a pure entry-quality defect. The system usually sees deterioration after entry; the hard part is acting early enough without damaging winner retention.

## Caution-Entry Statistics

All 55 BUY_NEW entries in the AM window were reduced/caution-like under the observed taxonomy.

| Metric | Value |
| --- | ---: |
| Total BUY_NEW caution/reduced-only entries | 55 |
| Winners | 26 |
| Losers | 27 |
| Early failures | 22 |
| Early-failure rate | 40.0% |
| Median campaign return | 0.00% |
| Mean campaign return | -0.04% |

A blanket caution-entry ban would remove both most early failures and most BUY_NEW winners in this period.

## Market / Regime Interaction

Using the available runtime deployment posture:

| Cohort | DEPLOY | BALANCED_DEPLOYMENT |
| --- | ---: | ---: |
| Early Failure | 16 | 6 |
| Caution Winner | 15 | 11 |

Regime interaction is partial. Early failures are not isolated to `BALANCED_DEPLOYMENT`; they also occur during `DEPLOY`. But the whole AM window is a sideways/cautious period with persistent cash optionality, so market/regime context likely amplifies caution-entry fragility.

The requested BULL/RECOVERY/RANGE/CORRECTION/BEAR labels were not exposed as direct daily labels in the scanned portfolio-construction summaries. The report therefore uses the available `deployment_posture` labels.

## Entry vs Exit Diagnosis

Campaign/count diagnosis:

| Diagnosis | Count / Weight | Interpretation |
| --- | ---: | --- |
| `ENTRY_SEPARABLE` | low | T0 features overlap too much for a clean filter |
| `EARLY_POST_ENTRY_SEPARABLE` | high | T+2 warnings and trend deterioration separate failures better |
| `PM_RESPONSE_LAG` | low-to-partial | PM warnings exist, but closes usually follow within 1BD |
| `LEGITIMATE_UNAVOIDABLE_LOSS` | partial | some shocks/fast drops remain hard to avoid without high false positives |
| `MIXED` | primary | early post-entry divergence plus winner-protection tradeoff |

Primary diagnosis: `EARLY_POST_ENTRY_SEPARABLE`.

## Avoided Loss vs Lost Winner Profit

Research-only hypothetical: T0 caution exclusion.

- Avoided early failures: up to `22`.
- Lost caution winners: `26`.
- Lost winner risk includes campaigns such as:
  - `39970`: +5.98%, MFE +22.06%
  - `98760`: +7.69%, MFE +21.46%
  - `71800`: +5.26%, MFE +17.83%
  - `59660`: +6.18%, MFE +12.81%
  - `43910`: +15.10%, MFE +15.10%
  - `44140`: +20.32%, still open at coverage

Research-only hypothetical: T+1/T+2 deterioration response.

- Better avoided-loss potential than T0 exclusion because PM warnings become more concentrated in failures.
- Still high winner contamination: caution winners also show warning signals, including `98120`, `59660`, `43910`, `53800`, `48240`, `75240`, `70930`, `92130`, `31860`, and `23750`.

Therefore the evidence supports studying early post-entry divergence, but only with a winner-control set. A loss-only rule would overstate benefit.

## Winner Protection Risk

Winner controls demonstrate the danger of overreacting to temporary weakness:

| Symbol | Campaign | Return | MFE | Giveback | Entry rank | Warnings in early trace |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| 39970 | `pc-1cb5cf7513ca1a11-39970-0001` | +5.98% | +22.06% | 16.08% | 16 | peak drawdown warning |
| 59660 | `pc-19cb23b260f96c7a-59660-0001` | +6.18% | +12.81% | 6.63% | 40 | peak drawdown warning, weak-hold reduce |
| 43910 | `pc-b97338263e004260-43910-0001` | +15.10% | +15.10% | 5.39% | 25 | repeated peak drawdown warnings |
| 53800 | `pc-bc89eed4f082ebc9-53800-0001` | +4.08% | +8.22% | 4.14% | 9 | weak-hold reduce |
| 31860 | `pc-9b48ba628ca91648-31860-0001` | +6.32% | +6.32% | 0.00% | 44 | weak-hold reduce |

These winners prove that PM warning signals are not automatically sell-now signals. The research problem is calibration of persistence and severity, not existence of warnings.

## REENTRY Comparison

REENTRY is not the AM primary, but the quick REENTRY failures from AL remain visible:

- REENTRY entries in AM window: `6`
- REENTRY early failures: `2`
- REENTRY winners: `2`
- REENTRY losers: `2`

Quick failures:

| Symbol | Open | Close | Return | Entry rank | Entry state |
| --- | --- | --- | ---: | ---: | --- |
| 24020 | 2023-09-06 | 2023-09-08 | -3.59% | 9 | `CONTINUATION_WITH_CAUTION` |
| 89180 | 2023-09-06 | 2023-09-08 | -11.11% | 8 | `HEALTHY_CONTINUATION_ENTRY` |

This is not enough to identify REENTRY as a churn driver. REENTRY also contains large winners in the broader AL window. No REENTRY contract change is recommended.

## Research Options

Preferred research option: `MIXED`, centered on Option B and Option C.

- Option B: T+1/T+2 early failure detector. Best supported by the observed divergence in PM warnings and trend deterioration by T+2.
- Option C: PM REDUCE/EXIT response study. Relevant, but not because of long response lag; rather because first warning is often one day before close, and the question is whether earlier action has positive avoided-loss minus lost-winner-profit value.
- Option D: Regime-aware caution admission. Worth studying because the whole window is sideways/cash-cautious, but current posture labels do not cleanly separate failures from winners.
- Option A: T0 entry-quality refinement. Lower priority because T0 separability is poor.
- Option E: no change. Not preferred; early failure is material enough to research.

## Next Step

Do not change production behavior yet. Build a read-only research matrix that evaluates T+1/T+2 warning persistence and severity against both early failures and caution winners, reporting avoided loss minus lost winner profit. Keep rank and T0 caution labels as descriptive covariates, not hard candidate rules.

## Final Judgments

PHASE32_AM_RUN_ID = runtime-test-historical-extended-smoke-20260827T093649849074Z

PHASE32_AM_COVERAGE_END = 2023-12-04

PHASE32_AM_BUY_NEW_EARLY_FAILURE_TOTAL = 22

PHASE32_AM_CAUTION_WINNER_CONTROL_TOTAL = 26

PHASE32_AM_STRONG_WINNER_CONTROL_TOTAL = 0

PHASE32_AM_T0_SEPARABILITY = NOT_SEPARABLE

PHASE32_AM_EARLIEST_MATERIAL_DIVERGENCE = T+2BD

PHASE32_AM_PM_EARLY_WARNING_AVAILABLE = YES

PHASE32_AM_PM_RESPONSE_LAG_MATERIAL = NO

PHASE32_AM_CAUTION_ENTRY_EARLY_FAILURE_RATE = 40.0%

PHASE32_AM_RANK_IS_SEPARABLE_SIGNAL = NO

PHASE32_AM_REGIME_INTERACTION_MATERIAL = PARTIAL

PHASE32_AM_AVOIDABLE_LOSS_POTENTIAL = MEDIUM

PHASE32_AM_LOST_WINNER_PROFIT_RISK = HIGH

PHASE32_AM_PRIMARY_DIAGNOSIS = EARLY_POST_ENTRY_SEPARABLE

PHASE32_AM_PREFERRED_RESEARCH_OPTION = MIXED

PHASE32_AM_NEW_MANDATORY_DEFECT_FOUND = NO

PHASE32_AM_PRODUCTION_REPAIR_JUSTIFIED_NOW = NO

PHASE32_AM_LONG_RUN_CONTINUE = YES

PHASE32_AM_NEXT_STEP = Read-only T+1/T+2 warning-persistence research matrix with avoided-loss minus lost-winner-profit controls; no production tuning yet.
