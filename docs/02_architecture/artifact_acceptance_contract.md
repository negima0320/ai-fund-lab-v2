# Artifact Acceptance Contract

Status: Phase16-R accepted design

This document defines the Artifact Acceptance Workflow for AI Fund Lab v2. It applies to Production, Demo, Paper, and Historical operation. It is not a Phase16-only workflow and it is not a Registry implementation plan.

Related contracts:

- `docs/02_architecture/ai_artifact_registry_and_capital_allocation_contract.md`
- `docs/02_architecture/artifact_path_registry_integration_and_migration_contract.md`
- `docs/02_architecture/operational_lifecycle_state_reset_and_environment_transition_contract.md`

## Purpose

Artifacts may be inventoried and technically validated before they are safe for Runtime use. This contract defines how an artifact or artifact set moves from:

```text
VALIDATED
↓
ACCEPTED
```

The goal is to prevent Runtime, AI, Registry, or CLI code from silently promoting artifacts into production use without review, regression evidence, and an auditable acceptance record.

## Scope

This contract defines:

- Artifact Lifecycle
- Artifact Promotion
- Acceptance Authority
- Acceptance Evidence
- Acceptance Criteria
- Acceptance Gate
- Artifact Review
- Regression Requirement
- Rollback
- Revoke
- Replacement
- Runtime use conditions

This contract does not implement the Registry, move artifacts, change Runtime consumers, generate artifacts, run Simulation, run Historical Test, or promote any existing artifact.

## Artifact Lifecycle

Allowed lifecycle statuses:

| Status | Meaning | Who can change to this status | Runtime use | Registry state |
|---|---|---|---:|---|
| `DRAFT` | Artifact exists or is proposed, but identity, schema, hash, producer, and consumer are not fully validated. | Producer tooling, inventory tooling, reviewer draft event. | No | Append-only draft event or inventory candidate. |
| `VALIDATED` | Hash, schema, physical existence, producer, consumer, and artifact-set consistency checks passed. Acceptance review has not approved Runtime use. | Validation tooling may propose; reviewer may confirm. | No | Registered or candidate record with validation evidence. |
| `REVIEW_REQUIRED` | Validation found a gap, risk, missing evidence, or human decision point. | Validation tooling may propose; reviewer may confirm. | No | Registered record remains blocked with reasons. |
| `ACCEPTED` | Human acceptance authority approved the artifact or artifact set for named Runtime consumers after review and regression gates. | Human Review plus Architecture Acceptance plus Regression Acceptance plus Release Approval. | Yes, only when `runtime_use_eligible=true` and all integrity checks pass. | Registry records immutable acceptance event and acceptance report reference. |
| `LEGACY` | Previously accepted or known artifact retained for evidence, rollback reference, audit, or migration history. It is no longer the active Runtime artifact. | Acceptance authority through replacement workflow. | No by default. Temporary rollback may re-accept a specific legacy instance through a new acceptance event. | Registry records superseded-by relationship. |
| `REVOKED` | Artifact is explicitly banned due to correctness, safety, lineage, schema, leakage, security, or review failure. | Acceptance authority, emergency safety authority with follow-up review. | No, never. | Registry records revoke event, reason, reviewer, and affected consumers. |

Optional terminal status:

| Status | Meaning | Runtime use |
|---|---|---:|
| `REJECTED` | Artifact failed review before acceptance and is retained only as evidence. | No |

`REJECTED` is optional because many failed candidates can remain `REVIEW_REQUIRED` with blocking reasons. `REVOKED` is reserved for artifacts that must be actively prohibited.

## State Transition Rules

Allowed transitions:

```text
DRAFT -> VALIDATED
DRAFT -> REVIEW_REQUIRED
DRAFT -> REJECTED
VALIDATED -> REVIEW_REQUIRED
VALIDATED -> ACCEPTED
VALIDATED -> REJECTED
REVIEW_REQUIRED -> VALIDATED
REVIEW_REQUIRED -> REJECTED
ACCEPTED -> LEGACY
ACCEPTED -> REVOKED
LEGACY -> ACCEPTED
LEGACY -> REVOKED
```

Rules:

- `ACCEPTED` is never created automatically.
- `REVOKED` cannot transition back to `ACCEPTED`. A corrected artifact must be a new artifact instance with a new hash and acceptance record.
- `LEGACY -> ACCEPTED` is allowed only for rollback through a new acceptance event and regression gate.
- Status changes are append-only events. Registry event deletion is prohibited.
- Physical file replacement in-place is prohibited for accepted artifacts. A new file hash means a new artifact instance.
- A Limited Registry Recovery Transaction is not ordinary acceptance, replacement, rollback, or revoke. It is permitted only under the Registry recovery contract when incomplete acceptance-attempt events were never used as Runtime authority and the removed event bodies remain permanently auditable.

## Acceptance Authority

Only the combined acceptance authority may promote an artifact to `ACCEPTED`:

| Authority | Responsibility |
|---|---|
| Human Review | Confirms intent, evidence completeness, known risks, and operational suitability. |
| Architecture Acceptance | Confirms the artifact fits the architecture, Source of Truth, lifecycle, and consumer boundaries. |
| Regression Acceptance | Confirms required regression gates passed and results are attached. |
| Release Approval | Confirms the accepted artifact may become Runtime-eligible in the target environment. |

The following must never self-promote to `ACCEPTED`:

- Runtime
- AI producers
- Registry code
- CLI commands
- Batch jobs
- Feature generators
- Simulation / backtest tools
- Report generators

They may produce `DRAFT`, `VALIDATED`, or `REVIEW_REQUIRED` evidence. They cannot create final acceptance authority by themselves.

## Runtime Use Conditions

Runtime may use an artifact only when all conditions are true:

- `accepted_status=ACCEPTED`
- `runtime_use_eligible=true`
- artifact instance hash matches the Registry record
- schema hash or schema version matches the Registry record
- artifact set hash matches when the artifact belongs to a set
- physical path exists and is readable
- producer is allowed for the artifact type
- consumer is allowed for the artifact type
- business date / feature date / as-of contract is satisfied
- artifact is not `LEGACY`, `REVOKED`, `REJECTED`, `DRAFT`, `VALIDATED`, or `REVIEW_REQUIRED`

Exceptions:

- Runtime authority state such as Current, Ledger, Pending, Execution, and Runtime State is not governed as an accepted AI artifact. These remain Runtime authorities.
- Safety decisions may be consumed under their separate freshness and safety contract, but if registered as artifacts they still must not claim `ACCEPTED` without this workflow.
- Emergency operator intervention may stop Runtime from using an artifact, but cannot promote another artifact to `ACCEPTED` without a follow-up acceptance event.

### ACCEPTED_CURRENT_PATH Authority Mode

`ACCEPTED_CURRENT_PATH` is allowed only when the permanent Runtime execution source path itself is the accepted artifact member. It is not a test-only shortcut and it is not a manual Registry override.

Required acceptance evidence:

- physical source path
- git commit
- SHA-256 content hash
- schema or source classification evidence
- behavior/regression evidence
- consumer compatibility evidence
- release approval

Runtime preflight must compare the accepted physical path and accepted content hash with the actual executing source before use. A path or hash mismatch must halt with a fail-closed Runtime artifact lookup error. Source changes require a new acceptance event and a new active artifact set; the previous accepted set must become `LEGACY` through the append-only replacement workflow. The same accepted authority applies to Historical, Demo, and Production consumers.

## Acceptance Criteria

All artifact types require:

- content hash verified
- schema hash or schema version verified
- artifact instance ID stable
- logical artifact ID stable
- physical path recorded
- producer identified
- consumer identified
- source artifacts and source hashes recorded when applicable
- runtime-use eligibility scoped to named consumers
- point-in-time fields checked when applicable
- review evidence attached
- regression evidence attached
- rollback/replacement plan recorded
- revoke impact known

### Candidate Artifact Set

Required to accept:

- Candidate model hash verified.
- Candidate model manifest hash and schema verified.
- Candidate feature schema expected by the model recorded.
- Training metadata exists and is linked.
- Validation evidence exists and is linked.
- Producer is Candidate AI training acceptance.
- Consumers are Candidate Model Loader and Opportunity AI.
- Artifact Set manifest hash is stable.
- Candidate inference semantic equality regression passes.
- Runtime consumer path change, if any, does not change Candidate scores.
- Point-in-time feature contract is reviewed.
- No training artifact is treated as a direct Runtime input.

### Opportunity Artifact Set

Required to accept:

- Opportunity model hash verified.
- Opportunity metrics hash and schema verified.
- Model and metrics pair is explicitly bound.
- Training evidence exists and is linked.
- Validation evidence exists and is linked.
- Producer is Opportunity AI training acceptance.
- Consumers are Opportunity Model Loader, Metrics Loader, and Morning Planning.
- Artifact Set manifest hash is stable.
- Opportunity ranking semantic equality regression passes.
- Phase5-E silent fallback is removed, rejected, or explicitly blocked by accepted-set lookup before production Runtime use.
- Point-in-time feature and Candidate-decision input contract is reviewed.

### Position Management Artifact Set

Required to accept:

- PM code-policy source hash verified.
- Runtime adapter source hash verified.
- If `RUNTIME_ADAPTER` uses `ACCEPTED_CURRENT_PATH`, the accepted source path must be the actual Runtime PM producer source, and Runtime must hash-check it before PM inference.
- If an accepted current-path Runtime adapter source changes in Production common code, the change is not Runtime-accepted until the formal Artifact Generation, Validation, Acceptance, Registry index, and checkpoint refresh are completed. Unit tests that bypass Registry authority are not sufficient acceptance evidence.
- Code-policy manifest hash is stable.
- Producer is PM code acceptance and Runtime adapter acceptance.
- Consumers are PM Producer and Sell Planning.
- Decision output contract is reviewed.
- PM decision parity regression passes.
- Current / Ledger / Pending authority boundaries remain unchanged.
- No hidden liquidation or cleanup authority is introduced.

### Capital Allocation Policy Artifact Set

Required to accept:

- Policy JSON hash verified.
- Policy schema verified.
- Policy version and owner recorded.
- Producer is human/policy acceptance.
- Consumers are Planning and Submit Guard.
- Artifact Set or policy manifest hash is stable.
- Planning/Pending/Submit Guard regression passes.
- Evaluation capital, cash buffer, max order amount, max positions, and exposure semantics are reviewed.
- Standalone Capital Allocation Decision Artifact requirement is either accepted as deferred or explicitly defined.

## Acceptance Gate

An artifact or artifact set may move to `ACCEPTED` only when every gate passes:

| Gate | Required result |
|---|---|
| Identity Gate | logical ID, instance ID, physical path, hash, schema, type, component are stable. |
| Lineage Gate | producer, source refs, source hashes, training/validation evidence are complete. |
| Consumer Gate | every intended consumer is named and compatible. |
| Runtime Eligibility Gate | `runtime_use_eligible=true` is scoped to exact consumer(s). |
| Point-in-Time Gate | no look-ahead, future data, future listed status, or future corporate action misuse. |
| Regression Gate | required regression suite passes. |
| Review Gate | human/architecture/regression/release approvals exist. |
| Rollback Gate | rollback or replacement path is documented. |
| Revoke Gate | revoke impact and deny-list behavior are documented. |

Any failed gate results in `REVIEW_REQUIRED` or `REJECTED`, not `ACCEPTED`.

## Regression Requirement

Minimum regression before `ACCEPTED`:

- Semantic Equality: same input produces same output before and after Registry lookup or path migration.
- Current unchanged: Current authority file and interpretation do not change.
- Ledger unchanged: Ledger records and replay interpretation do not change.
- Pending unchanged: Pending slot, approval linkage, and submit guard interpretation do not change.
- Planning unchanged: order candidates, sizing, policy context, and no-signal behavior remain equivalent unless the artifact change intentionally changes AI output and is approved.
- Runtime unchanged: Runtime state machine and job exit semantics remain unchanged.
- Feature unchanged: feature schema and feature calculation remain unchanged unless the accepted artifact is a feature artifact and the change is explicitly approved.
- AI unchanged: model inference output remains equivalent for path/Registry-only migration.
- Report unchanged: reports may include additional artifact references, but must not change Runtime authority.

For model replacement, semantic equality is not expected against the old model. Instead, acceptance requires:

- fixed validation dataset result evidence
- approved performance deltas
- safety and downside review
- regression proving Runtime integration behavior remains correct

## Review Workflow

Formal workflow:

```text
Artifact generation
↓
Read-only inventory
↓
DRAFT Registry event candidate
↓
Validation
↓
VALIDATED
↓
Human and architecture review
↓
Regression gate
↓
Acceptance report
↓
ACCEPTED event
↓
Runtime-use eligibility enabled for named consumers
```

Rules:

- Inventory does not imply acceptance.
- Validation does not imply acceptance.
- Review does not imply Runtime use until the `ACCEPTED` event is recorded.
- The acceptance report must be immutable after the acceptance event.
- If evidence changes after acceptance, a new artifact instance or superseding event is required.

## Acceptance Report

Every `ACCEPTED` event must reference an acceptance report containing:

- reviewer name or reviewer ID
- review timestamp
- acceptance authority roles
- artifact logical ID
- artifact instance ID
- artifact type
- artifact set ID, when applicable
- physical path
- content hash
- schema hash or schema version
- producer
- producer version
- consumer list
- runtime-use eligibility scope
- source artifact refs and hashes
- business date / feature date / as-of fields when applicable
- regression command(s)
- regression result(s)
- Runtime version
- Git commit
- environment scope
- known risks
- rollback plan
- replacement plan
- revoke conditions
- review decision

The report must be stored as persistent operational foundation and must not be deleted by Trading State Reset.

## Promotion Workflow

Promotion to `ACCEPTED` is a Registry event, not a file mutation.

Required promotion event fields:

- event type: `ARTIFACT_ACCEPTED`
- previous status
- new status: `ACCEPTED`
- artifact instance ID
- artifact set ID when applicable
- reviewer / authority fields
- acceptance report path and hash
- runtime-use eligible consumers
- effective-from timestamp
- supersedes artifact instance ID, when applicable
- rollback candidate, when applicable

The Registry records the acceptance event and materializes the index. Runtime may consume only after the index exposes `accepted_status=ACCEPTED` and `runtime_use_eligible=true` for the named consumer.

## Replacement

When a new artifact version replaces an accepted one:

```text
new artifact -> DRAFT -> VALIDATED -> ACCEPTED
old artifact -> LEGACY
```

Rules:

- The new artifact must complete the full acceptance workflow.
- The old artifact is not deleted.
- The old artifact receives a `LEGACY` event with `superseded_by`.
- Runtime must not use `LEGACY` artifacts unless rollback creates a new acceptance event.
- Reports must show both previous and new artifact IDs.
- Replacement must include regression comparing Runtime integration behavior.

## Rollback

Rollback restores Runtime eligibility to a previously accepted artifact by new event, not by deleting Registry history.

Allowed rollback flow:

```text
current ACCEPTED artifact -> REVOKED or LEGACY
previous LEGACY artifact -> ACCEPTED through rollback acceptance event
```

Rollback requires:

- rollback reason
- reviewer / release approval
- previous artifact hash re-verification
- schema compatibility check
- consumer compatibility check
- minimal regression gate
- explicit effective-from timestamp
- impact report

Emergency rollback may be expedited but must still produce a follow-up acceptance report before continued operation.

## Revoke

Move an artifact to `REVOKED` when any of the following is confirmed:

- hash mismatch
- schema mismatch
- wrong producer
- wrong consumer
- look-ahead leakage
- future listed status misuse
- future corporate action misuse
- incorrect model/metrics pair
- silent fallback to unaccepted artifact
- corrupted file
- security or secret exposure
- unsafe Runtime behavior
- acceptance evidence falsified or incomplete
- human review explicitly rejects continued use

Rules:

- Runtime must never use a `REVOKED` artifact.
- Registry lookup must fail closed for revoked artifacts.
- A revoked artifact cannot become accepted again.
- Corrected output must be a new artifact instance.
- Revoke events must include reason, reviewer, timestamp, affected consumers, and replacement or halt guidance.

## Runtime Authority Impact

This acceptance workflow does not change:

- Runtime Authority
- Current
- Ledger
- Pending
- Execution
- Runtime State
- State Machine
- Feature calculation
- AI inference
- Planning logic
- Submit Guard
- Broker behavior

The Registry and acceptance workflow identify which artifacts may be used. They do not decide trades, mutate Current, rewrite Ledger, create Pending, or bypass Safety.

## Unresolved Items

- Formal Registry implementation remains future work.
- Exact acceptance event JSON schema remains future work.
- Exact acceptance report template remains future work.
- Corporate Action acceptance requires a separate design decision: adjusted OHLCV only or standalone event table.
- Opportunity Phase5-E fallback must be removed, blocked, or explicitly handled before production acceptance of the Opportunity artifact set.
- Historical Runtime feature source acceptance requires canonical point-in-time data contract completion.

## Implementation Boundary

After this contract is accepted, a later phase may design Registry production implementation. That later phase must still avoid promoting artifacts to `ACCEPTED` until this workflow, evidence, and regression gates are operational.

## Phase16-AJ Amendment

Phase16-AJ resolves the earlier open item "Exact acceptance event JSON schema remains future work" for pre-Acceptance design purposes by adding schema fields and machine-readable compatibility contracts.

Additions:

- `artifact_acceptance_role_compatibility.v1.json` defines formal Artifact Set Types, required member roles, required approval roles, role omission policy, same-reviewer policy, runtime eligibility preconditions, and cross-field rule names.
- `artifact_acceptance_evidence_bundle.schema.json` defines the evidence bundle that binds Artifact Set Manifest, Acceptance Report, Regression Evidence, four approval roles, lineage, freeze manifest, compatibility evidence, and rollback target.
- `artifact_acceptance_validation_result.schema.json` defines Acceptance-specific validation output.

Formal Set Types are:

```text
CANDIDATE_AI_SET
OPPORTUNITY_AI_SET
POSITION_MANAGEMENT_POLICY_SET
CAPITAL_ALLOCATION_POLICY_SET
FEATURE_SCHEMA_SET
SAFETY_POLICY_SET
```

The older `*_ACCEPTED_SET` names are compatibility aliases only. Future Acceptance Writer output must use the formal Set Types.
