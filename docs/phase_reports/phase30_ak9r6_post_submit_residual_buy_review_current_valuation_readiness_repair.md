# Phase30-AK9R6 - Post-Submit Residual BUY Review Current-Valuation Readiness Repair

## Scope

Task ID: `Phase30-AK9R6`

Type: `FOCUSED_PRODUCTION_COMMON_RUNTIME_AUTHORITY_REPAIR`

Authorized implementation scope:

```text
Current Valuation Data Readiness / Historical Safety recognition of valid
post-submit residual BUY_ITEM_SCOPED_REVIEW Pending
```

No Strategy, Candidate, Portfolio Construction, Position Sizing, Submit
quantity, cash pruning, Sell Planning policy, cap, threshold, fresh Historical,
or long Historical change was performed.

## Primary Judgment

```text
POST_SUBMIT_RESIDUAL_BUY_REVIEW_PENDING_RECOGNIZED = YES
CURRENT_VALUATION_RESIDUAL_BUY_REVIEW_CONTINUATION_ALLOWED = YES
RESIDUAL_REVIEWED_BUY_FAIL_CLOSED_PRESERVED = YES
APPROVED_FILLED_BUY_LIFECYCLE_RECOGNIZED = YES
VALUATION_READINESS_PENDING_SCOPE_SEPARATED = YES
```

The AK9R5 halt class `CROSS_REPAIR_INTERACTION_REGRESSION` is repaired for the
Current Valuation readiness boundary. A same-day pending artifact may remain
`REVIEW_REQUIRED` after partial BUY submission only when the approved BUY subset
is already `CONSUMED` and the residual BUY subset remains explicitly
`REVIEW_REQUIRED`.

That shape is recognized only for `readiness_scope = current_valuation`.
Residual reviewed BUY items are not approved, submitted, consumed, deleted, or
converted into no-ops.

## Repair Summary

`src/ai_fund_lab_v2/runtime_v2/data_readiness.py` now propagates
`readiness_scope` into Pending and Historical Safety authority evaluation.

A new Current Valuation scoped authority recognizes the valid post-submit
residual shape:

```text
review_scope = BUY_ITEM_SCOPED_REVIEW
approved_buy_item_ids present and disjoint from review_required_buy_item_ids
approved BUY items state = CONSUMED
review-required BUY items state = REVIEW_REQUIRED
review-required BUY items approved != true
review_required_sell_item_ids empty
blocked submit feasibility items are BUY-only non-cash review reasons
residual reviewed ids match remaining review-only BUY items
historical neutral safety metadata remains date/run/profile/evidence-root bound
```

Invalid shapes continue to fail closed:

```text
review BUY accidentally consumed
aggregate cash / reserved cash / buying power failure
unresolved reviewed SELL item
missing or corrupted historical safety authority
```

## Current Valuation Boundary

The repair separates:

```text
execution-blocking Pending
```

from:

```text
valuation-nonblocking residual BUY review
```

for Current Valuation only. The valuation producer can now execute for already
filled holdings while the residual reviewed BUY items remain review-only and
visible in the pending artifact.

## Preservation

```text
AK9R4_SELL_PLANNING_COMPATIBILITY_PRESERVED = YES
AK9R1_PARTIAL_SUBMISSION_PRESERVED = YES
AK9R1B_CANONICAL_QUANTITY_PRECEDENCE_PRESERVED = YES
CURRENT_VALUATION_NORMAL_FAIL_CLOSED_PRESERVED = YES
AK9R5_MISSING_POST_SUBMIT_VALUATION_SENTINEL_ADDED = YES
```

The new helper is not used to submit, consume, or promote reviewed BUY items.
Sell Planning's existing BUY-item-scoped continuation path remains separate.

## Tests

```text
python3 -m pytest tests/runtime_v2/test_phase17_ab_current_valuation_pre_gate_authority.py
15 passed

python3 -m pytest tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py -k 'ak9r1 or ak8r or buy_item_scoped_review'
7 passed, 19 deselected

python3 -m pytest tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py -k 'buy_item_scoped_review'
2 passed, 24 deselected

python3 -m pytest tests/runtime_v2 -k 'ak9r1b or ak9r4 or ak3r2c1 or ak7r'
10 passed, 1605 deselected

env PYTHONPYCACHEPREFIX=/private/tmp/pycache-ak9r6 python3 -m compileall src/ai_fund_lab_v2/runtime_v2/data_readiness.py tests/runtime_v2/test_phase17_ab_current_valuation_pre_gate_authority.py
PASS
```

The first compileall attempt with `python` failed because the command is not
installed. A `python3` compileall attempt without `PYTHONPYCACHEPREFIX` hit the
macOS user cache sandbox; the rerun using `/private/tmp` passed.

## Leakage

```text
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_FOR_PARAMETER_SELECTION = FALSE
```

## Historical

```text
FRESH_HISTORICAL_EXECUTED_BY_CODEX = NO
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
```

## Recommended Next Task

```text
Phase30-AK9R7 - User-Operated Fresh 5BD Current-Valuation Continuation Validation
```
