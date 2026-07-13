# Phase16-L Artifact Path, Registry Integration, and Migration Design

Prefix: Phase16-L

Work name: Artifact Physical Path, Registry Integration, and Migration Sequence Design

## Final Judgment

`PHASE16_L_ARTIFACT_PATH_REGISTRY_MIGRATION_DESIGN_ACCEPTED`

This phase defines permanent physical path policy, Registry integration, migration sequence, consumer cutover, rollback, regression gates, and legacy policy. No Registry implementation, path creation, artifact copy/move, consumer change, config change, CLI change, fallback fix, model change, metrics change, Runtime change, AI change, Feature change, Reset, Restore, Simulation, or Historical Test was performed.

## Created / Updated Files

- `docs/02_architecture/artifact_path_registry_integration_and_migration_contract.md`
- `docs/phase_reports/phase16_l_artifact_path_registry_integration_and_migration_design.md`
- `reports/phase_reports/phase16_l_artifact_path_registry_integration_and_migration_design.json`
- `docs/01_requirements/phase_roadmap.md`

## Recommended Physical Path Structure

```text
.runtime/artifact_registry/
.runtime/artifacts/data/
.runtime/artifacts/features/
.runtime/artifacts/ai/
.runtime/artifacts/decisions/
.runtime/artifacts/control/
.runtime/artifacts/manifests/
```

Recommended option: centralized `.runtime/artifacts` plus separated `.runtime/artifact_registry`, introduced in stages. Current paths are registered first; physical movement happens only after hash/schema/consumer compatibility and acceptance gates.

## Logical / Physical Identity Policy

Logical identity is permanent meaning and role. Physical path is storage location.

Required separation:

- `logical_artifact_id`
- `artifact_instance_id`
- `physical_path`
- `current_path`
- `target_path`
- `legacy_path`

Phase-numbered physical paths must not become logical identity.

## Registry Storage Layout

Phase16-N clarification: the initial Registry implementation scope is JSONL event log plus materialized JSON central index. SQLite is `OPTIONAL_LATER` and is not required before Registry inventory or validation can begin.

| Item | Path |
|---|---|
| Event log | `.runtime/artifact_registry/events/registry_events.jsonl` |
| Materialized index | `.runtime/artifact_registry/index/registry_index.json` |
| Schema | `.runtime/artifact_registry/schema/*.schema.json` |
| Lock | `.runtime/artifact_registry/locks/registry.lock` |
| Checkpoint | `.runtime/artifact_registry/checkpoints/<checkpoint_id>/checkpoint.json` |
| Backup | `.runtime/artifact_registry/backups/<backup_id>/` |
| Migration manifest | `.runtime/artifact_registry/migrations/<migration_id>/migration_manifest.json` |
| Audit report | `reports/artifact_registry/<business_date>/registry_audit.md` |

## Accepted Artifact Set Layout

Defined sets:

- Candidate Accepted Artifact Set: model, manifest, feature schema, training metadata, validation evidence, hashes, accepted status.
- Opportunity Accepted Artifact Set: model, metrics, feature schema, training metadata, validation evidence, hashes, accepted status.
- PM Accepted Artifact Set: code-policy identity/hash, adapter identity/hash, policy version, feature version, accepted status.
- Capital Allocation Accepted Artifact Set: policy artifact, schema, version, hash, validation evidence, accepted status.

Set mismatch makes Runtime use ineligible.

## Current Path Classification

| Path | Classification |
|---|---:|
| `.runtime/candidate_ai/models/phase4bf_formal_candidate_model.pkl` | `TEMPORARY_REGISTERED_PATH`, `MIGRATION_REQUIRED` |
| `.runtime/candidate_ai/models/phase4bf_formal_candidate_model_manifest.json` | `TEMPORARY_REGISTERED_PATH`, `MIGRATION_REQUIRED` |
| `reports/opportunity_ai/phase5p/models/opportunity_model.pkl` | `TEMPORARY_REGISTERED_PATH`, `MIGRATION_REQUIRED` |
| `reports/opportunity_ai/phase5p/training/opportunity_training_metrics.json` | `TEMPORARY_REGISTERED_PATH`, `MIGRATION_REQUIRED` |
| `reports/opportunity_ai/phase5e/opportunity_training_metrics.json` | `LEGACY_ONLY`, `TRAINING_ONLY` |
| `.runtime/operations/feature_artifacts/<date>/` | `ACCEPTED_CURRENT_PATH`, `MIGRATION_REQUIRED` |
| `.runtime/runtime_state/buy_ai/<date>/` | `ACCEPTED_CURRENT_PATH`, `MIGRATION_REQUIRED` |
| `.runtime/runtime_state/position_management/<date>/` | `ACCEPTED_CURRENT_PATH`, `MIGRATION_REQUIRED` |
| `.runtime/phase9/canonical_data/` | `TEMPORARY_REGISTERED_PATH`, `MIGRATION_REQUIRED` |

## Migration Sequence

1. Stage 0: Inventory Freeze
2. Stage 1: Logical Registration
3. Stage 2: Artifact Set Acceptance
4. Stage 3: Consumer Compatibility Validation
5. Stage 4: New Path Preparation
6. Stage 5: Copy and Verify
7. Stage 6: Read Cutover
8. Stage 7: Regression
9. Stage 8: Legacy Freeze
10. Stage 9: Cleanup Decision

Initial migration uses copy, not move.

## Copy / Verify Policy

Required:

- deterministic copy
- staging path before final registration
- SHA-256 content hash
- aggregate directory inventory hash
- file count verification
- schema verification
- manifest/source-ref verification
- rollback point before read cutover

## Consumer Cutover Sequence

Recommended order:

1. Registry validates current explicit paths without changing consumers.
2. Candidate model and manifest registration.
3. Opportunity model/metrics artifact set registration.
4. PM code-policy and adapter set registration.
5. Capital Allocation policy set registration.
6. Feature producer source/target validation.
7. Decision producer output registration.
8. CLI/config logical ID integration.
9. Audit/report Registry refs.
10. Legacy freeze of old paths after regression.

Silent fallback remains prohibited throughout.

Phase16-N clarification: the first implementation scope after amendment is limited to read-only Artifact Inventory, Logical Artifact ID preparation, current path/hash/schema inventory, Draft/Validated Registry event preparation, Accepted Artifact Set manifest preparation, read-only compatibility validation, and Registry audit report generation. It still prohibits new physical paths, artifact copy/move, consumer cutover, CLI/config default changes, Opportunity fallback correction, standalone Capital Allocation Decision Artifact adoption, Backup/Reset/Restore, Historical Broker, Point-in-time Guard, and Historical Simulation.

## Registry Integration Recommendation

Use staged integration:

- Stage 1: CLI explicit path + Registry pre-validation.
- Later Production operation: config stores logical artifact IDs and startup resolves through Registry.
- Manual/operator override: explicit logical artifact ID.

Registry resolves and verifies an explicitly requested logical ID. It must not auto-select an artifact.

## Backward Compatibility

Existing CLI path args, default paths, config, reports, and acceptance tests remain valid before cutover. During transition there is only one active authority:

- before cutover: current explicit/default path is active
- after cutover: Registry-resolved logical ID is active

Dual authority is prohibited.

## Dual-read / Dual-write Policy

Prohibited:

- search multiple paths and use whichever exists
- active dual-write of decision artifacts
- fallback to old path after Registry failure

Allowed only:

- read-only comparison
- no decision authority
- no Submit authority
- audit diff only

## Rollback Strategy

Rollback triggers include hash mismatch, schema mismatch, consumer failure, regression failure, Runtime output divergence, decision/planning/pending divergence, Submit Guard divergence, and authority ambiguity.

Rollback guarantees:

- old path is sole active authority
- Registry history is retained
- incomplete accepted status is revoked or superseded
- new path is unusable
- Runtime State, Current, Ledger, and Pending remain unaffected

## Regression Gate

Required gates:

- Candidate Decision identity
- Opportunity Decision identity
- PM Decision identity
- Capital Allocation result identity
- Planning result identity
- Pending result identity
- Submit Guard result identity
- Current / Ledger / Runtime State unchanged
- AI Feature Schema unchanged
- Model / Metrics Hash unchanged

Semantic artifact divergence is FAIL. Timestamp/run-id-only differences must be classified separately.

## Legacy Policy

Old artifacts are retained as:

- `LEGACY_READ_ONLY`
- `EVIDENCE_ONLY`
- `TRAINING_ONLY`
- `REVOKED`
- `DELETION_CANDIDATE`

Deletion requires separate acceptance and is not approved by Phase16-L.

## Current Implementation Gaps

| Gap | Judgment |
|---|---:|
| Permanent Artifact Path | DESIGN_ACCEPTED_IMPLEMENTATION_REQUIRED |
| Registry storage | DESIGN_ACCEPTED_IMPLEMENTATION_REQUIRED |
| Artifact Set registration | DESIGN_ACCEPTED_IMPLEMENTATION_REQUIRED |
| Opportunity fallback | MIGRATION_REQUIRED |
| PM hash refs | DESIGN_ACCEPTED_IMPLEMENTATION_REQUIRED |
| Decision Artifact hash | DESIGN_ACCEPTED_IMPLEMENTATION_REQUIRED |
| Capital Allocation Artifact | DESIGN_ACCEPTED_IMPLEMENTATION_REQUIRED |
| Phase-numbered paths | MIGRATION_REQUIRED |
| Consumer cutover | DESIGN_ACCEPTED_IMPLEMENTATION_REQUIRED |
| Rollback implementation | DESIGN_ACCEPTED_IMPLEMENTATION_REQUIRED |
| Regression Gate implementation | DESIGN_ACCEPTED_IMPLEMENTATION_REQUIRED |

## Migration Gaps

- Current Runtime consumers still read explicit/default paths.
- Registry does not exist yet.
- New permanent artifact paths do not exist yet.
- Opportunity metrics fallback remains in current implementation.
- Current decision artifacts do not enforce full source/model hash contracts.

## Design Review Items

No blocking design review item remains for the Phase16-L design. Implementation sequencing must be reviewed before creating paths, copying artifacts, changing consumers, or fixing fallback.

## Next Prefix

`REVIEW_REQUIRED_BEFORE_NEXT_PREFIX`

Do not proceed to Registry implementation, path migration, consumer cutover, or Opportunity fallback correction without review.
