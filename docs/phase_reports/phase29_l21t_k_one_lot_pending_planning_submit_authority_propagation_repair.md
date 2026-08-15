# Phase29-L21T-K One-Lot Pending / Planning Submit Authority Propagation Repair

Mode: focused Production/Demo/Historical common runtime implementation + short regression. No fresh-run, resume-run, long Historical run, Production/Demo broker mutation, runtime/pending state mutation outside isolated tests, Accepted Generation change, model retraining, threshold tuning, Historical-only rescue, batch review contract change, or SELL authority change was performed.

## Primary Judgment

`PHASE29_L21T_K_ONE_LOT_PENDING_PLANNING_SUBMIT_AUTHORITY_PROPAGATION_REPAIRED_FOCUSED_REGRESSION_PASS`

```text
ONE_LOT_AUTHORITY_PENDING_PROPAGATION = PASS
PLANNING_SUBMIT_ONE_LOT_CONSUMPTION = PASS
SAFETY_HARD_CAP_PRESERVED = YES
BATCH_REVIEW_CONTRACT_CHANGED = NO
L21T_F_BEHAVIOR_CHANGED = NO
SELL_AUTHORITY_CHANGED = NO
FRESH_VALIDATION_READY = YES
```

## Scope

This repair addresses the L21T-J/L21T-K authority propagation break where Portfolio Construction, Position Sizing, and Runtime Planning had valid one-lot BUY authority, but Pending / Planning Submit feasibility lost the one-lot position sizing authority and rejected the item against the pre-lot selected amount.

Target causal evidence from the L21T-J run:

- `2023-05-16:sell_planning`, symbol `30410`, BUY_NEW, 100 shares.
- PC/PS/Runtime Planning had one-lot authority:
  - `one_lot_fallback_applied=true`
  - `one_lot_feasibility_status=PASS`
  - `one_lot_quantity=100`
  - `one_lot_notional=227400`
  - `strategy_cap_weight=0.18`
  - `safety_hard_cap_weight=0.25`
  - `safety_margin_after_trade=0.019661`
  - `planned_quantity=100`
- Pending / Planning Submit feasibility lost the authority:
  - `phase29_l19_lot_resolution={}`
  - `one_lot_authority_consumed=false`
  - `discrete_authorized_quantity=0`
  - `discrete_authorized_notional=0`
  - rejected with `estimated amount exceeds selected_position_amount`.

L21T-F `active_buy_missing` remains classified as downstream fail-closed behavior after BUY approval failed, not the root cause for K.

## Root Cause

Two common-runtime propagation boundaries were incomplete:

1. `pending.promotion._authority_context_from_item()` rebuilt the pending-level `policy_context` from item quantity contracts but did not carry `position_sizing_authority` or one-lot authority fields. This made the pending artifact lose the authoritative PS context needed by downstream planning-submit evidence.
2. `position_sizing_authority.resolve_position_sizing_authority()` could re-evaluate a position sizing artifact row with `maximum_position_weight`, but when it consumed a Strategy-produced `position_sizing_authority` dict, the strategy cap was only present inside `phase29_l19_lot_resolution`. Submit re-resolution therefore treated the item as normal `PORTFOLIO_POLICY`, leaving `one_lot_authority_consumed=false` in item evidence.

## Repair

Changed common runtime only:

- `src/ai_fund_lab_v2/runtime_v2/pending/promotion.py`
  - Propagates nested `position_sizing_authority`.
  - Propagates item-level position sizing and one-lot fields into pending `policy_context`.
- `src/ai_fund_lab_v2/runtime_v2/position_sizing_authority.py`
  - Uses `phase29_l19_lot_resolution.strategy_cap_weight` / `strategy_target_cap` as a strategy-cap fallback when re-consuming an authority dict.
  - Preserves the existing fail-closed predicates: semantic must be BUY_NEW/BUY_ADD/REENTRY, lot classification must be `DISCRETE_LOT_EXCEEDS_STRATEGY_CAP_WITHIN_SAFETY_HARD_MAX`, one-lot feasibility must be PASS, requested quantity must match the authorized one lot, safety hard cap must remain preserved, and explicit quality/capacity/corporate-action/reentry blockers still prevent consumption.

No BUY/SELL decision authority was merged. No submit-side resurrection of missing BUY was added. No Historical-only branch was added.

## Focused Regression Added

Added `test_phase29_l21t_k_strategy_authority_preserves_one_lot_authority_to_pending_submit_feasibility`.

The test materializes the `30410` L21T-K shape:

- Position Sizing selected amount: `186617.98`
- One-lot authorized notional: `227400.0`
- Runtime Planning `planned_quantity=100`
- Pending item BUY_NEW quantity `100`
- Pending `quantity_contract.position_sizing_authority.phase29_l19_lot_resolution.one_lot_quantity=100`
- Pending-level `policy_context.position_sizing_authority` preserved
- Planning Submit item evidence PASS
- Planning Submit item evidence `selected_position_amount=227400.0`
- Planning Submit item evidence `one_lot_authority_consumed=true`
- Binding constraint `ONE_LOT_STRATEGY_SOFT_CAP_OVERSHOOT_WITHIN_SAFETY_HARD_CAP`

## Verification

```text
PYTHONPATH=src python3 -m pytest tests/runtime_v2/test_phase23_i_strategy_planning_authority.py::test_phase29_l21t_k_strategy_authority_preserves_one_lot_authority_to_pending_submit_feasibility -q --tb=short
PASS: 1 passed

PYTHONPATH=src python3 -m pytest tests/runtime_v2/test_phase23_i_strategy_planning_authority.py::test_phase29_l21t_b_strategy_authority_commits_one_lot_buy_new_soft_cap_plan tests/runtime_v2/test_phase23_i_strategy_planning_authority.py::test_phase29_l21t_k_strategy_authority_preserves_one_lot_authority_to_pending_submit_feasibility tests/runtime_v2/test_phase26_step4_position_sizing_authority.py tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py -q --tb=short
PASS: 38 passed

PYTHONPATH=src python3 -m pytest tests/runtime_v2/test_phase26_step5_runtime_planning_authority.py tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py tests/runtime_v2/test_phase17_bv10_historical_sell_execution_projection.py tests/runtime_v2/test_phase29_l7_sell_quantity_contract_materialization.py -q --tb=short
PASS: 20 passed

PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/pending/promotion.py src/ai_fund_lab_v2/runtime_v2/position_sizing_authority.py src/ai_fund_lab_v2/runtime_v2/planning_submit_feasibility.py
PASS

git diff --check
PASS
```

Note: the first `py_compile` attempt without `PYTHONPYCACHEPREFIX` failed because macOS Python tried to write bytecode under `/Users/negishi/Library/Caches`, which is outside the writable sandbox. Re-running with a tmp pycache prefix passed.

## Residuals

Codex did not run fresh/resume/long Historical validation by instruction.

The existing batch review coupling observed in L21T-J remains unchanged. The `24350` PASS item becoming batch-blocked when `30410` is item-review-required is out of scope for K.

L21T-F invalid BUY preservation/composition behavior was not changed. SELL planning authority and SELL quantity contracts were not changed.

## User Fresh Validation Command

Recommended focused fresh validation for the requested period:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-smoke \
  --start-date 2022-08-23 \
  --end-date 2022-09-16 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```
