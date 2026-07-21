# Phase19-AD-U3-F Formal Bootstrap Execution Plan

## Final Judgment

```text
PHASE19_AD_U3_F_FORMAL_BOOTSTRAP_EXECUTION_PLAN_READY
PHASE19_AD_U3_FORMAL_BOOTSTRAP_HUMAN_DECISION_REQUIRED
```

This report does not declare Candidate training complete, Opportunity training complete, Calibration complete, Unified Generation created, Accepted Generation created, AD-U3 complete, BUY ready, production ready, or Runtime transition complete.

## Formal Bootstrap Purpose

The plan prepares the first formal Candidate and Opportunity Training Artifacts that comply with Phase19 architecture contracts. It does not create an Accepted Generation, Runtime Transition, BUY restart, production operation, or profit-performance guarantee.

## Formal Input Binding

Plan artifact:

```text
reports/phase19_ad_u3_f_formal_bootstrap_execution_plan/formal_bootstrap_execution_plan.json
```

Plan status:

```text
DRAFT_REVIEW_REQUIRED
```

Plan hash:

```text
334f75b77466e919eec2b04447088194dd0b97eaf8d54e9b10b5dcb19091bfa2
```

Candidate:

```text
dataset_revision_id = candidate_dataset_revision_policy_amended_95eedc15c17fee4e
split_id = split_2edb9f39d8008b10
```

Opportunity:

```text
dataset_revision_id = opportunity_dataset_revision_policy_amended_e7f9478409126d8e
split_id = split_61b5c8077880a82e
```

Dataset, Split, Policy, Schema, Lineage, Calendar, target horizon, embargo, and label-safe fields are expanded from the R2 corrected contract and U3-A resolver output.

## Candidate Model Family / Config

Candidate formal model family is confirmed from the existing formal training implementation:

```text
sklearn_sgd_classifier
classification
loss = log_loss
penalty = l2
class_weight = balanced
max_iter = 30
shuffle = false
early_stopping = false
```

Resolved config:

```text
reports/phase19_ad_u3_f_formal_bootstrap_execution_plan/candidate_formal_training_config.json
```

## Opportunity Model Family / Config

Opportunity formal model family is confirmed from the existing formal training implementation:

```text
sklearn_sgd_regressor
regression
loss = squared_error
penalty = l2
class_weight = NOT_APPLICABLE
max_iter = 30
shuffle = false
early_stopping = false
```

Resolved config:

```text
reports/phase19_ad_u3_f_formal_bootstrap_execution_plan/opportunity_formal_training_config.json
```

Fixture smoke model family is not treated as formal authority.

## Candidate / Opportunity Dependency

Current formal plan decision:

```text
NOT_APPLICABLE_FOR_FORMAL_BOOTSTRAP_INPUT_DATASET
```

The plan does not add Candidate in-sample predictions, Candidate scores, Candidate selected universe, or Candidate artifact output as Opportunity training features. If a future dependency is introduced, it must bind OOF or out-of-time prediction source, source window, source model artifact hash, and prediction artifact hash.

## Execution Order

```text
Preflight
Candidate Formal Training
Candidate Artifact Validation
Opportunity dependency readiness
Opportunity Formal Training
Opportunity Artifact Validation
Training Run Finalization
```

Candidate failure or Candidate artifact validation BLOCK prevents Opportunity start.

## Preflight Contract

Preflight requires U3-A resolver PASS, input contract hash match, artifact binding PASS, label-safe PASS, Versioned Split PASS, Corporate Action Policy `PASS_WITH_FORMAL_LIMITATION`, approved Model Quality Policy hash match, schema checks, and environment/resource checks.

Tracked training code dirty state at execution time is `REVIEW_REQUIRED`.

## Resource Plan

Resource plan uses measured dataset file sizes and dry estimates from observed rows, feature counts, and `rows * features * 8 * 3` overhead.

Resource shortage result:

```text
BLOCK_BEFORE_TRAINING
```

Resource evidence:

```text
reports/phase19_ad_u3_f_formal_bootstrap_execution_plan/resource_plan.json
```

## Warning Policy

Warnings are classified as:

```text
INFO
EXPECTED_WARNING
REVIEW_REQUIRED_WARNING
BLOCKING_WARNING
```

Exit code 0 alone is not sufficient for PASS. ConvergenceWarning is at least `REVIEW_REQUIRED_WARNING` unless explicitly accepted by post-training technical review.

## Staging / Commit Contract

Formal training output, if later approved and executed, stages under:

```text
.runtime/ai_lifecycle/training_staging/<formal_training_run_id>/
```

Successful training artifacts use:

```text
artifact_status = TRAINING_OUTPUT
runtime_eligibility = false
generation_eligibility = false
accepted = false
```

Accepted Generation directory, Runtime pointer, BUY restart, and Broker write remain prohibited.

## Failure / Abort Contract

Abort conditions include input hash mismatch, policy hash mismatch, schema mismatch, split mismatch, label-safe mismatch, quality floor failure, resource shortage, fit failure, artifact validation failure, blocking warning, dependency violation, artifact hash mismatch, and serialization failure.

Abort result:

```text
formal_generation_created = false
accepted_decision_created = false
runtime_pointer_changed = false
broker_write_executed = false
failure_staging_recorded = true
```

## Retry Policy

Same-run-id resume is not allowed. Retry requires a new run id bound to the same execution plan hash, config hash, and input hash. Reusing a prior Candidate artifact after Opportunity failure is `REVIEW_REQUIRED` with explicit artifact hash; latest discovery is prohibited.

## Post-Training Expected Outputs

Expected outputs are Candidate and Opportunity model files, artifact manifests, resolved configs, training statistics, technical validation result, model hashes, dependency binding, run manifest, preflight result, warning summary, hash verification, and non-mutation evidence.

Still not created by training:

```text
Calibration
Formal Validation PASS
Unified Generation Candidate
Accepted Decision
Accepted Generation Manifest
Runtime pointer
Broker write
```

## Execution Command Draft

The next-step command is drafted but not executed:

```text
PYTHONPATH=src PYTHONPYCACHEPREFIX=/tmp/ai-fund-lab-v2-pycache python3 -m ai_fund_lab_v2.ai_lifecycle.ad_u3_contract_bound_training_runner --contract reports/phase19_ad_r2_ad_u2_to_ad_u3_gate_review/ad_u3_dataset_input_contract_corrected.json --model-quality-policy .runtime/ai_lifecycle/policies/model_quality/phase19_ad_u3_d_model_quality_policy/model_quality_policy.json --schema-dir schemas/ai_lifecycle --mode formal-bootstrap --approved-execution-plan reports/phase19_ad_u3_f_formal_bootstrap_execution_plan/formal_bootstrap_execution_plan.json --confirm --report-dir reports/phase19_ad_u3_g_formal_bootstrap_training_output
```

The current draft plan is rejected by the runner until Human Review approves it.

## Human Review Package

Human review package:

```text
reports/phase19_ad_u3_f_formal_bootstrap_execution_plan/formal_bootstrap_execution_plan_human_review.json
reports/phase19_ad_u3_f_formal_bootstrap_execution_plan/formal_bootstrap_execution_plan_human_review.md
```

Current review fields:

```text
reviewer = null
decision = HUMAN_REVIEW_REQUIRED
reviewed_plan_hash = null
```

Codex is not the reviewer.

## Training Execution Status

Formal Bootstrap Training was not executed. Candidate fit, Opportunity fit, Calibration, Prediction, Backtest, Unified Generation, Accepted Decision, Accepted Generation, Runtime pointer, BUY restart, and Broker write were not executed.

## Failure Injection

FI-1 through FI-15 passed. The runner rejects the unapproved draft plan and blocks reviewed plan hash mismatch.

## Regression

Regression evidence is recorded in:

```text
reports/phase19_ad_u3_f_formal_bootstrap_execution_plan/regression_results.json
```

## Remaining Risks

Human Review approval is still required before formal training execution. Tracked training code dirty status at execution time must be reviewed. Formal run warnings and technical outputs remain unknown until execution. Corporate Action policy remains `PASS_WITH_FORMAL_LIMITATION`.

## Next Step

Human Review must approve or reject the Formal Bootstrap Execution Plan.
