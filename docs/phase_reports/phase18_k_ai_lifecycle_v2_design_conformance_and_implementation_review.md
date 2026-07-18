# Phase18-K — AI Lifecycle v2 Design Conformance and Implementation Review

- Run ID: `phase18k-design-conformance-review-20260717T000000Z`
- Primary: `PHASE18_K_CRITICAL_CONTRACT_VIOLATION_DETECTED`
- Secondary: `PHASE18_NOT_COMPLETE, PHASE19_NOT_READY`

## Executive Summary

Phase18 produced substantial Candidate/Opportunity lifecycle artifacts, but formal design conformance fails because the Phase18-I promotion-candidate event breaks the Artifact Registry event-log contract and Runtime resolver fails closed. Several lifecycle requirements remain partial or unimplemented.

## Key Findings

### K-GAP-001 — Phase18-I Promotion Candidate event is not compatible with formal Artifact Registry event schema

- Severity: `CRITICAL`
- Classification: `IMPLEMENTATION_CONTRACT_VIOLATION`
- Affected contract: Artifact Registry append-only event log, Runtime accepted artifact resolver fail-closed contract
- Runtime impact: RegistryArtifactResolver halts before resolving accepted BUY AI sets; Runtime BUY AI artifact lookup fails closed.
- Registry impact: Full event log validation FAIL/HALT; checkpoint/index remain at pre-Phase18-I hash and no longer describe the event log.
- Recommended step: Phase18-L remediation: define/validate Promotion Candidate schema or separate candidate transaction log; rebuild validator/index/checkpoint; rerun resolver tests.

### K-GAP-002 — Runtime Freshness/Drift gates are report-script implementations, not integrated Runtime Control Plane modules

- Severity: `HIGH`
- Classification: `RUNTIME_INTEGRATION_GAP`
- Affected contract: Runtime Control Plane freshness/drift gate and BUY PASS/REVIEW_REQUIRED/BLOCK boundary
- Runtime impact: Daily Runtime may not enforce Phase18-J gate semantics without explicit operator wiring.
- Registry impact: None directly, except resolver is already blocked by K-GAP-001.
- Recommended step: Move gate logic into src/runtime_v2 control-plane module with tests; keep scripts as wrappers.

### K-GAP-003 — Drift gate evidence is shallow and includes forced PASS placeholders

- Severity: `HIGH`
- Classification: `TEST_COVERAGE_GAP`
- Affected contract: AI Lifecycle v2 Drift Contract
- Runtime impact: Hard drift may be missed if only schema smoke passes.
- Registry impact: None.
- Recommended step: Implement quantitative drift validators and failure rehearsals for all-negative with hard drift.

### K-GAP-004 — Weekly lifecycle scheduler is not implemented

- Severity: `HIGH`
- Classification: `DESIGN_NOT_IMPLEMENTED`
- Affected contract: AI Lifecycle v2 weekly lifecycle trigger and observability contract
- Runtime impact: Lifecycle work cannot be automatically triggered from cadence/freshness eligibility.
- Registry impact: None directly.
- Recommended step: Add Phase18-L/M scheduler operator with lock/retry/timeout/no-overlap and no hot-swap guarantees.

### K-GAP-005 — PM/Safety policy lifecycle and Future AI onboarding are documented but not implemented as Phase18 lifecycle components

- Severity: `MEDIUM`
- Classification: `DESIGN_NOT_IMPLEMENTED`
- Affected contract: Full AI Lifecycle Coverage Review
- Runtime impact: BUY lifecycle work does not regress PM/Safety, but common lifecycle coverage remains incomplete.
- Registry impact: Existing PM registry artifacts remain separate.
- Recommended step: Add policy-validation lifecycle classification/operators for PM and Safety without applying trainable retrain semantics.

### K-GAP-006 — Rollback/revoke exists as metadata/rehearsal only, not as formal Registry rollback/revoke operator for BUY AI bundle

- Severity: `MEDIUM`
- Classification: `REGISTRY_AUTHORITY_GAP`
- Affected contract: Registry rollback/revoke acceptance contract
- Runtime impact: No executable rollback path for accepted BUY AI bundle yet.
- Registry impact: Rollback metadata available, but no formal event flow.
- Recommended step: Define and test authority-mediated rollback/revoke transaction after registry schema remediation.

### K-GAP-007 — Phase18 operators contain hard-coded run ids, artifact paths, dates, and bundle identities

- Severity: `MEDIUM`
- Classification: `DOCUMENTATION_DRIFT`
- Affected contract: No phase/test-specific shortcut and reproducible operator contract
- Runtime impact: Future lifecycle runs require code edits or new scripts instead of parameterized inputs.
- Registry impact: Promotion transaction ids are phase-specific.
- Recommended step: Parameterize run ids, artifact refs, decision date, and component bundles; keep fixed Evidence ids only in reports.

### K-GAP-008 — Phase18 cross-contract regression suite fails

- Severity: `HIGH`
- Classification: `TEST_COVERAGE_GAP`
- Affected contract: Resolver and runtime registry consumer cutover contract
- Runtime impact: Accepted artifact lookup fails closed.
- Registry impact: Formal registry cannot be validated as-is.
- Recommended step: Fix K-GAP-001, then rerun targeted and full lifecycle regression.

## Design-to-Implementation Matrix

| SoT Requirement | Phase18 Step | Implementation | Evidence | Status | Gap |
|---|---|---|---|---|---|
| PIT Dataset Rebuild | Phase18-A/B/C | src/ai_fund_lab_v2/ai_lifecycle dataset rebuild + real bundles | Phase18-B/C reports, dataset artifacts, tests/ai_lifecycle/test_phase18b | `PASS` |  |
| Training / Validation | Phase18-D/F/H | training_pipeline + Phase18 F/H opportunity redesign artifacts | Phase18-D/F/H reports, training bundles, tests/ai_lifecycle/test_phase18d | `PARTIAL` | Reusable pipeline has fixed date split and phase-specific scripts; no scheduler trigger. |
| Promotion Readiness | Phase18-G/H | Phase18-G/H review scripts and reports | Promotion blocking matrix and H reassessment | `PASS` |  |
| Authority | Phase18-I | Evidence-derived decision function | Authority decision artifact | `PARTIAL` | Operator is phase-specific and hard-coded. |
| Registry Promotion Candidate | Phase18-I | Promotion candidate transaction appended to event log | Full registry validation FAIL/HALT | `CONTRACT_CONFLICT` | Promotion Candidate event violates registry schema. |
| Runtime Discovery | Phase18-J | Read-only report script | Phase18-J report | `PARTIAL` | Not integrated into runtime_v2 control plane; resolver currently halted by registry log. |
| Freshness Gate | Phase18-J | Separate clocks in Phase18-J script | dataset_lag/model_training_lag/model_acceptance_age | `PARTIAL` | Uses promotion bundle lineage for dataset/training while accepted registry entries lack physical training refs. |
| Drift Gate | Phase18-J | Distribution smoke and classification | Phase18-J drift evidence | `PARTIAL` | Feature/candidate/calibration drift are mostly smoke/forced PASS. |
| Atomic BUY AI Bundle | Phase18-I/J | Joint bundle hash and compatibility evidence | atomic_buy_ai_bundle.json | `PASS` |  |
| Rollback / Revoke |  | Rollback metadata only | rollback_metadata.json | `PARTIAL` | No formal accepted rollback/revoke operator. |
| Weekly Scheduler |  | Not found | Repository search | `NOT_IMPLEMENTED` | No eligibility/lock/retry/timeout/no-overlap scheduler. |
| PM Policy Lifecycle |  | Existing Phase16/17 registry acceptance only | PM registry artifacts and tests | `PARTIAL` | No common Phase18 policy lifecycle operator. |
| Safety Policy Lifecycle |  | Existing runtime safety only | Repository search | `NOT_IMPLEMENTED` | No Phase18 Safety policy lifecycle. |
| Future AI Onboarding |  | SoT text only | docs/02_architecture/ai_lifecycle_v2.md | `NOT_IMPLEMENTED` | No onboarding contract implementation/test. |
| Lifecycle E2E Acceptance |  | A-J scripts produce artifacts but no single E2E regression | Targeted pytest fails in registry resolver suite | `CONTRACT_CONFLICT` | Cross-contract suite not green. |

## Registry Evidence

- Full event log validation: `FAIL` / `HALT`
- Event count: `43`
- First errors:
  - line 43: missing required field actor_type
  - line 43: missing required field actor_id
  - line 43: missing required field artifact_version
  - line 43: missing required field previous_status
  - line 43: missing required field physical_path
  - line 43: missing required field schema_version
  - line 43: missing required field business_date
  - line 43: missing required field feature_date
  - line 43: missing required field as_of
  - line 43: missing required field consumer_compatibility
  - line 43: missing required field point_in_time_status
  - line 43: missing required field retention_class

## Test Evidence

- Targeted regression status: `FAIL`
- Passed: `12`
- Failed: `13`

## Non-Mutation Confirmation

- broker_write: `False`
- runtime_submit: `False`
- buy_restarted: `False`
- registry_accepted_set_changed: `False`
- promotion_candidate_runtime_adopted: `False`
- target_changed: `False`
- feature_changed: `False`
- bv15_changed: `False`

## Final

`PHASE18_K_CRITICAL_CONTRACT_VIOLATION_DETECTED`

`PHASE18_NOT_COMPLETE` / `PHASE19_NOT_READY`
