# Phase29-J2 Fixed Cash Reserve Removal and Opportunity-Driven DCE Policy Repair Implementation

## Primary Judgment

PHASE29_J2_FIXED_CASH_RESERVE_REMOVED_OPPORTUNITY_DRIVEN_DCE_IMPLEMENTED_SHORT_REGRESSION_PASS_WITH_KNOWN_NON_J2_RUNTIME_PLANNING_REVIEW.

Fresh 100BD is not marked ready because one additional Runtime Planning regression outside J2 scope still fails.

## Implementation

Production files changed:

- `configs/strategy/dynamic_cash_exposure.json`
- `configs/safety/portfolio_limits.json`
- `src/ai_fund_lab_v2/strategy/dynamic_cash_exposure.py`

Test files changed:

- `tests/strategy/test_phase22_i_dynamic_cash_exposure.py`
- `tests/strategy/test_phase22_c_portfolio_policy.py`

## Policy Change

Strategy DCE active values changed from:

```text
baseline_target_cash_ratio = 0.20
baseline_target_gross_exposure_ratio = 0.80
minimum_cash_ratio = 0.12
maximum_gross_exposure_ratio = 0.88
```

to:

```text
baseline_target_cash_ratio = 0.00
baseline_target_gross_exposure_ratio = 1.00
minimum_cash_ratio = 0.00
maximum_gross_exposure_ratio = 1.00
```

The old values remain only as deprecated metadata in config.

Safety cash/exposure changed from:

```text
minimum_cash_ratio = 0.10
maximum_gross_exposure_ratio = 0.90
```

to:

```text
minimum_cash_ratio = 0.00
maximum_gross_exposure_ratio = 1.00
```

This is a cash-equity no-leverage boundary, not permission for margin or negative cash.

## Preserved Behavior

- J1 capacity contract preserved: DCE consumes `resolved_opportunity_capacity`.
- Legacy opportunity aliases are observable but no longer active fallback.
- Valid zero opportunity capacity remains valid.
- Unknown opportunity capacity remains fail-closed.
- Dynamic defensive cash remains active through market, breadth, volatility, risk posture, uncertainty, and low opportunity deltas.
- Strategy 0.18 concentration cap unchanged.
- Safety 0.25 concentration cap unchanged.
- Lot-first recycling, Pending, Broker, Corporate Action, Submit, SELL/REDUCE/EXIT logic unchanged.

## Regression

PASS:

```text
Focused DCE/PP: 30 passed
Broader J2 non-regression: 262 passed
py_compile: PASS
git diff --check: PASS
```

Known non-J2 failure in the additional Runtime Planning coverage set:

```text
tests/runtime_v2/test_phase26_step5_runtime_planning_authority.py::test_phase26_step5_buy_position_sizing_review_does_not_block_sell_planning
Observed: sell_planning_status = REVIEW_REQUIRED
Expected: PASS
```

This was not repaired because J2 explicitly forbids SELL and Accepted Generation changes.

## Fresh 100BD Gate

NOT READY until the known non-J2 Runtime Planning SELL/Accepted Generation review is resolved or explicitly waived.

Codex did not run fresh-run, resume, 100BD, or long Historical.

## Deliverables

- `reports/phase29_j2_fixed_cash_reserve_opportunity_driven_dce_policy_repair_implementation/implementation_summary.json`
- `reports/phase29_j2_fixed_cash_reserve_opportunity_driven_dce_policy_repair_implementation/policy_before_after.json`
- `reports/phase29_j2_fixed_cash_reserve_opportunity_driven_dce_policy_repair_implementation/authority_map_after.json`
- `reports/phase29_j2_fixed_cash_reserve_opportunity_driven_dce_policy_repair_implementation/config_change_log.json`
- `reports/phase29_j2_fixed_cash_reserve_opportunity_driven_dce_policy_repair_implementation/regression_results.json`
- `reports/phase29_j2_fixed_cash_reserve_opportunity_driven_dce_policy_repair_implementation/non_regression_matrix.json`
- `reports/phase29_j2_fixed_cash_reserve_opportunity_driven_dce_policy_repair_implementation/safety_invariants.json`
- `reports/phase29_j2_fixed_cash_reserve_opportunity_driven_dce_policy_repair_implementation/remaining_risks.json`
- `reports/phase29_j2_fixed_cash_reserve_opportunity_driven_dce_policy_repair_implementation/fresh_100bd_gate.json`
