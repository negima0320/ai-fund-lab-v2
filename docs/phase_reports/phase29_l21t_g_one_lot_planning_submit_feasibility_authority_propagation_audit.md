# Phase29-L21T-G One-Lot Planning/Submit Feasibility Authority Propagation Audit

Task ID: `Phase29-L21T-G`

Task type: READ-ONLY ROOT CAUSE / AUTHORITY LINEAGE AUDIT.

No Production, Strategy, Runtime, config, schema, pending state, runtime state, fresh-run, resume-run, or long Historical execution change was performed.

Target run:

```text
reports/runtime_tests/runs/runtime-test-historical-smoke-20260812T032908579124Z
```

Target halt:

```text
2022-08-24:sell_planning
run_state.status = HALT
completed_business_days = ["2022-08-23"]
next_job = "2022-08-24:sell_planning"
```

## Primary Judgment

```text
PHASE29_L21T_G_ONE_LOT_AUTHORITY_PLANNING_SUBMIT_FEASIBILITY_MIGRATION_GAP_CONFIRMED
```

The 2022-08-24 halt is not a SELL Planning composition root bug. It is a downstream one-lot authority propagation gap in the Production/Demo/Historical common Runtime Planning and Planning Submit Feasibility path.

PC and PS correctly produced and consumed the one-lot Strategy soft-cap overshoot authority. Runtime Planning received the executable BUY quantity. The BUY then became non-approved before SELL Planning because later common-runtime authority consumers did not consume the same one-lot exception consistently:

1. `strategy_authority._planning_quantity_contract()` re-ran `resolve_position_sizing_authority()` and recorded `position_sizing_above_effective_maximum_position_weight`.
2. `pending.promotion.attach_approval_link()` ran `planning_submit_feasibility_pre_approved_pending`, which returned direct item review reason `estimated amount exceeds selected_position_amount`.

L21T-F then behaved correctly: the active pending was valid as an artifact but not valid as an approved BUY authority, so composition preserved the original pending fail-closed and reported `active_buy_missing`.

## Direct Halt Cause

Immediate runtime halt producer:

```text
daily/2022-08-24/sell_planning/sell_planning_manifest.json
stage = sell_planning_pending_pipeline
status = REVIEW_REQUIRED
reason = ACTIVE_PENDING_NOT_EMPTY:active_buy_missing;PENDING_PLAN_CONFLICT_ORIGINAL_PRESERVED
```

Pre-sell snapshot:

```text
active = true
read_classification = VALID
state = REVIEW_REQUIRED
plan_created_date = 2022-08-24
target_session_date = 2022-08-24
consume_consumed = false
buy_item_count = 1
approved_item_ids = []
approved_buy_item_ids = []
item_id = strategy-851f1f9d718e970f698b
side = BUY
quantity = 100
item state = REVIEW_REQUIRED
approved = false
approved_by_top_level = false
active_buy_pending_reason = active_buy_missing
```

Underlying direct business cause:

```text
planning_submit_feasibility.reason = estimated amount exceeds selected_position_amount
pending item feasibility_status = REVIEW_REQUIRED
pending item batch_submit_status = ITEM_REVIEW_REQUIRED
buy_items_status = REVIEW_REQUIRED
approved_buy_item_ids = []
```

## Root Cause Chain

| Step | Judgment | Evidence |
|---|---:|---|
| 1. PC approves one-lot Strategy soft-cap overshoot | CONFIRMED | `portfolio_construction.json` for `78780`: `target_weight=0.243189`, `continuous_target_weight=0.18`, `one_lot_fallback_applied=true`, `one_lot_feasibility_status=PASS`, `one_lot_quantity=100`, `one_lot_notional=242000.0`, `strategy_cap_overshoot_applied=true`, `safety_hard_cap_weight=0.25`, `safety_margin_after_trade=0.006811`. |
| 2. PS revalidates the authority | CONFIRMED | `position_sizing.json` for `78780`: `safety_hard_cap_validation=PASS`, `one_lot_authority_consumed=true`, `one_lot_authority_reason=ONE_LOT_STRATEGY_SOFT_CAP_OVERSHOOT_WITHIN_SAFETY_HARD_CAP`. |
| 3. PS materializes one-lot quantity | CONFIRMED | `target_quantity_candidate=100`, `transaction_quantity_candidate=100`, `quantity_delta_candidate=100`, `final_target_quantity=100`, `final_quantity_delta=100`, `discrete_authorized_quantity=100`, `discrete_authorized_notional=242000.0`. |
| 4. Runtime Planning receives BUY quantity | CONFIRMED | `runtime_planning.json`: `planning_intent=BUY_NEW`, `order_side_intent=BUY`, `planned_quantity=100`, `quantity_delta_candidate=100`, `quantity_status=RESOLVED_EXECUTABLE`. |
| 5. Downstream Runtime Planning / Submit Feasibility reapplies legacy/effective cap or selected amount | CONFIRMED | `quantity_contract.position_sizing_authority_status=REVIEW_REQUIRED`, reason `position_sizing_above_effective_maximum_position_weight`; then `planning_submit_feasibility.reason=estimated amount exceeds selected_position_amount`. |
| 6. One-lot authority is not propagated to that consumer | CONFIRMED | `resolve_position_sizing_authority()` only checks `target_weight > maximum_weight` and does not consume `phase29_l19_lot_resolution`; `pending.promotion._authority_context_from_item()` does not carry `position_sizing_authority` or lot resolution into pre-approved feasibility policy context. |
| 7. BUY item becomes REVIEW_REQUIRED | CONFIRMED | Pending item `strategy-851f1f9d718e970f698b`: `state=REVIEW_REQUIRED`, `feasibility_status=REVIEW_REQUIRED`, `batch_submit_status=ITEM_REVIEW_REQUIRED`. |
| 8. approved_buy_item_ids becomes empty | CONFIRMED | Pending top-level `approved_item_ids=[]`, `approved_buy_item_ids=[]`. |
| 9. L21T-F composition returns active_buy_missing fail-closed | CONFIRMED | `read_active_buy_pending()` requires BUY item ID in top-level `approved_item_ids`; sell snapshot has no approved BUY IDs and reason `active_buy_missing`. |
| 10. sell_planning stops REVIEW_REQUIRED | CONFIRMED | `sell_planning_pending_pipeline.status=REVIEW_REQUIRED`, exit code 20, run halted at `2022-08-24:sell_planning`. |

## One-Lot Authority Producer

Canonical producer is Portfolio Construction, with Position Sizing acting as downstream validator/materializer.

Producer evidence:

- `src/ai_fund_lab_v2/strategy/portfolio_construction.py` records `strategy_cap_overshoot_applied`, `strategy_cap_overshoot_reason`, one-lot fallback fields, and Safety cap preservation when `_lot_aware_strategy_cap_overshoot_allowed()` permits the one-lot increment.
- `src/ai_fund_lab_v2/strategy/position_sizing.py` validates `_lot_aware_strategy_cap_overshoot_authorized_position()` and materializes discrete quantity when the boundary is `DISCRETE_LOT_EXCEEDS_STRATEGY_CAP_WITHIN_SAFETY_HARD_MAX`.

For `78780` on 2022-08-24:

```text
continuous_target_notional = 179119.8
continuous_target_weight = 0.18
one_lot_notional = 242000.0
one_lot_weight = 0.243189
strategy_cap_overshoot_weight = 0.063189
safety_hard_cap = 0.25
safety_margin_after_trade = 0.006811
```

## One-Lot Authority Consumers

Confirmed consumers:

- Position Sizing: consumes and records `one_lot_authority_consumed=true`.
- Runtime Planning: consumes final PS quantity and emits BUY_NEW 100.
- Strategy Planning Authority: consumes Runtime Planning quantity to generate a pending item, but its local position-sizing authority revalidation is not one-lot aware.

Missing or incomplete consumers:

- `src/ai_fund_lab_v2/runtime_v2/position_sizing_authority.py`: common runtime resolver does not consume `phase29_l19_lot_resolution`, `one_lot_fallback_applied`, `one_lot_feasibility_status`, `strategy_cap_overshoot_applied`, or Safety margin before marking `target_weight > maximum_position_weight` as `REVIEW_REQUIRED`.
- `src/ai_fund_lab_v2/runtime_v2/pending/promotion.py`: pre-approved pending feasibility rebuilds policy context from pending items but only propagates position-count and cash-exposure authority. It does not propagate the nested position-sizing authority / lot-resolution authority.
- `src/ai_fund_lab_v2/runtime_v2/planning_submit_feasibility.py`: BUY item feasibility treats `estimated_amount > selected_position_amount` as a hard position-sizing violation even when the selected executable quantity is exactly the authorized one lot.

Submit was not reached in the target run.

## Missing Consumer / Migration Gap

The missing consumer is the common Runtime submit-feasibility authority boundary:

```text
Strategy Planning Authority quantity contract
-> Pending approval link / planning_submit_feasibility_pre_approved_pending
-> Submit guard continuity
```

The code path is Production/Demo/Historical common. This is not a Historical-only issue and must not be repaired with a Historical branch.

The canonical one-lot exception was migrated into PC and PS, but not into the Runtime authority resolver used by Strategy Planning and Planning Submit Feasibility. The runtime resolver still behaves as if the Strategy 18% cap is a hard maximum unless the row shape avoids `maximum_position_weight`; the later selected-amount guard still behaves as if continuous target notional is the hard execution cap.

## selected_position_amount Authority

`selected_position_amount` is currently resolved by `runtime_v2.position_sizing_authority.resolve_position_sizing_authority()` as:

```text
target_notional = row.target_notional or row.selected_position_amount
incremental_buy = row.incremental_buy_notional or row.remaining_add_capacity
selected_position_amount = max(incremental_buy, 0)
```

For this case:

```text
target_notional = 241999.81
incremental_buy_notional = 241999.81
selected_position_amount = 241999.81
planned quantity = 100
reference price = 2420.0
estimated_amount = 242000.0
```

So the direct pre-approved feasibility violation is a 0.19 JPY mismatch after lot materialization:

```text
242000.0 > 241999.81
```

This amount is not the original 18% continuous cap amount (`179119.8`). It is the PS target notional calculated from rounded weight/equity, while the actual executable one-lot notional is exact quantity times reference price.

Conclusion:

- Producer: Position Sizing row / Runtime `PositionSizingAuthority`.
- Canonical authority after L21S/L21T-B/C: should be the discrete authorized one-lot notional when the one-lot authority contract passes.
- Current formula: continuous/rounded target notional, not the final executable lot notional.
- 18% relation: direct effective cap check still uses `maximum_position_weight=0.18`.
- Safety 25% relation: PC/PS evidence proves `post_trade_weight=0.243189 <= 0.25`, but submit feasibility does not consume that proof.
- Discrete lot awareness: incomplete.
- Current blocker validity after L21S/B/C: not valid for this exact one-lot authorized case; valid only when the one-lot authority predicates are absent or fail.

## Effective Maximum Position Weight Authority

`effective_maximum_position_weight` is produced in Strategy Position Sizing from Safety authority as:

```text
min(strategy_maximum_position_weight, safety_maximum_position_weight)
```

In the relevant row, the effective consumer value is `maximum_position_weight=0.18`; Safety hard cap evidence remains `0.25` in `phase29_l19_lot_resolution`.

The common runtime resolver checks:

```text
if maximum_weight is not None and target_weight > maximum_weight:
    reason = position_sizing_above_effective_maximum_position_weight
    status = REVIEW_REQUIRED
```

That resolver currently has no exception path equivalent to Strategy Position Sizing's `_lot_aware_strategy_cap_overshoot_authorized_position()`. For BUY_NEW / REENTRY / BUY_ADD, the intended contract is not to remove the Strategy soft cap or weaken Safety; it is to allow exactly the already-authorized one-lot Strategy soft-cap overshoot when Safety hard cap and all other gates pass.

## Planning Submit Feasibility Analysis

`planning_submit_feasibility_pre_approved_pending` is invoked in `pending.promotion.attach_approval_link()` before approved item IDs are materialized into pending. On failure it rewrites the plan to:

```text
state = REVIEW_REQUIRED
approved_item_ids = []
approved_buy_item_ids = []
buy_items_status = REVIEW_REQUIRED
review_scope = BUY_ITEM_SCOPED_REVIEW
sell_continuation_allowed = true
```

This explains why the approval artifact itself contains the BUY item ID, while the final current pending does not.

Two separate downstream mismatches are visible:

1. Strategy Planning quantity contract records `position_sizing_authority_status=REVIEW_REQUIRED` because common runtime position-sizing authority does not know the one-lot exception.
2. Pre-approved feasibility then records `position_sizing_authority_status=PASS` from a reduced policy context, but fails on `estimated_amount > selected_position_amount` because it compares exact lot notional against rounded PS target notional.

Both point to the same repair boundary: the common runtime feasibility consumer must consume the discrete one-lot authority contract instead of reinterpreting rounded continuous notional or Strategy soft cap as a hard execution blocker.

## L21T-F Evaluation

L21T-F is correct fail-closed behavior in this target run.

`read_active_buy_pending()` requires:

- valid pending read
- active/non-terminal state
- unconsumed pending
- same `plan_created_date`
- same `target_session_date`
- BUY item quantity > 0
- BUY item ID present in top-level `approved_item_ids`

The target pending satisfies artifact validity/date/quantity requirements but fails the approved BUY authority requirement. Therefore:

```text
active_buy_missing = SECONDARY_SYMPTOM
composition.py repair needed for this root cause = NO
```

L21T-F also preserved the original REVIEW_REQUIRED pending instead of overwriting it with EMPTY or SELL-only output, which is the desired fail-closed behavior.

## SELL Independence Evaluation

The BUY review is item-scoped:

```text
review_scope = BUY_ITEM_SCOPED_REVIEW
sell_continuation_allowed = true
sell_items_status = NOT_PRESENT
```

In this target run PM produced only HOLD decisions:

```text
pm_decision_count = 2
pm_hold_count = 2
pm_reduce_count = 0
pm_exit_count = 0
selected_count = 0
```

So there was no executable SELL item to continue. SELL no-signal under an invalid active BUY pending correctly preserved the original pending and returned REVIEW_REQUIRED. This does not prove an executable SELL would be blocked; it proves this target run did not exercise executable SELL continuation.

Repair must preserve BUY/SELL independence:

- BUY authority remains produced by Strategy Planning / pending producer.
- SELL authority remains produced by PM / SELL Planning.
- Shared pending composition may preserve or compose independently approved items.
- SELL must not rewrite BUY quantity or resurrect unapproved BUY authority.

## Historical Safety Consumer Split

Classification:

```text
NON_CAUSAL_REMAINING_GAP
```

The sell planning runtime manifest still contains an early `safety_operation_guard` snapshot with:

```text
safety_decision = REVIEW_REQUIRED
safety_reason = safety decision evidence missing
safety_status = SAFETY_MISSING
```

But the same manifest later records:

```text
historical_safety_authority.status = PASS
safety_decision = NEUTRAL
safety_reason = historical_neutral_no_event_safety_ready
safety_source = data_readiness_historical_temporal_authority
safety_block_buy = false
safety_block_sell = false
```

The stopping stage itself has `safety_status=PASS`, `safety_block_buy=false`, `safety_block_sell=false`. Therefore this is the same historical latest-path consumer split noted in L21T-A, not the direct cause of this halt.

## Regression / Pre-existing Gap Classification

Classification:

```text
B. L21T-C exposed a pre-existing downstream migration gap
D. legacy architecture conflict remains in common runtime feasibility
```

Not classified as:

- L21T-F regression: L21T-F preserved invalid active pending fail-closed.
- Pure L21T-C regression: L21T-C made the one-lot BUY quantity reachable; the failing downstream consumer already had independent cap/selected-amount validation semantics.
- Safety regression: Safety hard cap was not breached and historical Safety was neutralized by Data Readiness authority.

## Recommended Repair Boundary

Next repair should be Production/Demo/Historical common and focused on the Runtime authority consumer boundary:

```text
runtime_v2.position_sizing_authority
runtime_v2.planning.strategy_authority quantity_contract construction
runtime_v2.pending.promotion policy context propagation
runtime_v2.planning_submit_feasibility BUY item validation
submit guard continuity tests if Submit consumes the same evidence
```

Do not:

- remove Strategy 18% soft cap
- weaken Safety 25% hard cap
- bypass feasibility unconditionally
- carry BUY pending blindly
- merge BUY and SELL decision authorities
- restore missing BUY at Submit
- add Historical-only rescue

The allowed exception should be gated by canonical evidence equivalent to:

```text
one_lot_fallback_applied == true
one_lot_feasibility_status == PASS
strategy_cap_overshoot_applied == true
lot_overshoot_reason == ONE_LOT_STRATEGY_SOFT_CAP_OVERSHOOT_WITHIN_SAFETY_HARD_CAP
selected/final quantity == exactly one round lot
estimated_amount == one_lot_notional or <= discrete_authorized_notional with tick-safe tolerance
post_trade_weight <= safety_hard_cap
cash feasibility PASS
gross exposure PASS
BUY quality PASS / not rejected
REENTRY hard gates PASS when semantic is REENTRY
Corporate Action hard blockers absent
```

## Production-common Requirement

The repair belongs in common runtime authority and feasibility code, not in historical orchestration. Production fail-closed must remain intact:

- missing or malformed one-lot authority remains REVIEW_REQUIRED
- stale / consumed / unapproved / date-mismatched pending remains non-preservable
- Safety hard cap remains hard
- non-one-lot multi-lot overshoot remains blocked
- SELL/REDUCE/EXIT authority remains independent

## Validation Plan

Focused regression for the next implementation task:

1. 2022-08-24 style BUY_NEW one-lot overshoot reaches approved BUY pending:
   - PC/PS authority present
   - Strategy Planning quantity contract does not mark `position_sizing_above_effective_maximum_position_weight`
   - pre-approved feasibility PASS
   - `approved_buy_item_ids` contains the BUY item
   - Submit sees the BUY item
2. Rounded target notional vs exact one-lot notional:
   - `selected_position_amount=241999.81`
   - `estimated_amount=242000.0`
   - exact authorized one-lot notional PASS only when canonical one-lot evidence is valid.
3. Invalid one-lot evidence remains fail-closed:
   - missing lot resolution
   - reason mismatch
   - quantity > one lot
   - post-trade weight > Safety hard cap
   - stale/date mismatch/consumed pending
4. 2022-09-14 style valid BUY + executable SELL composition still creates composite pending.
5. SELL no-signal with invalid BUY still preserves original REVIEW_REQUIRED pending and does not EMPTY it.
6. BUY_NEW / BUY_ADD / REENTRY focused strategy regressions.
7. SELL / REDUCE / EXIT focused runtime regressions.
8. Submit guard focused tests for item-level authority continuity.
9. Static:
   - `python -m py_compile` focused modules
   - `git diff --check`

User fresh validation command after repair, not for this audit:

```bash
PYTHONPATH=src python3 -m ai_fund_lab_v2.runtime_v2.run_historical \
  --profile historical-smoke \
  --start-date 2022-08-23 \
  --end-date 2022-09-16
```

## L21T-H_READY

```text
YES
```

Recommended next task:

```text
Phase29-L21T-H — One-Lot Authority Planning/Submit Feasibility Consumer Repair
```

Entry scope:

- common runtime authority propagation
- planning submit feasibility one-lot consumption
- selected amount / exact lot notional reconciliation
- focused regression only before user-run historical validation
