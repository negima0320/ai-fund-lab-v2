# Materialized Registry Index and Event Replay Contract

Status: Phase16-AB accepted design

This document defines the permanent contract for rebuilding the Materialized Registry Index from the append-only Artifact Registry Event Log. It is a design contract only. It does not implement an Index Builder, Full Log Validator, Checkpoint Writer, Runtime lookup, artifact promotion, event migration, or Runtime integration.

## Purpose

The Artifact Registry uses this authority model:

```text
Event Log = Authority
Materialized Index = Derived View
Checkpoint = Integrity Evidence
```

The Event Log is the audit Source of Truth. The Materialized Index is a deterministic view rebuilt from the Event Log. A Checkpoint records integrity evidence about a specific Event Log and Index pair. If the Event Log and Index disagree, the Event Log wins and Runtime use must fail closed until the Index is rebuilt and validated.

## Authority Boundary

The Index Builder may:

- validate the full Event Log before replay;
- replay events in Event Log physical line order;
- derive current status and summary history per `logical_artifact_id`;
- rebuild the Materialized Index from scratch;
- write validation evidence and future checkpoint inputs.

The Index Builder must not:

- create a status not present in the Event Log;
- infer or auto-promote `ACCEPTED`;
- change `runtime_use_eligible` independently;
- choose a model or artifact for Runtime;
- write Event Log events;
- repair, delete, truncate, reorder, or edit Event Log lines;
- modify Current, Ledger, Pending, Runtime State, Feature, AI, Planning, Submit, or Broker state.

Exception boundary: a Limited Registry Recovery Transaction may replace the Event Log bytes only when the recovery transaction is approved under `artifact_registry_event_and_acceptance_evidence_contract.md`, the removed events were never Runtime authority, a full pre-recovery backup is retained, and the Index and Checkpoint are rebuilt from the recovered Event Log by formal tools. The Index Builder must not decide or perform this recovery; it may only validate and replay the resulting Event Log.

## Full Event Log Validation

Replay must be preceded by full validation of every Event Log byte and every event row. Validation result classes are:

| Result | Meaning |
| --- | --- |
| `PASS` | Event Log is replayable and Index can be derived. |
| `REVIEW_REQUIRED` | Event Log is structurally valid, but an operator or architecture review is required before use. |
| `HALT` | Event Log is unsafe or corrupt; replay and index write must stop. |

Required full-log checks:

| Check | Rule | Failure |
| --- | --- | --- |
| UTF-8 | File bytes must decode as UTF-8. | `HALT` |
| BOM policy | UTF-8 BOM is prohibited for formal Event Log bytes. | `HALT` |
| One line, one JSON | Each non-empty line is exactly one JSON object. | `HALT` |
| Empty line policy | Blank lines are invalid in formal logs. Existing Writer currently ignores blanks; Index Builder must tighten this before production replay. | `HALT` |
| Newline terminator | Every event line must end in `\n`; partial trailing JSON is invalid. | `HALT` |
| JSON object | Parsed value must be an object. | `HALT` |
| Event Schema | Each event must conform to `artifact_registry_event.v1`. | `HALT` |
| Event ID uniqueness | `event_id` must be unique across the entire log. | `HALT` |
| Fingerprint uniqueness | deterministic event fingerprint must be unique across the entire log. | `HALT` |
| `event_created_at` | Must be valid date-time evidence. | `HALT` if schema/format invalid |
| Artifact identity | Identity fields must be coherent for artifact events. | `HALT` |
| Lifecycle transition | Transition must be legal for the current replayed instance state. | `HALT` |
| Authority refs | Required authority/evidence refs must exist for status-changing events. | `HALT` for `ACCEPTED`, otherwise `REVIEW_REQUIRED` or `HALT` by severity |
| Runtime eligibility | `runtime_use_eligible=true` is legal only for `ACCEPTED` instances and compatible consumers. | `HALT` |
| Path migration fields | `PATH_MIGRATED` must include `previous_physical_path` and `new_physical_path`; `PATH_REGISTERED` must include `physical_path`. | `HALT` |

The following always stop replay with `HALT`: invalid JSON, invalid UTF-8, partial line, schema failure, duplicate `event_id`, duplicate fingerprint, illegal lifecycle, missing acceptance evidence for an `ARTIFACT_ACCEPTED` event, illegal return from `REVOKED`, and Event Log order corruption.

## Replay Input Contract

Input is the append-only JSONL file:

```text
.runtime/artifact_registry/events/registry_events.jsonl
```

The builder must treat the file bytes, not an external manifest or timestamp sort, as the replay source. The initial formal Registry currently contains an empty Event Log with zero rows. That is a valid input.

## Replay Ordering

Replay order is:

```text
Event Log physical line order
```

`event_created_at` is evidence, not ordering authority. The builder must not sort by timestamp, event ID, logical ID, artifact version, or hash. Append order equals audit order and lifecycle application order.

## Lifecycle Replay

For each event, replay uses:

- `event_type`
- `logical_artifact_id`
- `artifact_instance_id`
- `previous_status`
- `new_status`
- `runtime_use_eligible`

Supported statuses:

```text
DRAFT
VALIDATED
REVIEW_REQUIRED
ACCEPTED
LEGACY
REVOKED
REJECTED
```

Allowed lifecycle transitions are inherited from the Artifact Acceptance and Event contracts:

| From | To | Rule |
| --- | --- | --- |
| `null` | `DRAFT` | Initial discovery. |
| `DRAFT` | `VALIDATED` | Validation evidence required. |
| `DRAFT` | `REVIEW_REQUIRED` | Blocking reason required. |
| `VALIDATED` | `REVIEW_REQUIRED` | Review or validation gap found. |
| `VALIDATED` | `ACCEPTED` | Review, regression, release, and acceptance evidence required. |
| `VALIDATED` | `REVOKED` | Revoke evidence required. |
| `REVIEW_REQUIRED` | `VALIDATED` | Gap resolved by validation evidence. |
| `ACCEPTED` | `LEGACY` | Replacement or deactivation. |
| `ACCEPTED` | `REVOKED` | Immediate deny. |
| `LEGACY` | `ACCEPTED` | Rollback only through a new acceptance event. |
| `LEGACY` | `REVOKED` | Legacy artifact banned. |

Prohibited transitions include `DRAFT -> ACCEPTED`, `REVIEW_REQUIRED -> ACCEPTED`, `REVOKED -> ACCEPTED`, and `REVOKED -> VALIDATED`. The Index Builder must not complete missing transitions.

## State Projection

Projection is by `logical_artifact_id`. Each logical artifact entry summarizes the replayed state and must be reconstructable from Event Log rows.

Minimum derived fields:

| Index field | Replay source | Derived rule |
| --- | --- | --- |
| `logical_artifact_id` | Event identity | Entry key and value must match. |
| `active_artifact_instance_id` | latest active `ACCEPTED` event | `null` unless exactly one active accepted runtime-eligible instance exists. |
| `artifact_type` | latest artifact event | Latest non-null value for the logical artifact. |
| `component` | latest artifact event | Latest non-null value for the logical artifact. |
| `current_status` | latest lifecycle event | Status after physical-line replay. |
| `runtime_use_eligible` | latest eligibility/status event | True only when current status is `ACCEPTED` and eligibility event permits it. |
| `physical_path` | artifact/path events | Latest registered or migrated path. |
| `content_hash` | artifact events | Latest content hash for the current instance. |
| `schema_hash` | artifact events | Latest schema hash for the current instance. |
| `artifact_set_id` | artifact events | Latest set ID, or `null`. |
| `accepted_event_id` | latest accepted event | Event ID for active accepted instance, else `null`. |
| `accepted_at` | `ARTIFACT_ACCEPTED.event_created_at` | Timestamp evidence for active acceptance, else `null`. |
| `accepted_by` | acceptance event actor or authority | Actor/authority that accepted active instance, else `null`. |
| `legacy_instances` | `ARTIFACT_LEGACY` / `ARTIFACT_REPLACED` | Unique artifact instance IDs retained in replay order. |
| `revoked_instances` | `ARTIFACT_REVOKED` | Unique artifact instance IDs retained in replay order. |
| `last_event_id` | last event for entry | Must reference a row in the Event Log. |
| `last_updated_at` | last event `event_created_at` | Evidence timestamp; does not define replay order. |
| `derived_from_event_log` | builder constant | Must be `true`. |

Any additional field in a future index must be deterministically rebuildable from the Event Log.

## Active Instance Uniqueness

For each `logical_artifact_id`, at most one active instance may be both:

```text
current_status=ACCEPTED
runtime_use_eligible=true
```

The builder must classify the following as `HALT`:

- multiple active `ACCEPTED` instances for the same logical artifact and consumer scope;
- multiple instances with `runtime_use_eligible=true`;
- an instance appearing as both active and `LEGACY`;
- a `REVOKED` instance appearing as active;
- an `ELIGIBILITY_CHANGED` event that makes a non-`ACCEPTED` instance Runtime-eligible.

Phase16-Z Writer cannot append `ACCEPTED`, `LEGACY`, or `REVOKED`; these rules are for future Acceptance Writer and Index Builder phases.

## History Retention

The Materialized Index keeps summary history only. It must retain:

- `legacy_instances`
- `revoked_instances`
- `event_count`
- `last_event_id`
- `accepted_event_id`
- replacement lineage summary
- rollback lineage summary

The complete audit history remains the Event Log. The Index is not a replacement for the Event Log.

## Event Type Projection

| Event type | Updates | Must not update | Required previous state |
| --- | --- | --- | --- |
| `ARTIFACT_DISCOVERED` | identity, type, component, path, hashes, status `DRAFT`, last event | accepted fields, eligibility true | no active instance for same artifact instance |
| `ARTIFACT_VALIDATED` | status `VALIDATED`, hashes/schema/producer/consumer evidence, last event | acceptance fields, eligibility true | `DRAFT` or `REVIEW_REQUIRED` |
| `REVIEW_REQUIRED` | status `REVIEW_REQUIRED`, reason, last event | acceptance fields, eligibility true | `DRAFT`, `VALIDATED`, or `REVIEW_REQUIRED` |
| `ARTIFACT_ACCEPTED` | status `ACCEPTED`, active instance, acceptance fields, optional eligibility, last event | legacy/revoked history except through explicit replacement/revoke | `VALIDATED` or rollback from `LEGACY` with evidence |
| `ARTIFACT_LEGACY` | status `LEGACY`, clear active instance, add legacy history, last event | acceptance history deletion, Event Log repair | active `ACCEPTED` |
| `ARTIFACT_REVOKED` | status `REVOKED`, clear active instance, add revoked history, force eligibility false, last event | reactivation | `ACCEPTED`, `LEGACY`, `VALIDATED`, or `REVIEW_REQUIRED` |
| `ARTIFACT_REPLACED` | mark replaced instance `LEGACY`, replacement lineage, last event | acceptance of replacing instance unless separately logged | active `ACCEPTED` replaced instance |
| `PATH_REGISTERED` | `physical_path`, path classification, last event | status, acceptance fields, eligibility | existing `DRAFT`, `VALIDATED`, or `ACCEPTED` entry |
| `PATH_MIGRATED` | `physical_path` from `new_physical_path`, migration status, lineage, last event | status, acceptance fields, eligibility | `ACCEPTED` or `LEGACY` entry with matching previous path |
| `ELIGIBILITY_CHANGED` | `runtime_use_eligible`, consumer compatibility, last event | status, path, hashes | same instance in `ACCEPTED` or `LEGACY`; true only for `ACCEPTED` |
| `CHECKPOINT_CREATED` | global checkpoint linkage only | per-artifact status, path, eligibility | none |

## Path Event Handling

`PATH_REGISTERED` records or refreshes a physical path without changing lifecycle status or Runtime-use eligibility.

`PATH_MIGRATED` must use:

```text
previous_physical_path
new_physical_path
```

The builder updates `physical_path` to `new_physical_path` only after verifying the previous path matches the replayed entry. Path events must never promote an artifact, revoke an artifact, or change `runtime_use_eligible`.

## Index Schema Mapping

The current entry schema is:

```text
artifact_registry_entry.v1
```

Mapping from replay state to `artifact_registry_entry.v1`:

| Schema field | Replay source | Derived rule |
| --- | --- | --- |
| `schema_version` | constant | `artifact_registry_entry.v1` |
| `logical_artifact_id` | event identity | required non-null for artifact entries |
| `active_artifact_instance_id` | accepted active state | active instance or `null` |
| `artifact_type` | event identity | latest non-null |
| `component` | event identity | latest non-null |
| `current_status` | lifecycle replay | latest current status |
| `runtime_use_eligible` | lifecycle/eligibility replay | boolean, true only for accepted eligible |
| `physical_path` | artifact/path replay | latest known path or `null` |
| `content_hash` | artifact replay | current instance content hash or `null` |
| `schema_hash` | artifact replay | current instance schema hash or `null` |
| `artifact_set_id` | artifact replay | current artifact set or `null` |
| `accepted_event_id` | acceptance replay | active acceptance event or `null` |
| `accepted_at` | acceptance event | active acceptance timestamp or `null` |
| `accepted_by` | acceptance event | actor or authority ref |
| `legacy_instances` | lifecycle replay | ordered unique strings |
| `revoked_instances` | lifecycle replay | ordered unique strings |
| `last_event_id` | last event | event ID for latest event affecting entry |
| `last_updated_at` | last event | `event_created_at` evidence |
| `derived_from_event_log` | constant | `true` |

The repository currently has an entry schema but not a full index file schema for metadata such as `event_log_hash`, `event_count`, `entries`, and `index_hash`.

Amendment proposal:

```text
Add docs/02_architecture/schemas/artifact_registry_index.schema.json
```

The proposed index file schema should define:

```json
{
  "schema_version": "artifact_registry_index.v1",
  "generated_at": "...",
  "event_log_hash": "...",
  "event_count": 0,
  "last_event_id": null,
  "entries": {},
  "index_hash": "..."
}
```

No schema is added or modified by this phase.

## Materialized Index File

Future recommended path:

```text
.runtime/artifact_registry/index/registry_index.json
```

This phase does not create that path.

The file-level structure should include:

- `schema_version`
- `generated_at`
- `event_log_hash`
- `event_count`
- `last_event_id`
- `entries`
- `index_hash`

## Event Log Hash

The Event Log hash is:

```text
event_log_hash = SHA-256(file bytes)
```

This includes line order, newlines, whitespace, JSON representation, and any byte-level mutation. It differs from a canonical event hash chain: a file-byte hash detects file representation changes directly, while a hash chain can prove ordered event membership even if storage is reserialized. Phase16 initial implementation should use file-byte SHA-256; canonical hash chain can be a later extension if needed.

## Index Hash

The Index hash is:

```text
index_hash = SHA-256(canonical JSON of index object excluding index_hash and generated_at)
```

Canonicalization rules:

- UTF-8;
- `sort_keys=true`;
- compact separators;
- JSON `null` for inapplicable values;
- arrays preserve replay order;
- output file ends with a newline;
- `generated_at` is excluded from `index_hash` to preserve deterministic rebuilds.

## Atomic Index Write

The future Index Builder must write atomically:

```text
same-directory temp file
write complete canonical JSON
flush
fsync temp file
atomic replace
fsync parent directory
```

It must not directly overwrite the existing Index. If the write fails, the old Index must remain intact. A partial temp file is not an authoritative Index.

## Lock Policy

Initial implementation should use the same exclusive Registry lock as the Writer:

```text
.runtime/artifact_registry/locks/registry.lock
```

The lock must cover:

- full Event Log validation;
- Event Log byte hashing;
- full replay;
- Index hash calculation;
- atomic Index replacement.

Reason: if a Writer appends during replay, `event_log_hash`, `event_count`, `last_event_id`, and the derived entries may no longer refer to the same source. Shared locks or snapshot reads can be reviewed later after correctness is established.

## Checkpoint Relationship

Checkpoint is integrity evidence, not authority. A future Checkpoint Writer may run after a successful Index build and record:

- `event_log_hash`;
- `event_count`;
- `last_event_id`;
- `materialized_index_hash`;
- `entry_count`;
- schema versions;
- validation result;
- previous checkpoint reference.

The Index Builder may produce checkpoint inputs, but it must not be the authority that changes artifact lifecycle. Checkpoint mismatch with an intact Event Log is `REVIEW_REQUIRED`; Event Log corruption is `HALT`.

## Empty Log Behavior

An empty Event Log is a valid Registry state:

```json
{
  "entries": {},
  "event_count": 0,
  "last_event_id": null
}
```

The builder may report `EMPTY_REGISTRY` as informational evidence. It must not treat empty log as an error.

## Determinism

Given identical Event Log bytes and identical schema/version rules, rebuild must produce:

- same entries;
- same `event_count`;
- same `last_event_id`;
- same `event_log_hash`;
- same `index_hash`.

`generated_at` may differ and is excluded from `index_hash`.

## Idempotency

Building from the same Event Log repeatedly must produce the same semantic Index. If the existing Index already has the same `event_log_hash` and `index_hash`, a future builder may return:

```text
NO_CHANGE
```

without changing the file.

## Failure Classification

| Class | Examples | Builder behavior |
| --- | --- | --- |
| `HALT` | Event Log corruption, schema failure, illegal lifecycle, duplicate ID, duplicate fingerprint, multiple active instances, Event Log hash failure, projection impossible | Stop replay and do not write Index. |
| `REVIEW_REQUIRED` | Existing Index mismatch but Event Log normal, checkpoint mismatch with normal Event Log, rebuildable stale Index | Produce evidence; allow reviewed rebuild. |
| `VALIDATION_ERROR` | invalid input path, output schema mismatch, malformed builder config | Stop before authoritative write. |

## Recovery Boundary

The Index Builder may recover by:

- rebuilding Index from the Event Log;
- replacing an old Index atomically with the rebuilt Index;
- writing validation evidence.

The Index Builder must not recover by:

- repairing Event Log corruption;
- deleting events;
- truncating partial lines;
- reordering events;
- completing missing lifecycle transitions;
- promoting or accepting artifacts.

Event Log repair requires a separate reviewed operational procedure.

## Full Log Validator Reuse

Phase16-AA finding AA-F2 is closed at the design level by requiring a future common component:

```text
FullEventLogValidator
```

The common validator should be reusable by:

- Writer append workflows before accepting real event ingestion;
- Index Builder replay;
- Checkpoint creation;
- offline audit.

Options:

| Option | Strength | Risk | Initial recommendation |
| --- | --- | --- | --- |
| Full validation before every append | strongest early safety | slower as log grows | acceptable for initial small Registry |
| Full validation before Index/Checkpoint only | lower append cost | delayed detection of pre-existing bad rows | acceptable only for test roots, not production ingestion |
| Checkpoint-assisted incremental validation | scalable | more implementation complexity | later phase |

Phase16 initial Registry is small, so full validation before Index build and before real event append is acceptable.

## Fingerprint Considerations

Phase16-Z fingerprint basis is:

```text
event_type
logical_artifact_id
artifact_instance_id
new_status
content_hash
schema_hash
authority_ref
acceptance_report_ref
```

This provides idempotency for basic DRAFT/VALIDATED events but has known collision classes:

- events differing only by `reason`;
- events differing only by `source_refs` or `source_hashes`;
- `PATH_REGISTERED` events differing only by `physical_path`;
- `PATH_MIGRATED` events differing only by `previous_physical_path` or `new_physical_path`;
- eligibility changes differing only by consumer compatibility details.

Design requirement: before path migration, eligibility changes, checkpoint events, or acceptance events are appendable, the fingerprint contract must become event-type aware. Full Log Validation must detect duplicate fingerprints using the active fingerprint version recorded by the implementation contract.

## Performance Boundary

Initial Registry scale permits:

```text
full validation
full replay
full Event Log byte hash
full Index rewrite
```

Deferred optimizations:

- checkpoint-assisted replay;
- incremental build;
- SQLite query index;
- shared read locks;
- segment hashes or event hash chains.

These are not required for Phase16 initial implementation and must not precede the correctness contract.

## Test Plan

Implementation of the Index Builder must include tests for:

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
- invalid UTF-8 and BOM;
- blank line policy;
- `PATH_REGISTERED`;
- `PATH_MIGRATED`;
- `ACCEPTED -> LEGACY`;
- `ACCEPTED -> REVOKED`;
- `LEGACY -> ACCEPTED` rollback;
- multiple active instances;
- deterministic rebuild;
- atomic index write;
- failed write preserves old index;
- event log mutation during build;
- lock contention;
- checkpoint mismatch classification;
- existing Index mismatch classification.

## Design-change Stop Rule

Stop for separate review if implementation requires:

- Event Schema changes;
- lifecycle meaning changes;
- Registry authority changes;
- Artifact Acceptance meaning changes;
- Runtime-use eligibility meaning changes;
- Runtime integration;
- consumer path changes.

Possible stop classifications:

```text
SCHEMA_AMENDMENT_REQUIRED
ARCHITECTURE_REVIEW_REQUIRED
SPEC_CHANGE_REQUIRED
```

## Acceptance Criteria

The Materialized Index Builder implementation cannot begin until this contract is accepted and its implementation plan preserves:

- Event Log as authority;
- Index as derived view;
- full Event Log validation before replay;
- physical line order replay;
- lifecycle replay without inference;
- logical artifact projection;
- active instance uniqueness;
- LEGACY / REVOKED history retention;
- event-type projection rules;
- path event non-authority;
- deterministic Event Log and Index hashes;
- atomic Index write;
- exclusive lock policy;
- checkpoint responsibility separation;
- empty log normal behavior;
- deterministic rebuild and idempotency;
- failure classification and recovery boundary;
- AA-F2 and AA-F3 closure path.
