# Phase16-AE Materialized Registry Index Builder Architecture and Implementation Closure Review

## Executive Summary

Final judgment:

```text
PHASE16_AE_INDEX_BUILDER_ACCEPTED_WITH_MINOR_FIXES
```

Materialized Index Builder readiness:

```text
ACCEPTED_WITH_MINOR_FIXES
```

Phase16-AD correctly implements the Materialized Registry Index as a derived view from the Registry Event Log. The reviewed implementation uses the Event Log as the only lifecycle authority, gates build through `FullEventLogValidator`, replays physical-line-order events, writes only the formal Index path, supports empty registry and `NO_CHANGE`, and keeps Runtime / Current / Ledger / Pending / AI / Feature out of scope.

No code, schema, tests, Event Log, Checkpoint, Runtime, or artifact status changes were made during this Phase16-AE review. The review found no Critical or Major findings. Minor findings should be closed before Checkpoint Writer production hardening or before real accepted-artifact workflows.

## Review Scope

Reviewed:

- Project and Phase16 operational data purpose.
- Materialized Registry Index / Event Replay contract.
- Phase16-AD implementation and tests.
- Formal Event Log and Index state.
- Runtime import graph for Index Builder usage.
- Current build result and formal Index hash consistency.

Executed:

```text
python3 -m pytest -q tests/artifact_registry/test_inventory_helpers.py tests/artifact_registry/test_phase16u_schema_amendments.py tests/artifact_registry/test_phase16v_read_only_validator.py tests/artifact_registry/test_phase16x_validator_hardening.py tests/artifact_registry/test_phase16z_registry_event_writer.py tests/artifact_registry/test_phase16ac_full_event_log_validator.py tests/artifact_registry/test_phase16ad_materialized_index_builder.py
```

Result:

```text
88 passed
```

Formal Registry state:

```text
Event Log: .runtime/artifact_registry/events/registry_events.jsonl
Event count: 0
Event Log hash: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
Index: .runtime/artifact_registry/index/registry_index.json
Index hash: 371967323e58e154ce0455eb465112f8b701540e5edd09fd68e8bb65712d2c8f
Checkpoint files: none
```

## Project Purpose Alignment

Judgment: `ACCEPTED`

The implementation supports the top-level goal of a safe, correct, continuously operable automated trading system. It improves auditability and explainability by materializing a deterministic view over Registry Event Log authority without changing trading behavior.

## Phase16 Scope Alignment

Judgment: `ACCEPTED`

The Index is not Historical-only, Backtest-only, or Phase16-only. It uses the permanent `.runtime/artifact_registry/index/registry_index.json` path and `artifact_registry_index.v1` schema. No Runtime Mainline, mode-specific schema, artifact auto-promotion, or hidden consumer cutover was introduced.

## Index Authority Boundary

Judgment: `ACCEPTED`

Evidence:

- The builder validates through `FullEventLogValidator` before replay: [index_builder.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/artifact_registry/index_builder.py:73).
- Projection derives entries from validator-returned events: [index_builder.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/artifact_registry/index_builder.py:96).
- It writes only the Index path and report output.
- Runtime imports of `index_builder` were found only in script/test/docs, not Runtime v2 code.

No Event Log write, artifact status mutation, `ACCEPTED` promotion, model selection, artifact replacement, Current/Ledger/Pending mutation, Planning, or Submit control was observed.

## FullEventLogValidator Gate

Judgment: `ACCEPTED_WITH_MINOR_GAPS`

Evidence:

- The build path calls `FullEventLogValidator.validate(include_events=True)` inside the build flow: [index_builder.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/artifact_registry/index_builder.py:80).
- Build proceeds only when `overall_result=PASS` and `failure_class=NONE`: [index_builder.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/artifact_registry/index_builder.py:81).
- No `validate=false`, direct event input API, or production test shortcut was found.

Minor gap: the current Full Log Validator forces `overall_result=PASS` whenever `failure_class=NONE`, even when warning checks are present: [full_log_validator.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/artifact_registry/full_log_validator.py:325). This means the builder cannot currently demonstrate rejection of `PASS_WITH_WARNINGS`.

## Lock / Snapshot Consistency

Judgment: `ACCEPTED`

Evidence:

- The builder uses the Writer lock file via `LOCK_RELATIVE_PATH`: [index_builder.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/artifact_registry/index_builder.py:25).
- The exclusive lock covers validation, replay, projection, hash calculation, existing Index comparison, and atomic replacement: [index_builder.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/artifact_registry/index_builder.py:73).
- Lock contention is tested and blocks build without Index creation: [test_phase16ad_materialized_index_builder.py](/Users/negishi/work/ai-fund-lab-v2/tests/artifact_registry/test_phase16ad_materialized_index_builder.py:232).

## Replay Ordering

Judgment: `ACCEPTED`

The builder iterates the validator-returned events in list order and does not sort by timestamp, event ID, logical artifact ID, or artifact instance ID: [index_builder.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/artifact_registry/index_builder.py:125). Timestamp reverse-order behavior is tested: [test_phase16ad_materialized_index_builder.py](/Users/negishi/work/ai-fund-lab-v2/tests/artifact_registry/test_phase16ad_materialized_index_builder.py:139).

## Lifecycle Projection

Judgment: `ACCEPTED`

Projection handles `DRAFT`, `VALIDATED`, `REVIEW_REQUIRED`, `ACCEPTED`, `LEGACY`, `REVOKED`, and `REJECTED` through Event Log state and FullEventLogValidator preconditions. The builder does not infer missing transitions; invalid ordering is blocked before write.

## State Projection

Judgment: `ACCEPTED_WITH_MINOR_GAPS`

Entries contain the required `artifact_registry_entry.v1` fields:

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

Projection chooses the active accepted instance when present, otherwise the last replayed instance for the logical artifact: [index_builder.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/artifact_registry/index_builder.py:211).

Minor gap: schema-level invariants such as `entries` key matching `entry.logical_artifact_id` and `entry_count == len(entries)` are not expressible in the current schema and are not explicitly checked in `_validate_index()`.

## Active Instance Uniqueness

Judgment: `ACCEPTED_WITH_MINOR_GAPS`

The Full Log Validator enforces multiple active eligible instance checks, and the builder defensively raises on multiple active instances during `ARTIFACT_ACCEPTED` projection: [index_builder.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/artifact_registry/index_builder.py:189).

Minor gap: AD tests cover active uniqueness in AC but do not include a builder-level accepted-artifact fixture for multiple active projection.

## History Retention

Judgment: `ACCEPTED_WITH_MINOR_GAPS`

The builder keeps deterministic `legacy_instances` and `revoked_instances` with duplicate prevention: [index_builder.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/artifact_registry/index_builder.py:358). It does not copy all events into the Index.

`replacement_lineage` and `rollback_lineage` are replayed internally but not emitted in `artifact_registry_entry.v1`.

Classification:

```text
KNOWN_LIMITATION
```

Impact is non-blocking for empty registry and Checkpoint design, but should be revisited before Artifact Acceptance workflows depend on replacement or rollback lineage from the Index.

## PATH Projection

Judgment: `ACCEPTED`

`PATH_REGISTERED` updates `physical_path`; `PATH_MIGRATED` projects `new_physical_path`: [index_builder.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/artifact_registry/index_builder.py:164). FullEventLogValidator checks previous path consistency. The builder does not move files.

Event-type-aware fingerprint remains future work, but because the builder consumes only Validator-accepted Event Logs, this is not a direct Index Builder blocker.

## Index Schema Review

Judgment: `ACCEPTED_WITH_MINOR_GAPS`

Evidence:

- `artifact_registry_index.v1` exists and uses Draft 2020-12.
- Top-level `additionalProperties=false` is set: [artifact_registry_index.schema.json](/Users/negishi/work/ai-fund-lab-v2/docs/02_architecture/schemas/artifact_registry_index.schema.json:6).
- Required top-level fields are present: [artifact_registry_index.schema.json](/Users/negishi/work/ai-fund-lab-v2/docs/02_architecture/schemas/artifact_registry_index.schema.json:7).
- Entries are object values compatible with `artifact_registry_entry.v1`: [artifact_registry_index.schema.json](/Users/negishi/work/ai-fund-lab-v2/docs/02_architecture/schemas/artifact_registry_index.schema.json:28).

Minor gap: schema does not enforce entry key/value consistency, `entry_count == len(entries)`, or `index_hash` self-consistency. Implementation computes correct formal Index values, but validation hardening remains useful.

## Event Log Hash Review

Judgment: `ACCEPTED`

The builder uses `validation["event_log_hash"]` from FullEventLogValidator: [index_builder.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/artifact_registry/index_builder.py:240). Formal Index `event_log_hash` matches SHA-256 of Event Log bytes.

## Index Hash Review

Judgment: `ACCEPTED_WITH_MINOR_GAPS`

The hash excludes `index_hash` and `generated_at`, uses sorted compact canonical JSON through `stable_json_hash`, and is deterministic for the same payload: [index_builder.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/artifact_registry/index_builder.py:368).

`builder_version` and `event_log_path` are included in the hash. This is acceptable for the current local formal Index, but should be explicitly reviewed before cross-environment hash comparison is used as an environment-independent integrity claim.

## Empty Registry Review

Judgment: `ACCEPTED`

Formal Index:

```text
entries={}
event_count=0
entry_count=0
last_event_id=null
derived_from_event_log=true
```

No Runtime-use eligible artifact or accepted artifact exists. Empty registry is correctly treated as normal.

## NO_CHANGE Review

Judgment: `ACCEPTED`

`NO_CHANGE` compares:

```text
event_log_hash
event_count
last_event_id
entry_count
index_hash
```

Evidence: [index_builder.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/artifact_registry/index_builder.py:283). Formal rerun returned `NO_CHANGE` and `index_replaced=false`.

If an existing Index is semantically same but differently formatted, `NO_CHANGE` still works because comparison is by JSON fields, not file bytes.

## Atomic Write Review

Judgment: `ACCEPTED_WITH_MINOR_GAPS`

Implementation uses same-directory temp file, write, flush, fsync, temp schema validation, atomic replace, parent directory fsync, and temp cleanup: [index_builder.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/artifact_registry/index_builder.py:289).

Minor gap: tests record fsync and temp cleanup, but do not simulate fsync failure, parent fsync failure, `os.replace` failure, disk full, or permission denied.

## Existing Index Validation

Judgment: `ACCEPTED_WITH_MINOR_GAPS`

Existing Index validation checks JSON load, schema validation, and `index_hash` self-consistency: [index_builder.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/artifact_registry/index_builder.py:267). Invalid existing JSON is rebuilt from Event Log and tested: [test_phase16ad_materialized_index_builder.py](/Users/negishi/work/ai-fund-lab-v2/tests/artifact_registry/test_phase16ad_materialized_index_builder.py:222).

Minor gap: validation does not separately report stale or mismatched `event_log_hash`, `event_count`, `last_event_id`, or `entry_count`; those are handled by `NO_CHANGE` comparison and replacement behavior rather than an explicit existing-index validation finding.

## Failure / Recovery

Judgment: `ACCEPTED_WITH_MINOR_GAPS`

| Failure | Event Log changed | Existing Index | Build result | Operator action |
| --- | ---: | --- | --- | --- |
| Full Log validation failure | No | Preserved | `FAILED` | Fix Event Log/evidence by reviewed procedure. |
| Lock timeout | No | Preserved | exception | Retry after lock owner exits. |
| Replay/projection failure | No | Preserved if before replace | exception | Review event/implementation. |
| Schema failure before replace | No | Preserved | exception | Fix projection/schema. |
| Existing Index corruption | No | Replaced if Event Log valid | `PASS` with warning | Review warning and rebuilt Index. |
| Temp write/fsync failure | No | Expected preserved | exception | Inspect filesystem and retry. |
| Atomic replace failure | No | Expected preserved | exception | Inspect filesystem and retry. |
| Parent fsync failure | No | Replace may have occurred but durability uncertain | exception | Inspect Index and filesystem. |
| Permission denied / disk full | No | Expected preserved or uncertain partial temp only | exception | Fix environment and inspect temp. |

The builder does not repair Event Log corruption.

## Build Result Review

Judgment: `ACCEPTED`

Build result includes all required fields, including `build_status`, `overall_result`, `failure_class`, `previous_index_hash`, `index_replaced`, warnings, and errors. Formal latest result is `NO_CHANGE`, `PASS`, `failure_class=NONE`, `index_replaced=false`.

## Test Coverage

Judgment: `ACCEPTED_WITH_MINOR_GAPS`

Covered:

- empty log;
- single `DRAFT`;
- `DRAFT -> VALIDATED`;
- multiple logical IDs;
- physical line order;
- timestamp ignored;
- revoked history;
- `PATH_REGISTERED`;
- `PATH_MIGRATED`;
- Full Log validation failure;
- duplicate Event Log;
- deterministic Index hash;
- generated_at excluded;
- `NO_CHANGE`;
- atomic write;
- invalid existing Index rebuild;
- lock contention;
- Event Log unchanged;
- report output.

Missing / future tests:

| Gap | Classification |
| --- | --- |
| parent fsync failure | `REQUIRED_BEFORE_PRODUCTION` |
| permission denied / disk full | `REQUIRED_BEFORE_PRODUCTION` |
| multiple active accepted instance projection in builder tests | `REQUIRED_BEFORE_ARTIFACT_ACCEPTANCE` |
| existing Index event_log_hash / event_count / last_event_id / entry_count mismatch classification | `REQUIRED_BEFORE_CHECKPOINT` |
| wrong entry logical ID | `REQUIRED_BEFORE_CHECKPOINT` |
| replacement lineage / rollback lineage emitted or schema decision | `REQUIRED_BEFORE_ARTIFACT_ACCEPTANCE` |
| concurrent Writer / Builder multi-process | `REQUIRED_BEFORE_PRODUCTION` |

## Runtime Non-impact

Judgment: `ACCEPTED`

Confirmed:

- Event Log lines remain `0`.
- Event Log hash remains `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- No checkpoint files exist.
- `index_builder` imports are limited to script, tests, docs, and its module.
- Runtime v2 does not import `ai_fund_lab_v2.artifact_registry.index_builder`.
- AD protected hash result is `UNCHANGED`.

## Checkpoint Readiness

Judgment: `READY_WITH_MINOR_GAPS`

Ready inputs:

- `event_log_hash`;
- `event_count`;
- `last_event_id`;
- `index_hash`;
- `entry_count`;
- schema versions;
- FullEventLogValidator result;
- atomic Index;
- exclusive lock.

Checkpoint Writer can remain limited to integrity evidence generation. Minor gaps should be closed or explicitly accepted before production checkpointing.

## Design Conformance Matrix

| Area | Judgment |
| --- | --- |
| Project Purpose Alignment | `ACCEPTED` |
| Phase16 Scope Alignment | `ACCEPTED` |
| Index Authority Boundary | `ACCEPTED` |
| Full Log Validator Gate | `ACCEPTED_WITH_MINOR_GAPS` |
| Lock / Snapshot Consistency | `ACCEPTED` |
| Replay Ordering | `ACCEPTED` |
| Lifecycle Projection | `ACCEPTED` |
| State Projection | `ACCEPTED_WITH_MINOR_GAPS` |
| Active Instance Uniqueness | `ACCEPTED_WITH_MINOR_GAPS` |
| History Retention | `ACCEPTED_WITH_MINOR_GAPS` |
| PATH Projection | `ACCEPTED` |
| Index Schema | `ACCEPTED_WITH_MINOR_GAPS` |
| Event Log Hash | `ACCEPTED` |
| Index Hash | `ACCEPTED_WITH_MINOR_GAPS` |
| Empty Registry | `ACCEPTED` |
| NO_CHANGE | `ACCEPTED` |
| Atomic Write | `ACCEPTED_WITH_MINOR_GAPS` |
| Existing Index Validation | `ACCEPTED_WITH_MINOR_GAPS` |
| Failure / Recovery | `ACCEPTED_WITH_MINOR_GAPS` |
| Test Coverage | `ACCEPTED_WITH_MINOR_GAPS` |
| Runtime Non-impact | `ACCEPTED` |
| Checkpoint Readiness | `ACCEPTED_WITH_MINOR_GAPS` |

## Findings

No Critical findings.

No Major findings.

### AE-F1 Full Log Validator Warnings Cannot Currently Produce PASS_WITH_WARNINGS

- Severity: `MINOR`
- Affected contract: FullEventLogValidator Gate
- Affected implementation: `FullEventLogValidator._result()`
- Evidence: [full_log_validator.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/artifact_registry/full_log_validator.py:325)
- Risk: Builder gate is coded to reject `PASS_WITH_WARNINGS`, but the validator currently normalizes warning-only results to `PASS`.
- Registry impact: non-blocking for current empty Registry; future warning semantics may be less visible.
- Runtime impact: none.
- Production impact: should be clarified before production event ingestion and checkpoint automation.
- Required action: either classify non-blocking fingerprint-scope as informational instead of warning, or allow `PASS_WITH_WARNINGS` and test builder rejection.
- Blocking: non-blocking for Index Builder closure; required before production hardening.

### AE-F2 Existing Index Validation Does Not Explicitly Classify Stale Field Mismatches

- Severity: `MINOR`
- Affected contract: Existing Index Validation
- Affected implementation: `_validate_existing_index()`
- Evidence: [index_builder.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/artifact_registry/index_builder.py:267)
- Risk: stale `event_log_hash`, `event_count`, `last_event_id`, or `entry_count` are safely handled by rebuild/NO_CHANGE comparison, but reported as comparison behavior rather than explicit existing-index validation status.
- Registry impact: derived Index remains safe; evidence is less precise.
- Runtime impact: none.
- Production impact: should be tightened before Checkpoint Writer relies on validation classification.
- Required action: add explicit existing-index checks against rebuilt Index metadata and report `REVIEW_REQUIRED` when stale.
- Blocking: non-blocking for current Index Builder; required before Checkpoint Writer production readiness.

### AE-F3 Index Schema / Validation Does Not Enforce Cross-field Invariants

- Severity: `MINOR`
- Affected contract: Index Schema and State Projection
- Affected implementation: `artifact_registry_index.schema.json`, `_validate_index()`
- Evidence: [artifact_registry_index.schema.json](/Users/negishi/work/ai-fund-lab-v2/docs/02_architecture/schemas/artifact_registry_index.schema.json:28), [index_builder.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/artifact_registry/index_builder.py:252)
- Risk: schema alone cannot catch `entry_count != len(entries)`, entry key/value logical ID mismatch, or Index self-hash mismatch unless implementation checks are added.
- Registry impact: builder-created formal Index is correct; invalid external Index detection can be more explicit.
- Runtime impact: none.
- Production impact: should be strengthened before Runtime lookup or checkpoint validation.
- Required action: add explicit semantic Index validation beyond JSON Schema.
- Blocking: non-blocking for current empty Index; required before Runtime integration.

### AE-F4 Failure Injection and Accepted-artifact Projection Tests Are Incomplete

- Severity: `MINOR`
- Affected contract: Test Coverage / Failure Recovery
- Affected implementation: `tests/artifact_registry/test_phase16ad_materialized_index_builder.py`
- Evidence: [test_phase16ad_materialized_index_builder.py](/Users/negishi/work/ai-fund-lab-v2/tests/artifact_registry/test_phase16ad_materialized_index_builder.py:247)
- Risk: parent fsync failure, permission denied, disk full, multi-process concurrency, stale Index field mismatch, and accepted-artifact active projection are not directly tested.
- Registry impact: current tested behavior is sufficient for empty Registry; future real events need stronger coverage.
- Runtime impact: none.
- Production impact: required before production event/index/checkpoint workflow.
- Required action: add targeted failure-injection and accepted-artifact fixture tests.
- Blocking: non-blocking for closure; blocking before production hardening and Artifact Acceptance workflows.

## Fix Proposals

| ID | Target | Proposal | Blocking status |
| --- | --- | --- | --- |
| FP-AE-1 | `full_log_validator.py::_result` | Preserve `PASS_WITH_WARNINGS` semantics or downgrade fingerprint-scope notice to informational evidence; add builder rejection test for warning-only validator result. | Required before production hardening. |
| FP-AE-2 | `index_builder.py::_validate_existing_index` | Compare existing Index metadata against rebuilt Event Log metadata and classify stale mismatch as `REVIEW_REQUIRED`. | Required before Checkpoint Writer production use. |
| FP-AE-3 | `index_builder.py::_validate_index` / `artifact_registry_index.schema.json` | Add semantic validation for `entry_count`, entry key/logical ID match, and self-hash. Keep schema unchanged if checker cannot express it. | Required before Runtime lookup. |
| FP-AE-4 | `tests/artifact_registry/test_phase16ad_materialized_index_builder.py` | Add failure injection, stale Index mismatch, multiple active accepted fixture, replacement/rollback lineage, and multi-process lock tests. | Required before production and Artifact Acceptance. |

## Implementation Readiness

| Area | Readiness |
| --- | --- |
| Materialized Index Builder | `ACCEPTED` |
| Real Event + Index Workflow | `NOT_READY` |
| Checkpoint Writer Design | `READY` |
| Checkpoint Writer Implementation | `READY_WITH_MINOR_GAPS` |
| Artifact Acceptance | `NOT_READY` |
| Runtime Lookup | `NOT_READY` |
| Runtime Integration | `NOT_READY` |

## Final Judgment

```text
PHASE16_AE_INDEX_BUILDER_ACCEPTED_WITH_MINOR_FIXES
```

The Index Builder is accepted as a derived Materialized Registry Index component. The next phase should not implement Runtime lookup or Artifact Acceptance yet. Checkpoint Writer design or implementation can proceed if the minor gaps are either fixed first or explicitly tracked as pre-production hardening items.

## Next Prefix

Recommended next Prefix:

```text
Phase16-AF
```

Recommended scope:

```text
Artifact Registry Checkpoint Writer design, or minor hardening of Index validation before Checkpoint Writer implementation.
```
