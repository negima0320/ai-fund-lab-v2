# Phase19-AD-U4-B Calibration Implementation Plan

## Final Judgment

```text
PHASE19_AD_U4_B_IMPLEMENTATION_PLAN_COMPLETE
PHASE19_AD_U4_C_HUMAN_REVIEW_REQUIRED
```

Supporting:

```text
CANDIDATE_PIPELINE_PLAN_PASS
OPPORTUNITY_PIPELINE_PLAN_PASS
QUALITY_METRICS_PLAN_PASS
CALIBRATION_ARTIFACT_SCHEMA_PLAN_PASS
HASH_INVENTORY_CONTRACT_PASS
RUNNER_ARCHITECTURE_PLAN_PASS
FAILURE_POLICY_PASS
VALIDATION_CHECKLIST_PASS
NO_CALIBRATION_IMPLEMENTATION_PASS
NO_CALIBRATION_EXECUTION_PASS
NO_VALIDATION_EXECUTION_PASS
NO_RUNTIME_MUTATION_PASS
NO_BROKER_WRITE_PASS
```

Forbidden declarations were not made:

```text
CALIBRATION_EXECUTED
VALIDATION_EXECUTED
UNIFIED_GENERATION_CREATED
ACCEPTED_GENERATION_CREATED
RUNTIME_TRANSITION_COMPLETE
BUY_READY
PRODUCTION_READY
```

## Scope

This phase converts the approved U4-A Calibration Contract into an implementation-ready execution plan.

This phase does not implement or execute Calibration, Validation, Unified Generation, Accepted Generation, Runtime transition, or Broker use.

## Candidate Pipeline

Planned flow:

```text
Candidate Training Output
-> Validation Window Scores
-> Platt Scaling Fit
-> Calibration Artifact
-> Calibrated Candidate Probability
```

Implementation responsibilities:

```text
Input Reader
Calibration Fit
Calibration Diagnostics
Artifact Writer
Hash Generator
Schema Validation
```

The Input Reader must resolve the Candidate source artifact from explicit U4-A bindings. `latest`, mtime, and unbound manual paths are prohibited.

Platt Scaling must fit only on the existing `validation` split reclassified by U4-A as:

```text
CALIBRATION_FIT_WINDOW
```

Identity comparison is mandatory. If Platt worsens main metrics versus Identity, the result must be:

```text
CANDIDATE_CALIBRATION_REVIEW_REQUIRED
```

## Opportunity Pipeline

Planned flow:

```text
Opportunity Training Output
-> Validation Window Scores
-> Standardization Fit
-> Calibration Artifact
-> Normalized Opportunity Score
```

Standardization fit parameters:

```text
mean
standard deviation
approved clipping if required
```

The primary runtime-intended score is:

```text
normalized_opportunity_score
```

Percentile output is diagnostic only:

```text
PERCENTILE_DIAGNOSTIC_ONLY
```

The authoritative Opportunity source model hash is:

```text
48f469dddc739d85a544ddeda5682ef0f5c8b3c9ece889cdc8fe5d9f54643966
```

The Opportunity source scaler hash is:

```text
820e17c08c9844aa953c9bcce880ffd671a900cbc3dac062eddd7dafcc6c7548
```

These must remain separate fields. Ambiguous `model_hash` without target explanation is prohibited.

## Quality Metrics

Candidate minimum metrics:

```text
Brier Score
Log Loss
Expected Calibration Error
Calibration Curve
Prediction Histogram
Monotonicity
Finite Check
Collapse Check
Identity comparison
```

Opportunity minimum metrics:

```text
mean
std
quantiles
ordering preservation
Spearman Rank Correlation
outlier rate
clipping rate
finite ratio
collapse
explosion
Percentile diagnostic distribution
```

Common diagnostics:

```text
Timing
Memory
Input Count
Output Count
NaN Count
Inf Count
Parameter Count
Hash Verification
```

## Artifact Schema

Planned schema path:

```text
schemas/ai_lifecycle/calibration_artifact.schema.json
```

Artifact status:

```text
CALIBRATION_OUTPUT
```

Required fields include:

```text
artifact_id
artifact_status
schema_version
artifact_version
created_at
producer
source_phase
component
dataset_revision
dataset_revision_id
dataset_content_hash
dataset_schema_hash
dataset_lineage_hash
split_id
split_content_hash
dataset_usage_contract
dataset_usage_contract_hash
source_model_artifact
source_model_artifact_id
source_model_hash
source_model_hash_target
source_scaler_artifact
source_scaler_artifact_id
source_scaler_hash
source_scaler_hash_target
feature_order
feature_schema_identity
calibration_method
calibration_method_version
calibration_config
calibration_config_hash
calibration_parameters
calibration_parameter_hash
fit_window
fit_window_role
input_score_schema
output_score_schema
quality_metrics
quality_gate_result
hash_inventory
runtime_eligibility
generation_eligibility
accepted
content_hash
```

Default authority flags:

```text
runtime_eligibility = false
generation_eligibility = false
accepted = false
```

## Hash Inventory

Each Calibration Artifact must include explicit target definitions:

```text
artifact_file_sha256:
raw bytes of written calibration artifact manifest file

serialized_model_sha256:
raw bytes of source model serialization file

serialized_scaler_sha256:
raw bytes of source scaler serialization file

calibration_parameter_sha256:
canonical JSON of calibration_parameters only

manifest_sha256:
raw bytes of persisted manifest file

content_sha256:
canonical JSON manifest payload excluding content_hash/hash_inventory self references defined by schema
```

Required cross-checks:

```text
serialized_model_sha256 == source_model_hash
serialized_scaler_sha256 == source_scaler_hash
content_sha256 == content_hash
artifact_file_sha256 / manifest_sha256 recorded after write
```

## Runner Architecture

Planned module separation:

```text
Calibration Runner
-> Candidate Module
-> Opportunity Module
-> Artifact Writer
-> Evidence Writer
```

Runtime dependency is prohibited for all modules.

Execution order:

```text
preflight
Candidate calibration
Candidate gate
Opportunity calibration
Opportunity gate
artifact schema validation
hash verification
final evidence
```

## Failure Policy

Candidate failure:

```text
CANDIDATE_CALIBRATION_REVIEW_REQUIRED
Opportunity calibration start prohibited
```

Opportunity failure:

```text
OPPORTUNITY_CALIBRATION_REVIEW_REQUIRED
Validation and Generation prohibited
```

Hash mismatch:

```text
REVIEW_REQUIRED
Stop before downstream evaluation
```

Runtime or Broker touch:

```text
BLOCK
Reject run as out-of-scope
```

## Validation Checklist

Pre-implementation checks:

```text
JSON Schema exists/updated for Calibration Artifact
Hash Inventory contract fields represented in schema
Artifact Binding consumed from U4-A evidence
Dataset Usage Contract consumed from U4-A evidence
Candidate/Opportunity method decisions consumed from U4-A evidence
```

Runner preflight checks:

```text
source artifact status == TRAINING_OUTPUT
runtime_eligibility == false
accepted == false
source model hash matches raw serialized bytes
source scaler hash matches raw serialized bytes
split hash matches bound split
dataset usage contract hash matches U4-A
fit window role == CALIBRATION_FIT_WINDOW
```

Artifact validation checks:

```text
JSON Schema validation
Hash Inventory completeness
Artifact Binding cross-reference
Contract compliance
content_hash recomputation
no ambiguous model_hash-only field
no runtime/broker/current/pending/ledger/safety content
```

## Non-Execution

The following were not implemented or executed in U4-B:

```text
Calibration implementation
Calibration execution
Validation execution
Unified Generation
Accepted Generation
Runtime switch
Broker use
```

## Remaining Risks

Actual calibration quality metrics are unknown until a later approved execution phase.

Formal test and recent_holdout evaluation remain intentionally unexecuted.

Earlier Markdown reports contain a known Opportunity artifact id/hash narrative inconsistency; future work must use the U4-A authoritative source hash decision.

## Evidence

```text
reports/phase_reports/phase19_ad_u4_b_calibration_implementation_plan.json
reports/phase19_ad_u4_b_calibration_implementation_plan/
```

