# Phase29-L21T-J - One-Lot Authority Non-Firing and Batch Review Propagation Audit

Task ID: `Phase29-L21T-J`

Audit mode: READ-ONLY. No implementation, config, threshold, model, Accepted Generation, Runtime/Pending mutation, fresh-run, resume-run, or long Historical run was performed.

Target run:

`reports/runtime_tests/runs/runtime-test-historical-smoke-20260812T055747290953Z`

HALT:

- Business date: `2023-05-16`
- Stage: `sell_planning`
- Runtime CLI stop: `2023-05-16:sell_planning`, exit code `20`
- Fresh-run summary: `status=HALT`, `exit_code=30`, `run_result=HALT`, completed business days `28`
- Run state next job: `2023-05-16:sell_planning`

## Primary Judgment

`PHASE29_L21T_J_MULTI_CAUSAL_ONE_LOT_AND_BATCH_REVIEW_GAPS_CONFIRMED`

The HALT is not an `active_buy_missing` root-cause bug. `active_buy_missing` is a downstream symptom of an upstream BUY approval failure.

Root cause chain:

1. Strategy PC and PS correctly produced a valid one-lot BUY_NEW authority for `30410` quantity `100`.
2. Runtime Planning carried executable BUY quantity `100`.
3. The pending item / planning-submit-feasibility policy context lost the PS/PC one-lot authority payload: `phase29_l19_lot_resolution={}`, `one_lot_authority_consumed=false`, `discrete_authorized_quantity=0`.
4. L21T-H consumer logic therefore could not lift `selected_position_amount` from continuous `186,617.98` to the authorized one-lot notional `227,400`.
5. Planning Submit Feasibility failed the `30410` BUY item with `estimated amount exceeds selected_position_amount`.
6. Existing Phase24 aggregate batch contract converted the otherwise PASS `24350` 500-share BUY to `BLOCKED_BY_BATCH_REVIEW`.
7. Top-level `approved_item_ids=[]`, so L21T-F correctly read no approved active BUY and returned `active_buy_missing` fail-closed while preserving the original REVIEW_REQUIRED pending.
8. A SELL reduce item existed in the SELL pipeline, and pending state had `sell_continuation_allowed=true`, but composition did not materialize a SELL continuation pending under this invalid BUY state.

## Exact Halt Cause

SELL Planning stopped with:

`sell planning pipeline review required: existing_buy_pending_not_preservable:active_buy_missing;PENDING_PLAN_CONFLICT_ORIGINAL_PRESERVED`

Pre-sell snapshot:

- `state=REVIEW_REQUIRED`
- `read_classification=VALID`
- `plan_created_date=2023-05-16`
- `target_session_date=2023-05-16`
- `approved_item_ids=[]`
- `approved_buy_item_ids=[]`
- `buy_item_count=2`
- BUY items:
  - `strategy-4123c260ac0c1af2deb4`, symbol `24350`, quantity `500`, state `REVIEW_REQUIRED`
  - `strategy-2d6618ea2a942fb23636`, symbol `30410`, quantity `100`, state `REVIEW_REQUIRED`

The direct HALT is pending composition review. The causal upstream failure is the `30410` planning-submit feasibility review.

## 100-Share BUY Producer/Consumer Lineage

| Stage | Artifact / producer | 30410 evidence |
| --- | --- | --- |
| Buy Quality | `strategy/buy_quality_decisions.json` | `quality_status=PASS`, `quality_action=REDUCED_ALLOCATION_ONLY`, `quality_score=0.82066`, rank `1` |
| Portfolio Construction | `strategy/portfolio_construction.json` | `semantic_buy_type=BUY_NEW`, `current_position=false`, `current_quantity=null`, `target_weight=0.230339`, `accepted_buy_new_weight=0.049828`, `lot_aware_accepted_buy_new_weight=0.230339` |
| PC L19 authority | `portfolio_members[].phase29_l19_lot_resolution` | `one_lot_fallback_applied=true`, `one_lot_feasibility_status=PASS`, `one_lot_quantity=100`, `one_lot_notional=227400`, `strategy_cap_overshoot_applied=true`, `strategy_cap_weight=0.18`, `safety_hard_cap_weight=0.25`, `safety_margin_after_trade=0.019661` |
| Position Sizing | `strategy/position_sizing.json` | `position_type=NEW_POSITION`, `current_quantity=0`, `target_quantity_candidate=100`, `final_quantity_delta=100`, `transaction_target_notional=227400`, `target_notional=186617.98`, `reference_price=2274` |
| PS one-lot authority | `position_sizing.positions[]` | `one_lot_authority_consumed=true`, `one_lot_authority_reason=ONE_LOT_STRATEGY_SOFT_CAP_OVERSHOOT_WITHIN_SAFETY_HARD_CAP`, `discrete_authorized_quantity=100`, `discrete_authorized_notional=227400` |
| Runtime Planning | `strategy/runtime_planning.json` | `planning_intent=BUY_NEW`, `order_side_intent=BUY`, `planned_quantity=100`, `quantity_status=RESOLVED_EXECUTABLE`, `reference_price=2274` |
| Pending item | `.runtime/pending_order_plan/pending_order_plan.json` | `pending_item_id=strategy-2d6618ea2a942fb23636`, `quantity=100`, `source_decision_type=BUY_NEW`, `estimated_amount=227400`, `state=REVIEW_REQUIRED` |
| Pending quantity contract | `items[].quantity_contract` | `selected_position_amount=186617.98`, `estimated_amount=227400`, `phase29_l19_lot_resolution={}`, `one_lot_authority_consumed=false`, `discrete_authorized_quantity=0`, `lot_adjusted_quantity=100` |
| Planning Submit Feasibility | `pending_order_plan.planning_submit_feasibility.items[]` | `status=REVIEW_REQUIRED`, `violated_policy=position_sizing`, `reason=estimated amount exceeds selected_position_amount`, `selected_position_amount=186617.98`, `estimated_amount=227400` |

Exact item values:

- Security code: `30410`
- Source decision type: `BUY_NEW`
- Current quantity: `0`
- Target quantity: `100`
- Selected/requested quantity: `100`
- Reference price: `2,274`
- Estimated amount: `227,400`
- PS target notional / selected position amount before one-lot lift: `186,617.98`
- PC one-lot notional: `227,400`
- Strategy cap: `18%`
- Safety hard cap: `25%`
- PC final target weight: `23.0339%`
- PS target weight after quality/sizing: `18.9030%`
- One-lot post-trade weight: `23.0339%`

## Why L21T-H Authority Did Not Fire

L21T-H added common Runtime consumer logic in `resolve_position_sizing_authority()`:

- It loads a position sizing row from artifact or `policy_context`.
- It checks `target_weight > maximum_weight`.
- It then calls `_one_lot_strategy_soft_cap_authority()`.
- If the one-lot authority returns PASS, it sets `selected_position_amount = max(selected_amount, authorized_one_lot_notional)` and records `one_lot_authority_consumed=true`.

For `30410`, the original PS artifact satisfies the L21T-H predicates:

- `phase29_l19_lot_resolution` exists in PC and PS.
- `one_lot_fallback_applied=true`.
- `one_lot_feasibility_status=PASS`.
- `strategy_cap_overshoot_applied=true`.
- `one_lot_quantity=100`.
- Requested quantity is `100`.
- `one_lot_notional=227400`.
- Safety hard cap is preserved: `safety_hard_cap_preserved=true`, `safety_margin_after_trade=0.019661`.

However, the Planning Submit Feasibility consumer did not receive that authority. Its policy-context item has:

- `phase29_l19_lot_resolution={}`
- `one_lot_authority_consumed=false`
- `one_lot_authority_reason=""`
- `discrete_authorized_quantity=0`
- `discrete_authorized_notional=0`

Because the authority payload is absent at the consumer boundary, L21T-H cannot classify this as an authorized one-lot overshoot. The consumer keeps `selected_position_amount=186617.98`, while the actual one-lot order amount is `227400`, triggering the review.

Classification:

`L21T-H migration/integration gap`, not a correctly-outside-authority case.

This is not caused by BUY_NEW / BUY_ADD / REENTRY semantic branching. The item is BUY_NEW and L21T-H explicitly supports BUY_NEW one-lot overshoot when authority is present. It is not caused by existing-position branching; `30410` is a new position. It is not a Safety breach; PC says one lot remains within the 25% hard cap.

## 500-Share Normal BUY Collateral Blocking

The normal BUY item is:

- Symbol: `24350`
- Pending item ID: `strategy-4123c260ac0c1af2deb4`
- Source decision type: `BUY_NEW`
- Quantity: `500`
- Estimated amount: `159,500`
- Feasibility status: `PASS`
- Position sizing authority status: `PASS`
- Position sizing reason: `position_sizing_authority_resolved`
- Selected position amount: `176,140.4`
- Estimated amount <= selected position amount

Yet the pending item is:

- `approved=false`
- `state=REVIEW_REQUIRED`
- `batch_submit_status=BLOCKED_BY_BATCH_REVIEW`
- `item_review_reason=batch_submit_blocked_by_item_scoped_review`

This is collateral blocking from batch-level approval semantics, not an item-local feasibility failure.

## Batch Review Contract Analysis

Existing code in `pending/promotion.py` defines the behavior:

- `_review_scope_for_submit_feasibility()` classifies a failed BUY-only item with known violated policy as `BUY_ITEM_SCOPED_REVIEW`.
- It sets `sell_continuation_allowed=true`.
- When any approved candidate item is in review, `link_approval_to_pending()` returns the whole plan as `REVIEW_REQUIRED`.
- `_materialize_item_scoped_review_state()` sets the reviewed item to `ITEM_REVIEW_REQUIRED`, and all other approved candidate items to `BLOCKED_BY_BATCH_REVIEW`.
- Top-level `approved_item_ids`, `approved_buy_item_ids`, and `approved_sell_item_ids` are all cleared.

The behavior is covered by `tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py`, which asserts that earlier PASS BUY items become `BLOCKED_BY_BATCH_REVIEW` when a later BUY item fails aggregate submit feasibility.

Therefore, `24350` blocking is design-consistent with existing Phase24 aggregate pending batch reservation behavior.

But it is also a confirmed design coupling:

- Item-scoped review does not produce partial BUY approval.
- Other valid BUY items cannot proceed in the same batch.
- This may be intentionally conservative for aggregate reservation, but it prevents a valid 500-share BUY from reaching Submit/Execution.

Conclusion:

`batch-level review coupling gap = YES`, as a design-review item. This audit does not claim partial BUY approval is already allowed or should be added without a new contract.

## Pending Composition Causality

L21T-F is not the root cause.

`read_active_buy_pending()` requires:

- valid pending read
- active state
- unconsumed pending
- same plan/session date
- positive BUY item
- BUY item ID present in top-level `approved_item_ids`

The pending plan is valid, active, same-date, and contains positive BUY quantities, but top-level `approved_item_ids=[]`. Therefore `active_buy_missing` is correct fail-closed behavior.

SELL Planning result:

- `pending_composition_model=PRESERVE_ACTIVE_PENDING_ON_INVALID_BUY`
- `pending_composition_status=REVIEW_REQUIRED`
- `reason=existing_buy_pending_not_preservable:active_buy_missing;PENDING_PLAN_CONFLICT_ORIGINAL_PRESERVED`

This preserved the original REVIEW_REQUIRED pending instead of erasing it with EMPTY or SELL-only pending. That matches L21T-F fail-closed intent.

## SELL Independence Analysis

SELL authority itself was produced:

- PM decisions include two REDUCE decisions (`94340`, `76010`).
- SELL pipeline order plan includes at least a REDUCE SELL item for `76010`, quantity `100`, with `quantity_contract.status=PASS`.

The pending plan also records:

- `review_scope=BUY_ITEM_SCOPED_REVIEW`
- `sell_continuation_allowed=true`

However, SELL composition did not materialize a SELL continuation pending because the active BUY pending was not preservable as approved BUY, so the original REVIEW_REQUIRED pending was preserved.

Classification:

- BUY/SELL decision authority merge: not observed.
- SELL quantity rewritten by BUY: not observed.
- SELL continuation risk: YES. There is a contract mismatch between `sell_continuation_allowed=true` and pending composition preserving the invalid BUY pending without adding executable SELL.

This should be scoped as a SELL continuation / composition contract gap, not as an L21T-F regression and not as a reason to resurrect invalid BUY.

## Regression Classification

| Question | Judgment |
| --- | --- |
| L21T-H regression confirmed | YES, at integration/migration boundary |
| One-lot authority propagation gap | YES |
| Batch-level review coupling gap | YES |
| L21T-F regression | NO |
| SELL independence risk | YES |
| Runtime plumbing defect | YES, common Runtime authority materialization/consumer-context propagation defect |

Details:

- L21T-H logic is conceptually correct for this one-lot case, but the authority evidence was not propagated into the pending approval / planning-submit feasibility consumer path.
- The 500-share BUY blocking is current contract behavior, not an accidental artifact, but it is a coupling that now needs explicit review.
- L21T-F correctly treated an unapproved BUY as non-preservable and preserved the original REVIEW_REQUIRED pending.

## Recommended Next Repair Scope

Stay in Phase29. Do not move to Phase30 yet.

Recommended repair scope:

1. Production/Demo/Historical common authority propagation repair:
   - Ensure pending item quantity contract or planning-submit-feasibility policy context carries the PS one-lot authority fields for valid one-lot BUY_NEW / BUY_ADD / REENTRY cases.
   - Required fields include `phase29_l19_lot_resolution`, `one_lot_authority_consumed`, `one_lot_authority_reason`, `discrete_authorized_quantity`, and `discrete_authorized_notional`.
   - Do not loosen Safety hard caps or infer one-lot authority when PC/PS did not produce it.

2. Focused regression:
   - `2023-05-16 / 30410` style one-lot BUY_NEW reaches approved BUY pending when PC/PS authority is valid.
   - Invalid one-lot evidence remains fail-closed.
   - BUY_ADD and REENTRY semantic paths preserve their own hard blockers.

3. Batch review contract design decision:
   - Determine whether partial BUY approval is allowed under Phase24 aggregate reservation.
   - If allowed, define a new explicit contract before implementation.
   - If not allowed, preserve `BLOCKED_BY_BATCH_REVIEW` and document this as intentional capital deployment conservatism.

4. SELL continuation contract repair/audit:
   - Reconcile `sell_continuation_allowed=true` with composition behavior when BUY review is item-scoped and a valid SELL item exists.
   - Do not let SELL resurrect invalid BUY or rewrite BUY quantity.

Forbidden repair paths:

- Historical-only rescue.
- Blind carry-forward of BUY pending.
- Submit-side reconstruction of missing BUY authority.
- Weakening Production fail-closed behavior.
- BUY/SELL authority merge.
- 100BD-only exception.

## Resume Readiness Judgment

Resume readiness: `NO`.

Reason:

The halted run should not be resumed as validation until the one-lot authority propagation gap is repaired and focused regression confirms that `30410`-style authority survives into pending approval / planning-submit feasibility. The run is a valid audit source, but not a clean continuation baseline.

## Final Judgment

`PHASE29_L21T_J_MULTI_CAUSAL_ONE_LOT_AND_BATCH_REVIEW_GAPS_CONFIRMED`
