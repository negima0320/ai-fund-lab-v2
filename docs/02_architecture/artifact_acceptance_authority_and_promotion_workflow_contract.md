# Artifact Acceptance Authority and Promotion Workflow Contract

## Purpose

This contract defines how AI Fund Lab v2 promotes an artifact or artifact set from `VALIDATED` to `ACCEPTED`.

`ACCEPTED` means:

- human formal adoption;
- architecture compatibility;
- regression compatibility;
- release approval;
- artifact body, hash, schema, set membership, source lineage, and consumer compatibility are coherent.

Acceptance is not trading authority. Acceptance does not decide buy/sell, position sizing, safety release, submit permission, broker result, Current mutation, Ledger mutation, Pending mutation, or Runtime State mutation.

The following actors and tools must never auto-promote an artifact to `ACCEPTED`:

- Runtime;
- AI inference;
- Feature Producer;
- Registry automation alone;
- general CLI;
- backtest;
- simulation;
- Historical Runtime;
- report generator;
- scheduler.

## Scope

This contract covers:

- Acceptance Authority;
- Role-to-Artifact-Type Compatibility;
- Artifact Set requirements;
- Acceptance Evidence Bundle;
- evidence path policy;
- promotion workflow;
- formal registration order;
- `ARTIFACT_ACCEPTED` event requirements;
- future Acceptance Writer boundary;
- Runtime eligibility;
- replacement, rollback, revoke;
- failure classification;
- partial failure recovery;
- test plan;
- implementation plan.

This contract does not implement an Acceptance Writer, append Registry Events, promote artifacts, copy/move artifacts, create evidence paths, update schemas, switch Runtime consumers, or connect Runtime lookup.

## Artifact Type Classification

| Target | Classification | Notes |
|---|---|---|
| Candidate AI Artifact Set | `ACCEPTANCE_REQUIRED` | Runtime Candidate AI model use requires formal set acceptance. |
| Opportunity AI Artifact Set | `ACCEPTANCE_REQUIRED` | Model and metrics must be accepted as one set. Phase5-E metrics fallback is not acceptable. |
| Position Management Policy Artifact Set | `ACCEPTANCE_REQUIRED` | Code Policy plus Runtime Adapter, not an external model. |
| Capital Allocation Policy Artifact Set | `ACCEPTANCE_REQUIRED` | Policy acceptance does not change Planning behavior by itself. |
| Feature Schema Artifact | `ACCEPTANCE_REQUIRED` | Required before Registry-backed Runtime lookup because model inputs depend on schema. |
| Canonical Data Contract / Manifest | `VALIDATION_ONLY` until canonical data Registry authority is separately introduced. | Canonical data must be validated and frozen, but model/policy acceptance must not mutate canonical data. |
| Safety / Policy Artifact | `ACCEPTANCE_REQUIRED` when used as persistent Runtime policy; `VALIDATION_ONLY` for evidence reports. | Safety authority remains separate from Registry. |
| Generated Candidate Decision Artifact | `REGISTRATION_ONLY` for ordinary Runtime output. | Generated per-run evidence; not a reusable model/policy acceptance target. |
| Generated Opportunity Decision Artifact | `REGISTRATION_ONLY` for ordinary Runtime output. | Required as Planning input evidence once Runtime lookup exists. |
| Generated PM Decision Artifact | `REGISTRATION_ONLY` for ordinary Runtime output. | Generated from accepted code-policy set and inputs. |
| Capital Allocation Decision Artifact | `REGISTRATION_ONLY` initially; `ACCEPTANCE_REQUIRED` only if later adopted as reusable Planning authority. | Current `CapitalAllocationSignal` remains existing Planning evidence until Semantic Equality Gate passes. |
| Validation Evidence | `EVIDENCE_ONLY` | Supports acceptance; does not become Runtime eligible. |
| Regression Evidence | `EVIDENCE_ONLY` | Supports acceptance; does not become Runtime eligible. |
| Review Approval | `EVIDENCE_ONLY` | Supports acceptance; does not become Runtime eligible. |

## Role Compatibility

Approval roles are mandatory for reusable Runtime-use artifacts. A single operator may hold multiple roles in one-person operation, but each role must still be explicitly recorded as a separate approval role.

| Artifact Type / Set | HUMAN_REVIEW | ARCHITECTURE_ACCEPTANCE | REGRESSION_ACCEPTANCE | RELEASE_APPROVAL |
|---|---:|---:|---:|---:|
| Candidate AI Artifact Set | Required | Required | Required | Required |
| Opportunity AI Artifact Set | Required | Required | Required | Required |
| Position Management Policy Artifact Set | Required | Required | Required | Required |
| Capital Allocation Policy Artifact Set | Required | Required | Required | Required |
| Feature Schema Artifact | Required | Required | Required | Required |
| Canonical Data Contract / Manifest | Required for freeze | Required | Required for rebuild/parity | Required if Runtime source changes |
| Safety / Policy Artifact | Required | Required | Required | Required |
| Generated Candidate Decision Artifact | Optional / N/A | N/A | N/A | N/A |
| Generated Opportunity Decision Artifact | Optional / N/A | N/A | N/A | N/A |
| Generated PM Decision Artifact | Optional / N/A | N/A | N/A | N/A |
| Capital Allocation Decision Artifact candidate | Required if adopted | Required if adopted | Required if adopted | Required if adopted |
| Validation Evidence | Optional / N/A | N/A | N/A | N/A |
| Regression Evidence | Optional / N/A | N/A | N/A | N/A |
| Acceptance Report | Required reviewer identity | Required referenced approval | Required referenced approval | Required referenced approval |

Approval role omission is a `HALT` for `ARTIFACT_ACCEPTED`.

## Artifact Set Requirements

### Candidate AI Artifact Set

Required members:

- Candidate Model;
- Model Manifest;
- Feature Schema;
- Training Metadata;
- Training Data Lineage;
- Validation Evidence;
- Metrics / Evaluation Evidence;
- Runtime Consumer Compatibility;
- Model Hash;
- Schema Hash or explicit non-structural model schema review.

Current candidate evidence:

- Candidate model hash: `2ea75d14d3fe36828512d8e1fb0ac482798690c6594f22029c4d5b63c7fd6a02`.
- Candidate model manifest hash: `e64e15efc9da10b7b19039ff3ed2841f122a625cf46d7dbaa7d65385ee27e56c`.
- Candidate training artifact hash: `5734c3395bf28a9385b753130fa18953817cd8671784a0499f27b4358a526a6a`.
- Candidate validation artifact hash: `cdbe1930a9e1ea80be795009561b8da2137e2c5c26225da334995d2bf704155b`.
- Candidate manifest candidate set hash: not authoritative until formal Artifact Set Manifest is written under the Registry evidence path.

Acceptance blockers:

- formal Artifact Set Manifest under permanent evidence path is missing;
- feature schema member binding is not present in the candidate manifest;
- human, architecture, regression, and release approvals are missing;
- Acceptance Report is missing;
- real regression evidence for Candidate scoring parity and Runtime consumer compatibility is missing;
- permanent artifact path migration is not complete;
- pickle model schema requires explicit review acceptance because structural schema is not introspectable.

### Opportunity AI Artifact Set

Required members:

- Opportunity Model;
- Phase5-P Metrics;
- Feature Schema;
- Training Metadata;
- Training Data Lineage;
- Validation Evidence;
- Runtime Consumer Compatibility;
- Model Hash;
- Metrics Hash.

The Opportunity model and metrics must be accepted as a single Artifact Set. The formal set must bind:

```text
Phase5-P Model
+
Phase5-P Metrics
```

The following is prohibited:

```text
Phase5-P Model
+
Phase5-E Metrics fallback
```

Current opportunity evidence:

- Opportunity model hash: `140e350bd9b12bf0c595184587fa2a3bd74236e4bdf1818df481022980dd6acd`.
- Opportunity Phase5-P metrics hash: `8428f2327e77374743f69e2ebc956a97a9d718880ef2acfc26571f94d9fd9511`.
- Opportunity legacy Phase5-E fallback metrics hash observed in inventory: `3416d82a904609b1f1dec2112f1990ca537665b25ab73d63120dea353ee41fc4`.
- Opportunity training artifact hash: `5923c387f590807dcd9e88de4cb35bfb9b7e4682d01f69648133350a16901aed`.
- Opportunity validation artifact hash: `2fc8b3c2cab43734f6914944c54659e8e72c123bc5c68a9d731a7f64eec5a02d`.

Acceptance blockers:

- Phase5-E fallback remains a Runtime migration blocker;
- formal Artifact Set Manifest under permanent evidence path is missing;
- feature schema member binding is not present in the candidate manifest;
- human, architecture, regression, and release approvals are missing;
- Acceptance Report is missing;
- model/metrics same-set compatibility evidence is missing;
- real ranking and Planning/Pending unchanged regression evidence is missing;
- permanent artifact path migration is not complete;
- pickle model schema requires explicit review acceptance.

### Position Management Policy Artifact Set

Position Management is a deterministic policy/code boundary, not an external model.

Required members:

- Code Policy;
- Runtime Adapter;
- Policy Version;
- Feature Version;
- Code Hash;
- Adapter Hash;
- Behavior Contract;
- Regression Evidence;
- Runtime Consumer Compatibility.

Current PM evidence:

- PM code policy hash: `31fb8630fa1edb281a5e7067ec89677f98f564f21a5c2c5f09f938a5795b2c85`.
- PM Runtime adapter hash: `6ffa7da2b91f5fd5cfa76aa4c487e6e6cf5e1293ba929fe374abd61aaadb7d1b`.

Acceptance blockers:

- formal Artifact Set Manifest under permanent evidence path is missing;
- behavior contract and policy version evidence are missing;
- human, architecture, regression, and release approvals are missing;
- Acceptance Report is missing;
- PM behavior regression and Sell Planning unchanged evidence are missing;
- permanent artifact path policy must be reviewed because source paths are current code paths.

### Capital Allocation Policy Artifact Set

Required members:

- Capital Allocation Policy;
- Policy Schema;
- Policy Version;
- Policy Hash;
- Validation Evidence;
- Regression Evidence;
- Runtime Consumer Compatibility.

Current capital allocation evidence:

- Capital allocation policy hash: `d3e2a046fb4b56b3d78ff7c6913e456d59313e9f0f6be6969cb0c13a08b7fdcd`.
- Policy schema hash: `a287fdc70888939bd764ee85895cbe96ad2962cba7703209c64bfdfc262d13ce`.
- Alternate policy artifact hash observed in inventory: `11b6c77b296895a47b444a125826a6d31b162c4fac9a46ef6c71b1d2cf4973e7`.

Acceptance blockers:

- formal Artifact Set Manifest under permanent evidence path is missing;
- human, architecture, regression, and release approvals are missing;
- Acceptance Report is missing;
- Planning/Pending/Submit Guard semantic equality regression is missing;
- standalone Capital Allocation Decision Artifact adoption decision remains separate and must not change current behavior.

### Feature Schema Artifact

Required members:

- feature schema definition;
- feature producer version;
- schema hash;
- source data lineage;
- point-in-time / look-ahead validation evidence;
- consumer compatibility matrix for Candidate, Opportunity, PM, Capital Allocation input, as applicable;
- regression evidence proving unchanged generated feature columns and Runtime consumers.

Acceptance blockers:

- formal Feature Schema Artifact Set is not registered;
- consumer compatibility evidence is not complete;
- point-in-time validation evidence must be bound to the accepted feature schema.

## Acceptance Evidence Bundle

Each `ARTIFACT_ACCEPTED` event must reference an evidence bundle.

| Evidence | Schema | Proposed Path | Hash | subject_ref | Set Binding | Required | Expiry | Reuse |
|---|---|---|---|---|---|---|---|---|
| Artifact Set Manifest | `artifact_set_manifest.v1` | `.runtime/artifact_registry/evidence/manifests/{artifact_set_id}.json` | Required | artifact_set_id | Primary set definition | Required | No expiry unless artifact changes | Reusable only for same set hash |
| Acceptance Report | `artifact_acceptance_report.v1` | `.runtime/artifact_registry/evidence/acceptance/{acceptance_id}.json` | Required | artifact_set_id or logical_artifact_id | References all bundle members | Required | No expiry; invalidated by revoke | Not reusable across set hash changes |
| Regression Evidence | `artifact_regression_evidence.v1` | `.runtime/artifact_registry/evidence/regression/{regression_id}.json` | Required | artifact_set_id | References regression profile and result | Required | Expires on Runtime/consumer/feature schema change | Reusable only with same Runtime and set hash |
| Human Review Approval | `artifact_review_approval.v1` | `.runtime/artifact_registry/evidence/approvals/{approval_id}.json` | Required | artifact_set_id | Role `HUMAN_REVIEW` | Required | Expires by approval policy or artifact change | Not reusable across set hash changes |
| Architecture Acceptance Approval | `artifact_review_approval.v1` | `.runtime/artifact_registry/evidence/approvals/{approval_id}.json` | Required | artifact_set_id | Role `ARCHITECTURE_ACCEPTANCE` | Required | Expires by approval policy or architecture change | Not reusable across incompatible architecture |
| Regression Acceptance Approval | `artifact_review_approval.v1` | `.runtime/artifact_registry/evidence/approvals/{approval_id}.json` | Required | regression_id and artifact_set_id | Role `REGRESSION_ACCEPTANCE` | Required | Expires on Runtime/consumer change | Not reusable after regression input changes |
| Release Approval | `artifact_review_approval.v1` | `.runtime/artifact_registry/evidence/approvals/{approval_id}.json` | Required | artifact_set_id and release scope | Role `RELEASE_APPROVAL` | Required | Expires if release scope changes | Not reusable across releases unless explicitly scoped |
| Source / Lineage Manifest | `artifact_set_manifest.v1` or future lineage schema | `.runtime/artifact_registry/evidence/manifests/{lineage_id}.json` | Required | artifact_set_id | Source refs and source hashes | Required | No expiry unless source hash changes | Reusable by same set hash |
| Model / Policy Freeze Manifest | `artifact_set_manifest.v1` or future freeze schema | `.runtime/artifact_registry/evidence/manifests/{freeze_id}.json` | Required | artifact_set_id | Freeze evidence | Required | No expiry unless member changes | Reusable by same set hash |
| Runtime Consumer Compatibility Evidence | `artifact_validation_result.v1` or regression evidence | `.runtime/artifact_registry/evidence/regression/{compatibility_id}.json` | Required | consumer id and artifact_set_id | Consumer matrix | Required | Expires on consumer version change | Reusable only for same consumer version |
| Rollback Target | Acceptance Report field or manifest | `.runtime/artifact_registry/evidence/acceptance/{acceptance_id}.json` | Required if previous accepted exists | logical_artifact_id | Rollback plan | Required for replacement | No expiry while referenced artifact exists | Review required before reuse |

## Evidence Path Policy

Permanent machine-readable evidence paths are:

```text
.runtime/artifact_registry/evidence/acceptance/
.runtime/artifact_registry/evidence/regression/
.runtime/artifact_registry/evidence/approvals/
.runtime/artifact_registry/evidence/manifests/
```

Responsibilities:

```text
.runtime = machine-readable Operational Evidence
reports = human-readable Audit / Summary
docs = permanent Contract / Template
```

This contract does not create these paths. Path creation belongs to a later implementation phase.

## Promotion Workflow

Formal workflow:

```text
Artifact Inventory
↓
Copy to permanent Registry-controlled artifact/evidence path
↓
Verify copied bytes and hashes
↓
Logical Registration
↓
DRAFT Event
↓
Artifact / Set Validation
↓
VALIDATED Event
↓
Human Review
↓
Architecture Review
↓
Regression
↓
Regression Acceptance
↓
Release Approval
↓
Acceptance Report
↓
ARTIFACT_ACCEPTED Event
↓
Index Build
↓
Checkpoint
```

No step may invent missing evidence. The Acceptance Report must be the final bundle summary, not a substitute for missing approvals or regression evidence.

## Registration Order

The formal policy is option B:

```text
Permanent path Copy / Verify
↓
DRAFT / VALIDATED registration
↓
Acceptance
```

This aligns with the path migration contract:

```text
Copy
↓
Verify
↓
Register
↓
Cutover
↓
Legacy Freeze
```

Rationale:

- accepting a temporary or Phase-numbered path as Runtime-eligible creates migration ambiguity;
- content hash must be verified at the permanent path before Runtime eligibility;
- consumer cutover must occur after acceptance and checkpoint, not before.

Exception:

- A current source-code path may be accepted as an `ACCEPTED_CURRENT_PATH` only when architecture explicitly declares that source path to be the permanent operational artifact path. This exception requires Architecture Acceptance and Release Approval.

## Acceptance Event

The `ARTIFACT_ACCEPTED` event must include:

- `event_id`;
- `event_type=ARTIFACT_ACCEPTED`;
- `logical_artifact_id`;
- `artifact_instance_id`;
- `artifact_set_id`;
- `previous_status=VALIDATED` or `previous_status=LEGACY` for rollback;
- `new_status=ACCEPTED`;
- `runtime_use_eligible=true` only when eligibility conditions pass;
- `content_hash`;
- `schema_hash`;
- `authority_ref`;
- `review_ref`;
- `regression_ref`;
- `acceptance_report_ref`;
- `source_refs`;
- `consumer_compatibility`;
- `point_in_time_status`;
- `physical_path`;
- `artifact_type`;
- `component`;
- `producer`;
- `consumer`;
- `event_created_at`.

Set authority:

- For Candidate, Opportunity, PM, and Capital Allocation Policy, the Artifact Set is the acceptance authority unit.
- Member hashes are evidence inside the set manifest and acceptance report.
- Member-level events may record registration and validation, but must not create separate Runtime eligibility authority that conflicts with the set.
- Runtime eligibility for model/policy use is resolved from the accepted set entry, not from independent member acceptance.

This avoids double authority between a model member and the set that binds model, metrics, schema, and evidence.

## Acceptance Writer Boundary

A future Acceptance Writer should be a separate component from the existing DRAFT/VALIDATED Event Log Writer.

Allowed responsibilities:

- read Acceptance Evidence;
- verify role and authority;
- verify Artifact Set;
- verify Full Event Log;
- generate `ARTIFACT_ACCEPTED`, `ARTIFACT_LEGACY`, `ARTIFACT_REVOKED`, `ARTIFACT_REPLACED`, and rollback acceptance events;
- append valid events to the append-only Event Log.

Forbidden responsibilities:

- generate or modify artifacts;
- modify hashes to fit evidence;
- pretend regression was run;
- auto-generate approval;
- update Runtime;
- switch consumers;
- mutate Current, Ledger, Pending, Runtime State, Feature, AI, or Planning.

The Acceptance Writer must fail closed if any evidence reference, subject, hash, schema, role, approval, or regression result is missing or mismatched.

## Runtime Eligibility

`runtime_use_eligible=true` requires all of the following:

- status is `ACCEPTED`;
- Artifact Set is complete;
- content hash matches;
- schema hash matches or an explicit non-structural schema acceptance exists;
- Acceptance Evidence Bundle is complete;
- Regression result is `PASS`;
- Release Approval exists;
- Runtime Consumer Compatibility is `PASS`;
- point-in-time status is acceptable;
- artifact is not `LEGACY`;
- artifact is not `REVOKED`;
- artifact is not `REJECTED`;
- Event Log, Index, and Checkpoint consistency is valid.

A Registry Entry alone is not enough for Runtime use.

## Replacement

Replacement workflow:

```text
New Artifact Set VALIDATED
↓
Acceptance bundle completed
↓
New Artifact Set ACCEPTED with runtime_use_eligible=false initially if old active exists
↓
Old Artifact Set LEGACY with runtime_use_eligible=false
↓
New Artifact Set ELIGIBILITY_CHANGED to runtime_use_eligible=true
↓
Index Build
↓
Checkpoint
```

Because JSONL cannot atomically append multiple events as one transaction, the safe rule is:

- no step may leave two active Runtime-eligible artifacts for the same logical artifact and consumer;
- if a partial sequence exists, Runtime lookup must fail closed until Index and Checkpoint validate a single eligible artifact;
- operator recovery appends the missing lifecycle/eligibility event and rebuilds derived views.
- every acceptance attempt must use a unique `transaction_id`, `attempt_id`, and permanent evidence path namespace;
- evidence bundle, manifest, report, approval, compatibility, lineage, and freeze paths must not be reused across attempts or source hashes;
- before append, the writer or acceptance script must preflight that the Event Log, Index, and Checkpoint match and that no referenced evidence path is already bound to another event fingerprint or artifact set hash.

If future schema supports an atomic replacement event, it may combine old deactivation and new activation, but it must still be replayable from the Event Log.

## Rollback

Rollback workflow:

```text
LEGACY artifact
↓
New Human Review / Architecture Acceptance / Regression / Release Approval
↓
New Acceptance Report
↓
New ARTIFACT_ACCEPTED Event
```

Silent fallback and automatic return are prohibited. The rollback target must reverify:

- content hash;
- schema hash;
- Artifact Set membership;
- Runtime consumer compatibility;
- point-in-time status;
- minimal or full regression profile required by artifact type.

## Revoke

Revoke workflow:

```text
ACCEPTED
↓
ARTIFACT_REVOKED
```

`REVOKED` instances must never be accepted again as the same instance. If no replacement artifact exists, Runtime behavior must fail closed. The fallback behavior itself is outside this contract, but silent fallback to unaccepted artifacts is prohibited.

## Failure Classification

### HALT

- Artifact hash mismatch;
- schema mismatch;
- Artifact Set member missing;
- model / metrics mismatch;
- Acceptance Evidence missing;
- approval role missing;
- `subject_ref` mismatch;
- regression `FAIL`;
- consumer incompatibility;
- point-in-time `HALT`;
- illegal lifecycle;
- duplicate active Runtime-eligible artifact;
- silent fallback;
- Runtime/AI/CLI attempted acceptance promotion;
- Event Log corruption;
- Event Log / Index mismatch during Runtime lookup.

### REVIEW_REQUIRED

- optional evidence missing;
- known limitation not approved;
- rollback target unclear;
- migration readiness incomplete;
- current-path exception requested;
- non-structural model schema requires review acceptance;
- existing Index mismatch but Event Log is intact and rebuildable in offline review.

### VALIDATION_ERROR

- invalid input format;
- required schema field missing;
- path configuration invalid;
- unreadable evidence reference;
- malformed approval or regression evidence document.

## Partial Failure Recovery

### Acceptance Event append succeeds, Index Build fails

Event Log remains authority. Do not delete, edit, or truncate the accepted event.

Required recovery:

1. Run Full Event Log validation.
2. If Event Log is valid, rebuild Materialized Index from Event Log.
3. If Index build still fails, classify as `REVIEW_REQUIRED` or `HALT` depending on root cause.
4. Runtime lookup remains fail-closed until Index and Checkpoint are valid.

### Index Build succeeds, Checkpoint fails

Event Log remains authority and Index remains a derived view.

Required recovery:

1. Validate Event Log / Index consistency.
2. Regenerate Checkpoint.
3. If Checkpoint failure repeats, operator review is required.
4. Runtime lookup remains fail-closed if Checkpoint is required for Runtime eligibility.

### Incomplete acceptance transaction with reused evidence paths

If an acceptance attempt writes events whose evidence paths are then reused or overwritten before a coherent transaction reaches a stable accepted state, the normal recovery is to stop Runtime lookup, preserve the pre-recovery Event Log bytes, inventory the partial events, and obtain Human Review plus Architecture Acceptance before any Event Log recovery. A Limited Registry Recovery Transaction may be approved only if the partial events were never used as Runtime authority and all removed event bodies remain preserved in permanent evidence.

Direct manual rewrite remains prohibited for normal operation. A future Recovery CLI must generate the recovery plan, backup, removed-event inventory, before/after hashes, and approval record before replacing Event Log bytes, then run Full Log validation, Index build, Checkpoint, exactly-one-active-set validation, and Runtime authority preflight.

## Test Plan

Acceptance Writer implementation must include tests for:

- valid Candidate Set acceptance;
- valid Opportunity Set acceptance;
- valid PM Set acceptance;
- valid Capital Allocation Set acceptance;
- missing member;
- hash mismatch;
- schema mismatch;
- model / metrics mismatch;
- role missing;
- approval subject mismatch;
- regression `FAIL`;
- consumer incompatibility;
- point-in-time invalid;
- illegal transition;
- direct `DRAFT -> ACCEPTED`;
- direct `REVIEW_REQUIRED -> ACCEPTED`;
- `REVOKED -> ACCEPTED`;
- duplicate active Runtime-eligible artifact;
- replacement;
- rollback;
- revoke;
- Event append failure;
- Index build failure after acceptance event;
- Checkpoint failure after Index build;
- no Runtime mutation;
- no Current/Ledger/Pending mutation.

## Implementation Plan

Recommended phases:

| Prefix | Scope |
|---|---|
| Phase16-AJ | Acceptance Schema / Role Compatibility Amendment, including any event schema additions required by this contract. |
| Phase16-AK | Acceptance Evidence Builder / Validator for manifests, approvals, regression evidence, and reports. |
| Phase16-AL | Acceptance Writer implementation, append-only and fail-closed. |
| Phase16-AM | Formal Artifact Set Registration Dry Run with no Runtime consumer cutover. |
| Phase16-AN | Acceptance Workflow Review and first acceptance readiness decision. |

Runtime lookup, consumer cutover, and Runtime integration must remain later phases after accepted artifacts and checkpoints exist.

## Acceptance Criteria

This contract is complete when:

- Artifact Type classification is defined;
- Role-to-Artifact-Type Compatibility is defined;
- Candidate Set requirements are defined;
- Opportunity Set requirements are defined;
- PM Set requirements are defined;
- Capital Allocation Set requirements are defined;
- Acceptance Evidence Bundle is defined;
- Evidence path policy is defined;
- Acceptance workflow is defined;
- Formal Registration order is defined;
- Acceptance Event requirements are defined;
- Acceptance Writer boundary is defined;
- Runtime eligibility conditions are defined;
- Replacement, Rollback, and Revoke are defined;
- Partial Failure Recovery is defined;
- Test Plan is defined;
- Implementation Plan is defined;
- no Runtime or Registry state mutation is required by this design.

## Phase16-AJ Schema and Role Compatibility Amendment

Phase16-AJ fixes the Acceptance contract into machine-readable schema and compatibility artifacts.

Machine-readable contract:

```text
docs/02_architecture/contracts/artifact_acceptance_role_compatibility.v1.json
```

Formal Artifact Set Types:

```text
CANDIDATE_AI_SET
OPPORTUNITY_AI_SET
POSITION_MANAGEMENT_POLICY_SET
CAPITAL_ALLOCATION_POLICY_SET
FEATURE_SCHEMA_SET
SAFETY_POLICY_SET
```

Legacy aliases remain readable only for pre-Acceptance compatibility:

```text
CANDIDATE_ACCEPTED_SET -> CANDIDATE_AI_SET
OPPORTUNITY_ACCEPTED_SET -> OPPORTUNITY_AI_SET
PM_ACCEPTED_SET -> POSITION_MANAGEMENT_POLICY_SET
```

Acceptance Writer and future Runtime lookup must use the formal Set Types, not the legacy aliases.

Reusable Runtime-use Artifact Sets require all approval roles:

```text
HUMAN_REVIEW
ARCHITECTURE_ACCEPTANCE
REGRESSION_ACCEPTANCE
RELEASE_APPROVAL
```

`same_reviewer_allowed=true` is allowed for one-person operation, but `role_omission_allowed=false`.

Schema versioning classification:

```text
pre-Acceptance v1 hardening
```

Reason: the formal Event Log is empty and no `ARTIFACT_ACCEPTED` event exists.
