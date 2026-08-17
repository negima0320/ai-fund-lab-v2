# Phase30-AJ1 - Candidate AI / Top50 Market PIT Quality Surface Design Audit

Task ID: `Phase30-AJ1`

Boundary:

```text
READ_ONLY_DESIGN_AUDIT
NO_IMPLEMENTATION
NO_CANDIDATE_TOP50_COUNT_CHANGE
NO_THRESHOLD_TUNING
NO_MODEL_RETRAINING
NO_TRAINING_TARGET_CHANGE
NO_HISTORICAL_OUTCOME_FIT
NO_NEW_CANDIDATE_ENGINE
NO_PARALLEL_SELECTION_PATH
NO_RUNTIME_AUTHORITY_CHANGE
```

Evidence:

```text
docs/phase_reports/phase30_aj0_post_ai_12bd_action_effectiveness_candidate_coverage_audit.md
docs/phase_reports/phase30_ai_selection_quality_opportunity_capture_repair_implementation_and_legacy_retirement.md
docs/phase_reports/phase30_ah_selection_quality_opportunity_capture_repair_design.md
docs/phase_reports/phase30_ag_selection_coverage_capital_utilization_design_audit.md
docs/phase_reports/phase30_af_60bd_selection_winner_capital_regime_attribution_audit.md
docs/03_ai_design/candidate_ai_design.md
docs/03_ai_design/candidate_training_data_design.md
docs/03_ai_design/candidate_feature_catalog.md
src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py
src/ai_fund_lab_v2/candidate_ai/formal_inference.py
src/ai_fund_lab_v2/candidate_ai/feature_builder.py
```

Generated design evidence:

```text
reports/phase_reports/phase30_aj1_candidate_ai_top50_market_pit_quality_surface_design_audit.json
reports/phase_reports/phase30_aj1/candidate_feature_inventory.json
reports/phase_reports/phase30_aj1/downstream_quality_timing.json
reports/phase_reports/phase30_aj1/top50_quality_mismatch.json
reports/phase_reports/phase30_aj1/candidate_objective_alignment.json
reports/phase_reports/phase30_aj1/option_comparison.json
```

## Primary Judgment

```text
PHASE30_AJ1_CANDIDATE_QUALITY_SURFACE_DESIGN = COMPLETE
CANDIDATE_OBJECTIVE_ALIGNMENT = PARTIAL
CANDIDATE_STAGE_QUALITY_EVIDENCE_SUFFICIENCY = PARTIAL
DOWNSTREAM_QUALITY_SAFE_TO_SURFACE_UPSTREAM = PARTIAL
CANDIDATE_TOP50_QUALITY_REPAIR_AVAILABLE_WITH_EXISTING_DATA = YES
MODEL_RETRAINING_REQUIRED = NOT_YET
NEW_AI_REQUIRED = NO
PARALLEL_CANDIDATE_PATH_REQUIRED = NO
```

Recommended design:

```text
Option C - Hybrid
```

Keep the existing Candidate AI / Top50 authority and Top50 count. Add a
Candidate-stage PIT quality surface using existing Candidate-stage features,
then pass the resulting Top50 into the existing Phase30-AI Selection Quality
Comparator.

Do not move the full Strategy Intelligence comparator into Candidate selection.
Do not create a parallel Candidate path.

## Candidate AI Current Purpose

Durable Candidate AI documents define Candidate AI as:

```text
upward-momentum candidate discovery
all stocks -> about 50 names worth inspecting
not a buy decision
not expected-value ranking
not position sizing
not portfolio authority
```

The Candidate AI design question is:

```text
Which symbols show upward momentum / rising-market attention?
```

It is not:

```text
Which symbols should be bought?
Which symbols have the best expected return?
Which symbols are continuation-quality winners?
```

Runtime Production consumes Candidate output through:

```text
Market feature artifacts
-> Candidate score/rank Top50
-> Opportunity AI
-> Strategy Intelligence
-> Portfolio Construction
-> Position Sizing
-> Runtime Planning
```

## Candidate Score Semantics

The current accepted Candidate model feature order is:

```text
feature__liquidity_avg_volume_20d
feature__missing_flags_insufficient_history
feature__missing_flags_price
feature__missing_flags_volume
feature__price_momentum_return_20d
feature__price_momentum_return_5d
feature__price_momentum_return_60d
feature__trend_close_over_ma_20d
feature__trend_ma_20_60_ratio
feature__trend_ma_5_20_ratio
feature__volatility_return_std_20d
feature__volume_momentum_ratio_1d_20d
feature__volume_momentum_ratio_5d
```

Training target:

```text
label__momentum_candidate_label
= top_decile_20d AND NOT downside_bad_20d
```

Inference / ranking semantics:

```text
candidate_score = accepted-generation model score / calibrated-probability-style output
candidate_rank = candidate_score descending, then code ascending
Top50 = first 50 eligible rows by that ordering
```

Therefore:

```text
Candidate score means similarity to the trained upward-momentum label.
It does not mean current Strategy continuation quality.
It does not mean BUY authority.
It does not mean calibrated expected edge.
```

Alignment with current Strategy is partial. The label has a downside component,
but it does not directly encode Entry Admission, Continuation Quality,
Relative Strength, Downside Risk rollups, campaign lifecycle, ADD-worthiness,
opportunity cost, PC target competition, PS feasibility, or Runtime execution.

## Candidate Stage Feature Inventory

| Evidence | Classification | Notes |
|---|---|---|
| 5D / 20D / 60D price return | `AVAILABLE_AND_USED` | In accepted feature order. |
| close / MA20, MA5 / MA20, MA20 / MA60 | `AVAILABLE_AND_USED` | In accepted feature order. |
| acceleration / deceleration | `AVAILABLE_BUT_UNDERUSED` | Candidate features contain momentum deltas, but accepted feature order does not use them. |
| volume momentum | `AVAILABLE_AND_USED` | 5D and 1D/20D volume ratios used. |
| participation / traded value | `AVAILABLE_BUT_UNDERUSED` | `rolling_median_traded_value_20` exists and SI uses participation evidence, but accepted Candidate feature order omits it. |
| liquidity | `AVAILABLE_AND_USED` | Average volume used. |
| volatility | `AVAILABLE_AND_USED` | 20D return volatility used. |
| market regime | `AVAILABLE_NOT_USED` | PIT regime exists downstream; no accepted Candidate `market_regime_*` feature. |
| sector information | `NOT_AVAILABLE_AT_CANDIDATE_STAGE` | SI declares sector relative authority gaps. |
| Candidate model score/rank | `AVAILABLE_AND_USED` | Current dominant Top50 authority. |

Conclusion:

```text
CANDIDATE_STAGE_QUALITY_EVIDENCE_SUFFICIENCY = PARTIAL
```

There is enough PIT data for a lightweight Candidate-stage quality surface, but
not enough to reproduce full downstream Strategy Intelligence before Candidate
selection.

## Downstream Quality Timing

| Evidence | Current Producer | Candidate-pre calculable? | Classification |
|---|---|---|---|
| Continuation Quality | Strategy Intelligence | Partial | `REQUIRES_ARCHITECTURE_MOVE` |
| Relative Strength | Strategy Intelligence | Stock-vs-market partial; sector gap remains | `PARTIAL` |
| Downside Risk | Strategy Intelligence | Cheap volatility/exhaustion partial | `REQUIRES_ARCHITECTURE_MOVE` |
| Entry Admission | Strategy Intelligence / Entry Admission | Cheap timing partial; full action semantics downstream | `REQUIRES_ARCHITECTURE_MOVE` |
| Selection Quality Comparator | Strategy Intelligence | No, as full comparator | `MUST_REMAIN_DOWNSTREAM` |

```text
DOWNSTREAM_QUALITY_SAFE_TO_SURFACE_UPSTREAM = PARTIAL
```

Safe upstream surface means only shared PIT components such as trend structure,
acceleration, volatility, participation, liquidity, and stock-vs-market
relative strength. Full CQ / Risk / Entry / Comparator semantics should remain
downstream unless their producer is deliberately moved into a shared
market-wide evidence component.

## Why Top50 Is Mostly Caution

AJ0 12BD authority:

```text
HIGH_QUALITY_CONTINUATION = 6
VALID_CONTINUATION = 0
CAUTION_CONTINUATION = 563
REJECT = 32
```

AJ0 market-healthy benchmark:

```text
market_healthy_proxy_count_avg = 460.250 / day
candidate_healthy_proxy_count_avg = 10.417 / day
candidate_capture_ratio_avg = 2.3465%
total_market_healthy_proxy_count = 5,523
total_candidate_healthy_proxy_count = 125
total_missed_healthy_proxy_count = 5,398
```

Dominant Top50 caution evidence in the 12BD window:

| Evidence | Count |
|---|---:|
| `selection_quality_caution_continuation` | 504 |
| `entry_state=CONTINUATION_WITH_CAUTION` | 483 |
| `entry_action=BUY_NEW_REDUCED_ONLY` | 427 |
| `volatility_risk=OBSERVED` | 421 |
| `participation_quality=WEAK` | 404 |
| `trend_health=SUPPORTIVE` | 316 |
| `acceleration_state=MIXED` | 310 |
| `persistence=MIXED` | 274 |
| `exhaustion_risk=ELEVATED_RISK` | 225 |
| `reversal_risk=ELEVATED_RISK` | 225 |

Root causes:

```text
WHY_TOP50_IS_MOSTLY_CAUTION =
1. Candidate score/rank is optimized for momentum_candidate_label, not downstream continuation quality tier.
2. Accepted Candidate feature_order omits acceleration/deceleration fields used downstream.
3. Accepted Candidate feature_order omits PIT regime and sector-relative authority.
4. Top50 is score-dominant, so many PIT-healthy names rank below 50.
5. Phase30-AI comparator is post-Candidate and cannot admit missed market-healthy names.
```

## Market Healthy Proxy Misses

The AJ0 benchmark shows the main gap:

```text
Top50 quality issue is not Candidate count.
It is which 50 names are admitted.
```

A score-all diagnostic using the accepted Candidate feature order confirms the
same direction: strict PIT-healthy proxy names outside Top50 had much lower
Candidate scores and ranks despite positive trend structure.

| Metric | Top50 mean | Missed healthy mean |
|---|---:|---:|
| candidate_score | 0.602113 | 0.213345 |
| candidate_rank | 25.500000 | 2,139.681586 |
| 5D return | 0.029925 | 0.040013 |
| 20D return | 0.141426 | 0.037620 |
| 60D return | 0.443427 | 0.070356 |
| 5D vs 20D delta | -0.111501 | 0.002392 |
| close / MA20 | 1.039058 | 1.032226 |
| MA5 / MA20 | 1.022245 | 1.018280 |
| volume ratio 5D | 0.933919 | 1.186366 |
| volume ratio 1D/20D | 1.010959 | 1.305977 |
| volatility 20D | 0.070003 | 0.014306 |

Interpretation:

- Top50 is biased toward stronger prior 20D/60D momentum and higher volatility.
- Missed healthy names often have cleaner short-term acceleration and lower
  volatility, but lower Candidate score.
- This matches the downstream CAUTION diagnosis: the model can surface names
  with strong prior momentum that are later judged reduced-only, mixed,
  overheated, or participation-weak.

This diagnostic did not use future returns.

## Candidate Objective Alignment

```text
CANDIDATE_OBJECTIVE_ALIGNMENT = PARTIAL
```

Aligned:

- Candidate AI seeks upward-momentum candidates.
- The label avoids some downside-bad cases.
- Runtime PIT leakage safeguards are present.
- Top50 count and authority are clear.

Not fully aligned:

- Current Strategy wants sustainable continuation, not just prior momentum.
- Current Strategy needs entry timing, acceleration, downside containment,
  relative strength, and lifecycle interpretation.
- Candidate score is not calibrated expected edge and is not a continuation
  quality tier.
- Downstream comparator cannot fix names excluded before Candidate Top50.

## Option A / B / C Comparison

| Option | Expected Improvement | Data | Authority Impact | Risk | Judgment |
|---|---|---|---|---|---|
| A - Candidate-stage existing features only | Medium | High | Low | Medium | Useful but incomplete |
| B - Downstream evidence upstream materialization | High if done | Partial | High | High | Not primary for AJ2 |
| C - Hybrid | High | High for cheap screen, partial for full SI | Medium controlled | Medium | Recommended |

## Recommended Design

```text
RECOMMENDED_OPTION = Option C - Hybrid
```

Design:

```text
Market
-> Candidate AI score/rank
-> Candidate-stage PIT quality surface
-> Quality-aware Top50, still count=50
-> Phase30-AI Selection Quality Comparator
-> PC
-> PS
-> Runtime
```

Candidate-stage quality surface should use only existing PIT features already
available before Candidate selection:

- trend structure;
- MA structure;
- acceleration / deceleration;
- participation / traded-value confirmation;
- volatility / exhaustion proxy;
- liquidity;
- stock-vs-market relative strength if safely available.

It must not:

- use future returns;
- tune thresholds from Historical outcome;
- change Top50 count;
- create a new Candidate engine;
- bypass Candidate AI authority;
- duplicate the full Selection Quality Comparator;
- force BUYs or exposure.

## Existing Logic Retirement

| Logic | Classification | Notes |
|---|---|---|
| candidate score dominance | `MODIFY` | Keep score, but prevent it from being the sole Top50 ordering surface when PIT quality contradicts. |
| candidate rank dominance | `MODIFY` | Keep rank as evidence; add quality-aware ordering before Top50 cut. |
| high candidate score reason | `KEEP` | Continue as metadata, not BUY authority. |
| volume momentum reason | `KEEP` | Preserve as explainability. |
| ranking fallback | `DEPRECATE_DURING_MIGRATION` | Avoid score-only fallback where quality fields are available. |
| duplicated quality prefilter | `REMOVE_AFTER_MIGRATION` | Do not introduce a duplicate SI comparator or parallel quality engine. |

## Interaction With Phase30-AI

Phase30-AI remains preserved.

Role split:

```text
Candidate stage = broad market surface authority
Phase30-AI comparator = within-Candidate quality comparison evidence
PC = target portfolio authority
PS = quantity authority
Runtime = pure mapper
```

Candidate-stage surface should improve the 50 names admitted to SI. Phase30-AI
then evaluates those names with richer downstream evidence.

## Capital Utilization Expected Effect

Expected effect if AJ2 implements Option C correctly:

- higher HIGH / VALID candidate count inside Top50;
- fewer Top10 `REJECT` / `CAUTION_CONTINUATION` rows;
- more PC-positive quality opportunities when PIT evidence supports them;
- more PS-positive executable opportunities only when lot/capital constraints
  permit;
- lower unjustified cash caused by missed quality opportunities;
- cash remains justified when quality, risk, opportunity cost, PS, Runtime, or
  Safety evidence says no.

Forbidden:

```text
minimum exposure
minimum BUY count
cash cap
forced residual deployment
Historical winner-fitting
```

## Production Integrity

```text
PHASE30_AI_SELECTION_COMPARATOR_PRESERVED = YES
PHASE30_AE1_ADD_CONVERSION_PRESERVED = YES
PHASE30_W_ENTRY_ADMISSION_PRESERVED = YES
PHASE30_Z_REENTRY_PRESERVED = YES
ONE_PRODUCTION_SELECTION_PATH = YES
```

## Leakage

```text
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_AS_RUNTIME_INPUT = FALSE
HISTORICAL_OUTCOME_USED_FOR_PRODUCTION_PARAMETER_SELECTION = FALSE
TEST_RESULT_USED_AS_STRATEGY_INPUT = FALSE
```

## New AI / Model Retraining

```text
NEW_AI_REQUIRED = NO
PARALLEL_CANDIDATE_PATH_REQUIRED = NO
MODEL_RETRAINING_REQUIRED = NOT_YET
```

AJ2 should first repair the Candidate Top50 PIT quality surface with existing
data and existing authority. Model retraining or label redesign would require a
separate evidence phase after PIT-surface repair is validated.

## Implementation Authorization

```text
NO IMPLEMENTATION AUTHORIZED BY_PHASE30-AJ1
```

## Recommended Next Task

```text
Phase30-AJ2 - Candidate Top50 PIT Quality Surface Repair Implementation and Legacy Retirement
```
