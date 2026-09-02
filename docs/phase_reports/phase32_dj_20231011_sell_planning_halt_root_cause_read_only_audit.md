# Phase32-DJ — 2023-10-11 Sell-Planning HALT Root-Cause READ-ONLY Audit

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260902T060955933565Z`
- Requested profile/horizon: `historical-extended-smoke`, `650` business days
- Latest completed business date: `2023-10-10`
- Halt boundary: `2023-10-11:sell_planning`
- Runtime CLI exit code: `20`
- Outer `runtime_test` exit code: `30`
- Execution in this phase: READ-ONLY audit plus this report only.

No resume, recovery, replay, fresh-run, code/config/source change, Pending mutation, Ledger mutation, or runtime-state mutation was executed.

## Mandatory References Read

- `docs/phase_reports/phase32_dg_tick_normalized_momentum_trend_production_promotion.md`
- `docs/phase_reports/phase32_di_dg_tick_evidence_bq_consumer_compatibility_production_repair.md`
- Prior 2023-10-11 SELL/Corporate Action reports:
  - `docs/phase_reports/phase32_z_20231011_submit_halt_root_cause_audit.md`
  - `docs/phase_reports/phase32_aa_corporate_action_planning_pending_submit_authority_alignment_repair.md`
  - `docs/phase_reports/phase32_aw_2023_10_11_fresh_run_recurrent_sell_planning_halt_root_cause_audit.md`
  - `docs/phase_reports/phase32_ax_mixed_sell_review_fresh_run_contract_repair.md`
  - `docs/phase_reports/phase32_ba_post_partial_execution_current_valuation_authority_repair.md`
  - `docs/phase_reports/phase32_bb_2023_10_12_data_readiness_halt_read_only_audit.md`
  - `docs/phase_reports/phase32_bc_mixed_review_pending_day_rollover_lifecycle_repair.md`
- Current source areas:
  - `src/ai_fund_lab_v2/runtime_v2/planning_submit_feasibility.py`
  - `src/ai_fund_lab_v2/runtime_v2/pending/promotion.py`
  - `src/ai_fund_lab_v2/runtime_v2/pending/review_scope_authority.py`
  - `src/ai_fund_lab_v2/runtime_v2/historical_support/safety_temporal_authority.py`
  - `src/ai_fund_lab_v2/runtime_v2/executable_membership_guard.py`
  - `src/ai_fund_lab_v2/runtime_v2/historical_support/corporate_action_quarantine.py`

## Source / Authority Identity

- Current git commit: `a56f2bc26105eb14fd67322b7cd53c0d6ef1b1bd`
- Target run source baseline:
  - `source_commit = a56f2bc26105eb14fd67322b7cd53c0d6ef1b1bd`
  - `source_dirty = true`
  - `accepted_artifact_hash = 5451016e490214f81440f0d4fd154dc89cd76a86f84dd7daed5e8fb383e144a5`
  - `registry_hash = 4c07b5647425b32653e3e0a0e1a1164130133cc0db2c22881dcef5b7c97a35ba`
- Historical evaluation authority:
  - `status = PASS`
  - `generation_id = phase19_aq_accepted_generation_641e6e313543f013`
  - `run_authority_hash = sha256:208e129451ac0a1336fed4a636e67d2a18534d6dd1cf2acab18fe901a22efe0b`
- PM artifact binding for 2023-10-11:
  - accepted generation model/scaler binding: `PASS`
  - source authority: `VALID`
  - PM validation: `PASS`

There is no evidence that a runtime accepted-generation/hash mismatch is the first failure.

## First Failing Boundary

The first failed producer is not PM, Runtime Planning, or Pending publication during `morning`.

The `2023-10-11:data_readiness` job completed with:

- `exit_code = 0`
- `effective_component_statuses.safety = READY`
- `pending_active = false`
- `pending_slot_status = EMPTY`
- `safety_status = PASS`
- `safety_reason = historical_neutral_no_event_safety_ready`

The `2023-10-11:morning` job then wrote Pending:

- `pending_path = .runtime/pending_order_plan/pending_order_plan.json`
- `pending_plan_id = pending-strategy-plan-historical-2023-10-11-8c70c193d8520032`
- `pending_item_count = 2`
- `pending_commit_status = COMMITTED_CURRENT`

The first failing boundary is the next `2023-10-11:sell_planning` entry/readiness gate, which re-evaluates active same-day Pending as safety authority for sell planning.

Evidence:

- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260902T060955933565Z/daily/2023-10-11/sell_planning/runtime_manifest.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260902T060955933565Z/daily/2023-10-11/sell_planning/data_readiness_authority.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260902T060955933565Z/daily/2023-10-11/sell_planning/pending_continuity_evidence.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260902T060955933565Z/daily/2023-10-11/sell_planning/position_management_evidence.json`

`pending_continuity_evidence.json` and `position_management_evidence.json` both show `status = NOT_EXECUTED` with reason `historical_safety_temporal_authority_missing`, so the sell-planning body did not reach its PM/sell-continuity work.

## Exact HALT Component / Error

- `HALT_EXACT_COMPONENT`: Historical safety temporal authority / Data Readiness guard for `sell_planning`
- `HALT_EXACT_ERROR`: same-day active Pending is `REVIEW_REQUIRED` with no sell-continuation authority; therefore Historical daily neutral safety authority cannot be resolved for sell planning.
- `HALT_EXACT_REASON_CODES`:
  - `historical_safety_temporal_authority_missing`
  - `pending_review_required`
  - guard taxonomy codes: `TEMPORAL_MISMATCH`, `PENDING_BATCH_REVIEW_REQUIRED`
- `HALT_EXACT_EVIDENCE_PATH`:
  - `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260902T060955933565Z/daily/2023-10-11/sell_planning/runtime_manifest.json`
  - `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260902T060955933565Z/daily/2023-10-11/sell_planning/data_readiness_authority.json`

The run-level halt summary agrees:

- `next_job = 2023-10-11:sell_planning`
- `root_reason = historical_safety_temporal_authority_missing`
- `recommended_action = Refresh or inspect evidence: historical_safety_temporal_authority_missing, pending_review_required`

## Pending Shape

Current active Pending:

- path: `.runtime/pending_order_plan/pending_order_plan.json`
- state: `REVIEW_REQUIRED`
- `plan_overall_status = REVIEW_REQUIRED`
- `review_scope = AUTHORITY_UNKNOWN_REVIEW`
- `review_scope_source = phase24_ht_planning_submit_feasibility_v1`
- `review_scope_reason = corporate_action_event_not_resolved;corporate_action_event_not_resolved`
- `sell_continuation_allowed = false`
- `approved_item_ids = []`
- `approved_sell_item_ids = []`
- `approved_buy_item_ids = []`
- `review_required_sell_item_ids = [strategy-b5086c01c378aa03084d]`
- `review_required_buy_item_ids = [strategy-8f204937cd52348d3712]`

Items:

| Symbol | Side | Pending item | Source decision | PM decision | Quantity | State | Reason |
|---|---|---|---|---|---:|---|---|
| `76920` | BUY | `strategy-8f204937cd52348d3712` | `rp-2023-10-11-76920-buy_new-43f426e3f06332a5` | empty | `400` | `REVIEW_REQUIRED` | `corporate_action_event_not_resolved` |
| `50280` | SELL | `strategy-b5086c01c378aa03084d` | `rp-2023-10-11-50280-sell_exit-ef85562eee72162f` | `pm-2023-10-11-50280-reduce` | `100` | `REVIEW_REQUIRED` | `corporate_action_event_not_resolved` |

There is no PASS/approved SELL item in this Pending. This differs from earlier 2023-10-11 cases where `92460` was an independent feasible SELL.

## Affected Symbols

### 50280

- Current position quantity: `100`
- Current market value as of 2023-10-10: `46370`
- Position campaign id from `positions/position_campaigns.json`: `pc-d468aca3b9d6da8f-50280-0001`
- PM action: `EXIT`
- PM decision artifact: `pm-2023-10-11-50280-reduce`
- PM reason codes:
  - `pm_discrete_control_persistent_deterioration_exit`
  - `risk_increased_but_trend_not_broken`
  - `strategy_intelligence_sell_side_evidence_connected`
- Runtime Planning intent: `SELL_EXIT`
- Runtime Planning source decision: `rp-2023-10-11-50280-sell_exit-ef85562eee72162f`
- Proposed/Pending quantity: `100`
- Broker/current available quantity in feasibility evidence: `100`
- Corporate Action authority:
  - path: `.runtime/runtime_state/corporate_action_adjustments/2023-10-11/50280.json`
  - `status = REVIEW_REQUIRED`
  - `event_status = IMPACT_DETECTED`
  - `event_type = UNKNOWN_ADJFACTOR_IMPACT`
  - `adjustment_factor = 0.3333333333333333`
  - `pit_validation_status = PASS`
  - `quantity_reconciliation_status = REVIEW_REQUIRED`
  - `price_reconciliation_status = REVIEW_REQUIRED`
  - reason codes include `corporate_action_type_unresolved`, `corporate_action_ledger_adjustment_missing`, `corporate_action_current_adjustment_missing`, `corporate_action_pending_quantity_stale`, `corporate_action_already_applied_not_confirmed`, `corporate_action_adjusted_quantity_missing`

50280 is the concrete sell item that prevents sell-continuation authority.

Integrity notes:

- PM and position campaign evidence preserve `pc-d468aca3b9d6da8f-50280-0001`.
- The Pending item has `source_decision_id`, `source_decision_type`, `source_pm_decision_id`, and `order_plan_item_id`.
- The Pending item does not preserve `position_campaign_id` / `campaign_id`; both are empty. This is a campaign-provenance defect to retain as a secondary issue, but it is not the first HALT boundary because the halt occurs from unresolved Corporate Action safety authority before sell execution or submit.

### 76920

- Side: BUY
- Source decision: `rp-2023-10-11-76920-buy_new-43f426e3f06332a5`
- Quantity: `400`
- Pending state: `REVIEW_REQUIRED`
- Reason: `corporate_action_event_not_resolved`
- Source: `.runtime/runtime_state/corporate_action_quarantine/historical_symbol_registry.json`
- Registry entry:
  - `first_detected_date = 2022-10-28`
  - `latest_checked_date = 2022-10-19`
  - `resolution_status = UNRESOLVED`
  - `corporate_action_quarantine_status = QUARANTINED`
  - `production_applicability = NEVER`
  - `corporate_action_run_continuation_eligibility = ALLOWED_FOR_HISTORICAL_REPLAY_ONLY`

The same-day `strategy/corporate_event.json` has `KNOWN_NO_EVENT` for `76920` on `2023-10-11`; the block comes from the Historical unresolved symbol quarantine registry, not a same-day corporate event artifact.

76920 is not a SELL blocker. It contributes to Pending being review-required, but it does not create the sell-planning failure by itself.

## Contract Trace

`evaluate_precomputable_executable_membership_guard()` checks the Historical corporate-action quarantine registry before known per-item adjustment authority when runtime mode is `historical`. If an unresolved entry exists for the symbol, it returns item-scoped `REVIEW_REQUIRED` with `consumer_action = FAIL_CLOSED_REVIEW_ITEM_ALLOW_UNAFFECTED_ITEMS`.

`_derive_review_scope()` in `pending/promotion.py` classifies:

- `BUY_ITEM_SCOPED_REVIEW` when blocked items are BUY only.
- `MIXED_SELL_ITEM_SCOPED_REVIEW` when there is at least one blocked SELL and at least one PASS SELL.
- `AUTHORITY_UNKNOWN_REVIEW` otherwise.

For this Pending:

- blocked BUY ids: `[76920 item]`
- blocked SELL ids: `[50280 item]`
- PASS SELL ids: `[]`

Therefore `mixed_sell_item_scoped = false`, `buy_item_scoped = false`, and `review_scope = AUTHORITY_UNKNOWN_REVIEW`. With no approved/PASS sell item, this is consistent with the current scope contract.

`sell_planning` then re-enters readiness with active same-day review Pending. Because `sell_continuation_allowed = false`, Historical neutral sell safety cannot be resolved and the gate returns `historical_safety_temporal_authority_missing`.

## Comparison With Prior 2023-10-11 Repairs

This is not the same operational shape as the prior Phase32-AW/AX mixed SELL repair:

- Prior shape: reviewed CA SELL `50280` + unaffected feasible SELL `92460` + reviewed BUY items.
- Current shape: reviewed CA SELL `50280` + reviewed BUY `76920`; no `92460`; no PASS SELL.

Phase32-AX's `MIXED_SELL_ITEM_SCOPED_REVIEW` contract requires an independent PASS SELL to continue. That condition is absent. Therefore the previous mixed SELL repair is not shown to have regressed; it is simply not applicable to this Pending.

Phase32-AA behavior is preserved for 50280: the unresolved Corporate Action SELL is not approved/submittable and is blocked before Submit.

Phase32-BA/BC residual-current-valuation/day-rollover contracts are not reached, because this run halts before Submit/Execution and before current valuation.

## DG/DI Causality

DG/DI introduced tick-normalized trend/momentum evidence and repaired BQ consumer compatibility. The failing sell-planning guard path does not consume tick-normalized evidence directly:

- Halt producer: Historical safety temporal authority / Pending review scope.
- Direct item reason: Corporate Action authority.
- Direct SELL item: 50280, unresolved same-day AdjFactor authority.
- No evidence path shows tick evidence as the cause of `historical_safety_temporal_authority_missing`.

However, DG/DI-era Strategy changes can change the portfolio path. In this run, the 2023-10-11 Pending does not include the previously observed independent PASS SELL `92460`; therefore the run encounters a different 2023-10-11 Pending composition. This is best classified as:

`INDIRECT_PORTFOLIO_PATH_ONLY`

It is not a DG/DI direct code-path defect based on current evidence.

## Quantity / Position Authority

50280 quantity authority is consistent:

- held quantity: `100`
- PM sell/exit intent: full exit from current position
- Pending quantity: `100`
- broker/current available quantity in feasibility evidence: `100`
- submit quantity in corporate-action authority: `100`

No oversell, stale position quantity, duplicate reservation, already-exited campaign, partial reduce mismatch, or zero-quantity intent is the first failure.

The first quantity-related review detail is Corporate Action reconciliation, not ordinary position quantity mismatch:

- `quantity_reconciliation_status = REVIEW_REQUIRED`
- `corporate_action_pending_quantity_stale`
- `corporate_action_adjusted_quantity_missing`

## SELL Reason Consumer Compatibility

PM emitted a richer EXIT reason set and Runtime Planning consumed it as `SELL_EXIT`.

Observed:

- PM: `action = EXIT`
- PM decision id: `pm-2023-10-11-50280-reduce`
- PM reason codes include `pm_discrete_control_persistent_deterioration_exit` and `risk_increased_but_trend_not_broken`
- Runtime Planning: `planning_intent = SELL_EXIT`
- Runtime Planning reason codes include `full_liquidation_authority:PM_EXIT`, `position_sizing_negative_quantity_delta_maps_to_sell_exit`, `position_sizing_quantity_candidate_resolved`

No evidence shows generic/bare action labels replacing the richer PM reason as the first failure.

## Side Effects

No 2023-10-11 `submit` or `execution` directory exists under the target run daily evidence. No submit, broker order, execution, fill, cash mutation, or position mutation evidence was found for 2023-10-11 after the halt boundary.

The safe continuation point, if an operator chooses to continue after manual review or a later accepted repair, remains:

`2023-10-11:sell_planning`

## Classification

- `HALT_ROOT_CAUSE_CLASS`: `corporate-action authority`
- Secondary class: `Pending review-scope / Historical safety temporal authority expected fail-closed`
- Not root cause:
  - PM / SELL intent mismatch
  - SELL reason/provenance defect
  - quantity/position mismatch
  - stale position authority
  - valuation/ledger inconsistency
  - runtime accepted-generation/hash mismatch
  - tick/DG/DI direct interaction
  - execution/lot materialization issue

## Repair Necessity

`PRODUCTION_REPAIR_REQUIRED = NO` for the observed HALT.

Reason:

50280 has a same-day PIT Corporate Action adjustment ambiguity with `AdjFactor = 0.3333333333333333`, unresolved event type, unresolved quantity/price reconciliation, and unknown already-applied state. With no independent PASS SELL remaining, Runtime cannot safely proceed through sell planning. The fail-closed behavior is correct under the current contract.

No SELL threshold, REDUCE/EXIT philosophy, Winner Retention, REENTRY, ADD/G129, Candidate/BQ/Entry, or tick-normalized evidence repair is justified by this HALT.

Secondary observations that may deserve a future narrow audit, but are not the root cause of this halt:

1. 50280 Pending item loses `position_campaign_id`/`campaign_id` even though PM and position-campaign evidence have `pc-d468aca3b9d6da8f-50280-0001`.
2. 76920 is blocked by a Historical symbol quarantine registry entry whose source evidence is older (`requested_business_date = 2022-10-19`) while same-day corporate_event evidence says `KNOWN_NO_EVENT`; this is not the sell blocker, but it is a run-scoped quarantine lifecycle question.

## Final Answers

1. `TARGET_RUN`: `runtime-test-historical-extended-smoke-20260902T060955933565Z`
2. `LATEST_COMPLETED_DATE`: `2023-10-10`
3. `HALT_EXACT_COMPONENT`: Historical safety temporal authority / Data Readiness guard for `2023-10-11:sell_planning`
4. `HALT_EXACT_ERROR`: active same-day Pending is `REVIEW_REQUIRED` with `review_scope=AUTHORITY_UNKNOWN_REVIEW` and `sell_continuation_allowed=false`; same-day Historical neutral sell safety cannot be resolved.
5. `HALT_EXACT_REASON_CODES`: `historical_safety_temporal_authority_missing`, `pending_review_required`, `TEMPORAL_MISMATCH`, `PENDING_BATCH_REVIEW_REQUIRED`
6. `HALT_EXACT_EVIDENCE_PATH`: `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260902T060955933565Z/daily/2023-10-11/sell_planning/runtime_manifest.json`
7. `HALT_ROOT_CAUSE_CLASS`: `corporate-action authority`
8. `AFFECTED_SYMBOLS`: `50280` as SELL blocker; `76920` as BUY review contributor
9. `DG_DI_CAUSAL_RELATION`: `INDIRECT_PORTFOLIO_PATH_ONLY`
10. `PM_ACCEPTED_AUTHORITY_STATUS`: `PASS`
11. `SELL_PROVENANCE_INTEGRITY`: `PARTIAL`; decision ids are present, but Pending loses 50280 campaign id.
12. `SELL_QUANTITY_AUTHORITY_STATUS`: `PASS_FOR_POSITION_QUANTITY`; Corporate Action adjusted quantity reconciliation remains `REVIEW_REQUIRED`.
13. `SELL_REASON_CONSUMER_COMPATIBILITY`: `PASS`
14. `CORPORATE_ACTION_AUTHORITY_CAUSAL`: `YES`
15. `TICK_QUANTIZATION_CAUSAL`: `NO`
16. `HALT_FAIL_CLOSED_BEHAVIOR_CORRECT`: `YES`
17. `PRODUCTION_REPAIR_REQUIRED`: `NO` for this HALT
18. `REPAIR_SCOPE`: `NONE`; optional future audits only for 50280 campaign-id materialization and 76920 historical quarantine lifecycle.
19. `PERFORMANCE_TUNING_EXECUTED`: `NO`
20. `PRODUCTION_CHANGE_EXECUTED`: `NO`
21. `TARGET_RUN_MUTATED`: `NO`
22. `TARGET_RUN_RESUME_SAFETY`: `SAFE_AFTER_OPERATOR_REVIEW_OR_CANONICAL_CA_RESOLUTION`; no code repair is required by the observed halt, and no 2023-10-11 side effects exist.
23. `PRE_HALT_EVIDENCE_VALIDITY`: `VALID`; no evidence contaminates completed days through `2023-10-10`.
24. `NEXT_RECOMMENDED_STEP`: Operator should inspect/resolve the 2023-10-11 50280 Corporate Action review using the canonical human-review or CA-resolution path, then continue from `2023-10-11:sell_planning` if that path marks the Pending/safety authority valid. Do not change Strategy semantics.
25. `FINAL_JUDGMENT`: `PHASE32_DJ_20231011_SELL_PLANNING_HALT_EXPECTED_FAIL_CLOSED_CORPORATE_ACTION_AUTHORITY_IDENTIFIED`

