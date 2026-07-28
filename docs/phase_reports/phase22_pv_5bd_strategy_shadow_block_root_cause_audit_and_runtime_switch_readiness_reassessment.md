# Phase22-PV 5BD Strategy Shadow BLOCK Root-Cause Audit and Runtime Switch Readiness Reassessment

## Executive Summary

Judgment: `PHASE22_PV_IMPLEMENTATION_DEFECT_REPAIR_REQUIRED`

The Phase22-PU user-run 5BD Historical Runtime is valid as a Runtime PASS:

- Run ID: `runtime-test-historical-smoke-20260728T004341907286Z`
- Source commit: `74742aed54822999d5419301ce033b4084abc1cd`
- Dates: `2026-07-06` through `2026-07-10`
- `final_summary.json.status = PASS`
- `test_validity_judgment = VALID`
- `acceptance_gate_judgment = PASS`
- `run_state.json.status = COMPLETED`
- Completed business days: all 5 requested days

The Strategy Shadow result is separate from the Runtime result:

- `strategy_shadow_judgment = BLOCK`
- Blocked dates: all 5 requested days
- `active_runtime_consumer_eligibility = NO`
- `runtime_switch_performed = false`
- `runtime_mutation_performed = false`

The 5 Strategy Shadow BLOCKs are safe with respect to active Runtime isolation. They are not sufficient for Phase22 closure or Runtime Switch approval. PV found repair-required issues in Strategy Shadow feature-date authority propagation and Shadow observability/reason-code clarity. Therefore Runtime Switch remains not ready.

## Evidence Written

Evidence directory:

`reports/phase22_pv_5bd_strategy_shadow_block_root_cause_audit_and_runtime_switch_readiness_reassessment/`

Files:

- `executive_summary.json`
- `evidence_inventory.json`
- `per_day_shadow_table.json`
- `block_root_cause_classification.json`
- `feature_date_investigation.json`
- `phase22_pu_acceptance.json`
- `regression_assessment.json`

## PV-1 Strategy Shadow Evidence Inventory

Each daily Strategy Shadow directory contains these files:

- `capital_deployment.json`
- `corporate_event.json`
- `dynamic_cash_exposure.json`
- `dynamic_position_count.json`
- `input_manifest.json`
- `legacy_shadow_comparison.json`
- `market_context.json`
- `portfolio_construction.json`
- `portfolio_policy.json`
- `position_management.json`
- `position_sizing.json`
- `runtime_planning.json`
- `source_manifest.json`
- `strategy_decision_trace.json`
- `strategy_shadow_summary.json`

The files requested by PV as separate named artifacts are not materialized as separate files:

- `strategy_judgment.json`
- `strategy_manifest.json`
- `strategy_generation_manifest.json`
- `accepted_generation_resolution.json`
- `resolver_evidence.json`
- `validation_artifact.json`
- `schema_evidence.json`

Equivalent evidence exists, but it is embedded across `strategy_shadow_summary.json`, `strategy_decision_trace.json`, `source_manifest.json`, `input_manifest.json`, and component artifacts. This is classified as `OBSERVABILITY_DEFECT`, not as an active Runtime defect.

## PV-1 Per-Day Shadow Table

| business_date | top judgment | root blocker | PIT | Accepted Generation | Market Context | Capital Deployment | Portfolio Construction | Position Management | Position Sizing | mutation | consumer eligibility | runtime switch |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-07-06 | BLOCK | position_sizing | PASS | RESOLVED_COMMITTED | PASS | REVIEW_REQUIRED | REVIEW_REQUIRED | REVIEW_REQUIRED | BLOCK | false | REVIEW_REQUIRED / active NO | false |
| 2026-07-07 | BLOCK | position_sizing | PASS | RESOLVED_COMMITTED | PASS | REVIEW_REQUIRED | REVIEW_REQUIRED | REVIEW_REQUIRED | BLOCK | false | REVIEW_REQUIRED / active NO | false |
| 2026-07-08 | BLOCK | position_sizing | PASS | RESOLVED_COMMITTED | PASS | REVIEW_REQUIRED | REVIEW_REQUIRED | REVIEW_REQUIRED | BLOCK | false | REVIEW_REQUIRED / active NO | false |
| 2026-07-09 | BLOCK | position_sizing | PASS | RESOLVED_COMMITTED | PASS | REVIEW_REQUIRED | REVIEW_REQUIRED | REVIEW_REQUIRED | BLOCK | false | REVIEW_REQUIRED / active NO | false |
| 2026-07-10 | BLOCK | position_sizing | PASS | RESOLVED_COMMITTED | PASS | REVIEW_REQUIRED | REVIEW_REQUIRED | REVIEW_REQUIRED | BLOCK | false | REVIEW_REQUIRED / active NO | false |

Root reason codes for all days:

- `capital_deployment_review_required:REVIEW_REQUIRED`
- `dynamic_cash_exposure_review_required:REVIEW_REQUIRED`
- `dynamic_position_count_review_required:REVIEW_REQUIRED`
- `portfolio_construction_review_required:REVIEW_REQUIRED`
- `position_management_review_required:REVIEW_REQUIRED`
- `price_volatility_review_required:REVIEW_REQUIRED`
- `strategy_position_weight_above_safety_cap`

## PV-2 BLOCK Root Cause Classification

Primary classification: `IMPLEMENTATION_DEFECT`

Secondary classifications:

- `EXPECTED_SAFE_BLOCK`
- `ARTIFACT_ACCEPTANCE_BLOCK`
- `TEMPORAL_AUTHORITY_BLOCK`
- `OBSERVABILITY_DEFECT`

The expected safe portion is confirmed by implementation and evidence:

- `src/ai_fund_lab_v2/strategy/shadow_runtime.py` declares Strategy Shadow as `after_daily_runtime_jobs`, read-only, and isolated from active Runtime.
- A component `BLOCK` makes the day-level `strategy_shadow_judgment` become `BLOCK`.
- All summaries record `runtime_mutation_performed=false`, `active_runtime_consumer_eligibility=NO`, and `runtime_switch_performed=false`.

The artifact acceptance portion is also expected:

- Phase22-N states Runtime Switch is not ready.
- Phase22 artifacts remain `DRAFT` and `NOT_ELIGIBLE`.
- Corporate Event is `REVIEW_REQUIRED` because source coverage is partial.
- Downstream portfolio/construction/management/deployment artifacts remain review-only and non-consumable.

The repair-required portions are:

1. `2026-07-09` Strategy Shadow feature-date authority propagation:
   Runtime jobs use the materialized contract-selected `2026-07-09`, while `runtime_test.py` passes stale `day.feature_date` into Strategy Shadow generation.

2. Position Sizing / Source Manifest observability:
   `position_sizing.json` has `total_target_weight=0`, no decisions, and no actual overweight position, but the root reason includes `strategy_position_weight_above_safety_cap`. The code reason is config-vs-safety-cap, not actual produced position weight. `source_manifest.json` also classifies the direct blocker as `DIRECT_SOURCE_PIT_VIOLATION` while PIT validation is `PASS`.

## PV-3 Phase21 / Phase22 Contract Comparison

The generated artifacts match the Phase22 shadow-only implementation contract:

- Artifacts are generated daily.
- Strategy artifacts are not production consumers.
- Runtime mutation is forbidden and was not detected.
- Runtime Switch was not performed.
- Active legacy Runtime authority remains active.

The artifacts do not satisfy Runtime Switch contract requirements:

- Artifact lifecycle acceptance is not performed.
- Runtime consumer eligibility promotion is not performed.
- Corporate Event source completeness remains partial.
- Historical sector / downstream PIT readiness remains review-required.
- Human Runtime Switch approval is not present.
- Long validation is not complete.

Accepted Generation is `RESOLVED_COMMITTED`, but the resolved generation is current COMMITTED authority with `accepted_at/effective_from = 2026-07-20T00:00:00+09:00` for target dates `2026-07-06` through `2026-07-10`. This is not the direct cause of the 5 BLOCKs, but it is not sufficient as historical PIT authority for Runtime Switch readiness without a clarified historical generation contract.

## PV-4 2026-07-09 Feature Date Difference

Observed:

- Planned feature date: `2026-07-08`
- Runtime selected feature date: `2026-07-09`
- `planned_matches_materialized = false`
- `contract_status = PASS`

The Runtime job path is not fail-open. Runtime job command resolution reloads `.runtime/operations/feature_date_contract/2026-07-09.json` and rewrites `--feature-date` to `2026-07-09`. The jobs exit 0.

However, Strategy Shadow generation receives `feature_date=str(day.get("feature_date") or "")` in both run and resume paths. This means Strategy Shadow can use stale plan-time feature date authority even when the actual Runtime jobs used the materialized contract-selected feature date.

Judgment:

`IMPLEMENTATION_DEFECT_REPAIR_REQUIRED_FOR_STRATEGY_SHADOW_WIRING`

Runtime production-common defect is not confirmed by this evidence. Runtime Test Strategy Shadow wiring defect is confirmed.

## PV-5 Phase22-PU Acceptance

Phase22-PU source-hash mismatch repair is accepted for the observed run:

- No `source hash mismatch` text exists under the run evidence.
- All 5 submit jobs have `exit_code=0`.
- Logical manifests include `source_identity_version=historical_source_identity_v1`.
- Logical manifests include source identities for `listed_issues`, `normalized_ohlcv`, `raw_ohlcv`, and `trading_calendar`.
- Physical file hashes remain as data evidence, but are no longer used as stale preflight authority to block submit.
- No Phase17 PIT hash dependency reintroduction was found in the run evidence.
- No Historical-only bypass was found.

## PV-6 Regression Assessment

Observed test:

`tests/runtime_v2/test_phase19_ax_system_status.py`

Current result:

- `system-status --json`: exit `0`
- `system-status`: exit `0`
- `system-status --json --write-evidence --evidence-root <tmp>`: exit `20`
- Test expected: exit `10`

Classification:

- `shared runtime residue`
- `test isolation`
- `expected behavior mismatch`

The observed failure is not caused by the Phase22-PU source identity repair. The failing test asserts a Phase19-era `REVIEW_REQUIRED` status contract while current system-status now resolves the latest closed historical run and injects Strategy Shadow readiness separately. With a temporary evidence root, post-run context is isolated away and status can become `BLOCK`.

Production regression: `NO`.

Repair required: update or isolate Phase19 AX system-status tests to the current post-run system-status contract, including separate expectations for overview PASS and Strategy Shadow BLOCK readiness.

## Required Repairs

1. Repair Strategy Shadow feature-date propagation:
   use the materialized `selected_feature_date` from completed runtime job command resolution when generating Strategy Shadow. Do this for both run and resume paths.

2. Repair Position Sizing reason-code clarity:
   distinguish config maximum above safety cap from actual produced position weight above cap.

3. Repair Source Manifest blocker class mapping:
   do not label a Strategy Shadow component blocker as `DIRECT_SOURCE_PIT_VIOLATION` when run-level PIT validation is `PASS` and the direct cause is artifact/review/config.

4. Add explicit Strategy Shadow evidence files or clearly document embedded evidence mapping:
   the PV-required evidence exists only as embedded fields today.

5. Update system-status tests:
   separate overview status, write-evidence isolated-root behavior, and Strategy Shadow readiness.

## Next Phase Recommendation

Recommended next phase:

`Phase22-PW - Strategy Shadow Authority and Observability Repair`

Scope:

- Fix feature-date propagation into Strategy Shadow.
- Fix reason-code and blocker-class observability.
- Add regression tests for the 2026-07-09 plan-vs-materialized feature-date case.
- Add tests for position sizing cap reason-code semantics with zero produced positions.
- Add system-status contract tests for overview PASS and shadow BLOCK separation.

## Closure and Runtime Switch Eligibility

Phase22 Closure: `NO`

Runtime Switch Approval: `NO`

Runtime Switch Ready: `NO`

5BD Historical Runtime PASS is accepted as Runtime evidence. 5BD Strategy Shadow BLOCK is safe and isolated, but it is not accepted as closure or switch readiness evidence because repair-required Strategy Shadow authority and observability defects remain.
