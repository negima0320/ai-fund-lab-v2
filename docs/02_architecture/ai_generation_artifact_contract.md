# AI Generation Artifact Contract

This document is a permanent Architecture Source of Truth for Phase19 AD-U3 generation output artifacts. It defines what training, calibration, validation, generation, acceptance, and runtime-consumable manifests must emit before any Candidate or Opportunity model training is allowed to create a new generation.

It complements:

```text
docs/02_architecture/autonomous_ai_operations_architecture.md
docs/02_architecture/ai_training_and_generation_lifecycle.md
docs/01_requirements/phase_roadmap.md
```

## Scope

This contract covers:

```text
Candidate Training Artifact
Opportunity Training Artifact
Calibration Artifact
Validation Artifact
Runtime Baseline Artifact
Unified Generation Candidate
Accepted Decision
Accepted Generation Manifest
```

It does not authorize training by itself. It fixes the artifact shape, authority boundary, immutable hash bindings, serialization expectations, reproducibility evidence, and runtime eligibility rules that future training implementation must satisfy.

## Common Artifact Fields

All component artifacts must carry:

```text
artifact_id
artifact_type
artifact_version
artifact_status
created_at
producer
source_phase
component
generation_candidate_id
content_hash
schema_version
authority
```

All component artifacts must also bind inputs by identity and hash:

```text
dataset_input_contract_id
dataset_revision_id
dataset_content_hash
dataset_schema_hash
dataset_lineage_hash
split_id
split_content_hash
rolling_split_policy_hash
corporate_action_policy_hash
model_quality_policy_hash
feature_schema_identity
label_schema_identity
trading_calendar_identity
target_horizon_business_days
embargo_business_days
bootstrap_or_retraining
```

Path-only references are not authority. A path is usable only when the referenced content hash and schema hash match the manifest.

## Status Vocabulary

Allowed artifact statuses are:

```text
DRAFT
TRAINING_OUTPUT
FIXTURE_TRAINING_OUTPUT
VALIDATION_PENDING
VALIDATION_PASS
VALIDATION_BLOCK
GENERATION_CANDIDATE
REVIEW_REQUIRED
ACCEPTED
REJECTED
RETIRED
INVALIDATED
NOT_APPLICABLE
```

`FIXTURE_TRAINING_OUTPUT` is allowed only for Phase19 technical smoke artifacts and must carry `runtime_eligibility = false`, `generation_eligibility = false`, and `accepted = false`. Ambiguous aliases such as `latest`, `successful`, `newest`, `current_model`, or mtime-based selection are prohibited. Runtime eligibility is limited to an `ACCEPTED` Accepted Generation Manifest.

## Candidate Model Artifact

Schema:

```text
schemas/ai_lifecycle/candidate_model_artifact.schema.json
```

The Candidate artifact must record model family, serialization format, model file, model hash, training code version, training config and config hash, random seed, determinism contract, feature columns, feature and label schema hashes, train/validation/test/recent-holdout windows, training statistics, Model Quality Policy result, and prohibited input audit result.

It must not contain a latest-model alias, unbound model file, dataset path only, split recomputation result, Runtime input, Broker input, Paper input, or performance-derived training feature.

## Opportunity Model Artifact

Schema:

```text
schemas/ai_lifecycle/opportunity_model_artifact.schema.json
```

The Opportunity artifact follows the Candidate artifact contract and additionally binds the Candidate dependency contract, Candidate feature or score dependency, Candidate model hash if applicable, opportunity universe definition, and ranking/classification contract.

If Opportunity training consumes Candidate predictions or scores, those predictions must be bound to the Dataset Revision, Split, Candidate Artifact, and Candidate hash that produced them. Future leakage and same-window contamination are prohibited.

## Calibration Artifact

Schema:

```text
schemas/ai_lifecycle/calibration_artifact.schema.json
```

Calibration must record method, config, config hash, source model artifact ids and hashes, calibration dataset window, input and output schemas, pre/post calibration metrics, and calibration quality result.

When calibration is intentionally not used, the artifact status must be `NOT_APPLICABLE`. Missing calibration artifacts must not be interpreted as equivalent to an approved no-calibration decision.

## Scaler Artifact

Schema:

```text
schemas/ai_lifecycle/scaler_artifact.schema.json
```

Scaler artifacts are Generation component artifacts. They are required whenever a model artifact declares a scaled preprocessing pipeline. A scaler artifact records scaler method, library version, scaler file, scaler hash, scaler config hash, fitted parameters, parameter hash, train-window fit boundary, input feature order, scaled feature columns, excluded feature columns, feature dtypes, Dataset Revision binding, Split binding, Model Quality Policy binding, Corrective Action Policy binding, training config hash, training code commit, environment fingerprint, runtime eligibility, generation eligibility, accepted flag, authority, and content hash.

Allowed scaler statuses are:

```text
SCALER_TRAINING_OUTPUT
FIXTURE_SCALER_OUTPUT
INVALID
REJECTED
```

Scaler fit must use Training Window data only. Validation, Test, and Recent Holdout are transform-only. Candidate and Opportunity scalers are independent artifacts; cross-component scaler reuse is prohibited.

Scaler artifacts are not Runtime eligible by themselves. Runtime may use a scaler only through an Accepted Generation Manifest that binds the matching model artifact, scaler artifact, feature order, and hashes.

## Validation Artifact

Schema:

```text
schemas/ai_lifecycle/validation_artifact.schema.json
```

Validation must record validated artifact ids and hashes, dataset binding, split binding, schema binding, lineage binding, Model Quality Policy result, leakage guard result, prohibited input guard result, compatibility result, calibration result, runtime interface compatibility, final judgment, block reasons, and review-required reasons.

Validation is evidence, not a training feature. Validation outputs must not be joined into future training data.

## Runtime Baseline Artifact

Schema:

```text
schemas/ai_lifecycle/runtime_baseline_artifact.schema.json
```

Runtime Baseline records expected Candidate input schema, expected Opportunity input schema, expected output schema, runtime feature contract, runtime model loader contract, dependency versions, compatibility hash, required runtime capabilities, and forbidden runtime fallbacks.

Runtime Baseline must not contain Runtime State, Broker Snapshot, Current, Pending, Ledger, Safety state, or trading positions.

For Phase19-AO, Recent Holdout is not a Runtime Baseline source. The Runtime Baseline source is the Formal Validation / Corrective Re-evaluation test-window inference outputs and CandidateTop50 selection outputs.

The Phase19 Runtime Baseline must record at minimum:

```text
baseline_id
generation_candidate_id
source_validation_id
source_corrective_run_id
source_business_date_start
source_business_date_end
candidate_feature_schema_hash
candidate_feature_order_hash
candidate_feature_distribution_summary
candidate_score_distribution_summary
candidate_pass_ratio
candidate_population_summary
opportunity_feature_schema_hash
opportunity_feature_order_hash
opportunity_feature_distribution_summary
opportunity_score_distribution_summary
top5_summary
top10_summary
top20_summary
finite_checks
collapse_checks
explosion_checks
runtime_baseline_policy_version
threshold_policy
created_at
content_hash
schema_version
```

The baseline is operational health and drift comparison evidence only. It must not overwrite Formal Validation, rerun Dual Gate, or directly drive daily Runtime BUY decisions.

## Unified Generation Candidate

Schema:

```text
schemas/ai_lifecycle/unified_generation_candidate.schema.json
```

The Unified Generation Candidate binds Candidate, Opportunity, Calibration, Validation, Runtime Baseline, Dataset Revision, Split, Policy, Schema, and Lineage hashes under one generation candidate id.

Its status is `GENERATION_CANDIDATE`. It is the Human Review target, not Runtime authority.

## Accepted Decision

Schema:

```text
schemas/ai_lifecycle/accepted_decision.schema.json
```

Accepted Decision is the promotion authority. It records the generation candidate id, generation manifest hash, decision, reviewer, reviewed time, reason, reviewed generation hash, accepted generation id when approved, rejection reasons, conditions, authority, and decision hash.

Codex must not be recorded as the Human Reviewer. Automatic Validation PASS and Accepted Decision are separate events.

For Phase19-AO, Accepted Generation entry requires:

```text
Candidate Corrective Re-evaluation PASS
Opportunity Global Safety/Sanity Gate PASS
Opportunity Selection Utility Gate PASS
Dual Gate PASS
Independent Review PASS
Unified Generation binding PASS
Schema PASS
Hash PASS
Runtime Baseline PASS
Freshness Metadata PASS
Accepted Materializer Compatibility PASS
Authority History Path PASS
```

Recent Holdout is not a required Phase19 Accepted Generation entry gate and must remain unaccessed / unused.

## Accepted Generation Manifest

Schema:

```text
schemas/ai_lifecycle/accepted_generation_manifest.schema.json
```

Accepted Generation Manifest is the only model-generation artifact family Runtime may consume. It records accepted generation id/version, acceptance authority, source generation candidate and hash, accepted decision and hash, component artifact ids/hashes, policy hashes, dataset revision ids, split ids, schema hashes, lineage hashes, runtime baseline hash, immutability status, runtime eligibility status, manifest hash, and authority.

Phase19 Accepted Generation Manifest must also bind generation freshness metadata:

```text
raw_data_max_date_at_generation
normalized_data_max_date_at_generation
dataset_source_max_date
dataset_target_max_date
label_safe_cutoff
candidate_training_cutoff
opportunity_training_cutoff
calibration_cutoff
validation_cutoff
generation_created_at
freshness_policy_version
effective_from
accepted_generation_age_origin
```

Accepted Materialization generates `accepted_at`, `effective_from`, and `accepted_generation_age_origin`. Runtime State / Monitoring later generates runtime-loaded generation freshness and inference feature freshness.

## Phase19-AO Responsibility Boundary

Accepted Generation Materializer owns:

```text
Unified Generation Candidate validation
Accepted Decision binding
Runtime Baseline binding
Freshness Metadata binding
Authority Decision binding
Previous Generation reference
Accepted Manifest creation
Aggregate hash
Authority history append preparation
```

Runtime Consumer Adapter owns:

```text
Accepted Manifest parsing
Candidate model loading
Candidate scaler loading
Candidate calibration loading
Candidate feature-order enforcement
Opportunity model loading
Opportunity scaler loading
Opportunity calibration loading
Opportunity feature-order enforcement
hash validation
schema validation
fail-closed behavior
```

Runtime Transition owns:

```text
PREPARED
STAGED
SMOKE_VERIFIED
COMMITTED
ABORTED
ROLLED_BACK
Runtime reload
atomic pointer switch
rollback pointer update
```

## Output Paths

Generation candidate artifacts should be written append-only under:

```text
.runtime/ai_lifecycle/generations/<generation_candidate_id>/
  candidate/
  opportunity/
  scalers/
  calibration/
  validation/
  runtime_baseline/
  generation_manifest.json
```

Accepted manifests should be written append-only under:

```text
.runtime/ai_lifecycle/accepted_generations/<accepted_generation_id>/
  accepted_generation_manifest.json
```

Directory names and mtimes are never authority. All consumers must verify content hashes.

## Serialization And Compatibility

Model serialization must be declared by each model artifact. Existing sklearn pickle output may be used only as an internal, content-hash verified, accepted-manifest-bound format until replaced by a safer serialization format.

Runtime loaders must reject untrusted external paths, path traversal, unsigned artifacts, unreviewed artifacts, hash mismatches, manifest/model mismatches, and ambiguous latest-model discovery. Artifacts must record Python version, library versions, feature dtypes, missing-value representation, categorical encoding, score output type, and probability output semantics.

## Reproducibility

Training artifacts must record random seed, library versions, threading/parallelism settings, training code commit, config hash, dataset hash, split hash, and environment fingerprint.

Unless future evidence proves bitwise reproduction, the guarantee level is:

```text
REPRODUCIBLE_WITH_TOLERANCE
```

Validation must declare the tolerance boundary used for reproducibility checks.

## Security And Integrity

The contract blocks:

```text
path traversal
arbitrary external model path
untrusted pickle load
hash mismatch
manifest/model mismatch
unsigned Accepted Generation
unreviewed Accepted Generation
```

Runtime must fail closed if Accepted Generation authority cannot be resolved or verified.

## Prohibited Artifact Content

Model and generation artifacts must not contain:

```text
Broker credentials
API token
Runtime State
Paper Ledger
Broker Snapshot
cash
portfolio value
selected / bought outcomes
Backtest profit
Runtime PnL
Test result as training input
Audit result as training input
future information
```

Evidence may reference audits, but those audits must not become training features or automatic promotion metrics.
