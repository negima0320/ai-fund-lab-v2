# Phase18-R AI Lifecycle v2 Root Cause and Contract Closure Audit

- Run ID: `phase18r-root-cause-contract-closure-audit-20260717T000000Z`
- Primary: `PHASE18_R_ROOT_CAUSE_AND_CONTRACT_CLOSURE_AUDIT_COMPLETE`
- Secondary: `PHASE18_NOT_COMPLETE, PHASE19_NOT_READY, REMEDIATION_PLAN_READY`
- Production code fix: not performed

## Executive Summary

Phase18-R confirms that Q-GAP-001 through Q-GAP-008 are not eight independent bugs. They cluster around accepted authority resolution, resolver over-compensation for missing evidence, incomplete Atomic BUY AI Bundle runtime evidence, immediate/delayed metric ambiguity, BUY-only control semantics, rollback failure semantics, and test architecture gaps.

The next implementation step is ready, but Phase18 remains incomplete and Phase19 is not ready.

## 21.1 SoT Authority Flow

```text
Source -> Dataset -> Training -> Promotion -> Authority -> Registry -> Runtime -> BUY / SELL
```

| node | owner | output | failure |
|---|---|---|---|
| Dataset Source Authority | AI Lifecycle Dataset Builder | source refs, schema/content hashes, lineage | Dataset rebuild REVIEW/BLOCK; no Runtime fallback |
| Label-safe Dataset Bundle | AI Lifecycle Dataset Publisher | dataset bundle with label_safe_cutoff and metadata | Bundle unpublished; Training blocked |
| Training Bundle | AI Lifecycle Training Pipeline | model, metrics, calibration, baseline evidence, dataset refs | Promotion blocked |
| Promotion Candidate Transaction | Registry Promotion Operator | candidate transaction and atomic BUY AI bundle candidate | No accepted Runtime use |
| Authority Decision | Human/Authority Control Plane | approved/rejected decision artifact | No Registry accepted event |
| Registry Accepted Event | Artifact Registry Writer | ARTIFACT_ACCEPTED event with runtime_use_eligible | Runtime resolver returns INSUFFICIENT_EVIDENCE/HALT |
| Registry Accepted State | Registry event log + index + checkpoint | accepted set identity | No latest/manual fallback |
| Accepted Atomic BUY AI Bundle Resolver | Runtime Accepted Authority Resolver | joint Candidate/Opportunity bundle identity | BUY BLOCK, SELL dependencies continue |
| Integrity Verification | Runtime Lifecycle Evidence Authority | verified hashes/schema/lineage/compatibility | CRITICAL_AUTHORITY_VIOLATION or INSUFFICIENT_EVIDENCE |
| Runtime Freshness Evidence | Runtime Lifecycle Evidence Authority | 3 business-day clocks from formal calendar | MODEL_UNHEALTHY or INSUFFICIENT_EVIDENCE |
| Runtime Drift Baseline | Accepted bundle baseline artifact | materialized baseline distributions | INSUFFICIENT_EVIDENCE |
| Runtime Current Evidence | Runtime BUY AI producer | current population/distribution/positive coverage hash | REVIEW/BLOCK depending severity |
| Runtime Lifecycle Decision | Runtime Control Plane | PASS/REVIEW/BLOCK plus scoped control flags | BUY-only block unless shared dependency fails |
| BUY Control | Runtime Planning/Submit | BUY planning/submit allowed or blocked | No forced BUY |
| SELL Continuity | Runtime SELL jobs | SELL planning/submit reachable if dependencies pass | Only SELL dependency failures block SELL |

## 21.2 Current Production Call Graph

```text
morning -> produce_buy_ai_decisions -> Registry model set resolver -> Candidate inference -> Opportunity inference -> lifecycle_evidence -> ai_lifecycle_gates -> BLOCK/REVIEW exits before morning planning; PASS continues to BUY planning
sell_planning -> PM producer -> sell_planning_pending_pipeline
submit -> pending/approval/submit guard path
```

- Gap: SELL continuity is a declared stage, not a proven downstream execution path from the same blocked BUY event.

## Accepted Artifact Resolution Contract

| artifact_type | production_runtime | condition |
|---|---|---|
| Registry accepted Atomic BUY AI Bundle | ALLOWED | Resolved from accepted event/state, runtime_use_eligible, verified hashes/schema/lineage |
| Promotion Candidate | FORBIDDEN | Evidence only until accepted event; candidate-only presence maps to INSUFFICIENT_EVIDENCE |
| Review Candidate | FORBIDDEN | Review evidence only |
| Latest Training Bundle | FORBIDDEN | No latest directory discovery; must be referenced by accepted bundle |
| Latest Dataset Bundle | FORBIDDEN | No latest directory discovery; must be referenced by accepted bundle |
| Manual Artifact Path | FORBIDDEN by default | Only diagnostic path equal to Registry member may be accepted; cannot override authority |
| Test Fixture Bundle | FORBIDDEN | Allowed only isolated test root, never normal Runtime success |
| Historical Isolated Bundle | ALLOWED only in isolated historical acceptance | Explicit mode/evidence, not Production accepted state |

## Integrity Verification Contract

- Registry accepted event identity
- Accepted state identity
- Atomic BUY AI Bundle identity
- Joint bundle hash
- Candidate/Opportunity bundle hashes
- Dataset/training bundle hashes
- Calibration artifact hash
- Schema, feature contract, target contract hashes
- Candidate/Opportunity compatibility
- Lineage refs
- Authority decision ref
- Registry event/checkpoint refs

Failure mapping:

- `missing accepted state`: INSUFFICIENT_EVIDENCE => BUY BLOCK, SELL dependency path may continue
- `hash/schema/lineage mismatch`: CRITICAL_AUTHORITY_VIOLATION => BUY BLOCK, no Runtime adoption
- `incompatible Candidate/Opportunity`: MODEL_UNHEALTHY or CRITICAL_AUTHORITY_VIOLATION depending source
- `unreadable bundle`: INSUFFICIENT_EVIDENCE

## Freshness Contract

Formal Trading Calendar is required for Production. Weekday fallback is forbidden for Production Runtime authority; it may appear only in isolated review/test evidence.

- `dataset_lag_business_days` = label_safe_cutoff - training_dataset_max_date
- `model_training_lag_business_days` = label_safe_cutoff - model_training_cutoff
- `model_acceptance_age_business_days` = runtime_decision_date - model_accepted_at

Invalid cases:

- `negative lag`: fail-closed REVIEW/BLOCK; never PASS
- `future cutoff`: CRITICAL_AUTHORITY_VIOLATION or INSUFFICIENT_EVIDENCE
- `accepted_at < created_at`: REVIEW_REQUIRED at minimum
- `decision_date < accepted_at`: INSUFFICIENT_EVIDENCE
- `calendar unavailable/unreadable/range short/holiday mismatch`: INSUFFICIENT_EVIDENCE; Production weekday fallback forbidden

## Drift Evidence Contract

- Immediate gate: artifact integrity, freshness, feature drift, candidate population drift, prediction distribution drift, positive coverage drift, all-negative behavior, score distribution consistency
- Delayed monitoring: realized calibration error, 5/10/20bd return, rank correlation, Top-k realized return, hit rate, bucket realized monotonicity
- Forbidden: summary stats random/sample restoration, current-derived baseline, Production use of test fixture baseline, hash-unverified baseline, zero-filled missing baseline

## Runtime Decision Contract

- Decisions: `PASS`, `REVIEW_REQUIRED`, `BLOCK`
- Classifications: `HEALTHY`, `MARKET_NO_OPPORTUNITY`, `MODEL_UNHEALTHY`, `INSUFFICIENT_EVIDENCE`, `CRITICAL_AUTHORITY_VIOLATION`
- Required scoped controls: `block_buy_planning`, `block_buy_submit`, `block_sell_planning`, `block_sell_submit`
- Existing `block_submit` should become a backward-compatible alias only after scoped submit flags are authoritative.

## 21.3 SoT vs Implementation Diff

| Contract Point | SoT | Current Implementation | Gap | Root Cause |
|---|---|---|---|---|
| Accepted artifact resolution | Registry accepted only | Atomic BUY bundle resolver falls back to latest Promotion Candidate | CONTRACT_CONFLICT | ROOT-A/ROOT-B |
| Integrity verification | Verify Registry event, bundle, hash, schema, lineage | Loads JSON and records content_hash | PARTIAL | ROOT-A/ROOT-C |
| Freshness clocks | Formal 3 clocks from label-safe/cutoff/accepted_at | created_at fallback and negative lag can pass | CONTRACT_CONFLICT | ROOT-B |
| Trading calendar | Formal calendar authority | weekday fallback with no fail-closed reason | CONTRACT_CONFLICT | ROOT-B |
| Drift baseline | Accepted materialized baseline | synthetic values from summary stats | PARTIAL | ROOT-C |
| Immediate/delayed | Delayed realized metrics not daily gate inputs | calibration_error_delta can block immediate gate | CONTRACT_CONFLICT | ROOT-D |
| BUY/SELL control | BUY block does not stop SELL dependencies | morning exits after BUY block; separate sell job not proven | PARTIAL | ROOT-E |
| Rollback restore | Atomic fail-closed with restore failure critical | restore snapshots but no restore-failure CRITICAL proof | PARTIAL | ROOT-F |

## 21.4 Q-GAP Root Cause Matrix

| Q-GAP | Severity | Symptom | Primary Root Cause | Shared Remediation Unit |
|---|---|---|---|---|
| Q-GAP-001 | CRITICAL | Accepted resolver falls back to Promotion Candidate | ROOT-A Accepted Authority Resolver boundary unclear | RU1 Accepted-only Artifact Authority and Integrity |
| Q-GAP-002 | HIGH | Negative model-training lag PASS | ROOT-B missing evidence/future dates normalized | RU2 Freshness and Formal Calendar Authority |
| Q-GAP-003 | HIGH | Unreadable calendar silently uses weekdays | ROOT-B fallback compensation | RU2 Freshness and Formal Calendar Authority |
| Q-GAP-004 | HIGH | Bundle hash/schema/lineage not verified | ROOT-A authority split from Registry resolver | RU1 Accepted-only Artifact Authority and Integrity |
| Q-GAP-005 | HIGH | Synthetic baseline from summary stats | ROOT-C accepted bundle lacks materialized runtime baseline | RU3 Materialized Drift Baseline and Immediate Gate |
| Q-GAP-006 | HIGH | Delayed calibration metric in immediate gate | ROOT-D Immediate/Delayed boundary not fixed | RU3 Materialized Drift Baseline and Immediate Gate |
| Q-GAP-007 | HIGH | SELL continuity not proven through downstream path | ROOT-E BUY block vs global Runtime halt ambiguity | RU4 BUY-only Control and SELL Continuity |
| Q-GAP-008 | MEDIUM | Restore failure CRITICAL path not proven | ROOT-F Registry transaction failure model incomplete | RU5 Atomic Restore Failure Semantics |

## Root Cause Clusters

- `ROOT-A`: Accepted Authority Resolver responsibility unclear/split
- `ROOT-B`: Evidence resolver compensates for missing evidence
- `ROOT-C`: Accepted Atomic BUY AI Bundle lacks complete Runtime baseline/contract
- `ROOT-D`: Immediate vs Delayed monitoring boundary not fixed
- `ROOT-E`: BUY block vs global Runtime halt control design ambiguous
- `ROOT-F`: Registry transaction failure model incomplete
- `ROOT-G`: Tests emphasize local operators/fixtures over Production call graph

## Remediation Units

### RU1 Accepted-only Artifact Authority and Integrity

- Purpose: Make Runtime consume only Registry accepted Atomic BUY AI Bundle authority and verify all hashes/contracts.
- Root causes: `ROOT-A, ROOT-B, ROOT-C`
- Target gaps: `Q-GAP-001, Q-GAP-004`
- Production modules: `runtime_v2/lifecycle_evidence.py, runtime_v2/buy_ai/producer.py, artifact_registry/resolver.py`
- Do not change: Target, features, BV15, Registry accepted state, Runtime switch
- Acceptance tests: accepted state resolves, accepted state missing does not fallback, promotion candidate only => INSUFFICIENT_EVIDENCE, bundle hash mismatch fail-closed, manual path rejected in Production
- Depends on: none

### RU2 Freshness and Formal Calendar Authority

- Purpose: Define and enforce the 3 clocks with formal calendar and invalid-date fail-closed semantics.
- Root causes: `ROOT-B, ROOT-G`
- Target gaps: `Q-GAP-002, Q-GAP-003`
- Production modules: `runtime_v2/lifecycle_evidence.py, runtime_v2/ai_lifecycle_gates.py`
- Do not change: Freshness thresholds unless SoT amendment is explicitly approved
- Acceptance tests: normal clocks, negative training lag, future model cutoff, missing/unreadable/range-short calendar, missing accepted_at, timezone mismatch
- Depends on: RU1

### RU3 Materialized Drift Baseline and Immediate Gate

- Purpose: Replace synthetic baselines and separate immediate label-free evidence from delayed realized monitoring.
- Root causes: `ROOT-C, ROOT-D, ROOT-B`
- Target gaps: `Q-GAP-005, Q-GAP-006`
- Production modules: `runtime_v2/lifecycle_evidence.py, runtime_v2/ai_lifecycle_gates.py, training bundle artifact writers`
- Do not change: Model target, feature contract, BUY eligibility
- Acceptance tests: materialized baseline vs stable current, feature/prediction/population/positive coverage hard drift, all-negative only, missing baseline, baseline hash mismatch, insufficient sample
- Depends on: RU1

### RU4 BUY-only Control and SELL Continuity

- Purpose: Make BUY lifecycle block scoped to BUY planning/submit and prove SELL path reachability through Production call graph.
- Root causes: `ROOT-E, ROOT-G`
- Target gaps: `Q-GAP-007`
- Production modules: `runtime_v2/ai_lifecycle_gates.py, runtime_v2/cli/run_daily_operation.py, runtime_v2/planning/sell_pipeline.py, runtime_v2/submit`
- Do not change: Broker write disabled, PM/Safety rules unchanged
- Acceptance tests: MODEL_UNHEALTHY + existing position, INSUFFICIENT_EVIDENCE + SELL signal, MARKET_NO_OPPORTUNITY + SELL signal, BUY submit blocked, SELL submit authorization reachable, Current/Valuation/PM/Safety reachable
- Depends on: RU1, RU2, RU3

### RU5 Atomic Restore Failure Semantics

- Purpose: Define restore failure as CRITICAL with unchanged accepted state evidence and manual recovery metadata.
- Root causes: `ROOT-F, ROOT-G`
- Target gaps: `Q-GAP-008`
- Production modules: `ai_lifecycle/rollback_revoke.py, artifact_registry writer/index/checkpoint`
- Do not change: Production Registry accepted state during tests
- Acceptance tests: event/index/checkpoint/post-validation failures, restore event/index/checkpoint failure, RESTORE_FAILED => CRITICAL, idempotent retry
- Depends on: RU1

## 21.5 Remediation Dependency Graph

```text
Accepted Authority
  -> Integrity
  -> Freshness / Baseline
  -> Runtime Decision
  -> BUY / SELL Control
  -> Closure Acceptance
Atomic Restore Failure Semantics depends on accepted authority but can be implemented in parallel after RU1 contract is fixed.
```

## Test Architecture Audit

- Existing regression: Phase18-Q rerun: 85 passed, 2 warnings; targeted lifecycle tests: 10 passed.
- Guarantees:
  - Registry resolver/index/checkpoint happy path and many failure rehearsals pass.
  - Current tests exercise local lifecycle gate states and isolated rollback/revoke failures.
  - MARKET_NO_OPPORTUNITY and MODEL_UNHEALTHY can be separated in local gate evidence.
- Does not guarantee:
  - Production Runtime accepted-only Atomic BUY AI Bundle discovery.
  - No Promotion Candidate fallback when accepted state is absent.
  - Negative/future freshness clocks fail-closed.
  - Formal calendar missing/unreadable/range-short failure behavior.
  - Accepted bundle hash/schema/lineage mismatch mapping.
  - Materialized baseline distribution authority.
  - Immediate/delayed calibration separation.
  - SELL planning/submit reachability through normal Runtime entrypoints under BUY block.
  - Restore-failure CRITICAL rollback semantics.

## Predefined Acceptance Contract

- `accepted_authority`: accepted state resolves, accepted state none does not fallback, promotion candidate only => INSUFFICIENT_EVIDENCE, accepted event/bundle hash mismatch fail-closed, manual path rejected
- `freshness`: normal 3 clocks, negative training lag, future model cutoff, missing/unreadable/range-short calendar, missing accepted_at, timezone mismatch
- `drift`: materialized baseline stable current, feature/prediction/population/positive coverage drift, all-negative only, all-negative + drift, missing baseline, baseline hash mismatch, insufficient sample
- `buy_sell`: MODEL_UNHEALTHY + existing position, INSUFFICIENT_EVIDENCE + SELL signal, MARKET_NO_OPPORTUNITY + SELL signal, BUY submit block, SELL submit authorization reachable, Current/Valuation/PM/Safety reachable
- `rollback`: event/index/checkpoint/post-validation failures, restore event/index/checkpoint failure, RESTORE_FAILED => CRITICAL

## Risks Of Local Patching

- Removing only the Promotion Candidate fallback without hash/lineage verification leaves forged accepted bundle risk.
- Adding a negative-lag check without formal calendar authority still allows wrong clocks.
- Replacing synthetic baseline without immediate/delayed split can keep calibration proxy misuse.
- Adding SELL continuity unit tests without call-graph proof can keep global block behavior hidden.

## Recommended Next Step

Implement RU1-RU3 together as the next remediation step because Accepted Authority, Integrity, Freshness, and Baseline evidence share the same Runtime evidence boundary. Then implement RU4 and RU5 with integration/failure-injection acceptance.

## Non-Mutation Confirmation

- Registry count before/after: `42` / `42`
- Registry hash before/after: `3c7a529dc4bcaf48ef8bda795a27b4e8be338e5bda1efd215e92b1801c0a019d` / `3c7a529dc4bcaf48ef8bda795a27b4e8be338e5bda1efd215e92b1801c0a019d`
- Runtime switch: not performed
- Runtime submit: not performed
- BUY restart: not performed
- Broker write: not performed

## Final Judgment

- `PHASE18_R_ROOT_CAUSE_AND_CONTRACT_CLOSURE_AUDIT_COMPLETE`
- `PHASE18_NOT_COMPLETE`
- `PHASE19_NOT_READY`
- `REMEDIATION_PLAN_READY`
