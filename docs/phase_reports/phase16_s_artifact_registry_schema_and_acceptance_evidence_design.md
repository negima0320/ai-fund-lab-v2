# Phase16-S Artifact Registry Schema and Acceptance Evidence Design

## Summary

- Prefix: `Phase16-S`
- Work: `Artifact Registry Event Schema and Acceptance Evidence Contract Design`
- Final judgment: `PHASE16_S_REGISTRY_SCHEMA_AND_ACCEPTANCE_EVIDENCE_DESIGN_ACCEPTED`
- Registry production implementation: not performed
- Validator implementation: not performed
- Event Log write: not performed
- Materialized Index generation: not performed
- Artifact status change / ACCEPTED promotion: not performed
- Runtime / Consumer / AI / Feature change: not performed

This phase defines machine-readable contracts required before Registry production implementation.

## Created / Updated Files

- `docs/02_architecture/artifact_registry_event_and_acceptance_evidence_contract.md`
- `docs/02_architecture/schemas/artifact_registry_event.schema.json`
- `docs/02_architecture/schemas/artifact_registry_entry.schema.json`
- `docs/02_architecture/schemas/artifact_set_manifest.schema.json`
- `docs/02_architecture/schemas/artifact_acceptance_report.schema.json`
- `docs/02_architecture/schemas/artifact_regression_evidence.schema.json`
- `docs/02_architecture/schemas/artifact_review_approval.schema.json`
- `docs/02_architecture/schemas/artifact_registry_checkpoint.schema.json`
- `docs/02_architecture/templates/artifact_acceptance_report_template.md`
- `docs/phase_reports/phase16_s_artifact_registry_schema_and_acceptance_evidence_design.md`
- `reports/phase_reports/phase16_s_artifact_registry_schema_and_acceptance_evidence_design.json`
- `docs/01_requirements/phase_roadmap.md`

## Registry Event Schema

Defined as JSON Schema Draft 2020-12:

```text
docs/02_architecture/schemas/artifact_registry_event.schema.json
```

The event is append-only and contains identity, lifecycle status, runtime-use eligibility, hash/schema integrity, physical path, producer, consumer compatibility, source refs, point-in-time status, review/regression/acceptance refs, and superseding event refs.

Inapplicable fields use `null`. Formal events must not use string sentinels such as `NOT_APPLICABLE` or `UNKNOWN`.

## Event Types

Defined event types:

- `ARTIFACT_DISCOVERED`
- `ARTIFACT_VALIDATED`
- `REVIEW_REQUIRED`
- `ARTIFACT_ACCEPTED`
- `ARTIFACT_LEGACY`
- `ARTIFACT_REVOKED`
- `ARTIFACT_REPLACED`
- `PATH_REGISTERED`
- `PATH_MIGRATED`
- `ELIGIBILITY_CHANGED`
- `CHECKPOINT_CREATED`

Each event type has required evidence, allowed previous/new status, authority, and runtime eligibility rules in the permanent contract.

## Lifecycle Transition Matrix

The matrix defines allowed and prohibited transitions for:

```text
DRAFT
VALIDATED
REVIEW_REQUIRED
ACCEPTED
LEGACY
REVOKED
```

Explicitly prohibited:

- `DRAFT -> ACCEPTED`
- `REVIEW_REQUIRED -> ACCEPTED`
- `REVOKED -> ACCEPTED`
- `REVOKED -> VALIDATED`
- Runtime / AI / CLI / automation self-promotion to `ACCEPTED`

`LEGACY -> ACCEPTED` is allowed only through a new rollback acceptance event.

## Materialized Entry Schema

Defined as:

```text
docs/02_architecture/schemas/artifact_registry_entry.schema.json
```

The Materialized Index is a derived view. Event Log remains the audit Source of Truth. If Event Log and Index disagree, Runtime lookup must fail closed and the Index must be rebuilt from Event Log.

## Artifact Set Manifest Schema

Defined as:

```text
docs/02_architecture/schemas/artifact_set_manifest.schema.json
```

Supported set types:

- Candidate Accepted Artifact Set
- Opportunity Accepted Artifact Set
- PM Accepted Artifact Set
- Capital Allocation Policy Artifact Set

Opportunity Artifact Set requires model, metrics, feature schema, training metadata, and validation evidence in the same set. Model/metrics mismatch is classified as `HALT`.

## Acceptance Report Schema

Defined as:

```text
docs/02_architecture/schemas/artifact_acceptance_report.schema.json
```

An artifact cannot move to `ACCEPTED` without an Acceptance Report. Allowed decisions:

```text
ACCEPT
REJECT
REVIEW_REQUIRED
```

`ARTIFACT_ACCEPTED` requires `decision=ACCEPT`.

## Regression Evidence Schema

Defined as:

```text
docs/02_architecture/schemas/artifact_regression_evidence.schema.json
```

Profiles:

- `CANDIDATE`
- `OPPORTUNITY`
- `PM`
- `CAPITAL_ALLOCATION`
- `FEATURE`
- `DATA`
- `REGISTRY_PATH_ONLY`

Inapplicable parity checks use `null`; not every artifact type is forced to provide every parity field.

## Review Approval Schema

Defined as:

```text
docs/02_architecture/schemas/artifact_review_approval.schema.json
```

Approval types:

- `HUMAN_REVIEW`
- `ARCHITECTURE_ACCEPTANCE`
- `REGRESSION_ACCEPTANCE`
- `RELEASE_APPROVAL`

One-person operation remains allowed at the current stage, but roles must be recorded separately. Future production policy may require distinct reviewer IDs.

## Checkpoint Schema

Defined as:

```text
docs/02_architecture/schemas/artifact_registry_checkpoint.schema.json
```

Checkpoint is integrity evidence only. `authority_change` must be `false`.

## Cross-field Validation Rules

The permanent contract defines future validator rules including:

- `ACCEPTED` requires acceptance report, review, and regression refs.
- `runtime_use_eligible=true` is allowed only for `ACCEPTED`.
- `REVOKED` must be runtime-ineligible.
- Illegal lifecycle transitions are `HALT`.
- Opportunity model/metrics mismatch is `HALT`.
- Silent fallback to unaccepted artifact is `HALT`.
- Event Log / Index mismatch must fail closed for Runtime lookup.

Validator implementation is future work and was not performed.

## Failure Classification

Defined classes:

- `VALIDATION_ERROR`
- `REVIEW_REQUIRED`
- `HALT`

Examples:

- Missing required field: `VALIDATION_ERROR`
- Unknown producer/consumer: `REVIEW_REQUIRED`
- Missing Acceptance Report for `ACCEPTED`: `HALT`
- Hash mismatch or invalid hash format: `HALT`
- Event Log corruption: `HALT`

## Phase16-P Compatibility

Read-only compatibility evaluation result:

```text
MAPPABLE_WITH_TRANSFORMATION
```

Phase16-P Draft Events already include core identity/path/hash fields, but lack formal event identity, actor, authority, lifecycle transition, runtime eligibility, producer, consumer compatibility, source refs, and review/regression/acceptance refs.

No Phase16-P artifact was rewritten. Required migration mapping is documented in the permanent contract.

## Acceptance Report Template

Created:

```text
docs/02_architecture/templates/artifact_acceptance_report_template.md
```

The template is human-readable acceptance evidence only. It does not auto-promote artifacts.

## Schema Versioning

Initial schema versions:

- `artifact_registry_event.v1`
- `artifact_registry_entry.v1`
- `artifact_set_manifest.v1`
- `artifact_acceptance_report.v1`
- `artifact_regression_evidence.v1`
- `artifact_review_approval.v1`
- `artifact_registry_checkpoint.v1`

Event Log must retain original event schema versions forever.

## Runtime / Authority Impact

No changes were made to:

- Runtime Authority
- Current
- Ledger
- Pending
- Runtime State
- Feature
- AI
- Consumer paths
- Artifact statuses

## Unresolved Items

- Validator implementation.
- Registry production implementation.
- Event ID deterministic generation details.
- Acceptance report storage path.
- Production separation-of-duties policy.
- Corporate Action Source of Truth decision.
- Opportunity Phase5-E fallback resolution.

## Implementation Readiness

Schema and evidence contracts are ready for review. Registry production implementation can be designed after Schema review, but must not begin automatically from this phase.

## Next Prefix

Next prefix should be decided after Schema review. Recommended options:

- `Phase16-T`: Schema review and validator implementation design.
- `Phase16-T`: Registry production implementation design, if explicitly authorized.
