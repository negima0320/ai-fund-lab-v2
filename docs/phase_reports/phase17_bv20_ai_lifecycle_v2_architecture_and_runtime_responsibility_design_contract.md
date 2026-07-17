# Phase17-BV20 AI Lifecycle v2 Architecture and Runtime Responsibility Design Contract

## Executive Summary

Phase17-BV20 created the formal AI Lifecycle v2 architecture contract. This was design-only. No implementation, retraining, dataset rebuild, Registry update, Runtime change, Runtime Test, LaunchAgent change, `.runtime` edit, J-Quants fetch, broker write, order submit, or notification was executed.

Final judgments:

```text
AI_LIFECYCLE_V2_DESIGN_COMPLETE
RUNTIME_RESPONSIBILITY_DEFINED
TRAINING_RESPONSIBILITY_DEFINED
PROMOTION_AUTHORITY_DEFINED
FRESHNESS_CONTRACT_DEFINED
DRIFT_CONTRACT_DEFINED
ROLLBACK_CONTRACT_DEFINED
IMPLEMENTATION_READY
REVIEW_REQUIRED
```

`REVIEW_REQUIRED` remains because BV20 is a design contract only. Exact implementation choices such as feature PSI baseline window, scheduler mechanism, final rollback event schema, and public report wording must be resolved during BV21-BV27.

## Design Deliverable

Created:

```text
docs/02_architecture/ai_lifecycle_v2.md
```

Additional BV20 addendum incorporated:

- `docs/02_architecture/ai_lifecycle_v2.md` is the formal AI Fund Lab v2-wide Single Source of Truth for AI lifecycle architecture.
- Phase reports record change history and review decisions only; the durable specification is centralized in the architecture document.
- The design applies to Candidate AI, Opportunity AI, Position Management AI, Safety / Safety Policy Engine, and future AI components.
- Future AI components must be onboarded by adding a lifecycle entry to the common architecture document rather than creating a separate lifecycle.

The design separates:

- Runtime Data Plane
- Runtime Control Plane
- AI Lifecycle Control Plane
- Artifact Registry
- Operator / Authority
- Monitoring / Alerting

Core policy:

```text
DAILY_INFERENCE
WEEKLY_RETRAIN
```

## Responsibility Summary

| Plane | Owns | Must Not Do |
| --- | --- | --- |
| Runtime Data Plane | daily feature/inference/planning/submit/execution/current/ledger | train, self-promote, fit calibrator, write Registry accepted event |
| Runtime Control Plane | daily orchestration, model age gate, dataset freshness gate, drift gate, lifecycle trigger coordination | approve models, mutate training data, self-promote |
| AI Lifecycle Control Plane | label-safe cutoff, PIT dataset rebuild, train, validation, recent holdout, leakage/drift/calibration audit, promotion request | write `ARTIFACT_ACCEPTED`, switch Runtime paths |
| Artifact Registry | accepted identity, hash, set consistency, consumer compatibility, Runtime discovery, rollback target | judge model profitability |
| Operator / Authority | promotion approval, Registry accepted authorization, rollback approval, emergency revoke, BUY re-enable | override missing evidence, ignore hash/schema/freshness failures |

## AI Component Coverage

The common architecture now defines every current AI component using the same lifecycle format:

| Component | Classification | Lifecycle |
| --- | --- | --- |
| Candidate AI | Trainable | PIT dataset, retrain, validation, Registry artifact set, Runtime accepted-set consumption |
| Opportunity AI | Trainable | Candidate-lineage-aware PIT dataset, retrain, validation, calibration, BV14/BV15 compatibility, Registry artifact set |
| Position Management AI | Rule-based current implementation | Code-policy / adapter evidence, semantic regression, Registry/authority acceptance, SELL Planning consumption |
| Safety / Safety Policy Engine | Policy Engine current implementation | Safety policy/evidence lifecycle, fail-closed validation, authority approval, Runtime safety authority consumption |

Trainable future variants of PM or Safety must be added to the SoT before implementation.

## Key Design Decisions

1. AI data update is not solely Runtime's responsibility. Runtime owns operational data refresh; AI Lifecycle owns training data readiness.
2. Dataset rebuild is AI Lifecycle Control Plane responsibility.
3. Retrain is AI Lifecycle Control Plane responsibility.
4. Promotion is Operator / Authority plus Registry responsibility.
5. Runtime enforces model age for BUY.
6. Runtime enforces dataset freshness for BUY.
7. Runtime daily operation does not directly execute training.
8. Weekly retrain failure keeps Champion only if Champion still passes freshness/drift gates.
9. Expired Champion causes `BUY BLOCK`.
10. SELL continues if SELL-specific dependencies pass.
11. Promotion is authority approved, not automatic.
12. Runtime switches models at the next job boundary after Registry acceptance.
13. Rollback is Registry-mediated, not model path edit.
14. Candidate updates before Opportunity; Opportunity validation references Candidate lineage.
15. Daily inference and weekly retrain are separated by locks and next-run discovery.

## Freshness Contract

Defined fields:

```text
market_data_max_date
feature_data_max_date
training_dataset_max_date
label_safe_cutoff
model_training_cutoff
model_created_at
model_accepted_at
model_age_business_days
dataset_age_business_days
```

BUY gate design:

- model age `> 20` business days: `BUY BLOCK`
- dataset age `> 20` business days: `BUY BLOCK`
- label-safe cutoff and training cutoff lag `> 20bd`: `BUY BLOCK`
- lag `> 5bd`: `REVIEW_REQUIRED`
- accepted model training lineage missing: `BUY BLOCK`
- future-dated training cutoff: `HALT`

SELL remains separate and should continue when SELL dependencies are healthy.

## Drift Contract

Defined metrics:

```text
feature PSI
prediction score mean
prediction positive rate
top1 score
all-negative consecutive days
candidate population distribution
recent ranking performance
calibration error
```

Recommended thresholds:

- feature PSI review `>0.20`, block `>0.30`
- all-negative predictions review at 3 consecutive business days
- positive-rate collapse below 25% baseline for 3 days
- top1 score `<=0` for 3 business days -> review
- promotion candidate recent holdout failure -> Champion maintained

## Promotion Contract

Promotion target members:

```text
MODEL
METRICS
FEATURE_SCHEMA
TRAINING_METADATA
TRAINING_DATA_LINEAGE
VALIDATION_EVIDENCE
CONSUMER_COMPATIBILITY
FRESHNESS_EVIDENCE
DRIFT_EVIDENCE
ROLLBACK_METADATA
```

Required sequence:

```text
Promotion Readiness PASS
-> Authority Review
-> Registry ARTIFACT_ACCEPTED
-> Materialized index/checkpoint update
-> Runtime next operation discovers new accepted set
```

## Rollback Contract

Rollback is Registry-mediated. Runtime must not change local model paths manually.

If a previous accepted set is eligible, Registry can accept or restore that target through authority. Runtime discovers it on the next job boundary. If no eligible rollback exists, BUY blocks while SELL continues if independent SELL authorities pass.

## Failure Semantics

Failure semantics are defined in `failure_semantics.json` and in `docs/02_architecture/ai_lifecycle_v2.md`.

Important boundary:

```text
AI lifecycle failures do not automatically stop SELL.
BUY stops when model freshness, dataset freshness, drift, or accepted artifact resolution fails.
```

## Implementation Roadmap

| Phase | Scope |
| --- | --- |
| BV21 | Dataset Rebuild Pipeline |
| BV22 | Training / Validation / Challenger Pipeline |
| BV23 | Promotion Readiness and Artifact Packaging |
| BV24 | Registry Promotion Operator |
| BV25 | Runtime Freshness / Drift Gates |
| BV26 | Weekly Scheduler and Monitoring |
| BV27 | End-to-End AI Lifecycle Acceptance |

Each step is documented with scope, input, output, acceptance criteria, forbidden operations, rollback, and tests in `implementation_roadmap.json`.

## Open Items

The design intentionally leaves these as implementation-phase review items:

- exact feature PSI baseline window per AI
- exact recent ranking gate thresholds by market regime
- public report wording for AI health without overexposing internal model details
- dedicated LaunchAgent vs Runtime Control Plane weekly trigger implementation
- exact Registry event schema for `SUPERSEDED` if added beyond existing state vocabulary

## Evidence Files

- `docs/02_architecture/ai_lifecycle_v2.md`
- `reports/phase17_bv20_ai_lifecycle_v2_architecture_and_runtime_responsibility_design_contract/summary.json`
- `reports/phase17_bv20_ai_lifecycle_v2_architecture_and_runtime_responsibility_design_contract/responsibility_matrix.json`
- `reports/phase17_bv20_ai_lifecycle_v2_architecture_and_runtime_responsibility_design_contract/lifecycle_state_machine.json`
- `reports/phase17_bv20_ai_lifecycle_v2_architecture_and_runtime_responsibility_design_contract/failure_semantics.json`
- `reports/phase17_bv20_ai_lifecycle_v2_architecture_and_runtime_responsibility_design_contract/freshness_contract.json`
- `reports/phase17_bv20_ai_lifecycle_v2_architecture_and_runtime_responsibility_design_contract/drift_contract.json`
- `reports/phase17_bv20_ai_lifecycle_v2_architecture_and_runtime_responsibility_design_contract/promotion_contract.json`
- `reports/phase17_bv20_ai_lifecycle_v2_architecture_and_runtime_responsibility_design_contract/rollback_contract.json`
- `reports/phase17_bv20_ai_lifecycle_v2_architecture_and_runtime_responsibility_design_contract/scheduler_contract.json`
- `reports/phase17_bv20_ai_lifecycle_v2_architecture_and_runtime_responsibility_design_contract/implementation_roadmap.json`
- `reports/phase17_bv20_ai_lifecycle_v2_architecture_and_runtime_responsibility_design_contract/evidence_inventory.json`
- `reports/phase_reports/phase17_bv20_ai_lifecycle_v2_architecture_and_runtime_responsibility_design_contract.json`

## Prohibited Operations Confirmation

Not executed:

- dataset rebuild
- train / retrain
- model generation
- Registry update
- Runtime change
- Runtime Test
- LaunchAgent change
- `.runtime` manual edit
- J-Quants fetch
- broker write
- order submit
- notification
