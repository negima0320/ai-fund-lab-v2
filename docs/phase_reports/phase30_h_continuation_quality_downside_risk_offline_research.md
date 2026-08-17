# Phase30-H — Continuation Quality / Downside Risk Offline Research

## Task ID

`Phase30-H`

## Status

```text
COMPLETE
READ-ONLY OFFLINE STRATEGY RESEARCH
NO TARGET RUN MUTATION
NO STRATEGY / RUNTIME / CONFIG / MODEL / THRESHOLD CHANGE
NO BUY QUALITY / BUY_WAIT / ADD / HOLD / REDUCE / EXIT CHANGE
NO HISTORICAL RESUME / FRESH-RUN / REPAIR
NO IMPLEMENTATION AUTHORIZED BY PHASE30_H
```

## Primary Judgment

```text
PHASE30_H_CONTINUATION_QUALITY_DOWNSIDE_RISK_PIT_SEPARATION_CONFIRMED_INTERPRETABLE_DIMENSION_DESIGN_READY
```

Using only information knowable at the decision time, AI Fund Lab v2 has strong evidence that it can learn to avoid a meaningful share of large losers while still identifying and concentrating capital into later strong Winners. The evidence does not support a blunt rejection of all risky names. It supports a redesign that separates Continuation Quality, Downside Risk, and Expected Edge into interpretable dimensions with explicit winner-preservation constraints.

## Dataset

Research boundary:

```text
Run ID: runtime-test-historical-extended-smoke-20260815T061857447380Z
Clean period: 2022-08-10 -> 2023-10-26
Completed business days: 299
Failed 2023-10-27 valuation candidate: EXCLUDED
```

Offline dataset:

```text
Rows: 14,950
Symbols: 635
Dates: 299
Selected BUYs: 219
BUY_NEW: 104
BUY_ADD: 33
REENTRY: 82
BUY_WAIT: 3,345
candidate_not_selected: 11,386
PIT integrity: PIT_FEATURES_ONLY_OUTCOME_LABELS_FUTURE_ONLY_RESEARCH
```

Future labels were used only as offline research outcomes: 20BD return, MFE, MAE, severe-loss flags, healthy-winner flags, and missed-winner flags. No production Strategy authority, runtime artifact, threshold, config, Safety gate, or target run artifact was changed.

Machine-readable artifacts:

```text
reports/phase_reports/phase30_h_continuation_quality_downside_risk_offline_research.json
reports/phase_reports/phase30_h/dataset_manifest.json
reports/phase_reports/phase30_h/continuation_feature_results.json
reports/phase_reports/phase30_h/downside_feature_results.json
reports/phase_reports/phase30_h/temporal_validation.json
reports/phase_reports/phase30_h/regime_validation.json
reports/phase_reports/phase30_h/winner_signature.json
reports/phase_reports/phase30_h/failure_signature.json
reports/phase_reports/phase30_h/add_research.json
reports/phase_reports/phase30_h/reentry_research.json
reports/phase_reports/phase30_h/missed_winner_analysis.json
reports/phase_reports/phase30_h/candidate_vs_selected.json
reports/phase_reports/phase30_h/winner_preservation_tradeoff.json
reports/phase_reports/phase30_h/research_dataset_sample.json
```

## Continuation Quality Evidence

Current BUY Quality and rank authority are not enough:

```text
BUY Quality HIGH: count 1,495, mean 20BD return -4.47%, win 36.17%, severe <= -5% 42.41%
BUY Quality LOW:  count 2,226, mean 20BD return +0.07%, win 43.21%, severe <= -5% 38.69%
Rank 1:           count 299, mean 20BD return +0.72%, win 58.06%, severe <= -5% 13.98%
Rank 6-10:        count 1,495, mean 20BD return -4.23%, severe <= -5% 45.08%
```

Rank 1 contains useful signal, but the current aggregate BUY Quality band does not reliably separate future Winners from dangerous stocks. Strong raw 20D momentum alone is actively hazardous in this clean sample:

```text
Strong 20D momentum: count 2,990, mean 20BD return -3.44%, median -6.30%, severe <= -5% 52.67%
Not strong 20D:      count 11,960, mean 20BD return -0.11%, severe <= -5% 37.86%
```

The useful continuation evidence is not "momentum is high"; it is whether the move is still structurally healthy. A research-only Continuation Quality / Downside Risk quadrant separated selected BUY outcomes materially:

```text
Selected LOW_CQ_HIGH_RISK: count 157, mean -2.76%, median -3.88%, win 34.64%, severe 49.02%, median MAE -15.55%
Selected kept ex-LOW_CQ_HIGH_RISK: count 62, mean +5.40%, median +1.38%, win 57.38%, severe 18.03%, median MAE -3.70%
Selected HIGH_CQ_LOW_RISK: count 11, mean +0.96%, win 54.55%, severe 27.27%
Selected MIXED_CQ_RISK: count 26, mean +9.74%, win 56.00%, severe 20.00%, median MFE +22.67%
```

This confirms that Continuation Quality is real, but it must be represented as multiple dimensions. A single "healthy / mixed" label or a blunt risk veto would miss too many optionality winners.

## Downside Risk Evidence

The research-only downside flag separated adverse outcomes, especially among selected BUYs and BUY_NEW:

```text
Selected downside_high=False: count 27, mean +1.00%, win 59.26%, severe 18.52%, median MAE -1.59%
Selected downside_high=True:  count 192, mean -0.64%, win 38.50%, severe 43.32%, median MAE -13.67%

BUY_NEW downside_high=False: count 14, mean +0.69%, win 57.14%, severe 28.57%, median MAE -4.66%
BUY_NEW downside_high=True:  count 90, mean -4.50%, win 35.63%, severe 52.87%, median MAE -16.56%
```

The strongest narrow failure signature was strong prior momentum followed by short-term reversal:

```text
Flagged selected BUYs: count 47, mean -4.63%, median -14.80%, severe 69.57%, median MAE -23.19%
Kept selected BUYs:    count 172, mean +0.72%, median 0.00%, severe 32.14%, median MAE -7.14%
Severe losers caught: 37.21%
Healthy winners lost: 18.87%
```

High volatility alone catches more severe losers but sacrifices too many winners:

```text
avoid_high_volatility catches 80.23% of severe selected losers,
but also removes 73.58% of healthy selected winners.
```

## Healthy Winner Signature

Research-only healthy Winners tend to share:

```text
HEALTHY_CONTINUATION or persistent positive short/medium structure
close above MA20 and supportive MA5/MA20
no strong-prior short-term reversal
volatility not extreme
controlled MAE before MFE expansion
often not the highest raw 20D momentum
```

Important caveat: strong Winners also appear inside `MIXED_CQ_RISK` and even `LOW_CQ_HIGH_RISK`. The winner signature is therefore a positive scoring representation, not a hard whitelist.

## Failure Signature

Research-only high failure risk is concentrated around:

```text
MIXED / FADING / OVERHEAT trajectory plus high volatility or weak volume
strong 20D prior momentum with negative 1D / 3D reversal
extreme volatility expansion
low price / high tick sensitivity when combined with other risk
event-risk uncertainty where source coverage is partial
```

The evidence supports treating this as a probabilistic downside-risk dimension and as a narrow veto candidate only when multiple failure dimensions agree.

## Temporal Robustness

Temporal split date:

```text
mid_date: 2023-03-22
```

Downside risk separation survived both halves:

```text
Early downside_high=False: mean +1.33%, severe 35.96%, median MAE -7.94%
Early downside_high=True:  mean +0.02%, severe 40.13%, median MAE -9.51%
Later downside_high=False: mean -1.23%, severe 38.48%, median MAE -9.05%
Later downside_high=True:  mean -2.36%, severe 44.29%, median MAE -10.88%
```

Quadrant results also remained directionally useful: `LOW_CQ_HIGH_RISK` remained worse than cleaner alternatives in both early and later segments, with stronger selected-BUY degradation in the later segment. Temporal robustness is `PARTIAL_TO_GOOD`; this is enough for design research, not enough for production thresholds.

## Regime Robustness

Regime results are supportive but not uniform:

```text
BULL LOW_CQ_HIGH_RISK: mean -2.29%, severe 45.97%, median MAE -10.77%
BULL HIGH_CQ_LOW_RISK: mean +0.09%, severe 38.24%, median MAE -8.41%

RANGE LOW_CQ_HIGH_RISK: mean -0.94%, severe 40.20%
RANGE HIGH_CQ_LOW_RISK: mean +1.78%, win 54.17%, severe 37.50%

RECOVERY LOW_CQ_HIGH_RISK: mean -0.81%, severe 40.26%
```

BEAR and CORRECTION regimes are noisier and sometimes reward risk-taking because rebound optionality dominates static downside labels. The redesign should therefore include regime-conditioned interpretation rather than universal cutoffs.

## Winner Preservation Trade-off

Blunt risk avoidance is not acceptable:

```text
avoid_downside_high_research_flag:
  severe selected losers caught: 94.19%
  healthy selected winners lost: 94.34%

avoid_low_cq_high_risk_quadrant:
  severe selected losers caught: 87.21%
  healthy selected winners lost: 62.26%

avoid_high_volatility:
  severe selected losers caught: 80.23%
  healthy selected winners lost: 73.58%
```

The best candidate for a narrow failure signature is:

```text
avoid_strong_momentum_short_reversal:
  severe selected losers caught: 37.21%
  healthy selected winners lost: 18.87%
```

This is the clearest answer to the central research question: yes, PIT data can avoid a meaningful share of large losers while preserving most Winners, but only through targeted failure signatures and positive continuation scoring, not through broad risk rejection.

## BUY_NEW

BUY_NEW is the most urgent redesign surface:

```text
BUY_NEW selected total: 104
BUY_NEW LOW_CQ_HIGH_RISK: count 80, mean -5.39%, median -11.27%, win 33.77%, severe 55.84%, median MAE -17.07%
BUY_NEW LOW_CQ_LOW_RISK:  count 8, mean +0.47%, win 62.50%, severe 12.50%
BUY_NEW MIXED_CQ_RISK:    count 6, mean +6.92%, win 66.67%, median MFE +26.58%
```

Current BUY_NEW selection is not merely accepting risk; it is over-concentrating in poor continuation / high downside setups while still missing higher-quality optionality elsewhere.

## ADD

ADD evidence is mixed and sample-limited, but directionally useful:

```text
ADD total: count 33, mean -2.23%, win 48.39%, severe 12.90%, median MAE -3.70%
ADD downside_high=False: count 6, mean +2.35%, win 66.67%, severe 0.00%
ADD downside_high=True:  count 27, mean -3.32%, win 44.00%, severe 16.00%
ADD HEALTHY_CONTINUATION: count 12, mean +4.39%, severe 0.00%
ADD MIXED_OR_UNRESOLVED: count 18, mean -5.05%, severe 16.67%
```

ADD should be researched as incremental continuation confirmation, not as an automatic extension of an existing position.

## REENTRY

REENTRY is not a blanket failure mode:

```text
REENTRY total: count 82, mean +4.37%, win 41.46%, severe 39.02%, median MFE +12.90%, median MAE -10.81%
REENTRY HEALTHY_CONTINUATION: count 18, mean +12.82%, win 61.11%, severe 16.67%, median MAE -1.65%
REENTRY MIXED_OR_UNRESOLVED: count 64, mean +2.00%, win 35.94%, severe 45.31%, median MAE -13.46%
```

REENTRY needs a recovery-vs-churn distinction. Healthy reentry can be high-value; unresolved reentry carries material downside and giveback risk.

## HOLD / SELL Implication

The same dimensions should inform HOLD / SELL research, but they should not directly replace Portfolio Manager authority. The implication is architectural: Continuation Quality deterioration, reversal after strong prior momentum, volatility expansion, weak participation, and regime stress should become shared evidence available to BUY_NEW, ADD, HOLD, REDUCE, and EXIT reasoning.

## Candidate vs Selected

Current BUY_NEW selection is worse than the eligible unselected universe on realized 20BD return, while selecting higher optionality:

```text
Selected BUY_NEW:        count 104, mean -3.78%, median -4.00%, win 38.61%, severe 49.50%, median MAE -15.55%, median MFE +9.86%
Eligible not selected:   count 9,016, mean -1.07%, median -1.68%, win 40.50%, severe 39.91%, median MAE -9.42%, median MFE +9.49%
Per-day selected minus nonselected 20BD return: -4.21 percentage points
Per-day selected minus nonselected MFE20:       +3.63 percentage points
```

This indicates the current selector finds optionality, but pays too much downside and converts too little of that optionality into realized forward return.

## Missed Winners

There are substantial missed Winners in the clean candidate universe:

```text
missed_count: 1,532
```

Examples include:

```text
65730 on 2023-08-09: not selected, LOW_CQ_HIGH_RISK, ret20 +408.90%, MFE +465.13%
59350 on 2023-03-17: not selected, MIXED_CQ_RISK, ret20 +130.24%, MFE +241.94%
92270 on 2022-10-25: not selected, HIGH_CQ_LOW_RISK, ret20 +125.61%, MFE +170.47%
68980 / 66960 / 21340: multiple not-selected high-MFE cases, many in LOW_CQ_HIGH_RISK
```

This is why the recommendation is not "reject LOW_CQ_HIGH_RISK." The redesign must preserve upside optionality while forcing risk-adjusted expected edge and position authority to understand failure probability.

## Continuation Quality Representation Recommendation

Represent Continuation Quality as interpretable dimensions:

```text
Trend Health
Persistence
Acceleration / Deceleration
Exhaustion / Reversal
Participation / Volume Confirmation
Relative Strength
Regime Compatibility
```

`momentum_trajectory_quality` should not remain a zero-weight informational tag in future design research. However, Phase30-H does not authorize assigning any production weight.

## Downside Risk Representation Recommendation

Separate hard facts from probabilistic risk:

```text
DISQUALIFYING_FACT:
  authoritative data failure
  corporate-action / valuation integrity issue
  hard liquidity or tradability block
  explicit Strategy safety violation

PROBABILISTIC_RISK:
  reversal after strong prior momentum
  volatility expansion
  weak participation
  microstructure / low-price fragility
  regime stress
  unresolved event risk
```

The first class can block. The second class should feed expected edge, sizing, ADD eligibility, and HOLD / SELL urgency research.

## Expected Edge Implication

Expected Edge research is now justified. A future design should reason in the form:

```text
Expected Edge =
  Continuation Opportunity
  x Payoff Potential
  - Downside Risk
  - Opportunity Cost
```

This must be designed as an interpretable evidence contract before production implementation.

## Can PIT Data Materially Improve Strategy?

```text
STRONG_EVIDENCE
```

## Strategy Redesign Evidence

```text
REDESIGN_EVIDENCE_STRONG
```

## Implementation Authorization

```text
NO IMPLEMENTATION AUTHORIZED BY PHASE30_H
```

## Recommended Next Task

```text
Phase30-I — Continuation Quality / Downside Risk Strategy Design
```

