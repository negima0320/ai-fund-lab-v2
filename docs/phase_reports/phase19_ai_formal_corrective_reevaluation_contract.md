# Phase19-AI — Formal Corrective Re-evaluation Contract

## Final Judgment

```text
PHASE19_AI_CORRECTIVE_REEVALUATION_CONTRACT_COMPLETE
PHASE19_AJ_HUMAN_DECISION_REQUIRED
```

Forbidden declarations were not made:

```text
CORRECTIVE_REEVALUATION_PASS
FORMAL_VALIDATION_PASS
DUAL_GATE_PASS
GENERATION_READY
RUNTIME_READY
```

## Corrective Re-evaluation Position

Phase19-U5 already observed the test window. Therefore the next use of the same test window must be classified as:

```text
CORRECTIVE_REEVALUATION
```

It must not be described as:

```text
FIRST_UNSEEN_FORMAL_VALIDATION
```

Purpose:

```text
Correct the validator policy mapping defect.
Evaluate Opportunity TopN utility in the Candidate-passed Universe.
Evaluate Global Quality and Selection Utility together.
```

It is not a path to retroactively change a failed result into PASS by tuning thresholds, TopN, population, metrics, or baselines after seeing the result.

## Test Observation Status

Required record:

```text
test_window_observed = true
first_unseen_validation_consumed = true
previous_run_id = phase19_ad_u5_formal_validation_7b36f4d2a95e1c6b
validator_defect_corrected = true
evaluation_contract_changed = true
model_changed = false
calibration_changed = false
feature_changed = false
target_changed = false
```

Previous Opportunity test metrics:

```text
sample_count = 1940
business_days = 39
Pearson = -0.013346777729190233
Spearman = -0.023113834309422397
MAE = 0.6983658381596776
RMSE = 0.8608991989523957
finite_ratio = 1.0
collapse = false
explosion = false
```

## Candidate Population Contract

Selection Utility Gate population:

```text
Candidate-passed Universe
```

Default rule:

```text
business dayごとにCandidate score上位50件
```

If an authoritative historical Candidate pass rule exists as an artifact-bound contract, that rule must be investigated and used instead.

Required bindings:

```text
candidate_source_artifact_id
candidate_source_content_hash
candidate_model_artifact_id
candidate_calibration_artifact_id
candidate_score_field
candidate_pass_rule
per_day_population_limit
business_day grouping
tie handling
missing handling
selected rows hash
```

Prohibited:

```text
Opportunity scoreでCandidateTop50を作る
全Opportunity rowsをCandidate通過扱いする
過去CSVを手動投入する
latest / mtimeでCandidate artifactを探索する
```

## Global Gate Status Semantics

Gate ID:

```text
OPPORTUNITY_GLOBAL_QUALITY_GATE_V1
```

Hard technical FAIL:

```text
finite_ratio < 1.0
NaN exists
Inf exists
collapse = true
explosion = true
ordering_preservation = false
source binding mismatch
schema mismatch
hash mismatch
```

Required predictive diagnostics:

```text
Pearson correlation
Spearman correlation
MAE
RMSE
zero baseline comparison
mean baseline comparison
median baseline comparison
directional accuracy
prediction_to_target_scale_ratio
prediction distribution
target distribution
```

Proposed qualitative mapping for Human Review:

```text
CLEARLY_DESTRUCTIVE
NON_DESTRUCTIVE_BUT_WEAK
POSITIVE_GLOBAL_SIGNAL
```

If approved threshold/status semantics are absent:

```text
GLOBAL_PREDICTIVE_STATUS = REVIEW_REQUIRED
generation_eligibility = false
```

## Selection Gate Status Semantics

Gate ID:

```text
OPPORTUNITY_SELECTION_UTILITY_GATE_V1
```

Required metric families:

```text
selected mean realized return
selected median realized return
CandidateTop50 mean realized return
Top-minus-CandidateTop50
Top-minus-bottom
Hit Rate
Downside Rate
Rank Lift
NDCG
Spearman within Candidate-passed Universe
```

Proposed qualitative mapping for Human Review:

```text
STRONG_SELECTION_UTILITY
CONSISTENT_SELECTION_UTILITY
MIXED_SELECTION_UTILITY
NO_SELECTION_UTILITY
REVERSED_SELECTION_UTILITY
```

Forbidden PASS shortcuts:

```text
Top5だけ良ければ無条件PASS
Top20だけ良ければ無条件PASS
単一銘柄の大勝でPASS
平均値だけでPASS
Hit RateだけでPASS
```

## Top5 / Top10 / Top20 Roles

Top5:

```text
PRIMARY_UTILITY_SLICE
実際の最終購入候補に最も近い
```

Top10:

```text
SECONDARY_CONFIRMATION_SLICE
Top5が偶然でないことを確認する
```

Top20:

```text
ROBUSTNESS_SLICE
Ranking signalが一定範囲まで維持されるか確認する
```

Recommended policy:

```text
Top5 alone cannot pass Selection Utility.
Top5 / Top10 / Top20 must be judged together.
```

## Baseline Contract

Required baselines:

```text
CandidateTop50 average
Candidate score rank baseline
Random ranking baseline
Bottom-N Opportunity ranking
```

Conditional baselines only when artifact-bound:

```text
simple rule baseline
historical champion baseline
challenger baseline
```

Prohibited:

```text
都合の悪いbaselineを除外する
実行後にbaselineを追加する
未bound historical modelを直接baseline利用する
```

## Dual-Gate Decision

Formal corrective decision:

```text
Global Gate Result
AND
Selection Utility Gate Result
```

Decision table:

```text
Global PASS + Selection PASS
→ DUAL_GATE_CORRECTIVE_PASS
→ generation_eligibility = true

Global FAIL + Selection PASS
→ DUAL_GATE_CORRECTIVE_FAIL
→ generation_eligibility = false

Global PASS + Selection FAIL
→ DUAL_GATE_CORRECTIVE_FAIL
→ generation_eligibility = false

Global REVIEW_REQUIRED or Selection REVIEW_REQUIRED
→ DUAL_GATE_CORRECTIVE_REVIEW_REQUIRED
→ generation_eligibility = false
```

This step still does not create Unified Generation.

## Candidate Corrective Re-evaluation

AE status:

```text
CORRECTIVE_REEVALUATION_ELIGIBLE
```

Recommendation:

```text
Candidateも同一runでcorrective reevaluationする
```

Reason:

```text
Combined Generation eligibilityを同一Dataset Revision / Split / test window / policy versionで揃えるため
```

Candidate and Opportunity results must not offset each other.

## Runtime Separation Confirmation

Corrective Re-evaluation evidence is Generation Acceptance Layer evidence only.

Runtime remains:

```text
Accepted Generation
↓
Candidate
↓
Opportunity
↓
TopN
↓
Order
```

Runtime must not:

```text
read Corrective Re-evaluation Evidence
rerun Global / Selection Gate
stop BUY because of Gate disagreement
```

## Evidence Paths

```text
docs/phase_reports/phase19_ai_formal_corrective_reevaluation_contract.md
reports/phase_reports/phase19_ai_formal_corrective_reevaluation_contract.json
reports/phase19_ai_formal_corrective_reevaluation_contract/
```

Required evidence:

```text
corrective_reevaluation_policy.json
test_observation_record.json
frozen_run_inputs.json
candidate_population_contract.json
candidate_population_daily_counts.json
candidate_selected_rows_hash.json
global_gate_status_policy.json
selection_gate_status_policy.json
baseline_contract.json
top5_metric_contract.json
top10_metric_contract.json
top20_metric_contract.json
dual_gate_corrective_decision_contract.json
candidate_corrective_reevaluation_contract.json
runtime_separation_confirmation.json
non_execution_evidence.json
remaining_risks.json
human_decision_required.json
final_judgment.json
```

## Remaining Risks

Human Review must approve the qualitative status semantics before formal corrective reevaluation.

No numeric threshold is invented in AI. Missing approved semantics must produce:

```text
REVIEW_REQUIRED
generation_eligibility = false
```

Candidate-passed universe reconstruction still requires artifact-bound execution in a later phase.

## Human Decision Required

Recommended decisions:

```text
1. Global品質は「致命的に壊れていないこと」の確認として扱うか
   Recommended: YES

2. Top5をPrimary、Top10を確認、Top20を安定性確認として扱うか
   Recommended: YES

3. Top5だけ良くTop10/20が悪い場合はPASSさせないか
   Recommended: YES、PASSさせない

4. Candidateも同じcorrective reevaluation runで再判定するか
   Recommended: YES
```
