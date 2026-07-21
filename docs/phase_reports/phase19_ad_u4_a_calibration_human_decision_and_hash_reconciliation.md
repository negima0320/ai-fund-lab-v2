# Phase19-AD-U4-A Calibration Human Decision Materialization and Opportunity Source Hash Reconciliation

## Final Judgment

```text
PHASE19_AD_U4_A_PASS
PHASE19_AD_U4_B_CALIBRATION_IMPLEMENTATION_PLAN_READY
```

Supporting:

```text
HUMAN_REVIEW_MATERIALIZED
CALIBRATION_DATASET_USAGE_CONTRACT_PASS
CALIBRATION_METHOD_DECISION_PASS
OPPORTUNITY_SOURCE_MODEL_HASH_RECONCILED
AUTHORITATIVE_SOURCE_HASH_DECIDED
ARTIFACT_BINDING_CONTRACT_PASS
R4_DOCUMENTATION_GAP_RESOLVED
NO_CALIBRATION_EXECUTION_PASS
NO_RUNTIME_MUTATION_PASS
NO_BROKER_WRITE_PASS
```

Forbidden declarations were not made:

```text
BUY_READY
PRODUCTION_READY
ACCEPTED_GENERATION_CREATED
RUNTIME_TRANSITION_COMPLETE
```

## Human Review Materialization

Reviewer:

```text
user:negishi
```

Decision:

```text
APPROVE_WITH_CALIBRATION_DATASET_AND_EVALUATION_POLICY
```

This approval materializes the U4 Human Review decision as contract evidence only. Calibration implementation, calibration execution, formal validation, generation, accepted decision, runtime transition, and broker use remain prohibited.

## Phase19 Evaluation Policy

Phase19 formal model quality evaluation is one formal cycle by default.

Same-generation rerun is allowed only for execution failure, evidence write failure, deterministic infrastructure failure, and only when model, config, data, and contract remain unchanged.

Corrective rerun requires a new artifact, new review, changed hash, reason, and documentation of previous test observation. Unlimited tuning after observing test is prohibited.

## Calibration Dataset Usage

The existing U3-K split bytes remain unchanged. The dataset usage contract reclassifies existing split roles for Phase19 calibration and validation:

```text
train:
model fit / imputer fit / scaler fit only

validation:
CALIBRATION_FIT_WINDOW

test:
FORMAL_VALIDATION_PRIMARY_WINDOW

recent_holdout:
AUXILIARY_FINAL_ROBUSTNESS_WINDOW
```

The `validation` split name remains unchanged in the underlying split artifact, but its Phase19 formal meaning is now `CALIBRATION_FIT_WINDOW`.

Dataset Usage Contract hash:

```text
c262c7a2370e942ece73b9a16dd0d76d30aaca11899d39b53cde77c1ca081d6f
```

## Candidate Method Decision

```text
APPROVE_PLATT_SCALING
```

Candidate calibration input is Candidate raw score plus validation labels. The output is:

```text
calibrated_candidate_probability
```

The output range must be `[0, 1]`, higher is better, and Platt must be fit only on the validation window reclassified as `CALIBRATION_FIT_WINDOW`.

Identity comparison is required. If Platt worsens main metrics versus Identity, the result must be:

```text
CANDIDATE_CALIBRATION_REVIEW_REQUIRED
```

## Opportunity Method Decision

```text
APPROVE_STANDARDIZED_PRIMARY
PERCENTILE_DIAGNOSTIC_ONLY
```

Opportunity primary output is:

```text
normalized_opportunity_score
```

Primary method is `STANDARDIZED`, fit only on validation-window parameters. Percentile is diagnostic only and must not become the runtime primary score in this contract.

Ranking preservation is required.

## Runtime Acceptance Separation

Phase19 evaluates AI model, scaler, calibration, formal validation, generation eligibility, and artifact integrity.

Later phases must separately evaluate accepted generation resolution, runtime connection, daily inference, order decision, approval, submit, execution, broker, ledger, report, notification, multi-day operation, and safety stop.

Phase19 `test` and `recent_holdout` evidence must not be treated as runtime acceptance evidence.

## Calibration Quality Gate

Candidate gate requires:

```text
no NaN/Inf
output in [0,1]
monotonic mapping
no collapse
metrics computable
validation-only fit
test/recent_holdout transform/eval only
```

Opportunity gate requires:

```text
no NaN/Inf
fitted std > 0
ordering preserved
no explosion/collapse
validation-only fit
test/recent_holdout transform/eval only
```

## Opportunity Model Hash Reconciliation

Reported values:

```text
U3-K Markdown value:
820e17c08c9844aa953c9bcce880ffd671a900cbc3dac062eddd7dafcc6c7548

R5 / U4 value:
48f469dddc739d85a544ddeda5682ef0f5c8b3c9ece889cdc8fe5d9f54643966
```

Actual rehash results:

```text
Opportunity model.pkl raw-byte SHA256:
48f469dddc739d85a544ddeda5682ef0f5c8b3c9ece889cdc8fe5d9f54643966

Opportunity scaler.pkl raw-byte SHA256:
820e17c08c9844aa953c9bcce880ffd671a900cbc3dac062eddd7dafcc6c7548
```

Classification:

```text
Primary: CASE_A
Secondary documentation issue: CASE_B
```

`820e17...` is a legitimate hash target, but it is the Opportunity scaler raw-byte hash, not the Opportunity model raw-byte hash. Prior U3-K Markdown used that scaler hash where Opportunity model hash and model artifact id should have used `48f469...`.

No artifact overwrite/update and no different artifact reference were detected.

## Authoritative Source Hash

Authoritative Opportunity source model artifact:

```text
corrective_opportunity_48f469dddc739d85
```

Authoritative Opportunity source model hash for future Calibration artifact binding:

```text
48f469dddc739d85a544ddeda5682ef0f5c8b3c9ece889cdc8fe5d9f54643966
```

`820e17...` must be used only as the Opportunity source scaler hash.

## Artifact Binding

Future Calibration artifacts must bind:

```text
Dataset Revision
Split Artifact
Dataset Usage Contract
Source Model Artifact
Authoritative Source Model Hash
Source Scaler Artifact
Source Scaler Hash
Feature Order
Calibration Method
Calibration Config
Fit Window
Quality Gate Contract
```

Forbidden resolution modes:

```text
latest
mtime
directory scan without hash binding
manual unbound path
```

## R4 Documentation Gap

The missing R4 Markdown report was created from existing R4 JSON evidence only:

```text
docs/phase_reports/phase19_ad_r4_opportunity_split_hash_reconciliation_review.md
```

R4 judgment and evidence were preserved.

## Non-Execution

The following remain not executed:

```text
Calibration implementation
Calibration execution
Formal Validation execution
recent_holdout evaluation
Unified Generation
Accepted Decision
Accepted Generation
Runtime pointer write
Runtime connection test
BUY restart
Broker write
Training
```

## Evidence

```text
reports/phase_reports/phase19_ad_u4_a_calibration_human_decision_and_hash_reconciliation.json
reports/phase19_ad_u4_a_calibration_human_decision_and_hash_reconciliation/
```

