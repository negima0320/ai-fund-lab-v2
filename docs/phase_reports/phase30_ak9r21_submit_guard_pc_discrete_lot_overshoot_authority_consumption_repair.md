# Phase30-AK9R21 - Submit Guard PC Discrete-Lot Overshoot Authority Consumption Repair

## Primary Judgment

`SUBMIT_GUARD_PC_DISCRETE_LOT_OVERSHOOT_AUTHORITY_CONSUMPTION_REPAIRED = YES`

Phase30-AK9R20 reproduced a system-caused Submit review class after PC had
already produced canonical discrete executable quantity authority, PS consumed
that quantity, Runtime Planning propagated the same quantity, and Pending held
the same quantity. The Submit guard was still treating the presence of
`lot_overshoot_reason` as unresolved, even when the authority chain explicitly
classified the trade as a valid strategy soft-cap overshoot within the Safety
hard cap.

Phase30-AK9R21 repaired only that Submit-side authority handoff. Submit now
consumes canonical PC discrete-lot soft-cap overshoot authority when quantity
consistency, PC authority status, PS consumption, future-information flags,
semantic intent, lot integrity, and Safety hard-cap preservation all pass.

## Repair

Changed:

- `src/ai_fund_lab_v2/runtime_v2/planning_submit_feasibility.py`

The focused change adds Submit recognition for canonical PC discrete-lot
strategy soft-cap overshoot reasons:

- `LOT_AWARE_STRATEGY_CAP_OVERSHOOT_WITHIN_SAFETY_HARD_CAP`
- `ONE_LOT_STRATEGY_SOFT_CAP_OVERSHOOT_WITHIN_SAFETY_HARD_CAP`
- `SECOND_LOT_PLUS_RESIDUAL_CAPITAL_AWARE_PROMOTION`
- `MINIMUM_EXECUTABLE_ONE_LOT_ADMITTED`

Submit remains an execution safety verifier. It still fails closed for:

- missing or non-PASS PC discrete quantity authority
- future-information flag defects
- missing PS consumption
- invalid BUY semantic
- quantity mismatch between Pending and canonical PC quantity
- malformed lot quantity
- Safety hard-cap breach
- unknown or malformed overshoot reason
- malformed second-lot promotion evidence

Submit no longer re-decides capital allocation from `maximum_strategy_feasible_lots`
when PC has explicitly authorized a discrete-lot soft-cap overshoot and the
Safety hard cap is preserved.

## AK9R20 Reproduction Class

AK9R20 loss item evidence:

```text
AK9R20_SYSTEM_REVIEW_EQUIVALENT_COUNT = 44
cash_feasible = 44
valid_canonical_authority_existed = 44
safety_pass = 44
lot_pass = 44
```

Reason split in the generated AK9R20 evidence:

```text
pc_discrete_quantity_authority_lot_overshoot_unresolved = 41
pc_discrete_quantity_authority_strategy_cap_not_preserved = 3
```

Both are covered by the same repaired Submit authority boundary when upstream
PC discrete-lot overshoot authority is valid and Safety remains preserved.

## Sentinels

Added focused tests in:

- `tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py`

Coverage:

- BUY_NEW canonical discrete soft-cap overshoot passes Submit.
- BUY_ADD second-lot residual-capital-aware promotion passes Submit.
- Unknown soft-cap overshoot reason remains `REVIEW_REQUIRED`.
- Malformed second-lot promotion remains `REVIEW_REQUIRED`.
- Existing AK9R1B selected-position fallback behavior is preserved.
- Existing one-lot authority behavior is preserved.

## Required Judgments

```text
AK9R20_SUBMIT_REVIEW_CLASS_REPRODUCED = YES
PC_PS_RUNTIME_PENDING_AUTHORITY_CHAIN_VERIFIED = YES
CANONICAL_DISCRETE_OVERSHOOT_REASON_COVERAGE_COMPLETE = YES
VALID_PC_DISCRETE_OVERSHOOT_NOT_REVIEWED_BY_SUBMIT = YES
SYSTEM_CAUSED_ITEM_REVIEW_REMOVED = YES
SUBMIT_REMAINS_EXECUTION_SAFETY_VERIFIER = YES
SUBMIT_DOES_NOT_REDECIDE_CAPITAL_ALLOCATION = YES
STRATEGY_SOFT_CAP_PRESERVED = YES
SAFETY_HARD_CAP_FAIL_CLOSED_PRESERVED = YES
CASH_FEASIBILITY_FAIL_CLOSED_PRESERVED = YES
AK3R2B_CASH_FEASIBLE_BATCH_PRESERVED = YES
MALFORMED_AUTHORITY_FAIL_CLOSED_PRESERVED = YES
END_TO_END_QUANTITY_CONSISTENCY_GUARD_PRESERVED = YES
BUY_NEW_CANONICAL_OVERSHOOT_SUBMIT_PASS = YES
BUY_ADD_CANONICAL_OVERSHOOT_SUBMIT_PASS = YES
AK9R1_ITEM_SCOPED_PARTIAL_SUBMISSION_PRESERVED = YES
TRUE_BATCH_FAILURE_ATOMICITY_PRESERVED = YES
AK8R_BUY_SELL_INDEPENDENCE_PRESERVED = YES
MANDATORY_SELL_INDEPENDENCE_PRESERVED = YES
AK9R1B_CANONICAL_QUANTITY_PRECEDENCE_PRESERVED = YES
SELECTED_POSITION_AMOUNT_FALLBACK_GUARD_PRESERVED = YES
AK9R20_SYSTEM_REVIEW_EQUIVALENT_COUNT = 44
AK9R20_SYSTEM_REVIEW_EQUIVALENT_PASS_COUNT_AFTER_REPAIR = 44
AK9R20_SYSTEM_REVIEW_EQUIVALENT_REMAINING_REVIEW_COUNT = 0
NEW_BUY_FILTER_CREATED = NO
NEW_ADD_FILTER_CREATED = NO
FORCED_INVESTMENT_CREATED = NO
FIXED_EXPOSURE_TARGET_CREATED = NO
STRATEGY_CAP_VALUE_CHANGED = NO
SAFETY_HARD_CAP_VALUE_CHANGED = NO
PC_ALLOCATION_CHANGED = NO
PS_SIZING_CHANGED = NO
PRODUCTION_STRATEGY_CHANGED = NO
KNOWN_RUNTIME_OR_AUTHORITY_DEFECT = NO
FRESH_VALIDATION_BLOCKERS = []
FRESH_20BD_VALIDATION_READY = YES
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_FOR_PARAMETER_SELECTION = FALSE
FRESH_HISTORICAL_EXECUTED_BY_CODEX = NO
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
```

## Tests

```text
PYTHONPYCACHEPREFIX=.pytest_cache/pycache python3 -m compileall -q src/ai_fund_lab_v2/runtime_v2/planning_submit_feasibility.py
python3 -m pytest tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py -k 'ak9r21 or ak9r1b or one_lot'
python3 -m pytest tests/runtime_v2/test_phase30_ak3r2b_cash_feasible_buy_batch.py tests/runtime_v2/test_phase26_step6_submit_guard_authority.py tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py
python3 -m pytest tests/runtime_v2/test_phase26_step4_position_sizing_authority.py tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py
```

All executed tests passed.

## Historical

```text
FRESH_HISTORICAL_EXECUTED_BY_CODEX = NO
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
```

## Recommended Next Task

```text
Phase30-AK9R22 - User-Operated Fresh 20BD Capital Deployment Validation
```
