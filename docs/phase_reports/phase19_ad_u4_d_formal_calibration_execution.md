# Phase19-AD-U4-D Formal Calibration Execution

## Final Judgment

```text
PHASE19_AD_U4_D_FORMAL_CALIBRATION_COMPLETE
PHASE19_AD_R6_CALIBRATION_REVIEW_READY
```

Supporting:

```text
CANDIDATE_FORMAL_CALIBRATION_ARTIFACT_CREATED
CANDIDATE_CALIBRATION_PASS
OPPORTUNITY_FORMAL_CALIBRATION_ARTIFACT_CREATED
OPPORTUNITY_CALIBRATION_PASS
VALIDATION_WINDOW_ONLY_PASS
HASH_INVENTORY_PASS
ARTIFACT_SCHEMA_PASS
SOURCE_BINDING_PASS
NO_RUNTIME_BROKER_MUTATION_PASS
FORMAL_VALIDATION_NOT_EXECUTED
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

## Preflight

Formal run id:

```text
phase19_ad_u4_d_formal_calibration_0d5fdc96b879d5f1
```

Runtime output:

```text
.runtime/ai_lifecycle/calibration_outputs/phase19_ad_u4_d_formal_calibration_0d5fdc96b879d5f1/
```

Preflight status:

```text
PASS
```

Candidate source:

```text
artifact_id = corrective_candidate_f08273d45cddf3b4
model raw-byte SHA256 = f08273d45cddf3b41bb4f62e237f635f49a6146ef8b46bfeeb80340e17134ecb
scaler raw-byte SHA256 = bf5a01d7d9d39674a21faf2082d3a766f19eec17a1dad53c679b39cd4a35448b
scaler artifact content hash = f731db7894e214444d34fac656e37c4a28cb6429c297d8f7ca252b34bdb31f94
```

The U4-D instruction text listed `f731...` as Candidate scaler raw-byte SHA256. Preflight reconciled this as the scaler artifact content hash, not the scaler file raw-byte hash. The execution used explicit U4-A source binding and the actual `scaler.pkl` raw-byte SHA256 `bf5...`.

Opportunity source:

```text
artifact_id = corrective_opportunity_48f469dddc739d85
model raw-byte SHA256 = 48f469dddc739d85a544ddeda5682ef0f5c8b3c9ece889cdc8fe5d9f54643966
scaler raw-byte SHA256 = 820e17c08c9844aa953c9bcce880ffd671a900cbc3dac062eddd7dafcc6c7548
```

## Dataset Window Usage

```text
train = not accessed
validation = accessed as CALIBRATION_FIT_WINDOW
test = not accessed
recent_holdout = not accessed
```

## Candidate Formal Calibration

Pipeline:

```text
Candidate Model
-> validation features
-> Imputer
-> Scaler
-> raw Candidate score
-> Platt Scaling fit
-> calibrated_candidate_probability
```

Result:

```text
CANDIDATE_CALIBRATION_PASS
```

Counts:

```text
sample_count = 934105
positive_count = 89240
negative_count = 844865
class_balance = 0.09553529849428062
```

Platt parameters were written to:

```text
reports/phase19_ad_u4_d_formal_calibration_execution/candidate_calibration_parameters.json
```

## Candidate Identity Comparison

```text
Identity Brier Score = 0.19288417381731715
Platt Brier Score = 0.08594154907100099

Identity Log Loss = 0.5819856546088178
Platt Log Loss = 0.3058207527066204

main_metric_worsened_vs_identity = false
```

Candidate Quality Gate:

```text
PASS
```

## Opportunity Formal Calibration

Pipeline:

```text
Opportunity Model
-> validation features
-> Imputer
-> Scaler
-> raw Opportunity prediction
-> validation mean/std fit
-> normalized_opportunity_score
```

Result:

```text
OPPORTUNITY_CALIBRATION_PASS
```

Counts and parameters:

```text
sample_count = 11063
standardization_mean = -0.048945486495779664
standardization_std = 0.08006253283392056
clipping = disabled
percentile = diagnostic_only
```

Opportunity Quality Gate:

```text
PASS
```

Required checks:

```text
finite_ratio = 1.0
ordering_preservation = true
Spearman rank correlation = 1.0
collapse = false
explosion = false
clipping_rate = 0.0
```

## Artifact Validation

Candidate Calibration Artifact:

```text
artifact_status = CALIBRATION_OUTPUT
runtime_eligibility = false
generation_eligibility = false
accepted = false
schema_validation = PASS
hash_inventory = PASS
```

Opportunity Calibration Artifact:

```text
artifact_status = CALIBRATION_OUTPUT
runtime_eligibility = false
generation_eligibility = false
accepted = false
schema_validation = PASS
hash_inventory = PASS
```

## Hash Inventory

Both Calibration Artifacts include:

```text
artifact_file_sha256
serialized_model_sha256
serialized_scaler_sha256
calibration_parameter_sha256
manifest_sha256
content_sha256
```

Cross-checks:

```text
serialized_model_sha256 == source model raw-byte SHA256
serialized_scaler_sha256 == source scaler raw-byte SHA256
content_sha256 == recomputed canonical content SHA256
```

Result:

```text
PASS
```

## Source Binding

Source binding result:

```text
Candidate = PASS
Opportunity = PASS
```

No `latest`, mtime, directory-based fallback, implicit source selection, or unbound manual path was used.

## Regression

```text
python3 -m pytest tests/ai_lifecycle/test_phase19_ad_u4_c_calibration_implementation.py
5 passed

py_compile
PASS

Formal execution contract validation
PASS

JSON validation
PASS
```

Formal execution warning classification:

```text
ENVIRONMENT_CPU_INFO_WARNING_ONLY_NO_CALIBRATION_WARNING_RECORDED
```

## Non-Mutation

The following were not executed:

```text
Formal Validation execution
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

## Remaining Risks

Independent Calibration Review has not yet been performed.

`test` and `recent_holdout` remain intentionally unused in U4-D.

Future artifacts must continue using explicit hash target fields to avoid confusing raw-byte hashes and artifact content hashes.

## Evidence

```text
reports/phase_reports/phase19_ad_u4_d_formal_calibration_execution.json
reports/phase19_ad_u4_d_formal_calibration_execution/
.runtime/ai_lifecycle/calibration_outputs/phase19_ad_u4_d_formal_calibration_0d5fdc96b879d5f1/
```

