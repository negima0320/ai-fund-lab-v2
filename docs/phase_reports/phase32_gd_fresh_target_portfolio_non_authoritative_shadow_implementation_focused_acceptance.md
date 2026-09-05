# Phase32-GD Fresh Target Portfolio Non-Authoritative SHADOW Implementation / Focused Acceptance

## Objective

Implement the Phase32-GB/GC Fresh Target Portfolio architecture as a
non-authoritative SHADOW diagnostic only.

No Production Strategy, PM, PC target authority, Position Sizing, Runtime
Planning, Pending, Submit, Execution, Safety, broker, threshold, weight, rank,
or model behavior was intentionally changed.

## Implementation Summary

Implemented `fresh_target_portfolio_shadow.v1` in
`src/ai_fund_lab_v2/strategy/marginal_capital_value.py` and embedded it from
`build_capital_competition_framework` in
`src/ai_fund_lab_v2/strategy/portfolio_construction.py`.

The artifact reuses the existing unified marginal capital / NCU SHADOW input
and records:

- current PIT opportunity evidence;
- hard eligibility status and reason codes;
- history-neutral fresh target membership and weight;
- current actual weight and diagnostic delta;
- `BUY_NEW_CONTEXT`, `BUY_ADD_CONTEXT`, and `CASH` row labels;
- recent-exit bounded guard state;
- history-safety displays proving old ownership is not a target input;
- winner-protection conflict observability;
- PM/Safety terminal deterioration precedence;
- safety displays including no-loss, concentration, headroom, liquidity, lot,
  current-campaign deterioration, and G129 increment scope;
- Production-vs-SHADOW divergence classes;
- stability and turnover-pressure metrics placeholders for day-to-day
  measurement.

## Authority Contract

Fresh Target is SHADOW only:

```text
authoritative_consumer_count = 0
action_authority = false
quantity_authority = false
order_authority = false
production_allocation_consumer = false
production_ordering_consumer = false
production_sizing_consumer = false
runtime_planning_consumer = false
```

The builder also records:

```text
ncu_comparator_instance_count = 1
future_information_used = false
historical_outcome_used = false
capital_reservation_created = false
future_order_promise_created = false
```

## Inputs and Exclusions

Allowed target inputs are current PIT opportunity, Buy Quality, Entry,
continuation, downside/risk, current market/regime/risk, cash, headroom, lot,
and hard eligibility facts.

Forbidden direct target inputs are explicitly excluded from target membership
and weight:

- old ownership;
- old closed campaign;
- prior EXIT count;
- prior ADD count;
- average cost;
- realized PnL;
- old campaign PnL;
- old campaign age;
- future price/return;
- historical outcome.

Current position is used only as a delta source:

```text
fresh_target_weight - current_actual_weight
```

## Files Changed

- `src/ai_fund_lab_v2/strategy/marginal_capital_value.py`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `tests/strategy/test_phase32_gd_fresh_target_portfolio_shadow.py`
- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/02_architecture/strategy_intelligence_architecture_v1.md`
- `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`
- `docs/phase_reports/phase32_gd_fresh_target_portfolio_non_authoritative_shadow_implementation_focused_acceptance.md`

## Focused Validation

Commands executed:

```text
PYTHONPYCACHEPREFIX=/private/tmp/pycache-gd PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase32_gd_fresh_target_portfolio_shadow.py
```

Result:

```text
7 passed
```

```text
PYTHONPYCACHEPREFIX=/private/tmp/pycache-gd PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase32_dq_unified_marginal_capital_shadow.py tests/strategy/test_phase32_eh_pc_security_opportunity_shadow_consumer.py tests/strategy/test_phase32_ej_winner_position_size_adequacy_shadow.py
```

Result:

```text
17 passed
```

```text
PYTHONPYCACHEPREFIX=/private/tmp/pycache-gd PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase32_gd_fresh_target_portfolio_shadow.py tests/strategy/test_phase32_dq_unified_marginal_capital_shadow.py tests/strategy/test_phase32_ew_reentry_semantic_removal_recent_exit_guard.py tests/runtime_v2/test_phase32_ez_recent_exit_guard_materialization.py
```

Result:

```text
30 passed
```

```text
PYTHONPYCACHEPREFIX=/private/tmp/pycache-gd PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py::test_phase31_g129_buy_add_submit_uses_order_increment_not_position_scope_delta tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py::test_phase31_g129_buy_add_true_order_increment_mismatch_still_reviews
```

Result:

```text
2 passed
```

Additional ADD regression command:

```text
PYTHONPYCACHEPREFIX=/private/tmp/pycache-gd PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase31_g115_add_marginal_authoritative_binding.py tests/strategy/test_phase31_g117_normal_buy_scope_repair.py tests/strategy/test_phase31_g113_add_marginal_competition_shadow.py -k 'not actual_76470'
```

Result:

```text
21 passed, 1 deselected
```

The deselected test is an existing old-run artifact-dependent test. Running it
without deselection failed because
`reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260825T072702567342Z/daily/2022-12-06/strategy/portfolio_construction.json`
is no longer present after old artifact cleanup. The failure was a missing
fixture artifact, not a GD behavioral failure.

## Acceptance Metrics

```text
NCU_COMPARATOR_INSTANCE_COUNT = 1
AUTHORITATIVE_CONSUMER_COUNT = 0
ACTION_AUTHORITY = false
QUANTITY_AUTHORITY = false
ORDER_AUTHORITY = false
ADD_SAFETY_BYPASS_COUNT = 0
G129_REGRESSION_COUNT = 0
CAMPAIGN_IDENTITY_MISMATCH_COUNT = 0
RUNTIME_AUTHORITY_LEAK_COUNT = 0
FUTURE_INFORMATION_USED_COUNT = 0
STALE_CROSS_RUN_EVIDENCE_ACCEPTED_COUNT = 0
CLOSED_CAMPAIGN_LEAK_COUNT = 0
PERMANENT_HISTORY_PENALTY_SIGNAL_COUNT = 0
```

## Required Answers

```text
FRESH_TARGET_SHADOW_IMPLEMENTED = YES
SHADOW_ONLY_CONTRACT_PRESERVED = YES
NCU_COMPARATOR_INSTANCE_COUNT = 1
PRODUCTION_TARGET_AUTHORITY_CHANGED = NO
PRODUCTION_ACTION_AUTHORITY_CHANGED = NO
PRODUCTION_QUANTITY_AUTHORITY_CHANGED = NO
PM_AUTHORITY_CHANGED = NO
MCV_PRODUCTION_AUTHORITY_CHANGED = NO
PS_RUNTIME_AUTHORITY_CHANGED = NO
SAFETY_AUTHORITY_CHANGED = NO
REENTRY_PRODUCTION_SEMANTIC_CHANGED = NO
RECENT_EXIT_GUARD_PRESERVED = YES
OLD_OWNERSHIP_TARGET_INPUT = NO
CLOSED_CAMPAIGN_TARGET_INPUT = NO
PRIOR_EXIT_COUNT_TARGET_INPUT = NO
PRIOR_ADD_COUNT_TARGET_INPUT = NO
AVERAGE_COST_TARGET_INPUT = NO
CURRENT_POSITION_USED_ONLY_AS_DELTA_SOURCE = YES
WINNER_PROTECTION_CONFLICT_OBSERVABLE = YES
TERMINAL_DETERIORATION_PRECEDENCE = PM/SAFETY
ADD_SAFETY_BYPASS_COUNT = 0
G129_REGRESSION = NO
FUTURE_INFORMATION_USED = NO
HISTORICAL_OUTCOME_USED = NO
FOCUSED_REGRESSION_RESULT = PASS_WITH_ONE_OLD_ARTIFACT_DEPENDENT_TEST_DESELECTED
```

## Execution Restrictions Confirmation

```text
FRESH_RUN_EXECUTED = NO
RESUME_EXECUTED = NO
REPLAY_EXECUTED = NO
RECOVER_EXECUTED = NO
LONG_HISTORICAL_EXECUTED = NO
RUNTIME_STATE_MUTATED = NO
PENDING_MUTATED = NO
LEDGER_MUTATED = NO
PRODUCTION_CHANGED = NO
SHADOW_PRODUCTION_CONNECTED = NO
```

## Next Recommended Step

Run a user-operated focused or short Historical validation that materializes the
new `fresh_target_portfolio_shadow.v1` artifact and compares day-to-day target
stability, turnover pressure, Production-vs-SHADOW divergence, winner
protection conflicts, and recent-exit guard rows before considering any
Production design step.

## Final Judgment

PHASE32_GD_FRESH_TARGET_PORTFOLIO_NON_AUTHORITATIVE_SHADOW_IMPLEMENTED_FOCUSED_ACCEPTED
