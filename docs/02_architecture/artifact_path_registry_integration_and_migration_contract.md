# Artifact Path, Registry Integration, and Migration Contract

Status: Phase16-L accepted design

This document defines the permanent physical path policy, Registry integration approach, and migration sequence for AI Fund Lab v2 artifacts. It applies to Production, Demo, Paper, and Historical operation. It is not a historical-only, backtest-only, demo-only, or Phase16-only path design.

Operational lifecycle, reset exclusion, and environment transition rules are defined in:

```text
docs/02_architecture/operational_lifecycle_state_reset_and_environment_transition_contract.md
```

Path migration and Registry storage are Persistent Operational Foundation concerns. Trading State Reset must not delete Registry history, accepted artifact sets, migration manifests, legacy evidence, schemas, policies, or canonical artifacts.

## Purpose

Phase16-J and Phase16-K established:

- AI Input / Output Contract
- AI Artifact Registry Contract
- Model / Metrics Artifact Set
- PM Code Policy Registry
- Decision Artifact Hash Contract
- Capital Allocation Contract
- Silent fallback prohibition

Phase16-L defines how those contracts can be introduced into the existing system without changing Runtime behavior first.

Top-level system priority remains:

```text
safety
↓
correctness
↓
continuous operation
↓
auditability
↓
explainability
↓
return
```

Therefore migration must freeze identity, hash, schema, and accepted status before any physical path move or Runtime consumer cutover.

## Physical Path Policy

Recommended permanent structure:

```text
.runtime/
  artifact_registry/
  artifacts/
    data/
    features/
    ai/
    decisions/
    control/
    manifests/
  runtime_state/
  operations/
```

Rules:

- `.runtime/artifact_registry` is the Registry storage area.
- `.runtime/artifacts` is permanent registered artifact storage.
- `.runtime/runtime_state` remains Runtime state/evidence storage and is not the Registry authority.
- `.runtime/operations` may remain current operational ingestion/feature working storage during migration.
- `reports/` remains report/audit output, not Runtime input authority.
- Phase numbers and modes are prohibited as permanent identity path segments.

Path names may include:

- responsibility
- artifact type
- component
- version or artifact ID
- business date / feature date when applicable
- content hash prefix when useful

Path names must not use as permanent identity:

- `phase16`
- `phase5p`
- `historical`
- `backtest`
- `demo_model`
- `paper_feature`

Mode belongs in artifact metadata and run manifests, not in permanent artifact identity.

## Logical / Physical Identity

The Registry separates permanent meaning from storage location.

| Field | Meaning |
|---|---|
| `logical_artifact_id` | Permanent role, such as `ai.candidate.model.accepted`. |
| `artifact_instance_id` | Immutable version/hash-specific instance. |
| `physical_path` | Storage path for the current instance. |
| `current_path` | Path used by current code before cutover. |
| `target_path` | Future permanent path after migration. |
| `legacy_path` | Old read-only evidence path after cutover. |

Example:

```text
logical_artifact_id: ai.candidate.model.accepted
artifact_instance_id: ai.candidate.model.accepted@phase4bf_formal_candidate_model@sha256-2ea75d14
current_path: .runtime/candidate_ai/models/phase4bf_formal_candidate_model.pkl
target_path: .runtime/artifacts/ai/candidate/model/phase4bf_formal_candidate_model/sha256-2ea75d14/model.pkl
legacy_path: .runtime/candidate_ai/models/phase4bf_formal_candidate_model.pkl
```

The target path may carry a historical version string from the model metadata, but the logical identity must not be the Phase-numbered path.

## Path Option Comparison

| Option | Summary | Runtime change | Consumer change | Migration risk | Rollback | Auditability | Production suitability | Path clarity | Backward compatibility | Phase path removal | Operational complexity |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A | Centralize under `.runtime/artifacts` plus `.runtime/artifact_registry` | Medium | Medium | Medium | High with copy-first | High | High | High | Medium | High | Medium |
| B | Split by existing responsibilities: `.runtime/data`, `.runtime/ai`, `.runtime/runtime_state` | Medium-Low | Medium | Medium | Medium | Medium | Medium-High | Medium | Medium-High | Medium | Medium |
| C | Keep existing paths and add Registry only | Low | Low | Low initially | High | Medium | Medium-Low | Low | High | Low | Low initially, high later |

Recommendation:

```text
Option A, phased.
```

Phase16-L does not move files. Stage 1 registers current paths. Later stages copy accepted artifacts into `.runtime/artifacts`, verify hashes/schemas, then cut consumers over after regression gates pass. This balances auditability and production suitability without forcing immediate Runtime change.

## Permanent Path Layout

### Data

```text
.runtime/artifacts/data/raw/jquants/equities_bars_daily/<artifact_instance_id>/
.runtime/artifacts/data/canonical/market_data/jquants/equities_bars_daily/daily/<artifact_instance_id>/data.parquet
.runtime/artifacts/data/calendar/jquants/<artifact_instance_id>/trading_calendar.parquet
.runtime/artifacts/data/listed_issues/jquants/<artifact_instance_id>/listed_issues.parquet
.runtime/artifacts/data/corporate_actions/jquants/<artifact_instance_id>/corporate_actions.parquet
```

### Feature

```text
.runtime/artifacts/features/candidate/<feature_date>/<artifact_instance_id>/candidate_features.parquet
.runtime/artifacts/features/opportunity/<feature_date>/<artifact_instance_id>/opportunity_feature_input.parquet
.runtime/artifacts/features/position/<feature_date>/<artifact_instance_id>/position_feature_input.parquet
.runtime/artifacts/features/capital_allocation/<feature_date>/<artifact_instance_id>/capital_policy_input.parquet
```

### AI Model / Policy

```text
.runtime/artifacts/ai/candidate/model/<model_version>/<hash_id>/model.pkl
.runtime/artifacts/ai/candidate/model/<model_version>/<hash_id>/manifest.json
.runtime/artifacts/ai/candidate/schema/<schema_id>/<hash_id>/feature_schema.json

.runtime/artifacts/ai/opportunity/model/<model_version>/<hash_id>/model.pkl
.runtime/artifacts/ai/opportunity/metrics/<metrics_version>/<hash_id>/metrics.json
.runtime/artifacts/ai/opportunity/artifact_set/<artifact_set_id>/artifact_set_manifest.json

.runtime/artifacts/ai/position_management/code_policy/<policy_version>/<hash_id>/code_policy_manifest.json
.runtime/artifacts/ai/position_management/runtime_adapter/<adapter_version>/<hash_id>/adapter_manifest.json

.runtime/artifacts/control/capital_allocation/policy/<policy_version>/<hash_id>/policy.json
```

PM code and adapter artifacts may point to source tree file hashes rather than copied source files in the first implementation. If source snapshots are later needed, they must be immutable snapshots with hashes.

### Decision

```text
.runtime/artifacts/decisions/candidate/<business_date>/<artifact_instance_id>/candidate_decisions.json
.runtime/artifacts/decisions/opportunity/<business_date>/<artifact_instance_id>/opportunity_rankings.json
.runtime/artifacts/decisions/position_management/<business_date>/<artifact_instance_id>/position_management_decisions.json
.runtime/artifacts/decisions/capital_allocation/<business_date>/<artifact_instance_id>/capital_allocation_decisions.json
```

During migration, current Runtime decision paths under `.runtime/runtime_state` remain the write authority until a later cutover explicitly changes them.

### Registry / Manifest

```text
.runtime/artifact_registry/events/registry_events.jsonl
.runtime/artifact_registry/index/registry_index.json
.runtime/artifact_registry/index/registry_index.sha256
.runtime/artifact_registry/schema/artifact_registry_event.schema.json
.runtime/artifact_registry/schema/artifact_registry_index.schema.json
.runtime/artifact_registry/locks/registry.lock
.runtime/artifact_registry/checkpoints/<checkpoint_id>/checkpoint.json
.runtime/artifact_registry/backups/<backup_id>/
.runtime/artifact_registry/migrations/<migration_id>/migration_manifest.json
.runtime/artifact_registry/audit/<business_date>/registry_audit.json
reports/artifact_registry/<business_date>/registry_audit.md
```

The Registry is operational infrastructure under `.runtime`, but it is separated from Runtime State Authority.

## Registry Storage Layout

Phase16-K recommended:

```text
append-only JSONL registry event log
↓
materialized central index
↓
optional SQLite query index
```

Phase16 initial Registry implementation requires only:

- append-only JSONL registry event log
- materialized JSON central index

SQLite status:

```text
OPTIONAL_LATER
```

SQLite is a later candidate for Production query performance or operational usability. It is not required for the Phase16 initial Registry implementation, and the initial scope must not be overimplemented as JSONL plus JSON index plus SQLite.

Physical layout:

| Item | Path |
|---|---|
| Event log | `.runtime/artifact_registry/events/registry_events.jsonl` |
| Materialized index | `.runtime/artifact_registry/index/registry_index.json` |
| Index hash | `.runtime/artifact_registry/index/registry_index.sha256` |
| Event schema | `.runtime/artifact_registry/schema/artifact_registry_event.schema.json` |
| Index schema | `.runtime/artifact_registry/schema/artifact_registry_index.schema.json` |
| Lock | `.runtime/artifact_registry/locks/registry.lock` |
| Checkpoint | `.runtime/artifact_registry/checkpoints/<checkpoint_id>/checkpoint.json` |
| Backup | `.runtime/artifact_registry/backups/<backup_id>/` |
| Migration manifest | `.runtime/artifact_registry/migrations/<migration_id>/migration_manifest.json` |
| JSON audit | `.runtime/artifact_registry/audit/<business_date>/registry_audit.json` |
| Markdown audit | `reports/artifact_registry/<business_date>/registry_audit.md` |

Registry events are append-only. Rollback is represented by `REVOKED`, `LEGACY`, or superseding events, not event deletion.

## Accepted Artifact Set Layout

### Candidate Accepted Artifact Set

```text
.runtime/artifacts/ai/candidate/artifact_set/<set_id>/artifact_set_manifest.json
```

Set manifest must include:

- model artifact id/path/hash
- model manifest artifact id/path/hash
- feature schema artifact id/path/hash
- training metadata artifact id/path/hash
- validation evidence id/path/hash
- accepted status
- allowed consumer

### Opportunity Accepted Artifact Set

```text
.runtime/artifacts/ai/opportunity/artifact_set/<set_id>/artifact_set_manifest.json
```

Set manifest must include:

- model artifact id/path/hash
- metrics artifact id/path/hash
- feature schema artifact id/path/hash
- training metadata artifact id/path/hash
- validation evidence id/path/hash
- accepted status
- allowed consumer

Runtime use is prohibited if the model and metrics do not belong to the same accepted set.

### PM Accepted Artifact Set

```text
.runtime/artifacts/ai/position_management/artifact_set/<set_id>/artifact_set_manifest.json
```

Set manifest must include:

- code-policy identity
- code hash
- runtime adapter identity
- adapter hash
- policy version
- feature version
- inference version
- accepted status
- allowed consumer

### Capital Allocation Accepted Artifact Set

```text
.runtime/artifacts/control/capital_allocation/artifact_set/<set_id>/artifact_set_manifest.json
```

Set manifest must include:

- policy artifact id/path/hash
- schema id/path/hash
- version
- validation evidence id/path/hash
- accepted status
- allowed consumer

Capital Allocation artifactization is staged:

1. Register Capital Allocation Policy Artifact and freeze policy version/hash/schema/accepted status.
2. Record current `CapitalAllocationSignal` as evidence with input refs, hashes, policy refs, and Current hash.
3. Read-only compare current Planning/Pending output against standalone Capital Allocation Decision Artifact candidate.
4. Consider standalone artifact adoption only through separate Acceptance after Semantic Equality Gate passes.

The staged comparison must include symbol, allocated capital, target quantity, cash reserve, position limit, rejection reason, Planning output, and Pending output. The standalone artifact must not immediately replace Planning, expand Capital Allocation authority, create dual authority, or silently fallback to/from the current signal.

## Current Path Classification

| Current path | Classification | Reason / evidence |
|---|---:|---|
| `.runtime/candidate_ai/models/phase4bf_formal_candidate_model.pkl` | `TEMPORARY_REGISTERED_PATH` + `MIGRATION_REQUIRED` | Runtime default in `runtime_v2/buy_ai/producer.py`; file exists; Phase16-F hash confirmed; path includes Phase-numbered artifact name. |
| `.runtime/candidate_ai/models/phase4bf_formal_candidate_model_manifest.json` | `TEMPORARY_REGISTERED_PATH` + `MIGRATION_REQUIRED` | File exists and belongs to Candidate model identity; Phase-numbered name requires migration. |
| `reports/opportunity_ai/phase5p/models/opportunity_model.pkl` | `TEMPORARY_REGISTERED_PATH` + `MIGRATION_REQUIRED` | Runtime default in `runtime_v2/buy_ai/producer.py`; file exists; path under reports and Phase-numbered. |
| `reports/opportunity_ai/phase5p/training/opportunity_training_metrics.json` | `TEMPORARY_REGISTERED_PATH` + `MIGRATION_REQUIRED` | Preferred metrics from Phase16-F; file exists; should be part of accepted Opportunity set; path under reports and Phase-numbered. |
| `reports/opportunity_ai/phase5e/opportunity_training_metrics.json` | `LEGACY_ONLY` / `TRAINING_ONLY` | Existing fallback in producer when metrics arg omitted; file exists; not same accepted set as Phase5-P model. |
| `.runtime/operations/feature_artifacts/<date>/` | `ACCEPTED_CURRENT_PATH` + `MIGRATION_REQUIRED` | Runtime CLI default `--feature-root`; observed dates/files exist; operational path is current Runtime input but not permanent registered artifact storage. |
| `.runtime/runtime_state/buy_ai/<date>/` | `ACCEPTED_CURRENT_PATH` + `MIGRATION_REQUIRED` | Runtime buy-AI producer writes decision artifacts here; current path is Runtime state/evidence, not permanent artifact store. |
| `.runtime/runtime_state/position_management/<date>/` | `ACCEPTED_CURRENT_PATH` + `MIGRATION_REQUIRED` | PM producer writes decisions/actions/audits here; observed current files exist. |
| `.runtime/phase9/canonical_data/` | `TEMPORARY_REGISTERED_PATH` + `MIGRATION_REQUIRED` | Phase16-G confirms normalized OHLCV canonical content and config; path is Phase-numbered and should migrate. |
| `.runtime/data/raw/jquants/equities_bars_daily/responses/` | `TEMPORARY_REGISTERED_PATH` | Phase16-G confirms raw historical responses; path is not Phase-numbered but needs Registry registration and hash inventory. |
| `.runtime/data/raw/jquants/listed_issues/data.parquet` | `TEMPORARY_REGISTERED_PATH` + `DESIGN_REVIEW_REQUIRED` | Configured canonical candidate; Phase16-G says historical range insufficient. |
| `.runtime/data/raw/jquants/trading_calendar/data.parquet` | `TEMPORARY_REGISTERED_PATH` + `DESIGN_REVIEW_REQUIRED` | Configured canonical candidate; Phase16-G says historical range insufficient. |
| `.runtime/operations/jquants/*` | `ACCEPTED_CURRENT_PATH` for operational Runtime, `MIGRATION_REQUIRED` for historical foundation | Runtime market refresh produces and consumes operational data; not full historical canonical source. |

## Migration Stages

### Stage 0: Inventory Freeze

Record current path, size, content hash, schema hash, producer, consumer, accepted status candidate, and current owner. No file move.

### Stage 1: Logical Registration

Register existing physical paths under permanent logical identities. Current consumers still use current paths. Accepted status may remain `VALIDATED` until human/acceptance review.

### Stage 2: Artifact Set Acceptance

Accept Candidate, Opportunity, PM, and Capital Allocation artifact sets. Opportunity model and metrics must be accepted together.

### Stage 3: Consumer Compatibility Validation

Verify current consumers can read registered artifacts by explicit path and produce identical semantic results. Registry validates but does not resolve active path yet.

### Stage 4: New Path Preparation

Prepare target path plan and migration manifest. This stage may create paths only in a later implementation phase.

### Stage 5: Copy and Verify

Copy, do not move. Verify hash, schema, size, row count, file count, manifest, and source refs.

### Stage 6: Read Cutover

Cut consumers over to Registry-validated logical IDs or target paths. No silent fallback. Old path is not fallback authority.

### Stage 7: Regression

Run semantic output equivalence gates for AI decisions, allocation, planning, pending, submit guard, and Runtime authority invariants.

### Stage 8: Legacy Freeze

Mark old paths as `LEGACY_READ_ONLY` or `EVIDENCE_ONLY`. Keep files read-only for audit.

### Stage 9: Cleanup Decision

Deletion requires a separate acceptance phase. Phase16-L does not approve deletion.

## Copy / Verify Policy

Initial migration uses:

```text
Copy
↓
Verify
↓
Cutover
↓
Legacy Freeze
```

Required controls:

| Item | Policy |
|---|---|
| Copy method | Deterministic file copy preserving bytes; directory copies record file inventory. |
| Atomicity | Copy into staging path, verify, then register final target path. |
| Hash verification | SHA-256 for every file and aggregate directory inventory hash. |
| File count verification | Required for directories. |
| Schema verification | Required for parquet/json/csv artifacts before acceptance. |
| Manifest verification | Source refs, source hashes, producer, consumer, and status must match. |
| Rollback point | Before read cutover and before accepted status promotion. |

## Consumer Cutover

| Consumer | Current source | Target source | Cutover method | Fallback policy | Compatibility test | Rollback |
|---|---|---|---|---|---|---|
| Candidate Model Loader | `--candidate-model-path` or default `.runtime/candidate_ai/models/...pkl` | logical ID `ai.candidate.model.accepted` resolved to `.runtime/artifacts/ai/candidate/...` | Add Registry validation first; later resolve explicit logical ID | No fallback search | Candidate Decision semantic equality | Restore old explicit path; revoke new target |
| Opportunity Model Loader | `--opportunity-model-path` or default `reports/opportunity_ai/phase5p/...` | accepted Opportunity Artifact Set | Set-based lookup after validation | No fallback search | Opportunity Decision semantic equality | Restore old explicit model+metrics paths |
| Opportunity Metrics Loader | CLI metrics path or Phase5-E fallback | metrics in accepted Opportunity Artifact Set | Remove fallback in later implementation; require set | No fallback | Model/metrics set hash match | Revoke set; require explicit old metrics path until fixed |
| PM Producer | source code + adapter code, explicit PM feature/opportunity paths | accepted PM Code Policy Set plus registered inputs | Validate code/adapter hashes before inference | No fallback | PM Decision semantic equality | Revoke PM set; old producer path remains |
| Feature Producer | operational normalized/listed paths; output `.runtime/operations/feature_artifacts` | registered canonical data inputs; target `.runtime/artifacts/features/...` | Validate source refs first; later output target artifacts | No fallback | Feature schema and row semantic checks | Keep current feature root |
| AI Decision Producer | `.runtime/runtime_state/buy_ai/<date>` and PM runtime_state | target decisions under `.runtime/artifacts/decisions/...` | Start by registering current outputs; later write target only after acceptance | No dual-write authority | Decision hash/source refs present; semantic equality | Restore current runtime_state output |
| Capital Allocation / Planning | `CapitalAllocationSignal` and order plan embedded policy context | registered Capital Allocation Policy first; standalone Decision Artifact only after separate acceptance | Stage 1 validates policy hash; Stage 2 records current signal as evidence; Stage 3 read-only compares; Stage 4 adoption only after Semantic Equality Gate | No fallback and no dual authority | Allocation, Planning, and Pending equality | Restore explicit policy path and current Planning behavior |
| Runtime CLI | explicit path args and defaults | explicit logical IDs or config logical IDs resolved by Registry | Prefer config logical ID after validation | Existing path remains until cutover; no mixed authority | CLI manifest path evidence unchanged semantically | Revert CLI config/args |
| Audit / Report | manifests/current paths | Registry refs plus current manifests | Add audit refs after validation | Report is not Runtime input | Report includes source refs and no redaction regression | Report can omit Registry refs until fixed |

## Initial Implementation Scope After Phase16-N

After Phase16-N amendments, the first implementation scope is limited to read-only inventory and validation preparation:

- Read-only Artifact Inventory
- Logical Artifact ID preparation
- current path / hash / schema inventory
- Draft / Validated Registry event preparation
- Accepted Artifact Set manifest preparation
- read-only compatibility validation
- Registry audit report generation

Still prohibited in the first implementation scope:

- new physical path creation
- artifact copy / move
- consumer cutover
- CLI / config default changes
- Opportunity fallback correction
- standalone Capital Allocation Decision Artifact adoption
- Backup / Reset / Restore
- Historical Broker
- Point-in-time Guard
- Historical Simulation

## Registry Integration Options

| Option | Description | Runtime change | Authority clarity | Auditability | Rollback | Operator usability | Production safety | Backward compatibility |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | CLI passes explicit path; Registry pre-validates | Low | Medium | Medium | High | Medium | Medium | High |
| 2 | CLI passes logical artifact ID; Registry resolves path | Medium | High | High | High | Medium | High | Medium |
| 3 | Config stores logical artifact ID; startup resolves via Registry | Medium | High | High | Medium-High | High | High | Medium |

Recommendation:

```text
Stage 1: Option 1
Stage 2+: Option 3 for production operation
Option 2 for manual/operator overrides
```

Registry lookup must resolve and verify an explicitly requested logical ID. It must not auto-select a "best" artifact.

## Backward Compatibility

| Existing surface | Compatibility policy |
|---|---|
| CLI path arguments | Preserve during Stage 1-5. Add Registry validation before requiring logical IDs. |
| Existing default paths | Preserve until artifact set acceptance and regression pass. Defaults are not accepted authority once Registry cutover happens. |
| Existing config | `config/phase9_data_sources.yaml` remains evidence/current config, not permanent path authority after cutover. |
| Existing LaunchAgent | No change in Phase16-L; later cutover must verify launch command args/config. |
| Existing report/audit | Continue reading current manifests; add Registry refs only after compatibility. |
| Existing acceptance tests | Reuse for regression; add Registry-specific gates later. |

During transition, only one authority is active:

- Before cutover: current explicit path/default path is active, Registry validates.
- After cutover: Registry-resolved logical ID is active, old path is legacy evidence.

Dual authority is prohibited.

## Dual-Read / Dual-Write Policy

Prohibited:

- search multiple paths and use whichever exists
- write Decision Artifacts to both old and new paths as active authority
- fallback to old path when Registry validation fails
- use Registry and default path as competing authorities

Allowed only for migration validation:

- read-only comparison
- no decision authority
- no Submit authority
- audit diff only

Dual-read comparison output must be marked `EVIDENCE_ONLY`.

## Rollback

Rollback triggers:

- hash mismatch
- schema mismatch
- consumer failure
- regression failure
- Runtime output divergence
- Decision Artifact divergence
- Planning divergence
- Pending divergence
- Submit Guard divergence
- authority ambiguity
- incomplete accepted status

Rollback guarantees:

- old path returns as sole active authority
- Registry history is retained
- incomplete `ACCEPTED` status is revoked or superseded
- new target path is marked `REVOKED` or `LEGACY_READ_ONLY`
- no Runtime State mutation is required
- no Current/Ledger/Pending contract is changed

Stage rollback:

| Stage | Rollback action |
|---|---|
| 0 Inventory | Re-run inventory; no Runtime effect. |
| 1 Registration | Append revoke/supersede event; current paths remain active. |
| 2 Set Acceptance | Revoke artifact set; no consumer cutover. |
| 3 Compatibility | Stop; keep current consumers. |
| 4 Path Preparation | Delete or ignore unaccepted staging path only in later implementation; no Runtime effect. |
| 5 Copy/Verify | Mark copied target invalid; current path remains active. |
| 6 Read Cutover | Revert config/CLI logical ID to previous accepted path; mark new target revoked. |
| 7 Regression | Fail gate; rollback cutover. |
| 8 Legacy Freeze | Unfreeze old path only by review if it must become active again. |
| 9 Cleanup | No cleanup without separate acceptance. |

## Regression Gate

Required gates:

- Candidate Decision semantic equality
- Opportunity Decision semantic equality
- PM Decision semantic equality
- Capital Allocation result semantic equality
- Planning result semantic equality
- Pending result semantic equality
- Submit Guard result semantic equality
- Current / Ledger / Runtime State unchanged
- AI Feature Schema unchanged
- Model / Metrics Hash unchanged
- PM code / adapter hash unchanged
- Safety and Policy authority unchanged

Path migration must not alter semantic artifacts. Runtime timestamps, run IDs, or path-only metadata may differ if classified separately and excluded from semantic comparison.

## Design-Change Stop Rule

If any of the following are required, migration must stop:

- AI model change
- Feature schema change
- Feature calculation change
- Decision schema change
- Capital Allocation meaning change
- Runtime authority change
- State machine change
- Current / Ledger / Pending contract change
- normal mainline change
- Production default change

Classification:

- `DESIGN_CHANGE_REQUIRED`
- `SPEC_CHANGE_REQUIRED`
- `ARCHITECTURE_REVIEW_REQUIRED`

Do not continue automatically.

## Legacy Policy

Legacy classifications:

| Classification | Meaning |
|---|---|
| `LEGACY_READ_ONLY` | Retained after cutover; not Runtime input. |
| `EVIDENCE_ONLY` | Audit/report evidence only. |
| `TRAINING_ONLY` | Training lineage only; not Runtime input. |
| `REVOKED` | Known unsafe or superseded; retained but unusable. |
| `DELETION_CANDIDATE` | May be considered for deletion only after separate acceptance. |

Phase16-L does not approve deletion.

## Current Implementation Gaps

| Gap | Judgment |
|---|---:|
| Permanent Artifact Path not implemented | `DESIGN_ACCEPTED_IMPLEMENTATION_REQUIRED` |
| Registry storage not implemented | `DESIGN_ACCEPTED_IMPLEMENTATION_REQUIRED` |
| Artifact Set not registered | `DESIGN_ACCEPTED_IMPLEMENTATION_REQUIRED` |
| Opportunity fallback | `MIGRATION_REQUIRED` |
| PM hash refs missing from outputs | `DESIGN_ACCEPTED_IMPLEMENTATION_REQUIRED` |
| Decision Artifact hash contract not enforced | `DESIGN_ACCEPTED_IMPLEMENTATION_REQUIRED` |
| Capital Allocation Decision Artifact missing | `DESIGN_ACCEPTED_IMPLEMENTATION_REQUIRED` |
| Phase-numbered paths | `MIGRATION_REQUIRED` |
| Consumer cutover method | `DESIGN_ACCEPTED_IMPLEMENTATION_REQUIRED` |
| Rollback implementation | `DESIGN_ACCEPTED_IMPLEMENTATION_REQUIRED` |
| Regression gates | `DESIGN_ACCEPTED_IMPLEMENTATION_REQUIRED` |

## Acceptance Criteria

This design is accepted when:

- permanent Physical Path policy is defined
- Logical Identity and Physical Path are separated
- Registry storage layout is defined
- Accepted Artifact Set layout is defined
- current paths are classified
- migration stages are defined
- Copy / Verify policy is defined
- Consumer Cutover sequence is defined
- Registry Integration options are compared
- Backward Compatibility is defined
- Dual-read / Dual-write policy is defined
- Rollback conditions are defined
- Regression Gate is defined
- Legacy Policy is defined
- Design-change Stop Rule is defined
- Production / Demo / Paper / Historical share the same design
