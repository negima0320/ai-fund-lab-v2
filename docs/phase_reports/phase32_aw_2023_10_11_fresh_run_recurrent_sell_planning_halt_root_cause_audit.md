# Phase32-AW — 2023-10-11 Fresh-Run Recurrent Sell-Planning HALT Root-Cause Audit

## Objective

READ-ONLY audit of the recurrent 2023-10-11 halt in fresh Historical run:

`runtime-test-historical-extended-smoke-20260831T003243720082Z`

Observed failure:

- business date: `2023-10-11`
- failed job: `sell_planning`
- job exit code: `20`
- run status: `HALT`
- completed business days: `252`, through `2023-10-10`

No code, config, runtime state, Pending state, recovery, replay, resume, or fresh-run mutation was performed.

## Evidence Coverage

Inspected target-run artifacts under:

`reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260831T003243720082Z`

Key artifacts:

- `run_state.json`
- `historical_evaluation_authority.json`
- `daily/2023-10-11/morning/runtime_manifest.json`
- `daily/2023-10-11/morning/planning_evidence.json`
- `daily/2023-10-11/morning/pending_generation_evidence.json`
- `daily/2023-10-11/sell_planning/runtime_manifest.json`
- `daily/2023-10-11/sell_planning/data_readiness_authority.json`
- `daily/2023-10-11/sell_planning/pending_continuity_evidence.json`
- `daily/2023-10-11/sell_planning/position_management_evidence.json`
- `daily/2023-10-11/position_management/pm_decisions.json`
- `daily/2023-10-11/positions/position_campaigns.json`
- `daily/2023-10-11/strategy/portfolio_construction.json`
- `daily/2023-10-11/strategy/position_sizing.json`
- `daily/2023-10-11/strategy/runtime_planning.json`

There are no `daily/2023-10-11/submit` or `daily/2023-10-11/execution` artifacts in this fresh run. The run halted before Submit.

## Run State

`run_state.json` records:

- `status = HALT`
- `next_job = 2023-10-11:sell_planning`
- `halted_at.business_date = 2023-10-11`
- `halted_at.job = sell_planning`
- `halted_at.exit_code = 20`
- command included:
  - `--mode historical`
  - `--broker-environment historical_simulated`
  - `--job sell_planning`
  - `--submit-enabled false`
  - `--stop-on-review-required`
  - `--stop-on-blocked`
  - `--runtime-test-run-id runtime-test-historical-extended-smoke-20260831T003243720082Z`
  - `--runtime-test-evidence-root reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260831T003243720082Z`

The completed-window measurement through `2023-10-10` remains outside the failing boundary.

## First Canonical Failure

The first canonical failure is emitted by `sell_planning` Data Readiness:

- `exit_code = 20`
- `reason = historical_safety_temporal_authority_missing`
- `final_safety_status = REVIEW_REQUIRED`
- `final_safety_reason = historical_safety_temporal_authority_missing`
- `safety_status = SAFETY_MISSING`
- `safety_reason = safety decision evidence missing`
- `safety_artifact_path = .runtime/runtime_state/safety/latest_safety_decision.json`
- `historical_neutral_authority_generated_or_resolved = false`
- `pending_active = true`
- `pending_slot_status = REVIEW_REQUIRED`
- `component_reasons.safety = ["historical_safety_temporal_authority_missing"]`
- `component_reasons.pending = ["pending_review_required"]`
- `review_guard_summary.guard_codes = ["PENDING_BATCH_REVIEW_REQUIRED", "TEMPORAL_MISMATCH"]`
- `review_guard_summary.guard_classes = ["BATCH_LEVEL_FAILURE", "DATA_INTEGRITY_SAFETY"]`

`sell_planning/pending_continuity_evidence.json` and `sell_planning/position_management_evidence.json` both show:

- `status = NOT_EXECUTED`
- `reason = historical_safety_temporal_authority_missing`

Therefore the failure occurs before sell-planning PM/SELL composition executes. It is not a Submit failure in the current run.

## 2023-10-11 Sell Path Trace

### Morning and Pending Generation

`morning/runtime_manifest.json` passed:

- `exit_code = 0`
- `pending_active = false`
- `pending_slot_status = EMPTY`
- `safety_status = PASS`
- `safety_reason = historical_neutral_no_event_safety_ready`
- `final_safety_status = READY`
- `final_safety_reason = historical_neutral_no_event_safety_ready`

`morning/planning_evidence.json` and `morning/pending_generation_evidence.json` passed:

- `pending_commit_status = COMMITTED_CURRENT`
- `pending_plan_id = pending-strategy-plan-historical-2023-10-11-049fca273c90bbe0`
- `pending_item_count = 4`
- `pending_path = .runtime/pending_order_plan/pending_order_plan.json`

The generated Pending has:

- `state = REVIEW_REQUIRED`
- `target_session_date = 2023-10-11`
- `environment = historical`
- `review_scope = AUTHORITY_UNKNOWN_REVIEW`
- `review_scope_source = phase24_ht_planning_submit_feasibility_v1`
- `review_scope_reason = reserved notional exceeds dynamic cash capacity;corporate_action_event_not_resolved;corporate_action_event_not_resolved`
- `sell_continuation_allowed = false`
- `approved_item_ids = []`
- `review_required_buy_item_ids = [strategy-bada62dfc97301e522e3, strategy-00ff402eea89a95ce104]`
- `review_required_sell_item_ids = [strategy-cfa6b28e6e655e622536]`

The Pending safety context itself is same-day historical neutral:

- `safety_authority = historical_initial_no_external_effect`
- `safety_decision = NEUTRAL`
- `safety_decision_id = historical-neutral-safety:2023-10-11`
- `safety_business_date = 2023-10-11`
- `runtime_test_run_id = runtime-test-historical-extended-smoke-20260831T003243720082Z`

However, Data Readiness rejects Historical neutral safety authority because the Pending lifecycle/review scope is not compatible with daily neutral sell continuation:

- `pending_safety_authority.status = REVIEW_REQUIRED`
- `pending_safety_authority.reason = historical_pending_safety_authority_mismatch`
- `pending_safety_authority.review_scope = AUTHORITY_UNKNOWN_REVIEW`
- `pending_safety_authority.sell_continuation_allowed = false`
- `pending_safety_authority.mismatched_fields = ["pending_lifecycle_state"]`
- `historical_neutral_authority_reason = historical_daily_neutral_safety_authority_not_available`

### PM / PC / PS / Runtime Planning

The 2023-10-11 SELL candidates are `50280` and `92460`.

#### 50280

PM:

- `symbol = 50280`
- `decision_type = REDUCE`
- `position_campaign_id = pc-a10786827568f7a1-50280-0001`
- `reason_codes = ["risk_increased_but_trend_not_broken"]`

PC:

- `membership_intent = REMOVE_CANDIDATE`
- `pm_action = EXIT`
- `source_pm_decision_ref = pm-2023-10-11-50280-reduce`
- `current_quantity = 100`
- `target_weight = 0.0`
- `position_campaign_id = pc-a10786827568f7a1-50280-0001`
- `reference_price = 461.0`
- `source_pm_reason_codes` include:
  - `pm_discrete_control_persistent_deterioration_exit`
  - `risk_increased_but_trend_not_broken`
  - `strategy_intelligence_sell_side_evidence_connected`

PS:

- `current_quantity = 100`
- `target_quantity_candidate = 0`
- `quantity_delta_candidate = -100`
- `final_target_quantity = 0`
- `final_quantity_delta = -100`
- `quantity_status = RESOLVED_CANDIDATE`

Runtime Planning:

- `planning_id = rp-2023-10-11-50280-sell_exit-aacde78e4d38427a`
- `planning_intent = SELL_EXIT`
- `order_side_intent = SELL`
- `planned_quantity = 100`
- `quantity_delta_candidate = -100`
- `target_quantity_candidate = 0`
- `quantity_status = RESOLVED_EXECUTABLE`
- `source_pm_action = EXIT`
- `source_pm_decision_id = pm-2023-10-11-50280-reduce`
- `full_liquidation_authority_present = true`
- `full_liquidation_authority_source = PM_EXIT`
- `reference_price = 461.0`
- `reference_price_authority.PIT_status = PASS`
- `reference_price_authority.source_path` is the target run's 2023-10-11 `raw_normalized/jquants/equities_bars_daily/data.parquet`

Pending item:

- `pending_item_id = strategy-cfa6b28e6e655e622536`
- `source_decision_id = rp-2023-10-11-50280-sell_exit-aacde78e4d38427a`
- `source_decision_type = SELL_EXIT`
- `source_pm_decision_id = pm-2023-10-11-50280-reduce`
- `quantity = 100`
- `state = REVIEW_REQUIRED`
- `batch_submit_status = ITEM_REVIEW_REQUIRED`
- `feasibility_status = REVIEW_REQUIRED`
- `item_review_reason = corporate_action_event_not_resolved`

Corporate Action authority:

- `corporate_action_adjustment_authority_status = REVIEW_REQUIRED`
- `corporate_action_adjustment_authority_reason = corporate_action_event_not_resolved`
- `corporate_action_adjustment_factor = 0.3333333333333333`
- `corporate_action_effective_date = 2023-10-11`
- `corporate_action_event_status = IMPACT_DETECTED`
- `corporate_action_event_type = UNKNOWN_ADJFACTOR_IMPACT`
- `current_quantity = 100`
- `broker_available_quantity = 100`
- `pending_quantity = 100`
- `submit_quantity = 100`
- `pit_validation_status = PASS`
- `quantity_reconciliation_status = REVIEW_REQUIRED`
- `price_reconciliation_status = REVIEW_REQUIRED`
- reason codes:
  - `corporate_action_event_not_resolved`
  - `corporate_action_type_unresolved`
  - `corporate_action_ledger_adjustment_missing`
  - `corporate_action_current_adjustment_missing`
  - `corporate_action_pending_quantity_stale`
  - `corporate_action_already_applied_not_confirmed`
  - `corporate_action_adjusted_quantity_missing`

The Corporate Action event lineage inside the authority still references the previous run path:

`reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260830T081425790243Z/daily/2023-10-11/market_refresh/inputs/historical_asof/2023-10-11/raw/jquants/equities_bars_daily/data.parquet`

This is stale/cross-run evidence lineage and should be cleaned up in the repair scope. It is not the first run-level failure, because the fresh run first stops at sell_planning Data Readiness before Submit, but it confirms that the CA authority is being carried through persistent `.runtime` state rather than purely run-scoped fresh evidence.

#### 92460

PM:

- `symbol = 92460`
- `decision_type = REDUCE`
- `position_campaign_id = pc-d6a05a4ff55392f6-92460-0001`
- `reason_codes = ["risk_increased_but_trend_not_broken"]`

PC:

- `membership_intent = REMOVE_CANDIDATE`
- `pm_action = EXIT`
- `source_pm_decision_ref = pm-2023-10-11-92460-reduce`
- `current_quantity = 100`
- `target_weight = 0.0`
- `position_campaign_id = pc-d6a05a4ff55392f6-92460-0001`
- `reference_price = 3130.0`

PS:

- `current_quantity = 100`
- `target_quantity_candidate = 0`
- `quantity_delta_candidate = -100`
- `final_target_quantity = 0`
- `final_quantity_delta = -100`

Runtime Planning:

- `planning_id = rp-2023-10-11-92460-sell_exit-2c6f66da8c3bd5da`
- `planning_intent = SELL_EXIT`
- `order_side_intent = SELL`
- `planned_quantity = 100`
- `quantity_status = RESOLVED_EXECUTABLE`
- `source_pm_action = EXIT`
- `source_pm_decision_id = pm-2023-10-11-92460-reduce`
- `full_liquidation_authority_present = true`
- `full_liquidation_authority_source = PM_EXIT`

Pending item:

- `pending_item_id = strategy-75f58281becff7dcaa44`
- `source_decision_id = rp-2023-10-11-92460-sell_exit-2c6f66da8c3bd5da`
- `source_decision_type = SELL_EXIT`
- `source_pm_decision_id = pm-2023-10-11-92460-reduce`
- `quantity = 100`
- `feasibility_status = PASS`
- `corporate_action_adjustment_authority_status = PASS`
- `corporate_action_adjustment_authority_reason = corporate_action_not_detected`
- `corporate_action_adjustment_factor = 1.0`
- `quantity_reconciliation_status = PASS`
- `batch_submit_status = BLOCKED_BY_BATCH_REVIEW`
- `item_review_reason = batch_submit_blocked_by_item_scoped_review`

92460 is not defective as an item. It is blocked only because the batch contains reviewed items and sell_planning stops before Submit.

#### BUY Review Items

The same Pending also contains two BUY_NEW review items:

- `38560`: `BUY_NEW`, `quantity = 100`, `item_review_reason = reserved notional exceeds dynamic cash capacity`
- `76920`: `BUY_NEW`, `quantity = 400`, `item_review_reason = corporate_action_event_not_resolved`

These BUY items are not the first failing SELL boundary. They contribute to the Pending's `REVIEW_REQUIRED` state, but the sell-continuation contract would tolerate BUY-only item-scoped review. The blocker for SELL continuation is the reviewed SELL item `50280`.

## Exact Failing Invariant

The exact failing invariant is:

Historical `sell_planning` requires a READY same-day safety temporal authority before proceeding. When the active same-day Pending is `REVIEW_REQUIRED`, Historical daily neutral authority is accepted only if the Pending review scope is compatible with sell continuation. The current Pending has `review_scope = AUTHORITY_UNKNOWN_REVIEW`, `sell_continuation_allowed = false`, and a reviewed SELL item (`50280`). Therefore Data Readiness cannot resolve `HISTORICAL_DAILY_NEUTRAL` safety and returns:

`historical_safety_temporal_authority_missing`

This is correct as a fail-closed safety result for the unresolved 50280 SELL, but the current orchestration has no canonical normal fresh-run path to:

1. keep 50280 in REVIEW_REQUIRED,
2. keep BUY review items unsubmitted,
3. allow unaffected feasible SELL item 92460 to proceed, or
4. terminalize a no-submission/review-only same-day shape without halting the whole long run.

## Comparison With Previous 2023-10-11 Halt

### Phase32-Z / AA Root

The earlier primary long Historical run `runtime-test-historical-extended-smoke-20260830T081425790243Z` failed at:

- `2023-10-11:submit`
- after 92460 was accepted/submitted
- when 50280 reached Submit as approved/PASS-submittable despite unresolved Corporate Action authority

Phase32-AA repaired that Planning/Pending/Submit authority mismatch by requiring 50280's unresolved Corporate Action status to be materialized before Submit as item `REVIEW_REQUIRED`.

### Current Fresh Run

In the current fresh run, Phase32-AA behavior is present:

- 50280 does not reach Submit.
- 50280 is already `REVIEW_REQUIRED` in Pending.
- Its feasibility guard is item-scoped and names `corporate_action_event_not_resolved`.
- 92460 is feasible/PASS but batch-blocked.

Therefore the old Z/AA root cause is not reproduced as a Submit leak.

### Phase32-AD / AE Relation

Phase32-AD already observed a `sell_planning` halt with:

- `historical_safety_temporal_authority_missing`
- secondary `pending_review_required`

after partial-submit recovery replay regenerated a same-day review Pending. Phase32-AE then repaired the special partial-submit replay path by adding `finalize-partial-submit-day`, an accepted-items-only finalization path for the old partially submitted run.

Phase32-AE did not repair the ordinary fresh-run `morning -> sell_planning` path for a same-day mixed Pending containing a reviewed SELL item and an unaffected feasible SELL item. The current fresh run reaches that ordinary path, not the AE finalization path.

## Classification

Classification:

`PREVIOUS_REPAIR_INCOMPLETE`

Explanation:

- Not `SAME_ROOT_CAUSE_REGRESSION` relative to Phase32-Z/AA: 50280 is no longer leaking as approved to Submit.
- Same root shape as Phase32-AD sell_planning halt, but AE scoped the repair to partial-submit finalization and did not cover fresh-run pre-submit mixed-review Pending.
- The previous fix did not protect this run because the current path is a normal fresh-run sell_planning entry, with no preserved accepted submit evidence and no invocation of `finalize-partial-submit-day`.

## Failure Class

- Historical-profile-specific: YES for the reproduced trigger (`historical_replay = true`, `historical_simulated`, `HISTORICAL_DAILY_NEUTRAL` safety).
- Corporate-Action-specific: YES for the concrete reviewed SELL item `50280` (`AdjFactor = 0.3333333333333333`, unresolved adjustment).
- SELL_EXIT-specific: YES for the concrete failing SELL item (`source_decision_type = SELL_EXIT`).
- SELL_REDUCE-specific: NO as final executable semantic; PM's raw decision name is `REDUCE`, but PC/PS/Runtime convert to full `SELL_EXIT` via `PM_EXIT` full liquidation authority.
- Planning/Pending authority mismatch: YES at the orchestration/consumer boundary. Planning/Pending correctly records 50280 as REVIEW_REQUIRED, but sell_planning cannot continue/terminalize the mixed review shape.
- Basis/quantity identity mismatch: CONTRIBUTING for 50280 Corporate Action authority (`quantity_reconciliation_status = REVIEW_REQUIRED`, stale pending quantity risk); not the first run-level failure.
- Generic Production-path defect: PARTIAL/UNCONFIRMED. The concrete failure is Historical safety temporal authority, but the broader inability to route unaffected feasible SELL items around item-level reviewed SELLs is a common planning/pending orchestration correctness issue.

## Minimal Correct Repair Boundary

Do not change Strategy, SELL decision rules, Corporate Action semantics, quantities, thresholds, weights, or safety fail-closed behavior.

Narrow repair scope:

1. Define a canonical Pending review-scope for mixed SELL review:
   - reviewed SELL items must not submit,
   - unaffected feasible SELL items may be explicitly preserved as executable only if their own Corporate Action/quantity/price/broker authority is PASS,
   - BUY review items remain item-scoped and unsubmitted,
   - batch-level safety must remain fail-closed for unresolved SELL items unless the scope explicitly separates executable and reviewed SELL authorities.
2. Teach Historical safety temporal authority / Data Readiness to recognize that explicit scope, rather than treating the whole Pending as `AUTHORITY_UNKNOWN_REVIEW`.
3. Teach normal fresh-run sell_planning/submit orchestration how to consume that scope:
   - 50280 stays REVIEW_REQUIRED and is not submitted,
   - 92460 can proceed once idempotency and item authority are PASS,
   - no duplicate submission is possible,
   - Submit must still fail closed if 50280 appears as submittable.
4. Clean the Corporate Action authority freshness boundary so fresh runs do not carry stale prior-run lineage paths in `.runtime/runtime_state/corporate_action_adjustments/<date>/<symbol>.json`.

Required focused tests:

- fresh-run-style `morning -> sell_planning` with reviewed CA SELL + feasible SELL:
  - 50280-like item remains REVIEW_REQUIRED,
  - 92460-like item remains executable or is explicitly terminalized by the intended contract,
  - no `historical_safety_temporal_authority_missing` for the accepted mixed-review scope,
  - no Submit leak of reviewed SELL item.
- stale cross-run Corporate Action authority lineage must be rejected or regenerated from current run-scoped evidence.
- genuine unresolved Corporate Action reviewed SELL cannot be submitted.
- genuine missing/stale safety authority outside the accepted scope still fail-closes.
- existing Phase32-AA, Phase32-AE, G129, KI-004, KI-006, and Winner Retention focused tests remain PASS.

## Resume / Fresh-Run Readiness

The current run halted at `sell_planning` before Submit and Execution:

- no 2023-10-11 submit artifacts exist,
- no 2023-10-11 execution artifacts exist,
- no broker/order side effect was created by the failing job,
- `external_effect_audit.status = PASS`,
- `broker_order_api_calls = 0`.

After a future narrow repair, same-run resume from `2023-10-11:sell_planning` should be safe if the repair accepts the existing Pending or regenerates only canonical same-day sell_planning state idempotently. A new fresh-run is not inherently required for correctness of completed 252BD.

Because the repair has not yet been implemented or validated, resume is `CONDITIONAL`, not immediately safe now.

## Required Final Answers

- `EXACT_FAILING_SYMBOL`: run-level first failure has no item symbol; the concrete SELL item that makes Pending incompatible is `50280`. The unaffected feasible SELL item is `92460`.
- `EXACT_FAILING_INVARIANT`: Historical sell_planning Data Readiness cannot resolve same-day neutral safety authority for active same-day `REVIEW_REQUIRED` Pending with `review_scope = AUTHORITY_UNKNOWN_REVIEW`, `sell_continuation_allowed = false`, and reviewed SELL item `50280`; it returns `historical_safety_temporal_authority_missing`.
- `CURRENT_ROOT_CAUSE`: normal fresh-run sell_planning lacks a canonical mixed-review SELL continuation/terminalization contract for unresolved Corporate Action SELL item `50280` plus feasible SELL item `92460`; the reviewed SELL item correctly prevents blanket neutral sell continuation, but the orchestration cannot isolate reviewed vs executable SELL items and halts the run before Submit.
- `IS_THIS_THE_SAME_ROOT_CAUSE_AS_THE_PREVIOUS_10_11_HALT`: NO relative to Phase32-Z/AA submit leak. It is the same sell_planning safety/pending shape as Phase32-AD, now exposed on ordinary fresh-run path. Classification: `PREVIOUS_REPAIR_INCOMPLETE`.
- `WHY_DID_THE_PREVIOUS_REPAIR_NOT_PREVENT_THIS_FRESH_RUN_FAILURE`: Phase32-AA did protect 50280 by making it REVIEW_REQUIRED before Submit. Phase32-AE repaired only the partial-submit accepted-items finalization path, not the normal fresh-run `morning -> sell_planning` path with same-day mixed reviewed SELL Pending.
- `FIRST_BAD_BOUNDARY`: `morning pending_generation COMMITTED_CURRENT` -> `sell_planning runtime_data_readiness_gate`; Data Readiness rejects Historical neutral safety authority before sell_planning PM/Pending continuity executes.
- `IS_THIS_A_CORRECTNESS_DEFECT`: YES. The system fail-closes safely, but the current contract cannot progress an otherwise valid long Historical run when a reviewed Corporate Action SELL coexists with an unaffected feasible SELL. It also exposes stale cross-run CA authority lineage.
- `MINIMAL_REPAIR_SCOPE`: Pending review-scope authority + Historical safety temporal authority + normal sell_planning/submit orchestration for mixed reviewed SELL/executable SELL, plus CA authority run-scoped freshness; no Strategy semantic change.
- `CAN_CURRENT_RUN_BE_RESUMED_AFTER_REPAIR`: CONDITIONAL YES. Since no 2023-10-11 Submit/Execution side effects exist, same-run resume from sell_planning should be safe after focused validation of the narrow repair.
- `IS_NEW_FRESH_RUN_REQUIRED`: NO, not inherently. Fresh-run may be useful for full acceptance, but completed 252BD are not contaminated by this pre-submit halt.
- `IS_PRODUCTION_PATH_AFFECTED`: CONCRETE repro is Historical-profile-specific. The broader mixed reviewed SELL/executable SELL orchestration boundary is production-relevant unless Production has a separate operator-review workflow that explicitly handles the same scope.
- `FINAL_JUDGMENT`: `PHASE32_AW_FRESH_RUN_SELL_PLANNING_MIXED_SELL_REVIEW_CONTRACT_GAP_IDENTIFIED`

## NO CODE CHANGE

Confirmed. This phase performed READ-ONLY investigation and created this report only.

## NO Runtime State Mutation

Confirmed. No resume, recover, replay, fresh-run, rollback, Submit, Execution, or state mutation command was executed.

## Final Judgment

`PHASE32_AW_FRESH_RUN_SELL_PLANNING_MIXED_SELL_REVIEW_CONTRACT_GAP_IDENTIFIED`
