# Phase16-M Operational Data Foundation Executive Architecture Review

Prefix: `Phase16-M`

Work name: `Operational Data Foundation Executive Architecture Review`

Created at: 2026-07-13

## Final Judgment

`PHASE16_M_ACCEPTED_WITH_MINOR_AMENDMENTS`

Implementation readiness:

`IMPLEMENTATION_READY_AFTER_MINOR_AMENDMENTS`

This is an executive architecture review only. No existing design document, roadmap, Runtime code, CLI, config, AI, Feature producer, Capital Allocation, path, artifact, reset, restore, simulation, or Historical Runtime Test was changed or executed.

## Created Files

- `docs/phase_reports/phase16_m_operational_data_foundation_executive_architecture_review.md`
- `reports/phase_reports/phase16_m_operational_data_foundation_executive_architecture_review.json`

## Executive Summary

Phase16-I through Phase16-L are directionally consistent: Phase16 is now `Operational Data Foundation`, not a Historical-only or backtest-only phase. The reviewed architecture keeps normal Runtime v2 as the fixed mainline, separates artifact identity from physical paths, prohibits Phase-numbered paths as permanent Source of Truth, and preserves Runtime authority for Pending, Execution, Ledger, Current, Safety, Policy, and Submit.

The design can proceed after minor amendments, but only for limited implementation scope: read-only logical Registry inventory, artifact set manifest preparation, hash/schema validation, and pre-cutover compatibility checks. Full path migration, consumer cutover, fallback removal, Capital Allocation decision artifact implementation, Reset/Restore, Historical Broker, Point-in-time Guard, and Historical Runtime Simulation are not ready to start from this review alone.

No critical design blocker was found. Major implementation blockers remain by design and are already acknowledged in Phase16-G/K/L: the Registry does not exist, artifact sets are not registered, historical Calendar/Listed/Corporate Action sources remain incomplete, and current Runtime feature generation is wired to recent operational data rather than complete 2021+ canonical historical inputs.

## Evidence Reviewed

| Area | Evidence |
|---|---|
| Phase16 purpose | `docs/phase_reports/phase16_i_operational_data_foundation_purpose_and_goals.md`; `docs/01_requirements/phase_roadmap.md` |
| Scope revision | `docs/phase_reports/phase16_h_scope_revision_and_canonical_data_foundation.md` |
| Canonical historical data audit | `docs/phase_reports/phase16_g_canonical_historical_data_source_audit.md` |
| AI input/output contract | `docs/02_architecture/ai_input_output_and_artifact_contract.md`; `docs/phase_reports/phase16_j_ai_input_output_and_artifact_architecture.md` |
| Registry and Capital Allocation | `docs/02_architecture/ai_artifact_registry_and_capital_allocation_contract.md`; `docs/phase_reports/phase16_k_ai_artifact_registry_and_capital_allocation_design.md` |
| Physical path and migration | `docs/02_architecture/artifact_path_registry_integration_and_migration_contract.md`; `docs/phase_reports/phase16_l_artifact_path_registry_integration_and_migration_design.md` |
| Historical contract phase references | `docs/02_architecture/historical_runtime_test_contract.md` |

## Required Questions

| Question | Answer | Evidence / reason |
|---|---|---|
| 1. Is the design still aligned with the top-level project purpose? | Yes | Phase16-I and K restate Production-oriented safe continuous Japanese equity auto-trading, with safety above return. |
| 2. Is Phase16 correctly scoped? | Yes, with minor doc alignment needed | I/L prohibit Historical-only paths and Phase16-specific Runtime roots. Some older phase-gate text still names outdated K/L contents. |
| 3. Are layers clear? | Mostly clear | J defines Raw, Canonical, Feature, AI Artifact, AI Decision, Policy/Safety/Planning, Runtime State Machine. |
| 4. Is Source of Truth clear? | Clear for architecture, not fully implemented | G confirms OHLCV raw/normalized but gaps remain for Calendar/Listed/Corporate Action and Runtime historical feature wiring. |
| 5. Is authority clear? | Yes | K states Registry owns identity/integrity/eligibility, not buy/sell/submit/Current authority. L keeps Runtime state separate. |
| 6. Is the Artifact Registry appropriate? | Yes, with staging amendment | JSONL plus materialized index is appropriate. Optional SQLite must stay explicitly non-blocking and later-stage only. |
| 7. Is Capital Allocation correctly placed? | Yes, with phased amendment | K classifies it as Policy/Allocation, not AI. Current implementation embeds allocation in Planning, so standalone artifact introduction must be staged. |
| 8. Is Runtime boundary protected? | Yes | J/K/L prohibit Registry from owning Pending, Execution, Ledger, Current, Submit, or Safety authority. |
| 9. Is physical path design appropriate? | Yes | L recommends Option A phased: register current paths first, copy/verify later, cut over only after regression. |
| 10. Is migration/rollback credible? | Yes for design, implementation missing | L defines stages, copy-not-move, rollback triggers, and no Current/Ledger/Pending mutation on rollback. |
| 11. Is failure/recovery well-defined? | Mostly; minor amendment needed | K defines HALT/REVIEW_REQUIRED. Daily generated decision registration failure should be clarified before implementation. |
| 12. Is the design production applicable? | Yes, if phased | It applies to Production/Demo/Paper/Historical and avoids mode-specific Source of Truth. Full production operation requires later implementation gates. |
| 13. Is it overengineered? | No if staged | Registry + paths are complex, but justified by auditability and production safety. Implementing all layers at once would be over-scope. |
| 14. Are documents consistent? | Mostly; minor inconsistencies remain | Roadmap now lists K/L as Registry/Path, while H and historical contract still contain older K/L labels. |
| 15. Can implementation start now? | Only after minor amendments and only in limited scope | Startable: read-only inventory and validation. Not startable: path migration, consumer cutover, historical simulation. |

## Architecture Review

### Project Purpose Alignment

Judgment: `ACCEPTED`

Phase16-I defines the project purpose as safe, continuous Japanese stock auto-trading with eventual Production operation. It explicitly ranks safety, correctness, continuity, auditability, and explainability before return. Phase16-K repeats this purpose and says the Registry supports safe operation by verifying eligible artifacts, not by deciding trades or optimizing return.

### Phase16 Scope Alignment

Judgment: `ACCEPTED_WITH_MINOR_AMENDMENT`

The accepted Phase16 scope is common Operational Data Foundation for Production, Demo, Paper, and Historical. Phase16-I prohibits Historical-only, Backtest-only, Replay-only, and Phase16-only Source of Truth or Runtime routes. Phase16-L also states the path design is not historical-only, demo-only, or Phase16-only.

Minor amendment is required because `docs/phase_reports/phase16_h_scope_revision_and_canonical_data_foundation.md` and `docs/02_architecture/historical_runtime_test_contract.md` still show older labels where Phase16-K is "Canonical Path and Data Lineage Migration Design" and Phase16-L is "Canonical Market Data Foundation". These labels are superseded historical-plan evidence; the current roadmap and completed reports define K as Registry/Capital Allocation and L as Artifact Path/Registry Migration.

### Layer Architecture Judgment

Judgment: `ACCEPTED`

| Layer | Judgment | Notes |
|---|---:|---|
| J-Quants Raw | `CLEAR` | G confirms formal raw daily quote responses for 2021+. |
| Canonical Market Data | `CLEAR_WITH_GAPS` | Normalized OHLCV exists; Calendar/Listed/Corporate Action remain incomplete. |
| Feature Producer | `CLEAR_WITH_IMPLEMENTATION_GAP` | J defines Feature Artifact boundary; G says Runtime feature generation currently uses recent operations data. |
| Feature Artifact | `CLEAR` | J and L define candidate/opportunity/position/capital feature artifacts. |
| AI Artifact | `CLEAR_WITH_IMPLEMENTATION_GAP` | Candidate/Opportunity/PM identities are defined; Registry not implemented. |
| AI Decision Artifact | `CLEAR_WITH_IMPLEMENTATION_GAP` | Required hashes/source refs defined; current outputs do not fully enforce them. |
| Policy / Safety | `CLEAR` | K keeps them outside Registry trading authority. |
| Capital Allocation | `CLEAR_WITH_IMPLEMENTATION_GAP` | Policy/Decision artifact split is defined; standalone decision artifact not implemented. |
| Planning / Pending / Submit | `CLEAR` | Registry does not own active Pending or Submit authority. |
| Execution / Ledger / Current | `CLEAR` | L rollback explicitly avoids Current/Ledger/Pending mutation. |
| Runtime Report | `CLEAR` | Report/audit can add Registry refs later but must not become Runtime input authority. |

### Source of Truth Judgment

Judgment: `ACCEPTED_WITH_KNOWN_GAPS`

Runtime Source of Truth chain should be:

```text
J-Quants Raw
↓
Canonical Market Data / Calendar / Listed / Corporate Action
↓
Canonical Feature Producer
↓
Feature Artifact
↓
AI Artifact / AI Decision Artifact
↓
Policy / Safety / Capital Allocation
↓
Runtime v2 Mainline
```

Phase16-G confirms formal raw daily quotes under `.runtime/data/raw/jquants/equities_bars_daily/responses/` and normalized OHLCV under `.runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet`. It also confirms that trading calendar, listed issues, and corporate action evidence are insufficient for full 2021+ historical simulation. These gaps are data-foundation blockers, not contradictions in the I-L architecture.

### Authority Judgment

Judgment: `ACCEPTED`

Registry authority is bounded to artifact identity, integrity, accepted status, Runtime-use eligibility, consumer compatibility, migration status, and revoke/legacy state. It explicitly does not own model profitability, AI correctness, Safety, Policy, Broker results, Submit, Current, Ledger, Pending, or Execution authority. This protects Runtime v2 mainline authority.

### Artifact Registry Judgment

Judgment: `ACCEPTED_WITH_MINOR_AMENDMENT`

The logical Registry contract is production-suitable: accepted status, content/schema hashes, producer/consumer compatibility, source refs, point-in-time fields, and append-only history are appropriate. The storage recommendation of append-only JSONL event log plus materialized index is suitable for initial implementation.

Minor amendment: the optional SQLite index should be explicitly described as later operational optimization, not Phase16 implementation prerequisite, to avoid over-scoping the first Registry implementation.

### Capital Allocation Judgment

Judgment: `ACCEPTED_WITH_MINOR_AMENDMENT`

K correctly states that Capital Allocation is not AI. It allocates capital, quantity, cash buffer, and exposure constraints to accepted Opportunity/Policy-approved symbols. It must not decide AI scores, Safety release, Submit authority, Broker result, Current mutation, or model selection.

Minor amendment: because the current implementation uses `CapitalAllocationSignal` embedded in Planning and Pending evidence, the design should explicitly stage implementation as: register Capital Allocation policy first, preserve current Planning behavior, then introduce standalone Capital Allocation Decision Artifact only after equality gates pass.

### Runtime Boundary Judgment

Judgment: `ACCEPTED`

The design does not change Runtime v2 authority. J defines AI as bounded decision artifact producers; K states Registry does not own Runtime State authority; L keeps `.runtime/runtime_state` separate from `.runtime/artifacts` and says decision paths under runtime state remain current write authority until an explicit cutover.

### Physical Path Judgment

Judgment: `ACCEPTED`

Option A phased is the right architecture: central `.runtime/artifacts` and separate `.runtime/artifact_registry`, with current paths registered before any physical move. This gives auditability without forcing immediate Runtime or CLI changes. Phase-numbered paths may be temporarily registered but must not become logical identity or permanent Source of Truth.

### Migration / Rollback Judgment

Judgment: `ACCEPTED`

L defines Inventory Freeze, Logical Registration, Artifact Set Acceptance, Consumer Compatibility, New Path Preparation, Copy/Verify, Read Cutover, Regression, Legacy Freeze, and Cleanup Decision. Copy-not-move and deletion-by-separate-acceptance are appropriate. Rollback preserves old path as sole active authority and does not require Current/Ledger/Pending mutation.

### Failure / Recovery Judgment

Judgment: `ACCEPTED_WITH_MINOR_AMENDMENT`

K's default fail-closed behavior is correct for required model/policy artifacts and integrity mismatch. However, generated daily decision registration failure should be clarified as `REVIEW_REQUIRED before planning/submit` with no downstream Runtime mutation, unless the failure reveals a model/control artifact integrity problem. This preserves safety without turning every audit-write issue into an overbroad HALT.

### Production Applicability

Judgment: `ACCEPTED`

The reviewed contracts apply to Production, Demo, Paper, and Historical modes. They prohibit mode-specific registries and Historical-only Source of Truth. Mode differences belong in artifact metadata and manifests, not in separate Runtime roots or permanent paths.

### Complexity Judgment

Judgment: `ACCEPTED_WITH_STAGING_REQUIRED`

The architecture is complex but justified by production safety, artifact auditability, and avoiding hidden Phase artifact dependencies. It becomes overengineered only if all storage, path migration, logical ID resolution, SQLite indexing, Capital Allocation artifactization, and consumer cutover are attempted in one implementation prefix.

### Cross-document Consistency

Judgment: `ACCEPTED_WITH_MINOR_AMENDMENT`

Core architecture is consistent. Minor naming/sequence drift remains in older Phase16-H and historical contract phase-gate references. These should be amended before implementation planning so later prefixes do not accidentally resume the old Historical-first sequence.

## Findings

### Critical Findings

None.

### Major Findings

| ID | Finding | Affected contract | Risk | Production impact | Phase16 impact | Action | Blocking |
|---|---|---|---|---|---|---|---:|
| M-01 | Full Registry/path/consumer implementation is not ready yet. | K Registry; L Path Migration | Attempting cutover before Registry, artifact sets, and regression gates exist can create authority ambiguity. | High if applied to Production defaults. | Blocks full migration and consumer cutover. | Implement in staged prefixes after minor amendments. | Yes for full implementation; no for read-only inventory. |
| M-02 | Historical Calendar, Listed Issues, and Corporate Action sources remain incomplete. | G Canonical Data; future L2/M data foundation | Historical simulation may depend on Phase artifacts or incomplete universe/corporate-action evidence. | Medium to high for historical validation and Production auditability. | Blocks Phase17 Historical Runtime Simulation readiness. | Complete data foundation before Feature/Simulation readiness acceptance. | Yes for Historical Simulation; no for Registry design. |

### Minor Findings

| ID | Finding | Affected contract | Risk | Production impact | Phase16 impact | Action | Blocking |
|---|---|---|---|---|---|---|---:|
| m-01 | Phase16-K/L naming differs across roadmap, H, and historical contract. | Roadmap / historical contract references | Later work may follow stale phase sequence. | Low | Could confuse next prefixes. | Amend phase-gate references. | Yes before implementation planning. |
| m-02 | Optional SQLite could be mistaken as initial requirement. | K Registry storage | Over-scoped implementation. | Low | Could slow Registry start. | Clarify JSONL + index first; SQLite later only. | Yes before Registry implementation. |
| m-03 | Generated decision registration failure semantics need one more rule. | K failure behavior | Audit-write failure might be treated as broad HALT or allowed too far. | Medium | Could affect planning/submit gate behavior. | Add rule: generated decision registration failure is REVIEW_REQUIRED before planning/submit unless integrity failure. | Yes before generated decision registration implementation. |
| m-04 | Capital Allocation artifactization needs staged wording. | K Capital Allocation | Premature standalone artifact could change Planning semantics. | Medium | Could violate semantic equality gate. | Register policy first; keep current Planning behavior until equality gates pass. | Yes before Capital Allocation artifact implementation. |

### Observations

| ID | Observation |
|---|---|
| o-01 | The architecture correctly refuses to promote Phase4/5/6 artifacts or `reports/` paths to Source of Truth by path alone. |
| o-02 | L's copy/verify/cutover/legacy-freeze approach is safer than moving artifacts in place. |
| o-03 | Registry pre-validation of explicit paths is the right first implementation stage because it has low Runtime blast radius. |
| o-04 | Runtime reports can include Registry refs later, but reports must remain evidence/output rather than Runtime input authority. |

## Amendment Proposals

### Amendment 1: Align Phase16 Sequence References

| Field | Value |
|---|---|
| Target docs / sections | `docs/phase_reports/phase16_h_scope_revision_and_canonical_data_foundation.md` Phase16 Current Plan; `docs/02_architecture/historical_runtime_test_contract.md` Phase16 Readiness Gates |
| Current design | Older references describe Phase16-K as Canonical Path/Data Lineage and Phase16-L as Canonical Market Data Foundation. |
| Problem | Current accepted roadmap and completed reports define K as AI Artifact Registry / Capital Allocation and L as Artifact Physical Path / Registry Integration / Migration. |
| Proposed change | Update phase-gate labels to match accepted K/L and later data-foundation sequencing. Preserve old text only as historical amendment evidence if needed. |
| Reason | Prevent implementation prefixes from following stale Historical-first sequencing. |
| Scope | Documentation amendment only. |
| Regression risk | Low. |
| Blocking | Blocks implementation planning, not architecture acceptance. |

### Amendment 2: Clarify Registry Storage Staging

| Field | Value |
|---|---|
| Target docs / sections | `docs/02_architecture/ai_artifact_registry_and_capital_allocation_contract.md` Registry Storage Options; `docs/02_architecture/artifact_path_registry_integration_and_migration_contract.md` Registry Storage Layout |
| Current design | Recommended pattern includes JSONL event log, materialized central index, and optional SQLite query index. |
| Problem | Optional SQLite might be interpreted as a Phase16 initial implementation requirement. |
| Proposed change | State that Phase16 initial Registry implementation requires only append-only JSONL plus materialized JSON index; SQLite is a later optional production optimization. |
| Reason | Avoid overengineering and keep first implementation auditable and small. |
| Scope | Documentation amendment only. |
| Regression risk | Low. |
| Blocking | Blocks Registry implementation scoping. |

### Amendment 3: Clarify Generated Decision Registration Failure

| Field | Value |
|---|---|
| Target docs / sections | `docs/02_architecture/ai_artifact_registry_and_capital_allocation_contract.md` Runtime Eligibility and Failure Behavior / Failure Fallback Policy |
| Current design | Generated decision hash/source issues are `REVIEW_REQUIRED`; required model/control integrity issues are `HALT`. |
| Problem | Registry write or registration failure for same-day generated decisions needs explicit downstream behavior. |
| Proposed change | Add: if a generated Candidate/Opportunity/PM/Capital Allocation Decision Artifact cannot be registered or validated, Planning/Submit must not proceed and status becomes `REVIEW_REQUIRED`; Current/Ledger/Pending must not be mutated. Escalate to `HALT` only when the failure indicates required model/control artifact integrity or authority mismatch. |
| Reason | Preserve safety and availability semantics without overusing HALT. |
| Scope | Documentation amendment before implementation. |
| Regression risk | Low to medium. |
| Blocking | Blocks generated decision registration implementation. |

### Amendment 4: Stage Capital Allocation Artifactization

| Field | Value |
|---|---|
| Target docs / sections | `docs/02_architecture/ai_artifact_registry_and_capital_allocation_contract.md` Capital Allocation Decision Artifact; `docs/02_architecture/artifact_path_registry_integration_and_migration_contract.md` Consumer Cutover |
| Current design | Capital Allocation Policy and Decision Artifacts are defined; current implementation embeds allocation signals in Planning/Pending evidence. |
| Problem | Implementing standalone Capital Allocation Decision Artifact too early may alter Planning semantics. |
| Proposed change | State the staged path: first register Capital Allocation Policy Artifact and current policy hash; then record current `CapitalAllocationSignal` evidence; only introduce standalone Capital Allocation Decision Artifact after semantic equality gates pass. |
| Reason | Protect Runtime mainline and avoid accidental behavior change. |
| Scope | Documentation amendment before implementation. |
| Regression risk | Medium if skipped; low if staged. |
| Blocking | Blocks Capital Allocation artifact implementation, not read-only Registry inventory. |

## Implementation Readiness

Overall readiness:

`IMPLEMENTATION_READY_AFTER_MINOR_AMENDMENTS`

Startable only after the above amendments:

- read-only artifact inventory freeze
- Registry event/index schema drafting
- current-path logical registration in draft/validated state
- Candidate model/manifest hash registration
- Opportunity model/metrics set manifest preparation
- PM code-policy and adapter hash manifest preparation
- Capital Allocation policy hash registration
- Registry audit report generation
- compatibility checks that do not alter Runtime consumers

Not startable from this review alone:

- physical path creation under `.runtime/artifacts`
- artifact copy/move
- consumer cutover to logical IDs
- CLI/config default changes
- Opportunity fallback correction in Runtime
- standalone Capital Allocation Decision Artifact consumption
- Backup/Reset/Restore
- Historical Broker
- Point-in-time Guard
- Historical Runtime Simulation
- Phase17 performance test

## Pre-implementation Fixes

Required before implementation prefixes:

1. Apply the four documentation amendments above.
2. Define the next implementation prefix scope narrowly as read-only Registry inventory / logical registration only.
3. Explicitly prohibit path creation, copy, consumer cutover, fallback fix, and Runtime behavior change in the first implementation prefix.
4. Keep Phase16-L's rollback and design-change stop rules active.

## Remaining Design Work

- Canonical Market Data permanent path acceptance after current phase-numbered path review.
- Trading Calendar, Listed Issues, and Corporate Action foundation.
- Canonical Feature Producer connection from accepted canonical inputs.
- AI Model / Policy / Capital Allocation freeze manifests.
- Backup / Reset / Restore operational contract and implementation.
- Historical Broker boundary.
- Point-in-time Guard.
- Phase16 Operational Data Foundation readiness acceptance.

## Implementation-startable Scope

The next executable design/implementation scope should be:

```text
Read-only Artifact Registry inventory and logical registration preparation
```

It must not include path migration, Runtime consumer cutover, AI/model change, Feature change, fallback correction, Reset, Restore, or simulation.

## Next Prefix

`REVIEW_REQUIRED_BEFORE_NEXT_PREFIX`

Recommended next human decision: approve the four minor amendments and then open a narrow implementation prefix for Registry inventory only.
