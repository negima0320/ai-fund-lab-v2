# Phase16-AF Materialized Index Validation Minor Hardening

## Final Judgment

```text
PHASE16_AF_INDEX_VALIDATION_HARDENING_ACCEPTED
```

Phase16-AF closed the four minor findings from Phase16-AE without changing Registry Event Log authority, artifact status, Runtime, Current, Ledger, Pending, AI, Feature, Consumer paths, or Checkpoint state.

## Created / Changed Files

- `src/ai_fund_lab_v2/artifact_registry/full_log_validator.py`
- `src/ai_fund_lab_v2/artifact_registry/index_builder.py`
- `tests/artifact_registry/test_phase16af_index_validation_hardening.py`
- `docs/phase_reports/phase16_af_materialized_index_validation_minor_hardening.md`
- `reports/phase_reports/phase16_af_materialized_index_validation_minor_hardening.json`

Updated validation/build evidence:

- `reports/phase16_registry_full_log_validation/`
- `reports/phase16_registry_index_build/`

## AE-F1 Closure

Result:

```text
CLOSED
```

`FullEventLogValidator` now preserves normal validation aggregation:

```text
warning-only -> PASS_WITH_WARNINGS / NONE
no warning -> PASS / NONE
```

The formal empty Event Log has no warning and remains:

```text
overall_result=PASS
failure_class=NONE
warnings=[]
```

The Index Builder still permits only:

```text
PASS / NONE
```

and rejects `PASS_WITH_WARNINGS`.

## AE-F2 Closure

Result:

```text
CLOSED
```

Existing Index classification was added:

```text
existing_index_status:
  NOT_FOUND
  VALID_CURRENT
  STALE
  CORRUPT
```

Stale metadata fields are explicitly detected:

```text
event_log_hash
event_count
last_event_id
entry_count
index_hash
```

Build Result now records:

```text
existing_index_status
stale_fields
previous_index_hash
index_replaced
rebuild_reason
```

Formal Index result:

```text
existing_index_status=VALID_CURRENT
stale_fields=[]
rebuild_reason=null
index_replaced=false
```

## AE-F3 Closure

Result:

```text
CLOSED
```

Semantic invariant validation was added beyond JSON Schema.

Top-level checks:

- `entry_count == len(entries)`
- `derived_from_event_log == true`
- empty Event Log requires `last_event_id == null`
- non-empty Event Log requires `last_event_id != null`
- `event_log_hash` format
- `index_hash` self-consistency

Entry checks:

- entry key equals `entry.logical_artifact_id`
- `runtime_use_eligible=true` requires `current_status=ACCEPTED`
- `LEGACY`, `REVOKED`, and `REJECTED` must not be eligible
- eligible entry requires `active_artifact_instance_id`
- `content_hash` and `schema_hash` are SHA-256 or null

Generated Index must pass schema validation, semantic validation, and self-hash validation before atomic replace.

## AE-F4 Closure

Result:

```text
CLOSED_WITH_REMAINING_PRODUCTION_GAPS
```

Added tests cover:

- warning-free validation returns `PASS`
- warning-only aggregation returns `PASS_WITH_WARNINGS`
- builder rejects `PASS_WITH_WARNINGS`
- stale existing Index fields classify as `STALE`
- index self-hash mismatch classifies as `CORRUPT`
- semantic invariant violations are rejected
- accepted artifact projection sets active instance, eligibility, accepted event, accepted time, and accepted authority
- `os.replace` failure preserves old Index
- file fsync failure preserves old Index
- parent directory fsync failure returns `REVIEW_REQUIRED` durability status after replace
- lock release after exception

Remaining production gaps:

- disk full simulation
- multi-process Writer / Builder concurrency
- broader permission-denied matrix

These remain `REQUIRED_BEFORE_PRODUCTION`, not blockers for Checkpoint Writer implementation.

Role-to-Artifact-Type Compatibility:

```text
NOT_IN_SCOPE
```

This remains an Artifact Acceptance precondition, not an Index validation hardening item.

## Warning Semantics

Formal Full Log Validation after hardening:

```text
overall_result=PASS
failure_class=NONE
warnings=[]
event_count=0
```

Warning-only unit behavior:

```text
PASS_WITH_WARNINGS / NONE
```

## Existing Index Classification

Formal Index classification:

```text
existing_index_status=VALID_CURRENT
stale_fields=[]
rebuild_reason=null
previous_index_hash=371967323e58e154ce0455eb465112f8b701540e5edd09fd68e8bb65712d2c8f
```

Stale test cases:

- `event_log_hash mismatch -> STALE`
- `event_count mismatch -> STALE`
- `last_event_id mismatch -> STALE`
- `entry_count mismatch -> STALE`

Corrupt test case:

- `index_hash self-consistency mismatch -> CORRUPT`

## Cross-field Invariant Validation

Semantic validator result for formal Index:

```text
semantic_validation_result=PASS
```

Invalid invariant tests now reject:

- `entry_count != len(entries)`
- entry key / logical ID mismatch
- empty event log with non-null `last_event_id`
- non-empty event log with null `last_event_id`
- `VALIDATED + runtime_use_eligible=true`
- `LEGACY + runtime_use_eligible=true`
- eligible entry with null active instance
- index self-hash mismatch

## Accepted Artifact Projection Test

Accepted artifact fixture is isolated under `tmp_path`; no formal Event Log event was added.

Tested flow:

```text
DRAFT -> VALIDATED -> ACCEPTED
```

Verified:

- `active_artifact_instance_id`
- `runtime_use_eligible=true`
- `accepted_event_id`
- `accepted_at`
- `accepted_by`
- `entry_count`
- deterministic `index_hash`

## Atomic Failure Tests

Tested:

- `os.replace` failure preserves old Index and cleans temp files
- file `fsync` failure preserves old Index and cleans temp files
- parent directory `fsync` failure reports:

```text
overall_result=REVIEW_REQUIRED
durability_status=REVIEW_REQUIRED
index_replaced=true
```

- lock is released after exception

## Test Result

Command:

```text
python3 -m pytest -q tests/artifact_registry/test_inventory_helpers.py tests/artifact_registry/test_phase16u_schema_amendments.py tests/artifact_registry/test_phase16v_read_only_validator.py tests/artifact_registry/test_phase16x_validator_hardening.py tests/artifact_registry/test_phase16z_registry_event_writer.py tests/artifact_registry/test_phase16ac_full_event_log_validator.py tests/artifact_registry/test_phase16ad_materialized_index_builder.py tests/artifact_registry/test_phase16af_index_validation_hardening.py
```

Result:

```text
106 passed
```

## Formal Registry Rerun

Full Log Validation:

```text
overall_result=PASS
failure_class=NONE
event_count=0
warnings=[]
```

Index Build:

```text
overall_result=PASS
failure_class=NONE
build_status=NO_CHANGE
existing_index_status=VALID_CURRENT
event_count=0
entry_count=0
index_replaced=false
semantic_validation_result=PASS
durability_status=NOT_APPLICABLE
```

Index hash:

```text
371967323e58e154ce0455eb465112f8b701540e5edd09fd68e8bb65712d2c8f
```

Event Log before / after:

```text
before=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
after=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
unchanged=true
```

Protected hash result:

```text
UNCHANGED
```

## Prohibited Actions

| Action | Result |
| --- | --- |
| Registry Event added | `NO` |
| Event Log changed | `NO` |
| Writer changed | `NO` |
| Writer auto-integration | `NO` |
| Checkpoint Writer implemented | `NO` |
| Checkpoint created | `NO` |
| Artifact Status changed | `NO` |
| ACCEPTED promotion | `NO` |
| Runtime Lookup / Integration | `NO` |
| Consumer changed | `NO` |
| Artifact path migration | `NO` |
| AI / Feature changed | `NO` |
| Reset / Simulation / Historical Test | `NO` |

## Remaining Gaps

| Gap | Classification |
| --- | --- |
| disk full simulation | `REQUIRED_BEFORE_PRODUCTION` |
| multi-process Writer / Builder concurrency | `REQUIRED_BEFORE_PRODUCTION` |
| broader permission-denied matrix | `REQUIRED_BEFORE_PRODUCTION` |
| Role-to-Artifact-Type Compatibility | `NOT_IN_SCOPE`, required before Artifact Acceptance |

## Readiness

| Area | Readiness |
| --- | --- |
| Materialized Index Validation | `HARDENED` |
| Checkpoint Writer | `READY` |
| Artifact Acceptance | `NOT_READY` |
| Runtime Lookup | `NOT_READY` |
| Runtime Integration | `NOT_READY` |

## Next Prefix

Recommended next Prefix:

```text
Phase16-AG
```

Recommended scope:

```text
Artifact Registry Checkpoint Writer design or implementation, using Event Log hash and Materialized Index hash as integrity evidence only.
```
