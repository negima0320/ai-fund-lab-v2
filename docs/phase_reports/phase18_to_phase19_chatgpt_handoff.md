# Phase18 to Phase19 ChatGPT Handoff

## Project Goal

AI Fund Lab v2 must safely generate, validate, approve, accept, and atomically transition BUY AI generations from J-Quants-derived PIT data while preserving SELL continuity, Trading State, Safety, and Broker boundaries.

## Phase18 Final State

```text
Final Judgment:
PHASE18_DESIGN_COMPLETE

Supporting:
PHASE18_AF_FINAL_ARCHITECTURE_CONSISTENCY_PASS
PHASE18_AF_PHASE19_U1_READY

Architecture design:
COMPLETE

Architecture consistency:
PASS

Residual contradictions:
0
```

Phase18 completed design and handoff only. It did not complete autonomous operation implementation.

## Current Runtime / AI State

```text
Accepted Atomic BUY AI Bundle:
not yet materialized

Runtime BUY inference authority:
still legacy Registry accepted component sets

Lifecycle Gate authority:
Accepted Atomic BUY AI Bundle evidence

Runtime Authority unification:
not implemented

Rolling Split:
not implemented

Unified Generation:
not implemented

Atomic Runtime Transition:
not implemented

Autonomous Scheduler:
not implemented

Production-equivalent E2E:
not executed

BUY restart:
not allowed

Broker write:
not performed
```

Legacy Runtime models:

```text
Candidate:
.runtime/artifacts/ai/candidate/model/formal_candidate_model/sha256-2ea75d14d3fe3682/model.pkl

Opportunity:
.runtime/artifacts/ai/opportunity/model/formal_opportunity_model/sha256-140e350bd9b12bf0/model.pkl
```

Dataset / AI mismatch:

```text
Common PIT Dataset max date = 2026-05-15
Phase18 Promotion Candidate train end = 2024-12-02
latest Dataset != latest AI
```

## Final Architecture

Top-level SoT:

```text
docs/02_architecture/autonomous_ai_operations_architecture.md
```

Target loop:

```text
Market Data Update
-> Common PIT Dataset Update
-> Label-safe Availability
-> Data Sufficiency
-> Retraining Trigger
-> Versioned Rolling Split
-> Candidate / Opportunity / Calibration Generation Assembly
-> Independent Validation
-> Promotion Decision
-> Accepted Decision
-> Accepted Atomic BUY AI Bundle
-> Staged Runtime Transition
-> Smoke Verification
-> Atomic COMMITTED Pointer Switch
-> Runtime Inference
-> Freshness / Drift / Health Monitoring
-> Retraining or Rollback
```

`Accepted AI Generation` is only the operational name for `Accepted Atomic BUY AI Bundle`; it is not a new Authority.

## Authority Boundary

BUY AI Generation owns Dataset lineage, Split, Candidate, Opportunity, Calibration, Validation, Runtime baseline, Freshness metadata, hashes, Authority decision, Rollback reference, and Generation identity.

BUY AI Generation does not own Current, Pending, Ledger, PM, Safety, Broker Snapshot, Approval, Submit Guard, Execution, Broker write, cash, positions, or portfolio value.

BUY AI Lifecycle Gate controls BUY Planning or scoped BUY Block only. SELL continues only when SELL dependencies are healthy.

## Atomic Runtime Transition

States:

```text
PREPARED
STAGED
SMOKE_VERIFIED
COMMITTED
ABORTED
ROLLED_BACK
```

Production Runtime Resolver may read only the current `COMMITTED` Runtime accepted pointer.

Forbidden:

- latest directory / symlink
- filesystem mtime max
- accepted_at max
- Promotion Candidate fallback
- manual model path
- config direct path
- legacy component fallback

## Phase19 Units

Phase19 must use only:

1. `AD-U1 Bootstrap and Authority Unification`
2. `AD-U2 Dataset-to-Split Sufficiency Slice`
3. `AD-U3 Unified Generation Slice`
4. `AD-U4 Validation-to-Authority Slice`
5. `AD-U5 Atomic Runtime Transition Slice`
6. `AD-U6 Autonomous Scheduler and Recovery Slice`
7. `AD-U7 Production-equivalent E2E Slice`

First task:

```text
AD-U1 Bootstrap and Authority Unification
```

Do not start with AD-U2 or later. Do not implement the whole scheduler/retraining/transition/E2E flow in one step.

## Must-read Documents

- `docs/02_architecture/autonomous_ai_operations_architecture.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/runtime_test_specification.md`
- `docs/02_architecture/historical_runtime_test_contract.md`
- `docs/03_operations/runtime_test_command_guide.md`
- `docs/phase_reports/phase18_ab_runtime_legacy_model_provenance_and_ai_generation_pipeline_audit.md`
- `docs/phase_reports/phase18_ac_autonomous_ai_operations_architecture_design.md`
- `docs/phase_reports/phase18_ad_autonomous_ai_operations_architecture_closure_review.md`
- `docs/phase_reports/phase18_ae_autonomous_ai_operations_architecture_final_system_review.md`
- `docs/phase_reports/phase18_af_autonomous_ai_operations_architecture_final_consistency_amendment.md`
- `docs/phase_reports/phase18_final_summary_and_phase19_handoff.md`
- `docs/phase_reports/phase17_final_summary_and_phase18_handoff.md`
- `docs/01_requirements/phase_roadmap.md`

## Evidence Locations

- `reports/phase18_ad_autonomous_ai_operations_architecture_closure_review/`
- `reports/phase18_ae_architecture_final_system_review/`
- `reports/phase18_af_autonomous_ai_operations_architecture_final_consistency_amendment/`
- `reports/phase_reports/phase18_final_summary_and_phase19_handoff.json`

## Non-negotiable Rules

- Do not use Promotion Candidate directly at Runtime.
- Do not use latest/manual/legacy fallback.
- Do not create manual accepted JSON.
- Do not force BUY.
- Do not relax BV15.
- Do not ignore `no_buy_reason`.
- Do not use Paper Ledger, Broker Snapshot, PnL, selected/bought, cash, portfolio value, backtest profit, or future information for training or automatic promotion.
- Do not let BUY AI failure automatically stop SELL.
- Do not mutate Trading State during generation transition.
- Do not write to Broker.

## Current Known Blockers

- Accepted Atomic BUY AI Bundle not materialized.
- Runtime BUY inference still uses legacy component accepted sets.
- Lifecycle Gate and Runtime inference authority not unified.
- Rolling Split not implemented.
- Unified Candidate / Opportunity / Calibration / Baseline generation not implemented.
- Atomic COMMITTED Runtime pointer transition not implemented.
- Autonomous Scheduler not implemented.
- Production-equivalent E2E not executed.

## Final Warning

Do not call the system autonomous, production-ready, BUY-ready, or fully implemented. Phase18 is design complete. Phase19 begins implementation from AD-U1.
