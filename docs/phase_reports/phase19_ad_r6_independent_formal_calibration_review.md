# Phase19-AD-R6 Independent Formal Calibration Review

## Final Judgment

```text
PHASE19_AD_R6_PASS
PHASE19_AD_U5_FORMAL_VALIDATION_READY
```

Supporting:

```text
SOURCE_IDENTITY_PASS
DATASET_WINDOW_SEPARATION_PASS
CANDIDATE_CALIBRATION_REVIEW_PASS
OPPORTUNITY_CALIBRATION_REVIEW_PASS
ARTIFACT_CONTRACT_PASS
HASH_INVENTORY_PASS
QUALITY_GATE_CONSISTENCY_PASS
FAILURE_POLICY_PASS
REGRESSION_PASS
NON_MUTATION_PASS
FORMAL_VALIDATION_READINESS_PASS
```

Forbidden declarations were not made:

```text
FORMAL_VALIDATION_PASS
UNIFIED_GENERATION_CREATED
ACCEPTED_GENERATION_CREATED
RUNTIME_TRANSITION_COMPLETE
BUY_READY
PRODUCTION_READY
```

## Scope

Reviewed run:

```text
phase19_ad_u4_d_formal_calibration_0d5fdc96b879d5f1
```

This review did not execute Formal Validation, test performance review, recent_holdout performance review, Unified Generation, Accepted Generation, Runtime integration, or Broker operation.

## Source Identity Review

Candidate source identity:

```text
source model raw-byte SHA256:
f08273d45cddf3b41bb4f62e237f635f49a6146ef8b46bfeeb80340e17134ecb

source scaler raw-byte SHA256:
bf5a01d7d9d39674a21faf2082d3a766f19eec17a1dad53c679b39cd4a35448b

source scaler artifact content hash:
f731db7894e214444d34fac656e37c4a28cb6429c297d8f7ca252b34bdb31f94
```

Opportunity source identity:

```text
source model raw-byte SHA256:
48f469dddc739d85a544ddeda5682ef0f5c8b3c9ece889cdc8fe5d9f54643966

source scaler raw-byte SHA256:
820e17c08c9844aa953c9bcce880ffd671a900cbc3dac062eddd7dafcc6c7548
```

Result:

```text
PASS
```

## Dataset Window Review

Reviewed access:

```text
train = not accessed
validation = accessed only as CALIBRATION_FIT_WINDOW
test = not accessed
recent_holdout = not accessed
```

Result:

```text
PASS
```

## Candidate Calibration Review

Required counts were independently reproduced:

```text
sample_count = 934105
positive_count = 89240
negative_count = 844865
class_balance = 0.09553529849428062
```

Platt parameters are finite:

```text
intercept = -2.1005606155730354
coefficient = 0.5161675365783901
```

Candidate output:

```text
finite = true
range [0,1] = true
collapse_absent = true
monotonicity = PASS
```

Review result:

```text
CANDIDATE_CALIBRATION_REVIEW_PASS
```

## Candidate Metric Recalculation

Independent recomputation:

```text
Identity Brier Score = 0.19288417381731715
Platt Brier Score = 0.08594154907100099

Identity Log Loss = 0.5819856546088178
Platt Log Loss = 0.3058207527066204
```

Comparison:

```text
matches_reported = true
brier_improved = true
log_loss_improved = true
```

## Opportunity Calibration Review

Required values were independently reproduced:

```text
sample_count = 11063
standardization_mean = -0.048945486495779664
standardization_std = 0.08006253283392056
```

Checks:

```text
fit std > 0 = true
finite ratio = 1.0
normalized mean approximately 0 = true
normalized std approximately 1 = true
ordering preserved = true
Spearman = 1.0
collapse = false
explosion = false
clipping rate = 0.0
percentile is not primary output = true
```

Review result:

```text
OPPORTUNITY_CALIBRATION_REVIEW_PASS
```

## Opportunity Metric Recalculation

Independent recomputation matched reported U4-D metrics:

```text
matches_reported = true
```

## Artifact Contract Review

Candidate and Opportunity artifacts both satisfy:

```text
artifact_status = CALIBRATION_OUTPUT
runtime_eligibility = false
generation_eligibility = false
accepted = false
schema_validation = PASS
```

Required bindings are present:

```text
Dataset binding
Split binding
Dataset Usage Contract binding
Source Model binding
Source Scaler binding
Feature Order binding
Calibration Method
Calibration Config
Calibration Parameters
Fit Window
Quality Metrics
Quality Gate
Hash Inventory
Authority flags
```

No unbound path or ambiguous hash target was detected.

## Hash Inventory Review

Candidate and Opportunity artifacts both include and pass independent validation for:

```text
artifact_file_sha256
serialized_model_sha256
serialized_scaler_sha256
calibration_parameter_sha256
manifest_sha256
content_sha256
```

Each hash records:

```text
target
algorithm
canonicalization
self-reference exclusions where applicable
```

Serialized model/scaler raw-byte hashes are explicitly distinct from artifact content hashes unless the bytes are actually identical. No hash target confusion remains in the reviewed artifacts.

## Quality Gate Review

Candidate gate:

```text
PASS
Identityより主要指標は悪化していない
```

Opportunity gate:

```text
PASS
ordering / finite / std / collapse / explosion 条件を満たす
```

No gate relaxation was detected against U4-A/U4-B contracts.

## Failure Policy Review

Reviewed implementation behavior:

```text
Candidate failure -> Opportunity start prohibited
Opportunity failure -> Validation / Generation prohibited
Hash mismatch -> REVIEW_REQUIRED
test/recent_holdout access -> BLOCK policy
Runtime/Broker dependency -> BLOCK policy
```

Result:

```text
PASS
```

## Regression Review

Reviewed U4-D regression:

```text
py_compile = PASS
U4-C pytest = 5 passed
Formal execution contract validation = PASS
JSON validation = PASS
```

Warning classification:

```text
pyarrow CPU info warning = environment-only
Formal Calibration recorded warnings = none
```

## Non-Mutation Review

Confirmed not executed:

```text
Formal Validation
test access
recent_holdout access
Unified Generation creation
Accepted Decision creation
Accepted Generation creation
Runtime pointer write
BUY restart
Broker write
Ledger mutation
```

Result:

```text
PASS
```

## Formal Validation Readiness

Decision:

```text
PHASE19_AD_U5_FORMAL_VALIDATION_READY
```

This authorizes only the next Formal Validation step to use the `test` window for the first time.

Still prohibited:

```text
Unified Generation
Accepted Generation
Runtime Transition
BUY_READY
PRODUCTION_READY
```

## Evidence

```text
reports/phase_reports/phase19_ad_r6_independent_formal_calibration_review.json
reports/phase19_ad_r6_independent_formal_calibration_review/
```

