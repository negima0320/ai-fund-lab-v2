# Phase19-AD-U3-H Formal Training Diagnostics and Root Cause Investigation

## Final Judgment

```text
PHASE19_AD_U3_H_ROOT_CAUSE_IDENTIFIED
PHASE19_AD_U3_H_CORRECTIVE_ACTION_READY
```

Calibration remains prohibited for the current U3-G Training Artifacts.

```text
Calibration Entry = PROHIBITED_UNTIL_CORRECTIVE_ACTION
```

This phase did not change `max_iter`, learning rate, features, targets, scaling, model family, Runtime pointer, Accepted Decision, Accepted Generation, BUY state, SELL state, Trading state, or Broker state.

## Candidate Diagnosis

Candidate data and artifact are structurally valid, but the prediction distribution is collapsed toward probability `1.0`.

Validation prediction distribution:

```text
rows = 934105
min = 0.0
p1 = 1.0
p5 = 1.0
median = 1.0
p95 = 1.0
p99 = 1.0
max = 1.0
count_eq_1 = 929821
ratio_eq_1 = 0.9954137918114131
```

Candidate label distribution is not itself extreme enough to explain this collapse alone:

```text
label min = 0.0
label max = 1.0
label mean = 0.09611939786323809
positive labels = 336118
negative labels = 3160762
```

Candidate uses raw numeric features after median imputation. `feature__liquidity_avg_volume_20d` is an in-component scale outlier:

```text
max_abs = 267391735.0
std = 4430046.845507548
classification = EXTREME_SCALE
```

Candidate also stopped at the configured iteration limit:

```text
max_iter = 30
n_iter_ = 30
ConvergenceWarning = present
```

## Opportunity Diagnosis

Opportunity is the primary blocker.

Validation prediction distribution:

```text
rows = 11063
min = -3.784492343664435e+24
p1 = -1.5381894113609655e+24
p5 = -7.424831383363719e+23
p25 = -9.778290612147858e+22
median = -1.1213884215786125e+22
p75 = -2.1313044994260864e+21
p95 = -7.782835332943361e+20
p99 = -1.2315498470369806e+20
max = -2.949436240918092e+17
```

The extreme minimum prediction was traced to a single dominant linear contribution:

```text
target_date = 2025-09-16
code = 67400
prediction = -3.784492343664435e+24
dominant feature = feature__liquidity_avg_volume_20d
raw value = 254608785.0
transformed value = 254608785.0
coefficient = -1.4863950369510268e+16
contribution = -3.7844923438813105e+24
```

That contribution dominates the prediction. The intercept is only:

```text
5589695122.406853
```

## Feature Statistics

Feature scale investigation used Tukey outlier analysis on `log10(max_abs)` and `log10(std)` within each component feature distribution after the recorded training preprocessing. No fixed absolute threshold such as `1e6` was used for classification.

Candidate top feature-scale outlier:

```text
feature__liquidity_avg_volume_20d
max_abs = 267391735.0
std = 4430046.845507548
classification = EXTREME_SCALE
```

Opportunity top feature-scale outliers:

```text
feature__liquidity_avg_volume_20d
max_abs = 234339295.0
std = 10128501.683674611
classification = EXTREME_SCALE

feature__candidate_rank
max_abs = 50.0
std = 14.42350537296959
classification = EXTREME_SCALE
```

The Opportunity training preprocessing is:

```text
numeric_or_bool_median_imputation
categorical_mapping
```

No numeric standardization or target scaling is recorded.

## Target Statistics

Opportunity target scale is small compared with the prediction magnitude:

```text
label = label__expected_edge_label_20d
min = -0.47000000000000003
p1 = -0.47000000000000003
p5 = -0.42760547
median = -0.019355100000000004
p95 = 0.34263579
p99 = 0.5187557339999994
max = 0.54
std = 0.24560209700822
```

Therefore `TARGET_SCALE` is not the primary cause.

Candidate target:

```text
label = label__momentum_candidate_label
min = 0.0
max = 1.0
mean = 0.09611939786323809
std = 0.2947549138142511
```

## Prediction Distribution

Candidate prediction is finite and non-constant, but collapsed:

```text
constant_prediction = false
collapsed_prediction = true
ratio_eq_1 = 0.9954137918114131
```

Opportunity prediction is finite and non-constant, but its magnitude is incompatible with the target scale:

```text
finite = true
constant_prediction = false
max_abs = 3.784492343664435e+24
log10_max_abs = 24.578007630961114
std = 3.0370187792968264e+23
```

No NaN or Inf was found in either prediction distribution.

## SGD Review

Candidate:

```text
model_family = sklearn_sgd_classifier
loss = log_loss
penalty = l2
alpha = 0.0001
learning_rate = optimal
eta0 = 0.0
tol = 0.0001
max_iter = 30
n_iter_ = 30
shuffle = false
fit_intercept = true
```

Opportunity:

```text
model_family = sklearn_sgd_regressor
loss = squared_error
penalty = l2
alpha = 0.0001
learning_rate = invscaling
eta0 = 0.01
tol = 0.0001
max_iter = 30
n_iter_ = 30
shuffle = false
fit_intercept = true
coef_abs_max = 1.4863950369510268e+16
```

Both fitted model objects report `n_iter_ = 30`, equal to configured `max_iter = 30`. This directly supports the ConvergenceWarning cause: the optimizer reached the iteration ceiling.

## Learning Curve

Per-iteration loss and gradient norm are not available.

Reason:

```text
The U3-G sklearn SGD artifacts do not record per-iteration loss or gradient norm, and sklearn model objects do not retain a learning curve by default for this training path.
```

Available evidence:

```text
candidate_n_iter = 30
opportunity_n_iter = 30
candidate_max_iter = 30
opportunity_max_iter = 30
```

## Calibration Feasibility

Calibration is prohibited for the current outputs.

Decision:

```text
TRAINING_ABNORMALITY_NOT_SAFE_CALIBRATION_INPUT
```

Evidence:

```text
Opportunity predictions are finite but span orders of magnitude inconsistent with target scale.
Extreme prediction is dominated by raw-scale feature contribution and non-converged SGDRegressor.
Calibration would transform output scale after training and could mask rather than fix non-converged raw-score behavior.
```

## Root Cause

Primary root cause:

```text
Unscaled high-magnitude Opportunity features interacting with SGDRegressor configuration that stops at max_iter=30 before convergence.
```

Classification:

```text
FEATURE_SCALE = HIGH
MODEL_CONFIGURATION = HIGH
PREPROCESSING = MEDIUM
DATASET = MEDIUM
TARGET_SCALE = LOW
IMPLEMENTATION = LOW
```

The dataset contains legitimate high-scale liquidity/volume features, but the current preprocessing passes them to SGD without scaling. The implementation path and artifact bindings are intact, so this is not classified as a hash/schema/serialization implementation defect.

## Corrective Options

Option A:

```text
Add contract-bound numeric feature scaling for SGD training.
```

Impact:

```text
Targets FEATURE_SCALE and PREPROCESSING while preserving the SGD family.
```

Risk:

```text
Requires artifact contract update and formal retraining approval. Scaler must be fit on train window only.
```

Production fit:

```text
HIGH if train-window-only and hash-bound.
```

Option B:

```text
Use a model family less sensitive to raw feature scale.
```

Impact:

```text
Reduces SGD scale sensitivity without changing dataset labels.
```

Risk:

```text
Material model-family change requiring policy, compatibility, and validation review.
```

Production fit:

```text
MEDIUM to HIGH after policy approval and runtime compatibility validation.
```

Option C:

```text
Keep SGD but approve diagnostic config review for convergence settings.
```

Impact:

```text
Addresses MODEL_CONFIGURATION max-iteration stop.
```

Risk:

```text
Longer training can still diverge or produce unstable coefficients if raw scale remains.
```

Production fit:

```text
MEDIUM; best paired with scaling evidence.
```

## Failure Injection

Reviewed:

```text
feature overflow
target overflow
prediction overflow
NaN
Inf
collapsed prediction
constant prediction
```

Result:

```text
Feature / target / prediction overflow = not observed
Prediction NaN / Inf = not observed
Candidate collapsed prediction = REVIEW_REQUIRED
Constant prediction = not observed
```

## Evidence Paths

```text
reports/phase19_ad_u3_h_training_root_cause_investigation/candidate_feature_statistics.json
reports/phase19_ad_u3_h_training_root_cause_investigation/opportunity_feature_statistics.json
reports/phase19_ad_u3_h_training_root_cause_investigation/candidate_target_statistics.json
reports/phase19_ad_u3_h_training_root_cause_investigation/opportunity_target_statistics.json
reports/phase19_ad_u3_h_training_root_cause_investigation/candidate_prediction_distribution.json
reports/phase19_ad_u3_h_training_root_cause_investigation/opportunity_prediction_distribution.json
reports/phase19_ad_u3_h_training_root_cause_investigation/sgd_configuration_review.json
reports/phase19_ad_u3_h_training_root_cause_investigation/learning_curve_review.json
reports/phase19_ad_u3_h_training_root_cause_investigation/calibration_feasibility_review.json
reports/phase19_ad_u3_h_training_root_cause_investigation/root_cause_classification.json
reports/phase19_ad_u3_h_training_root_cause_investigation/corrective_options.json
reports/phase19_ad_u3_h_training_root_cause_investigation/failure_injection_results.json
reports/phase19_ad_u3_h_training_root_cause_investigation/final_judgment.json
```

## Next Step

Choose and approve a corrective action plan before any corrective training rerun. Calibration, Formal Validation, Unified Generation, Accepted Decision, Accepted Generation, Runtime Transition, BUY restart, and Broker write remain prohibited until the corrective gate is cleared.
