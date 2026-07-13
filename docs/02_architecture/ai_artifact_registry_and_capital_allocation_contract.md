# AI Artifact Registry and Capital Allocation Contract

Status: Phase16-K accepted design

This document defines the permanent AI Artifact Registry and Capital Allocation contract for AI Fund Lab v2. It applies to Production, Demo, Paper, and Historical operation. It is not a historical-test registry, a backtest registry, or a Phase16-only registry.

Operational lifecycle, reset exclusion, and environment transition rules are defined in:

```text
docs/02_architecture/operational_lifecycle_state_reset_and_environment_transition_contract.md
```

Artifact Registry history, accepted artifact sets, policy artifacts, schemas, and freeze manifests are Persistent Operational Foundation. They must be backed up as operational foundation and excluded from Trading State Reset.

## Purpose

AI Fund Lab v2 exists to build a Japanese equity auto-trading system that can be operated safely and continuously, and eventually in Production.

Return target:

```text
annualized 50%
```

Priority:

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

The Registry supports that goal by identifying which artifacts may be used by Runtime. It does not decide what to buy, what to sell, what to submit, or what Current state is authoritative.

## Registry Role

The AI Artifact Registry is the `Artifact Identity and Runtime Eligibility Authority` for registered artifacts. It is a verification index for artifact identity, integrity, accepted status, Runtime-use eligibility, consumer compatibility, and legacy/migration/revoke status.

It answers:

- What artifact is this?
- What logical role does it serve?
- What physical file currently carries that artifact?
- What version, schema, and hash are accepted?
- Who produced it?
- Who may consume it?
- Is it eligible for Runtime use?
- Is it legacy, temporary, migrated, revoked, or accepted?
- Which source artifacts and hashes does it depend on?

It is not a file inventory. A file can exist without being registered. A registered artifact can be ineligible for Runtime use.

## Authority

Registry authority is limited to artifact identity and eligibility:

| Authority | Registry owns? | Rule |
|---|---:|---|
| Artifact identity | Yes | Registry assigns logical and instance identity. |
| Artifact integrity | Yes | Registry records and verifies content/schema hashes. |
| Runtime-use eligibility | Yes | Registry states whether an artifact may be consumed by a named Runtime consumer. |
| Accepted status | Yes, through approved human/acceptance process | Runtime and AI cannot self-promote artifacts to `ACCEPTED`. |
| Model selection authority | No | Registry records accepted model sets; it does not optimize or select models automatically. |
| Feature selection authority | No | Registry verifies accepted feature artifacts; it does not choose feature dates alone. |
| AI decision authority | No | AI producers generate decisions; Registry verifies decision provenance. |
| Capital Allocation judgment | No | Capital Allocation / Planning apply allocation policy and sizing rules. Registry verifies artifacts only. |
| Planning authority | No | Planning remains a Runtime control layer. |
| Runtime State authority | No | Current, Ledger, Pending, Execution, and Runtime State remain Runtime authorities. |
| Submit authority | No | Submit Guard, Pending, approval, broker capability, and configured mode govern submit. |
| Safety authority | No | Safety remains an independent Runtime control. |
| Policy authority | No | Policy artifacts define policy; Registry verifies identity and eligibility. |

Registry must not decide:

- which symbols to buy
- which symbols to sell
- which orders to submit
- which Pending slot is active
- which Current state is authoritative
- whether Safety can be bypassed
- whether Broker results are accepted
- how much capital to allocate
- what Planning, Pending, Execution, Ledger, or Current state should be

## Guarantees

The Registry guarantees, for registered artifacts:

- unique logical identity
- artifact type
- component
- physical path at the time of registration
- version
- content hash
- schema hash
- producer and producer version
- consumer compatibility
- accepted status
- runtime-use eligibility
- business date / feature date / as_of fields when applicable
- source artifact references
- source hashes
- retention class
- legacy status
- migration status
- revoke status
- immutable history of status changes

## Non-Guarantees

The Registry does not guarantee:

- model profitability
- annualized return
- correctness of AI judgment
- Safety judgment
- Policy judgment
- Broker order acceptance
- Broker execution
- Runtime Current correctness
- Ledger correctness
- Pending lifecycle correctness
- absence of market risk
- absence of data-provider error
- that a Phase-numbered physical path is permanent

## Artifact Types

### Data Artifacts

| Artifact type | Runtime-use eligibility | Consumer | Notes |
|---|---:|---|---|
| Raw Data Artifact | Not direct Runtime AI input | Canonical producer, audit | Provider-origin evidence. |
| Canonical Data Artifact | Feature producer only | Feature Refresh, audit | Accepted normalized point-in-time data. |
| Trading Calendar Artifact | Runtime/Feature/Safety eligible | Calendar resolver, freshness gates | Must be point-in-time and versioned. |
| Listed Issues Artifact | Feature producer eligible | Feature Refresh | Universe/listing evidence. |
| Corporate Action Artifact | Feature/canonical producer eligible | Canonical/Feature producers | Split, reverse split, delisting, adjustment evidence. |

### Feature Artifacts

| Artifact type | Runtime-use eligibility | Consumer |
|---|---:|---|
| Candidate Feature Artifact | Eligible for Candidate AI | Candidate AI |
| Opportunity Feature Artifact | Eligible for Opportunity AI | Opportunity AI |
| Position Feature Artifact | Eligible for Position Management | PM producer |
| Capital Allocation Input Artifact | Eligible for Capital Allocation policy/allocation | Allocation layer |

### AI Artifacts

| Artifact type | Runtime-use eligibility | Consumer |
|---|---:|---|
| Candidate Model Artifact | Eligible only as part of accepted Candidate Artifact Set | Candidate AI |
| Opportunity Model Artifact | Eligible only as part of accepted Opportunity Artifact Set | Opportunity AI |
| Opportunity Metrics Artifact | Eligible only with matching Opportunity Artifact Set | Opportunity AI |
| PM Code Policy Artifact | Eligible only with accepted PM Code Policy Set | PM producer |
| PM Runtime Adapter Artifact | Eligible only with accepted PM Code Policy Set | PM producer |

### Decision Artifacts

| Artifact type | Runtime-use eligibility | Consumer |
|---|---:|---|
| Candidate Decision Artifact | Eligible for Opportunity AI and audit | Opportunity AI |
| Opportunity Decision Artifact | Eligible for Planning and Capital Allocation | Planning, allocation |
| Position Management Decision Artifact | Eligible for Sell Planning | Sell Planning |

### Control Artifacts

| Artifact type | Runtime-use eligibility | Consumer |
|---|---:|---|
| Policy Artifact | Eligible when accepted and current | Planning, Pending, Submit Guard |
| Safety Artifact | Eligible within freshness/expires contract | Planning, Pending, Submit Guard |
| Capital Allocation Policy Artifact | Eligible when accepted and hash-verified | Allocation layer, Planning |
| Capital Allocation Decision Artifact | Eligible for Planning/Pending when generated from accepted inputs | Planning, Pending, audit |

### Evidence / Legacy

| Artifact type | Runtime-use eligibility | Consumer |
|---|---:|---|
| Training Artifact | Not eligible | Audit, model lineage |
| Validation Artifact | Not eligible unless explicitly registered as model-set evidence | Audit, acceptance |
| Acceptance Fixture | Not eligible | Tests/audit |
| Historical Evidence | Not eligible as Runtime input | Audit/report |
| Legacy Artifact | Not eligible unless migrated and accepted under a new logical identity | Audit/migration |

## Artifact Identity

Registry separates logical identity from physical storage.

Required identity fields:

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
- `producer`
- `producer_version`
- `consumer`
- `accepted_status`
- `runtime_use_eligible`
- `source_artifact_refs`
- `source_hashes`
- `retention_class`
- `legacy_status`
- `migration_status`

Example:

```text
logical_artifact_id: candidate_model.accepted
artifact_instance_id: candidate_model.accepted@phase4bf_formal_candidate_model@sha256:<hash>
artifact_type: CANDIDATE_MODEL_ARTIFACT
component: Candidate AI
version: phase4bf_formal_candidate_model
physical_path: .runtime/candidate_ai/models/phase4bf_formal_candidate_model.pkl
content_hash: sha256:<hash>
accepted_status: ACCEPTED
runtime_use_eligible: true
path_policy: TEMPORARY_REGISTERED_PATH
```

Phase-numbered physical paths must not be used as logical identity.

## Accepted Status

Allowed statuses:

| Status | Meaning | Runtime use |
|---|---|---:|
| `DRAFT` | Produced but not validated. | No |
| `VALIDATED` | Schema/hash checks passed, but not accepted. | No |
| `ACCEPTED` | Approved by acceptance authority for named consumers. | Yes, if all eligibility checks pass |
| `REJECTED` | Failed review or validation. | No |
| `LEGACY` | Historical artifact retained for evidence/migration only. | No |
| `REVOKED` | Previously accepted but explicitly banned. | No |

Runtime may use an artifact only when:

- registered in the Registry
- `accepted_status=ACCEPTED`
- `runtime_use_eligible=true`
- content hash matches
- schema hash/version matches
- physical path exists and is readable
- producer is allowed for the artifact type
- consumer is allowed for the artifact type
- point-in-time status is valid
- source refs and source hashes are present and valid
- artifact is not `LEGACY`, `REJECTED`, or `REVOKED`

Artifact existence alone never grants Runtime eligibility.

## Registry Update Authority

| Action | Allowed authority | Disallowed authority |
|---|---|---|
| Create DRAFT registration | Producer, migration tool, acceptance process | AI self-acceptance |
| Mark VALIDATED | Validation process / CI / human review | Runtime mainline without validation |
| Mark ACCEPTED | Human Review / Acceptance Process / Architecture-approved migration | Runtime job, AI job, feature producer alone |
| Register model/metrics artifact set | Acceptance Process | AI inference code |
| Mark LEGACY | Architecture-approved migration | Runtime job |
| Mark REVOKED | Human Review / Safety authority / Architecture owner | AI producer |
| Update physical path mapping | Architecture-approved migration | Runtime fallback |

Runtime may produce decision artifact registrations as `DRAFT` or `VALIDATED` evidence, but must not promote model, metrics, feature, or policy artifacts to `ACCEPTED`.

## Runtime Eligibility and Failure Behavior

| Condition | Default behavior | Notes |
|---|---:|---|
| Artifact unregistered | `HALT` for model/policy, `REVIEW_REQUIRED` for optional evidence | No silent fallback. |
| Accepted status missing | `HALT` for Runtime AI/control input | Artifact exists is insufficient. |
| Hash mismatch | `HALT` | Treat as integrity failure. |
| Schema mismatch | `REVIEW_REQUIRED` or `HALT` | `HALT` for model/control, `REVIEW_REQUIRED` for generated decisions before submit. |
| Model/Metrics set mismatch | `HALT` | Opportunity model and metrics must belong to same accepted set. |
| Legacy artifact referenced | `HALT` for Runtime input | Audit-only read is allowed. |
| Physical path missing | `HALT` for required model/policy, `REVIEW_REQUIRED` for missing decision before planning | Do not search nearby paths. |
| Consumer incompatible | `HALT` | Registry must name allowed consumers. |
| Decision artifact missing input hashes | `REVIEW_REQUIRED` | Planning may not proceed to Submit. |
| Safety artifact expired | `REVIEW_REQUIRED` or `HALT` per Safety contract | Submit must not proceed. |
| Registry event log write failure for generated decision artifact | `REVIEW_REQUIRED` | Planning, Pending generation, Submit, Current mutation, Ledger mutation, and new Pending consumption must not proceed. Preserve generated artifact as isolated evidence when possible. |
| Materialized index update failure for generated decision artifact | `REVIEW_REQUIRED` | Event/index inconsistency requires review before downstream Runtime action. |
| Model / policy / safety / authority integrity mismatch | `HALT` | Integrity or authority mismatch is not an audit-write problem and must not continue as normal review-only flow. |

Silent fallback is prohibited. Fallback, when explicitly allowed by a later design, must be named, bounded, logged, and review-required.

### Generated Decision Artifact Registration Failure

For generated Candidate, Opportunity, Position Management, and Capital Allocation Decision Artifacts, ordinary registration or audit failures are `REVIEW_REQUIRED`.

Examples:

- Registry event log write failure
- materialized index update failure
- Decision Artifact registration failure
- missing Decision Artifact source refs
- missing Decision Artifact input hashes

Required behavior:

- do not proceed to Planning
- do not generate new Pending
- do not proceed to Submit
- do not change Current
- do not change Ledger
- do not newly consume existing Pending
- preserve the generated artifact as isolated evidence when possible

### Integrity / Authority Failure

Integrity or authority failures are `HALT`.

Examples:

- model hash mismatch
- Model / Metrics Artifact Set mismatch
- code-policy hash mismatch
- Policy Artifact mismatch
- Safety Artifact mismatch
- authority mismatch
- Legacy / Revoked Artifact referenced as Runtime input

The boundary is strict: ordinary Registry write/update failure must not automatically become `HALT`, but integrity or authority mismatch must not continue as a mere `REVIEW_REQUIRED` flow.

## Model / Metrics Artifact Set

Model artifacts and metrics artifacts must not be selected independently.

### Opportunity Accepted Artifact Set

The Opportunity Artifact Set must include:

- `opportunity_artifact_set_id`
- Opportunity model artifact id
- Opportunity model version
- Opportunity model hash
- Opportunity metrics artifact id
- Opportunity metrics hash
- feature schema id/hash
- training metadata id/hash
- validation report id/hash
- accepted status
- allowed consumer: Opportunity AI Runtime producer

The current mismatch is closed by design:

```text
Runtime model: Phase5-P
metrics omitted fallback: Phase5-E
```

Design rule:

```text
Opportunity AI must load model and metrics from the same accepted Opportunity Artifact Set.
```

If metrics is omitted, Runtime must not fallback to Phase5-E. It must fail closed or review-required until a later implementation removes the fallback and loads the accepted set.

### Candidate Accepted Artifact Set

Candidate should also be registered as a set:

- candidate model artifact id
- model hash
- feature schema id/hash
- training summary id/hash
- validation report id/hash
- accepted status
- allowed consumer: Candidate AI Runtime producer

## PM Code Policy Registry

Position Management currently has no external model artifact. Therefore, its accepted identity is a Code Policy Set.

Required registration unit:

- `pm_code_policy_set_id`
- PM code-policy artifact id
- PM code hash
- Runtime adapter artifact id
- adapter hash
- `MODEL_VERSION`
- `FEATURE_VERSION`
- inference version
- accepted status
- allowed consumer: Runtime PM producer

PM Decision Artifact must reference:

- PM code-policy artifact id
- PM code-policy hash
- Runtime adapter artifact id
- adapter hash
- feature artifact id/hash
- opportunity artifact id/hash
- Current artifact/state hash

## Decision Artifact Hash Contract

Candidate, Opportunity, and PM Decision Artifacts must record enough evidence to reproduce and audit their output.

Required fields:

- `artifact_instance_id`
- `artifact_type`
- `schema_version`
- `business_date`
- `feature_date`
- `as_of`
- `generated_at`
- `producer`
- `producer_version`
- `artifact_hash`
- `input_artifact_refs`
- `input_hashes`
- `model_artifact_refs` or `code_policy_artifact_refs`
- `model_hashes` or `code_policy_hashes`
- `source_registry_snapshot_id`
- `point_in_time_status`

Prohibited:

- missing source refs
- missing input hashes
- missing model/code-policy hash
- unknown schema
- unknown producer
- hidden model fallback
- unregistered legacy input

## Registry Storage Options

| Option | Atomicity | Append-only auditability | Human readability | Queryability | Migration | Hash verification | Concurrency | Rollback | Production suitability |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Single JSON registry | Medium | Low | High | Low | Medium | Medium | Low | Low | Low-Medium |
| JSONL append-only registry | Medium | High | High | Medium | High | High | Medium | High | Medium-High |
| SQLite registry | High | Medium unless event-sourced | Low-Medium | High | Medium | High | High | Medium | High |
| Manifest-per-artifact + central index | Medium | Medium-High | High | Medium | High | High | Medium | Medium | Medium-High |

Recommended design:

```text
append-only JSONL registry event log
↓
materialized central index
↓
optional SQLite query index for Production operations
```

Phase16 initial implementation prerequisite:

```text
append-only JSONL registry event log
materialized JSON central index
```

SQLite status:

```text
OPTIONAL_LATER
```

SQLite is only a later candidate when Production operations need stronger query performance or operational usability. It is not a Phase16 initial Registry prerequisite. Registry completion must not be interpreted as requiring JSONL, JSON index, and SQLite to be implemented at the same time.

Rationale:

- append-only history preserves auditability
- materialized index keeps Runtime checks fast
- SQLite can be introduced later without changing the logical contract
- rollback means revoking or superseding entries, not deleting history
- initial implementation should avoid overengineering and stay limited to JSONL plus materialized JSON index

This document recommends the logical storage pattern but does not implement it.

## Physical Path Policy

Registry is logical authority. Physical path is storage location.

Path classifications:

| Classification | Meaning | Runtime use |
|---|---|---:|
| `ACCEPTED_PERMANENT_PATH` | Permanent operational path accepted by architecture. | Allowed if Registry checks pass |
| `TEMPORARY_REGISTERED_PATH` | Current physical path registered under permanent logical identity while migration is pending. | Allowed only with migration deadline/review |
| `MIGRATION_REQUIRED` | Path contains Phase number or non-permanent location and must move or be remapped. | Conditional |
| `LEGACY_ONLY` | Evidence only; cannot be Runtime input. | No |

Phase-numbered physical paths may be temporarily registered, but that does not make the path permanent and does not promote the Phase artifact itself to Source of Truth.

## Retention and Immutability

| Artifact | Retention / immutability |
|---|---|
| Accepted Model Artifact | Immutable; never overwrite in place. |
| Accepted Metrics Artifact | Immutable; never overwrite in place. |
| Accepted Code Policy Artifact | Immutable hash identity; code changes create new artifact instance. |
| Accepted Feature Artifact | Immutable for a given business/feature date and source refs. |
| Decision Artifact | Append-only / immutable; corrections produce new artifacts with supersedes refs. |
| Registry history | Append-only audit trail. |
| Legacy Artifact | Read-only evidence. |
| Revoked Artifact | Do not delete; mark unusable. |

## Failure / Fallback Policy

Silent fallback is prohibited.

Specific rules:

- Unregistered model: `HALT`
- Unregistered metrics: `HALT` for Opportunity AI
- Opportunity model/metrics set mismatch: `HALT`
- Candidate feature unregistered: `REVIEW_REQUIRED` before inference
- Decision artifact missing source hashes: `REVIEW_REQUIRED`
- Legacy artifact used as Runtime input: `HALT`
- Physical path missing: `HALT` for required model/policy, `REVIEW_REQUIRED` for generated decision dependency
- Schema mismatch: `REVIEW_REQUIRED` before planning; `HALT` before submit if unresolved
- Consumer incompatible: `HALT`
- Generated Decision Artifact registration or audit-write failure: `REVIEW_REQUIRED`; Planning, Pending generation, Submit, Current mutation, Ledger mutation, and new Pending consumption must not proceed.
- Integrity / authority mismatch: `HALT`; this includes model hash mismatch, model/metrics set mismatch, code-policy hash mismatch, policy/safety artifact mismatch, authority mismatch, and Legacy/Revoked Runtime input.

Existing Opportunity metrics fallback is a migration target. It must not be treated as accepted behavior in this architecture.

## Capital Allocation Contract

Capital Allocation is not AI in Runtime v2. It is an Allocation / Policy layer.

Role:

```text
Allocate capital, quantity, cash buffer, and position limits
to accepted Opportunity / Policy-approved symbols.
```

It decides:

- investment amount
- target quantity
- cash buffer
- effective symbol/order count limit
- position exposure limit
- per-position weight limit
- rejection or skip reason due to allocation constraints

It must not decide:

- Candidate score
- Opportunity score
- PM score
- Safety release
- Submit authority
- Broker order result
- Current mutation
- model/metrics selection

### Capital Allocation Inputs

Required inputs:

- Opportunity Decision Artifact
- Capital Allocation Policy Artifact
- Policy Artifact, if separate from allocation policy
- Safety Decision Artifact
- Current state
- available cash
- buying power
- existing positions
- current exposure
- portfolio constraints
- lot size / trading unit
- business date
- as_of / valuation_as_of

Allowed Current fields:

- cash
- buying_power
- total_equity / market_value when available
- positions
- position quantity
- average price
- current price
- market value
- current exposure
- position_state_as_of
- valuation_as_of
- current freshness/status fields

Current fields must be read from Runtime-owned Current, not Broker-only snapshots.

### Capital Allocation Outputs

Capital Allocation Decision Artifact must include:

- `schema_version`
- `business_date`
- `as_of`
- `generated_at`
- `allocation_decision_id`
- `policy_artifact_ref`
- `policy_hash`
- `safety_artifact_ref`
- `safety_hash`
- `current_ref`
- `current_hash`
- `opportunity_decision_ref`
- `opportunity_decision_hash`
- `input_refs`
- `input_hashes`
- `symbol`
- `side`
- `allocated_capital`
- `target_quantity`
- `estimated_price`
- `cash_required`
- `cash_reserve`
- `position_limit`
- `effective_order_limit`
- `rejection_reason`
- `policy_context`

### Capital Allocation Policy Artifact

The policy artifact defines reusable rules:

- policy version
- policy source
- evaluation capital
- target investment ratio
- cash buffer
- max exposure
- max position weight
- max positions
- min order amount
- max buy order amount
- max sell liquidation amount
- buy notional policy
- sell liquidation policy
- manual review threshold
- lot / quantity constraints

Current implementation evidence: `runtime_v2.policy.capital_deployment.CapitalDeploymentPolicy` already validates these fields and exposes a stable policy hash.

### Capital Allocation Decision Artifact

The decision artifact is the business-date result of applying the policy to accepted Opportunity/Safety/Current inputs.

Current implementation evidence:

- `CapitalAllocationSignal` carries allocation id, symbol, side, amount, cash required, price evidence, policy version/source, and policy context.
- Morning Planning derives planning budget from target investment ratio, cash buffer, max exposure, available cash, max position weight, max positions, and max buy order amount.
- Sell Planning allocates SELL quantity from Runtime-owned Current position valuation.

Current gap:

- There is no standalone registered Capital Allocation Decision Artifact yet. Planning embeds allocation signals in OrderPlan/Pending evidence.

### Capital Allocation Artifactization Stages

Standalone Capital Allocation Decision Artifact must not immediately replace current Planning authority. Capital Allocation artifactization is staged:

| Stage | Scope | Authority rule |
|---|---|---|
| Stage 1 | Register Capital Allocation Policy Artifact with policy version, hash, schema, and accepted status. | Runtime Planning behavior does not change. |
| Stage 2 | Record current `CapitalAllocationSignal` as evidence with input refs, input hashes, policy refs, and Current hash. | Evidence only; standalone decision artifact is not Planning input authority. |
| Stage 3 | Read-only compare current Planning result against standalone Capital Allocation Decision Artifact candidate. | No dual authority; comparison is audit-only. |
| Stage 4 | Consider standalone Capital Allocation Decision Artifact adoption only after Semantic Equality Gate passes and a separate Acceptance approves it. | No silent fallback between old signal and new artifact. |

Minimum Semantic Equality Gate fields:

- symbol
- allocated capital
- target quantity
- cash reserve
- position limit
- rejection reason
- Planning output
- Pending output

Prohibited during artifactization:

- immediate replacement of existing Planning behavior
- expansion of Capital Allocation authority
- dual authority with Planning
- silent fallback between current `CapitalAllocationSignal` and a standalone artifact

## Producer / Consumer Matrix

| Artifact | Producer | Consumer | Authority | Runtime-use eligible | Accepted status required |
|---|---|---|---|---:|---:|
| Candidate Feature | Feature Refresh | Candidate AI | Feature producer | Yes | Yes |
| Candidate Model | Candidate AI training/acceptance | Candidate AI | Acceptance Process | Yes | Yes |
| Candidate Decision | Runtime buy_ai producer | Opportunity AI, audit | Candidate AI producer | Yes | Generated decision must be registered/validated |
| Opportunity Feature | Feature Refresh | Opportunity AI | Feature producer | Yes | Yes |
| Opportunity Model | Opportunity AI training/acceptance | Opportunity AI | Acceptance Process | Yes, as set | Yes |
| Opportunity Metrics | Opportunity AI training/acceptance | Opportunity AI | Acceptance Process | Yes, as set | Yes |
| Opportunity Decision | Runtime buy_ai producer | Planning, Capital Allocation | Opportunity AI producer | Yes | Generated decision must be registered/validated |
| Position Feature | Feature Refresh | Position Management | Feature producer | Yes | Yes |
| PM Code Policy | PM code acceptance | PM producer | Acceptance Process | Yes | Yes |
| PM Decision | Runtime PM producer | Sell Planning | PM producer | Yes | Generated decision must be registered/validated |
| Capital Allocation Policy | Human/Policy acceptance | Allocation layer, Planning | Human/Acceptance Process | Yes | Yes |
| Capital Allocation Decision | Allocation layer | Planning, Pending, Audit | Allocation producer | Yes | Generated decision must be registered/validated |
| Policy | Human/Policy acceptance | Planning, Pending, Submit Guard | Policy authority | Yes | Yes |
| Safety | Safety producer | Planning, Pending, Submit Guard | Safety authority | Yes within freshness | Yes/valid freshness |
| Pending | Planning/Pending writer | Approval, Submit Guard | Runtime Pending authority | Registry target: No | Not applicable |

Pending is not an AI Artifact Registry target because it is Runtime authority state, not an AI/data/control artifact selected by the Registry. Pending must reference registered upstream artifacts and policy/safety hashes, but its active slot authority remains Runtime v2.

## Mode Independence

Production, Demo, Paper, and Historical must share the same Registry contract.

Forbidden:

- `historical_registry`
- `backtest_model_registry`
- `phase16_registry`
- `demo_ai_registry`

Mode differences must be represented through artifact instance metadata:

- `business_date`
- `feature_date`
- `as_of`
- `broker_environment`
- `runtime_mode`
- `producer`
- `consumer`
- `point_in_time_status`

## Current Implementation Gaps

| Area | Judgment | Reason |
|---|---:|---|
| Candidate model registration | DESIGN_ACCEPTED_IMPLEMENTATION_REQUIRED | Logical set and hash contract defined; central registry not implemented. |
| Candidate decision hash | DESIGN_ACCEPTED_IMPLEMENTATION_REQUIRED | Current output records paths but not full registry hash contract. |
| Opportunity model/metrics set | MIGRATION_REQUIRED | Current default model and omitted metrics fallback can come from different Phase lineages. |
| Opportunity fallback | MIGRATION_REQUIRED | Silent Phase5-E metrics fallback must be removed or replaced by accepted set lookup. |
| Opportunity decision hash | DESIGN_ACCEPTED_IMPLEMENTATION_REQUIRED | Full source/model/metrics hash contract not enforced. |
| PM code-policy registration | DESIGN_ACCEPTED_IMPLEMENTATION_REQUIRED | PM code/adapter hashes must be registered as accepted code-policy set. |
| PM decision hash | DESIGN_ACCEPTED_IMPLEMENTATION_REQUIRED | PM decision must include code-policy/adapter/input hashes. |
| Capital Allocation contract | DESIGN_ACCEPTED_IMPLEMENTATION_REQUIRED | Policy fields exist; formal policy/decision artifact split must be implemented. |
| Capital Allocation artifact | DESIGN_ACCEPTED_IMPLEMENTATION_REQUIRED | Allocation signal exists; standalone registered decision artifact does not. |
| Central Registry | DESIGN_ACCEPTED_IMPLEMENTATION_REQUIRED | Logical design accepted; no implementation in this phase. |
| Phase-numbered paths | MIGRATION_REQUIRED | May be temporary registered paths, not permanent logical identity. |

## Migration Principles

- Do not promote Phase-numbered artifacts to Source of Truth by path.
- Register logical identities before moving files.
- Use accepted artifact sets for model/metrics combinations.
- Revoke or legacy-mark unsafe artifacts rather than deleting history.
- Preserve feature schema, model behavior, and Runtime mainline unless a later explicit phase authorizes changes.
- Keep Registry read-only for Runtime decisions except generated decision registration events.
- Do not let Runtime fallback search for replacement artifacts.

## Acceptance Criteria

This design is accepted when:

- Registry purpose is defined.
- Registry authority is limited to Artifact Identity and Runtime Eligibility and separated from trading authority.
- Guarantees and non-guarantees are explicit.
- Artifact types are classified.
- Artifact identity separates logical identity from physical path.
- Accepted status and Runtime eligibility are defined.
- Model / Metrics Artifact Set is defined.
- PM Code Policy registration is defined.
- Decision Artifact hash contract is defined.
- Registry storage options are compared.
- Physical Path policy is defined.
- Silent fallback is prohibited.
- Capital Allocation role, input, output, and authority boundary are defined.
- Capital Allocation Policy and Decision Artifacts are defined.
- Capital Allocation artifactization stages and Semantic Equality Gate are defined.
- Producer / Consumer Matrix is provided.
- Production, Demo, Paper, and Historical share the same contract.
