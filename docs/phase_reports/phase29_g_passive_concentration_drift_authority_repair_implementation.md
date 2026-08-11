# Phase29-G Passive Concentration Drift Authority Repair Implementation

## Status

COMPLETE

Judgment:

```text
PHASE29_G_PASSIVE_CONCENTRATION_DRIFT_AUTHORITY_REPAIR_IMPLEMENTED_SHORT_REGRESSION_PASS_FRESH_100BD_READY
```

No fresh run, resume, 100BD, or long Historical execution was performed.

## Objective

Phase29-G separates passive valuation drift above the independent Safety concentration cap from active BUY/ADD risk increase.

The repair allows an existing position to be retained above Safety cap only when the position is directionally non-increasing: existing quantity is present, PM is HOLD or ADD, membership is RETAIN, accepted incremental weight is zero, target quantity does not exceed current quantity, and the target weight is the retained current or baseline valuation.

This does not rewrite PM ADD into HOLD. PM intent remains observable while executable ADD quantity can be zero.

## Implementation

Changed production file:

```text
src/ai_fund_lab_v2/strategy/position_sizing.py
```

Implemented behavior:

- Position Sizing now passes `safety_cap` into raw position materialization.
- Passive drift above Safety cap emits `PASSIVE_CONCENTRATION_DRIFT_RETAINED` and `SAFETY_CAP_DRIFT_NO_RISK_INCREASE`.
- REDUCE above Safety cap with non-increasing risk emits `SAFETY_CAP_DRIFT_RISK_REDUCING_TRANSACTION_ALLOWED`.
- Producer-level `produced_position_weight_above_safety_cap` aggregation now uses the same directional exception predicate as schema validation.
- Active risk increases remain fail-closed.

Numeric caps were not changed:

```text
strategy_maximum_position_weight = 0.18
safety_maximum_position_weight = 0.25
```

## Regression Coverage

Added focused Phase29-G tests in:

```text
tests/strategy/test_phase22_j_position_sizing.py
```

Covered cases:

- PM ADD passive drift above Safety cap retained.
- PM HOLD passive drift above Safety cap retained.
- ADD from below cap to above cap remains blocked.
- Already-over-cap ADD that further increases risk remains blocked.
- REDUCE from above Safety cap remains executable.
- EXIT from above Safety cap remains executable.
- BUY_NEW cap behavior remains capped.
- Missing current quantity does not qualify for passive drift.
- Passive drift does not invalidate unrelated BUY quantity authority.
- Safety cap boundary tolerance is preserved.

## Validation

```text
PYTHONPATH=src PYTHONPYCACHEPREFIX=/tmp/ai-fund-lab-v2-pycache python3 -m pytest tests/strategy/test_phase22_j_position_sizing.py -k 'phase29_g or phase28_d36 or phase28_d69 or phase28_d61' -q
19 passed, 55 deselected
```

```text
PYTHONPATH=src PYTHONPYCACHEPREFIX=/tmp/ai-fund-lab-v2-pycache python3 -m pytest tests/strategy/test_phase22_j_position_sizing.py -q
74 passed
```

```text
PYTHONPATH=src PYTHONPYCACHEPREFIX=/tmp/ai-fund-lab-v2-pycache python3 -m pytest tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase22_g_runtime_planning.py tests/runtime_v2/test_phase23_i_strategy_planning_authority.py tests/runtime_v2/test_phase23_ab_no_order_submit_guard.py tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py tests/runtime_v2/test_phase28_d3_sell_pending_reconciliation.py tests/runtime_v2/test_phase28_d8_sell_pending_authority_merge.py tests/runtime_v2/test_phase17_bv9_historical_sell_quantity_authority.py tests/runtime_v2/test_phase15bm_safety_blocked_submit_path.py tests/runtime_v2/test_phase17_bj_historical_daily_neutral_safety_authority.py tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py tests/runtime_v2/test_phase19_bi_empty_pending_no_action_contract.py tests/ai_lifecycle/test_phase19_ad_u2_d_corporate_action_policy_approval.py tests/strategy/test_phase22_aa_corporate_event.py tests/order_manager/test_broker_snapshot_loader.py -q
304 passed
```

```text
PYTHONPYCACHEPREFIX=/tmp/ai-fund-lab-v2-pycache python3 -m py_compile src/ai_fund_lab_v2/strategy/position_sizing.py tests/strategy/test_phase22_j_position_sizing.py
PASS
```

## Conclusion

Phase29-G is implemented and short regression is green. Passive concentration drift is now retained without forcing SELL/REDUCE/EXIT or halting unrelated Strategy Planning, while active BUY/ADD risk increases remain blocked.

Fresh 100BD validation is ready for the operator-approved next step.
