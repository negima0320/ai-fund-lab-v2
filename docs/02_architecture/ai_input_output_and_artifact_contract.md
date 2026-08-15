# AI Input, Output, Artifact, and Data Boundary Contract

Status: Phase16-J accepted architecture draft

This document defines the permanent AI input/output and artifact boundary for Runtime v2. It applies to Production, Demo, Paper, and Historical operation. It is not a Phase16-only or Historical-only rule.

## Purpose

Runtime v2 must treat AI as a bounded producer of decision artifacts. AI may read accepted Feature Artifacts and frozen AI Artifacts. Runtime may consume AI Decision Artifacts. Neither side may silently depend on training datasets, label datasets, backtest outputs, Phase-numbered reports, or live Runtime authority objects outside the explicit contract.

The architecture is:

```text
Canonical Data
↓
Feature Artifact
↓
AI Artifact
↓
AI Decision Artifact
↓
Policy / Safety / Planning
↓
Runtime State Machine
```

## AI Inventory

| Component | Classification | Runtime role | Current evidence | Judgment |
|---|---:|---|---|---|
| Candidate AI | AI Model | Scores broad-market candidates for BUY consideration. | `runtime_v2.buy_ai.producer.produce_buy_ai_decisions()` reads `candidate_features.parquet` and a model artifact, then writes `candidate_decisions.json`. | ACCEPTED_WITH_GAPS |
| Opportunity AI | AI Model | Ranks Candidate AI output into BUY opportunity order. | `runtime_v2.buy_ai.producer._produce_opportunity_artifact()` reads `candidate_decisions.json`, `opportunity_feature_input.parquet`, an Opportunity model, and metrics. | MIGRATION_REQUIRED |
| Position Management | AI-like deterministic policy | Produces HOLD / EXIT / REDUCE / ADD decisions for existing positions. | `runtime_v2.position_management.producer.produce_position_management_decisions()` reads Current, PM feature, and Opportunity context, then writes `position_management_decisions.json`. | ACCEPTED_WITH_GAPS |
| Policy | Runtime control, not AI | Applies operational policy and sizing constraints. | Morning/Sell planning load `CapitalDeploymentPolicy` and policy hash context. | BOUNDARY_DEFINED |
| Safety | Runtime control, not AI | Allows, blocks, or halts Runtime action. | CLI loads Runtime Safety Decision before planning and submit. | BOUNDARY_DEFINED |
| Capital Allocation | Policy / allocation control, not AI in Runtime v2 contract | Produces or constrains budget/sizing. | Current Runtime planning accepts capital deployment policy; feature refresh also produces `capital_policy_input.parquet`. | BOUNDARY_DEFINED_WITH_REVIEW |
| Submit Guard | Runtime control, not AI | Validates Pending, approval, safety, freshness, and submit policy before Broker write. | CLI invokes `run_submit_pipeline()` only for submit job with explicit `--submit-enabled=true`. | BOUNDARY_DEFINED |

## Layer Responsibilities

| Layer | Owns | May consume | Must not consume | Output |
|---|---|---|---|---|
| Raw Data | Provider-origin evidence. | Provider API/file responses. | AI training labels as authority. | Raw artifacts and manifests. |
| Canonical Data | Accepted point-in-time market data. | Raw Data and calendar/listed/corporate-action evidence. | Runtime state, AI decisions. | Canonical normalized data refs. |
| Feature Artifact | Runtime AI input surface. | Canonical Data, Current only where explicitly required for PM position features. | AI model outputs, label datasets, backtest outputs. | Candidate, Opportunity, PM, Capital feature artifacts. |
| AI Artifact | Frozen scoring identity. | Training lineage for audit only. | Runtime Current, Pending, Ledger as hidden training input. | Model/policy refs, hashes, schema expectations. |
| AI Decision Artifact | Runtime-readable AI output. | Feature Artifact and AI Artifact. | Raw Data, training dataset, backtest result, Broker state except explicit PM Current input. | Candidate, Opportunity, PM decisions. |
| Policy / Safety / Planning | Runtime control. | AI Decision Artifacts, Current, Policy, Safety. | AI training datasets. | Plans, approvals, Pending candidates. |
| Runtime State Machine | Authority and state transitions. | Planning/Pending/Broker/Execution/Ledger/Current artifacts. | Raw AI training data as decision authority. | Pending, Execution, Ledger, Current, Runtime State, Reports. |

## Candidate AI Contract

Candidate AI selects purchase candidates from the accepted market feature universe.

### Inputs

Allowed:

- Candidate Feature Artifact: `<feature_root>/<feature_date>/candidate_features.parquet`
- Candidate Model Artifact: current default `.runtime/candidate_ai/models/phase4bf_formal_candidate_model.pkl`
- Explicit Runtime parameters: `business_date`, `feature_date`, `top_n`, `evaluation_time`

Prohibited:

- Raw Data
- Normalized Data directly
- Opportunity training datasets
- Backtest outputs
- Paper ledger
- Broker snapshots
- Current cash, holdings, Pending, Ledger, or Execution state
- Phase-numbered report artifacts as Source of Truth

Current evidence:

- `src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py` defines `DEFAULT_CANDIDATE_MODEL_PATH`.
- `produce_buy_ai_decisions()` resolves `candidate_feature_path = feature_dir / "candidate_features.parquet"`.
- `_produce_candidate_artifact()` reads the model pickle, validates model feature columns, audits leakage via `audit_inference_features()`, reads the feature parquet, scores, and writes Runtime artifact JSON.

### Output

Current path:

```text
.runtime/runtime_state/buy_ai/<business_date>/candidate_decisions.json
```

Current schema version:

```text
runtime_v2_candidate_decision_v1
```

Required logical fields:

- `schema_version`
- `business_date`
- `runtime_id`
- `model_version`
- `model_path`
- `model_hash`
- `feature_date`
- `feature_path`
- `feature_artifact_hash`
- `generated_at`
- `candidate_count`
- `rows[].symbol`
- `rows[].candidate_score`
- `rows[].candidate_rank`
- `rows[].reason`
- `point_in_time_evidence`

BUY Quality feature passthrough:

Candidate AI Decision Artifact must preserve the PIT multi-horizon feature
subset needed by downstream Adaptive BUY Quality when those fields are present
in `candidate_features.parquet`. It must not recalculate, zero-fill, or infer
these values. True missing values remain absent so BUY Quality can fail closed.
The propagated subset includes price momentum horizons, volatility, recent-move
z-scores, momentum deltas, trend, and volume momentum fields used by the
Momentum Trajectory authority.

Current gap:

- Current implementation records model path and feature path, but a formal Artifact Registry and required artifact hashes are not yet enforced in this contract.
- The default model path contains a Phase-numbered file name. It may remain as an implementation artifact temporarily, but it is not the Source of Truth concept.

## Opportunity AI Contract

Opportunity AI ranks accepted Candidate AI decisions into executable BUY opportunity order.

### Inputs

Allowed:

- Candidate AI Decision Artifact: `candidate_decisions.json`
- Opportunity Feature Artifact: `<feature_root>/<feature_date>/opportunity_feature_input.parquet`
- Opportunity Model Artifact: current default `reports/opportunity_ai/phase5p/models/opportunity_model.pkl`
- Opportunity Training Metrics Artifact for model calibration/evidence

Prohibited:

- Phase5 training datasets as Runtime input
- Backtest results
- Paper ledger
- Broker snapshots
- Current cash, holdings, Pending, Ledger, or Execution state
- Direct Raw or Normalized Data

Current evidence:

- `_produce_opportunity_artifact()` calls `run_opportunity_inference()` with `candidate_path`, `feature_path`, `model_path`, and `training_metrics_path`.
- `load_ai_planning_signals_from_opportunity_artifact()` converts `opportunity_rankings.json` to `AIPlanningSignal` for Morning Planning.
- `run_daily_operation.py` passes `buy_ai_result.ai_signals` into `run_morning_ai_planning_pending_pipeline()`.

### Output

Current path:

```text
.runtime/runtime_state/buy_ai/<business_date>/opportunity_rankings.json
```

Current schema version:

```text
runtime_v2_opportunity_ranking_v1
```

Required logical fields:

- `schema_version`
- `business_date`
- `runtime_id`
- `model_version`
- `model_path`
- `model_hash`
- `metrics_path`
- `metrics_hash`
- `feature_date`
- `candidate_artifact_path`
- `candidate_artifact_hash`
- `opportunity_feature_path`
- `opportunity_feature_hash`
- `generated_at`
- `ranking_count`
- `rankings[].symbol`
- `rankings[].opportunity_score`
- `rankings[].rank`
- `rankings[].expected_return`
- `rankings[].confidence`
- `rankings[].reason`
- `point_in_time_evidence`

BUY Quality feature passthrough:

Opportunity AI Ranking Artifact must preserve the PIT multi-horizon feature
subset needed by downstream Adaptive BUY Quality when those fields are present
in `opportunity_feature_input.parquet`. Opportunity AI must pass through the
canonical feature values, not recompute them from prices or model outputs. True
missing or malformed source fields remain absent/malformed for BUY Quality
fail-closed handling.

Current gap:

- Runtime default Opportunity model path is `reports/opportunity_ai/phase5p/models/opportunity_model.pkl`.
- If `--opportunity-training-metrics-path` is omitted, `_produce_opportunity_artifact()` falls back to `reports/opportunity_ai/phase5e/opportunity_training_metrics.json`.
- The fallback metrics path is not aligned with the default Phase5-P model identity and must be migrated before treating the artifact registry as complete.

## Position Management Contract

Position Management is an AI-like deterministic policy. It is governed like AI because it produces decision artifacts, but the current Runtime does not use an external trained model artifact for it.

### Inputs

Allowed:

- Runtime Current: `.runtime/persistent_ledger/state.json`
- Position Feature Artifact: `position_feature_input.parquet`
- Opportunity context: normally `opportunity_rankings.json` or an accepted equivalent opportunity artifact
- PM code-policy identity: `ai_fund_lab_v2.position_management_ai.inference.MODEL_VERSION`

Prohibited:

- Raw Data directly
- AI training datasets
- Backtest outputs
- Paper ledger as authority for Runtime decisions
- Broker snapshots except through Current / Broker Evidence boundaries
- Hidden liquidation or cleanup authority

Current evidence:

- `produce_position_management_decisions()` reads Current from `<runtime_root>/persistent_ledger/state.json`.
- `_validate_pm_input_contract()` validates Current, feature path, opportunity path, freshness, missing fields, and held symbols.
- `run_position_management_inference()` is called only after the input contract is ready.
- `_artifact_payload()` writes `position_management_decisions.json` with `model_version`, `inference_version`, input paths, decision counts, and decisions.

### Output

Current path:

```text
.runtime/runtime_state/position_management/<business_date>/position_management_decisions.json
```

Current schema version:

```text
runtime_v2_position_management_decision_v1
```

Required logical fields:

- `schema_version`
- `business_date`
- `runtime_id`
- `model_version`
- `inference_version`
- `code_policy_hash`
- `adapter_hash`
- `feature_date`
- `current_source`
- `current_hash`
- `pm_feature_source`
- `pm_feature_hash`
- `opportunity_source`
- `opportunity_hash`
- `generated_at`
- `decision_count`
- `decisions[].symbol`
- `decisions[].decision`
- `decisions[].reason`
- `decisions[].confidence`
- `decisions[].runtime_action`
- `point_in_time_evidence`

Current gap:

- Current implementation records input paths and versions, but does not yet enforce `code_policy_hash`, `adapter_hash`, or all input artifact hashes through a central registry.
- Standalone PM inference defaults still reference Phase-numbered report paths. Runtime producer path uses explicit Runtime inputs; standalone defaults must not be treated as Runtime Source of Truth.

## Policy, Safety, Capital Allocation, and Submit Guard Boundaries

Policy, Safety, Capital Allocation, and Submit Guard are not AI in this contract.

Policy may:

- read AI Decision Artifacts
- read Current
- apply explicit capital deployment and sizing rules
- record policy source, version, and hash

Policy must not:

- mutate AI Decision Artifacts
- retrain or select models
- read AI training datasets as Runtime input

Safety may:

- read Runtime Safety evidence
- allow, block, review, or halt actions
- attach safety decision IDs and policy versions to plans and Pending

Safety must not:

- rewrite AI decisions
- become a hidden investment model
- use Safety outcomes as AI training input without an explicit later training phase

Capital Allocation may:

- constrain buying power, exposure, per-order size, and total budget
- consume Opportunity Decision Artifacts and explicit policy inputs

Capital Allocation must not:

- select Candidate/Opportunity models
- read training or label datasets in Runtime
- silently override AI ranks without policy evidence

Submit Guard may:

- validate Pending, approval, safety, freshness, idempotency, unknown outcomes, and broker capability before Broker write

Submit Guard must not:

- score investments
- read Feature Artifacts or training datasets for investment judgment
- bypass Policy or Safety evidence

## Artifact Registry Contract

A central Artifact Registry is required as the durable contract across Production, Demo, Paper, and Historical modes.

Each registered artifact must include:

- `artifact_id`
- `artifact_type`
- `schema_version`
- `producer`
- `consumer`
- `business_date`
- `feature_date`
- `as_of`
- `generated_at`
- `source_artifact_refs`
- `source_hashes`
- `artifact_path`
- `artifact_hash`
- `runtime_use_allowed`
- `audit_use_allowed`
- `retention_class`
- `point_in_time_status`

Artifact types:

| Type | Runtime use | Audit use | Notes |
|---|---:|---:|---|
| Raw Data Artifact | No direct AI use | Yes | Provider-origin evidence. |
| Canonical Data Artifact | Feature producer only | Yes | Accepted point-in-time data. |
| Feature Artifact | AI input | Yes | Candidate/Opportunity/PM/Capital feature files. |
| Model Artifact | AI input | Yes | Frozen model identity. |
| Code Policy Artifact | PM input | Yes | Frozen PM code-policy identity. |
| AI Decision Artifact | Runtime input | Yes | Candidate/Opportunity/PM decisions. |
| Training Artifact | No | Yes | May explain model lineage, not Runtime input. |
| Acceptance Fixture | No | Yes | Test-only evidence. |
| Legacy Artifact | No | Yes | Historical documentation only until migrated. |

## Producer / Consumer Matrix

| Artifact | Producer | Current path | Consumer | Runtime use judgment |
|---|---|---|---|---|
| Candidate Feature Artifact | Feature Refresh | `.runtime/operations/feature_artifacts/<date>/candidate_features.parquet` | Candidate AI | ACCEPTED_WITH_REGISTRY_GAP |
| Opportunity Feature Artifact | Feature Refresh | `.runtime/operations/feature_artifacts/<date>/opportunity_feature_input.parquet` | Opportunity AI | ACCEPTED_WITH_REGISTRY_GAP |
| Position Feature Artifact | Feature Refresh | `.runtime/operations/feature_artifacts/<date>/position_feature_input.parquet` | Position Management | ACCEPTED_WITH_REGISTRY_GAP |
| Capital Policy Input | Feature Refresh | `.runtime/operations/feature_artifacts/<date>/capital_policy_input.parquet` | Capital policy/allocation design | REVIEW_REQUIRED |
| Candidate Model Artifact | Candidate AI training lineage | `.runtime/candidate_ai/models/phase4bf_formal_candidate_model.pkl` | Candidate AI | MIGRATION_REQUIRED_FOR_NAME_AND_REGISTRY |
| Opportunity Model Artifact | Opportunity AI training lineage | `reports/opportunity_ai/phase5p/models/opportunity_model.pkl` | Opportunity AI | MIGRATION_REQUIRED_FOR_NAME_AND_REGISTRY |
| Opportunity Metrics Artifact | Opportunity AI training lineage | `reports/opportunity_ai/phase5p/training/opportunity_training_metrics.json` preferred; current fallback can use Phase5-E | Opportunity AI | MIGRATION_REQUIRED |
| Candidate Decision Artifact | Runtime buy_ai producer | `.runtime/runtime_state/buy_ai/<date>/candidate_decisions.json` | Opportunity AI, Planning evidence | ACCEPTED_WITH_REGISTRY_GAP |
| Opportunity Decision Artifact | Runtime buy_ai producer | `.runtime/runtime_state/buy_ai/<date>/opportunity_rankings.json` | Morning Planning | ACCEPTED_WITH_METRICS_GAP |
| PM Decision Artifact | Runtime PM producer | `.runtime/runtime_state/position_management/<date>/position_management_decisions.json` | Sell Planning | ACCEPTED_WITH_REGISTRY_GAP |

Phase29-L21T-AY requires the actual Runtime market_refresh Feature Refresh
producer to materialize the Phase29-L21T-AV multi-horizon trajectory feature
facts in both Candidate and Opportunity feature artifacts:

```text
price_momentum_return_1d
price_momentum_return_3d
price_momentum_return_10d
recent_move_volatility_z_1d
recent_move_volatility_z_3d
momentum_5d_vs_20d_delta
momentum_1d_vs_5d_delta
```

These columns are raw PIT feature facts. They are not model retraining,
threshold policy, BUY_WAIT classification, Pending authority, Submit authority,
or SELL authority. Consumer readiness must remain fail-closed: the fix is to
materialize the producer columns, not to relax the consumer schema.

## Point-in-Time Rules

All AI inputs must be point-in-time valid for `business_date` and `feature_date`.

Required point-in-time fields:

- `business_date`
- `feature_date`
- `market_data_as_of`
- `listed_as_of`
- `current_as_of` for PM
- `generated_at`
- `evaluation_time`
- `source_artifact_hashes`

Rules:

- Feature data must not include observations after `feature_date`.
- Historical mode may set `business_date` and `evaluation_time`, but the artifact schema must remain identical to Production/Demo/Paper.
- Mode may change Broker boundary behavior, not AI input schema.
- AI outputs must be reproducible from accepted Feature Artifacts and frozen AI Artifacts.

## Current Gaps

| Area | Gap | Judgment |
|---|---|---:|
| Artifact Registry | No central registry is enforced for model, feature, and decision artifact hashes. | IMPLEMENTATION_REQUIRED |
| Candidate model path | Default model path contains Phase-numbered name. | MIGRATION_REQUIRED |
| Candidate decision hashes | Output records paths and schema evidence but not all required hashes. | IMPLEMENTATION_REQUIRED |
| Opportunity metrics | Default model is Phase5-P while omitted metrics fallback is Phase5-E. | IMPLEMENTATION_REQUIRED |
| Opportunity decision hashes | Output records paths and schema evidence but not all required hashes. | IMPLEMENTATION_REQUIRED |
| PM code-policy identity | PM records model/inference version, but central code-policy hash is not enforced in output. | IMPLEMENTATION_REQUIRED |
| Capital Allocation | Runtime boundary is policy-like, but final permanent artifact contract is incomplete. | DESIGN_REVIEW_REQUIRED |
| Phase artifacts | Several current physical paths include Phase-numbered names. They may be evidence or temporary storage, not Source of Truth. | MIGRATION_REQUIRED |

## Migration Rules

Migration must follow these rules:

- Do not promote Phase-numbered artifacts to Source of Truth by naming alone.
- First define logical artifact identity, registry fields, and acceptance rules.
- Then map current physical paths to registered artifacts with hashes.
- Preserve model behavior unless a later explicit retraining phase authorizes changes.
- Preserve feature calculation, feature schema, feature meaning, and feature cutoff.
- Preserve Runtime v2 Mainline.

## Acceptance Criteria

The architecture is accepted when:

- Candidate, Opportunity, and PM inputs are limited to allowed artifacts.
- AI Decision Artifacts contain source refs and hashes sufficient for replay and audit.
- Policy/Safety/Capital Allocation/Submit Guard are classified outside AI.
- Training, Acceptance Fixture, Legacy, and Phase-numbered artifacts are excluded from Runtime Source of Truth unless registered through a later migration.
- Production, Demo, Paper, and Historical share the same logical artifact contract.
