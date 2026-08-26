# Phase31-F1S — 2022-08-23 Clean Fresh-Run SELL Planning HALT Root-Cause Audit

## PRIMARY_JUDGMENT

PHASE31_F1S_BUY_SELL_COMPOSITE_PENDING_CONTINUATION_GAP_CONFIRMED

## Required Output

TARGET_RUN_ID = runtime-test-historical-extended-smoke-20260821T041825673015Z

HALT_DATE = 2022-08-23

HALT_REASON = ACTIVE_PENDING_NOT_EMPTY:PASS;PENDING_PLAN_CONFLICT_ORIGINAL_PRESERVED

HALT_SYMBOLS = 60540

SELL_PLANNING_FAILURE_BRANCH = active pending preservation / pending conflict on same-day approved BUY+SELL pending

ACTIVE_PENDING_ITEM_COUNT = 6

PENDING_BUY_COUNT = 5

PENDING_SELL_COUNT = 1

F1_EQUIVALENCE_BRANCH_ENTERED = YES, by current accepted F1L/F1R contract evaluation; actual artifact only records the generic active-pending conflict branch

EQUIVALENCE_RESULT = NOT_EQUIVALENT

FIRST_FAILED_EQUIVALENCE_PREDICATE = EQUIVALENT_SELL_PENDING_BUY_ITEM_PRESENT

PENDING_SYMBOL_SET = 60540

AUTHORITATIVE_SELL_EXIT_SYMBOL_SET = 60540 from Strategy Runtime planning / pending embedded SELL_EXIT lineage; NOT_AVAILABLE from sell_planning PM artifact because sell_planning saw 60540 as REDUCE

SET_EQUALITY = FAIL for sell_planning PM authority; PASS only if using Strategy Runtime planning / pending embedded SELL_EXIT lineage

AUTHORITATIVE_SELL_SET_STATUS = PARTIAL

CURRENT_POSITION_SOURCE_STATUS = PASS

BUY_SELL_COMPOSITION_INVOLVED = YES

EXECUTION_ADVANCED_OR_STALE_STATE = NO

ROOT_CAUSE_CLASSIFICATION = NEW_COMPOSITION_FAMILY

SAME_AS_PRIOR_F1_PENDING_DEFECT = PARTIAL

ESCALATION_REASON_OCCURRENCE_COUNT = 7

F1F_F1I_ACTIVATION_CONFIRMED = YES

DUPLICATE_SIDE_EFFECT_COUNT = 0

HALTED_RUN_STATE_INTEGRITY = PASS

INTEGRATION_DEFECT_CONFIRMED = YES

REPAIR_CANDIDATE = YES

IMPLEMENTATION_CHANGED = NO

FRESH_RUN_EXECUTED_BY_CODEX = NO

RESUME_EXECUTED_BY_CODEX = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

RESUME_AFTER_REPAIR_POSSIBLE = CONDITIONAL

NEXT_TASK_RECOMMENDATION = Phase31-F1T focused repair. Do not resume before F1S root cause is resolved.

## Target Evidence

Evidence root:

reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260821T041825673015Z

HALT evidence:

- `fresh_run_summary.json`: status HALT, exit_code 30
- `daily/2022-08-23/sell_planning/cli_result.json`: exit_code 20
- `daily/2022-08-23/sell_planning/runtime_manifest.json`: final_state REVIEW_REQUIRED
- `daily/2022-08-23/sell_planning/pending_continuity_evidence.json`: status REVIEW_REQUIRED, reason `ACTIVE_PENDING_NOT_EMPTY:PASS;PENDING_PLAN_CONFLICT_ORIGINAL_PRESERVED`

No fresh-run, resume, replay, or long Historical was executed for this audit.

## Active Pending Shape

The active pending consumed by sell_planning is:

- pending_plan_id: pending-strategy-plan-historical-2022-08-23-9fa776fa8db6a019
- state: APPROVED
- plan_created_date: 2022-08-23
- target_session_date: 2022-08-23
- consumed: false
- total item count: 6
- BUY item count: 5
- SELL item count: 1
- approved SELL count: 1

Items:

| symbol | side | qty | state | approved | source_decision_type | planning_intent | source_planning_id |
|---|---:|---:|---|---|---|---|---|
| 94320 | BUY | 200 | CREATED | true | BUY_ADD | BUY_ADD | rp-2022-08-23-94320-buy_add-23c9864ca866775d |
| 38150 | BUY | 100 | CREATED | true | BUY_NEW | BUY_NEW | rp-2022-08-23-38150-buy_new-fc5482fc407daf9b |
| 72980 | BUY | 100 | CREATED | true | BUY_NEW | BUY_NEW | rp-2022-08-23-72980-buy_new-f22202d73ddf6703 |
| 44410 | BUY | 100 | CREATED | true | BUY_NEW | BUY_NEW | rp-2022-08-23-44410-buy_new-a585baccd1b2000b |
| 71730 | BUY | 100 | CREATED | true | BUY_NEW | BUY_NEW | rp-2022-08-23-71730-buy_new-4ca6a98a368f436e |
| 60540 | SELL | 100 | CREATED | true | SELL_EXIT | SELL_EXIT | rp-2022-08-23-60540-sell_exit-c5f5bce7bf475987 |

Partial/fill markers:

- batch_submit_status: empty for all items
- feasibility_status: empty for all items
- submitted_quantity: not present
- filled_quantity: not present
- consume.submitted_order_ids: empty
- consume.ledger_order_record_ids: empty

## SELL Inventory

2022-08-23 Strategy PM / canonical SELL state:

| symbol | campaign_id | baseline PM action | canonical SELL state | final PM action | F1F reason | prior unrepresentable reduce count | category |
|---|---|---|---|---|---|---:|---|
| 60540 | pc-76067b2554f5a8c2-60540-0001 | REDUCE inferred by prior bridge | PERSISTENT_DETERIORATION | EXIT | pm_discrete_control_persistent_deterioration_exit | 1 | F1F_ESCALATED_EXIT |
| 99840 | pc-e0dade51d35367f9-99840-0001 | REDUCE | WEAKENING_BUT_INTACT | REDUCE | none | 0 | REDUCE |
| 70140 | pc-4e8c6877b290e227-70140-0001 | REDUCE | WEAKENING_BUT_INTACT | REDUCE | none | 0 | REDUCE |
| 94320 | pc-e80a76c61e56bbed-94320-0001 | ADD | HEALTHY_OR_RECOVERING | ADD | none | 0 | NO_ORDER for SELL |
| 61750 | pc-2bcbf35559bcc6ff-61750-0001 | HOLD | HEALTHY_OR_RECOVERING | HOLD | none | 0 | NO_ORDER |
| 27880 | pc-a61c009f3661d9af-27880-0001 | HOLD | HEALTHY_OR_RECOVERING | HOLD | none | 0 | NO_ORDER |
| 27780 | pc-952c2d33c6b96507-27780-0001 | HOLD | HEALTHY_OR_RECOVERING | HOLD | none | 0 | NO_ORDER |
| 33190 | pc-f5888dd79e3768ff-33190-0001 | HOLD | HEALTHY_OR_RECOVERING | HOLD | none | 0 | NO_ORDER |

Strategy Runtime planning:

| symbol | runtime planning intent | runtime quantity | current holding quantity |
|---|---|---:|---:|
| 60540 | SELL_EXIT | 100 | 100 |
| 99840 | NO_ORDER from REDUCE below minimum | 0 | 100 |
| 70140 | NO_ORDER from REDUCE below minimum | 0 | 100 |

sell_planning PM artifact:

- pm_exit_count = 0
- pm_reduce_count = 3
- 60540 appears as `decision_type = REDUCE`, `pm_decision_id = pm-2022-08-23-60540-reduce`
- sell_planning order_plan non_executable_sell_decisions includes 60540/99840/70140 as REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT

This confirms a producer/consumer mismatch: Strategy Runtime planning has 60540 as SELL_EXIT, while sell_planning's direct PM input has 60540 as REDUCE/no executable order.

## F1L/F1R Equivalence Evaluation

The active pending is not eligible for F1L/F1R same-day SELL pending reuse because it is not a SELL-only pending plan.

Predicate result:

- same date/session: PASS
- plan state APPROVED: PASS
- unconsumed: PASS
- contains no BUY items: FAIL
- supported item state CREATED/READY/APPROVED: PASS
- no partial/fill evidence: PASS
- current position available for SELL symbol 60540: PASS
- pending SELL qty equals current full position qty: PASS
- SELL item EXIT lineage: PASS

First failed predicate:

EQUIVALENT_SELL_PENDING_BUY_ITEM_PRESENT

Set analysis:

- Pending SELL symbol set: {60540}
- Strategy Runtime authoritative SELL_EXIT set: {60540}
- sell_planning PM authoritative SELL_EXIT set: {}
- sell_planning PM REDUCE/no-order set: {60540, 99840, 70140}

Therefore the F1R strict set-equivalence contract is not sufficient by itself: the immediate blocker is BUY+SELL composition, and the underlying authority gap is that sell_planning does not consume the same canonical SELL_EXIT set that produced the same-day pending.

## Current Position Authority

Canonical current position authority:

.runtime/persistent_ledger/state.json

State:

- as_of = 2022-08-22
- source = runtime_v2_runtime_owned_fill_projection
- pm_current_source = .runtime/persistent_ledger/state.json
- pm_current_freshness = FRESH

Per-symbol:

| symbol | current_qty | pending_qty | runtime_sell_qty |
|---|---:|---:|---:|
| 60540 | 100 | 100 | 100 in Strategy Runtime planning; 0 in sell_planning PM REDUCE quantity contract |

CURRENT_POSITION_SOURCE_STATUS = PASS

## BUY / SELL Composition

BUY_SELL_COMPOSITION_INVOLVED = YES

The same-day pending was produced by morning as a composite accepted Strategy pending:

- BUY_ADD 94320 qty 200
- BUY_NEW 38150 qty 100
- BUY_NEW 72980 qty 100
- BUY_NEW 44410 qty 100
- BUY_NEW 71730 qty 100
- SELL_EXIT 60540 qty 100

sell_planning then saw active pending and preserved it fail-closed as REVIEW_REQUIRED instead of recognizing a same-day accepted composite pending whose SELL component had already been produced by canonical Strategy Runtime planning.

## Pending State / Execution Progress

EXECUTION_ADVANCED_OR_STALE_STATE = NO

Evidence:

- plan_created_date = 2022-08-23
- target_session_date = 2022-08-23
- state = APPROVED
- item states = CREATED
- consumed = false
- no SUBMITTED or PARTIALLY_FILLED markers
- no submit/execution/fill daily directory exists under the 2022-08-23 target run evidence

## Comparison Against Prior F1 Cases

2022-09-07 F1L/F1O:

- single SELL pending
- current_positions propagation mismatch
- no BUY+SELL composite pending as the primary blocker

2022-10-12 F1R:

- four SELL-only same-day pending set
- strict multi-SELL set-equivalence gap
- no BUY item in the pending set

2022-08-23 F1S:

- one SELL_EXIT plus five BUY items in same-day approved pending
- Strategy Runtime authoritative SELL_EXIT set differs from sell_planning PM direct input
- fail-closed active pending preservation

Classification:

- SAME_F1L_FAMILY = NO
- SAME_F1O_FAMILY = NO
- SAME_F1R_FAMILY = PARTIAL
- NEW_COMPOSITION_FAMILY = YES
- GENUINE_CONFLICT = NO
- OTHER = SELL authority producer/consumer mismatch also present

## F1F/F1I Activation

ESCALATION_REASON_OCCURRENCE_COUNT = 7

ESCALATED_SYMBOL_DATE_LIST:

- 2022-08-16 94340
- 2022-08-17 54010
- 2022-08-17 83060
- 2022-08-17 47840
- 2022-08-22 40800
- 2022-08-22 15180
- 2022-08-23 60540

F1F_F1I_ACTIVATION_CONFIRMED = YES

The clean run is using the F1F/F1I SELL escalation family; 60540 is the 2022-08-23 active example.

## State Integrity

DUPLICATE_SIDE_EFFECT_COUNT = 0

HALTED_RUN_STATE_INTEGRITY = PASS

No unsafe duplicate submit/order/execution/fill/cash/position side effect was found in the target 2022-08-23 run evidence. The run stopped before submit/execution directories were created for 2022-08-23.

## Repair Gate

REPAIR_CANDIDATE = YES

Narrow repair family:

Phase31-F1T should address same-day accepted BUY+SELL composite pending continuation where the SELL component is already a canonical Strategy Runtime SELL_EXIT, while preserving fail-closed behavior for genuine BUY/SELL conflicts.

The repair should also align sell_planning's authoritative SELL set construction with the canonical Strategy Runtime SELL_EXIT authority used to create the same-day pending. It must not weaken F1L/F1R by treating arbitrary BUY+SELL pending as equivalent, and must not use the raw PM REDUCE artifact as the final SELL authority when canonical Runtime planning has already escalated to SELL_EXIT.

RESUME_AFTER_REPAIR_POSSIBLE = CONDITIONAL

Resume is reasonable only after the F1T repair proves:

- same-day BUY+SELL composite pending with canonical SELL_EXIT component is recognized safely
- sell_planning authoritative SELL_EXIT set includes 60540
- REDUCE/no-order rows 99840 and 70140 remain excluded
- no duplicate pending is created
- BUY items are preserved without being silently overwritten
