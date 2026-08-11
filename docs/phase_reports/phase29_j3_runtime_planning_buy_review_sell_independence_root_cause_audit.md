# Phase29-J3 Runtime Planning BUY Review / SELL Independence Root Cause Audit

## Primary Judgment

PHASE29_J3_RUNTIME_PLANNING_BUY_REVIEW_SELL_INDEPENDENCE_STALE_FIXTURE_CONFIRMED.

## Classification

Primary classification: J3-B — STALE_TEST_FIXTURE.

The failure is not caused by Phase29-J2, Phase29-J1, or BUY-side review propagation into SELL. The failing Phase26 fixture does not create the current required `strategy/input_manifest.json` with `strategy_source_authority` and canonical `listed_issues` source records.

## Reproduction

Command:

```text
PYTHONPATH=src PYTHONPYCACHEPREFIX=/tmp/ai-fund-lab-v2-pycache python3 -m pytest tests/runtime_v2/test_phase26_step5_runtime_planning_authority.py::test_phase26_step5_buy_position_sizing_review_does_not_block_sell_planning -vv
```

Result:

```text
FAILED
Observed sell_planning_status = REVIEW_REQUIRED
Expected sell_planning_status = PASS
```

## Root Cause

Runtime Planning produces both sides:

- BUY `31330`: `BUY_NEW`, quantity resolved.
- SELL `7203`: `SELL_EXIT`, current quantity 100, planned quantity 100, price authority PASS.

The SELL plan then fails pending-item materialization in:

```text
src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py::_pending_item_from_strategy_plan
```

The branch is:

```text
if side == "SELL" and listed_info is None
```

The reason code is:

```text
strategy_sell_canonical_listed_info_authority_missing:7203
```

The missing authority comes from:

```text
_canonical_listed_info_from_strategy_source_authority
```

because the fixture has no `strategy/input_manifest.json`.

## Accepted Generation

Accepted Generation is involved but not the direct SELL failure cause.

Observed binding:

```text
generation_binding_status = REVIEW_REQUIRED
selection_reason = strategy_input_manifest_missing
```

This makes the generated BUY pending item and pending plan REVIEW_REQUIRED, but SELL item generation fails earlier due to missing canonical listed-info authority.

## Fixture Probe

I ran a temporary probe without changing repo files: the same fixture plus current-contract `input_manifest.json` and canonical `listed_issues` authority.

Result:

```text
buy_planning_status = PASS
sell_planning_status = PASS
pending_sell_items_status = PASS
sell_continuation_allowed = true
```

The BUY Accepted Generation review remained present, proving BUY review itself does not block valid SELL when the SELL-side authority is complete.

## Neighbor Regressions

```text
tests/runtime_v2/test_phase26_step5_runtime_planning_authority.py
3 passed, 1 failed
```

```text
tests/runtime_v2/test_phase28_d3_sell_pending_reconciliation.py
tests/runtime_v2/test_phase28_d8_sell_pending_authority_merge.py
tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py
tests/runtime_v2/test_phase17_bv9_historical_sell_quantity_authority.py
tests/runtime_v2/test_phase27_d6d_pm_hold_exit_boundary.py
tests/runtime_v2/test_phase23_i_strategy_planning_authority.py
tests/runtime_v2/test_phase23_ab_no_order_submit_guard.py
63 passed
```

## J2 / J1 Causality

J2 causal: NO.

J1 causal: NO.

No J2 DCE cash/exposure policy branch or J1 opportunity-capacity branch is on the failing path.

## Fresh 100BD Gate

Fresh 100BD Ready: NO.

The failure is non-production and fixture-stale, but the regression suite still contains the failing fixture. Repair the fixture in J4, then rerun short regression before user-operated 100BD.

## Recommended Next Task

Phase29-J4 Stale Runtime Planning Fixture Repair.
