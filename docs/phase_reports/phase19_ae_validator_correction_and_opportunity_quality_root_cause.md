# Phase19-AE Validator Correction and Opportunity Quality Root Cause

## Final Judgment

```text
PHASE19_AE_COMPLETE
PHASE19_AF_HUMAN_DECISION_REQUIRED
```

Forbidden declarations were not made:

```text
FORMAL_VALIDATION_PASS
R7_READY
UNIFIED_GENERATION_READY
ACCEPTED_GENERATION_READY
RUNTIME_READY
```

## Human Decision Materialization

Human Review:

```text
reviewer = user:negishi
decision = APPROVE_VALIDATOR_CORRECTION_AND_OPPORTUNITY_CORRECTIVE_INVESTIGATION
```

Approved:

```text
RC-D_VALIDATOR_POLICY_FIELD_MAPPING_DEFECT
Candidate = CORRECTIVE_REEVALUATION_ELIGIBLE assessment
Opportunity = PREDICTIVE_QUALITY_REVIEW_REQUIRED investigation
```

Still prohibited:

```text
Training
Calibration refit
Formal Validation rerun
recent_holdout access
Policy threshold lowering
Model / feature / target change
Unified Generation
Accepted Generation
Runtime transition
Broker write
```

## Policy Applicability Contract

Materialized field scopes:

```text
TRAINING_DATA_SUFFICIENCY
CALIBRATION_DATA_SUFFICIENCY
FORMAL_TEST_DATA_SUFFICIENCY
LIFECYCLE_DATA_SUFFICIENCY
UNSCOPED_REVIEW_REQUIRED
```

Formal test gate fields:

```text
minimum_test_rows
minimum_test_business_days
minimum_test_positive_labels
minimum_test_negative_labels
```

Top-level lifecycle fields:

```text
minimum_positive_labels
minimum_negative_labels
```

These are no longer implicitly mapped to the single `test` window. For Formal Test they are recorded as:

```text
UNSCOPED_REVIEW_REQUIRED
```

For Opportunity regression targets, positive/negative counts are explicitly defined as sign-coverage only:

```text
positive = target > 0
negative = target <= 0
```

## Validator Correction

Changed:

```text
src/ai_fund_lab_v2/ai_lifecycle/candidate_validator.py
src/ai_fund_lab_v2/ai_lifecycle/opportunity_validator.py
src/ai_fund_lab_v2/ai_lifecycle/formal_validation_runner.py
```

Correction:

```text
test-window-scoped fields only are applied to test gate
top-level lifecycle label floors are not silently applied to test
unknown minimum/maximum policy fields produce REVIEW_REQUIRED
component REVIEW_REQUIRED propagates to combined REVIEW_REQUIRED semantics
```

Formal Validation was not rerun.

## Validator Regression

Regression:

```text
py_compile = PASS
pytest = 12 passed
```

Covered:

```text
top-level lifecycle label floor is not applied to test window
explicit minimum_test_positive_labels is applied
explicit minimum_test_negative_labels is applied
unscoped field causes REVIEW_REQUIRED
Candidate binary count semantics
Opportunity regression sign-coverage semantics
result-driven top-level threshold mutation does not create test PASS
U5 historical mis-mapping regression guarded
```

Known warnings:

```text
U4-C intentional overflow / constant fixture warnings
```

## Candidate Assessment

Candidate status:

```text
CORRECTIVE_REEVALUATION_ELIGIBLE
```

Basis:

```text
finite = true
non_collapsed = true
calibration_stable = true
Brier = 0.08706860657893768
Log Loss = 0.31475352809279716
ECE = 0.006901105624084435
ROC-AUC = 0.6152783698517283
PR-AUC = 0.13569431649867195
PR-AUC class-prior baseline = 0.09673509949826696
```

This is not a Formal Validation PASS. Same-test future use is only:

```text
CORRECTIVE_REEVALUATION
```

## Opportunity Target Audit

Target:

```text
label__expected_edge_label_20d
target_horizon_business_days = 20
```

Windows audited:

```text
train
validation
test
```

Recent Holdout was not accessed.

Test target distribution:

```text
sample_count = 1940
positive_count = 915
negative_count = 1025
target_mean = -0.05366487087628865
target_std = 0.2739959467962885
zero_count = 0
```

No missing targets were detected in audited train / validation / test windows.

## Opportunity Window Metrics

Train:

```text
Pearson = 0.1057193554664133
Spearman = 0.07988644085792167
directional_accuracy = 0.5304956651416728
top_minus_bottom_target_mean = 0.07273178273944908
```

Validation:

```text
Pearson = 0.09147543507435503
Spearman = 0.05590548133776607
directional_accuracy = 0.5228238271716532
top_minus_bottom_target_mean = 0.07630617172538393
```

Test:

```text
Pearson = -0.013346777729190233
Spearman = -0.023113834309422397
directional_accuracy = 0.49948453608247423
top_minus_bottom_target_mean = 0.008193531958762879
```

Finding:

```text
The weak validation rank signal does not transfer to test.
```

## Opportunity Baseline Comparison

Test:

```text
model MAE = 0.6983658381596776
model RMSE = 0.8608991989523957
zero_baseline_mae = 0.2326556451030928
zero_baseline_rmse = 0.2792018933083429
mean_baseline_mae = 0.23450917056727602
mean_baseline_rmse = 0.2739959467962885
median_baseline_mae = 0.23223950036082475
median_baseline_rmse = 0.2765545587139336
```

Result:

```text
model_beats_zero = false
model_beats_mean = false
model_beats_median = false
```

## Opportunity Feature Contribution

Largest coefficient:

```text
feature__market_return_5d
coefficient = -0.03848528414097445
```

`feature__market_return_5d` contribution rank by mean absolute contribution:

```text
train = recorded
validation = recorded
test = rank 2
```

Dominant contribution is not enough to produce useful test rank ordering.

## Opportunity Model Configuration

Model:

```text
model_family = sklearn_sgd_regressor
loss = squared_error
penalty = l2
alpha = 0.0001
learning_rate = optimal
eta0 = 0.0
max_iter = 30
tol = 0.0001
feature_scaling = StandardScaler
target_scaling = not declared
sample_weight = not declared / not used
```

Review item:

```text
Squared-error SGD without target scaling may be mismatched to signed expected-edge ranking.
```

No model/config change was made in AE.

## Alignment / Leakage Audit

Audited:

```text
feature date
label horizon
symbol/date duplicate rows
missing targets
corporate action policy hash
dataset lineage hash
split content hash
prohibited input audit
```

Finding:

```text
No duplicate code-target_date rows
No missing targets
Artifact-level prohibited-input audit = PASS
No available evidence of alignment or leakage defect
```

Recent Holdout was not accessed.

## Opportunity Root Cause

Classification:

```text
ORC-H
Multiple contributing causes
```

Primary:

```text
ORC-B
Feature set / fitted signal has weak or non-transferable predictive signal

ORC-D
Train / validation / test regime or signal drift
```

Secondary:

```text
ORC-C
Model family/configuration may be mismatched to signed expected-edge ranking

ORC-G
Metric/validator contract was incomplete because no Opportunity correlation/error hard thresholds existed
```

Not supported:

```text
ORC-E
Dataset alignment or leakage defect not detected

ORC-F
Calibration/standardization issue not supported because ordering is preserved
```

## Corrective Options

Option A — Retain model, correct validator only:

```text
NOT_RECOMMENDED_CURRENTLY
```

Option B — Opportunity model/configuration correction:

```text
RECOMMENDED_FOR_REVIEW
```

Option C — Feature/target corrective work:

```text
RECOMMENDED_FOR_REVIEW
```

Option D — Opportunity component rejection:

```text
VALID_CONSERVATIVE_OPTION
```

Option E — Revised Dataset/Split:

```text
CONDITIONAL
```

## Test Observation Status

```text
test_window_observed = true
first_unseen_validation_consumed = true
AE test metric use = diagnostic_only_root_cause_investigation
future same-test use = CORRECTIVE_REEVALUATION
fully unseen required status = REVISED_SPLIT_REQUIRED
recent_holdout_accessed = false
```

## Non-mutation

Confirmed:

```text
policy_threshold_lowering = false
training_executed = false
calibration_refit_executed = false
formal_validation_rerun = false
recent_holdout_accessed = false
model_config_changed = false
feature_changed = false
target_changed = false
unified_generation_created = false
accepted_generation_created = false
runtime_transition = false
broker_write = false
```

## Changed Files

```text
src/ai_fund_lab_v2/ai_lifecycle/candidate_validator.py
src/ai_fund_lab_v2/ai_lifecycle/opportunity_validator.py
src/ai_fund_lab_v2/ai_lifecycle/formal_validation_runner.py
tests/ai_lifecycle/test_phase19_ad_u5_formal_validation.py
docs/phase_reports/phase19_ae_validator_correction_and_opportunity_quality_root_cause.md
docs/01_requirements/phase_roadmap.md
```

## Evidence Paths

Summary:

```text
reports/phase_reports/phase19_ae_validator_correction_and_opportunity_quality_root_cause.json
```

Evidence:

```text
reports/phase19_ae_validator_correction_and_opportunity_quality_root_cause/
```

## Remaining Risks

```text
Current Opportunity artifact remains generation-ineligible.
Opportunity metric hard thresholds remain undefined.
Existing U5 test is observed and cannot become first-unseen PASS.
Candidate-only generation is not authorized by current architecture.
```

## Human Decision Required

Next Human Review must decide:

```text
Approve corrected validator / policy applicability contract
Choose Opportunity corrective path
Decide whether Opportunity correlation/error thresholds are required
Decide whether same test may be used as corrective reevaluation or revised split is required
```
