# Phase32-DX - 2023-12-11 Morning HALT Post-DW Root Cause Read-Only Audit

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260902T060955933565Z`
- Failure under audit: resume stopped at `2023-12-11:morning` with exit code `10`
- Mode: READ-ONLY audit
- Mutations performed by this audit: none to source/config/runtime/Pending/Ledger/run state
- Report creation only: `docs/phase_reports/phase32_dx_20231211_morning_halt_post_dw_root_cause_read_only_audit.md`

## Evidence Inspected

- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260902T060955933565Z/run_state.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260902T060955933565Z/strategy_shadow_manifest.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260902T060955933565Z/historical_evaluation_authority.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260902T060955933565Z/daily/2023-12-11/data_readiness/*`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260902T060955933565Z/daily/2023-12-11/market_refresh/*`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260902T060955933565Z/daily/2023-12-11/morning/*`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260902T060955933565Z/daily/2023-12-11/strategy/*`
- Current source inspection of:
  - `src/ai_fund_lab_v2/strategy/marginal_capital_value.py`
  - `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
  - `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py`
  - `scripts/runtime_test.py`
- Runtime Test Command Guide exit-code semantics.

No resume, recover, replay, fresh-run, or mutating runtime command was executed.

## Run State

- `run_state.status`: `HALT`
- `run_state.next_job`: `2023-12-11:morning`
- `halted_at.business_date`: `2023-12-11`
- `halted_at.job`: `morning`
- `halted_at.exit_code`: `10`
- `halted_at.resumed`: `true`
- completed business days: `293`
- last completed day before halt: `2023-12-08`

The `halted_at.feature_date_command_resolution` was `PASS`:

- `feature_date_authority_source`: `normal_feature_date_contract`
- `contract_status`: `PASS`
- `planned_feature_date`: `2023-12-11`
- `selected_feature_date`: `2023-12-11`
- `planned_matches_materialized`: `true`

Therefore the halt is not caused by missing feature-date materialization or PIT date selection at the resume entry gate.

## Exit Code 10 Meaning

The Runtime Test Command Guide maps:

- `0`: `PASS`
- `10`: `REVIEW_REQUIRED`
- `20`: `BLOCKED`
- `30`: `HALT`

So the observed command-level exit code `10` is canonical `REVIEW_REQUIRED`, not a subprocess crash and not a fail-closed precondition exit code by itself.

The morning CLI result confirms a normal Runtime manifest return:

- `daily/2023-12-11/morning/cli_result.json`
- `exit_code`: `10`
- stdout: `{"exit_code": 10, "manifest": ".runtime/runtime_state/run_manifest/2023-12-11/runtime-v2-morning-2023-12-11-20260902T224411.533652+0000.json"}`
- stderr: empty

## Pre-Morning Gates

For `2023-12-11`:

- `data_readiness/cli_result.json`: exit code `0`
- `market_refresh/cli_result.json`: exit code `0`
- `morning/cli_result.json`: exit code `10`

The first failing morning stage in `morning/runtime_manifest.json` is:

- stage `25`: `phase22_strategy_artifact_generation` = `BLOCK`
- stage `26`: `phase23_i_strategy_planning_authority_pipeline` = `BLOCKED`
- top-level reason: `morning pipeline blocked: strategy_runtime_planning_blocked`

Earlier morning readiness, data readiness, historical safety authority, candidate/opportunity producer, and PM producer stages passed or were ready.

## Direct Failure Cause

The first canonical failing artifact is:

`reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260902T060955933565Z/daily/2023-12-11/strategy/portfolio_construction_draft.json`

It contains:

- `schema_version`: `portfolio_construction_draft_shadow_error.v1`
- `producer_result_status`: `BLOCK`
- `runtime_consumer_eligibility`: `NOT_ELIGIBLE`
- `production_consumer_connected`: `false`
- `runtime_switch_performed`: `false`
- `reason_codes`: `["strategy_shadow_generation_error"]`
- `error`: `name '_two_stage_divergence_class' is not defined`

This is also recorded in `strategy_shadow_summary.json`:

- `root_blocker_components`: `["portfolio_construction", "runtime_planning"]`
- `errors[0].component`: `portfolio_construction_draft`
- `errors[0].error`: `name '_two_stage_divergence_class' is not defined`
- `direct_blockers.portfolio_construction.status`: `BLOCK`
- `direct_blockers.portfolio_construction.primary_reason_code`: `strategy_shadow_generation_error`

The downstream path is:

1. `portfolio_construction_draft` generation raises `NameError`.
2. Error artifact is emitted as `portfolio_construction_draft_shadow_error.v1`.
3. `portfolio_construction.json` becomes `portfolio_construction_shadow_error.v1` and fails formal portfolio-construction validation with missing required fields and unsupported schema.
4. `position_sizing` blocks with `reason_codes=["portfolio_construction_block:BLOCK"]`.
5. `runtime_planning` blocks with:
   - `upstream_block:INCOMPATIBLE_SCHEMA`
   - `upstream_block_propagation:position_sizing_or_portfolio_construction`
   - plus same-day planning reasons including `existing_pending_conflict:29620`.
6. `strategy_planning_authority_evidence.json` reports:
   - `status`: `BLOCKED`
   - `reason`: `strategy_runtime_planning_blocked`
7. Morning exits `10` because the run is configured with `--stop-on-review-required` and the strategy planning authority pipeline is blocked/review-required.

## DW Causality

DW modified the unified marginal-capital shadow implementation and connected the new DQ/DW shadow builder into portfolio construction:

- `src/ai_fund_lab_v2/strategy/marginal_capital_value.py`
  - adds/uses `_two_stage_divergence_class`
  - emits `unified_marginal_capital_shadow.v2`
  - emits `authoritative_consumer_count: 0`
  - emits `production_allocation_consumer: false`
  - emits `production_ordering_consumer: false`
  - emits `production_sizing_consumer: false`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
  - calls `marginal_capital_value.build_unified_marginal_capital_shadow(...)`
  - embeds `unified_marginal_capital_shadow` into the capital competition framework
  - records the shadow schema and consumer flags.

The target run evidence was generated while the working tree was dirty:

- subprocess trace `source_commit`: `1f64f49ee9a8dd48280007e4df656e5f03e231ca`
- subprocess trace `source_dirty`: `true`
- planned command source commit argument: `a56f2bc26105eb14fd67322b7cd53c0d6ef1b1bd`

The actual failing symbol name, `_two_stage_divergence_class`, belongs to the DW two-stage shadow implementation. Current source inspection shows `_two_stage_divergence_class` is now present in `marginal_capital_value.py`, which indicates the target run halted on an intermediate dirty DW source state where the function was referenced before being available to the Runtime path.

Conclusion: DW is directly causally related to the halt.

## Source / Producer Hash / Registry Check

Current inspected source hashes:

- `src/ai_fund_lab_v2/strategy/marginal_capital_value.py`: `8d8971f269a0c6a19983ca6d1c8dd9679f852cf435b26c45d97e16f7558e48e0`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`: `6568571b828c9bbd3c3b24ebd9c9d683d30d67e2999ad19fc565b209bc57d6d0`
- `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py`: `661607eed78087590b06c9058fe7338f3b048711197af0737a4d7b8d5cda86a9`
- `scripts/runtime_test.py`: `bcd96455e1d9fec68d5a75ab8dc635ad6f2304adf63395e83f828f9c2f94e038`

Accepted-generation evidence:

- `strategy_shadow_manifest.json`: `hash_validation = PASS`
- `historical_evaluation_authority.json.status`: `PASS`
- accepted generation: `phase19_aq_accepted_generation_641e6e313543f013`
- accepted aggregate hash: `b97d3ccb14448b6ac721afcd93acedbabf4275712bb07816f13c322b2045480b`

PM evidence:

- `strategy/position_management.json.validation_status`: `PASS`
- `strategy/position_management.json.source_authority_status`: `VALID`
- `strategy/position_management.json.existing_pm_authority_active`: `true`

No evidence was found that the first failure was an accepted generation mismatch, PM producer hash mismatch, registry checkpoint mismatch, or PM Runtime Adapter authority mismatch.

## Schema / Version Compatibility

There is schema incompatibility in the failure path, but it is downstream of the DW NameError:

- `portfolio_construction_draft.json` is an error artifact with schema `portfolio_construction_draft_shadow_error.v1`.
- `portfolio_construction.json` is an error artifact with schema `portfolio_construction_shadow_error.v1`.
- Formal portfolio-construction validation then reports required-field and unsupported-schema errors.
- Runtime planning records `upstream_block:INCOMPATIBLE_SCHEMA`.

Therefore the schema incompatibility is a consequence of the failed shadow generation artifact, not the primary cause.

## Shadow-Only Contract

Current source retains the explicit DQ/DW shadow-only consumer flags:

- `authoritative_consumer_count = 0`
- `shadow_only = true`
- `production_allocation_consumer = false`
- `production_ordering_consumer = false`
- `production_sizing_consumer = false`
- `runtime_planning_consumer = false`

The target run artifacts also show no broker write or runtime switch:

- `strategy_shadow_summary.active_runtime_consumer_eligibility`: `NO`
- `strategy_shadow_summary.broker_write_performed`: `false`
- `strategy_shadow_summary.external_delivery_performed`: `false`
- `strategy_shadow_summary.runtime_switch_performed`: `false`
- `legacy_shadow_comparison.active_runtime_decision_changed`: `false`
- `legacy_shadow_comparison.runtime_behavior_changed`: `false`

However, the shadow-only contract was not operationally isolated enough: a shadow builder exception inside portfolio construction prevented the formal planning artifact family from materializing, and that BLOCK propagated into morning planning. So the shadow did not become an authoritative allocator/sizer/orderer, but its failure was still allowed to block Production morning readiness.

## Latent Defect vs DW Regression

This is not evidenced as a pre-DW latent defect.

The first concrete error references a DW-introduced symbol:

`name '_two_stage_divergence_class' is not defined`

The failure occurs in `portfolio_construction_draft`, the component touched by DW via unified marginal-capital shadow embedding. Prior 293 completed days in the same target run had progressed through `2023-12-08`; the halt appeared on a resume executed against dirty post-DW source. The most precise classification is:

- DW implementation regression: YES
- Source/artifact registry mismatch: NO evidence
- Schema incompatibility: downstream consequence
- Runtime/Pending/Ledger state defect: NO evidence as first cause
- PIT/feature-date defect: NO evidence

## Production Impact

No trading side effect occurred at the failed `2023-12-11:morning` boundary:

- No `2023-12-11` sell planning, submit, execution, fill, position mutation, or cash mutation evidence was present in the inspected daily artifacts.
- The halt occurs before order submission.

Production behavior changed in the control-plane sense that morning cannot continue when the DW shadow builder fails inside the formal planning artifact generation path. Production Strategy semantics, allocation consumption, ordering consumption, sizing consumption, and broker writes did not change in the target evidence.

## Required Answers

- `DIRECT_FAILURE_CAUSE`: `portfolio_construction_draft` failed with `NameError: name '_two_stage_divergence_class' is not defined`; the resulting error artifact caused portfolio construction/position sizing/runtime planning to block and morning exited `10` as `REVIEW_REQUIRED`.
- `DW_CAUSALLY_RELATED`: `YES`
- `SHADOW_ONLY_CONTRACT_PRESERVED`: `PARTIAL` - authoritative consumer flags remain zero/false and no runtime switch/broker write occurred, but the shadow builder exception was not isolated from Production morning planning readiness.
- `PRODUCTION_BEHAVIOR_CHANGED`: `YES` for control-plane continuation availability; `NO` for submitted orders, fills, cash, positions, or Strategy semantic side effects.
- `PRODUCTION_REPAIR_REQUIRED`: `YES` unless current post-DW source is formally accepted as already repairing the missing-symbol path; at minimum, focused validation must prove DW shadow builder failures cannot block Production planning while `authoritative_consumer_count=0`.
- `SAFE_CONTINUATION_PATH`: same-run continuation from `2023-12-11:morning` after the DW source is validated/repaired. Do not replay prior completed days. Fresh-run is not required by the evidence inspected here.
- `TARGET_RUN_MUTATED`: `NO`

## Final Judgment

`PHASE32_DX_20231211_MORNING_HALT_ROOT_CAUSE_IDENTIFIED_DW_SHADOW_BUILDER_REGRESSION`

