# Phase18-AC Autonomous AI Operations Architecture Design

- Phase: `Phase18-AC`
- Primary Judgment: `PHASE18_AC_ARCHITECTURE_CONSOLIDATION_REQUIRED`
- Secondary Judgment: `PHASE18_AC_AUTONOMOUS_AI_OPERATIONS_DESIGN_COMPLETE`
- Main Design: `docs/02_architecture/autonomous_ai_operations_architecture.md`

## Current AI Structure

Runtime BUY AI currently resolves Registry accepted component sets:

- Candidate: `.runtime/artifacts/ai/candidate/model/formal_candidate_model/sha256-2ea75d14d3fe3682/model.pkl`
- Opportunity: `.runtime/artifacts/ai/opportunity/model/formal_opportunity_model/sha256-140e350bd9b12bf0/model.pkl`

Phase18 Promotion Candidate is separate:

- Candidate train end: `2024-12-02`
- Opportunity train end: `2024-12-02`
- `runtime_use_eligible=false`
- no Accepted Atomic BUY AI Bundle exists

## Automated Today

- Runtime market refresh
- Runtime feature/inference path
- Registry accepted component-set resolution
- Freshness / drift gate evaluation
- fail-closed BUY behavior
- scoped BUY block
- SELL continuity

## Manual / Unconnected / Legacy

- Common PIT Dataset to retraining is not automatically chained.
- Split refresh is not guaranteed after dataset refresh.
- Candidate / Opportunity / Calibration are not generated as one accepted generation.
- Promotion Candidate is not Runtime eligible.
- Accepted Atomic BUY AI Bundle is missing.
- Runtime uses legacy accepted component sets, not Phase18 atomic generation.

## Target Architecture

Target architecture is an autonomous loop:

```text
Market Data
-> Common PIT Dataset
-> Label-safe availability
-> Retraining trigger
-> Rolling split
-> Candidate training
-> Opportunity training
-> Calibration
-> Validation
-> Promotion
-> Authority
-> Accepted AI Generation
-> Atomic Runtime transition
-> Runtime inference
-> Monitoring
-> Next generation
```

`Accepted AI Generation` is the operational name for the existing Accepted Atomic BUY AI Bundle concept. It is not a new parallel authority.

## Authority Boundary

Runtime must resolve only one authority:

```text
Accepted AI Generation
```

The same generation must provide:

- inference model refs
- freshness metadata
- drift baseline
- lineage
- rollback reference
- runtime health evidence

Production-equivalent Runtime must not use legacy direct paths, latest paths, config direct paths, manual paths, or Promotion Candidate fallback.

## Existing Implementation Decisions

| Area | Decision |
|---|---|
| Dataset pipeline | `KEEP/MODIFY` |
| Training pipeline | `KEEP/MODIFY` |
| Calibration | `KEEP/MERGE` |
| Lifecycle Scheduler | `MODIFY` |
| Promotion Candidate | `MERGE` |
| Registry | `KEEP/MODIFY` |
| Authority workflow | `MERGE` |
| Runtime baseline | `KEEP/MERGE` |
| Freshness metadata | `KEEP/MERGE` |
| Runtime resolver | `MODIFY` |
| Legacy resolver | `DEPRECATE` |
| Rollback | `KEEP/MODIFY` |
| Runtime Test Runner | `MODIFY` |

## Human Approval Boundary

Recommended mode:

- Low-risk refresh with all gates PASS: automatic Accepted Decision and atomic transition allowed.
- Material model/schema/strategy change: human review required.
- BLOCK / hash mismatch / lineage mismatch: rejected until remediation.
- Emergency rollback: pre-authorized rollback to previous generation, with operator evidence.

## Retraining Trigger

Trigger evaluation uses:

- label-safe cutoff advancement
- model training lag
- dataset version change
- feature schema change
- drift
- all-negative sequence
- model health
- cooldown
- minimum new sample count
- previous generation status

The trigger emits a lifecycle decision artifact. If evidence is insufficient, it fails closed for BUY only when the current accepted generation violates gates.

## Rolling Split Policy

Each generation must produce a new immutable split from current label-safe dataset authority:

- Train
- Calibration
- Validation
- Test
- Recent Holdout

Fixed reuse of old split definitions after dataset refresh is prohibited.

## Failure / Recovery

Failures keep the current accepted generation unless the current generation itself violates runtime gates.

- BUY blocks on missing/mismatched/stale AI authority.
- SELL continues when Current, PM, Safety, and Broker dependencies are healthy.
- Accepted transaction or Runtime transition failure restores previous accepted generation atomically.
- Partial artifacts are not published.

## Next Implementation Units

1. Generation identity, Dataset authority, Rolling Split
2. Candidate / Opportunity / Calibration unified generation run
3. Validation, Promotion, Accepted Transaction
4. Runtime Accepted-only Resolver and Atomic Transition
5. Scheduler, Trigger, Monitoring, Recovery
6. Production-equivalent End-to-End Acceptance

## Acceptance Conditions

The system can be considered safe for autonomous AI operation only when:

- one accepted generation drives inference, freshness, drift, baseline, and rollback
- dataset update triggers retraining evaluation
- fresh AI generation can be produced without manual file edits
- accepted transition is atomic
- low-risk PASS transitions can be automated
- material changes require human review
- BUY fails closed on AI evidence issues
- SELL continuity remains intact
- rollback is verified

## Non-Mutation Confirmation

- Dataset rebuild: `False`
- Split changed: `False`
- Candidate retrained: `False`
- Opportunity retrained: `False`
- Calibration refit: `False`
- Model artifact created: `False`
- Baseline regenerated: `False`
- Promotion Candidate created: `False`
- Registry changed: `False`
- Accepted Event created: `False`
- Runtime accepted state created: `False`
- Runtime resolver changed: `False`
- Scheduler changed: `False`
- Runtime switch: `False`
- BUY forced: `False`
- Broker write: `False`
- Production Runtime executed: `False`
- Historical fresh-run executed: `False`

## Final

`PHASE18_AC_ARCHITECTURE_CONSOLIDATION_REQUIRED`

## Phase18-AD Amendment Notice

Phase18-AD performed a closure review of this design against Phase18-AB systemic generation findings and repository call graph evidence.

The Phase18-AC judgment above is not changed. Phase18-AD adds implementation-SoT contracts to `docs/02_architecture/autonomous_ai_operations_architecture.md`, including Bootstrap, Data Sufficiency, Data Revision, Split Lifecycle, Training Reproducibility, Unified Compatibility, Automatic Approval Boundary, Runtime Transition Compatibility, Legacy Removal Proof, Concurrency/Resume, Storage/Retention, External Dependency Failure, Monitoring, Security, Failure Matrix, and Production-equivalent Acceptance.

Phase18-AD supersedes the original six implementation units with vertical slices AD-U1 through AD-U7. Phase18-AC remains the target architecture baseline; Phase18-AD is the closure amendment required before implementation.
