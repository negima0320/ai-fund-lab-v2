# Artifact Acceptance Report

## Artifact Identity

- acceptance_report_id:
- artifact_or_set_ref:
- logical_artifact_id:
- artifact_instance_id:
- artifact_type:
- component:
- artifact_version:
- physical_path:

## Artifact Set

- artifact_set_id:
- artifact_set_type:
- member_artifacts:
- required_member_types:
- artifact_set_hash:

## Hash / Schema

- reviewed_artifact_hashes:
- reviewed_schema_hashes:
- schema_version:
- schema_hash:

## Producer / Consumer

- producer:
- producer_version:
- intended_consumers:
- runtime_use_eligible_scope:

## Source Evidence

- reviewed_source_refs:
- source_hashes:
- canonical_data_manifest_ref:
- model_freeze_manifest_ref:
- feature_schema_version:

## Architecture Review

- architecture_reviewer:
- architecture_decision:
- authority_boundary_confirmed:
- point_in_time_status:
- known_limitations:

## Regression Review

- regression_reviewer:
- regression_evidence_refs:
- regression_summary:
- semantic_equality:
- current_unchanged:
- ledger_unchanged:
- pending_unchanged:
- runtime_state_unchanged:

## Risk

- risk_classification:
- safety_notes:
- fallback_or_silent_dependency_review:

## Rollback Target

- rollback_target:
- rollback_conditions:
- rollback_validation_required:

## Replacement Target

- replacement_target:
- supersedes_artifact_instance_id:
- legacy_transition_required:

## Approval

- human_reviewer:
- architecture_reviewer:
- regression_reviewer:
- release_approver:
- approval_signatures:
- review_started_at:
- review_completed_at:
- git_commit:
- runtime_version:

## Final Decision

- decision: ACCEPT | REJECT | REVIEW_REQUIRED
- conditions:
- notes:

This template creates acceptance evidence only. It does not promote any artifact automatically.
