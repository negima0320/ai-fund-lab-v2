# Phase19-AD-U3-E Contract-Bound Training Runner

## Final Judgment

```text
PHASE19_AD_U3_E_CONTRACT_BOUND_TRAINING_RUNNER_PASS
PHASE19_AD_U3_FORMAL_BOOTSTRAP_EXECUTION_PLAN_READY
```

This report does not declare Candidate training complete, Opportunity training complete, Calibration complete, Unified Generation created, Accepted Generation created, AD-U3 complete, BUY ready, production ready, or Runtime transition complete.

## Training Runner Design

Implemented:

```text
src/ai_fund_lab_v2/ai_lifecycle/ad_u3_contract_bound_training_runner.py
src/ai_fund_lab_v2/ai_lifecycle/ad_u3_training_quality_gate.py
src/ai_fund_lab_v2/ai_lifecycle/ad_u3_training_artifact_writer.py
```

The runner accepts only:

```text
AD-U3 Dataset Input Contract path
Approved Model Quality Policy path
Generation Output Schema directory
Explicit execution mode
```

It rejects direct dataset paths, split overrides, threshold overrides, feature/label overrides, latest/glob discovery, Runtime/Paper/Broker paths, legacy models, accepted component models, random split, and split recomputation.

## Formal Authority

The runner uses the Phase19-AD-U3-A resolver for Dataset Revision, Dataset hash, Feature schema, Label schema, Versioned Split, Policy hash, Calendar identity, Label-safe max, and Bootstrap mode. It does not reinterpret those fields independently.

The approved Model Quality Policy is required:

```text
.runtime/ai_lifecycle/policies/model_quality/phase19_ad_u3_d_model_quality_policy/model_quality_policy.json
```

The policy must have:

```text
policy_status = APPROVED
reviewer = user:negishi
decision = APPROVE
reviewed_policy_hash = policy_hash
authority includes Human Review decision user:negishi
```

## Execution Modes

Implemented modes:

```text
VALIDATE_ONLY
FIXTURE_SMOKE
FORMAL_BOOTSTRAP
FORMAL_RETRAINING
```

Executed in U3-E:

```text
VALIDATE_ONLY
FIXTURE_SMOKE
```

Formal modes are rejected unless both `--confirm` and an approved execution plan artifact are supplied. No approved execution plan exists in U3-E, so Formal Bootstrap is blocked.

## Candidate Training Adapter

The Candidate fixture adapter resolves contract-bound Candidate input, materializes explicit config, fits a fixture-only sklearn SGD classifier on synthetic technical-smoke data, writes staging artifacts, computes model hash, validates the artifact against the U3-D/U3-E schema, and marks the output Runtime-ineligible.

Formal quality result:

```text
NOT_EVALUATED_FOR_ACCEPTANCE
```

Fixture structural result:

```text
PASS
```

## Opportunity Training Adapter

The Opportunity fixture adapter mirrors the Candidate adapter with an sklearn SGD regressor. It records Candidate dependency as a fixture technical binding and states that Candidate predictions are not used as Opportunity training features in this smoke.

Formal quality result:

```text
NOT_EVALUATED_FOR_ACCEPTANCE
```

Fixture structural result:

```text
PASS
```

## Approved Split Usage

The runner consumes Versioned Split definitions from the resolved contract. It does not call `make_time_series_split`, does not use random split, and does not recalculate date boundaries.

Fixture smoke uses an explicitly marked fixture split:

```text
FIXTURE_ONLY
NOT_PRODUCTION_SPLIT
```

## Training Configuration

Candidate and Opportunity configs are fully materialized with component, model family, hyperparameters, random seed, numpy seed, thread count, parallelism, feature columns, label column, missing value strategy, categorical encoding, class weight strategy, serialization format, library versions, Python version, training code commit, and config hash.

## Missing Value Handling

Imputation is fit only on the training window. Validation, test, and recent holdout frames are transform-only. No implicit fillna is treated as an undocumented default.

## Constant Feature Handling

Policy whitelist:

```text
feature__missing_flags_insufficient_history
feature__missing_flags_price
feature__missing_flags_volume
```

The fixture Opportunity constant feature is whitelisted. Unexpected constants block fixture structural quality.

## Determinism / Reproducibility

The runner records random seed, numpy seed, model seed through config, thread count, parallelism, training code commit, config hash, dataset hash, split hash, and environment fingerprint.

Guarantee level:

```text
REPRODUCIBLE_WITH_TOLERANCE
```

## Serialization / Integrity

Fixture smoke uses sklearn pickle as an internal staging-only artifact. Model content hash is computed after serialization and must match the artifact manifest. Runtime direct load is prohibited.

## Artifact Staging

Fixture outputs are written under:

```text
.runtime/ai_lifecycle/training_staging/<run_id>/
```

They are not written to a formal generation directory. They carry:

```text
artifact_status = FIXTURE_TRAINING_OUTPUT
runtime_eligibility = false
generation_eligibility = false
accepted = false
```

## Atomic Failure Handling

Failure handling records staging failure status and leaves:

```text
formal_generation_candidate_created = false
accepted_decision_created = false
runtime_pointer_written = false
broker_write_executed = false
```

## Fixture Technical Smoke

Fixture smoke passed for Candidate and Opportunity. It did not use the formal full Dataset and did not evaluate production model quality.

## Artifact Schema Validation

Candidate and Opportunity fixture artifacts validate against:

```text
schemas/ai_lifecycle/candidate_model_artifact.schema.json
schemas/ai_lifecycle/opportunity_model_artifact.schema.json
```

U3-E formally extends artifact status vocabulary with `FIXTURE_TRAINING_OUTPUT`.

## Non-Mutation

Runtime pointer, Accepted Decision, Unified Generation, Accepted Generation, Current, Pending, Ledger, Safety, BUY state, SELL state, Trading State, and Broker write remain unchanged.

## Regression

```text
74 passed, 1 warning
```

The warning is an sklearn convergence warning from the deliberately tiny fixture smoke dataset. It is not used as production quality evidence.

JSON validation:

```text
36 files checked
0 failures
```

## Evidence

Evidence directory:

```text
reports/phase19_ad_u3_e_contract_bound_training_runner/
```

Summary:

```text
reports/phase_reports/phase19_ad_u3_e_contract_bound_training_runner.json
```

## Remaining Risks

Formal Bootstrap full-dataset training still requires a Human-reviewed execution plan. Fixture smoke metrics are technical only and must not be used as production quality evidence. Later gates must still implement validation, calibration if needed, Unified Generation assembly, Accepted Decision, and Runtime Transition.

## Next Step

Prepare the Formal Bootstrap Execution Plan artifact for full contract-bound Candidate and Opportunity training.
