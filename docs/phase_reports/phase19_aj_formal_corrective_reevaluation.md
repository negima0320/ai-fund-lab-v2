# Phase19-AJ — Formal Corrective Re-evaluation

## Final Judgment

```text
PHASE19_AJ_CORRECTIVE_REEVALUATION_COMPLETE
PHASE19_AK_REVIEW_READY
```

Forbidden declarations were not made:

```text
UNIFIED_GENERATION_CREATED
ACCEPTED_GENERATION_CREATED
RUNTIME_READY
BUY_READY
```

## Candidate Re-evaluation

Result:

```text
CORRECTIVE_REEVALUATION_PASS
```

Test window:

```text
classification = CORRECTIVE_REEVALUATION
sample_count = 165028
business_days = 39
positive_count = 15964
negative_count = 149064
```

Metrics:

```text
ROC-AUC = 0.6152783698517283
PR-AUC = 0.13569431649867195
class_prior = 0.09673509949826696
Brier = 0.08706860657893768
LogLoss = 0.31475352809279716
ECE = 0.006901105624084435
finite_ratio = 1.0
collapse = false
```

Corrective checks:

```text
minimum_test_rows = PASS
minimum_test_business_days = PASS
finite/range/collapse/class coverage = PASS
ROC-AUC above random = PASS
PR-AUC above class prior = PASS
```

The legacy formal validator still records top-level lifecycle label floors as unscoped for a single test window. AJ does not reinterpret those floors as test-window label floors.

## Opportunity Global

Gate:

```text
OPPORTUNITY_GLOBAL_QUALITY_GATE_V1
```

Result:

```text
PASS
qualitative_predictive_status = NON_DESTRUCTIVE_BUT_WEAK
```

Safety / sanity checks:

```text
finite_ratio = 1.0
NaN = 0
Inf = 0
collapse = false
explosion = false
ordering_preservation = true
calibration_status = PASS
binding = PASS
```

Predictive diagnostics:

```text
Pearson = -0.013346777729190233
Spearman = -0.023113834309422397
MAE = 0.6983658381596776
RMSE = 0.8608991989523957
directional_accuracy = 0.49948453608247423
prediction_to_target_scale_ratio = 2.8096240917342885
```

Baseline diagnostics remain weak:

```text
model_beats_zero = false
model_beats_mean = false
model_beats_median = false
```

Global PASS here means Safety / Sanity PASS, not strong standalone global predictive quality.

## Opportunity Selection

Gate:

```text
OPPORTUNITY_SELECTION_UTILITY_GATE_V1
```

Result:

```text
PASS
qualitative_selection_status = CONSISTENT_SELECTION_UTILITY_WITH_WEAK_RANK_CORRELATION
```

Candidate-passed Universe:

```text
CandidateTop50
sample_count = 1940
business_days = 39
candidate_rank_min = 1
candidate_rank_max = 50
```

CandidateTop50 average realized return:

```text
0.05086912680412372
```

Top5:

```text
selected_count = 195
mean_return = 0.1225475794871795
median_return = 0.032869
hit_rate = 0.5487179487179488
downside_rate = 0.4256410256410256
lift_vs_CandidateTop50 = 0.07167845268305578
top_minus_bottom = 0.13808531282051284
```

Top10:

```text
selected_count = 390
mean_return = 0.08295158461538461
median_return = 0.006246
hit_rate = 0.5076923076923077
downside_rate = 0.48205128205128206
lift_vs_CandidateTop50 = 0.032082457811260894
top_minus_bottom = 0.07872221538461538
```

Top20:

```text
selected_count = 780
mean_return = 0.08722251538461537
median_return = -0.007455
hit_rate = 0.4846153846153846
downside_rate = 0.4897435897435897
lift_vs_CandidateTop50 = 0.03635338858049165
top_minus_bottom = 0.0709280987179487
```

Ranking diagnostics:

```text
Spearman within Candidate-passed Universe = -0.03406935897352299
```

The Selection Gate passes because Top5 / Top10 / Top20 all show positive mean realized returns and positive lift over CandidateTop50. The weak negative Spearman is retained as a review risk.

## Dual Gate

Decision:

```text
DUAL_GATE_CORRECTIVE_PASS
```

Inputs:

```text
Global Gate = PASS
Selection Gate = PASS
Candidate corrective status = CORRECTIVE_REEVALUATION_PASS
```

Generation eligibility evidence:

```text
candidate_generation_eligibility = true
opportunity_generation_eligibility = true
combined_generation_eligibility = true
```

This does not create Unified Generation or Accepted Generation.

## Candidate Population

Candidate binding validation:

```text
PASS
```

Bound fields:

```text
candidate_source_artifact_id
candidate_source_content_hash
candidate_model_artifact_id
candidate_calibration_artifact_id
candidate_score_field
candidate_pass_rule
per_day_population_limit
business_day_grouping
selected_rows_hash
```

Candidate rows were not rebuilt from Opportunity score, latest paths, mtime, or manual CSV insertion.

## Runtime Separation

Runtime separation validation:

```text
PASS
```

Static audit:

```text
src/ai_fund_lab_v2/runtime_v2
findings = []
```

Runtime remains prohibited from:

```text
reading Dual Gate evidence
executing Global / Selection Gate
suppressing BUY due to Gate disagreement
```

## Regression

```text
py_compile = PASS
pytest = 13 passed
Schema = PASS
Hash = PASS
Binding = PASS
Runtime Guard = PASS
```

Test command:

```text
PYTHONPATH=src python3 -m pytest tests/ai_lifecycle/test_phase19_ah_dual_gate.py tests/ai_lifecycle/test_phase19_ad_u5_formal_validation.py
```

## Non-mutation

PASS.

```text
Training = 0
Calibration refit = 0
Feature change = 0
Model change = 0
Target change = 0
Policy change = 0
recent_holdout access = 0
Unified Generation = 0
Accepted Generation = 0
Runtime transition = 0
Broker write = 0
Ledger mutation = 0
```

## Evidence

```text
docs/phase_reports/phase19_aj_formal_corrective_reevaluation.md
reports/phase_reports/phase19_aj_formal_corrective_reevaluation.json
reports/phase19_aj_formal_corrective_reevaluation/
```

Required evidence:

```text
candidate_corrective_results.json
opportunity_global_results.json
opportunity_selection_results.json
dual_gate_results.json
candidate_population_validation.json
artifact_validation.json
hash_validation.json
binding_validation.json
runtime_separation_validation.json
regression_results.json
non_mutation.json
remaining_risks.json
final_judgment.json
```

## Remaining Risks

Global predictive diagnostics remain weak even though Global Safety / Sanity passes.

Selection utility is positive across Top5 / Top10 / Top20, but Spearman within the Candidate-passed Universe is weak negative.

Recent Holdout remains unaccessed and must be handled in a separate approved phase.

Corrective Re-evaluation PASS does not authorize Unified Generation, Accepted Generation, Runtime transition, BUY_READY, or PRODUCTION_READY.

## Next Step

```text
PHASE19_AK_REVIEW_READY
```
