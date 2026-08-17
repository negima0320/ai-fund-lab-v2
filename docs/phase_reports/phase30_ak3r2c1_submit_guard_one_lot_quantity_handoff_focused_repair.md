# Phase30-AK3R2C1 - Submit Guard One-Lot Quantity Handoff Focused Repair

## Task

`Phase30-AK3R2C1`

## Objective

Repair the focused `one_lot_authority_quantity_mismatch` confirmed by
Phase30-AK3R2C0. The repair is limited to the Submit guard canonical executable
quantity handoff.

## Primary Judgment

```text
SUBMIT_GUARD_ONE_LOT_QUANTITY_HANDOFF_REPAIRED = YES
CANONICAL_EXECUTABLE_QUANTITY_PROPAGATED = YES
AUTHORIZED_ONE_LOT_QUANTITY_REVALIDATION_PASS = YES
TRUE_QUANTITY_MISMATCH_REVIEW_PRESERVED = YES
NORMAL_BUY_SUBMIT_GUARD_PRESERVED = YES
AK3R2B_CASH_FEASIBLE_BATCH_PRESERVED = YES
SUBMIT_FINAL_FAIL_CLOSED_PRESERVED = YES
STRATEGY_CAP_PRESERVED = YES
SAFETY_HARD_CAP_PRESERVED = YES
FUTURE_INFORMATION_USED = FALSE
```

## Repair

`runtime_v2.submit.pipeline._buy_guard_evidence()` now passes the canonical
Pending executable `quantity` into the synthetic `SubmitGuardItem` used for
Submit guard revalidation.

The handoff chain is now:

```text
Pending canonical quantity
-> SubmitGuardItem.quantity
-> planning_submit_feasibility._one_lot_submit_authority()
-> quantity == discrete_authorized_quantity
-> PASS
```

The repair does not recompute quantity and does not introduce a new authority.
It reuses the canonical Pending evidence already materialized before Submit.

## Canonical Quantity Handoff

The synthetic Submit guard item now carries:

```text
quantity
estimated_price
reference_price
reservation_price
reservation_price_authority
reservation_reason
reserved_notional
quantity_contract
```

The required repair field is:

```text
quantity = evidence["quantity"]
```

The other fields preserve existing reserved-notional and reference-price
authority during the same revalidation path.

## Mandatory Sentinels

```text
CASE_1_AUTHORIZED_ONE_LOT = PASS
CASE_2_TRUE_QUANTITY_MISMATCH = REVIEW_REQUIRED
CASE_3_MISSING_AUTHORITY = PRESERVED_BY_EXISTING_AK3R1_SENTINELS
CASE_4_TAMPERED_QUANTITY = FAIL_CLOSED
CASE_5_NORMAL_LEGACY_BUY = BEHAVIOR_UNCHANGED
CASE_6_AK3R2B_CASH_PRUNED_ITEM = NOT_SUBMIT_GUARD_REVALIDATED
```

## Preservation

```text
AK2_ONE_LOT_AUTHORITY_PRESERVED = YES
AK3R1_SUBMIT_HANDOFF_PRESERVED = YES
AK3R2B_CASH_FEASIBLE_BATCH_PRESERVED = YES
UNAUTHORIZED_QUANTITY_MISMATCH_REVIEW_PRESERVED = YES
NORMAL_BUY_SUBMIT_GUARD_PRESERVED = YES
SUBMIT_FINAL_FAIL_CLOSED_PRESERVED = YES
STRATEGY_CAP_PRESERVED = YES
SAFETY_HARD_CAP_PRESERVED = YES
```

No Strategy, Candidate, Portfolio Construction target, Position Sizing
semantics, cap, Safety, or cash pruning behavior was changed.

## Tests

```text
compileall src/ai_fund_lab_v2/runtime_v2 src/ai_fund_lab_v2/strategy = PASS

tests/runtime_v2/test_phase26_step6_submit_guard_authority.py = 11 passed
tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py
tests/runtime_v2/test_phase30_ak3r2b_cash_feasible_buy_batch.py = 27 passed
tests/runtime_v2/test_phase26_step4_position_sizing_authority.py
tests/strategy/test_phase30_w_entry_one_lot_repair.py
tests/strategy/test_phase22_j_position_sizing.py = 117 passed
tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py = 24 passed
```

Additional validation:

```text
JSON_VALIDATION = PASS
git diff --check = PASS
```

## Historical

```text
FRESH_HISTORICAL_EXECUTED_BY_CODEX = NO
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
```

## Implementation Authorization

```text
IMPLEMENTATION_AUTHORIZED_ONLY_FOR = Submit guard canonical executable quantity handoff
```

## Recommended Next Task

```text
Phase30-AK3R2C2 - User-Operated Fresh 5BD End-to-End Validation
```
