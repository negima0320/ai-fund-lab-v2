# Phase17-A Integrated System Test and Production Readiness Test Strategy

## Final Judgment

Final judgment: `PHASE17_A_INTEGRATED_TEST_STRATEGY_ACCEPTED`

Recommended next prefix: `Phase17-B`

Recommended next work:

```text
Historical Runtime Readiness Revalidation and 5BD Smoke Test Preparation
```

Phase17-A is a design, audit, and planning phase only. No Historical Runtime execution, Trading State reset, Current/Ledger/Pending mutation, Tachibana API write, AI retraining, policy optimization, Registry redesign, Acceptance redesign, artifact path redesign, canonical data regeneration, or feature regeneration was performed.

## Reviewed Materials

Required Phase16 handoff and architecture materials were reviewed, including:

- `docs/phase_reports/phase16_final_summary_and_phase17_handoff.md`
- `reports/phase_reports/phase16_final_summary_and_phase17_handoff.json`
- `docs/phase_reports/phase16_ax_operational_data_foundation_final_conformance_and_ai_integrity_audit.md`
- `reports/phase_reports/phase16_ax_operational_data_foundation_final_conformance_and_ai_integrity_audit.json`
- `docs/phase_reports/phase16_aw_capital_allocation_loadable_policy_registry_cutover.md`
- `reports/phase_reports/phase16_aw_capital_allocation_loadable_policy_registry_cutover.json`
- `docs/phase_reports/phase16_av_runtime_consumer_registry_cutover.md`
- `reports/phase_reports/phase16_av_runtime_consumer_registry_cutover.json`
- `docs/phase_reports/phase16_au_registry_artifact_resolver.md`
- `reports/phase_reports/phase16_au_registry_artifact_resolver.json`
- `docs/phase_reports/phase16_at_formal_artifact_acceptance.md`
- `reports/phase_reports/phase16_at_formal_artifact_acceptance.json`
- `docs/phase_reports/phase16_as_formal_artifact_approval_copy_and_validated_registration.md`
- `reports/phase_reports/phase16_as_formal_artifact_approval_copy_and_validated_registration.json`
- `docs/phase_reports/phase16_ap_formal_registration_technical_blocker_resolution.md`
- `reports/phase_reports/phase16_ap_formal_registration_technical_blocker_resolution.json`
- `docs/phase_reports/phase16_aq_opportunity_phase5e_fallback_removal.md`
- `reports/phase_reports/phase16_aq_opportunity_phase5e_fallback_removal.json`
- `docs/phase_reports/phase16_g_canonical_historical_data_source_audit.md`
- `reports/phase_reports/phase16_g_canonical_historical_data_source_audit.json`
- `docs/phase_reports/phase16_b_prerequisite_audit.md`
- `reports/phase_reports/phase16_b_prerequisite_audit.json`
- `docs/phase_reports/phase16_a_historical_runtime_v2_performance_test_design.md`
- `reports/phase_reports/phase16_a_historical_runtime_v2_performance_test_design.json`
- `docs/02_architecture/operational_data_architecture.md`
- `docs/02_architecture/artifact_registry_event_and_acceptance_evidence_contract.md`
- `docs/02_architecture/materialized_registry_index_and_event_replay_contract.md`
- `docs/02_architecture/artifact_acceptance_contract.md`
- `docs/02_architecture/artifact_acceptance_authority_and_promotion_workflow_contract.md`
- `docs/02_architecture/artifact_path_registry_integration_and_migration_contract.md`
- `docs/02_architecture/ai_input_output_and_artifact_contract.md`
- `docs/02_architecture/ai_artifact_registry_and_capital_allocation_contract.md`
- `docs/02_architecture/historical_runtime_test_contract.md`
- `docs/02_architecture/runtime_temporal_freshness_contract.md`
- `docs/02_architecture/operational_lifecycle_state_reset_and_environment_transition_contract.md`

Supplemental references reviewed:

- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/01_requirements/phase_roadmap.md`

## Phase17 Positioning

Phase17 is the final pre-production test phase for AI Fund Lab v2. It is not a model tuning phase and not a profit-only backtest phase.

Phase17 combines:

- Integrated System Test
- Historical Runtime Validation
- Backtest and Investment Performance Analysis
- Tachibana Demo Operational Validation
- Regression and Degradation Prevention
- Environment Transition and Production Readiness Review

Project objective:

```text
Build a Japanese equity auto-trading system that can operate safely,
continuously, and audibly, then move toward Production operation.
```

Investment target:

```text
initial_cash=1,000,000 JPY
market=Japanese equities
trade_type=cash equities only
ultimate_target=50% annualized return
```

Return is important, but it is lower priority than Runtime Integrity, Safety, Authority, Temporal Correctness, Data Integrity, Operational Continuity, and auditability.

## Shared Foundation

Historical, Demo, and Production must share the same persistent operational foundation:

- Canonical Data Contract
- Feature Producer
- Feature Schema
- Accepted AI Artifact Sets
- AI Decision Contract
- Policy
- Safety
- Capital Allocation
- Runtime v2 Mainline
- Artifact Registry
- Registry Resolver
- Acceptance Authority

Environment differences must be represented by:

- `environment_id`
- `run_type`
- `broker_environment`
- initial Trading State
- Broker boundary
- evaluation time

Environment-specific AI models, Feature logic, Runtime mainlines, Registries, or artifact authority models are prohibited.

## Track A: Historical Runtime Integrated Test

Purpose:

Validate the completed Operational Data Foundation through the normal Runtime v2 Mainline under historical dates.

Test target:

```text
Canonical Market Data
↓
Feature Producer
↓
Candidate AI
↓
Opportunity AI
↓
Position Management
↓
Policy
↓
Safety
↓
Capital Allocation / Planning
↓
Authoritative Pending
↓
Submit Guard
↓
Historical Simulated Broker
↓
Execution Processor
↓
Ledger Writer
↓
Current Projector
↓
Current Apply
↓
Runtime State
↓
Runtime Report / Audit / Performance Evidence
```

Test environment:

Normal Runtime root `.runtime`, with Historical Simulated Broker replacing only the external broker boundary.

Inputs:

- Accepted Registry-backed Candidate, Opportunity, PM, Capital Allocation, and Feature Schema artifact sets.
- Canonical market data and point-in-time manifests.
- Initial clean Trading State.
- Historical clock inputs: `business_date`, `evaluation_time`, and feature/market dates.
- Historical broker configuration.

Outputs:

- Daily Runtime report.
- Audit report.
- Performance evidence.
- Initial/final state manifests.
- Failure classification reports when applicable.

Authority:

Runtime v2 remains authority for Current, Ledger, Pending, Execution, and Runtime State. Registry remains artifact identity and eligibility authority. Historical Simulated Broker has authority only at the broker boundary.

Pass criteria:

- Runtime uses normal mainline.
- Registry lookup succeeds and remains fail-closed.
- Current/Ledger/Pending remain internally consistent.
- No double submit, double execution, double ledger write, or duplicated PnL.
- Temporal and authority contracts hold.
- Generated performance is attached only to periods with Runtime Integrity PASS.

Fail criteria:

- Non-haltable test defects, data defects, feature defects, AI limitations, policy limitations, safety limitations, execution assumption bias, or broker adapter defects are found and classified.

Halt criteria:

- Runtime Core defect.
- Authority contract violation.
- Temporal contract violation.
- Registry Event Log / Index / Checkpoint mismatch during Runtime lookup.
- Silent fallback to unaccepted artifacts.
- State restore failure.
- Current / Cash / Quantity inconsistency.

Excluded scope:

- Historical-only Runtime.
- Phase17-specific Runtime root.
- Profit-only substitute engine.
- AI retraining.
- Model or policy optimization.

Relationship with other tracks:

Track A produces official Historical Runtime Performance only when integrity gates pass. Track B may analyze failures or performance causes, but cannot replace Track A.

## Track B: Backtest and Performance Analysis

Purpose:

Analyze investment performance and root causes by AI, Policy, Safety, Capital Allocation, Execution Assumption, and Market Regime.

Test target:

- Candidate AI contribution.
- Opportunity AI ranking quality.
- Position Management exit/hold behavior.
- Capital Allocation and cash utilization.
- Safety block impact.
- Execution assumption bias.
- Market regime sensitivity.

Test environment:

Fast or analytical backtest environment, explicitly marked as analysis-only.

Inputs:

- Accepted artifacts and frozen hashes.
- Point-in-time feature and decision evidence where available.
- Track A outputs for attribution.
- Analytical fixtures only when labeled `EVIDENCE_ONLY` or `ANALYSIS_ONLY`.

Outputs:

- Performance report.
- Attribution report.
- Risk and regime report.
- Improvement hypothesis report.

Authority:

Track B has no Runtime authority and no artifact acceptance authority. It may recommend improvements, but any model, policy, feature, or architecture change requires a separate reviewed phase and new evidence.

Metrics:

- Total Return
- Annualized Return
- Maximum Drawdown
- Profit Factor
- Win Rate
- Average Return per Trade
- Median Return per Trade
- Average Gain
- Average Loss
- Payoff Ratio
- Exposure
- Cash Utilization
- Turnover
- Trade Count
- Average Holding Period
- Unfilled Count
- Safety Block Count

Pass criteria:

- Metrics are computed from clearly scoped inputs.
- Analytical results are not labeled official Historical Runtime Performance.
- Runtime-integrity-failed periods are excluded from official performance.

Fail criteria:

- Ambiguous attribution.
- Missing metrics.
- Input leakage or future data contamination in analytical data.

Halt criteria:

- Analytical backtest is used as substitute for Track A.
- Backtest results feed the same Runtime run.
- Historical results are used to silently select or promote a model/policy.

Excluded scope:

- Runtime authority mutation.
- Artifact Acceptance.
- AI retraining or model selection inside Phase17-A/Track B.

Relationship with other tracks:

Track B explains Track A results and informs later improvement design. It must not become the official system performance gate.

## Track C: Tachibana Demo Operational Test

Purpose:

Validate real-time operation, real API behavior, scheduler behavior, and broker-boundary behavior that Historical Runtime cannot prove.

Test target:

- API authentication.
- Session maintenance.
- Market Data refresh.
- Feature generation.
- AI decisions.
- Policy, Safety, and Capital Allocation.
- Pending generation.
- Submit and Submit Guard.
- Order state.
- Execution retrieval.
- Ledger update.
- Current update.
- Valuation.
- Runtime State.
- Report and Audit.
- Scheduler.
- Rerun and recovery.
- PC restart.
- API timeout/error.
- Market holiday.
- Data stale.
- No fill / partial fill.
- Duplicate prevention.
- Idempotency.
- Human Review.

Test environment:

Tachibana Demo environment, using accepted shared foundation and normal Runtime v2 Mainline.

Inputs:

- Demo credentials and broker environment configuration.
- Accepted artifact sets.
- Demo initial Trading State.
- Broker snapshot evidence.
- Runtime business dates and evaluation times.

Outputs:

- Demo operation manifests.
- Broker readonly and submit evidence.
- Execution and ledger evidence.
- Current/valuation evidence.
- Scheduler and recovery evidence.
- Demo readiness and continuity reports.

Authority:

Runtime-owned positions and broker snapshot are distinct. In Demo only:

```text
Broker Snapshot entire positions != Runtime-owned positions entire positions
```

This exception exists because Tachibana Demo may contain holdings not owned by Runtime. Production must not inherit this assumption.

Pass criteria:

- Demo operation follows normal Runtime v2 mainline.
- External writes occur only in approved Demo submit scopes.
- Broker evidence is normalized and does not directly overwrite Runtime-owned Current without accepted execution/correction authority.
- Duplicate prevention and idempotency hold.

Fail criteria:

- API/session errors, stale data, no-fill or partial-fill behavior, scheduler failures, or recovery issues are found and classified without violating Runtime authority.

Halt criteria:

- Unexpected Production API access.
- Demo write outside approved scope.
- Unreviewed Broker Snapshot to Runtime-owned Current absorption.
- Duplicate submit or post-send-unknown auto-resubmit.
- Safety bypass.

Excluded scope:

- Production API connection.
- Production order submission.
- Demo-specific AI, Feature, Registry, or Runtime mainline.

Relationship with other tracks:

Track C starts only after Historical and regression gates demonstrate stable core behavior. It validates operational reality, not investment strategy alone.

## Track D: Regression and Degradation Prevention

Purpose:

Prevent Phase17 work from breaking Phase15 and Phase16 accepted behavior.

Test target:

- Baseline definition.
- Accepted behavior snapshots.
- Golden artifact and hash comparison.
- Contract regression.
- Schema regression.
- Registry regression.
- Resolver regression.
- Runtime decision regression.
- Safety regression.
- Capital Allocation regression.
- Pending lifecycle regression.
- Submit Guard regression.
- Execution regression.
- Ledger regression.
- Current regression.
- Temporal regression.
- Point-in-time regression.
- Determinism regression.
- Environment transition regression.

Test environment:

Read-only or isolated test roots where possible; normal `.runtime` only when a planned environment transition or accepted test explicitly requires it.

Inputs:

- Git commit.
- Runtime version.
- Registry checkpoint.
- Accepted Artifact Set IDs.
- Artifact hashes.
- Feature Schema hash.
- Policy hash.
- Safety hash.
- Capital Allocation hash.
- Canonical Data manifest.
- Initial state hash.

Outputs:

- Regression report.
- Golden hash comparison report.
- Contract compatibility report.
- Failure classification report.

Pass criteria:

- Accepted Phase15/Phase16 behavior remains intact.
- Expected nondeterminism is explicitly classified.
- No unapproved semantic changes to Runtime decisions, Safety, Capital Allocation, Pending, Submit Guard, Execution, Ledger, Current, or artifact authority.

Fail criteria:

- Regression is found but classified and contained before execution expands.

Halt criteria:

- Regression affects Runtime authority, artifact authority, Safety, Submit, Execution, Ledger, Current, or fail-closed behavior.

Excluded scope:

- Updating the baseline to hide a regression.
- Treating path-only or timestamp-only differences as semantic differences without classification.

Relationship with other tracks:

Track D gates every other track before and after execution.

## Track E: Environment Transition and Production Readiness

Purpose:

Validate lifecycle transitions from Historical to Demo and from Demo to Production without carrying Trading State across environments.

Test target:

```text
Historical Runtime Test
↓
Tachibana Demo Operation
↓
Production Operation
```

Historical to Demo requirements:

- Historical evidence freeze.
- Historical Trading State backup.
- Historical Run close.
- Normal Runtime Trading State clean reset.
- Demo environment initialization.
- Demo broker environment selection.
- Artifact / Registry / Canonical Data continuity confirmation.

Forbidden Historical to Demo carryover:

- Historical position to Demo.
- Historical Ledger as Demo authority.
- Historical Pending submitted in Demo.
- Historical PnL reflected into Demo Current.
- Historical Feature / Decision Artifact as Demo decision authority.

Demo to Production requirements:

- Demo evidence freeze.
- Demo Trading State backup.
- Demo Run close.
- Production account reconciliation.
- Production initial Current from broker evidence and reconciliation.
- Production Broker authority enabled only by separate Acceptance.

Pass criteria:

- Persistent Operational Foundation continues unchanged unless a separate acceptance changes it.
- Resettable Trading State is cleanly reset or initialized per environment.
- Production readiness is based on integrity, continuity, broker reconciliation, safety, operational recovery, and accepted authority.

Fail criteria:

- Environment transition procedure is incomplete or evidence is missing.

Halt criteria:

- Trading State inheritance across environments.
- Registry checkpoint mismatch.
- Freeze manifest mismatch.
- Production reconciliation mismatch requiring review.
- Pending or unsettled execution remains at transition.

Excluded scope:

- Production broker write.
- Production credential activation without separate Acceptance.

Relationship with other tracks:

Track E consumes evidence from Tracks A, C, and D and produces the Production Readiness final decision.

## Recommended Execution Order

Recommended sequence:

1. `Phase17-B`: Historical Runtime readiness revalidation and 5BD smoke preparation.
2. `Phase17-C`: Historical 5BD smoke test.
3. `Phase17-D`: Historical 20BD continuity test.
4. `Phase17-E`: Historical 1-year integrated Runtime test.
5. `Phase17-F`: Performance and attribution analysis.
6. `Phase17-G`: Historical full-period Runtime test.
7. `Phase17-H`: Tachibana Demo readiness review.
8. `Phase17-I`: Tachibana Demo short operation.
9. `Phase17-J`: Tachibana Demo continuous operation.
10. `Phase17-K`: Environment transition and Production readiness review.

Rationale:

- Start with readiness revalidation because Phase16-B/G found historical prerequisites before the Operational Data Foundation was completed.
- Run 5BD before 20BD because state continuity and mainline correctness matter more than performance.
- Run 1-year before full-period because performance and failure attribution are cheaper to inspect at one-year scale.
- Run Demo only after Historical core behavior and regression controls are stable.
- Production readiness comes after Demo evidence and environment transition review.

## Entry Criteria

Phase17 execution stages may begin only when:

- Operational Data Foundation is `COMPLETE`.
- Phase17 readiness is `READY`.
- Registry Event Log, Materialized Index, and Checkpoint validate.
- Exactly five accepted runtime-use eligible Artifact Sets exist.
- Candidate, Opportunity, PM, Capital Allocation, and Feature Schema resolve through Registry Resolver.
- Opportunity Phase5-E fallback remains removed and absent from the accepted set.
- Capital Deployment Policy JSON is Registry-resolved.
- Backup / Reset / Restore procedure for Trading State is accepted before any reset.
- Historical Clock requirements are revalidated for the intended jobs.
- Historical Broker boundary and schema mapping are accepted before simulated broker execution.
- No production or demo broker write is enabled outside an approved scope.

## Exit Criteria

Phase17 final exit requires:

- Historical Runtime Integrated Test accepted.
- Investment Performance Analysis completed and separated from official Runtime performance.
- Tachibana Demo Operational Test accepted.
- Regression and degradation controls passed.
- Historical to Demo and Demo to Production transition evidence accepted.
- Production Readiness Report accepted.
- No unresolved `HALT`, `ARCHITECTURE_REVIEW_REQUIRED`, or `DESIGN_CHANGE_REQUIRED`.

## Pass / Fail / Halt Criteria

Independent pass dimensions:

- Runtime Integrity
- Data Integrity
- Temporal Correctness
- Authority Correctness
- Safety
- Determinism
- State Consistency
- Operational Continuity
- Broker Boundary
- Investment Performance
- Regression
- Production Readiness

Performance pass is not sufficient by itself. Runtime Integrity failure invalidates official performance for the affected period.

Fail means a problem is found, classified, contained, and does not require immediate stop.

Halt means execution must stop before expansion or downstream action. Halt examples:

- double submit
- double execution
- double ledger write
- double PnL
- Current / Cash / Quantity inconsistency
- Pending lifecycle inconsistency
- Temporal violation
- Authority violation
- nondeterministic state transition
- normal mainline bypass
- restore failure
- incorrect no-fill update
- Registry / Resolver fail-closed violation
- silent fallback to unaccepted artifact
- production write risk

## Problem Classification

Problems must be classified before fixes:

- `TEST_DESIGN_GAP`
- `TEST_ENVIRONMENT_FAILURE`
- `DATA_DEFECT`
- `CANONICAL_DATA_GAP`
- `FEATURE_DEFECT`
- `AI_MODEL_LIMITATION`
- `POLICY_LIMITATION`
- `SAFETY_LIMITATION`
- `CAPITAL_ALLOCATION_LIMITATION`
- `EXECUTION_ASSUMPTION_BIAS`
- `BROKER_ADAPTER_DEFECT`
- `RUNTIME_CORE_DEFECT`
- `TEMPORAL_CONTRACT_VIOLATION`
- `AUTHORITY_CONTRACT_VIOLATION`
- `REGRESSION`
- `ARCHITECTURE_REVIEW_REQUIRED`
- `DESIGN_CHANGE_REQUIRED`
- `UNKNOWN`

Low return, low win rate, high drawdown, low trade count, high cash ratio, or long holding period are not Runtime Core change reasons.

## Evidence Requirements

Minimum evidence per major test:

- Test Plan
- Test Manifest
- Environment Manifest
- Freeze Manifest
- Initial State Manifest
- Final State Manifest
- Point-in-time Manifest
- Runtime Report
- Audit Report
- Performance Report
- Regression Report
- Failure Classification Report
- Environment Transition Report
- Production Readiness Report

Every test should record:

- Git commit.
- Runtime version.
- Registry checkpoint.
- Accepted Artifact Set IDs.
- Artifact hashes.
- Feature Schema hash.
- Policy hash.
- Safety hash.
- Capital Allocation hash.
- Canonical Data manifest.
- Initial state hash.
- Final state hash.

## Retest Rules

Retests must not overwrite the original run. A retest requires:

- new Git commit when code changes;
- new version when artifact/policy/schema behavior changes;
- new `run_id`;
- new `environment_id` when environment scope changes;
- new manifest;
- new result set;
- new evidence directory.

Historical result feedback must not affect the same run. Improvements require separate design, acceptance, and execution evidence.

## Historical Runtime Test vs Fast / Analytical Backtest

Historical Runtime Performance:

- Uses normal Runtime v2 Mainline.
- Uses accepted Registry-backed artifacts.
- Replaces only broker boundary with Historical Simulated Broker.
- Mutates Trading State only inside an approved test execution.
- Produces official system performance only when Runtime Integrity passes.

Fast / Analytical Backtest:

- Used for analysis, attribution, comparison, and root-cause investigation.
- May run faster than the full Runtime.
- Does not replace Track A.
- Has no Runtime authority, artifact acceptance authority, or production readiness authority.
- Must be labeled analysis-only.

## Production Readiness Decision

Production readiness is not a single return threshold. It requires:

- Runtime Integrity PASS.
- Data Integrity PASS.
- Temporal Correctness PASS.
- Authority Correctness PASS.
- Safety PASS.
- Broker Boundary PASS.
- Operational Continuity PASS.
- Regression PASS.
- Environment Transition PASS.
- Production reconciliation accepted.
- Investment performance reviewed and risk-understood.
- No unresolved HALT / architecture review / design change finding.

Production broker writes require separate explicit acceptance after the Phase17 evidence set is complete.

## Open Items

These are not blockers for accepting the Phase17-A strategy, but must be revalidated before execution:

- Formal Backup / Reset / Restore procedure readiness for normal Runtime Trading State.
- Historical Clock coverage for every job used in 5BD/20BD/1Y/full-period tests.
- Historical Simulated Broker adapter contract and execution schema mapping for mainline execution.
- Historical calendar, listed issues, corporate action, and point-in-time universe readiness for the selected window.
- Public report / notification optionality for historical and demo scopes.
- PM Runtime Adapter source drift observation from Phase16-AX.
- Demo-only Broker Snapshot vs Runtime-owned Current handling, with explicit prohibition on carrying that exception into Production.

## Out of Scope for Phase17-A

The following were intentionally not performed:

- Historical Runtime execution.
- 5BD / 20BD / 1-year / full-period execution.
- Tachibana API write.
- Tachibana Demo order submit.
- Production API connection.
- Trading State reset.
- Current mutation.
- Ledger mutation.
- Pending mutation.
- AI retraining.
- Model replacement.
- Policy optimization.
- Safety optimization.
- Capital Allocation optimization.
- Runtime Core modification.
- Registry redesign.
- Acceptance redesign.
- Artifact path redesign.
- Canonical Data regeneration.
- Feature regeneration.

