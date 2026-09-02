# Phase32-DH — Post-DG Fresh-Run First-Day Morning HALT Root-Cause READ-ONLY Audit

## Final Judgment

`PHASE32_DH_POST_DG_FIRST_DAY_MORNING_HALT_ROOT_CAUSE_IDENTIFIED`

The target run halted at `2022-10-03:morning` because the Strategy planning consumer received only `UNRESOLVED` runtime-planning items after DG tick-normalized evidence was misread by Buy Quality as missing/insufficient. This is not a market-data readiness failure and not a PM accepted-generation/hash failure. It is a DG production consumer compatibility defect at the tick evidence propagation/source-selection boundary.

No code, config, runtime state, Pending, Ledger, replay, resume, recover, or fresh-run action was executed in this phase.

## Target Run

- Run: `runtime-test-historical-extended-smoke-20260902T051836637658Z`
- Profile: `historical-extended-smoke`
- Start date: `2022-10-03`
- Business days requested: `650`
- Initial cash: `1000000`
- Completed business days: `[]`
- Runtime status: `HALT`
- Continuation point: `2022-10-03:morning`
- Outer `runtime_test` exit code: `30`
- Runtime CLI exit code at failed job: `20`

## Exact HALT Evidence

Primary evidence:

- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260902T051836637658Z/run_state.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260902T051836637658Z/daily/2022-10-03/morning/cli_result.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260902T051836637658Z/daily/2022-10-03/morning/runtime_manifest.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260902T051836637658Z/daily/2022-10-03/morning/strategy_planning_authority_evidence.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260902T051836637658Z/daily/2022-10-03/strategy/buy_quality_decisions.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260902T051836637658Z/daily/2022-10-03/strategy/technical_features.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260902T051836637658Z/daily/2022-10-03/strategy/portfolio_construction.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260902T051836637658Z/daily/2022-10-03/strategy/runtime_planning.json`

Run state records:

- `market_refresh`: exit `0`
- `data_readiness`: exit `0`
- `morning`: exit `20`
- `halt_summary.root_reason`: `morning pipeline review required: strategy_planning_authority_unresolved`
- `halt_summary.halt_classification`: `REVIEW_REQUIRED`

Morning manifest records:

- `final_state`: `REVIEW_REQUIRED`
- `reason`: `morning pipeline review required: strategy_planning_authority_unresolved`
- `strategy_planning_authority`: `REVIEW_REQUIRED`
- `strategy_planning_authority_active`: `false`
- `strategy_planning_pm_authority`: `true`
- `strategy_planning_pm_authority_reason`: `same_day_pm_materialized_before_formal_strategy_generation`
- `candidate_review_required`: `false`
- `opportunity_review_required`: `false`
- `pm_review_required`: `false`
- `review_guard_summary.batch_blocking_count`: `0`
- `review_guard_summary.system_defect_count`: `0`

Strategy planning authority evidence records:

- `status`: `REVIEW_REQUIRED`
- `reason`: `strategy_planning_authority_unresolved`
- `reason_codes`: `["strategy_plan_order_side_unresolved"]`
- `planning_consumer_eligibility`: `REVIEW_REQUIRED`
- `pending_authority_eligibility`: `AUTHORITY_INELIGIBLE`
- `pending_commit_status`: `NOT_COMMITTED_REVIEW_REQUIRED_EMPTY_UNSCOPED`
- `pending_item_count`: `0`
- `selected_symbols`: `[]`

## Failure Path

1. `market_refresh` completed successfully and produced current-run historical evidence.
2. `data_readiness` completed successfully and selected `feature_date = 2022-10-03` from a materialized feature-date contract.
3. `technical_features.json` produced 50 rows with valid PIT minimum-tick and tick-normalized evidence.
4. Buy Quality did not consume that valid tick evidence as authoritative row evidence.
5. `buy_quality_decisions.json` classified all 50 rows as `tick_quantization_status = INSUFFICIENT_EVIDENCE`.
6. Of those 50 rows, 39 became `quality_action = REVIEW_REQUIRED`; 11 became `REJECT`.
7. Portfolio Construction received Buy Quality review/reject outputs and produced no deployable security allocation:
   - `member_count = 50`
   - `resolved_target_member_count = 0`
   - `final_no_deployable_opportunity = true`
   - `selected_symbols = []`
8. Runtime Planning produced 38 plans, all `planning_intent = UNRESOLVED` and `order_side_intent = UNRESOLVED`.
9. Strategy Planning Authority rejected Pending publication with `strategy_plan_order_side_unresolved`.
10. Morning halted intentionally with Runtime CLI exit code `20`; `runtime_test` recorded run-level HALT exit code `30`.

## DF Minimum-Tick Authority First-Day Status

`technical_features.json` is clean on the failed first day:

- `producer_result_status`: `PASS`
- `validation_status`: `PASS`
- `coverage_status`: `FULL`
- `pit_validation.status`: `PASS`
- `row_count`: `50`
- `minimum_tick_authority_schema_version`: present
- `tick_normalized_evidence_schema_version`: `tick_normalized_trend_momentum.v1`
- `minimum_tick_authority_source`: `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260902T051836637658Z/daily/2022-10-03/market_refresh/inputs/historical_asof/2022-10-03/raw/jquants/listed_issues/data.parquet`
- Row counts:
  - `minimum_tick_authority_status = KNOWN`: `50`
  - `minimum_tick_authority_status = INSUFFICIENT_EVIDENCE`: `0`
  - `tick_quantization_status = PASS`: `50`
  - `tick_quantization_status = INSUFFICIENT_EVIDENCE`: `0`

This confirms DF first-day minimum-tick authority materialization itself passed and was run-scoped/PIT.

## DG Consumer Compatibility Finding

Buy Quality evidence contradicts Technical Features:

- `decision_count`: `50`
- `quality_action = REVIEW_REQUIRED`: `39`
- `quality_action = REJECT`: `11`
- `tick_quantization_status = INSUFFICIENT_EVIDENCE`: `50`
- rows with `tick_normalized_evidence_missing`: `50`
- rows with non-empty `tick_quantization_validation.minimum_tick_authority_hash`: `0`

Sample BQ tick validation for `94320`:

- `status`: `REVIEW_REQUIRED`
- `tick_quantization_status`: `INSUFFICIENT_EVIDENCE`
- `trend_state`: `INSUFFICIENT_EVIDENCE`
- `momentum_state`: `INSUFFICIENT_EVIDENCE`
- `single_tick_pct`: `null`
- `minimum_tick_authority_hash`: `""`
- `reason_codes`:
  - `tick_normalized_evidence_insufficient_review_required`
  - `tick_normalized_evidence_missing`

The source-level cause is in the DG production wiring/schema compatibility:

- `shadow_runtime._supply_reentry_source_evidence(...)` reports `technical_supplied_count = 50`, but the enrichment list copies minimum-tick fields such as `minimum_tick`, `single_tick_pct`, `minimum_tick_authority_status`, and `minimum_tick_authority_hash`; it does not copy the full tick-normalized consumer fields required by BQ such as:
  - `tick_quantization_status`
  - `tick_normalized_trend_state`
  - `momentum_confidence_state`
  - `candidate_rank_tick_reliability`
  - `trend_robustness_authority`
  - `momentum_confidence_authority`
  - tick-normalized reason codes
- `buy_quality._tick_quantization_source_row(opportunity, candidate)` treats the presence of tick keys as materialized evidence.
- Candidate rows contain DG tick placeholder keys with empty string values:
  - `tick_quantization_status = ""`
  - `tick_normalized_trend_state = ""`
  - `momentum_confidence_state = ""`
  - `candidate_rank_tick_reliability = ""`
- Because enriched opportunity rows do not expose the full tick-normalized fields, BQ falls through to the candidate placeholder row and `tick_evidence_from_row(...)` returns `INSUFFICIENT_EVIDENCE`.

Therefore the first bad boundary is not Technical Features generation. It is the Technical Features -> Buy Quality consumer-materialization/source-selection boundary.

## Active Accepted Generation / Registry Status

The accepted AI generation path is not the cause:

- `historical_evaluation_authority_validation.status`: `PASS`
- `generation_id`: `phase19_aq_accepted_generation_641e6e313543f013`
- `run_authority_hash`: `sha256:e30ee021a214c80e917bdd9e567b8ff01d33b6007ac416f994929cea4b1579f6`
- `latest_fallback_absent`: `true`
- `production_authority_unchanged`: `true`

PM accepted source authority is not the cause:

- Current `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py` hash: `661607eed78087590b06c9058fe7338f3b048711197af0737a4d7b8d5cda86a9`
- Runtime PM artifact accepted hash: `661607eed78087590b06c9058fe7338f3b048711197af0737a4d7b8d5cda86a9`
- PM `generation_binding_validation.status`: `PASS`
- PM `model_hash_status`: `PASS`
- PM `scaler_hash_status`: `PASS`
- PM source artifact `technical_features`: `PASS`
- PM source artifact `accepted_generation`: `PASS`

This excludes the Phase32-A/D PM Runtime Adapter hash-mismatch class for this run.

## Relation to DF and DG

DF introduced canonical PIT minimum-tick authority and Technical Features row materialization. On this run, that materialization passes on the first day.

DG promoted tick-normalized momentum/trend evidence into production consumers, including Buy Quality. The HALT is introduced by DG consumer compatibility: the actual fresh-run BQ path does not receive the full tick-normalized row contract even though Technical Features produced it. Empty candidate placeholder fields are treated as materialized evidence, causing BQ to fail closed across all rows.

This is a production correctness defect in the new DG wiring/consumer contract, not performance tuning and not a Strategy parameter/threshold/weight issue.

## Schema / Manifest Compatibility

The relevant schema incompatibility is:

- Producer side: `technical_features.json` row schema includes valid `tick_quantization_status`, `tick_normalized_trend_state`, `momentum_confidence_state`, `candidate_rank_tick_reliability`, authorities, and hash-backed minimum-tick fields.
- Consumer side: Buy Quality consumes only `candidate_summary` and `opportunity_summary`, plus optional volatility/corporate artifacts. It does not receive `technical_features` as a first-class source artifact.
- Bridging side: `shadow_runtime._supply_reentry_source_evidence` enriches opportunity rows from Technical Features, but currently omits the full tick-normalized consumer fields.
- Resolver side: `_tick_quantization_source_row` considers rows with empty placeholder keys to be usable source rows.

The manifest correctly records `strategy_input_sources.technical_features` with current-run path/hash and `PIT = PASS`, but Buy Quality's own `source_artifacts` do not include `technical_features`. BQ therefore has no direct canonical source record for the valid DF evidence it should consume.

## Classification

- Root cause class: `Runtime/code regression`
- Subclass: `DG production consumer compatibility / schema materialization defect`
- Data readiness issue: `NO`
- Config/environment issue: `NO`
- Accepted-generation/hash mismatch: `NO`
- State/ledger/broker authority issue: `NO`
- Intentional fail-closed safety gate: `YES`, as the immediate HALT behavior once authority became unresolved
- Strategy performance issue: `NO`

## Required Answers

1. `TARGET_RUN`: `runtime-test-historical-extended-smoke-20260902T051836637658Z`
2. `HALT_EXACT_COMPONENT`: `Runtime morning -> Strategy Planning Authority activation`
3. `HALT_EXACT_ERROR`: `morning pipeline review required: strategy_planning_authority_unresolved`; first canonical reason code `strategy_plan_order_side_unresolved`
4. `HALT_EXACT_EVIDENCE_PATH`: `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260902T051836637658Z/daily/2022-10-03/morning/strategy_planning_authority_evidence.json`
5. `HALT_ROOT_CAUSE_CLASS`: `Runtime/code regression: DG tick-normalized evidence consumer compatibility defect`
6. `DF_MINIMUM_TICK_AUTHORITY_FIRST_DAY_STATUS`: `PASS`; 50/50 Technical Feature rows have `minimum_tick_authority_status=KNOWN` and `tick_quantization_status=PASS`
7. `DG_FIRST_DAY_CONSUMER_COMPATIBILITY`: `FAIL`; Buy Quality actual path reads 50/50 rows as `tick_normalized_evidence_missing`
8. `ACTIVE_ACCEPTED_GENERATION_STATUS`: `PASS`; historical accepted generation and PM adapter authority are not causal
9. `SCHEMA_MANIFEST_COMPATIBILITY`: `FAIL` at Technical Features -> Buy Quality materialization/source-selection boundary
10. `HALT_FAIL_CLOSED_BEHAVIOR_CORRECT`: `YES`; once Runtime Planning produced unresolved order sides, Pending authority correctly failed closed
11. `REGRESSION_INTRODUCED_BY`: `Phase32-DG production promotion wiring/consumer compatibility`
12. `PRODUCTION_REPAIR_REQUIRED`: `YES`
13. `REPAIR_SCOPE`: Narrowly repair DG tick-normalized evidence propagation/source selection so BQ consumes current-run Technical Features authority, ignores empty placeholder tick fields, and preserves fail-closed behavior for genuinely missing/stale/mismatched tick authority
14. `PERFORMANCE_TUNING_EXECUTED`: `NO`
15. `PRODUCTION_CHANGE_EXECUTED`: `NO`
16. `TARGET_RUN_MUTATED`: `NO`
17. `FAILED_RUN_REUSABLE_AFTER_REPAIR`: `LIKELY YES`; no completed business day, no committed Pending item, no submit/execution side effect, and `next_job=2022-10-03:morning`
18. `FRESH_VALIDATION_REQUIRED`: `YES`; after repair, a new user-operated fresh-run should validate the first-day path, even though the failed run appears retryable from the morning boundary
19. `NEXT_RECOMMENDED_STEP`: Implement a narrow Phase32-DI repair for the DG BQ tick evidence materialization/source-selection contract, then run focused regression and user-operated fresh Historical validation
20. `FINAL_JUDGMENT`: `PHASE32_DH_POST_DG_FIRST_DAY_MORNING_HALT_ROOT_CAUSE_IDENTIFIED`

## Minimal Future Repair Boundary

Required repair should be limited to the DG evidence handoff and validation contract:

- Propagate full Technical Features tick-normalized fields into the BQ-consumed row surface, or make `technical_features` a first-class BQ source summary.
- Change BQ tick source selection so empty placeholder fields do not shadow valid current-run Technical Features authority.
- Preserve fail-closed behavior for actual `INSUFFICIENT_EVIDENCE`, stale/cross-run authority, future-date authority, and schema/hash mismatch.
- Add a first-day fresh-run-shaped focused test where Technical Features has 50 valid tick rows and candidate rows contain empty placeholder tick keys; BQ must consume valid technical authority rather than fail all rows.

No Strategy parameter, threshold, weight, ranking, cash policy, PM semantics, BQ threshold, or performance tuning change is indicated by this audit.
