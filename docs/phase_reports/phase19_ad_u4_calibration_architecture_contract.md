# Phase19-AD-U4 Calibration Architecture Contract

## Final Judgment

```text
PHASE19_AD_U4_CALIBRATION_CONTRACT_COMPLETE
PHASE19_AD_U4_HUMAN_REVIEW_REQUIRED
```

Status:

```text
PASS
```

This phase did not implement or execute:

```text
Calibration
Validation
Unified Generation
Accepted Generation
Runtime switch
Broker use
```

## Role

Calibration is a formal generation step:

```text
Training
-> Calibration
-> Validation
-> Unified Generation
-> Accepted Generation
```

Training Output must not be passed directly to Runtime. Runtime may later consume calibrated scoring only through an Accepted Generation.

## Candidate Contract

Candidate flow:

```text
Training Output
-> Calibration Input
-> Calibration Method
-> Calibration Artifact
-> Calibrated Candidate Score
```

Source artifact:

```text
artifact_id = corrective_candidate_f08273d45cddf3b4
artifact_status = TRAINING_OUTPUT
model_hash = f08273d45cddf3b41bb4f62e237f635f49a6146ef8b46bfeeb80340e17134ecb
scaler_artifact_id = candidate_scaler_bf5a01d7d9d39674
scaler_artifact_hash = f731db7894e214444d34fac656e37c4a28cb6429c297d8f7ca252b34bdb31f94
```

Candidate output semantics:

```text
calibrated_candidate_probability
range = [0, 1]
higher_is_more_candidate_like = true
runtime_direct_use_allowed = false
```

Candidate method candidates:

```text
Platt Scaling
Isotonic Regression
Temperature Scaling
Identity
Other, review required
```

Recommended review default:

```text
Platt Scaling
```

This is a review recommendation only, not an execution approval.

## Opportunity Contract

Opportunity flow:

```text
Training Output
-> Calibration
-> Normalized Opportunity Score
```

Source artifact:

```text
artifact_id = corrective_opportunity_820e17c08c9844aa
artifact_status = TRAINING_OUTPUT
model_hash = 48f469dddc739d85a544ddeda5682ef0f5c8b3c9ece889cdc8fe5d9f54643966
scaler_artifact_id = opportunity_scaler_820e17c08c9844aa
scaler_artifact_hash = b4e661a834b0f1a9c0b68f4d8ab50e889dc328c528a680b2629fa5f1c8d02484
```

Opportunity output semantics:

```text
normalized_opportunity_score
higher_is_better = true
runtime_direct_use_allowed = false
```

Opportunity method candidates:

```text
Raw
Standardized
Percentile
Rank
Other, review required
```

Recommended review default:

```text
Standardized or Percentile, selected by calibration evidence
```

This is a review recommendation only, not an execution approval.

## Method Investigation

Candidate:

```text
Platt Scaling: stable binary probability calibration, medium data need, high production fit.
Isotonic Regression: flexible monotonic mapping, higher data need, higher overfit risk.
Temperature Scaling: simple low-parameter rescaling, less natural for current sklearn SGD probability output unless logits are exposed.
Identity: acceptable only with explicit no-calibration evidence.
```

Opportunity:

```text
Raw: preserves output but weak comparability.
Standardized: simple z-score normalization with hash-bound mean/std parameters.
Percentile: bounded empirical score, useful for downstream rank/threshold policies.
Rank: robust ordering score, but loses absolute edge magnitude.
```

Method selection is deferred to Human Review.

## Calibration Dataset Contract

Target policy:

```text
Training = prohibited for calibrator fit
Calibration window = required for calibrator fit
Validation window = prohibited for calibrator fit if reserved for formal validation
Test = prohibited for calibrator fit
Recent Holdout = prohibited for calibrator fit
Production = prohibited
```

Current U3-K split issue:

```text
The current split exposes train, validation, test, and recent_holdout.
It does not expose a separately named calibration window.
```

Allowed Human Review resolutions before execution:

```text
Use the existing validation window as Calibration Fit, then reserve test and recent_holdout for downstream validation/review.
Materialize a revised split with explicit calibration and validation windows before calibration execution.
```

No calibration execution may proceed until this dataset decision is approved.

## Calibration Artifact Contract

Required fields:

```text
artifact_id
schema_version
artifact_version
artifact_status
component
created_at
producer
input_hash
source_model_artifact_id
source_model_hash
source_scaler_artifact_id
source_scaler_hash
dataset_revision_id
dataset_content_hash
split_id
split_content_hash
calibration_method
calibration_config
calibration_config_hash
parameters
parameter_hash
calibration_dataset_window
input_score_schema
output_score_schema
lineage
runtime_eligibility
generation_eligibility
accepted
content_hash
```

Allowed statuses:

```text
CALIBRATION_OUTPUT
NOT_APPLICABLE
REVIEW_REQUIRED
REJECTED
```

Missing calibration artifact is not equivalent to an approved no-calibration decision.

## Runtime Contract

Runtime direct use of Training Artifact is prohibited.

Future Runtime resolution order:

```text
Accepted Generation
-> Calibration Artifact
-> Model
-> Scaler
```

Runtime must reject:

```text
Training Artifact direct path
latest calibration
latest model
latest scaler
mtime discovery
manual component directory
Broker/Paper/PnL-derived calibration
```

## Failure Policy

Calibration failure:

```text
Generation禁止
Accepted禁止
Runtime禁止
Broker禁止
```

Validation failure:

```text
Generation禁止
Accepted禁止
Runtime禁止
Broker禁止
```

Partial calibration artifacts remain non-runtime evidence only.

## Human Review Points

Required review:

```text
Calibration Method
Calibration Dataset
Leakage controls
Artifact structure
Runtime connection
Failure Policy
```

## Remaining Risks

```text
Candidate and Opportunity calibration methods are compared but not selected.
Current split lacks explicit calibration window.
Calibration quality thresholds are not yet materialized.
No calibration runner or schema implementation is added in U4.
Runtime integration remains forbidden until later accepted-generation gates.
```

## Evidence Paths

```text
reports/phase19_ad_u4_calibration_architecture_contract/calibration_method_comparison.json
reports/phase19_ad_u4_calibration_architecture_contract/candidate_calibration_contract.json
reports/phase19_ad_u4_calibration_architecture_contract/opportunity_calibration_contract.json
reports/phase19_ad_u4_calibration_architecture_contract/calibration_dataset_contract.json
reports/phase19_ad_u4_calibration_architecture_contract/calibration_artifact_contract.json
reports/phase19_ad_u4_calibration_architecture_contract/runtime_contract_review.json
reports/phase19_ad_u4_calibration_architecture_contract/failure_policy.json
reports/phase19_ad_u4_calibration_architecture_contract/remaining_risks.json
reports/phase19_ad_u4_calibration_architecture_contract/final_judgment.json
reports/phase_reports/phase19_ad_u4_calibration_architecture_contract.json
```

## Next Step

```text
PHASE19_AD_U4_HUMAN_REVIEW_REQUIRED
```
