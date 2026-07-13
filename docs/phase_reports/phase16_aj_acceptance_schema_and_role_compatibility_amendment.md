# Phase16-AJ Acceptance Schema and Role Compatibility Amendment

## Executive Summary

Phase16-AJ converts the Phase16-AI Acceptance authority design into machine-readable schema and compatibility contracts. This phase amended JSON Schemas, added role/member compatibility contracts, and added structural tests. It did not generate evidence, implement an Acceptance Writer, append Registry Events, promote artifacts, copy artifacts, rebuild Index, create Checkpoint, connect Runtime lookup, or change AI / Feature / Runtime behavior.

Final judgment:

```text
PHASE16_AJ_ACCEPTANCE_SCHEMA_AND_ROLE_COMPATIBILITY_ACCEPTED
```

## Created / Updated Files

Created:

- `docs/02_architecture/contracts/artifact_acceptance_role_compatibility.v1.json`
- `docs/02_architecture/schemas/artifact_acceptance_evidence_bundle.schema.json`
- `docs/02_architecture/schemas/artifact_acceptance_validation_result.schema.json`
- `tests/artifact_registry/test_phase16aj_acceptance_schema_and_role_compatibility.py`
- `docs/phase_reports/phase16_aj_acceptance_schema_and_role_compatibility_amendment.md`
- `reports/phase_reports/phase16_aj_acceptance_schema_and_role_compatibility_amendment.json`

Updated:

- `docs/02_architecture/schemas/artifact_set_manifest.schema.json`
- `docs/02_architecture/schemas/artifact_acceptance_report.schema.json`
- `docs/02_architecture/schemas/artifact_review_approval.schema.json`
- `docs/02_architecture/schemas/artifact_regression_evidence.schema.json`
- `docs/02_architecture/schemas/artifact_registry_event.schema.json`
- `docs/02_architecture/artifact_acceptance_authority_and_promotion_workflow_contract.md`
- `docs/02_architecture/artifact_acceptance_contract.md`
- `docs/02_architecture/artifact_registry_event_and_acceptance_evidence_contract.md`
- `docs/02_architecture/artifact_registry_validator_contract.md`
- `src/ai_fund_lab_v2/artifact_registry/validator.py`
- `tests/artifact_registry/test_phase16u_schema_amendments.py`

## Artifact Set Type Result

Formal Artifact Set Type enum:

```text
CANDIDATE_AI_SET
OPPORTUNITY_AI_SET
POSITION_MANAGEMENT_POLICY_SET
CAPITAL_ALLOCATION_POLICY_SET
FEATURE_SCHEMA_SET
SAFETY_POLICY_SET
```

Legacy aliases remain readable only for pre-Acceptance compatibility:

```text
CANDIDATE_ACCEPTED_SET
OPPORTUNITY_ACCEPTED_SET
PM_ACCEPTED_SET
```

Acceptance Writer and future Runtime lookup must use the formal Set Types.

## Member Role Result

Formal member roles are fixed in `artifact_set_manifest.schema.json` and `artifact_acceptance_role_compatibility.v1.json`.

Candidate:

```text
MODEL
MODEL_MANIFEST
FEATURE_SCHEMA
TRAINING_METADATA
TRAINING_DATA_LINEAGE
VALIDATION_EVIDENCE
METRICS_EVIDENCE
CONSUMER_COMPATIBILITY
```

Opportunity:

```text
MODEL
METRICS
FEATURE_SCHEMA
TRAINING_METADATA
TRAINING_DATA_LINEAGE
VALIDATION_EVIDENCE
CONSUMER_COMPATIBILITY
```

Position Management:

```text
CODE_POLICY
RUNTIME_ADAPTER
POLICY_VERSION
FEATURE_VERSION
BEHAVIOR_CONTRACT
REGRESSION_EVIDENCE
CONSUMER_COMPATIBILITY
```

Capital Allocation:

```text
POLICY
POLICY_SCHEMA
POLICY_VERSION
VALIDATION_EVIDENCE
REGRESSION_EVIDENCE
CONSUMER_COMPATIBILITY
```

Feature Schema:

```text
FEATURE_SCHEMA
POINT_IN_TIME_EVIDENCE
CONSUMER_COMPATIBILITY
SCHEMA_VALIDATION_EVIDENCE
```

## Required Member Matrix

The Required Member Matrix is machine-readable in:

```text
docs/02_architecture/contracts/artifact_acceptance_role_compatibility.v1.json
```

Opportunity explicitly requires `MODEL` and `METRICS` in the same Artifact Set. The contract does not encode Phase5-P or Phase5-E paths as identity; it relies on `artifact_instance_id`, content hash, source lineage, set membership, and accepted status.

## Role Compatibility Matrix

Reusable Runtime-use Artifact Sets require:

```text
HUMAN_REVIEW
ARCHITECTURE_ACCEPTANCE
REGRESSION_ACCEPTANCE
RELEASE_APPROVAL
```

Machine-readable defaults:

```text
same_reviewer_allowed=true
role_omission_allowed=false
production_multi_reviewer_policy=DEFERRED_TO_RELEASE_POLICY
```

## Artifact Set Manifest Result

`artifact_set_manifest.schema.json` now supports:

- formal and legacy-compatible `artifact_set_type`;
- `set_authority_scope=SET_LEVEL`;
- formal `member_role`;
- member `physical_path`, `artifact_set_id`, status, runtime eligibility, accepted status, and migration status;
- `required_member_roles`;
- `consumer_compatibility_ref`;
- `source_lineage_ref`;
- `freeze_manifest_ref`;
- `regression_evidence_refs`.

Cross-field Validator, not JSON Schema alone, must enforce required member roles by Set Type.

## Evidence Bundle Schema Result

Added:

```text
docs/02_architecture/schemas/artifact_acceptance_evidence_bundle.schema.json
```

It binds:

- Artifact Set Manifest;
- Acceptance Report;
- Regression Evidence;
- four approval roles;
- source lineage;
- freeze manifest;
- consumer compatibility;
- rollback target;
- evidence hashes.

## Acceptance Report Result

`artifact_acceptance_report.schema.json` now supports Set-level subject fields:

- `artifact_set_id`;
- `artifact_set_type`;
- `artifact_set_manifest_ref`;
- `artifact_set_hash`;
- `reviewed_member_hashes`;
- `evidence_bundle_ref`;
- `regression_result`;
- `consumer_compatibility_result`;
- `point_in_time_result`;
- `rollback_target_ref`.

`decision=ACCEPT` evidence completeness remains a Cross-field Validator responsibility.

## Approval Schema Result

`artifact_review_approval.schema.json` now supports:

- `approval_role`;
- `subject_type=ARTIFACT_SET`;
- `artifact_set_type`;
- `reviewed_hash`.

All approval subject refs must point to the same Artifact Set. That is a Cross-field Rule.

## Regression Evidence Result

`artifact_regression_evidence.schema.json` now supports:

- `artifact_set_id`;
- `artifact_set_type`;
- `baseline_ref`;
- `candidate_ref`;
- `semantic_equality_result`;
- `consumer_compatibility_result`;
- `point_in_time_result`;
- `planning_unchanged`;
- `submit_unchanged`;
- `evidence_hash`.

Artifact Set Type specific regression requirements remain in the compatibility contract and Cross-field Validator.

## Acceptance Event Result

`artifact_registry_event.schema.json` now supports:

- `artifact_set_type`;
- `evidence_bundle_ref`;
- `consumer_compatibility_ref`;
- replacement operation fields;
- rollback operation fields;
- revoke fields;
- `runtime_fail_closed_required`;
- `incident_ref`.

Set-level Authority is represented by using the Artifact Set logical identity in `logical_artifact_id` for `ARTIFACT_ACCEPTED`.

## Runtime Eligibility Preconditions

Machine-readable preconditions are listed in `artifact_acceptance_role_compatibility.v1.json`.

Any missing condition is `HALT` for runtime eligibility:

- `ARTIFACT_ACCEPTED`;
- `new_status=ACCEPTED`;
- `SET_LEVEL`;
- complete Artifact Set;
- member hash/schema match;
- complete Evidence Bundle;
- four approval roles;
- Regression `PASS`;
- Consumer Compatibility `PASS`;
- Point-in-time `PASS`;
- valid Release Approval;
- not `LEGACY`, `REVOKED`, or `REJECTED`.

## Replacement Contract

Replacement fields were added to the Event schema:

- `replacement_operation_id`;
- `replacement_from_ref`;
- `replacement_to_ref`;
- `replacement_stage`.

The machine-readable stage enum supports:

```text
NEW_VALIDATED
NEW_ACCEPTED_INELIGIBLE
OLD_LEGACY
NEW_ELIGIBLE
INDEX_BUILT
CHECKPOINTED
```

Stage ordering is a Cross-field Rule. Runtime lookup must fail closed on duplicate active eligible artifacts or partial replacement.

## Rollback Contract

Rollback fields were added:

- `rollback_operation_id`;
- `rollback_target_ref`;
- `new_acceptance_report_ref`;
- `new_regression_ref`;
- `new_approval_refs`.

`LEGACY -> ACCEPTED` requires new evidence. `REVOKED -> ACCEPTED` remains prohibited.

## Revoke Contract

Revoke fields were added:

- `revoke_reason`;
- `authority_ref`;
- `affected_consumers`;
- `replacement_ref`;
- `runtime_fail_closed_required`;
- `incident_ref`.

`runtime_use_eligible=false` is required for revoke by lifecycle / eligibility rules. Same-instance reacceptance after `REVOKED` is a Cross-field Rule and remains prohibited.

## Acceptance Validation Result

Added:

```text
docs/02_architecture/schemas/artifact_acceptance_validation_result.schema.json
```

This is required for the future Acceptance Evidence Builder / Validator. Existing `artifact_validation_result.v1` remains valid for general Registry validation.

## Cross-field Rules

The Cross-field Rules are fixed in the contract JSON:

- Set Type and required member roles match;
- Set Type and required approval roles match;
- all Approval subject refs match;
- all Evidence Bundle subject refs match;
- Acceptance Report set hash matches Manifest;
- Regression Evidence set hash matches Manifest;
- member hash and schema hash match Manifest;
- Opportunity Model / Metrics same-set;
- PM Code Policy / Adapter same-set;
- Capital Allocation Policy / Schema same-set;
- runtime eligibility conditions;
- replacement stage ordering;
- rollback requires new evidence;
- `REVOKED` re-acceptance prohibited.

## Schema Versioning Classification

Classification:

```text
pre-Acceptance v1 hardening
```

Reason:

- formal Event Log is empty;
- formal Index has zero entries;
- current Checkpoint references empty Registry state;
- no `ARTIFACT_ACCEPTED` event exists.

## Compatibility Result

Compatible with:

- Phase16-P draft inventory: `COMPATIBLE_WITH_TRANSFORMATION`;
- current empty Formal Event Log: `COMPATIBLE`;
- current empty Index: `COMPATIBLE`;
- current Checkpoint: `COMPATIBLE`;
- existing Validator: `COMPATIBLE_WITH_ALIAS_SUPPORT`;
- FullEventLogValidator: `COMPATIBLE`;
- Index Builder: `COMPATIBLE`;
- Checkpoint Writer: `COMPATIBLE`.

No existing formal Event needs rewrite.

## Test Result

Command:

```text
python3 -m pytest -q tests/artifact_registry
```

Result:

```text
130 passed in 1.02s
```

## Formal Registry Impact

Formal Event Log:

```text
event_count=0
```

Index:

```text
event_count=0
entry_count=0
```

Checkpoint:

```text
latest_checkpoint_hash=9add63e17d7e6ca876704d9266e86e3ccbcd2fbe726d080c31a7e67833b8c1f4
```

No Registry Event, Index, or Checkpoint mutation was performed.

## Readiness

| Area | Judgment |
|---|---|
| Acceptance Evidence Builder readiness | `READY_FOR_IMPLEMENTATION_DESIGN` |
| Acceptance Writer readiness | `NOT_READY_IMPLEMENTATION_REQUIRED` |
| Formal Registration readiness | `NOT_READY` |
| Runtime Lookup readiness | `NOT_READY` |

## Remaining Amendments

- Future Acceptance Evidence Builder must implement Cross-field Rules.
- Future Acceptance Writer must use formal Set Types, not legacy aliases.
- Production multi-reviewer separation policy remains deferred to Release Policy.
- Opportunity Phase5-E fallback remains an implementation blocker before acceptance.

## Final Judgment

```text
PHASE16_AJ_ACCEPTANCE_SCHEMA_AND_ROLE_COMPATIBILITY_ACCEPTED
```

Next Prefix:

```text
Phase16-AK
```
