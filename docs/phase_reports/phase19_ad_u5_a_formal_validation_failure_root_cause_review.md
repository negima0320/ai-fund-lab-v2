# Phase19-AD-U5-A Formal Validation Failure Root Cause and Corrective Policy Review

## Final Judgment

```text
PHASE19_AD_U5_A_VALIDATOR_CORRECTION_REQUIRED
PHASE19_AD_U5_A_HUMAN_DECISION_REQUIRED
```

Root cause review is complete. The result does not authorize Formal Validation PASS, R7 readiness, Unified Generation, Accepted Generation, Runtime readiness, or Broker use.

## Policy Origin Audit

Approved policy:

```text
BALANCED_WITH_COMPONENT_OVERRIDES
policy_hash = 42fc4fde8f8f1f465c8eca14d532286407e1b2985470466fd5a762131d106a46
approved_phase = PHASE19_AD_U3_D
reviewer = user:negishi
```

Candidate approved top-level label floors:

```text
minimum_positive_labels = 50000
minimum_negative_labels = 500000
```

Opportunity approved top-level label floors:

```text
minimum_positive_labels = 5000
minimum_negative_labels = 5000
```

Origin:

```text
U3-C Codex draft from dataset/split evidence
U3-D Human Review approval
```

Key finding:

```text
minimum_test_rows and minimum_test_business_days are explicit test-window fields.
minimum_test_positive_labels and minimum_test_negative_labels do not exist.
```

Therefore the approved policy does not explicitly authorize applying the top-level label floors as single test-window label floors.

## Split Capacity Audit

U5-A did not access recent_holdout rows. This follows the U5-A prohibition. The audit measured train, validation, and test rows, and recorded recent_holdout split metadata only.

Candidate test window:

```text
business_days = 39
sample_count = 165028
positive_count = 15964
negative_count = 149064
positive_per_business_day = 409.3333333333333
negative_per_business_day = 3822.153846153846
```

If the current top-level label floors are interpreted as test-window floors:

```text
required_business_days_for_positive_threshold = 123
required_business_days_for_negative_threshold = 131
```

Opportunity test window:

```text
business_days = 39
sample_count = 1940
positive_count = 915
negative_count = 1025
positive_per_business_day = 23.46153846153846
negative_per_business_day = 26.28205128205128
```

If the current top-level label floors are interpreted as test-window floors:

```text
required_business_days_for_positive_threshold = 214
required_business_days_for_negative_threshold = 191
```

Conclusion:

```text
The current 39-business-day test window cannot satisfy the top-level label floors if they are applied as single-window test thresholds.
```

## Candidate Label Semantics

Candidate label:

```text
label__momentum_candidate_label
```

U5 validator semantics:

```text
positive = label == 1
negative = label == 0
neutral/excluded = none
```

Classification:

```text
POLICY_AMBIGUOUS
```

The binary label semantics match the Candidate label, but the policy does not clearly state that top-level label floors apply to the test window.

## Opportunity Label Semantics

Opportunity label:

```text
label__expected_edge_label_20d
```

U5 validator semantics:

```text
positive = target > 0
negative = target <= 0
zero = negative side
neutral/excluded = none
```

Classification:

```text
POLICY_AMBIGUOUS
```

Opportunity is a regression score training output. Positive/negative side counting is directionally meaningful, but the policy does not clearly state that the top-level `5000 / 5000` label floors apply to the single test window.

## Gate Applicability

Architecture confirms split separation and per-split minimum rows/business dates.

U3-D policy contains:

```text
minimum_test_rows
minimum_test_business_days
minimum_validation_positive_labels
minimum_validation_negative_labels
```

U3-D policy does not contain:

```text
minimum_test_positive_labels
minimum_test_negative_labels
```

U5 validator behavior:

```text
Applied top-level minimum_positive_labels and minimum_negative_labels to test window.
```

Classification:

```text
POLICY_AMBIGUOUS_PLUS_VALIDATOR_APPLICABILITY_DEFECT
```

## Candidate Metric Quality

Observed Candidate primary metrics:

```text
Brier Score = 0.08706860657893768
Log Loss = 0.31475352809279716
ECE = 0.006901105624084435
ROC-AUC = 0.6152783698517283
PR-AUC = 0.13569431649867195
class_balance = 0.09673509949826696
```

Baseline comparison:

```text
class-prior Brier = 0.08737742002332735
class-prior Log Loss = 0.317849451352439
PR-AUC baseline prevalence = 0.09673509949826696
```

Finding:

```text
Candidate is finite, calibrated, non-collapsed, and modestly improves over class-prior baselines.
No approved Brier / LogLoss / ECE / ROC-AUC / PR-AUC hard threshold was found.
```

This is not classified as a primary Candidate predictive-quality failure, but it still requires Human Review for acceptability.

## Opportunity Metric Quality

Observed Opportunity primary metrics:

```text
MAE = 0.6983658381596776
RMSE = 0.8608991989523957
Pearson = -0.013346777729190233
Spearman = -0.023113834309422397
prediction_to_target_scale_ratio = 2.8096240917342885
```

Target-only baselines:

```text
zero_baseline_mae = 0.2326556451030928
zero_baseline_rmse = 0.2792018933083429
mean_baseline_mae = 0.23450917056727602
mean_baseline_rmse = 0.2739959467962885
```

Finding:

```text
Opportunity metrics show a genuine predictive-quality concern.
Pearson and Spearman are near zero.
Model MAE/RMSE are worse than zero and mean baselines under the current normalized-score metric.
```

Approved policy does not define MAE, RMSE, Pearson, Spearman, or scale-ratio hard thresholds. Therefore this is not encoded as a current hard FAIL, but it must not be hidden behind the label-count failure.

## Validator Implementation

Reviewed:

```text
src/ai_fund_lab_v2/ai_lifecycle/candidate_validator.py
src/ai_fund_lab_v2/ai_lifecycle/opportunity_validator.py
src/ai_fund_lab_v2/ai_lifecycle/formal_validation_runner.py
```

Confirmed:

```text
test window filtering = split_definition.test start/end
recent_holdout execution = primary_pass only
component gate = all checks true
combined gate = candidate_pass and opportunity_pass
```

Defect:

```text
Top-level minimum_positive_labels / minimum_negative_labels were mapped to test-window label counts without explicit approved test-window label threshold fields.
```

Classification:

```text
RC-D_VALIDATOR_POLICY_FIELD_MAPPING_DEFECT
```

## All Gate Results

Candidate failed checks:

```text
minimum_positive_labels
minimum_negative_labels
```

Opportunity failed checks:

```text
minimum_positive_labels
minimum_negative_labels
```

Non-count checks:

```text
Candidate = no non-count quality gate failure
Opportunity = no non-count quality gate failure encoded by current policy
```

Combined:

```text
PRIMARY_FORMAL_VALIDATION_FAIL
```

## Root Cause Classification

Primary:

```text
RC-C
Policy label/window applicability and validator semantics differ or are ambiguous

RC-D
Validator implementation defect: top-level label sufficiency floors were applied as single test-window label floors without explicit policy fields
```

Secondary:

```text
RC-A
Policy threshold is incompatible with approved test-window capacity if interpreted as single-window test label floor

RC-B
Split/test window is too short for that interpreted statistical requirement

RC-E
Opportunity model has genuine predictive-quality failure concern
```

Not primary:

```text
RC-F
Candidate model has no approved metric-threshold failure beyond the label-count gate
```

## Corrective Options

Option A — Policy Correction:

```text
Applicability = HIGH
```

Define explicit window-scoped label thresholds and metric thresholds where needed. Must record that U5 test has already been observed.

Option B — Revised Split:

```text
Applicability = MEDIUM
```

Required if Human Review confirms current top-level label floors are intended as single test-window floors.

Option C — Aggregated OOS Evaluation Contract:

```text
Applicability = LOW_UNLESS_PRIOR_INTENT_IS_PROVEN
```

Do not adopt after-the-fact unless prior intent is proven.

Option D — Corrective Model Work:

```text
Applicability = HIGH_FOR_OPPORTUNITY_QUALITY_AFTER_POLICY_DECISION
```

Opportunity requires separate quality review because rank/error evidence is weak.

Option E — Component Rejection:

```text
Applicability = MEDIUM
```

BALANCED_WITH_COMPONENT_OVERRIDES must not let one component hide another.

## Test Observation Record

```text
test_window_observed = true
observed_at_phase = PHASE19_AD_U5
observed_metrics = recorded
future_use_is_fully_unseen = false
```

If the same test window is reused after policy, validator, model, or split correction, it must be called:

```text
corrective reevaluation
```

It must not be called:

```text
first unseen formal validation
```

## Non-mutation

Confirmed:

```text
Model Quality Policy changed = false
minimum label threshold changed = false
Split changed = false
Dataset rematerialized = false
Training executed = false
Calibration refit executed = false
Formal Validation rerun = false
recent_holdout accessed by U5-A = false
Feature changed = false
Model changed = false
Unified Generation created = false
Accepted Generation created = false
Runtime changed = false
Broker used = false
```

## Evidence Paths

Documentation:

```text
docs/phase_reports/phase19_ad_u5_a_formal_validation_failure_root_cause_review.md
```

Summary:

```text
reports/phase_reports/phase19_ad_u5_a_formal_validation_failure_root_cause_review.json
```

Evidence:

```text
reports/phase19_ad_u5_a_formal_validation_failure_root_cause_review/
```

## Remaining Risks

```text
Approved policy lacks explicit test positive/negative label threshold fields.
Observed U5 test is no longer fully unseen.
Opportunity predictive quality is materially weak under current metrics.
If single-window label floors are confirmed, the current test window is far too small.
```

## Human Decision Required

Human Review must decide:

```text
Whether top-level label floors apply to train/bootstrap, validation, test, or all evaluated windows
Whether U5 validator must be corrected to use explicit window-scoped thresholds only
Whether Opportunity near-zero correlation requires corrective model work
Whether revised split is required for a new fully unseen Formal Validation window
```
