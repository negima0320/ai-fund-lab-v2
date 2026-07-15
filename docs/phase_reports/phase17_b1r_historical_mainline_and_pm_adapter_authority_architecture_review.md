# Phase17-B1R Historical Mainline Exposure and PM Adapter Authority Architecture Review

## Final Judgment

Final judgment: `PHASE17_B1R_CONTRACT_AMENDMENT_REQUIRED`

Recommended next prefix:

```text
Phase17-B1I-A Historical Environment Composition
Phase17-B1I-B PM Adapter Authority Resolution
Phase17-B1I-C Canonical / Point-in-time / Feature Readiness
Phase17-B1I-D 5BD Entry Gate Revalidation
```

Phase17-B1R was a read-only Architecture Review. No Runtime code, CLI code, Submit code, Execution code, PM producer code, Registry, Artifact Acceptance record, Trading State, Current, Ledger, Pending, Feature Artifact, Canonical Data, Historical Broker execution, Tachibana API access, Demo submit, Production access, or 5BD execution was changed.

## Reviewed Materials

Required materials reviewed:

- `docs/phase_reports/phase17_a_integrated_system_test_and_production_readiness_strategy.md`
- `reports/phase_reports/phase17_a_integrated_system_test_and_production_readiness_strategy.json`
- `docs/phase_reports/phase17_b_historical_runtime_readiness_revalidation_and_5bd_preparation.md`
- `reports/phase_reports/phase17_b_historical_runtime_readiness_revalidation_and_5bd_preparation.json`
- `docs/phase_reports/phase17_b1_historical_runtime_test_support_and_5bd_smoke.md`
- `reports/phase_reports/phase17_b1_historical_runtime_test_support_and_5bd_smoke.json`
- `docs/phase_reports/phase16_final_summary_and_phase17_handoff.md`
- `reports/phase_reports/phase16_final_summary_and_phase17_handoff.json`
- `docs/phase_reports/phase16_ax_operational_data_foundation_final_conformance_and_ai_integrity_audit.md`
- `reports/phase_reports/phase16_ax_operational_data_foundation_final_conformance_and_ai_integrity_audit.json`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/historical_runtime_test_contract.md`
- `docs/02_architecture/runtime_temporal_freshness_contract.md`
- `docs/02_architecture/operational_data_architecture.md`
- `docs/02_architecture/operational_lifecycle_state_reset_and_environment_transition_contract.md`
- `docs/02_architecture/ai_input_output_and_artifact_contract.md`
- `docs/02_architecture/ai_artifact_registry_and_capital_allocation_contract.md`
- `docs/02_architecture/artifact_acceptance_contract.md`
- `docs/02_architecture/artifact_acceptance_authority_and_promotion_workflow_contract.md`
- `docs/02_architecture/artifact_path_registry_integration_and_migration_contract.md`

Current code inspected read-only:

- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/simulation/broker.py`
- `src/ai_fund_lab_v2/runtime_v2/simulation/harness.py`
- `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py`
- `src/ai_fund_lab_v2/runtime_v2/artifact_lookup.py`
- `src/ai_fund_lab_v2/runtime_v2/historical_support/`

## Current Architecture

The accepted architecture already separates:

- `run_type=HISTORICAL` as a lifecycle environment;
- normal `.runtime` as the active Runtime root;
- Current / Ledger / Pending / Runtime State as resettable Runtime authority;
- Registry / accepted artifacts / canonical data as persistent operational foundation;
- Broker boundary as the permitted environment-specific replacement point.

The current implementation is narrower than the architecture:

- CLI exposes `--mode simulation`, but `_validate_rehearsal_args()` rejects non-demo jobs except limited safety paths.
- `run_submit_pipeline()` has an `adapter` seam, but blocks `mode != "demo"` before adapter selection.
- `run_execution_readonly_pipeline()` has a `snapshot_provider` seam, but accepts only `demo` and `production`.
- `SimulationBroker` is broker-boundary-only in isolation, but `run_simulation_replay()` is a separate harness and cannot be the official Historical Runtime mainline.
- PM producer resolves the accepted PM set and requires `RUNTIME_ADAPTER`, but executes the current source file imported from `src/.../position_management/producer.py`.

## Problem Statement

### Historical Mainline Problem

The issue is not that Historical Runtime is architecturally prohibited. The Lifecycle and Historical Runtime contracts already require Historical execution through the normal Runtime v2 Mainline with only the broker boundary replaced.

The current problem is an implementation and contract exposure gap:

```text
HISTORICAL environment is architecturally intended
but not formally exposed through CLI / Submit / Execution composition.
```

Because `submit` and `execution` are non-idempotent or authority-sensitive boundaries, simply bypassing CLI or forcing adapter injection outside the official composition path would reduce Production equivalence.

### PM Adapter Authority Problem

The accepted PM set contains a `RUNTIME_ADAPTER` snapshot with hash:

```text
6ffa7da2b91f5fd5cfa76aa4c487e6e6cf5e1293ba929fe374abd61aaadb7d1b
```

The currently executed PM source hash is:

```text
0e238f497dbc4b558cf4e955450ac0d63feb71d3f656f958b92d222f9086b8e5
```

Runtime gates on accepted adapter existence and hash, but the Python import executes the source tree file. That means the accepted artifact and the deployed execution body are not currently the same authority object.

## Contract Interpretation

Historical exposure can be handled inside the existing architectural model if `HISTORICAL` becomes a formal environment composition, not a separate Runtime:

```text
run_type=HISTORICAL
runtime_mode=historical or simulation, as formally named
broker_environment=historical_simulated
runtime_root=.runtime
```

This requires a limited contract amendment because current CLI and pipeline mode gates recognize `demo` / `production` operational modes, while the Lifecycle contract recognizes `HISTORICAL` as an environment. The amendment should align those layers.

PM authority can be handled inside the existing Acceptance model if the current source path is explicitly accepted as an `ACCEPTED_CURRENT_PATH`. The Artifact Path contract already permits a current source-code path exception only when architecture declares the source path to be the permanent operational artifact path and Acceptance / Release Approval are recorded.

## Historical Exposure Options

| Option | Summary | Pros | Cons | Judgment |
|---|---|---|---|---|
| A. Environment-selected Broker Boundary | Formal environment composition selects Submit Adapter and Execution Snapshot Provider for `run_type=HISTORICAL`. | Preserves normal `.runtime`, normal CLI, Submit Guard, Execution Processor, Ledger, Current, and environment boundary. | Requires CLI/pipeline composition implementation and explicit external effect guard. | Recommended design core |
| B. Existing CLI Composition Injection | External runner injects existing adapter seams and calls jobs. | Lower immediate code change if kept outside CLI. | Risks becoming a parallel mainline and losing official manifest/audit equivalence. | Reject as official mainline; may be implementation helper only if it invokes the official CLI/composition contract |
| C. Historical Mode as Formal Runtime Environment | Promote `simulation` from test-ish mode to formal `HISTORICAL` environment. | Aligns current `--mode simulation` surface with lifecycle. | Needs contract naming cleanup and mode validation changes. | Recommended amendment paired with Option A |
| D. No Safe Exposure | Conclude Runtime architecture cannot expose Historical safely. | Conservative. | Too strong; contracts already define Historical boundary replacement. | Not adopted |

## Recommended Historical Exposure Design

Adopt Option A plus Option C:

```text
Formal Historical Environment Composition
```

Design:

```text
run_type=HISTORICAL
broker_environment=historical_simulated
runtime_root=.runtime
Submit Adapter=HistoricalSimulatedBrokerSubmitAdapter
Execution Snapshot Provider=HistoricalExecutionSnapshotProvider
external_delivery=false
```

The normal job sequence remains:

```text
Market / Data Readiness
Feature
Candidate / Opportunity
PM / Sell Planning
Safety / Policy / Capital Allocation
Pending
Submit Guard
Historical Broker Boundary
Execution Processor
Ledger / Current
Runtime State
Report / Audit
```

Required contract amendment:

- Define formal `HISTORICAL` Runtime environment composition.
- Decide CLI naming: either `--mode historical` or keep `--mode simulation` with `run_type=HISTORICAL`; prefer `--mode historical` for clarity and keep `simulation` as compatibility alias only if needed.
- Define `broker_environment=historical_simulated`.
- Define no-external-effect semantics: Tachibana API, Demo write, Production write, notification delivery, Discord, LINE, Blog publish all disabled.
- Define manifest fields: `simulation=true`, `historical_replay=true`, `broker_write=false`, `production_equivalent=false`, `acceptance_only=false`, `external_delivery=false`.

Required implementation scope:

- Environment composition resolver outside Runtime Core.
- CLI validation update for formal Historical environment.
- Submit pipeline mode gate update to allow the formal Historical environment only when a historical adapter is selected and external effects are disabled.
- Execution readonly mode gate update to allow the formal Historical environment only when a historical snapshot provider is selected.
- Historical broker adapter completion against the broker contract.
- Historical execution snapshot provider.
- Regression tests proving Demo/Production adapter selection and behavior remain unchanged.

This is a limited contract and implementation amendment, not a Runtime Core redesign.

## PM Authority Options

| Option | Summary | Pros | Cons | Judgment |
|---|---|---|---|---|
| A. Current source formal Acceptance | Register and accept the current executed source as the PM `RUNTIME_ADAPTER` member. | Minimal Runtime change; aligns accepted authority with actual deployed code. | Requires new PM Artifact Set, regression, old set legacy transition. | Recommended |
| B. Execute frozen accepted adapter | Runtime dynamically imports `.runtime/artifacts/.../runtime_adapter.py`. | Byte identity between accepted snapshot and executed file. | Adds dynamic import/security/package context risk and changes execution path. | Reject for this phase |
| C. Reclassify adapter as Identity Evidence | Adapter member proves source version/hash rather than being imported. | Matches current source-tree deployment style. | Needs explicit contract wording and fail-closed source hash check. | Adopt as part of Option A |
| D. Architecture Gap | Current gate-only behavior is not enough. | Correctly names current risk. | Does not provide resolution alone. | Current state classification, not final design |

## Recommended PM Authority Design

Adopt Option A with Option C semantics:

```text
Accept current executed PM source as the PM Runtime Adapter authority
using an ACCEPTED_CURRENT_PATH exception.
```

The next PM artifact set should:

- use the current executed source path as the `RUNTIME_ADAPTER` physical path;
- bind hash `0e238f497dbc4b558cf4e955450ac0d63feb71d3f656f958b92d222f9086b8e5`;
- include `CODE_POLICY`, `RUNTIME_ADAPTER`, `POLICY_VERSION`, `FEATURE_VERSION`, `BEHAVIOR_CONTRACT`, `REGRESSION_EVIDENCE`, and `CONSUMER_COMPATIBILITY`;
- mark the old PM set or old adapter snapshot `LEGACY` when replacement is complete;
- fail closed if the deployed source hash differs from the accepted `RUNTIME_ADAPTER` hash;
- keep Historical / Demo / Production on the same authority.

Required contract amendment:

- Clarify that PM `RUNTIME_ADAPTER` may be an executable source-tree current path only under `ACCEPTED_CURRENT_PATH`.
- Clarify that in this mode the adapter artifact is identity evidence binding deployed source, not a copied module imported from `.runtime/artifacts`.
- Require startup / preflight source hash verification before PM inference.
- Require new Acceptance evidence if the source hash changes.

Required implementation scope:

- Formal PM Artifact Set registration / validation / acceptance for current source.
- Old PM artifact set replacement / legacy event.
- Runtime lookup or PM preflight hash check that compares the executing source file to accepted `RUNTIME_ADAPTER`.
- PM semantic regression, Sell Planning regression, Current/Ledger/Pending unchanged regression.
- No monkey patching, import rewrite, or manual copy.

## Production Equivalence

The recommended Historical design remains production-equivalent at the Runtime control layers:

- normal `.runtime`;
- normal Current / Ledger / Pending;
- normal Registry Resolver;
- normal Feature / AI / Planning / Pending path after later data readiness work;
- normal Submit Guard;
- normal Execution Processor;
- normal Ledger and Current projection.

It is not production-equivalent at the broker boundary by design:

```text
broker_environment=historical_simulated
broker_write=false
production_equivalent=false
```

This distinction must be explicit in every manifest and report.

## Demo / Production Regression Risk

The highest risk is accidentally changing Demo or Production submit/execution behavior while exposing Historical.

Controls:

- Historical environment selection must be explicit.
- Demo and Production default adapter selection must remain unchanged.
- Production must never accept historical simulated broker adapter.
- Demo submit must remain guarded by existing Demo write preconditions.
- Existing `POST_SEND_UNKNOWN` no-auto-resubmit behavior must remain unchanged.
- Submit Guard evidence must be identical for Demo/Production inputs except environment metadata.
- Execution normalization and ledger append behavior must be tested for no regressions.

## Required Contract Amendments

1. Add a Historical Environment Composition amendment to the Runtime / Historical / Lifecycle contracts.
2. Add a no-external-effect historical command contract.
3. Add PM `ACCEPTED_CURRENT_PATH` adapter authority amendment.
4. Add source-hash fail-closed requirements for PM producer preflight.

These amendments are limited. They do not redefine Runtime authority, Current, Ledger, Pending, Submit Guard, Execution Processor, Safety, Registry, or Artifact Acceptance.

## Required Implementation Scope

Historical:

- Environment composition resolver.
- CLI mode / validation alignment.
- Historical submit adapter selection.
- Historical execution snapshot provider selection.
- Historical broker contract completion.
- External effect blocker.
- Historical clock audit for exact job sequence.

PM:

- Current source PM Artifact Set acceptance.
- Runtime source hash preflight / fail-closed check.
- Old adapter snapshot legacy transition.
- PM and Sell Planning regression evidence.

Follow-on:

- canonical historical input resolver;
- point-in-time manifests;
- feature generation readiness;
- 5BD entry gate revalidation.

## Explicit Non-Goals

- Historical-only Runtime.
- Phase17-only Mainline.
- Test-only Runtime root.
- Test-only Current / Ledger / Pending.
- Submit Guard bypass.
- Execution Processor bypass.
- Dynamic import of arbitrary accepted source without review.
- Monkey patching imports.
- Manual copy-over of PM source.
- Registry or Acceptance mutation in this review.
- 5BD execution in this review.

## Migration / Rollback

Historical environment composition migration:

1. Add contract amendments.
2. Add composition resolver and tests.
3. Enable Historical mode only behind explicit CLI/config environment selection.
4. Run read-only command validation.
5. Revalidate Entry Gates.

Rollback:

- Disable the Historical environment composition.
- Demo/Production remain on existing adapter selection.
- No Trading State rollback is required if no Historical execution has started.

PM authority migration:

1. Register current PM source as new PM set member.
2. Validate hash and regression evidence.
3. Accept new PM set.
4. Mark old set / old adapter snapshot legacy.
5. Enable source-hash fail-closed check.

Rollback:

- Re-accept previous PM set through rollback acceptance event if needed.
- Do not delete accepted or legacy evidence.
- Runtime lookup must fail closed if duplicate active PM sets appear.

## Acceptance Gates

Historical exposure acceptance gates:

- `NORMAL_MAINLINE_READY`
- `HISTORICAL_BROKER_READY`
- `EXTERNAL_EFFECTS_DISABLED`
- Demo submit regression PASS
- Production submit guard regression PASS
- Execution readonly regression PASS
- no Runtime Core diff

PM authority acceptance gates:

- current source hash accepted;
- old snapshot no longer active or explicitly legacy;
- PM source hash preflight fail-closed test;
- PM semantic regression PASS;
- Sell Planning regression PASS;
- Current / Ledger / Pending unchanged PASS;
- Registry Event Log / Index / Checkpoint PASS.

## Recommended Execution Order

1. `Phase17-B1I-A Historical Environment Composition`
2. `Phase17-B1I-B PM Adapter Authority Resolution`
3. `Phase17-B1I-C Canonical / Point-in-time / Feature Readiness`
4. `Phase17-B1I-D 5BD Entry Gate Revalidation`
5. `Phase17-C Historical Runtime 5BD Smoke Test`

## Blocking Findings

1. `HISTORICAL_ENVIRONMENT_CONTRACT_AMENDMENT_REQUIRED`
   - Classification: `CONTRACT_AMENDMENT_REQUIRED`
   - Historical exists architecturally, but implementation-facing CLI/mode/composition contract is incomplete.

2. `HISTORICAL_BROKER_COMPOSITION_NOT_IMPLEMENTED`
   - Classification: `IMPLEMENTATION_REQUIRED`
   - Submit adapter and execution snapshot provider cannot yet be selected through the official normal CLI path.

3. `PM_ACCEPTED_CURRENT_PATH_REQUIRED`
   - Classification: `ARTIFACT_AUTHORITY_GAP`
   - Accepted PM adapter snapshot does not match the current executed source.

4. `PM_SOURCE_HASH_FAIL_CLOSED_REQUIRED`
   - Classification: `IMPLEMENTATION_REQUIRED`
   - Runtime must fail closed if the deployed PM source hash drifts from accepted authority.

## Operations Not Performed

- Runtime code modification.
- CLI modification.
- Submit modification.
- Execution modification.
- PM producer modification.
- Registry mutation.
- Artifact Acceptance mutation.
- Trading State reset.
- Current / Ledger / Pending mutation.
- Feature regeneration.
- Canonical regeneration.
- Historical Broker execution.
- 5BD execution.
- Tachibana API access.
- Demo submit.
- Production access.
