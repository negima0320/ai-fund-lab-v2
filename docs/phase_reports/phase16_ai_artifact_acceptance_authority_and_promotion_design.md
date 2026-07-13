# Phase16-AI Artifact Acceptance Authority and Promotion Design

## Executive Summary

Phase16-AI defines the authority, compatibility, evidence, and workflow required before any Artifact can be promoted to `ACCEPTED`.

Final judgment:

```text
PHASE16_AI_ARTIFACT_ACCEPTANCE_AUTHORITY_AND_PROMOTION_DESIGN_ACCEPTED
```

This phase is design-only. It did not implement Acceptance Writer, change schemas, append Registry events, promote artifacts, create evidence paths, copy artifacts, rebuild Index, create Checkpoint, or connect Runtime lookup.

## Created Files

- `docs/02_architecture/artifact_acceptance_authority_and_promotion_workflow_contract.md`
- `docs/phase_reports/phase16_ai_artifact_acceptance_authority_and_promotion_design.md`
- `reports/phase_reports/phase16_ai_artifact_acceptance_authority_and_promotion_design.json`

## Artifact Type Classification

| Target | Classification |
|---|---|
| Candidate AI Artifact Set | `ACCEPTANCE_REQUIRED` |
| Opportunity AI Artifact Set | `ACCEPTANCE_REQUIRED` |
| Position Management Policy Artifact Set | `ACCEPTANCE_REQUIRED` |
| Capital Allocation Policy Artifact Set | `ACCEPTANCE_REQUIRED` |
| Feature Schema Artifact | `ACCEPTANCE_REQUIRED` |
| Canonical Data Contract / Manifest | `VALIDATION_ONLY` |
| Safety / Policy Artifact | `ACCEPTANCE_REQUIRED` when used as persistent Runtime policy |
| Generated Decision Artifacts | `REGISTRATION_ONLY` |
| Validation / Regression / Approval Evidence | `EVIDENCE_ONLY` |

## Role-to-Artifact-Type Compatibility

Reusable Runtime-use artifacts require all roles:

```text
HUMAN_REVIEW
ARCHITECTURE_ACCEPTANCE
REGRESSION_ACCEPTANCE
RELEASE_APPROVAL
```

One-person operation may use the same `reviewer_id` for multiple roles, but the role records must be explicit. Role omission is `HALT` for `ARTIFACT_ACCEPTED`.

## Candidate Artifact Set

Required:

- Candidate Model;
- Model Manifest;
- Feature Schema;
- Training Metadata;
- Training Data Lineage;
- Validation Evidence;
- Metrics / Evaluation Evidence;
- Runtime Consumer Compatibility;
- Model Hash;
- Schema Hash or explicit non-structural schema review.

Current candidate evidence:

| Item | Hash |
|---|---|
| Candidate model | `2ea75d14d3fe36828512d8e1fb0ac482798690c6594f22029c4d5b63c7fd6a02` |
| Candidate model manifest | `e64e15efc9da10b7b19039ff3ed2841f122a625cf46d7dbaa7d65385ee27e56c` |
| Candidate training artifact | `5734c3395bf28a9385b753130fa18953817cd8671784a0499f27b4358a526a6a` |
| Candidate validation artifact | `cdbe1930a9e1ea80be795009561b8da2137e2c5c26225da334995d2bf704155b` |

Blockers:

- formal Artifact Set Manifest under permanent evidence path missing;
- feature schema member binding missing from manifest candidate;
- approval roles missing;
- Acceptance Report missing;
- real regression evidence missing;
- permanent path migration incomplete;
- pickle model structural schema requires review acceptance.

## Opportunity Artifact Set

Required:

- Opportunity Model;
- Phase5-P Metrics;
- Feature Schema;
- Training Metadata;
- Training Data Lineage;
- Validation Evidence;
- Runtime Consumer Compatibility;
- Model Hash;
- Metrics Hash.

The accepted set must bind Phase5-P model and Phase5-P metrics together. Phase5-P model plus Phase5-E metrics fallback is prohibited.

Current opportunity evidence:

| Item | Hash |
|---|---|
| Opportunity model | `140e350bd9b12bf0c595184587fa2a3bd74236e4bdf1818df481022980dd6acd` |
| Opportunity Phase5-P metrics | `8428f2327e77374743f69e2ebc956a97a9d718880ef2acfc26571f94d9fd9511` |
| Opportunity Phase5-E fallback metrics observed | `3416d82a904609b1f1dec2112f1990ca537665b25ab73d63120dea353ee41fc4` |
| Opportunity training artifact | `5923c387f590807dcd9e88de4cb35bfb9b7e4682d01f69648133350a16901aed` |
| Opportunity validation artifact | `2fc8b3c2cab43734f6914944c54659e8e72c123bc5c68a9d731a7f64eec5a02d` |

Blockers:

- Phase5-E fallback remains a migration blocker;
- formal Artifact Set Manifest under permanent evidence path missing;
- feature schema member binding missing from manifest candidate;
- approval roles missing;
- Acceptance Report missing;
- model/metrics same-set compatibility evidence missing;
- ranking and Planning/Pending unchanged regression missing;
- permanent path migration incomplete;
- pickle model structural schema requires review acceptance.

## PM Artifact Set

PM is a code-policy set, not a model set.

Required:

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

| Item | Hash |
|---|---|
| PM code policy | `31fb8630fa1edb281a5e7067ec89677f98f564f21a5c2c5f09f938a5795b2c85` |
| PM Runtime adapter | `6ffa7da2b91f5fd5cfa76aa4c487e6e6cf5e1293ba929fe374abd61aaadb7d1b` |

Blockers:

- formal Artifact Set Manifest under permanent evidence path missing;
- behavior contract and policy version evidence missing;
- approval roles missing;
- Acceptance Report missing;
- PM behavior regression and Sell Planning unchanged evidence missing.

## Capital Allocation Artifact Set

Required:

- Capital Allocation Policy;
- Policy Schema;
- Policy Version;
- Policy Hash;
- Validation Evidence;
- Regression Evidence;
- Runtime Consumer Compatibility.

Current evidence:

| Item | Hash |
|---|---|
| Capital Allocation policy | `d3e2a046fb4b56b3d78ff7c6913e456d59313e9f0f6be6969cb0c13a08b7fdcd` |
| Policy schema | `a287fdc70888939bd764ee85895cbe96ad2962cba7703209c64bfdfc262d13ce` |
| Alternate policy artifact observed | `11b6c77b296895a47b444a125826a6d31b162c4fac9a46ef6c71b1d2cf4973e7` |

Blockers:

- formal Artifact Set Manifest under permanent evidence path missing;
- approval roles missing;
- Acceptance Report missing;
- Planning/Pending/Submit Guard semantic equality regression missing;
- standalone Capital Allocation Decision Artifact remains staged and must not change current behavior.

## Feature / Canonical / Safety Classification

Feature Schema is `ACCEPTANCE_REQUIRED` because accepted models and policies depend on compatible feature columns and point-in-time guarantees.

Canonical Data Contract / Manifest is `VALIDATION_ONLY` in this contract because canonical data authority is governed by Operational Data Foundation contracts. If later used as Registry Runtime lookup authority, it must receive its own acceptance workflow.

Safety / Policy Artifact is `ACCEPTANCE_REQUIRED` when used as persistent Runtime policy, but Registry acceptance does not grant Safety release authority.

## Acceptance Evidence Bundle

Required bundle:

- Artifact Set Manifest;
- Acceptance Report;
- Regression Evidence;
- Human Review Approval;
- Architecture Acceptance Approval;
- Regression Acceptance Approval;
- Release Approval;
- Source / Lineage Manifest;
- Model / Policy Freeze Manifest;
- Runtime Consumer Compatibility Evidence;
- Rollback Target.

Each item must have schema, path, hash, `subject_ref`, set binding, required/optional classification, expiry policy, and reuse policy.

## Evidence Path Policy

Permanent machine-readable evidence paths:

```text
.runtime/artifact_registry/evidence/acceptance/
.runtime/artifact_registry/evidence/regression/
.runtime/artifact_registry/evidence/approvals/
.runtime/artifact_registry/evidence/manifests/
```

Path creation is prohibited in Phase16-AI and was not performed.

## Acceptance Workflow

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

## Formal Registration Order

Chosen policy: option B.

```text
Permanent path Copy / Verify
↓
DRAFT / VALIDATED registration
↓
Acceptance
```

This matches the migration sequence:

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

Current code paths may be accepted as permanent only through explicit Architecture Acceptance and Release Approval.

## Acceptance Event Design

`ARTIFACT_ACCEPTED` must include:

- event identity;
- logical and instance identity;
- artifact set id;
- `previous_status=VALIDATED` or `LEGACY` for rollback;
- `new_status=ACCEPTED`;
- `runtime_use_eligible=true` only after all eligibility gates pass;
- content hash and schema hash;
- authority, review, regression, acceptance report refs;
- source refs;
- consumer compatibility;
- point-in-time status.

Authority unit:

- Candidate, Opportunity, PM, and Capital Allocation Policy use Set-level acceptance authority.
- Member-level events may register/validate members, but Runtime eligibility comes from the accepted set to avoid double authority.

## Acceptance Writer Boundary

Future Acceptance Writer should be separate from the existing DRAFT/VALIDATED Writer.

Allowed:

- read evidence;
- verify roles and authority;
- verify Artifact Set;
- verify Full Event Log;
- generate acceptance/replacement/revoke/rollback events;
- append valid events.

Forbidden:

- generate or modify artifacts;
- adjust hashes to match;
- fabricate regression or approvals;
- update Runtime;
- switch consumers;
- mutate Current, Ledger, Pending, Runtime State, Feature, AI, or Planning.

## Runtime-use Eligibility

`runtime_use_eligible=true` requires:

- status `ACCEPTED`;
- complete Artifact Set;
- hash match;
- schema match or explicit schema review;
- complete evidence bundle;
- regression `PASS`;
- release approval;
- consumer compatibility `PASS`;
- point-in-time `PASS`;
- not `LEGACY`, not `REVOKED`, not `REJECTED`;
- Event Log / Index / Checkpoint consistency.

Registry Entry existence alone is insufficient.

## Replacement

Replacement must avoid two Runtime-eligible artifacts for the same logical artifact and consumer. Because JSONL cannot append multi-event transactions atomically, replacement should first accept the new set without eligibility when an old eligible set exists, then legacy the old set, then enable new eligibility. Runtime lookup must fail closed if replay observes multiple eligible artifacts or partial replacement.

## Rollback

Rollback requires new review, regression, release approval, and acceptance event. A `LEGACY` artifact must not silently return to Runtime use.

## Revoke

`REVOKED` instances cannot be accepted again as the same instance. If no replacement exists, Runtime must fail closed. Silent fallback remains prohibited.

## Partial Failure Recovery

Acceptance Event append succeeds but Index Build fails:

- do not edit Event Log;
- run Full Event Log validation;
- rebuild Index from Event Log;
- require operator review if rebuild fails;
- Runtime lookup remains fail-closed.

Index Build succeeds but Checkpoint fails:

- validate Event Log / Index consistency;
- regenerate Checkpoint;
- require operator review if repeated failure;
- Runtime lookup remains fail-closed if Checkpoint is required.

## Current Candidate Blocking Items

Candidate:

- formal evidence path and Artifact Set Manifest missing;
- feature schema binding missing;
- role approvals missing;
- Acceptance Report missing;
- regression evidence missing;
- permanent path migration incomplete.

Opportunity:

- Phase5-E fallback blocker;
- formal evidence path and Artifact Set Manifest missing;
- feature schema binding missing;
- role approvals missing;
- Acceptance Report missing;
- model/metrics same-set evidence missing;
- regression evidence missing;
- permanent path migration incomplete.

PM:

- behavior contract missing;
- role approvals missing;
- Acceptance Report missing;
- regression evidence missing;
- formal evidence path missing.

Capital Allocation:

- role approvals missing;
- Acceptance Report missing;
- semantic equality regression missing;
- standalone Decision Artifact remains separate staged decision.

Feature Schema:

- formal accepted Feature Schema set missing;
- point-in-time and consumer compatibility evidence must be bundled.

Role Compatibility:

- no formal approval evidence exists yet for the four required roles.

## Test Plan

Future Acceptance Writer tests must cover:

- valid Candidate Set Acceptance;
- valid Opportunity Set Acceptance;
- valid PM Set Acceptance;
- valid Capital Allocation Set Acceptance;
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
- Checkpoint failure after Index build.

## Implementation Plan

Recommended next phases:

| Prefix | Scope |
|---|---|
| Phase16-AJ | Acceptance Schema / Role Compatibility Amendment |
| Phase16-AK | Acceptance Evidence Builder / Validator |
| Phase16-AL | Acceptance Writer |
| Phase16-AM | Formal Artifact Set Registration Dry Run |
| Phase16-AN | Acceptance Workflow Review |

## Readiness

| Area | Judgment |
|---|---|
| Schema amendment requirements | Required next |
| Artifact Acceptance implementation readiness | `DESIGN_READY_IMPLEMENTATION_REQUIRED` |
| Formal registration readiness | `NOT_READY` |
| Runtime Lookup readiness | `NOT_READY` |
| Runtime Integration readiness | `NOT_READY` |

## Runtime / Registry State

Formal Event Log remains empty:

```text
.runtime/artifact_registry/events/registry_events.jsonl
event_count=0
```

Formal Index remains empty:

```text
.runtime/artifact_registry/index/registry_index.json
entry_count=0
```

No `ACCEPTED` event was appended and no artifact was promoted.

## Final Judgment

```text
PHASE16_AI_ARTIFACT_ACCEPTANCE_AUTHORITY_AND_PROMOTION_DESIGN_ACCEPTED
```

Next Prefix:

```text
Phase16-AJ
```
