# Phase19-AD-U3-I Feature Scaling Corrective Contract

## Final Judgment

```text
PHASE19_AD_U3_I_FEATURE_SCALING_CORRECTIVE_CONTRACT_PASS
PHASE19_AD_U3_CORRECTIVE_TRAINING_EXECUTION_PLAN_READY
```

This phase does not declare Corrective Training complete, Calibration ready, Calibration complete, Formal Validation PASS, Unified Generation created, Accepted Generation created, BUY ready, production ready, or Runtime transition complete.

## Human Review Decision

Materialized:

```text
reviewer = user:negishi
decision = APPROVE
approved_corrective_action = OPTION_A_CONTRACT_BOUND_FEATURE_SCALING
```

Codex is not the reviewer.

Policy:

```text
.runtime/ai_lifecycle/policies/corrective_actions/phase19_ad_u3_i_feature_scaling/corrective_action_policy.json
```

The policy is `APPROVED` and `reviewed_policy_hash == policy_hash`.

## Approved Corrective Action

Approved:

```text
Contract-bound feature scaling
```

Still prohibited:

```text
max_iter change
learning_rate change
eta0 change
alpha change
tol change
model family change
target clipping
prediction clipping
feature deletion
Runtime pointer write
Accepted Generation creation
Broker write
```

## Scaler Method Comparison

Compared:

```text
StandardScaler
RobustScaler
MaxAbsScaler
```

Basis:

```text
U3-H identified raw high-magnitude numeric features interacting with sklearn SGD.
Current training matrices are dense numpy arrays.
Dataset, Target, and Model Family must remain unchanged.
Runtime transform must be reproducible from hash-bound parameters.
```

## Scaler Method Decision

Decision:

```text
StandardScaler
```

Reason:

```text
StandardScaler directly addresses SGD raw feature scale sensitivity with mean/scale parameters that can be hash-bound and replayed.
Binary flags and categorical encodings are excluded from scaling.
RobustScaler remains a later option if StandardScaler corrective evidence is insufficient.
```

No additional scaler-method Human Review is required for U3-I.

## Candidate Scaling Scope

Candidate inventory classifies continuous numeric features for scaling and excludes binary flags.

Example:

```text
feature__liquidity_avg_volume_20d = CONTINUOUS_NUMERIC_SCALE
feature__missing_flags_price = BINARY_FLAG
```

## Opportunity Scaling Scope

Opportunity inventory classifies continuous numeric features for scaling, binary flags as pass-through, and categorical encoded features as pass-through pending explicit review.

Example:

```text
feature__liquidity_avg_volume_20d = CONTINUOUS_NUMERIC_SCALE
feature__candidate_rank = CONTINUOUS_NUMERIC_SCALE
feature__candidate_reason = CATEGORICAL_ENCODED
feature__missing_flags_price = BINARY_FLAG
```

## Train-Window-Only Fit Contract

Formal order:

```text
Training Window raw features
-> Training Window only imputer fit
-> Training Window only scaler fit
-> Training Window transform
-> Validation transform-only
-> Test transform-only
-> Recent Holdout transform-only
```

Candidate and Opportunity scalers are component-isolated.

## Missing / Scaling Pipeline

Pipeline:

```text
raw feature
-> train-window-only imputer fit
-> imputer transform
-> train-window-only StandardScaler fit
-> scaler transform
-> model fit
```

Scaler does not receive NaN in the implemented smoke path. Imputer and scaler bindings are reflected through preprocessing pipeline hash and scaler artifact hash.

## Scaler Artifact Contract

Added:

```text
schemas/ai_lifecycle/scaler_artifact.schema.json
```

Scaler artifact binds:

```text
scaler file/hash
scaler config/hash
fitted parameters/hash
Dataset Revision
Split
Model Quality Policy
Corrective Action Policy
Training Config
Training Code
Environment
Feature order
Scaled/excluded features
```

Scaler artifact alone is not Runtime eligible.

## Model / Scaler Binding

Corrective model artifacts bind:

```text
scaler_artifact_id
scaler_artifact_hash
scaler_method
scaled_feature_schema_hash
preprocessing_pipeline_hash
```

Runner validation rejects component mismatch, hash mismatch, and feature order mismatch.

## Generation Contract Updates

Updated schemas:

```text
candidate_model_artifact.schema.json
opportunity_model_artifact.schema.json
calibration_artifact.schema.json
validation_artifact.schema.json
runtime_baseline_artifact.schema.json
unified_generation_candidate.schema.json
accepted_generation_manifest.schema.json
```

The schema updates are compatibility-preserving for historical U3-G artifacts; U3-I corrective artifacts enforce scaler binding through runner validation.

## Runtime Inference Contract

Design-only update:

```text
Accepted Generation
-> Generation-bound Imputer
-> Generation-bound Scaler
-> Generation-bound Candidate Model
-> Generation-bound Opportunity Model
```

Runtime implementation and Runtime Transition were not performed.

Runtime must eventually reject:

```text
latest scaler search
component mismatch
scaler hash mismatch
feature order mismatch
direct Training Artifact scaler use
```

## Fixture Scaling Smoke

Fixture smoke passed.

Confirmed:

```text
high-magnitude feature included
missing value included
binary flag excluded from scaling
Candidate / Opportunity scalers separated
Validation extreme value does not affect fit parameters
Scaler artifact schema PASS
Model artifact schema PASS
Model / Scaler binding PASS
Hash verification PASS
runtime_eligibility = false
```

Fixture metrics are not production quality evidence.

## Saturation Guard Design

Candidate corrective artifacts must record:

```text
prediction quantiles
ratio_eq_0
ratio_eq_1
unique_prediction_count
prediction_std
collapsed_prediction
```

Threshold:

```text
HUMAN_REVIEW_REQUIRED_THRESHOLD
```

Current `ratio_eq_1 = 0.9954137918114131` must not auto-pass.

## Magnitude Guard Design

Opportunity corrective artifacts must record:

```text
prediction min/max/quantiles/median/std
max_abs
target min/max/std
prediction_to_target_scale_ratio
dominant_feature_contribution
coefficient_abs_max
```

Threshold:

```text
HUMAN_REVIEW_REQUIRED_THRESHOLD
```

Extreme prediction-to-target scale mismatch must not pass to Calibration automatically.

## Convergence Evidence Contract

Corrective training artifacts must record:

```text
max_iter
n_iter
tol
convergence_warning
warning_classification
coefficient_abs_max
intercept
```

U3-I keeps `max_iter = 30`; tuning remains deferred until scaling evidence exists.

## Old Training Artifact Disposition

U3-G artifacts are retained append-only:

```text
SUPERSEDED_FOR_CORRECTIVE_RETRAINING
CALIBRATION_PROHIBITED
```

They must not be used as implicit fallback.

## Formal Corrective Training Block

Formal Corrective Training was not executed.

```text
CORRECTIVE_BOOTSTRAP -> REJECTED
```

Reason:

```text
Requires separate Human-reviewed Execution Plan
```

## Non-Mutation

Confirmed:

```text
runtime_mutated = false
trading_state_mutated = false
runtime_pointer_written = false
accepted_decision_written = false
accepted_generation_created = false
unified_generation_created = false
corrective_formal_training_executed = false
buy_restarted = false
broker_write_executed = false
```

## Failure Injection

FI-1 through FI-17 passed.

Covered:

```text
Validation/Test/Holdout scaler-fit contamination
cross-component scaler reuse
scaler hash mismatch
model/scaler binding mismatch
target scaling
identifier/date scaling
missing/unapproved corrective policy
runtime eligible true
latest scaler discovery
feature order change
scaler file mutation
U3-G implicit fallback
formal corrective training execution
Runtime / Trading mutation
Broker write
```

## Regression

Regression evidence:

```text
reports/phase19_ad_u3_i_feature_scaling_corrective_contract/regression_results.json
```

## Changed Files

Changed files evidence:

```text
reports/phase19_ad_u3_i_feature_scaling_corrective_contract/changed_files.json
```

## Evidence Paths

Evidence directory:

```text
reports/phase19_ad_u3_i_feature_scaling_corrective_contract/
```

Summary:

```text
reports/phase_reports/phase19_ad_u3_i_feature_scaling_corrective_contract.json
```

## Remaining Risks

Formal Corrective Bootstrap full-dataset execution still requires a Human-reviewed Execution Plan. Scaling may not fully resolve convergence, so max_iter / learning-rate review remains deferred until post-scaling evidence. Candidate saturation and Opportunity magnitude thresholds still need Human Review.

## Next Step

Prepare a Human-reviewed Corrective Bootstrap Execution Plan using the scaler-bound training contract.
