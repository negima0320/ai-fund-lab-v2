# Phase30-AK9R12 - Fresh Runtime Pending Lifecycle Invocation Wiring Repair

## Primary Judgment

```text
CANONICAL_PENDING_LIFECYCLE_AUTHORITY_REUSED = YES
PRE_DATA_READINESS_PENDING_LIFECYCLE_INVOCATION_IMPLEMENTED = YES
ORCHESTRATION_DOES_NOT_REIMPLEMENT_LIFECYCLE_RULES = YES
DATA_READINESS_PENDING_LIFECYCLE_CIRCULAR_DEPENDENCY_REMOVED = YES
POST_EXECUTION_PENDING_LIFECYCLE_HOOK_PRESERVED = YES
AK9R8_EXPIRATION_SEMANTICS_PRESERVED = YES
DATA_READINESS_FAIL_CLOSED_PRESERVED = YES
MANDATORY_SELL_INDEPENDENCE_PRESERVED = YES
NEW_DAY_BUY_REQUIRES_FRESH_AUTHORITY = YES
STALE_REVIEW_PRIORITY_NOT_INHERITED = YES
CURRENT_STATE_UNCHANGED_BY_PRE_READINESS_LIFECYCLE = YES
REAL_RUNTIME_ORCHESTRATION_SENTINEL_ADDED = YES
REAL_ORCHESTRATION_DAY1_TO_DAY2_PASS = YES
REAL_ORCHESTRATION_INVALID_PENDING_FAIL_CLOSED = YES
SENTINEL_FRESH_INVOCATION_ORDER_MATCH = YES
ORCHESTRATION_FIDELITY = FULL
STRATEGY_AND_CAPITAL_CONVERSION_UNCHANGED = YES
PRODUCTION_RUNTIME_ORCHESTRATION_CHANGED = YES
PRODUCTION_STRATEGY_CHANGED = NO
KNOWN_RUNTIME_OR_AUTHORITY_DEFECT = NO
FRESH_VALIDATION_BLOCKERS = []
FRESH_20BD_VALIDATION_READY = YES
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_FOR_PARAMETER_SELECTION = FALSE
FRESH_HISTORICAL_EXECUTED_BY_CODEX = NO
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
```

## Repair

Phase30-AK9R12 wires the existing canonical Pending lifecycle authority into
the Production-common Runtime CLI before Data Readiness consumers inspect
Pending state.

Changed file:

```text
src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py
```

New behavior:

```text
if a data-readiness-gated job is about to evaluate Data Readiness
and an active Pending slot has target_session_date < business_date:
  invoke runtime_v2.pending.lifecycle_runner.run_pending_lifecycle_review()
  before evaluate_runtime_data_readiness()
```

The orchestration layer only decides that a stale active Pending needs lifecycle
review before the consumer gate. It does not decide whether to expire, consume,
preserve, or fail closed. Those decisions remain owned by
`runtime_v2.pending.lifecycle_runner`.

## Invocation Order

Required production-common sequence is now represented by the Runtime CLI:

```text
market_refresh
-> data_readiness job starts
-> pre_data_readiness_pending_lifecycle when required
-> runtime_data_readiness_gate
-> morning / sell_planning / submit / execution / current_valuation_refresh
```

For stale residual `BUY_ITEM_SCOPED_REVIEW` Pending, the pre-readiness lifecycle
stage clears the stale slot before Data Readiness evaluates Pending / Historical
Safety. This removes the circular dependency found in AK9R11.

## Preservation

Unchanged:

```text
Strategy
Candidate
Buy Quality
PM
PC
PS
AK7R sizing
Strategy cap
Safety cap
Cash allocation
Submit sizing
selected_position_amount semantics
Current Valuation semantics
```

The existing post-execution `runtime_test` lifecycle hook is preserved. It still
handles same-day post-execution terminalization cases driven by
`execution/pending_terminalization_evidence.json`.

## Sentinel

Added:

```text
tests/runtime_v2/test_phase30_ak9r12_pre_data_readiness_pending_lifecycle_orchestration.py
```

Positive sentinel:

```text
run_daily_operation.main --job data_readiness
-> pre_data_readiness_pending_lifecycle stage
-> STALE_NEXT_DAY_RESIDUAL_BUY_REVIEW_EXPIRED
-> runtime_data_readiness_gate READY
-> Current state unchanged
```

Negative sentinel:

```text
stale residual review Pending with unresolved reviewed SELL
-> pre_data_readiness_pending_lifecycle stage REVIEW_REQUIRED
-> runtime_data_readiness_gate is not reached
-> Pending remains REVIEW_REQUIRED / active
```

This replaces the AK9R10 fidelity gap for this boundary by exercising the real
Runtime CLI orchestration entrypoint instead of manually calling
`run_pending_lifecycle_review()` before Data Readiness.

## Tests

```text
env PYTHONPYCACHEPREFIX=/private/tmp/pycache-ak9r12 python3 -m compileall src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py tests/runtime_v2/test_phase30_ak9r12_pre_data_readiness_pending_lifecycle_orchestration.py tests/runtime_v2/test_phase30_ak9r10_full_day1_day2_pending_lifecycle.py src/ai_fund_lab_v2/runtime_v2/pending/lifecycle_runner.py src/ai_fund_lab_v2/runtime_v2/data_readiness.py
PASS

python3 -m pytest tests/runtime_v2/test_phase30_ak9r12_pre_data_readiness_pending_lifecycle_orchestration.py -q
2 passed

python3 -m pytest tests/runtime_v2/test_phase30_ak9r12_pre_data_readiness_pending_lifecycle_orchestration.py tests/runtime_v2/test_phase30_ak9r10_full_day1_day2_pending_lifecycle.py -q
4 passed

python3 -m pytest tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py -q
32 passed

python3 -m pytest tests/runtime_v2/test_phase15aq_runtime_data_readiness_gate.py tests/runtime_v2/test_phase17_bj_historical_daily_neutral_safety_authority.py -q
20 passed

python3 -m pytest tests/runtime_v2/test_phase17_ab_current_valuation_pre_gate_authority.py -q
15 passed

python3 -m pytest tests/runtime_v2/test_phase17_x_historical_sell_planning_authority.py -k 'ak9r4 or buy_item_scoped or mandatory' -q
3 passed, 14 deselected

python3 -m pytest tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py -k 'ak9r1 or ak8r or buy_item_scoped_review' -q
7 passed, 19 deselected

python3 -m pytest tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py tests/runtime_v2/test_phase26_step6_submit_guard_authority.py -k 'ak9r1b or ak3r2c1 or buy or sell or mandatory' -q
17 passed, 18 deselected

python3 -m pytest tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py tests/runtime_v2/test_phase15az_current_valuation_no_fill_producer.py -q
35 passed

python3 -m pytest tests/runtime_v2 -k 'mandatory_sell or buy_sell_independence or ak8r' -q
1 passed, 1624 deselected

python3 -m pytest tests/strategy/test_phase30_z_reentry_genuine_recovery.py tests/strategy/test_phase29_l21k_prior_exit_materialization.py -q
22 passed
```

## Historical

```text
FRESH_HISTORICAL_EXECUTED_BY_CODEX = NO
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
```

## Recommended Next Task

```text
User-operated fresh 20BD validation
```
