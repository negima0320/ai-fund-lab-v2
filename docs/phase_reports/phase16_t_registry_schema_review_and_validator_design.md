# Phase16-T Registry Schema Review and Validator Design

## Summary

- Prefix: `Phase16-T`
- Work: `Artifact Registry Schema Review and Validator Implementation Contract`
- Final judgment: `PHASE16_T_ACCEPTED_WITH_SCHEMA_AMENDMENTS_REQUIRED`
- Validator implementation: not performed
- Registry implementation: not performed
- Schema direct modification: not performed
- Event Log / Index creation: not performed
- Artifact status / ACCEPTED promotion: not performed
- Runtime / AI / Feature / Consumer change: not performed

Phase16-S schemas are usable for design continuity, but several amendments should be reviewed before production implementation.

## Created Files

- `docs/02_architecture/artifact_registry_validator_contract.md`
- `docs/phase_reports/phase16_t_registry_schema_review_and_validator_design.md`
- `reports/phase_reports/phase16_t_registry_schema_review_and_validator_design.json`

## Schema Review Result

Result:

```text
SCHEMA_REVIEW_PASS_WITH_AMENDMENT_PROPOSALS
```

JSON parse:

```text
PASS
```

The 7 schema files all define:

- JSON Schema Draft 2020-12 `$schema`
- `$id`
- `type=object`
- `required`
- `properties`
- `additionalProperties=false`

Cross-schema consistency is broadly aligned for lifecycle status, runtime-use eligibility, hash/schema integrity, artifact set references, approval references, regression references, and checkpoint/index separation.

## Meta-schema Validation Result

```text
META_SCHEMA_VALIDATION_NOT_EXECUTED
```

Reason:

```text
jsonschema library is not installed.
```

No dependency was installed.

## Validator Responsibility Design

Defined validators:

- Schema Validator
- Lifecycle Validator
- Integrity Validator
- Artifact Set Validator
- Acceptance Evidence Validator
- Runtime Eligibility Validator
- Checkpoint Validator

Validator authority is read-only and contract-only. It must not decide AI, policy, safety, Planning, Pending, Submit, Execution, Ledger, Current, or Broker results.

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

Runtime lookup must fail closed on unsafe or inconsistent results.

## Validation Result Contract

Defined fields:

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

## Failure Classification

- `VALIDATION_ERROR`: required field missing, type mismatch, enum mismatch, invalid format, unknown schema dialect.
- `REVIEW_REQUIRED`: unknown producer, consumer compatibility unconfirmed, incomplete optional evidence, rebuildable index mismatch.
- `HALT`: hash mismatch, schema hash mismatch for Runtime-eligible artifact, model/metrics mismatch, illegal lifecycle transition, missing Acceptance Report for `ACCEPTED`, revoked artifact Runtime request, Event Log corruption, authority mismatch, silent fallback.

Artifact-specific HALT examples:

- Opportunity model/metrics mismatch.
- PM hidden liquidation authority.
- Capital Allocation Planning/Pending/Submit Guard parity failure.
- Data/Feature point-in-time violation.

## Event ID Recommendation

Recommended:

```text
Primary event_id: UUIDv7
Idempotency fingerprint: deterministic hash of event_type + logical_artifact_id + artifact_instance_id + new_status + content_hash + schema_hash + authority_ref + acceptance_report_ref
```

Fallback:

```text
ULID
```

Event ID must not define Artifact Identity or Authority.

## Acceptance Evidence Path

Defined future paths only; not created:

```text
.runtime/artifact_registry/evidence/acceptance/
.runtime/artifact_registry/evidence/regression/
.runtime/artifact_registry/evidence/approvals/
.runtime/artifact_registry/checkpoints/
.runtime/artifact_registry/validation/
```

Role split:

- `.runtime`: machine-readable operational evidence.
- `reports`: human-readable audit summaries.
- `docs`: permanent contracts, schemas, templates.

## Event Log Atomicity Requirements

Future writer must support:

- append-only JSONL
- one complete JSON event per line
- no partial line
- exclusive lock
- fsync before index update
- duplicate event ID detection
- idempotency fingerprint detection
- crash recovery
- corruption detection
- validate before append

Writer implementation was not performed.

## Index Rebuild Rules

Defined:

- replay Event Log from the beginning
- parse and validate each event
- stop on illegal lifecycle transition
- preserve `REVOKED` and `LEGACY` history
- enforce accepted instance uniqueness by logical ID and consumer scope
- store `last_event_id`
- generate canonical index hash
- compare checkpoint

Event Log / Index mismatch:

- Runtime lookup: fail closed
- Offline audit with intact Event Log: `REVIEW_REQUIRED`, rebuild from Event Log
- Event Log corruption: `HALT`

## Phase16-P Migration Mapping

Default transformed status:

```text
DRAFT
```

Allowed only with sufficient evidence:

```text
VALIDATED
```

Explicitly prohibited:

```text
ACCEPTED
runtime_use_eligible=true
invented acceptance evidence
invented regression approval
invented authority
```

Phase16-P Draft Events are migration inputs only.

## Role Separation Policy

Current single-operator policy:

- same reviewer ID may fill multiple roles during development
- roles must still be recorded separately
- role-specific evidence refs are required

Production enablement review must decide whether distinct reviewer IDs are mandatory.

## Schema Versioning Policy

- Existing events must never be rewritten.
- Event Log retains original schema versions forever.
- Validator dispatches by schema version.
- Backward-compatible changes can add optional fields.
- Breaking changes require a major schema version and migration plan.
- Unknown schema version is `REVIEW_REQUIRED` offline and `HALT` for Runtime lookup.

## Schema Amendment Proposals

### Proposal 1

- target schema: all non-event schemas
- field / rule: add required schema version const
- problem: only Event schema embeds version today
- blocking status: `REVIEW_REQUIRED_BEFORE_IMPLEMENTATION`

### Proposal 2

- target schema: `artifact_registry_event.schema.json`
- field / rule: remove empty string allowance from hash fields
- problem: null policy requires `null` for inapplicable fields
- blocking status: `REVIEW_REQUIRED_BEFORE_IMPLEMENTATION`

### Proposal 3

- target schema: new `artifact_validation_result.schema.json`
- field / rule: formal schema for Validator output
- problem: Validation Result Contract is currently document-only
- blocking status: `OPTIONAL_FOR_VALIDATOR_DESIGN_REQUIRED_FOR_VALIDATOR_IMPLEMENTATION`

### Proposal 4

- target schema: `artifact_registry_event.schema.json`
- field / rule: add previous/new physical path fields for path migration
- problem: `PATH_MIGRATED` is hard to validate if encoded only in `reason` or `source_refs`
- blocking status: `REVIEW_REQUIRED_BEFORE_PATH_MIGRATION_IMPLEMENTATION`

## Implementation Readiness

Validator implementation should not start until Schema Amendment Proposals 1 and 2 are reviewed. Proposal 3 should be completed before writing the Validator. Proposal 4 is required before path migration implementation.

## Next Prefix

Recommended:

```text
Phase16-U
```

Recommended scope:

```text
Schema Amendment Review and Minimal Schema Revision
```

Do not proceed to Validator implementation or Registry production implementation until amendments are accepted.
