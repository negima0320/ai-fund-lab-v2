# Phase16-J AI Input, Output, Artifact, and Data Boundary Architecture

Prefix: Phase16-J

Work name: AI Input, Output, Artifact, and Data Boundary Architecture

## Final Judgment

`PHASE16_J_AI_INPUT_OUTPUT_ARTIFACT_ARCHITECTURE_ACCEPTED`

The permanent AI boundary architecture is defined for Production, Demo, Paper, and Historical operation. Current Runtime v2 implementation has enough evidence to classify Candidate AI, Opportunity AI, and Position Management boundaries, but Artifact Registry enforcement and several Phase-numbered physical paths remain migration gaps.

No Runtime change, AI change, feature regeneration, simulation, reset, or test execution was performed.

## Created Files

- `docs/02_architecture/ai_input_output_and_artifact_contract.md`
- `docs/phase_reports/phase16_j_ai_input_output_and_artifact_architecture.md`
- `reports/phase_reports/phase16_j_ai_input_output_and_artifact_contract.json`

## AI Inventory

| Component | Classification | Judgment | Evidence |
|---|---:|---:|---|
| Candidate AI | AI Model | ACCEPTED_WITH_GAPS | `runtime_v2.buy_ai.producer.produce_buy_ai_decisions()` reads Candidate Feature Artifact and Candidate model, writes `candidate_decisions.json`. |
| Opportunity AI | AI Model | MIGRATION_REQUIRED | `_produce_opportunity_artifact()` reads Candidate Decision Artifact, Opportunity Feature Artifact, model, and metrics, writes `opportunity_rankings.json`; metrics fallback currently points to Phase5-E. |
| Position Management | AI-like deterministic policy | ACCEPTED_WITH_GAPS | `produce_position_management_decisions()` reads Current, PM feature, and Opportunity context, writes `position_management_decisions.json`. |
| Policy | Non-AI Runtime control | BOUNDARY_DEFINED | Morning/Sell planning consume `CapitalDeploymentPolicy` and policy context. |
| Safety | Non-AI Runtime control | BOUNDARY_DEFINED | CLI loads Runtime Safety Decision before planning and submit. |
| Capital Allocation | Non-AI policy/allocation control | DESIGN_REVIEW_REQUIRED | Runtime policy path exists, but permanent artifact contract remains incomplete. |
| Submit Guard | Non-AI Runtime control | BOUNDARY_DEFINED | CLI invokes submit pipeline only under submit job and explicit submit-enabled flag. |

## Candidate Architecture

Accepted logical flow:

```text
Candidate Feature Artifact
+ Candidate Model Artifact
↓
Candidate AI
↓
Candidate Decision Artifact
```

Current evidence:

- Feature input path: `<feature_root>/<feature_date>/candidate_features.parquet`
- Current default model path: `.runtime/candidate_ai/models/phase4bf_formal_candidate_model.pkl`
- Output path: `.runtime/runtime_state/buy_ai/<business_date>/candidate_decisions.json`
- Output schema: `runtime_v2_candidate_decision_v1`

Gaps:

- Model path is Phase-numbered.
- Artifact Registry and input/output hashes are not centrally enforced.

## Opportunity Architecture

Accepted logical flow:

```text
Candidate Decision Artifact
+ Opportunity Feature Artifact
+ Opportunity Model / Metrics Artifact
↓
Opportunity AI
↓
Opportunity Decision Artifact
↓
Morning Planning
```

Current evidence:

- Candidate input: `candidate_decisions.json`
- Feature input: `<feature_root>/<feature_date>/opportunity_feature_input.parquet`
- Current default model path: `reports/opportunity_ai/phase5p/models/opportunity_model.pkl`
- Output path: `.runtime/runtime_state/buy_ai/<business_date>/opportunity_rankings.json`
- Output schema: `runtime_v2_opportunity_ranking_v1`
- Planning bridge: `load_ai_planning_signals_from_opportunity_artifact()`

Gaps:

- Omitted metrics path falls back to `reports/opportunity_ai/phase5e/opportunity_training_metrics.json`.
- Model/metrics registry identity is not yet enforced.

## Position Management Architecture

Accepted logical flow:

```text
Current
+ Position Feature Artifact
+ Opportunity Context
+ PM Code Policy
↓
Position Management
↓
PM Decision Artifact
↓
Sell Planning
```

Current evidence:

- Current input: `<runtime_root>/persistent_ledger/state.json`
- Feature input: `position_feature_input.parquet`
- Opportunity input: `pm_opportunity_path`
- Output path: `.runtime/runtime_state/position_management/<business_date>/position_management_decisions.json`
- Output schema: `runtime_v2_position_management_decision_v1`
- Sell bridge: `sell_exit_decisions` passed to `run_sell_planning_pending_pipeline()`

Gaps:

- PM code-policy hash and adapter hash are not centrally enforced in the output artifact.
- Standalone inference defaults reference Phase-numbered report artifacts; Runtime producer path must remain the authority.

## Artifact Registry

The architecture requires a central Artifact Registry covering:

- Raw Data Artifact
- Canonical Data Artifact
- Feature Artifact
- Model Artifact
- Code Policy Artifact
- AI Decision Artifact
- Training Artifact
- Acceptance Fixture
- Legacy Artifact

Required fields include artifact ID, type, schema version, producer, consumer, business date, feature date, source refs, source hashes, artifact path, artifact hash, point-in-time status, and Runtime-use eligibility.

Current status: `IMPLEMENTATION_REQUIRED`.

## Boundary

AI may read:

- Feature Artifacts
- Model Artifacts
- Code Policy Artifact for PM
- Candidate Decision Artifact as Opportunity input
- Current only for PM, through explicit Runtime producer contract

AI must not read:

- Raw Data directly
- Training datasets as Runtime input
- Label datasets
- Backtest outputs
- Phase-numbered reports as Source of Truth
- Broker, Ledger, Pending, Execution, or Current except the explicit PM Current input

Runtime may read:

- AI Decision Artifacts
- Policy
- Safety
- Current
- Pending
- Broker Evidence
- Ledger and Execution artifacts

Runtime must not use AI training or acceptance fixtures as decision authority.

## Current Gap

| Gap | Status |
|---|---:|
| Artifact Registry missing | IMPLEMENTATION_REQUIRED |
| Candidate model Phase-numbered path | MIGRATION_REQUIRED |
| Opportunity model Phase-numbered path | MIGRATION_REQUIRED |
| Opportunity metrics Phase5-E fallback | IMPLEMENTATION_REQUIRED |
| Decision artifact source hashes incomplete | IMPLEMENTATION_REQUIRED |
| PM code-policy hash not enforced centrally | IMPLEMENTATION_REQUIRED |
| Capital Allocation permanent artifact contract incomplete | DESIGN_REVIEW_REQUIRED |

## Migration Gap

Current physical paths can be mapped as temporary implementation evidence, but they are not Source of Truth by themselves. A later phase must register accepted artifacts and hashes without changing model behavior, feature semantics, or Runtime Mainline.

## Unresolved Items

- Final Artifact Registry implementation and storage path.
- Formal hash fields for Candidate, Opportunity, and PM decision artifacts.
- Canonical model registry paths that do not depend on Phase-numbered artifact names.
- Opportunity metrics source alignment with the default Phase5-P model.
- Capital Allocation artifact contract.

## Next Prefix

`Phase16-K`

Recommended next work: implement or design the Artifact Registry and model/metrics registry migration needed by this architecture. Do not run Historical Runtime Simulation until the registry and Source of Truth gaps are closed.
