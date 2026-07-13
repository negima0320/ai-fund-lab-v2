# Phase16-AA Registry Event Writer Architecture and Implementation Closure Review

## Executive Summary

Final judgment:

```text
PHASE16_AA_WRITER_ACCEPTED_WITH_MINOR_FIXES
```

Writer readiness:

```text
ACCEPTED_WITH_MINOR_FIXES
```

Phase16-Z implemented an append-only Registry Event Log Writer that is aligned with the Artifact Registry contracts and Phase16 Operational Data Foundation. The writer validates events before append, writes only `DRAFT` and `VALIDATED` events, rejects promotion statuses, uses an exclusive POSIX lock, checks duplicate event IDs and deterministic fingerprints, detects corrupted/partial existing log lines, and writes only to the formal Registry Event Log path.

No code, tests, schemas, real events, index, checkpoint writer, Runtime, AI, Feature, Artifact Status, or Artifact Acceptance changes were made during this Phase16-AA review.

## Review Scope

Reviewed:

- Project and Phase16 Operational Data Foundation purpose.
- Artifact Registry, Acceptance, Validator, Event Log, and path contracts.
- Phase16-Y and Phase16-Z reports.
- `src/ai_fund_lab_v2/artifact_registry/writer.py`
- `src/ai_fund_lab_v2/artifact_registry/validator.py`
- `tests/artifact_registry/test_phase16z_registry_event_writer.py`
- Formal Registry path under `.runtime/artifact_registry/`
- Current Event Log state.
- Runtime import graph and protected hash evidence.

Executed:

```text
python3 -m pytest -q tests/artifact_registry/test_inventory_helpers.py tests/artifact_registry/test_phase16u_schema_amendments.py tests/artifact_registry/test_phase16v_read_only_validator.py tests/artifact_registry/test_phase16x_validator_hardening.py tests/artifact_registry/test_phase16z_registry_event_writer.py
```

Result:

```text
55 passed
```

## Project Purpose Alignment

Judgment: `ACCEPTED`

The writer supports the top-level purpose:

```text
安心・安全に継続運用できる日本株自動売買システムを作り、
最終的にProduction運用する
```

It strengthens auditability and correctness by creating the first append-only Registry Event Log component. It does not make trading decisions, select artifacts, promote artifacts, or modify Runtime state.

## Phase16 Scope Alignment

Judgment: `ACCEPTED`

The writer is not Historical-only, Backtest-only, or Phase16-only. It uses the permanent Registry Event schema and writes to the formal operational Registry path:

```text
.runtime/artifact_registry/
```

There is no mode-specific Event schema, no Runtime Mainline connection, and no artifact auto-promotion.

## Writer Responsibility

Judgment: `ALIGNED`

Observed responsibilities:

- receive event;
- compute deterministic fingerprint;
- generate UUIDv4 + fingerprint event ID when absent;
- run validator;
- enforce writer status boundary;
- acquire exclusive lock;
- read existing Event Log;
- reject duplicate event ID and fingerprint;
- append one JSON line;
- fsync;
- release lock;
- return append result.

Not observed:

- no Event content status correction;
- no Artifact Acceptance;
- no `runtime_use_eligible` mutation;
- no Artifact or model selection;
- no Index update;
- no Current / Ledger / Pending mutation;
- no Planning / Submit control.

Note: event ID generation is expected by the Event ID policy and is not artifact status correction.

## Authority Boundary

Judgment: `ACCEPTED`

Writer allowed statuses:

```text
DRAFT
VALIDATED
```

Rejected by writer logic:

```text
ACCEPTED
LEGACY
REVOKED
runtime_use_eligible=true
```

The writer enforces status after validation, so even a schema-valid future `ACCEPTED` event path would still be blocked by writer policy. `new_status=null` and invalid statuses fail validation. No existing `VALIDATED` event is interpreted as `ACCEPTED`.

Artifact Acceptance remains unreachable from Phase16-Z Writer.

## Formal Registry Path

Judgment: `ACCEPTED_WITH_MINOR_GAPS`

Created:

```text
.runtime/artifact_registry/events/
.runtime/artifact_registry/events/registry_events.jsonl
.runtime/artifact_registry/locks/
.runtime/artifact_registry/locks/registry.lock
.runtime/artifact_registry/schema/
.runtime/artifact_registry/checkpoints/
```

Not created:

```text
.runtime/artifact_registry/index/
```

The path structure matches Phase16-L/T design and does not overlap with Current, Ledger, Pending, Runtime State, or `.runtime/artifacts`.

Minor gaps:

- existing path-as-file or permission failures stop through standard filesystem exceptions, but are not mapped to dedicated writer exception types;
- symlink policy for the Event Log path is not explicit.

## Validation Gate

Judgment: `ACCEPTED_WITH_MINOR_GAPS`

Append requires:

```text
overall_result=PASS
failure_class=NONE
```

Rejected:

- `PASS_WITH_WARNINGS`
- `REVIEW_REQUIRED`
- `FAIL`
- `HALT`

The writer copies the input event into `event_to_append`, validates that exact object, and serializes that same object after validation. This blocks caller-side mutation after function entry from changing the appended object.

Minor gap:

- validation occurs before lock acquisition. The Event Log duplicate scan is lock-protected, but the referenced artifact file can theoretically change between validation and append. This is a general artifact-file TOCTOU risk and should be handled before high-trust real event append workflows.

## Append-only Review

Judgment: `ACCEPTED`

Observed:

- `os.open(..., O_APPEND | O_CREAT | O_WRONLY)`
- no truncate;
- no seek;
- no rewrite of existing file;
- no replace;
- no sort;
- no deduplicate-by-rewrite;
- existing event mutation is not implemented.

Event correction must be represented as a future new event, not by editing existing lines.

## Atomicity Review

Judgment:

```text
ATOMIC_ENOUGH_FOR_CURRENT_SCOPE
```

Implementation:

```text
json.dumps(..., ensure_ascii=True)
↓
encode utf-8
↓
append newline
↓
os.write loop
↓
os.fsync
↓
os.close
```

Strengths:

- one event is encoded as one JSON object plus newline;
- embedded newlines are escaped by JSON encoding;
- zero-byte writes raise;
- `EINTR` retries;
- `fsync` is called before success is returned;
- file descriptor is closed in `finally`.

Limitation:

- POSIX regular-file writes with `O_APPEND` do not provide an absolute crash-proof guarantee for an entire logical line if a process is killed, disk fills, or an OS/filesystem fault occurs mid-write. A partial trailing line could remain.
- The writer detects partial lines on the next read and refuses further append, but does not repair.

Classification:

```text
PARTIAL_LINE_RISK_REMAINS
```

This is non-blocking for current empty-log initialization and isolated writer tests, but should be addressed or operationally accepted before large-scale real event ingestion.

## Lock / Concurrency Review

Judgment: `ACCEPTED_WITH_MINOR_GAPS`

Implementation:

```text
fcntl.flock
LOCK_EX | LOCK_NB
timeout
```

Confirmed:

- duplicate scan and append occur inside the same lock section;
- exceptions release lock through context manager `__exit__`;
- lock contention test passes;
- same-process contention using a held lock is rejected.

Operational boundary:

- lock is POSIX/macOS `fcntl` based;
- behavior on NFS or non-POSIX filesystems is not guaranteed;
- lock file deletion while open is not explicitly handled;
- validator runs before lock acquisition, which avoids long lock hold time but leaves artifact-file TOCTOU risk.

## Duplicate / Idempotency Review

Judgment: `ACCEPTED_WITH_MINOR_GAPS`

Fingerprint input matches Phase16-T:

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

Canonicalization:

- payload uses deterministic JSON hash via `stable_json_hash`;
- nulls are represented by JSON `null`;
- key order is deterministic;
- `event_id` is excluded, so UUID differences do not bypass idempotency.

Limitations:

- `reason` and `source_refs` are not fingerprint inputs by contract, so two events differing only by those fields collide.
- `PATH_REGISTERED` / `PATH_MIGRATED` path fields are not fingerprint inputs. This is not used for Phase16-Z DRAFT/VALIDATED writer scope, but should be revisited before path migration events are allowed.

## Existing Log Validation

Judgment:

```text
STRUCTURAL_VALIDATION_ONLY
```

Currently checked before append:

- every nonblank line parses as JSON;
- every event line is newline-terminated;
- each parsed row is an object;
- new event ID is not already present;
- new fingerprint is not already present.

Not currently checked for existing log:

- full schema validation for every existing event;
- lifecycle validation for every existing event;
- internal duplicate event IDs among existing rows if they do not match the new event;
- internal duplicate fingerprints among existing rows if they do not match the new event.

This is acceptable for the current empty Event Log and first writer phase, but should be tightened before Index Builder or real event append at scale.

## Corruption Detection

Judgment: `ACCEPTED_WITH_MINOR_GAPS`

Detected:

- invalid JSON line;
- partial trailing line without newline;
- non-object JSON event;
- duplicate new event ID;
- duplicate new fingerprint.

Behavior:

- append is rejected;
- writer does not repair, truncate, delete, or rewrite;
- operator review is required.

Gaps:

- blank lines are ignored;
- BOM / invalid UTF-8 behavior is surfaced via JSON decode path, but not tested;
- huge line limits are not enforced;
- Event Log symlink policy is implicit;
- permission errors propagate as filesystem exceptions, not dedicated writer errors.

## Failure / Recovery Review

| Failure | Exception / behavior | Event added? | Log state | Lock release | Operator action |
| --- | --- | ---: | --- | --- | --- |
| Lock timeout | `RegistryLockError` | No | unchanged | lock not acquired by writer | retry after owner exits |
| Validation failure | `RegistryEventValidationError` | No | empty/unchanged | no lock acquired | fix event/evidence |
| Duplicate event ID | `RegistryDuplicateEventError` | No | unchanged | yes | use existing event or new event ID with distinct fingerprint |
| Duplicate fingerprint | `RegistryDuplicateEventError` | No | unchanged | yes | treat as replay/idempotent reject |
| Log corruption | `RegistryLogCorruptionError` | No | unchanged | yes | reviewed repair procedure needed |
| Partial write / process kill | may leave partial line | Unknown | partial line possible | OS-dependent | future append halts; manual review |
| fsync failure | `OSError` | line may already be written | durability uncertain | yes | inspect log; retry only after review |
| Disk full | `OSError` | partial line possible | uncertain | yes | free space and inspect log |
| Permission denied | filesystem exception | No | unchanged | if lock opened, context handles | fix permission |
| Registry directory missing | initialized | No event until append | directories created | n/a | expected |
| Lock file abnormal | filesystem exception | No | unchanged | n/a | inspect registry path |

The writer deliberately has no repair feature. This is safe for current scope.

## Event Count / Real Event Review

Formal Event Log:

```text
.runtime/artifact_registry/events/registry_events.jsonl
```

Current event count:

```text
0
```

No real Registry Event was appended during Phase16-Z or Phase16-AA. Tests use isolated temporary registry roots.

## Test Coverage

Judgment: `ACCEPTED_WITH_MINOR_GAPS`

Current tests cover:

- append success;
- formal path initialization in isolated root;
- duplicate fingerprint;
- duplicate event ID;
- validator failure;
- `ACCEPTED` / `LEGACY` / `REVOKED` reject;
- lock contention;
- corrupted JSON;
- partial line;
- fsync;
- failed append no event;
- multiple append;
- stable fingerprint.

Missing tests and classification:

| Gap | Classification |
| --- | --- |
| PASS_WITH_WARNINGS reject | `REQUIRED_BEFORE_REAL_EVENT_APPEND` |
| REVIEW_REQUIRED reject | `REQUIRED_BEFORE_REAL_EVENT_APPEND` |
| zero-byte `os.write` | `REQUIRED_BEFORE_REAL_EVENT_APPEND` |
| fsync failure leaves review-required state | `REQUIRED_BEFORE_REAL_EVENT_APPEND` |
| disk full simulation | `REQUIRED_BEFORE_PRODUCTION` |
| permission denied | `REQUIRED_BEFORE_REAL_EVENT_APPEND` |
| lock release on append exception | `REQUIRED_BEFORE_REAL_EVENT_APPEND` |
| non-UTF8 log | `REQUIRED_BEFORE_INDEX_BUILDER` |
| blank line policy | `REQUIRED_BEFORE_INDEX_BUILDER` |
| existing internal duplicate events | `REQUIRED_BEFORE_INDEX_BUILDER` |
| existing illegal lifecycle event | `REQUIRED_BEFORE_INDEX_BUILDER` |
| symlink Event Log | `REQUIRED_BEFORE_PRODUCTION` |
| concurrent multi-process append | `REQUIRED_BEFORE_PRODUCTION` |
| valid second event for same logical artifact | `REQUIRED_BEFORE_REAL_EVENT_APPEND` |
| PATH_MIGRATED fingerprint collision | `REQUIRED_BEFORE_ARTIFACT_MIGRATION` |

## Runtime / System Non-impact

Judgment: `ACCEPTED`

Confirmed:

- Runtime v2 unchanged by Phase16-AA.
- Runtime CLI unchanged.
- Runtime config unchanged.
- Current unchanged.
- Ledger unchanged.
- Pending unchanged.
- Runtime State unchanged.
- Candidate Model unchanged.
- Opportunity Model unchanged.
- Metrics unchanged.
- PM code-policy unchanged.
- Feature Schema / calculation unchanged.
- Consumer path unchanged.
- Opportunity fallback unchanged.
- Capital Allocation behavior unchanged.
- Runtime does not import `ai_fund_lab_v2.artifact_registry.writer`.

Protected hash status:

```text
UNCHANGED
```

## Remaining Phase16-Y Minor Findings

### Y-F1 Report Write Atomicity

Still open for report evidence generation. It is separate from Event Log Writer append. It should be closed before automated report/index workflows, but it does not block the current Event Log Writer closure.

### Y-F2 Schema Checker Strategy

The writer depends on the current hardened minimal validator. This is sufficient for the current schemas and DRAFT/VALIDATED writer phase. Formal dependency strategy remains required before Runtime integration.

### Y-F3 Role-to-Artifact-Type Compatibility

Non-blocking for DRAFT/VALIDATED Event Writer. It remains relevant before Artifact Acceptance.

## Design Conformance Matrix

| Area | Judgment |
| --- | --- |
| Project Purpose Alignment | `ACCEPTED` |
| Phase16 Scope Alignment | `ACCEPTED` |
| Writer Responsibility | `ACCEPTED` |
| Authority Boundary | `ACCEPTED` |
| Formal Registry Path | `ACCEPTED_WITH_MINOR_GAPS` |
| Validation Gate | `ACCEPTED_WITH_MINOR_GAPS` |
| Append-only Guarantee | `ACCEPTED` |
| Atomicity | `ACCEPTED_WITH_MINOR_GAPS` |
| Lock / Concurrency | `ACCEPTED_WITH_MINOR_GAPS` |
| Duplicate / Idempotency | `ACCEPTED_WITH_MINOR_GAPS` |
| Existing Log Validation | `ACCEPTED_WITH_MINOR_GAPS` |
| Corruption Detection | `ACCEPTED_WITH_MINOR_GAPS` |
| Failure / Recovery | `ACCEPTED_WITH_MINOR_GAPS` |
| Test Coverage | `ACCEPTED_WITH_MINOR_GAPS` |
| Runtime Non-impact | `ACCEPTED` |
| Index Builder Readiness | `ACCEPTED_WITH_MINOR_GAPS` |

## Findings

No Critical findings.

No Major findings.

### AA-F1 Partial Line Risk Remains Under Crash / Disk Fault

- Severity: `MINOR`
- Affected contract: Event Log Atomicity
- Affected implementation: `append_line_atomic()`
- Evidence: event line can require multiple `os.write` calls; process kill or disk fault after a partial write can leave a partial trailing line.
- Risk: Event Log becomes append-blocked until reviewed.
- Registry impact: future append halts through partial-line detection.
- Runtime impact: none.
- Production impact: needs operational repair procedure before production event ingestion.
- Required action: document/implement crash recovery and consider stronger append framing or staging strategy.
- Blocking: non-blocking for current closure; required before Production.

### AA-F2 Existing Log Validation Is Structural, Not Full Contract Validation

- Severity: `MINOR`
- Affected contract: Event Log integrity / Index rebuild readiness
- Affected implementation: `read_event_log()`, `append_event()`
- Evidence: existing rows are parsed and scanned against the new event only; full schema/lifecycle validation of all existing rows is not performed.
- Risk: a pre-existing invalid event unrelated to the new event may remain undetected until Index Builder or audit.
- Registry impact: possible delayed detection.
- Runtime impact: none.
- Production impact: must be fixed before Index Builder relies on the log.
- Required action: add full-log validation or checkpoint/audit validator before index build.
- Blocking: required before Index Builder implementation.

### AA-F3 Fingerprint Scope Has Known Collision Classes By Contract

- Severity: `MINOR`
- Affected contract: Idempotency fingerprint
- Affected implementation: `event_fingerprint()`
- Evidence: `reason`, `source_refs`, and path migration fields are not fingerprint inputs.
- Risk: two semantically distinct path/reason/source-only events can collide.
- Registry impact: future path migration or correction events may need expanded fingerprint policy.
- Runtime impact: none.
- Production impact: relevant before migration events and broader event types.
- Required action: revisit fingerprint for `PATH_REGISTERED` / `PATH_MIGRATED` phase.
- Blocking: not blocking DRAFT/VALIDATED writer; blocking before Artifact Migration events.

## Fix Proposals

### FP-AA1 Full Log Validation Before Append / Index Build

- Target file: `src/ai_fund_lab_v2/artifact_registry/writer.py`
- Target functions: `read_event_log()`, `append_event()`
- Current: structural parse plus new-event duplicate scan.
- Problem: existing unrelated schema/lifecycle-invalid events are not rejected.
- Fix: add optional strict full-log validation using `validate_registry_event()` for every existing row and detect internal duplicate IDs/fingerprints.
- Contract basis: Event Log is audit Source of Truth.
- Required tests: existing duplicate ID, duplicate fingerprint, illegal lifecycle event, schema-invalid event.
- Regression risk: medium.
- Blocking status: before Index Builder implementation.

### FP-AA2 Crash / Partial Write Recovery Procedure

- Target file: `src/ai_fund_lab_v2/artifact_registry/writer.py` and operations docs.
- Target function: `append_line_atomic()`
- Current: detects partial lines later but does not repair.
- Problem: process kill or disk fault can leave a trailing partial line.
- Fix: define reviewed repair procedure and optionally introduce line hash/checkpoint framing before production ingestion.
- Contract basis: append-only Event Log safety and auditability.
- Required tests: simulated partial write, repair denied by default, repair workflow when later authorized.
- Regression risk: medium.
- Blocking status: before Production.

### FP-AA3 Expand Fingerprint Policy for Path/Migration Events

- Target file: `src/ai_fund_lab_v2/artifact_registry/writer.py`
- Target function: `event_fingerprint()`
- Current: Phase16-T fingerprint fields only.
- Problem: path/source/reason-only differences can collide.
- Fix: keep current fingerprint for DRAFT/VALIDATED model, but define event-type-specific fingerprint extensions before `PATH_REGISTERED` / `PATH_MIGRATED`.
- Contract basis: idempotency and migration audit.
- Required tests: legitimate path migration events with distinct old/new paths.
- Regression risk: low.
- Blocking status: before Artifact Migration events.

## Readiness

| Target | Readiness |
| --- | --- |
| Event Log Writer | `ACCEPTED` |
| Real DRAFT Event Append | `NOT_READY` |
| Real VALIDATED Event Append | `NOT_READY` |
| Materialized Index Builder Design | `READY` |
| Materialized Index Builder Implementation | `NOT_READY` |
| Checkpoint Writer | `NOT_READY` |
| Artifact Acceptance | `NOT_READY` |
| Runtime Integration | `NOT_READY` |

Rationale:

- Writer closure is accepted for architecture and isolated tests.
- Real event append should wait for explicit event authoring/import phase and additional operational tests around warning rejection, write failure, permission, and lock release.
- Index Builder design can proceed, but implementation should include or depend on full-log validation.
- Artifact Acceptance and Runtime Integration remain out of scope and not ready.

## Final Judgment

```text
PHASE16_AA_WRITER_ACCEPTED_WITH_MINOR_FIXES
```

Next prefix:

```text
Phase16-AB
```

Recommended next scope: Materialized Index Builder design, plus full-log validation requirements, without appending real events or integrating Runtime.
