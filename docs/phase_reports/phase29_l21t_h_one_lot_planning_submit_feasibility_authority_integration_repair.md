# Phase29-L21T-H One-Lot Planning / Submit Feasibility Authority Integration Repair

Task ID: `Phase29-L21T-H`

Mode: focused implementation + short regression. No fresh-run, resume-run, long Historical run, runtime state mutation, pending state mutation, Accepted Generation change, model change, threshold tuning, Safety hard-cap relaxation, or Historical-only branch was performed.

## Primary Judgment

```text
PHASE29_L21T_H_ONE_LOT_PLANNING_SUBMIT_FEASIBILITY_AUTHORITY_INTEGRATION_REPAIRED_FOCUSED_REGRESSION_PASS
```

```text
L21T_FRESH_VALIDATION_READY = YES
```

## Root Cause

L21T-G confirmed that PC / PS / Runtime Planning correctly delivered the 2022-08-24 `78780` one-lot BUY_NEW quantity, but common Runtime authority consumers later reinterpreted it through older continuous position amount / effective maximum position weight semantics.

Observed failing chain:

```text
PC one-lot authority PASS
-> PS one-lot quantity 100 materialized
-> Runtime Planning BUY_NEW quantity 100
-> Strategy Planning / Planning Submit Feasibility rechecks position cap / selected amount
-> BUY pending item REVIEW_REQUIRED
-> approved_buy_item_ids empty
-> L21T-F composition correctly reports active_buy_missing fail-closed
```

The direct Planning Submit Feasibility reason was:

```text
estimated amount exceeds selected_position_amount
```

The lower authority symptom was:

```text
position_sizing_above_effective_maximum_position_weight
```

## Changed Files

- `src/ai_fund_lab_v2/runtime_v2/position_sizing_authority.py`
- `tests/runtime_v2/test_phase26_step4_position_sizing_authority.py`
- `tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py`
- `tests/runtime_v2/test_phase23_i_strategy_planning_authority.py`
- `docs/phase_reports/phase29_l21t_h_one_lot_planning_submit_feasibility_authority_integration_repair.md`

## Producer

The canonical producer remains Strategy Portfolio Construction / Position Sizing.

The repair consumes existing evidence only:

- `phase29_l19_lot_resolution`
- `one_lot_fallback_applied`
- `one_lot_feasibility_status`
- `one_lot_quantity`
- `one_lot_notional`
- `strategy_cap_overshoot_applied`
- `lot_overshoot_reason`
- `post_trade_weight`
- `safety_hard_cap` / `safety_hard_cap_weight`
- `safety_hard_cap_preserved`
- `safety_margin_after_trade`
- discrete/final quantity fields when present

No duplicate Strategy authority was introduced.

## Consumer

The repaired consumer is common Runtime `resolve_position_sizing_authority()`.

It now recognizes a validated one-lot Strategy soft-cap overshoot authority when `target_weight > maximum_position_weight`, instead of always returning `position_sizing_above_effective_maximum_position_weight`.

When the one-lot authority is valid, it records:

```text
position_sizing_authority_status = PASS
position_sizing_authority_reason = one_lot_strategy_soft_cap_overshoot_authority_consumed
position_sizing_binding_constraint = ONE_LOT_STRATEGY_SOFT_CAP_OVERSHOOT_WITHIN_SAFETY_HARD_CAP
selected_position_amount >= authorized one_lot_notional
one_lot_authority_consumed = true
```

This also fixes Planning Submit Feasibility's exact-lot notional comparison, including the 2022-08-24 shape:

```text
selected_position_amount from rounded PS target = 241999.81
estimated one-lot amount = 242000.0
authorized one_lot_notional = 242000.0
```

## Canonical Authority Chain

```text
Portfolio Construction
-> phase29_l19_lot_resolution one-lot Strategy soft-cap overshoot authority
-> Position Sizing discrete one-lot materialization
-> Runtime Planning BUY_NEW / BUY_ADD / REENTRY quantity
-> Strategy Planning Authority pending item
-> common Runtime PositionSizingAuthority consumer
-> Planning Submit Feasibility
-> Pending approval link
-> Submit guard continuity
```

## Old Behavior

Runtime `PositionSizingAuthority` did this:

```text
if target_weight > maximum_position_weight:
    REVIEW_REQUIRED / position_sizing_above_effective_maximum_position_weight
```

Planning Submit Feasibility then also treated:

```text
estimated_amount > selected_position_amount
```

as a hard violation, even if the difference was the exact authorized one-lot notional after lot materialization.

## New Behavior

The Strategy 18% soft cap check remains active. It is bypassed only when all one-lot authority predicates pass:

- BUY semantic is `BUY_NEW`, `BUY_ADD`, or `REENTRY`
- boundary is `DISCRETE_LOT_EXCEEDS_STRATEGY_CAP_WITHIN_SAFETY_HARD_MAX`
- `strategy_cap_overshoot_applied == true`
- `one_lot_fallback_applied == true`
- `one_lot_feasibility_status == PASS`
- reason is canonical one-lot Strategy soft-cap overshoot
- requested quantity is exactly the authorized one-lot quantity
- authorized notional is positive
- post-trade weight is within Safety hard cap
- `safety_hard_cap_preserved` is not false
- Safety margin is not negative
- explicit Buy Quality / capacity / Corporate Action / REENTRY blocker fields, when present, are not failing

Malformed, missing, stale, multi-lot, or Safety-breaching authority remains fail-closed.

## Strategy 18% Semantics

18% remains the normal Strategy soft cap.

The repair does not allow arbitrary BUY_NEW up to 25%. It only consumes a formally produced one-lot exception for the discrete Japanese round-lot case.

## Safety 25% Semantics

25% remains a hard Safety cap.

The one-lot consumer refuses the exception if:

- `post_trade_weight > safety_hard_cap`
- Safety margin is negative
- `safety_hard_cap_preserved == false`
- Safety cap evidence is missing

## Exactly-One-Lot Validation

The repair requires requested quantity to match `one_lot_quantity`. A 200-share request with a 100-share one-lot authority remains blocked.

## BUY_NEW Result

Focused tests confirm the 2022-08-24 style BUY_NEW case now passes Runtime position-sizing authority and Planning Submit Feasibility:

```text
target_weight = 0.243189
maximum_position_weight = 0.18
one_lot_quantity = 100
one_lot_notional = 242000.0
selected_position_amount = 241999.81 -> upgraded to 242000.0 by authority consumption
```

## BUY_ADD Result

BUY_ADD keeps its semantic type. The common Runtime authority consumer accepts an authorized one-lot BUY_ADD overshoot and records `one_lot_authority_consumed=true`. It does not convert BUY_ADD to BUY_NEW.

## REENTRY Result

REENTRY keeps its semantic type. The common Runtime authority consumer accepts only an authorized one-lot REENTRY overshoot and does not bypass explicit REENTRY hard-blocker fields when present.

## SELL Independence Result

SELL / REDUCE / EXIT code paths were not changed. L21T-F behavior remains intact:

- valid BUY pending + SELL no-signal is preserved
- valid BUY + executable SELL can compose
- invalid / unapproved BUY is not blindly preserved as executable authority
- original REVIEW_REQUIRED pending remains visible fail-closed

SELL focused regressions passed.

## Pending Composition Regression Result

Pending composition focused suite passed:

```text
17 passed
```

This confirms L21T-F was not reverted.

## Production-common Confirmation

The implementation is in common Runtime authority code:

```text
src/ai_fund_lab_v2/runtime_v2/position_sizing_authority.py
```

It is not mode-specific and applies uniformly to Production, Demo, and Historical runtime consumers.

```text
Historical-special branch = NO
```

## Focused Regression Results

PASS:

```bash
PYTHONPATH=src python3 -m pytest \
  tests/runtime_v2/test_phase26_step4_position_sizing_authority.py \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py \
  tests/runtime_v2/test_phase23_i_strategy_planning_authority.py -q
```

Result:

```text
37 passed
```

PASS:

```bash
PYTHONPATH=src python3 -m pytest \
  tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py \
  tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py \
  tests/runtime_v2/test_phase28_d3_sell_pending_reconciliation.py -q
```

Result:

```text
39 passed
```

PASS:

```bash
PYTHONPATH=src python3 -m pytest \
  tests/strategy/test_phase22_j_position_sizing.py -k 'phase29_l21t_c or phase29_l21t_b or phase29_l21f or phase29_l21s or phase29_l19 or BUY_ADD or REENTRY' \
  tests/strategy/test_phase22_g_runtime_planning.py -k 'phase29_l21t_b or phase29_l21f or sell_reduce_exit or sell or BUY_ADD or REENTRY' -q
```

Result:

```text
23 passed, 114 deselected
```

PASS:

```bash
PYTHONPATH=src python3 -m pytest \
  tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py \
  tests/runtime_v2/test_phase15m_sell_broker_available_quantity_evidence.py \
  tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py -q
```

Result:

```text
23 passed
```

PASS:

```bash
PYTHONPATH=src python3 -m pytest \
  tests/strategy/test_phase22_e_portfolio_construction.py -k 'phase29_l21s or phase29_l19 or phase28_d55_b or phase29_l21d or phase29_l16_sell_reduce_exit' \
  tests/strategy/test_phase29_l21k_prior_exit_materialization.py \
  tests/strategy/test_phase22_qe_input_materialization.py -q
```

Result:

```text
16 passed, 89 deselected
```

## Static Results

PASS:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache PYTHONPATH=src python3 -m py_compile \
  src/ai_fund_lab_v2/runtime_v2/position_sizing_authority.py \
  src/ai_fund_lab_v2/runtime_v2/planning_submit_feasibility.py \
  src/ai_fund_lab_v2/runtime_v2/pending/promotion.py \
  src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py
```

Note: `PYTHONPYCACHEPREFIX` was used so pyc output stays inside a writable temp path under the Codex sandbox.

PASS:

```bash
git diff --check
```

## Remaining Gaps

Codex did not run fresh/resume/long Historical validation. The target run should be revalidated by the user after this focused repair.

The historical latest-path Safety observability split noted in L21T-A/G remains a non-causal remaining gap and was not changed.

## Fresh Validation Readiness

```text
L21T_FRESH_VALIDATION_READY = YES
```

Recommended user-run focused fresh validation:

```bash
PYTHONPATH=src python3 -m ai_fund_lab_v2.runtime_v2.run_historical \
  --profile historical-smoke \
  --start-date 2022-08-23 \
  --end-date 2022-09-16
```
