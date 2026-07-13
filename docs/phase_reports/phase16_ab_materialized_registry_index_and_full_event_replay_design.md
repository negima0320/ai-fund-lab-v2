# Phase16-AB Materialized Registry Index and Full Event Log Replay Design

## Final Judgment

```text
PHASE16_AB_MATERIALIZED_INDEX_AND_REPLAY_DESIGN_ACCEPTED
```

Phase16-AB completed the design-only contract for the future Materialized Registry Index Builder and Full Event Log Replay. No Index Builder, Full Log Validator, Checkpoint Writer, Registry event append, index path creation, schema modification, artifact promotion, Runtime lookup, Runtime integration, simulation, reset, or Historical Test was performed.

## Created / Updated Files

- `docs/02_architecture/materialized_registry_index_and_event_replay_contract.md`
- `docs/phase_reports/phase16_ab_materialized_registry_index_and_full_event_replay_design.md`
- `reports/phase_reports/phase16_ab_materialized_registry_index_and_full_event_replay_design.json`

## Evidence Reviewed

| Area | Evidence |
| --- | --- |
| Event / acceptance contract | `docs/02_architecture/artifact_registry_event_and_acceptance_evidence_contract.md` |
| Validator contract | `docs/02_architecture/artifact_registry_validator_contract.md` |
| Acceptance lifecycle | `docs/02_architecture/artifact_acceptance_contract.md` |
| Path and Registry storage | `docs/02_architecture/artifact_path_registry_integration_and_migration_contract.md` |
| Event schema | `docs/02_architecture/schemas/artifact_registry_event.schema.json` |
| Entry schema | `docs/02_architecture/schemas/artifact_registry_entry.schema.json` |
| Checkpoint schema | `docs/02_architecture/schemas/artifact_registry_checkpoint.schema.json` |
| Writer implementation | `src/ai_fund_lab_v2/artifact_registry/writer.py` |
| Validator implementation | `src/ai_fund_lab_v2/artifact_registry/validator.py` |
| Phase16-Z report | `docs/phase_reports/phase16_z_registry_event_writer.md` |
| Phase16-AA report | `docs/phase_reports/phase16_aa_registry_event_writer_architecture_and_implementation_closure_review.md` |

Current formal Registry state:

```text
.runtime/artifact_registry/events/registry_events.jsonl
event_count=0
.runtime/artifact_registry/index/ does not exist
```

## Authority Model

| Component | Authority |
| --- | --- |
| Event Log | Audit Source of Truth and lifecycle authority. |
| Materialized Index | Derived View only. |
| Checkpoint | Integrity Evidence only. |

The Index must not independently decide artifact status, auto-promote artifacts, change Runtime-use eligibility, choose models, or modify Runtime authorities.

## Full Log Validation

Defined required full-log checks:

- UTF-8 and BOM policy;
- one line, one JSON object;
- no blank formal rows;
- newline termination and partial-line detection;
- schema validation for every event;
- event ID uniqueness;
- fingerprint uniqueness;
- `event_created_at` format;
- artifact identity consistency;
- lifecycle legality;
- authority/evidence reference consistency;
- `runtime_use_eligible` legality;
- `PATH_REGISTERED` / `PATH_MIGRATED` field consistency.

Classification:

```text
PASS
REVIEW_REQUIRED
HALT
```

JSON corruption, partial lines, schema failure, duplicate IDs/fingerprints, illegal lifecycle, missing acceptance evidence for `ACCEPTED`, and illegal `REVOKED` recovery are `HALT`.

## Replay Ordering

Replay order is:

```text
Event Log physical line order
```

`event_created_at` is evidence only and must not be used to sort replay.

## Lifecycle Replay

Replay applies `event_type`, `previous_status`, `new_status`, `logical_artifact_id`, `artifact_instance_id`, and `runtime_use_eligible` without completing missing transitions.

Supported states:

```text
DRAFT
VALIDATED
REVIEW_REQUIRED
ACCEPTED
LEGACY
REVOKED
REJECTED
```

Illegal transitions stop replay with `HALT`.

## State Projection

Projection is defined by `logical_artifact_id`. Minimum fields include:

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

Every projected field must be reconstructable from Event Log rows.

## Active Instance Uniqueness

For one `logical_artifact_id`, only one active Runtime-use eligible accepted instance may exist. Multiple accepted active instances, multiple `runtime_use_eligible=true` instances, active `LEGACY`, and active `REVOKED` instances are `HALT`.

## History Retention

The Index retains summary history:

```text
legacy_instances
revoked_instances
event_count
last_event_id
accepted_event_id
replacement lineage
rollback lineage
```

Complete history remains in the Event Log.

## Event Type Projection

Defined projection behavior for:

```text
ARTIFACT_DISCOVERED
ARTIFACT_VALIDATED
REVIEW_REQUIRED
ARTIFACT_ACCEPTED
ARTIFACT_LEGACY
ARTIFACT_REVOKED
ARTIFACT_REPLACED
PATH_REGISTERED
PATH_MIGRATED
ELIGIBILITY_CHANGED
CHECKPOINT_CREATED
```

Path and checkpoint events are explicitly non-promotional and must not change artifact status or Runtime eligibility unless the event type contract specifically permits eligibility changes.

## Path Event Handling

`PATH_REGISTERED` can update path metadata. `PATH_MIGRATED` must use `previous_physical_path` and `new_physical_path`, verify the previous path, and update only `physical_path` and migration metadata. It must not change lifecycle status or `runtime_use_eligible`.

## Index Schema Mapping

Mapped replay state to `artifact_registry_entry.v1`.

Schema gap:

```text
artifact_registry_entry.schema.json exists
artifact_registry_index.schema.json does not exist
```

Amendment Proposal:

```text
Add artifact_registry_index.schema.json in a later schema phase.
```

No schema was added or modified in Phase16-AB.

## Event Log Hash

Defined:

```text
event_log_hash = SHA-256(file bytes)
```

This detects row order, newline, whitespace, and representation changes.

## Index Hash

Defined:

```text
index_hash = SHA-256(canonical JSON excluding index_hash and generated_at)
```

`generated_at` is excluded so deterministic rebuilds produce the same semantic hash.

## Atomic Index Write

Future builder must use:

```text
same-directory temp file
write
flush
fsync
atomic replace
parent directory fsync
```

Failed writes must preserve the previous Index.

## Lock Policy

Initial implementation must use the existing exclusive Registry lock:

```text
.runtime/artifact_registry/locks/registry.lock
```

The lock must cover full validation, hash calculation, replay, index hash calculation, and atomic replacement.

## Checkpoint Relationship

Checkpoint is Integrity Evidence, not authority. Future checkpoints should include:

```text
event_log_hash
event_count
last_event_id
materialized_index_hash
entry_count
schema_versions
validation_result
previous_checkpoint_ref
```

Checkpoint Writer remains a separate future component.

## Empty Log Behavior

The current empty Event Log is valid. Rebuild from an empty log produces:

```text
entries={}
event_count=0
last_event_id=null
```

This may be reported as `EMPTY_REGISTRY`, but it is not an error.

## Determinism and Idempotency

Identical Event Log bytes must produce identical entries, event count, last event ID, Event Log hash, and Index hash. Rebuilding the same log may return `NO_CHANGE` when the existing Index already matches.

## Failure Classification

| Classification | Meaning |
| --- | --- |
| `HALT` | Corrupt or unsafe Event Log; no Index write. |
| `REVIEW_REQUIRED` | Event Log normal but existing Index/checkpoint mismatch or review-needed condition. |
| `VALIDATION_ERROR` | Invalid builder input/output schema or configuration. |

## Recovery Boundary

Allowed recovery:

- rebuild Index from Event Log;
- atomically replace old Index;
- write validation evidence.

Forbidden recovery:

- Event Log repair;
- event deletion;
- event sorting;
- lifecycle completion;
- artifact promotion.

## Full Log Validator Reuse

AA-F2 is addressed by designing a future shared:

```text
FullEventLogValidator
```

Reusable by Writer append workflows, Index Builder replay, Checkpoint creation, and offline audit. Initial small Registry can afford full validation before Index build and before real event append.

## Fingerprint Considerations

AA-F3 is addressed by requiring event-type aware fingerprint extension before path migration, eligibility changes, checkpoint events, or acceptance events become appendable.

Known collision classes in the current Phase16-Z fingerprint:

- different `reason`;
- different `source_refs` / `source_hashes`;
- different path fields for `PATH_REGISTERED` / `PATH_MIGRATED`;
- different consumer compatibility for eligibility changes.

## Performance Boundary

Initial implementation can use:

```text
full validation
full replay
full hash
full Index rewrite
```

Checkpoint replay, incremental build, and SQLite query indexes are deferred.

## Test Plan

Required future tests:

- empty log;
- single `DRAFT`;
- `DRAFT -> VALIDATED`;
- multiple logical IDs;
- duplicate event ID;
- duplicate fingerprint;
- illegal lifecycle;
- invalid schema event;
- partial line;
- invalid JSON;
- invalid UTF-8 / BOM;
- blank line policy;
- `PATH_REGISTERED`;
- `PATH_MIGRATED`;
- `ACCEPTED -> LEGACY`;
- `ACCEPTED -> REVOKED`;
- `LEGACY -> ACCEPTED`;
- multiple active instances;
- deterministic rebuild;
- atomic index write;
- failed write preserves old index;
- event log mutation during build;
- lock contention.

## Runtime and Registry State Impact

No Runtime or Registry state was changed:

- no Event Log modification;
- no real event append;
- no Index path creation;
- no Checkpoint creation;
- no artifact status change;
- no Runtime lookup;
- no Current / Ledger / Pending change;
- no AI / Feature / Consumer change.

## Schema Amendment Proposals

| Proposal | Reason | Required now |
| --- | --- | ---: |
| Add `artifact_registry_index.schema.json` | Current schemas define entry and checkpoint, but not the full index file wrapper. | No |
| Event-type aware fingerprint versioning | Needed before path, eligibility, checkpoint, and acceptance events are appendable. | Before those event types are enabled |
| Formal Event Log blank-line/BOM policy in validator implementation | Needed for full-log replay safety. | Before Index Builder implementation |

## Implementation Readiness

| Area | Readiness |
| --- | --- |
| Materialized Index Builder Design | `READY` |
| Full Event Log Replay Contract | `READY` |
| Full Log Validator Implementation | `NOT_STARTED` |
| Materialized Index Builder Implementation | `NOT_STARTED` |
| Checkpoint Writer Implementation | `NOT_STARTED` |
| Runtime Lookup / Integration | `NOT_STARTED` |

## Next Prefix

Recommended next Prefix:

```text
Phase16-AC
```

Recommended scope:

```text
Full Event Log Validator design-to-implementation or Materialized Index Builder implementation plan, without Runtime integration or ACCEPTED promotion.
```
