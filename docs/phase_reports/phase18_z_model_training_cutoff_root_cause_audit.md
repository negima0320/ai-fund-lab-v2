# Phase18-Z Model Training Cutoff Root Cause and Freshness Remediation Audit

- Run ID: `phase18z-model-training-cutoff-root-cause-audit-20260717T000000Z`
- Final judgment: `PHASE18_Z_TRUE_STALE_MODEL_CONFIRMED`
- Root cause: `TRUE_STALE_MODEL`

## Cutoff Provenance

- Direct source: `.runtime/artifact_registry/promotion_candidates/transactions/promotion-tx-phase18y-contract-completion-1081babc49b5d26b/freshness_metadata.json` / `$.model_training_cutoff_authority.split_train_end`
- Value: `2024-12-02`
- Source split file: `.runtime/ai_lifecycle/training/opportunity_ai/opportunity_training_phase18h_1081babc49b5d26b/split_definition.json` / `$.train.end`

## Component Training Periods

- Candidate train: `2021-06-14` to `2024-12-02`
- Opportunity train: `2021-09-08` to `2024-12-02`
- Opportunity validation: `2025-01-06` to `2025-12-01`
- Opportunity test: `2026-01-05` to `2026-03-03`
- Opportunity recent holdout: `2026-04-01` to `2026-05-15`

## Freshness

- label_safe_cutoff: `2026-06-04`
- training_dataset_max_date: `2026-05-15`
- model_training_lag_business_days: `69`
- Calendar note: calendar starts after model_training_cutoff; computed lag is lower bound but still exceeds 20bd threshold

## Legacy Resolver Comparison

- Candidate legacy == promotion: `False`
- Opportunity legacy == promotion: `False`

## Root Cause Decision

- TRUE_STALE_MODEL: `True`
- TRAINING_METADATA_LINEAGE_BUG: `False`
- CUTOFF_DEFINITION_BUG: `False`
- ATOMIC_COMPONENT_CUTOFF_MISMATCH: `False`
- BUSINESS_DAY_CALCULATION_BUG: `False`
- Reason: Both Promotion Candidate predictive components were trained on train splits ending 2024-12-02. Dataset has label-safe data through 2026-05-15 / cutoff 2026-06-04, so model freshness is genuinely stale.

## Next Action

- `PLAN_FORMAL_RETRAINING_NEXT_UNIT`

## Non-Mutation Confirmation

- registry_accepted_updated: `False`
- runtime_accepted_state_created: `False`
- cutoff_value_overwritten: `False`
- threshold_relaxed: `False`
- retraining_performed: `False`
- forced_buy: `False`
- broker_write: `False`
- historical_fresh_run_executed: `False`

## Validation

- pytest: `PASS`
- compile: `PASS`
- json_validation: `PASS`

## Final

`PHASE18_Z_TRUE_STALE_MODEL_CONFIRMED`
