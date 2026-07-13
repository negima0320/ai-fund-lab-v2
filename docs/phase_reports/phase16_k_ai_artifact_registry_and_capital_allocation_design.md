# Phase16-K AI Artifact Registry and Capital Allocation Contract Design

Prefix: Phase16-K

Work name: AI Artifact Registry and Capital Allocation Contract Design

## Final Judgment

`PHASE16_K_AI_ARTIFACT_REGISTRY_AND_CAPITAL_ALLOCATION_DESIGN_ACCEPTED`

The AI Artifact Registry logical contract and Capital Allocation Policy / Decision Artifact contract are accepted as design. Implementation, path migration, model movement, metrics switching, fallback removal, Capital Allocation code changes, Runtime changes, AI changes, Feature changes, Reset, Restore, Simulation, and Historical Test were not performed.

## Created / Updated Files

- `docs/02_architecture/ai_artifact_registry_and_capital_allocation_contract.md`
- `docs/phase_reports/phase16_k_ai_artifact_registry_and_capital_allocation_design.md`
- `reports/phase_reports/phase16_k_ai_artifact_registry_and_capital_allocation_design.json`
- `docs/01_requirements/phase_roadmap.md`

## Artifact Registry Role

Phase16-N wording amendment: the Registry is the `Artifact Identity and Runtime Eligibility Authority`. It identifies which artifacts are eligible for Runtime use by logical identity, version, schema, hash, producer, consumer, accepted status, source refs, and migration status.

The Registry is not a sell/buy/submit authority.

## Registry Authority

Registry owns:

- artifact identity
- integrity/hash evidence
- accepted status record
- Runtime-use eligibility
- legacy/migration/revoke status

Registry does not own:

- model profitability
- AI decision correctness
- Capital Allocation judgment
- Planning authority
- Safety or Policy judgment
- Current, Ledger, Pending, Execution authority
- Submit authority
- Broker result authority

## Guarantees / Non-Guarantees

Guarantees:

- unique logical artifact ID
- physical path mapping
- content hash and schema hash
- producer/consumer compatibility
- accepted status
- source refs and source hashes
- retention and migration classification

Non-guarantees:

- return performance
- AI judgment correctness
- Safety release
- Policy approval
- Broker execution
- Runtime Current correctness

## Artifact Types

Defined Registry targets:

- Raw Data Artifact
- Canonical Data Artifact
- Trading Calendar Artifact
- Listed Issues Artifact
- Corporate Action Artifact
- Candidate / Opportunity / Position / Capital Feature Artifacts
- Candidate Model Artifact
- Opportunity Model Artifact
- Opportunity Metrics Artifact
- PM Code Policy Artifact
- PM Runtime Adapter Artifact
- Candidate / Opportunity / PM Decision Artifacts
- Policy Artifact
- Safety Artifact
- Capital Allocation Policy Artifact
- Capital Allocation Decision Artifact
- Training / Validation / Acceptance Fixture / Historical Evidence / Legacy Artifacts

## Artifact Identity

The design separates:

- `logical_artifact_id`
- `artifact_instance_id`
- `artifact_type`
- `component`
- `version`
- `business_date`
- `feature_date`
- `as_of`
- `physical_path`
- `content_hash`
- `schema_hash`
- `producer_version`

Phase-numbered physical paths must not become logical identity.

## Accepted Status

Statuses:

- `DRAFT`
- `VALIDATED`
- `ACCEPTED`
- `REJECTED`
- `LEGACY`
- `REVOKED`

Runtime-use requires `ACCEPTED`, `runtime_use_eligible=true`, hash match, schema match, consumer compatibility, valid source refs, point-in-time validity, and existing physical path.

## Runtime Eligibility

Artifact existence alone is insufficient. Runtime must fail closed or move to review-required when Registry checks fail. Silent fallback is prohibited.

## Model / Metrics Artifact Set

Opportunity AI must use an accepted artifact set containing model, metrics, feature schema, training metadata, and hashes. The current Phase5-P model with Phase5-E metrics fallback is classified as `MIGRATION_REQUIRED`.

Candidate AI should also use an accepted artifact set with model, manifest/feature schema, training summary, validation report, and hashes.

## PM Code Policy Registry

Position Management has no external model artifact. The accepted unit is:

- PM code-policy artifact
- Runtime adapter artifact
- policy version
- feature version
- code hash
- adapter hash
- accepted status
- Runtime-use eligibility

PM Decision Artifacts must reference code-policy artifact ID/hash and adapter artifact ID/hash.

## Decision Artifact Hash Contract

Candidate, Opportunity, and PM Decision Artifacts must include artifact hash, input refs, input hashes, model/code-policy refs, model/code-policy hashes, schema version, business date, as_of, producer, and producer version.

Prohibited:

- source refs missing
- input hash missing
- model/code-policy hash missing
- unknown schema
- unknown producer

## Registry Storage Recommendation

Recommended design:

```text
append-only JSONL registry event log
↓
materialized central index
↓
optional SQLite query index for Production operations
```

Phase16-N clarification: Phase16 initial Registry implementation requires only the append-only JSONL event log plus materialized JSON central index. SQLite is `OPTIONAL_LATER`; it is not a prerequisite for the initial Registry implementation.

This maximizes auditability while leaving a path to stronger Production queryability. No implementation was performed.

## Physical Path Policy

Classifications:

- `ACCEPTED_PERMANENT_PATH`
- `TEMPORARY_REGISTERED_PATH`
- `MIGRATION_REQUIRED`
- `LEGACY_ONLY`

Phase-numbered paths may be temporarily registered under permanent logical identity, but this does not make them permanent Source of Truth.

## Retention / Immutability

- Accepted Model / Metrics / Code Policy Artifacts are immutable.
- Decision Artifacts are append-only / immutable.
- Registry history is append-only.
- Legacy Artifacts are read-only.
- Revoked Artifacts are retained but unusable.

## Failure / Fallback Policy

Silent fallback is prohibited.

Examples:

- model hash mismatch: `HALT`
- model/metrics set mismatch: `HALT`
- legacy artifact Runtime reference: `HALT`
- decision source hash missing: `REVIEW_REQUIRED`
- schema mismatch: `REVIEW_REQUIRED` before planning, `HALT` before submit if unresolved

Opportunity metrics fallback is a migration target and must not be accepted as permanent behavior.

Generated Decision Artifact registration or audit-write failures are `REVIEW_REQUIRED` and must stop before Planning, Pending generation, Submit, Current mutation, Ledger mutation, or new Pending consumption. Integrity or authority mismatches remain `HALT`.

## Capital Allocation Role

Capital Allocation is not AI. It allocates capital and quantity to accepted Opportunity / Policy-approved symbols.

It decides investment amount, target quantity, cash buffer, effective order limit, position limit, and allocation rejection reasons.

It must not decide Candidate score, Opportunity score, Safety release, Submit authority, Broker result, Current mutation, or model/metrics selection.

Phase16-N clarification: standalone Capital Allocation Decision Artifact adoption is staged. Register policy first, record current `CapitalAllocationSignal` as evidence, run read-only semantic equality against Planning/Pending output, and only consider adoption through separate Acceptance after the gate passes.

## Capital Allocation Input

Required inputs:

- Opportunity Decision Artifact
- Capital Allocation Policy Artifact
- Safety Decision
- Current
- available cash / buying power
- existing positions / exposure
- portfolio constraints
- lot size / trading unit
- business date
- as_of

Allowed Current fields include cash, buying power, total equity, positions, quantity, average price, current price, market value, current exposure, position_state_as_of, valuation_as_of, and freshness/status fields.

## Capital Allocation Output

Required output fields:

- allocation decision ID
- symbol
- allocated capital
- target quantity
- cash reserve
- position limit
- rejection reason
- policy refs/hash
- safety refs/hash
- Current ref/hash
- input refs/hashes
- generated_at

## Capital Allocation Artifacts

Two artifacts are defined:

- Capital Allocation Policy Artifact: reusable capital deployment rules.
- Capital Allocation Decision Artifact: business-date allocation result generated from accepted inputs.

Current implementation has `CapitalDeploymentPolicy` and `CapitalAllocationSignal`, but no standalone registered Decision Artifact. Judgment: `DESIGN_ACCEPTED_IMPLEMENTATION_REQUIRED`.

## Producer / Consumer Matrix

The full matrix is in the architecture document. Key points:

- Pending is Registry-adjacent but not a Registry target because it is Runtime authority state.
- Pending must reference registered upstream artifacts and hashes.
- Submit Guard remains Submit authority, not Registry.

## Current Implementation Gaps

| Area | Judgment |
|---|---:|
| Candidate model registration | DESIGN_ACCEPTED_IMPLEMENTATION_REQUIRED |
| Candidate decision hash | DESIGN_ACCEPTED_IMPLEMENTATION_REQUIRED |
| Opportunity model/metrics set | MIGRATION_REQUIRED |
| Opportunity fallback | MIGRATION_REQUIRED |
| Opportunity decision hash | DESIGN_ACCEPTED_IMPLEMENTATION_REQUIRED |
| PM code-policy registration | DESIGN_ACCEPTED_IMPLEMENTATION_REQUIRED |
| PM decision hash | DESIGN_ACCEPTED_IMPLEMENTATION_REQUIRED |
| Capital Allocation contract | DESIGN_ACCEPTED_IMPLEMENTATION_REQUIRED |
| Capital Allocation artifact | DESIGN_ACCEPTED_IMPLEMENTATION_REQUIRED |
| Central Registry | DESIGN_ACCEPTED_IMPLEMENTATION_REQUIRED |
| Phase-numbered paths | MIGRATION_REQUIRED |

## Migration Gaps

- Register accepted logical identities before moving files.
- Replace Opportunity metrics fallback with accepted artifact set lookup in a later implementation phase.
- Add decision artifact hash enforcement.
- Add PM code-policy and adapter registry entries.
- Add Capital Allocation Decision Artifact generation and registry linkage.

## Design Review Items

No blocking design review item remains for Phase16-K. Implementation details for storage engine and migration sequencing remain for later phases.

## Next Prefix

`REVIEW_REQUIRED_BEFORE_NEXT_PREFIX`

Do not proceed to Registry implementation, fallback correction, artifact migration, or Capital Allocation code changes until this design is reviewed.
