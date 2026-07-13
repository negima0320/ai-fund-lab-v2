# Phase16-AD Materialized Artifact Registry Index Builder Implementation

## Final Judgment

```text
PHASE16_AD_MATERIALIZED_REGISTRY_INDEX_BUILDER_ACCEPTED
```

Phase16-AD implemented the Materialized Artifact Registry Index Builder. The builder treats the append-only Registry Event Log as the only audit Source of Truth and creates the Materialized Index as a derived view.

Only the Materialized Index and report outputs were changed. No Registry Event, Event Log row, artifact body, Runtime state, Current, Ledger, Pending, Runtime State, AI model, Feature artifact, Policy, Planning, Submit, Consumer path, Checkpoint, Reset, Simulation, or Historical Test was changed.

## Created / Changed Files

- `docs/02_architecture/schemas/artifact_registry_index.schema.json`
- `src/ai_fund_lab_v2/artifact_registry/index_builder.py`
- `scripts/run_artifact_registry_index_build.py`
- `tests/artifact_registry/test_phase16ad_materialized_index_builder.py`
- `docs/phase_reports/phase16_ad_materialized_registry_index_builder_implementation.md`
- `reports/phase_reports/phase16_ad_materialized_registry_index_builder_implementation.json`

Formal Index created:

```text
.runtime/artifact_registry/index/registry_index.json
```

Build evidence:

```text
reports/phase16_registry_index_build/
```

## Index Schema Result

Created:

```text
docs/02_architecture/schemas/artifact_registry_index.schema.json
```

Schema:

```text
artifact_registry_index.v1
```

Fields:

```text
schema_version
generated_at
event_log_path
event_log_hash
event_count
last_event_id
entry_count
entries
index_hash
derived_from_event_log
builder_version
```

`entries` uses `logical_artifact_id -> artifact_registry_entry.v1-compatible object`. No `$ref` was used because the current project schema checker is minimal and does not require `$ref` support.

## Index Builder Result

Implemented:

- `MaterializedRegistryIndexBuilder`
- `run_index_build()`
- `index_hash()`
- read-only CLI runner
- build result writer
- atomic report output

Build status values:

```text
BUILT
NO_CHANGE
EMPTY_REGISTRY
FAILED
```

## FullEventLogValidator Gate

The builder always executes:

```text
FullEventLogValidator.validate(include_events=True)
```

Build is allowed only when:

```text
overall_result=PASS
failure_class=NONE
```

The builder reuses the validator output:

```text
events
event_count
last_event_id
event_log_hash
```

There is no separate build path that bypasses FullEventLogValidator.

## Replay Ordering

Replay order is:

```text
Event Log physical line order
```

The builder does not sort by `event_created_at`, `event_id`, or `logical_artifact_id`.

## Lifecycle Projection

Implemented projection for:

```text
DRAFT
VALIDATED
REVIEW_REQUIRED
ACCEPTED
LEGACY
REVOKED
REJECTED
```

The builder does not complete missing transitions, infer status, or ignore invalid events. Invalid replay is blocked by FullEventLogValidator Gate before Index write.

## State Projection

Projection is by `logical_artifact_id`, with instance state retained during replay. Each entry includes:

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

## Active Instance Uniqueness

The builder preserves the FullEventLogValidator uniqueness gate and also guards projection from multiple active eligible instances per `logical_artifact_id`.

Violation:

```text
HALT / Index write prohibited
```

## History Retention

Implemented summary retention:

```text
legacy_instances
revoked_instances
replacement_lineage during replay
rollback_lineage during replay
last_event_id
accepted_event_id
```

The final `artifact_registry_entry.v1` stores legacy and revoked summaries. Full history remains in Event Log.

## PATH Event Projection

Implemented:

- `PATH_REGISTERED`: updates `physical_path` without status or eligibility authority.
- `PATH_MIGRATED`: updates `physical_path` to `new_physical_path` after FullEventLogValidator confirms previous path consistency.

The builder does not perform artifact path migration. It only projects Event Log state.

## Event Log Hash

The builder uses the hash from FullEventLogValidator:

```text
event_log_hash = SHA-256(file bytes)
```

Formal Event Log hash:

```text
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
```

## Index Hash

Implemented deterministic hash:

```text
index_hash = SHA-256(canonical JSON excluding index_hash and generated_at)
```

Formal Index hash:

```text
371967323e58e154ce0455eb465112f8b701540e5edd09fd68e8bb65712d2c8f
```

`generated_at` differences do not change `index_hash`.

## Empty Registry Result

Initial formal build from the empty Event Log:

```text
build_status=EMPTY_REGISTRY
event_count=0
entry_count=0
last_event_id=null
```

Created Index:

```json
{
  "schema_version": "artifact_registry_index.v1",
  "event_count": 0,
  "last_event_id": null,
  "entry_count": 0,
  "entries": {},
  "derived_from_event_log": true
}
```

## NO_CHANGE Result

A subsequent build against the same Event Log returned:

```text
build_status=NO_CHANGE
index_replaced=false
```

`generated_at` alone does not cause a rewrite.

## Atomic Write Result

Index write uses:

```text
same-directory temp file
canonical JSON write
flush
fsync
schema validation from temp file
atomic replace
parent directory fsync
temp cleanup
```

Failed write preserves the existing Index.

## Lock Result

The builder uses the same exclusive Registry lock as the Writer:

```text
.runtime/artifact_registry/locks/registry.lock
```

The lock covers:

```text
Full Event Log Validation
Event Log Hash confirmation
Replay
Projection
Index Hash calculation
Existing Index comparison
Atomic Replace
```

Lock contention blocks build and preserves the existing Index.

## Existing Index Validation

Existing Index is checked before comparison:

- UTF-8 / JSON object readability through JSON load
- `artifact_registry_index.v1` schema
- `index_hash` self-consistency

If existing Index is invalid but Event Log is valid, the builder rebuilds from Event Log and atomically replaces the invalid derived view. Existing Index is never treated as authority.

## Test Result

Command:

```text
python3 -m pytest -q tests/artifact_registry/test_inventory_helpers.py tests/artifact_registry/test_phase16u_schema_amendments.py tests/artifact_registry/test_phase16v_read_only_validator.py tests/artifact_registry/test_phase16x_validator_hardening.py tests/artifact_registry/test_phase16z_registry_event_writer.py tests/artifact_registry/test_phase16ac_full_event_log_validator.py tests/artifact_registry/test_phase16ad_materialized_index_builder.py
```

Result:

```text
88 passed
```

Covered:

- empty log to `EMPTY_REGISTRY`
- single `DRAFT`
- `DRAFT -> VALIDATED`
- multiple logical IDs
- physical line order
- `event_created_at` ignored
- legacy / revoked history
- `PATH_REGISTERED`
- `PATH_MIGRATED`
- FullEventLogValidator failure blocks build
- duplicate Event Log blocks build
- deterministic Index hash
- `generated_at` excluded from hash
- `NO_CHANGE`
- atomic Index write
- invalid existing Index rebuild
- lock contention
- input Event Log unchanged
- report output generation

## Formal Index Build Result

Initial formal build:

```text
overall_result=PASS
failure_class=NONE
build_status=EMPTY_REGISTRY
event_count=0
entry_count=0
last_event_id=null
index_replaced=true
```

Runner re-execution:

```text
overall_result=PASS
failure_class=NONE
build_status=NO_CHANGE
event_count=0
entry_count=0
last_event_id=null
index_replaced=false
```

## Before / After

Event Log:

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
| Real Event append | `NOT_PERFORMED` |
| Event Log modification | `NOT_PERFORMED` |
| Artifact Status change | `NOT_PERFORMED` |
| ACCEPTED promotion | `NOT_PERFORMED` |
| Checkpoint Writer | `NOT_IMPLEMENTED` |
| Checkpoint artifact creation | `NOT_PERFORMED` |
| Writer integration | `NOT_IMPLEMENTED` |
| Runtime lookup / integration | `NOT_IMPLEMENTED` |
| Consumer switch | `NOT_PERFORMED` |
| Artifact path migration | `NOT_PERFORMED` |
| AI / Feature change | `NOT_PERFORMED` |
| Current / Ledger / Pending change | `NOT_PERFORMED` |
| Reset / Simulation / Historical Test | `NOT_PERFORMED` |

## Known Gaps

| Gap | Status |
| --- | --- |
| Checkpoint Writer | `NOT_IMPLEMENTED` |
| Writer automatic Index build integration | `NOT_IMPLEMENTED` |
| Runtime lookup from Index | `NOT_IMPLEMENTED` |
| Event-type aware fingerprint extension | still future work before production append of PATH / eligibility / checkpoint / acceptance events |
| Full replacement / rollback lineage exposure in final Entry schema | replayed internally; final `artifact_registry_entry.v1` only stores legacy/revoked summaries |

## Implementation Readiness

| Area | Readiness |
| --- | --- |
| Full Event Log Validator | `READY` |
| Materialized Index Builder | `READY` |
| Empty Registry operational build | `READY` |
| Checkpoint Writer | `NOT_STARTED` |
| Writer integration | `NOT_STARTED` |
| Runtime Lookup / Integration | `NOT_STARTED` |

## Next Prefix

Recommended next Prefix:

```text
Phase16-AE
```

Recommended scope:

```text
Materialized Index Builder architecture and implementation closure review, before Checkpoint Writer or Runtime integration.
```
