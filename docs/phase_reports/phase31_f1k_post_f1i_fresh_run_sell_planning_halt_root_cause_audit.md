# Phase31-F1K — Post-F1I Fresh-Run SELL Planning HALT Root-Cause Audit

## PRIMARY_JUDGMENT

PHASE31_F1K_PENDING_SELL_CONFLICT_NEWLY_EXPOSED_BY_F1F_F1I

The 2022-09-07 HALT was not caused by stale REDUCE quantity after PM EXIT. The F1F/F1I lineage worked through PM, PS, and Runtime Planning: 93600 was escalated from REDUCE to PM EXIT, PS recomputed full liquidation quantity, and Runtime Planning produced SELL_EXIT quantity 100.

The HALT was caused downstream in SELL Planning because a same-day active pending SELL for 93600 already existed from the Morning strategy planning path. The later sell_planning job preserved the original pending plan and returned REVIEW_REQUIRED with `ACTIVE_PENDING_NOT_EMPTY:active_buy_missing;PENDING_PLAN_CONFLICT_ORIGINAL_PRESERVED`; runtime_test stopped on review-required, mapping Runtime CLI exit 20 to top-level exit 30.

## Required Output

TARGET_RUN_ID = runtime-test-historical-extended-smoke-20260821T014643273280Z

HALT_STAGE = 2022-09-07:sell_planning

HALT_SYMBOLS = 93600

HALT_REASON = active same-day SELL pending already existed for 93600; sell_planning preserved original pending and returned REVIEW_REQUIRED.

HALT_CONTRACT = SELL Planning active pending preservation / conflict guard: do not overwrite active pending; return REVIEW_REQUIRED with original pending preserved.

ESCALATION_REASON_OCCURRENCE_COUNT = 13

ESCALATED_SYMBOL_DATE_LIST = 2022-08-16:94340, 2022-08-17:54010, 2022-08-17:83060, 2022-08-17:47840, 2022-08-22:40800, 2022-08-22:15180, 2022-08-23:60540, 2022-08-24:70140, 2022-08-26:43760, 2022-09-01:89440, 2022-09-01:39890, 2022-09-02:72980, 2022-09-07:93600

F1F_F1I_ACTIVATION_CONFIRMED = YES

PM_PS_ACTION_MISMATCH_COUNT = 0

PS_RUNTIME_ACTION_MISMATCH_COUNT = 0

ESCALATED_EXIT_FULL_QUANTITY_MATERIALIZED = YES

PENDING_CONFLICT_CONFIRMED = YES

POSITION_CAMPAIGN_CONSISTENCY = PARTIAL

F1I_HISTORY_BRIDGE_SIDE_EFFECT = NO

SELL_PLANNING_FAILURE_BRANCH = `runtime_v2.planning.sell_pipeline` active pending preservation branch returning REVIEW_REQUIRED with `PRESERVE_ACTIVE_PENDING_ON_NO_SIGNAL`

ROOT_CAUSE_CLASSIFICATION = PENDING_SELL_CONFLICT

INTEGRATION_DEFECT_CONFIRMED = YES

REPAIR_CANDIDATE = YES

REPAIR_SCOPE = focused SELL Planning same-day SELL pending idempotency / reconciliation for already-materialized equivalent SELL_EXIT pending, or runtime_test stage sequencing so a Morning-created SELL pending is not reprocessed as a conflicting active pending by a later sell_planning job.

FUTURE_INFORMATION_USED_FOR_ROOT_CAUSE = NO

IMPLEMENTATION_CHANGED = NO

FRESH_RUN_EXECUTED_BY_CODEX = NO

RESUME_EXECUTED_BY_CODEX = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

RESUME_AFTER_REPAIR_POSSIBLE = CONDITIONAL

FRESH_RUN_REQUIRED_AFTER_REPAIR = CONDITIONAL

NEXT_TASK_RECOMMENDATION = Phase31-F1L focused SELL Planning integration repair.

## F1K-1 Exact HALT Evidence

Evidence root:

`reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260821T014643273280Z`

HALT artifacts:

- `daily/2022-09-07/sell_planning/cli_result.json`
- `daily/2022-09-07/sell_planning/subprocess_trace.json`
- `daily/2022-09-07/sell_planning/runtime_log.log`
- `daily/2022-09-07/sell_planning/sell_planning_manifest.json`
- `daily/2022-09-07/sell_planning/pending_continuity_evidence.json`

Exact evidence:

- Runtime CLI exit code = 20
- subprocess returncode = 20
- runtime_test stopped at `2022-09-07:sell_planning`
- top-level runtime_test exit code = 30
- `pending_continuity_evidence.status = REVIEW_REQUIRED`
- `pending_continuity_evidence.reason = ACTIVE_PENDING_NOT_EMPTY:active_buy_missing;PENDING_PLAN_CONFLICT_ORIGINAL_PRESERVED`
- manifest warning = `sell planning pipeline review required: ACTIVE_PENDING_NOT_EMPTY:active_buy_missing;PENDING_PLAN_CONFLICT_ORIGINAL_PRESERVED`

The direct symbol is 93600. The pre-sell pending snapshot contained one active approved SELL item:

- pending_plan_id = `pending-strategy-plan-historical-2022-09-07-7212438d623c7951`
- pending_item_id = `strategy-c8537cd09201c855e2b4`
- symbol = 93600
- side = SELL
- quantity = 100
- state = CREATED
- target_session_date = 2022-09-07

## F1K-2 2022-09-07 PM SELL Inventory

DIRECT_EXIT:

- None.

F1F_ESCALATED_EXIT:

- 93600
- campaign_id = `pc-748fe6b67b37c9a8-93600-0001`
- baseline PM action = REDUCE
- canonical_sell_state = PERSISTENT_DETERIORATION
- escalation_considered = true
- escalation_decision = PM_EXIT
- escalation_reason = `pm_discrete_control_persistent_deterioration_exit`
- final_pm_action = EXIT
- PM reason codes = `pm_discrete_control_persistent_deterioration_exit`, `risk_increased_but_trend_not_broken`, `strategy_intelligence_sell_side_evidence_connected`
- recovery_state = NO_RECOVERY
- PIT proof = PASS, feature dates 2022-09-06 and 2022-09-07, future dates empty
- prior_unrepresentable_reduce_count = 1
- prior_unrepresentable_reduce_dates = 2022-09-06

REDUCE:

- 32710
- canonical_sell_state = WEAKENING_BUT_INTACT
- final_pm_action = REDUCE
- PS reduce semantic = REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT
- Runtime Planning = NO_ORDER

- 68360
- canonical_sell_state = WEAKENING_BUT_INTACT
- final_pm_action = REDUCE
- PS reduce semantic = REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT
- Runtime Planning = NO_ORDER

UNRESOLVED:

- None in the 2022-09-07 PM SELL set.

## F1K-3 F1F Escalation Occurrences Before HALT

ESCALATION_REASON_OCCURRENCE_COUNT = 13

Occurrences:

| Date | Symbol | PM final | PS action/quantity | Runtime action/quantity | Fill/no-fill |
| --- | --- | --- | --- | --- | --- |
| 2022-08-16 | 94340 | EXIT | EXIT / 300 | SELL_EXIT / 300 | filled |
| 2022-08-17 | 54010 | EXIT | EXIT / 100 | SELL_EXIT / 100 | filled |
| 2022-08-17 | 83060 | EXIT | EXIT / 100 | SELL_EXIT / 100 | filled |
| 2022-08-17 | 47840 | EXIT | EXIT / 100 | SELL_EXIT / 100 | filled |
| 2022-08-22 | 40800 | EXIT | EXIT / 100 | SELL_EXIT / 100 | filled |
| 2022-08-22 | 15180 | EXIT | EXIT / 100 | SELL_EXIT / 100 | filled |
| 2022-08-23 | 60540 | EXIT | EXIT / 100 | SELL_EXIT / 100 | filled |
| 2022-08-24 | 70140 | EXIT | EXIT / 100 | SELL_EXIT / 100 | filled |
| 2022-08-26 | 43760 | EXIT | EXIT / 100 | SELL_EXIT / 100 | filled |
| 2022-09-01 | 89440 | EXIT | EXIT / 100 | SELL_EXIT / 100 | filled |
| 2022-09-01 | 39890 | EXIT | EXIT / 100 | SELL_EXIT / 100 | filled |
| 2022-09-02 | 72980 | EXIT | EXIT / 100 | SELL_EXIT / 100 | filled |
| 2022-09-07 | 93600 | EXIT | EXIT / 100 | SELL_EXIT / 100 | not reached; halted in sell_planning |

F1F/F1I is genuinely active in this fresh run.

## F1K-4 PM -> PS Contract

PM_PS_ACTION_MISMATCH_COUNT = 0

93600:

- PM final action = EXIT
- PS pm_action = EXIT
- PS current_quantity = 100
- PS final_target_quantity = 0
- PS final_quantity_delta = -100
- PS quantity_delta_candidate = -100
- PS reduce_execution_semantic = empty / not applicable
- PS reduce_executability_status = NOT_APPLICABLE

No REDUCE-derived zero/stale quantity survived after PM EXIT. The REDUCE raw quantity from the canonical escalation evidence was diagnostic context only, not the executable PS quantity.

32710 and 68360:

- PM final action = REDUCE
- PS reduce_execution_semantic = REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT
- PS reduce_final_sell_quantity = 0
- PS reduce_executability_status = INTENTIONAL_NO_ORDER

These are REDUCE-compatible intentional no-order rows and do not conflict with PM action.

## F1K-5 PS -> Runtime Planning Contract

PS_RUNTIME_ACTION_MISMATCH_COUNT = 0

93600:

- PS EXIT, quantity delta -100
- Runtime Planning planning_intent = SELL_EXIT
- order_side_intent = SELL
- planned_quantity = 100
- full_liquidation_authority_present = true
- full_liquidation_authority_source = PM_EXIT
- quantity_status = RESOLVED_EXECUTABLE

32710 and 68360:

- PS REDUCE intentional no-order
- Runtime Planning planning_intent = NO_ORDER
- order_side_intent = NONE
- planned_quantity = 0
- reduce_execution_semantic = REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT

## F1K-6 Runtime -> SELL Planning Contract

SELL_PLANNING_INPUT_CONTRACT:

- Runtime action for 93600 = SELL_EXIT
- requested/planned sell quantity = 100
- current holding quantity = 100
- pending sell quantity already active = 100
- existing pending symbol = 93600
- existing pending side = SELL
- existing pending state = CREATED / APPROVED at plan level
- existing pending target session = 2022-09-07
- campaign id in PM/SI/canonical SELL evidence = `pc-748fe6b67b37c9a8-93600-0001`

SELL_PLANNING_FAILURE_BRANCH:

`src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py` active-pending branch:

- detects active pending
- writes `pending_continuity_evidence.json`
- sets `classification = REVIEW_REQUIRED`
- sets `resolution_action = ORIGINAL_PENDING_PRESERVED`
- sets reason codes `ACTIVE_PENDING_NOT_EMPTY:<reason>` and `PENDING_PLAN_CONFLICT_ORIGINAL_PRESERVED`
- returns `SellPlanningPipelineResult(status="REVIEW_REQUIRED", pending_composition_model="PRESERVE_ACTIVE_PENDING_ON_NO_SIGNAL")`

With `--stop-on-review-required`, Runtime exits 20.

## F1K-7 EXIT Escalation Quantity Semantics

ESCALATED_EXIT_FULL_QUANTITY_MATERIALIZED = YES

The priority defect hypothesis is rejected for 93600:

- baseline PM action was REDUCE
- F1F canonical SELL semantic escalated to EXIT
- PS did not carry stale REDUCE quantity
- PS materialized full liquidation target quantity 0 from current quantity 100
- Runtime Planning emitted SELL_EXIT quantity 100

No producer/consumer ordering gap was found between PM action mutation and PS quantity materialization.

## F1K-8 Pending / Duplicate SELL Conflict

PENDING_CONFLICT_CONFIRMED = YES

The active pending conflict is same-day and same-symbol:

- Morning planning on 2022-09-07 generated pending plan `pending-strategy-plan-historical-2022-09-07-7212438d623c7951`
- Morning selected_symbols = 93600
- Morning pending item count = 1
- The pending item was SELL 93600 quantity 100 from planning id `rp-2022-09-07-93600-sell_exit-816e30699b8499ff`
- The later sell_planning job read that same active pending plan and preserved it rather than overwriting or accepting it idempotently

This is not a REDUCE pending surviving after PM became EXIT. It is an already-materialized SELL_EXIT pending being treated as an active pending conflict by a later SELL Planning pass.

## F1K-9 Position / Campaign Consistency

POSITION_CAMPAIGN_CONSISTENCY = PARTIAL

The execution-relevant quantity path is consistent:

- current position exists for 93600
- PM adapter quantity = 100
- SI quantity = 100
- PS current_quantity = 100
- Runtime planned SELL_EXIT quantity = 100
- pending SELL quantity = 100

The PM/SI/canonical SELL campaign id is internally consistent:

- `pc-748fe6b67b37c9a8-93600-0001`

However, the copied 2022-09-07 run-scoped observability file `daily/2022-09-07/positions/position_campaigns.json` lists 93600 as:

- `pc-31068916e7a9fdd8-93600-0001`

The prior 2022-09-06 `position_campaigns.json` and 2022-09-07 SI/PM lineage use `pc-748fe6b67b37c9a8-93600-0001`. This artifact-level campaign id discrepancy did not produce the HALT branch, but it is a separate observability consistency concern to keep visible.

## F1K-10 F1I History Bridge Side-Effect Check

F1I_HISTORY_BRIDGE_SIDE_EFFECT = NO

For 93600:

- `pm_decision_history_summary.decision_evidence_not_execution = true`
- `fake_execution_event_created = false`
- `future_information_used = false`
- `prior_unrepresentable_reduce_summary.same_day_self_count_protected = true`
- prior reduce date = 2022-09-06
- current business date = 2022-09-07

No evidence was found that F1I:

- mutated economic campaign events
- changed current quantity
- created fake pending
- created fake SELL
- altered campaign OPEN/CLOSED status
- altered execution authority

F1I did expose the 9/6 prior same-campaign unrepresentable REDUCE evidence, which correctly activated F1F on 9/7.

## F1K-11 Compare With Pre-F1I Broken Run

Structural comparison run:

`runtime-test-historical-extended-smoke-20260821T002814288741Z`

On 2022-09-07 in the pre-F1I broken-history run, 93600 was:

- PM action = REDUCE
- canonical_sell_state = WEAKENING_BUT_INTACT
- prior_unrepresentable_reduce_count = 0
- PS reduce_execution_semantic = REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT
- Runtime Planning = NO_ORDER
- sell_planning pending continuity status = PASS / `sell_planning_stage_not_reached`

HALT_NEWLY_EXPOSED_BY_F1F_F1I = YES

The conflict branch is newly exposed because F1I supplied the prior campaign evidence, F1F escalated 93600 to PM EXIT, Morning materialized a same-day SELL_EXIT pending, and the subsequent sell_planning job treated that active pending as a conflict.

## F1K-12 Root Cause Classification

ROOT_CAUSE_CLASSIFICATION = PENDING_SELL_CONFLICT

Rejected classifications:

- F1F_ESCALATED_EXIT_QUANTITY_RECOMPUTE_GAP: rejected; full quantity 100 materialized.
- PM_PS_ACTION_SEMANTIC_MISMATCH: rejected; PM EXIT mapped to PS EXIT.
- PS_RUNTIME_ACTION_MISMATCH: rejected; PS EXIT mapped to Runtime SELL_EXIT.
- POSITION_CAMPAIGN_MISMATCH: not direct HALT cause; quantity path passes, but observability is PARTIAL.
- F1I_HISTORY_BRIDGE_SIDE_EFFECT: rejected; no fake execution/pending/current mutation found.
- PREEXISTING_SELL_PLANNING_DEFECT: partial context only. The guard existed before, but this exact failing branch was exposed by F1F/F1I creating a real same-day SELL_EXIT pending.

## F1K-13 Repair Gate

REPAIR_CANDIDATE = YES

Narrow repair family:

Phase31-F1L focused SELL Planning integration repair.

Repair should address the same-day active SELL pending idempotency/reconciliation contract. The narrow target is a case where Morning already materialized an equivalent SELL_EXIT pending for the same symbol, same session, and same quantity, and a later sell_planning pass should not convert that equivalent state into a HALT unless there is a genuine conflict.

RESUME_AFTER_REPAIR_POSSIBLE = CONDITIONAL

Resume may be possible only if the repair is idempotent and preserves the already-written 2022-09-07 SELL_EXIT pending evidence without needing to regenerate prior strategy artifacts. The pending plan itself is not corrupt: it is a valid 93600 SELL 100 plan.

FRESH_RUN_REQUIRED_AFTER_REPAIR = CONDITIONAL

A fresh run is required if the repair changes upstream planning generation, campaign materialization, or pending artifact semantics. If the repair is limited to same-day equivalent pending acceptance in sell_planning and the existing pending artifact is accepted as valid, a focused resume/retry from 2022-09-07 sell_planning may be sufficient after repair.

## Final Questions

1. 2022-09-07のsell_planningは何で止まったか？ Same-day active pending SELL 93600 existed; sell_planning preserved it and returned REVIEW_REQUIRED.
2. どのsymbolが直接原因か？ 93600.
3. F1F/F1I escalationはfresh runで実際に発火していたか？ YES, 13 occurrences through 2022-09-07.
4. PM EXITへ昇格した後、PS quantityはfull EXIT用に正しく再計算されたか？ YES, 93600 became PS EXIT current 100 -> target 0 -> delta -100.
5. REDUCE由来のzero/stale quantityが残っていないか？ No stale REDUCE quantity survived on 93600.
6. RuntimeはPM EXITをSELL_EXITへ正しく変換したか？ YES, Runtime Planning produced SELL_EXIT quantity 100.
7. Pending conflictはあるか？ YES, active same-day SELL 93600 quantity 100.
8. campaign/position quantityは整合しているか？ Quantity path PASS; campaign observability PARTIAL due copied 9/7 `position_campaigns.json` id discrepancy.
9. F1I history bridgeが副作用を作っていないか？ NO.
10. 修理後resumeできるか、それともfresh-run必須か？ CONDITIONAL; resume may be possible for a narrow idempotent sell_planning repair, fresh-run is needed if upstream artifact semantics change.
