# Phase18-AD Autonomous AI Operations Architecture Closure Review

- Phase: `Phase18-AD`
- Title: `Autonomous AI Operations Architecture Closure Review and Design Amendment`
- Primary Judgment: `PHASE18_AD_ARCHITECTURE_AMENDMENT_REQUIRED`
- Secondary Judgments: `PHASE18_AD_LEGACY_REMOVAL_PLAN_COMPLETE`, `PHASE18_AD_ACCEPTANCE_CONTRACT_COMPLETE`, `PHASE18_AD_IMPLEMENTATION_NOT_READY`

## Scope

This phase was design and audit only. No Dataset rebuild, split change, retraining, calibration refit, model creation, Registry update, Accepted state update, Runtime resolver change, Scheduler change, Runtime switch, BUY restart, Broker write, Historical fresh-run, or Production Runtime execution was performed.

## AB Facts Reflected Into AC

Phase18-AB facts were partially reflected by Phase18-AC:

- Runtime currently uses legacy Registry accepted component models:
  - Candidate: `.runtime/artifacts/ai/candidate/model/formal_candidate_model/sha256-2ea75d14d3fe3682/model.pkl`
  - Opportunity: `.runtime/artifacts/ai/opportunity/model/formal_opportunity_model/sha256-140e350bd9b12bf0/model.pkl`
- Phase18 Promotion Candidate is separate and not Runtime eligible.
- Common PIT Dataset -> Split -> Training -> Calibration -> Validation -> Promotion -> Accepted -> Runtime Transition is not one connected Generation Pipeline.
- Latest Dataset does not imply latest AI.

Phase18-AC correctly proposed the single accepted generation loop, but it did not fully close Bootstrap, Data Sufficiency, Data Revision, Split Lifecycle, Training Reproducibility, Unified Compatibility, Automatic Approval Boundary, Runtime Transition Compatibility, Schema Migration, Legacy Removal Proof, Concurrency/Resume, Retention, External Dependency, Monitoring, Security, Failure Matrix, and Production-equivalent Acceptance.

## Current Production Call Graph

```text
LaunchAgent / CLI
-> run_daily_operation
-> market_refresh / data_readiness
-> produce_buy_ai_decisions
-> resolve_buy_ai_artifact_paths
-> Registry accepted component sets
-> Candidate inference
-> Opportunity inference
-> build_runtime_lifecycle_evidence
-> accepted_buy_ai_bundle.json resolver
-> evaluate_runtime_ai_gate
-> BUY planning or scoped BUY block
-> sell_planning / submit / execution / valuation / runtime_state
```

The current Runtime BUY AI path has a two-authority mismatch:

```text
Runtime inference authority = Registry accepted component sets
Lifecycle Gate authority = Accepted Atomic BUY AI Bundle
```

## Target Production Call Graph

```text
LaunchAgent / CLI
-> run_daily_operation
-> Accepted Generation Resolver
-> accepted_buy_ai_bundle.json
-> Candidate / Opportunity / Calibration / Baseline / Freshness from one generation
-> Runtime inference
-> Lifecycle Gate from the same generation
-> BUY scoped control
-> SELL continuity
-> Monitoring
-> Lifecycle Scheduler
-> Generation Pipeline
-> Authority
-> Atomic Accepted Transition
```

## Authority Count and Roles

Target BUY AI Runtime authority count is one:

```text
Accepted Atomic BUY AI Bundle
```

`Accepted AI Generation` remains only the operational name for that existing artifact concept. It is not a new Authority.

Other authorities remain separate by responsibility:

- Current / Pending / Ledger / Safety govern trading state and submit safety.
- Promotion Candidate remains pre-acceptance evidence.
- Registry component sets remain valid for non-BUY policy sets and audit history, but not as BUY Runtime model authority after cutover.

## Legacy Paths

Legacy BUY AI paths identified:

| Resolver | Caller | Environment | Authority | Production Reachable | Target State |
|---|---|---|---|---|---|
| `resolve_buy_ai_artifact_paths` | `produce_buy_ai_decisions` | Runtime | Registry component accepted set | Yes | Replace for BUY AI |
| `DEFAULT_CANDIDATE_MODEL_PATH` | isolated test path allowance | non-`.runtime` tests | direct test path | No | Keep only for tests |
| `DEFAULT_OPPORTUNITY_MODEL_PATH` | isolated test path allowance | non-`.runtime` tests | direct test path | No | Keep only for tests |
| Promotion Candidate transaction path | Authority review | Lifecycle | pre-acceptance evidence | No | Never fallback |

Legacy removal order is now fixed in the SoT amendment: parallel accepted resolver evidence, non-production smoke, Historical proof, production-equivalent cutover, component-set BUY removal, and negative tests.

## Added Design Contracts

Phase18-AD amended `docs/02_architecture/autonomous_ai_operations_architecture.md` with:

- Bootstrap Contract
- Data Sufficiency Contract
- Data Revision Contract
- Split Lifecycle Contract
- Training Environment Reproducibility
- Unified Component Compatibility
- Model Quality Contract
- Automatic Approval Boundary
- Runtime Transition Compatibility
- Schema Migration Contract
- Legacy Removal Proof
- Concurrency / Idempotency / Resume
- Storage / Retention / Integrity
- External Dependency Failure
- Monitoring and Alerting
- Security / Secrets Boundary
- Performance-independent Monitoring guard
- Failure Matrix requirement
- Production-equivalent Acceptance Contract
- Architecture Coverage Matrix completion rule
- Revised vertical implementation units AD-U1 through AD-U7

## Bootstrap Contract

No accepted generation means BUY remains blocked until a bootstrap accepted generation is produced through AI Lifecycle Control Plane, approved by Human Review, materialized atomically, and Runtime-smoked. `previous_generation_ref=null` is allowed only as explicit bootstrap metadata. Manual JSON creation is prohibited. SELL, Current, Valuation, PM, and Safety continue when their own authorities are healthy.

## Data Sufficiency Contract

Training must not start merely because files exist. Candidate and Opportunity must separately pass minimum business days, row count, eligible symbols, positive labels, missingness, universe/sector/market coverage, corporate action integrity, calendar coverage, label completion, label-safe horizon, source consistency, and duplicate/gap limits.

Insufficient data emits `NO_RETRAIN_INSUFFICIENT_NEW_DATA`; current Accepted continues unless current Accepted freshness/integrity blocks BUY.

## Split Lifecycle Contract

Every generation creates an immutable split policy artifact: Train, Calibration, Validation, Test, Recent Holdout, label horizon buffer, minimum business days, regime coverage, overlap rejection, split maintain conditions, holdout reuse count, and split policy version. Holdout retuning is prohibited, and split policy version changes require Human Review.

## Scheduler / Restart / Resume Contract

The current weekly scheduler has locks and idempotency artifacts, but it is not yet the full generation-to-accepted orchestrator. AD requires generation idempotency key, stage locks, stale lock evidence, transaction journal, resume artifact, retry policy, duplicate generation rejection, and process-kill recovery across Dataset, Split, Training, Calibration, Validation, Promotion, Accepted Transaction, Runtime Transition, and Rollback.

## Failure / Recovery Matrix

Evidence file:

```text
reports/phase18_ad_autonomous_ai_operations_architecture_closure_review/failure_matrix.json
```

The matrix covers raw data missing, partial normalized data, PIT rows missing, label-safe not advanced, insufficient training data, split overlap, training crash, missing model artifact, calibration mismatch, Validation BLOCK, promotion failure, Authority timeout, accepted transaction partial failure, Registry mismatch, Runtime accepted state missing, resolver hash mismatch, schema incompatibility, transition smoke failure, rollback failure, scheduler missed, duplicate execution, process restart, artifact corruption, disk full, current Accepted freshness BLOCK, drift REVIEW/BLOCK, no healthy previous generation, notification failure, and legacy resolver unexpectedly reached.

## Production-equivalent Acceptance

Completion requires static acceptance, real J-Quants-derived generation, Runtime transition smoke, multi-day Historical acceptance, failure injection, and autonomous operation acceptance. Mock-only evidence is not sufficient.

## Architecture Coverage Matrix

Evidence file:

```text
reports/phase18_ad_autonomous_ai_operations_architecture_closure_review/architecture_coverage_matrix.json
```

Result:

```text
VERIFIED_WITH_LIMITATION: 9
BLOCKED: 5
UNKNOWN: 0
IMPLEMENTATION_READY: false
```

Blocked areas are Split lifecycle, Authority materialization, Runtime Resolver authority unification, Runtime Transition, and Production-equivalent E2E acceptance.

## Revised Implementation Units

| Unit | Goal |
|---|---|
| AD-U1 | Bootstrap and Authority Unification |
| AD-U2 | Dataset-to-Split Sufficiency Slice |
| AD-U3 | Unified Generation Slice |
| AD-U4 | Validation-to-Authority Slice |
| AD-U5 | Atomic Runtime Transition Slice |
| AD-U6 | Autonomous Scheduler and Recovery Slice |
| AD-U7 | Production-equivalent E2E Slice |

The units are vertical slices. Legacy Runtime BUY AI resolution must be cut over by AD-U5, before AD-U7 acceptance.

## Implementation Readiness

Implementation can start on AD-U1, but the overall architecture is not implementation-ready as a complete autonomous system. `PHASE18_AD_IMPLEMENTATION_READY` is not allowed because the Coverage Matrix contains BLOCKED items and current Runtime inference still uses legacy component set authority while Lifecycle Gate uses accepted bundle authority.

## Evidence Artifacts

- `architecture_coverage_matrix.json`
- `current_and_target_call_graph.json`
- `authority_map.json`
- `legacy_path_inventory.json`
- `failure_matrix.json`
- `acceptance_contract.json`
- `implementation_dependency_graph.json`
- `unresolved_items.json`

## Non-Mutation Confirmation

- Dataset rebuild: `False`
- Split changed: `False`
- Retraining: `False`
- Calibration refit: `False`
- Model artifact created: `False`
- Registry changed: `False`
- Accepted state changed: `False`
- Runtime resolver changed: `False`
- Scheduler changed: `False`
- Runtime switch: `False`
- BUY restart: `False`
- Broker write: `False`
- Historical fresh-run: `False`
- Production Runtime executed: `False`

## Final

Primary:

```text
PHASE18_AD_ARCHITECTURE_AMENDMENT_REQUIRED
```

Secondary:

```text
PHASE18_AD_LEGACY_REMOVAL_PLAN_COMPLETE
PHASE18_AD_ACCEPTANCE_CONTRACT_COMPLETE
PHASE18_AD_IMPLEMENTATION_NOT_READY
```
