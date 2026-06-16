# Phase9-K Model Manifest / Retrain Eligibility Review

- status: POLICY_MANIFESTS_READY_MODEL_RETRAIN_REQUIRED
- decision_for: 2026-06-15
- data_until: 2026-06-15
- retrain_required: True

## Eligibility

| AI | status | version | train_until | safe_train_until | schema | blockers |
| --- | --- | --- | --- | --- | --- | --- |
| candidate | LEAKAGE_AUDIT_REQUIRED |  |  | 2026-05-18 |  | missing_model_or_policy_version, missing_train_until, missing_feature_schema_hash, leakage_audit_not_ok, forbidden_source_audit_not_ok, source_data_refs_not_jquants_only |
| opportunity | MANIFEST_METADATA_INCOMPLETE | opportunity_model_phase5e_v1 |  | 2026-05-18 |  | missing_train_until, missing_feature_schema_hash, forbidden_source_audit_not_ok, source_data_refs_not_jquants_only |
| position | MODEL_ELIGIBLE | position_management_policy_phase6i_winner_holding_v1 |  |  | 3ddf67ff43f207fb | none |
| capital | MODEL_ELIGIBLE | phase7d_realistic_execution_constraints_v1/CAP5 |  |  | d66489c1ef814918 | none |

## Safe Train Until

- candidate: 2026-05-18
- opportunity: 2026-05-18
- position: not_required
- capital: not_required

## Policy Manifests

- position: `.runtime/phase9/policy_manifests/position_policy_manifest.json`
- capital: `.runtime/phase9/policy_manifests/capital_policy_manifest.json`

## Safety

- forbidden_source_audit_status: REVIEW_REQUIRED
- model_retraining_executed: False
- inference_executed: False
- order_plan_generation_executed: False
- broker_order_api_called: False
- virtual_fill_executed: False

## Next Action

- Run Phase9-L model retrain or manifest repair planning for Candidate/Opportunity using safe_train_until.
