# Artifact Registry Event and Acceptance Evidence Contract

Status: Phase16-S accepted design

This document defines the permanent machine-readable schemas and validation rules for Artifact Registry events and acceptance evidence. It applies to Production, Demo, Paper, and Historical operation. It is not a Registry implementation, validator implementation, artifact promotion, or Runtime integration plan.

## Purpose

Phase16-K through Phase16-R defined Registry responsibility, artifact identity, lifecycle, runtime-use eligibility, acceptance authority, regression gates, replacement, rollback, and revoke. This document completes the production design by defining the data contracts needed before implementation:

- Registry Event Schema
- Materialized Registry Entry Schema
- Artifact Set Manifest Schema
- Acceptance Report Schema
- Regression Evidence Schema
- Review Approval Schema
- Registry Checkpoint Schema

## Authority Boundary

The Registry has authority only over:

- Artifact Identity
- Hash / Schema Integrity
- Accepted Status Record
- Runtime-use Eligibility
- Consumer Compatibility
- Legacy / Migration / Revoke Status

The Registry does not have authority over:

- AI judgment
- model auto-selection
- policy judgment
- safety judgment
- capital allocation judgment
- Planning
- Pending
- Submit
- Execution
- Ledger
- Current
- Broker results

Schemas must not encode trading decisions, allocation decisions, or Runtime authority mutation as Registry authority.

## Null Policy

All schemas use JSON Schema Draft 2020-12.

Inapplicable fields must be represented as:

```json
null
```

Field omission is not allowed for required schema fields. String sentinels such as `NOT_APPLICABLE`, `UNKNOWN`, or empty string may appear only in legacy imported evidence before migration. Formal Registry events and acceptance evidence must use `null` for not applicable values.

## Event Log and Index Authority

The append-only Event Log is the audit Source of Truth.

The Materialized Registry Index is a derived view reconstructed from the Event Log. The index must not create independent authority. If the Event Log and Index disagree:

```text
Runtime lookup must fail closed
Registry audit status becomes REVIEW_REQUIRED or HALT
Index must be rebuilt from the Event Log before use
```

Event deletion, mutation, or in-place correction is prohibited. Corrections are represented by superseding events.

## Schema Files

| Schema | Path |
|---|---|
| Registry Event | `docs/02_architecture/schemas/artifact_registry_event.schema.json` |
| Materialized Registry Entry | `docs/02_architecture/schemas/artifact_registry_entry.schema.json` |
| Artifact Set Manifest | `docs/02_architecture/schemas/artifact_set_manifest.schema.json` |
| Acceptance Report | `docs/02_architecture/schemas/artifact_acceptance_report.schema.json` |
| Regression Evidence | `docs/02_architecture/schemas/artifact_regression_evidence.schema.json` |
| Review Approval | `docs/02_architecture/schemas/artifact_review_approval.schema.json` |
| Registry Checkpoint | `docs/02_architecture/schemas/artifact_registry_checkpoint.schema.json` |
| Validation Result | `docs/02_architecture/schemas/artifact_validation_result.schema.json` |

## Registry Event Schema

Schema version:

```text
artifact_registry_event.v1
```

Required fields:

```text
event_id
event_type
event_schema_version
event_created_at
actor_type
actor_id
authority_ref
logical_artifact_id
artifact_instance_id
artifact_type
component
artifact_version
previous_status
new_status
runtime_use_eligible
physical_path
content_hash
schema_version
schema_hash
artifact_set_id
business_date
feature_date
as_of
producer
producer_version
consumer_compatibility
source_refs
source_hashes
point_in_time_status
retention_class
path_classification
migration_status
review_ref
regression_ref
acceptance_report_ref
reason
supersedes_event_id
previous_physical_path
new_physical_path
```

`event_id` must be unique and stable. `content_hash` and `schema_hash` use SHA-256 hex or `sha256:<hex>` format when applicable, otherwise `null`.

Hash fields must not use empty string, `UNKNOWN`, or `NOT_APPLICABLE`.

## Event Types

| Event Type | Required fields beyond base | Allowed previous status | Allowed new status | Required authority | Required evidence | Runtime eligibility change |
|---|---|---|---|---|---|---|
| `ARTIFACT_DISCOVERED` | identity, path, type, component | `null` | `DRAFT` | inventory actor | discovery evidence | must be false |
| `ARTIFACT_VALIDATED` | hash, schema, producer, consumer | `DRAFT`, `REVIEW_REQUIRED` | `VALIDATED` | validation actor | validation evidence | must be false |
| `REVIEW_REQUIRED` | reason | `DRAFT`, `VALIDATED`, `REVIEW_REQUIRED` | `REVIEW_REQUIRED` | validation or reviewer | blocking reason | must be false |
| `ARTIFACT_ACCEPTED` | review, regression, acceptance report | `VALIDATED`, `LEGACY` | `ACCEPTED` | acceptance authority | approval + regression + report | may become true |
| `ARTIFACT_LEGACY` | superseded relationship or reason | `ACCEPTED` | `LEGACY` | acceptance authority | replacement evidence | false |
| `ARTIFACT_REVOKED` | reason | `ACCEPTED`, `LEGACY`, `VALIDATED`, `REVIEW_REQUIRED` | `REVOKED` | acceptance or emergency authority | revoke evidence | false |
| `ARTIFACT_REPLACED` | supersedes event/artifact refs | `ACCEPTED` | `LEGACY` | acceptance authority | replacement report | false for replaced artifact |
| `PATH_REGISTERED` | path, path classification | `DRAFT`, `VALIDATED`, `ACCEPTED` | unchanged | registry migration authority | path evidence | unchanged |
| `PATH_MIGRATED` | old path, new path in reason/source refs | `ACCEPTED`, `LEGACY` | unchanged | registry migration authority | hash-preserving migration evidence | unchanged |
| `ELIGIBILITY_CHANGED` | consumer compatibility, runtime flag | `ACCEPTED`, `LEGACY` | same status | acceptance authority | eligibility review | true only if status is `ACCEPTED` |
| `CHECKPOINT_CREATED` | checkpoint ref | `null` | `null` | registry service | checkpoint evidence | unchanged |

`ARTIFACT_ACCEPTED` must never be emitted by Runtime, AI, CLI, feature generation, report generation, simulation, or backtest tools.

## Lifecycle Transition Matrix

| From | To | Allowed | Notes |
|---|---|---:|---|
| `DRAFT` | `VALIDATED` | Yes | Validation evidence required. |
| `DRAFT` | `REVIEW_REQUIRED` | Yes | Blocking reason required. |
| `DRAFT` | `ACCEPTED` | No | Must pass through `VALIDATED`. |
| `VALIDATED` | `REVIEW_REQUIRED` | Yes | Review or validation gap found. |
| `VALIDATED` | `ACCEPTED` | Yes | Acceptance report and regression required. |
| `VALIDATED` | `REVOKED` | Yes | Use for actively banned validated artifacts. |
| `REVIEW_REQUIRED` | `VALIDATED` | Yes | Gap resolved by new validation evidence. |
| `REVIEW_REQUIRED` | `ACCEPTED` | No | Must return to `VALIDATED` first. |
| `ACCEPTED` | `LEGACY` | Yes | Replacement or deactivation. |
| `ACCEPTED` | `REVOKED` | Yes | Immediate deny. |
| `LEGACY` | `ACCEPTED` | Yes | Requires a new rollback acceptance event. |
| `LEGACY` | `REVOKED` | Yes | Legacy evidence found unsafe. |
| `REVOKED` | `ACCEPTED` | No | Same instance can never be reaccepted. |
| `REVOKED` | `VALIDATED` | No | Corrected artifact must be a new instance. |

## Materialized Registry Entry Schema

Required fields:

```text
logical_artifact_id
active_artifact_instance_id
artifact_type
component
current_status
runtime_use_eligible
physical_path
content_hash
schema_hash
artifact_set_id
accepted_event_id
accepted_at
accepted_by
legacy_instances
revoked_instances
last_event_id
last_updated_at
derived_from_event_log
```

`derived_from_event_log` must be `true`. The entry is invalid if it cannot be reconstructed from the Event Log. Runtime must not trust an index entry whose `last_event_id` is absent from the Event Log.

## Artifact Set Manifest Schema

Artifact Set manifests cover:

- Candidate Accepted Artifact Set
- Opportunity Accepted Artifact Set
- PM Accepted Artifact Set
- Capital Allocation Policy Artifact Set

Required fields:

```text
artifact_set_id
artifact_set_type
artifact_set_version
component
member_artifacts
required_member_types
member_hashes
schema_hashes
compatibility_constraints
training_period
feature_schema_ref
validation_evidence_refs
runtime_consumer_refs
artifact_set_hash
status
runtime_use_eligible
```

Opportunity set validation must require these roles in the same set:

- model
- metrics
- feature schema
- training metadata
- validation evidence

If Opportunity model and metrics are not in the same set, validation result is `HALT`.

## Acceptance Report Schema

An artifact cannot move to `ACCEPTED` without an Acceptance Report.

Required fields:

```text
acceptance_report_id
artifact_or_set_ref
reviewed_artifact_hashes
reviewed_schema_hashes
reviewed_source_refs
human_reviewer
architecture_reviewer
regression_reviewer
release_approver
review_started_at
review_completed_at
decision
acceptance_criteria_results
regression_results
known_limitations
risk_classification
rollback_target
replacement_target
git_commit
runtime_version
feature_schema_version
canonical_data_manifest_ref
model_freeze_manifest_ref
approval_signatures
notes
```

Allowed decisions:

```text
ACCEPT
REJECT
REVIEW_REQUIRED
```

`ARTIFACT_ACCEPTED` requires `decision=ACCEPT`.

## Regression Evidence Schema

Regression Evidence supports profiles instead of forcing all parity checks on every artifact:

| Profile | Required parity focus |
|---|---|
| `CANDIDATE` | candidate decision parity, feature/schema compatibility, Current/Ledger/Pending unchanged. |
| `OPPORTUNITY` | opportunity ranking parity, Candidate input binding, Planning/Pending unchanged. |
| `PM` | PM decision parity, Current boundary unchanged, Planning/Pending unchanged. |
| `CAPITAL_ALLOCATION` | capital allocation parity, Planning/Pending/Submit Guard unchanged. |
| `FEATURE` | feature schema/calculation equality, point-in-time checks. |
| `DATA` | source hash, schema, point-in-time, no look-ahead checks. |
| `REGISTRY_PATH_ONLY` | semantic equality and hash-preserving path/lookup migration. |

Common required fields are defined in `artifact_regression_evidence.schema.json`. Inapplicable parity fields use `null`.

## Validation Result Schema

Validation Result artifacts use:

```text
artifact_validation_result.v1
```

Required fields:

```text
schema_version
validation_id
validated_at
subject_type
subject_ref
validator_version
validated_schema_version
overall_result
failure_class
checks
errors
warnings
evidence_refs
recommended_action
```

Validation Result artifacts are read-only evidence. They do not change Registry authority, artifact status, Materialized Index, Runtime state, Current, Ledger, or Pending.


## Review Approval Schema

Approval types:

```text
HUMAN_REVIEW
ARCHITECTURE_ACCEPTANCE
REGRESSION_ACCEPTANCE
RELEASE_APPROVAL
```

Required fields:

```text
approval_id
approval_type
subject_ref
reviewer_id
reviewer_role
decision
approved_at
evidence_refs
conditions
expires_at
supersedes_approval_id
```

One-person operation is permitted at the current stage, but roles must be recorded separately. Production should prefer separation of duties for Human Review, Regression Acceptance, and Release Approval. A future policy may require distinct reviewer IDs without changing the schema.

## Registry Checkpoint Schema

Checkpoints are integrity evidence only. They do not change Registry authority.

Required fields:

```text
checkpoint_id
created_at
event_log_hash
event_count
last_event_id
materialized_index_hash
entry_count
schema_versions
validation_result
previous_checkpoint_ref
created_by
authority_change
```

`authority_change` must be `false`.

## Cross-field Validation Rules

Future validators must implement these rules:

- `ACCEPTED` requires `acceptance_report_ref`, `review_ref`, and `regression_ref`.
- Non-event Registry evidence schemas require each schema-specific `schema_version` const.
- `runtime_use_eligible=true` is allowed only when `new_status=ACCEPTED` or current status is `ACCEPTED`.
- `REVOKED` always requires `runtime_use_eligible=false`.
- `LEGACY` defaults to `runtime_use_eligible=false`.
- `DRAFT`, `VALIDATED`, `REVIEW_REQUIRED`, and `REJECTED` are never runtime eligible.
- `ARTIFACT_ACCEPTED` requires actor authority to be acceptance authority, not Runtime, AI, Registry automation, or CLI alone.
- Hash fields must be `null` or a valid SHA-256 hex value, optionally prefixed with `sha256:`.
- Empty string, `UNKNOWN`, and `NOT_APPLICABLE` are invalid in formal hash fields.
- `content_hash` must be SHA-256 when the artifact is a file; directories must use a recorded directory inventory hash as content hash or source hash.
- Validation Result evidence must conform to `artifact_validation_result.v1`.
- `PATH_MIGRATED` requires `previous_physical_path` and `new_physical_path`.
- `PATH_MIGRATED` requires `previous_physical_path != new_physical_path`.
- Business-date scoped decision artifacts require `business_date`.
- Feature artifacts require `feature_date`.
- Model artifacts normally require `business_date=null`.
- Event transition must match the Lifecycle Transition Matrix.
- `REVOKED` cannot transition to `ACCEPTED` or `VALIDATED`.
- Opportunity Artifact Set requires model, metrics, feature schema, training metadata, and validation evidence in the same set.
- Opportunity model/metrics set mismatch is `HALT`.
- Acceptance Report `decision=ACCEPT` is required for `ARTIFACT_ACCEPTED`.
- Materialized Index must be rebuildable from Event Log.
- Event Log and Index mismatch requires fail-closed behavior.
- Review approval `APPROVED` requires `approved_at`.
- Expired approval cannot be used for new acceptance.
- Point-in-time status `HALT` blocks acceptance.
- Silent fallback to an unaccepted artifact is `HALT`.

## Failure Classification

| Failure | Classification |
|---|---|
| Optional metadata missing | `REVIEW_REQUIRED` |
| Required schema field missing | `VALIDATION_ERROR` |
| Acceptance Report missing for `ACCEPTED` | `HALT` |
| Hash format invalid | `HALT` |
| Content hash mismatch | `HALT` |
| Schema hash mismatch | `HALT` |
| Illegal lifecycle transition | `HALT` |
| Runtime actor attempts auto-promotion | `HALT` |
| Model / Metrics Set mismatch | `HALT` |
| Event Log corrupted | `HALT` |
| Materialized Index not rebuildable | `REVIEW_REQUIRED` |
| Event Log / Index mismatch | `HALT` for Runtime lookup; `REVIEW_REQUIRED` for offline repair if Event Log is intact |
| Unknown producer | `REVIEW_REQUIRED` |
| Unknown consumer | `REVIEW_REQUIRED` |
| Point-in-time evidence missing | `REVIEW_REQUIRED` or `HALT` depending on artifact type |
| Revoked artifact requested by Runtime | `HALT` |

## Phase16-P Compatibility

Read-only compatibility was evaluated against:

- `reports/phase16_registry_inventory/draft_registry_events.jsonl`
- `reports/phase16_registry_inventory/draft_registry_index.json`
- `reports/phase16_registry_inventory/*_manifest_candidate.json`

Result:

```text
MAPPABLE_WITH_TRANSFORMATION
```

Phase16-P draft events already contain:

- `event_type`
- `logical_artifact_id`
- `artifact_instance_id`
- `artifact_type`
- `component`
- `physical_path`
- `content_hash`
- `schema_hash`
- `path_classification`
- `migration_status`

Formal schema migration must add or transform:

| Formal field | Mapping |
|---|---|
| `event_id` | generate deterministic migration event ID. |
| `event_type` | map `DRAFT_REGISTER_ARTIFACT_CANDIDATE` to `ARTIFACT_DISCOVERED` or `ARTIFACT_VALIDATED`. |
| `event_schema_version` | set `artifact_registry_event.v1`. |
| `event_created_at` | use migration timestamp; preserve original inventory timestamp in source refs or reason. |
| `actor_type` | set `INVENTORY_TOOL` or `VALIDATION_TOOL`. |
| `actor_id` | set Phase16-P inventory tool identity. |
| `previous_status` | set `null` for discovered, or `DRAFT` for validated migration event. |
| `new_status` | map `status` to lifecycle status. |
| `runtime_use_eligible` | derive false unless formal acceptance exists. |
| `schema_version` | derive from inventory schema_version when known, otherwise `null`. |
| `producer` | join from `artifact_inventory.json`. |
| `producer_version` | set `null` unless known. |
| `consumer_compatibility` | derive from inventory consumer field and compatibility table. |
| `source_refs` / `source_hashes` | join from inventory fields. |
| `retention_class` | join from inventory. |
| `review_ref` / `regression_ref` / `acceptance_report_ref` | `null`; no acceptance exists. |

Phase16-P materialized index is not compatible as a formal index because it lacks accepted event IDs, accepted timestamps, accepted-by, legacy/revoked instance lists, and last-event tracking. It is a migration input only.

Phase16-P manifest candidates are mappable into Artifact Set Manifest Schema but require:

- `artifact_set_id`
- `artifact_set_type`
- `artifact_set_version`
- member role normalization
- required member type declaration
- runtime consumer refs
- formal status field mapping from `accepted_status_candidate`
- `runtime_use_eligible=false` until accepted

## Versioning Policy

Initial schema versions:

- `artifact_registry_event.v1`
- `artifact_registry_entry.v1`
- `artifact_set_manifest.v1`
- `artifact_acceptance_report.v1`
- `artifact_regression_evidence.v1`
- `artifact_review_approval.v1`
- `artifact_registry_checkpoint.v1`
- `artifact_validation_result.v1`

Phase16-U hardening added schema-version consts to non-event schemas, formalized the Validation Result schema, removed empty-string hash allowance, and added explicit path migration fields. Because production Event Log and formal Registry implementation do not exist yet, these changes are classified as `v1 initial hardening`.

Backward-compatible additions may add optional fields. Breaking changes after production use begins require a new schema version and a migration plan. Event Log must retain original event schema versions forever.

## Acceptance Criteria for This Contract

This contract is complete when:

- Registry Event Schema is defined.
- Event Types are defined.
- Lifecycle Transition Matrix is defined.
- Materialized Entry Schema is defined.
- Artifact Set Manifest Schema is defined.
- Acceptance Report Schema is defined.
- Regression Evidence Schema is defined.
- Review Approval Schema is defined.
- Checkpoint Schema is defined.
- Cross-field Rules are defined.
- Failure Classification is defined.
- Event Log is Source of Truth.
- Index is a derived view.
- Phase16-P compatibility is evaluated.
- Acceptance Report Template exists.
- Runtime / Authority / Artifact Status remain unchanged.

## Unresolved Items

- Validator implementation.
- Registry production implementation.
- Event ID deterministic generation rule details.
- Acceptance report storage path.
- Separation-of-duties production policy.
- Corporate Action Source of Truth decision.
- Opportunity Phase5-E fallback resolution.

## Phase16-AJ Amendment

Phase16-AJ classifies Acceptance schema changes as:

```text
pre-Acceptance v1 hardening
```

Reason: the formal Event Log is empty, the Materialized Index has zero entries, and no `ARTIFACT_ACCEPTED` event exists.

Schema additions:

- `artifact_registry_event.schema.json` now includes optional fields for `artifact_set_type`, `evidence_bundle_ref`, `consumer_compatibility_ref`, replacement operation refs, rollback refs, revoke fields, and fail-closed incident guidance.
- `artifact_set_manifest.schema.json` now includes formal Artifact Set Type enum values, `set_authority_scope`, formal member roles, evidence refs, compatibility refs, lineage refs, freeze manifest refs, and member-level status/eligibility fields.
- `artifact_acceptance_report.schema.json`, `artifact_review_approval.schema.json`, and `artifact_regression_evidence.schema.json` now include Artifact Set subject fields required by set-level acceptance.
- `artifact_acceptance_evidence_bundle.schema.json` and `artifact_acceptance_validation_result.schema.json` are added.

Rules that JSON Schema cannot safely express remain Cross-field Validator rules:

- required member matrix by Set Type;
- required approval role matrix by Set Type;
- all approval and evidence `subject_ref` values match the same Artifact Set;
- Acceptance Report and Regression Evidence set hash match the Manifest;
- Opportunity model and metrics are in the same set;
- PM code policy and adapter are in the same set;
- Capital Allocation policy and schema are in the same set;
- runtime eligibility preconditions;
- replacement stage ordering;
- rollback requires new evidence;
- `REVOKED` instance re-acceptance is prohibited.
