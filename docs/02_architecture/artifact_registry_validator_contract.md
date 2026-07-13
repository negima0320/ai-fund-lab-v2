# Artifact Registry Validator Contract

Status: Phase16-T accepted design, amended by Phase16-U

This document defines the validator architecture for Artifact Registry schemas and evidence. It reviews the Phase16-S schemas and defines future validator responsibilities, validation order, result contract, event ID policy, evidence path policy, event log atomicity requirements, index rebuild rules, Phase16-P migration mapping, role separation, and schema versioning.

This is not a validator implementation. It does not modify schemas, write registry events, generate a materialized index, promote artifacts, or change Runtime.

## Purpose

The validator confirms whether artifacts, registry events, evidence, and derived indexes conform to the Artifact Registry contracts. It does not decide what Runtime should trade, which model should win, how policy should allocate capital, or whether broker/execution/current state is correct.

Validator authority is limited to:

- artifact identity contract conformance
- hash and schema integrity
- lifecycle transition legality
- acceptance evidence completeness
- runtime-use eligibility conformance
- consumer compatibility evidence
- legacy/migration/revoke status consistency
- checkpoint and index rebuild consistency

The validator must not decide:

- model auto-selection
- AI judgment
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

## Schema Review Result

Reviewed schemas:

- `docs/02_architecture/schemas/artifact_registry_event.schema.json`
- `docs/02_architecture/schemas/artifact_registry_entry.schema.json`
- `docs/02_architecture/schemas/artifact_set_manifest.schema.json`
- `docs/02_architecture/schemas/artifact_acceptance_report.schema.json`
- `docs/02_architecture/schemas/artifact_regression_evidence.schema.json`
- `docs/02_architecture/schemas/artifact_review_approval.schema.json`
- `docs/02_architecture/schemas/artifact_registry_checkpoint.schema.json`
- `docs/02_architecture/schemas/artifact_validation_result.schema.json`

Review result after Phase16-U hardening:

```text
SCHEMA_REVIEW_PASS
```

Findings:

- All 8 schema files are valid JSON.
- All 8 schema files declare JSON Schema Draft 2020-12.
- All 8 schema files have unique `$id`.
- All 8 schema files define `type=object`.
- All 8 schema files define `required`.
- All 8 schema files define `properties`.
- All 8 schema files set `additionalProperties=false`.
- `jsonschema` library is not installed, so Draft 2020-12 meta-schema validation was not executed.
- Phase16-U added schema-version consts to non-event schemas.
- Phase16-U removed empty string allowance from formal Event hash fields.
- Phase16-U added `artifact_validation_result.schema.json`.
- Phase16-U added `previous_physical_path` and `new_physical_path` to Registry Event.

Meta-schema validation result:

```text
META_SCHEMA_VALIDATION_NOT_EXECUTED
```

## Validator Responsibilities

### Schema Validator

Responsibilities:

- JSON parse
- JSON Schema dialect match
- required fields
- type checks
- enum checks
- format checks
- `additionalProperties=false`
- `$id` and schema version compatibility

Input:

- any Registry event, materialized entry, artifact set manifest, acceptance report, regression evidence, review approval, checkpoint, or validation result.

Output:

- validation result checks with `VALIDATION_ERROR` for schema failures.

### Lifecycle Validator

Responsibilities:

- `event_type`
- `previous_status`
- `new_status`
- allowed transition
- required authority
- required evidence refs
- runtime eligibility transition legality

Key rules:

- `DRAFT -> ACCEPTED` is illegal.
- `REVIEW_REQUIRED -> ACCEPTED` is illegal.
- `REVOKED -> ACCEPTED` is illegal.
- `REVOKED -> VALIDATED` is illegal.
- `LEGACY -> ACCEPTED` requires a new rollback acceptance event.
- Runtime, AI, CLI, report tools, and simulation tools cannot self-promote to `ACCEPTED`.

### Integrity Validator

Responsibilities:

- content hash format
- content hash match
- schema hash format
- schema hash match
- artifact set hash match
- physical path existence
- file size / file count evidence
- source hash consistency
- directory inventory hash consistency

This validator is read-only. It may compute hashes for validation evidence, but it must not rewrite artifacts.

### Artifact Set Validator

Responsibilities:

- required members
- member types
- member roles
- member hashes
- schema compatibility
- model / metrics set consistency
- PM code-policy / adapter consistency
- Capital Allocation policy set consistency

Artifact-specific rules:

- Opportunity set must include model, metrics, feature schema, training metadata, and validation evidence in the same set.
- Opportunity model / metrics mismatch is `HALT`.
- PM set must bind code-policy hash and Runtime adapter hash.
- Capital Allocation set must bind accepted policy hash and schema.

### Acceptance Evidence Validator

Responsibilities:

- Acceptance Report exists for `ARTIFACT_ACCEPTED`.
- Human Review approval exists.
- Architecture Acceptance approval exists.
- Regression Acceptance approval exists.
- Release Approval exists.
- Regression Evidence exists and matches subject.
- Acceptance Report `decision=ACCEPT` for accepted event.
- Approval role and evidence refs are complete.

### Runtime Eligibility Validator

Responsibilities:

- status is `ACCEPTED`
- `runtime_use_eligible=true`
- content hash matches
- schema hash/version matches
- consumer compatibility is true
- point-in-time status is valid
- artifact is not `LEGACY`
- artifact is not `REVOKED`
- artifact is not `REJECTED`, `DRAFT`, `VALIDATED`, or `REVIEW_REQUIRED`

This validator answers only whether a registered artifact is contract-eligible for a named consumer. It does not decide whether Runtime should trade.

### Checkpoint Validator

Responsibilities:

- Event Log hash
- Event count
- last event ID
- Materialized Index hash
- Entry count
- schema versions
- previous checkpoint chain
- rebuild consistency

Checkpoint validation does not change Registry authority.

## Validation Pipeline

Recommended order:

```text
1. Parse
2. Schema validation
3. Identity validation
4. Lifecycle validation
5. Integrity validation
6. Artifact Set validation
7. Acceptance Evidence validation
8. Runtime Eligibility validation
9. Checkpoint / Index consistency validation
```

Failure continuation policy:

| Stage | Continue after failure? | Reason |
|---|---:|---|
| Parse | No | Subject cannot be trusted as structured data. |
| Schema validation | No for lifecycle/integrity; yes for collecting schema errors | Cross-field checks require typed fields. |
| Identity validation | No for event append / runtime eligibility | Identity ambiguity is unsafe. |
| Lifecycle validation | No for status-changing events | Illegal transition can corrupt history. |
| Integrity validation | No for acceptance / runtime eligibility | Hash mismatch is unsafe. |
| Artifact Set validation | No for set acceptance | Set mismatch may bind wrong model/metrics. |
| Acceptance Evidence validation | No for `ACCEPTED` | Acceptance cannot proceed without evidence. |
| Runtime Eligibility validation | No for runtime lookup | Runtime must fail closed. |
| Checkpoint validation | Continue for offline audit if Event Log is parseable | Index can be rebuilt from Event Log. |

## Validation Result Contract

Machine-readable result fields:

```text
validation_id
validated_at
subject_type
subject_ref
validator_version
schema_version
overall_result
failure_class
checks
errors
warnings
evidence_refs
recommended_action
```

The formal schema is:

```text
docs/02_architecture/schemas/artifact_validation_result.schema.json
```

Allowed `overall_result`:

```text
PASS
PASS_WITH_WARNINGS
REVIEW_REQUIRED
FAIL
```

Allowed `failure_class`:

```text
NONE
VALIDATION_ERROR
REVIEW_REQUIRED
HALT
```

Each check:

```text
check_id
check_type
result
severity
message
field_path
evidence_ref
```

Allowed check results:

```text
PASS
WARN
REVIEW_REQUIRED
FAIL
SKIPPED
```

Recommended result mapping:

| Condition | overall_result | failure_class |
|---|---|---|
| All required checks pass | `PASS` | `NONE` |
| Non-blocking warnings only | `PASS_WITH_WARNINGS` | `NONE` |
| Evidence or human decision required | `REVIEW_REQUIRED` | `REVIEW_REQUIRED` |
| Schema or contract validation failed | `FAIL` | `VALIDATION_ERROR` |
| Unsafe condition detected | `FAIL` | `HALT` |

## Failure Classification

### VALIDATION_ERROR

Examples:

- required field missing
- type mismatch
- enum mismatch
- invalid format
- additional property not allowed
- missing schema version
- unknown schema dialect

### REVIEW_REQUIRED

Examples:

- producer unknown
- consumer compatibility not confirmed
- source refs incomplete
- optional evidence missing
- decision artifact registration failed but no Runtime use attempted
- Materialized Index mismatch that is rebuildable from intact Event Log
- point-in-time evidence incomplete for non-runtime artifact
- one-person approval requires production policy review

### HALT

Examples:

- content hash mismatch
- schema hash mismatch for Runtime-eligible artifact
- model / metrics set mismatch
- illegal lifecycle transition
- Acceptance Report missing for `ACCEPTED`
- `REVOKED` artifact requested by Runtime
- Event Log corruption
- authority mismatch
- Runtime / AI / CLI self-promotion to `ACCEPTED`
- silent fallback to unaccepted artifact
- point-in-time violation
- Event Log / Index mismatch during Runtime lookup

Artifact-specific notes:

- Candidate: scoring parity failure is `HALT` for path/Registry migration; performance-change review is required for model replacement.
- Opportunity: model/metrics mismatch and Phase5-E silent fallback are `HALT`.
- PM: hidden liquidation or cleanup authority is `HALT`.
- Capital Allocation: Planning/Pending/Submit Guard parity failure is `HALT`.
- Data / Feature: point-in-time or look-ahead failure is `HALT`.

## Event ID Policy

Compared options:

| Option | Sortability | Uniqueness | Determinism | Human readability | Replay safety | Distributed generation | Complexity |
|---|---:|---:|---:|---:|---:|---:|---:|
| UUIDv7 | High | High | No | Medium | High with idempotency key | High | Medium |
| ULID | High | High | No | High | High with idempotency key | High | Low-Medium |
| timestamp + logical ID + content hash | High | Medium | High | Medium | Medium; can collide for repeated events on same artifact | Medium | Low |

Recommendation:

```text
Primary event_id: UUIDv7
Idempotency fingerprint: deterministic hash of event_type + logical_artifact_id + artifact_instance_id + new_status + content_hash + schema_hash + authority_ref + acceptance_report_ref
```

Rationale:

- UUIDv7 gives sortable, distributed-safe event IDs.
- Deterministic fingerprint protects replay/idempotency.
- Event ID must not define artifact identity or authority.
- Artifact identity remains `logical_artifact_id` + `artifact_instance_id`.

If UUIDv7 is unavailable in the initial implementation, ULID is acceptable with the same deterministic idempotency fingerprint.

## Evidence Path Policy

Future physical paths:

```text
.runtime/artifact_registry/evidence/acceptance/
.runtime/artifact_registry/evidence/regression/
.runtime/artifact_registry/evidence/approvals/
.runtime/artifact_registry/checkpoints/
.runtime/artifact_registry/validation/
```

Path roles:

| Area | Role |
|---|---|
| `.runtime` | machine-readable operational evidence and Registry state. |
| `reports` | human-readable audit summaries and public/internal reports. |
| `docs` | permanent contracts, schema definitions, and templates. |

This phase defines paths only. It does not create formal Registry paths.

## Event Log Atomicity Requirements

Future Event Log Writer requirements:

- append-only
- one complete JSON event per line
- no partial line
- exclusive lock during append
- fsync event log before index update
- duplicate event ID detection
- deterministic idempotency fingerprint detection
- reject mutation of existing lines
- crash recovery detects last complete newline
- corrupted trailing partial event causes `HALT` until repaired by reviewed procedure
- event hash or log hash included in checkpoint
- writer must validate event before append
- index update must happen after successful append

Writer implementation is future work.

## Materialized Index Rebuild Rules

Rebuild procedure:

```text
1. Read Event Log from beginning.
2. Parse each complete JSONL event.
3. Validate schema for each event.
4. Validate lifecycle transition for each artifact instance/logical ID.
5. Apply event to derived state.
6. Keep legacy and revoked instance history.
7. Enforce one active accepted instance per logical artifact ID and consumer scope.
8. Store last_event_id per entry.
9. Compute deterministic index hash from canonical JSON.
10. Compare checkpoint event_count, last_event_id, event_log_hash, and materialized_index_hash.
```

If Event Log and Index disagree:

| Context | Behavior |
|---|---|
| Runtime lookup | fail closed. |
| Offline audit with intact Event Log | `REVIEW_REQUIRED`, rebuild index from Event Log. |
| Event Log parse/hash corruption | `HALT`. |
| Checkpoint mismatch only | `REVIEW_REQUIRED` unless Runtime lookup is requested. |

## Phase16-P Migration Mapping

Phase16-P artifacts are migration inputs only. They must not be promoted to `ACCEPTED` by transformation.

Default converted status:

```text
DRAFT
```

Allowed upgraded converted status:

```text
VALIDATED
```

Only when source evidence is sufficient and validation passes.

`ACCEPTED` is prohibited during migration.

| Source field | Target field | Default / derived value | Manual review required | Cannot migrate automatically |
|---|---|---|---:|---:|
| `event_type` | `event_type` | map `DRAFT_REGISTER_ARTIFACT_CANDIDATE` to `ARTIFACT_DISCOVERED`; optionally emit second `ARTIFACT_VALIDATED` event if evidence is sufficient | Yes for validated migration | No |
| missing | `event_id` | generate UUIDv7 at migration time | No | No |
| missing | `event_schema_version` | `artifact_registry_event.v1` | No | No |
| missing | `event_created_at` | migration timestamp | No | No |
| missing | `actor_type` | `INVENTORY_TOOL` or `VALIDATION_TOOL` | Yes | No |
| missing | `actor_id` | Phase16-P inventory migration actor | Yes | No |
| missing | `authority_ref` | `null` for discovered/validated migration | Yes | Authority cannot be invented |
| `logical_artifact_id` | `logical_artifact_id` | copy | No | No |
| `artifact_instance_id` | `artifact_instance_id` | copy if stable, else recompute from logical ID + hash | Yes | No |
| `artifact_type` | `artifact_type` | copy | No | No |
| `component` | `component` | copy | No | No |
| missing | `artifact_version` | derive from manifest/model version if present, else `null` | Yes | No |
| `status` | `new_status` | `DRAFT` or `VALIDATED`; never `ACCEPTED` | Yes | ACCEPTED cannot migrate automatically |
| missing | `previous_status` | `null` for discovered; `DRAFT` for generated validated event | No | No |
| `runtime_use_eligibility_candidate` | `runtime_use_eligible` | false | Yes | true cannot migrate automatically |
| `physical_path` | `physical_path` | copy | No | No |
| `content_hash` / directory hash | `content_hash` | normalize SHA-256 or null; never empty string or sentinel text | Yes for directory hash choice | No |
| `schema_hash` | `schema_hash` | copy or null | No | No |
| missing | `schema_version` for non-event evidence schemas | target schema const is known and must be explicitly added during conversion | No | No |
| missing | `schema_version` | derive from inventory entry when known | Yes | No |
| missing | `producer` | join from `artifact_inventory.json` | Yes if unknown | No |
| missing | `producer_version` | `null` unless known | Yes | No |
| missing | `consumer_compatibility` | derive from inventory consumer field as unverified unless compatibility evidence exists | Yes | No |
| missing | `source_refs` / `source_hashes` | join from inventory entry | Yes | No |
| missing | `review_ref` | `null` | Yes | Review approval cannot be invented |
| missing | `regression_ref` | `null` | Yes | Regression approval cannot be invented |
| missing | `acceptance_report_ref` | `null` | Yes | Acceptance evidence cannot be invented |

## Role Separation

Current single-operator policy:

- One operator may fill multiple approval roles in non-production development.
- Each role must still be recorded separately.
- Each role must have separate evidence refs.

Required roles:

- Human Reviewer
- Architecture Reviewer
- Regression Reviewer
- Release Approver

Production enablement review conditions:

- Before Production, decide whether distinct reviewer IDs are required.
- Before Production, define emergency approval and rollback policy.
- Before Production, define approval expiry and supersession rules.

Same `reviewer_id` is currently allowed across roles, but the role fields must not be collapsed.

## Schema Versioning

Rules:

- Existing events must never be rewritten.
- Event Log retains original schema versions forever.
- Backward-compatible minor changes may add optional fields or broaden descriptions without changing existing semantics.
- Breaking major changes require a new schema version and migration plan.
- Validator must dispatch by schema version.
- Validator must support all schema versions present in the Event Log, or return `REVIEW_REQUIRED` for offline audit and `HALT` for Runtime lookup.
- Unknown schema version is `REVIEW_REQUIRED` for offline review and `HALT` for Runtime eligibility.
- Migration is required when a new schema changes status semantics, hash semantics, identity semantics, or acceptance evidence requirements.

## Implementation Boundary

Future Validator may create:

- Validation Result Artifact
- Audit Report

Future Validator must not change:

- Registry Event Log
- Artifact Status
- Physical Artifact
- Materialized Index
- Current
- Ledger
- Pending
- Runtime State
- AI model
- Feature artifact
- Consumer path

The Validator is read-only with respect to Runtime and Registry authority.

## Schema Amendment Proposals

### Proposal 1: Add schema version field to non-event schemas

- target schema: all non-event schemas
- field / rule: add required `schema_version` const
- current definition: version is documented externally but not embedded
- problem: validators must infer schema version from file path or `$id`
- proposed change: add e.g. `artifact_set_manifest_schema_version: "artifact_set_manifest.v1"` or uniform `schema_version`
- compatibility impact: breaking for current schema instances; should be done before production implementation
- blocking status: `RESOLVED_BY_PHASE16_U`

### Proposal 2: Remove empty string allowance from formal hash fields

- target schema: `artifact_registry_event.schema.json`
- field / rule: `content_hash`, `schema_hash`
- current definition: SHA-256 or empty string is accepted
- problem: Phase16-S null policy says inapplicable fields must use `null`
- proposed change: remove empty string pattern allowance and require SHA-256 or `null`
- compatibility impact: breaking only for formal events using empty string; should be fixed before production
- blocking status: `RESOLVED_BY_PHASE16_U`

### Proposal 3: Add Validation Result Schema file

- target schema: new `artifact_validation_result.schema.json`
- field / rule: machine-readable validation result
- current definition: contract-defined only in this document
- problem: future Validator output should itself be schema-validated
- proposed change: add formal JSON Schema for Validation Result in a follow-up phase
- compatibility impact: additive
- blocking status: `RESOLVED_BY_PHASE16_U`

### Proposal 4: Add old/new path fields for path migration events

- target schema: `artifact_registry_event.schema.json`
- field / rule: path migration details
- current definition: old/new path must be encoded in `reason` or `source_refs`
- problem: machine validation of `PATH_MIGRATED` is weaker
- proposed change: add optional `previous_physical_path` and `new_physical_path`
- compatibility impact: additive if optional
- blocking status: `RESOLVED_BY_PHASE16_U`

## Acceptance Criteria

This contract is accepted when:

- 7 schemas are reviewed for consistency.
- validator responsibilities are separated.
- validation pipeline is defined.
- validation result contract is defined.
- failure classification is concrete.
- event ID policy is recommended.
- acceptance evidence paths are defined.
- event log atomicity requirements are defined.
- index rebuild rules are defined.
- Phase16-P migration mapping is defined.
- role separation policy is defined.
- schema versioning is defined.
- validator read-only boundary is defined.
- schema amendments are proposalized, not directly applied.
- Runtime, Registry, and artifacts remain unchanged.

## Phase16-AJ Amendment

Acceptance validation is split into Schema validation and Cross-field validation.

Schema validation covers field presence, enum values, object shape, hash format, and machine-readable evidence structures.

Cross-field validation must cover:

- Artifact Set Type to required member roles;
- Artifact Set Type to required approval roles;
- same Artifact Set `subject_ref` across approvals, evidence bundle, report, and regression evidence;
- member hash and schema hash consistency;
- Opportunity model / metrics same-set rule;
- PM code-policy / adapter same-set rule;
- Capital Allocation policy / schema same-set rule;
- `runtime_use_eligible=true` preconditions;
- replacement ordering;
- rollback new-evidence requirement;
- `REVOKED` re-acceptance prohibition.

`artifact_acceptance_validation_result.v1` is the required output schema for the future Acceptance Evidence Builder / Validator. Existing `artifact_validation_result.v1` remains valid for general read-only validation, Full Log validation, Index validation, and non-Acceptance checks.
