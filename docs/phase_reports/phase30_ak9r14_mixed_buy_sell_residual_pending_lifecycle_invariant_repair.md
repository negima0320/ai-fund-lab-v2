# Phase30-AK9R14 - Mixed BUY/SELL Residual Pending Lifecycle Invariant Repair

## Primary Judgment

```text
MIXED_BUY_SELL_RESIDUAL_PENDING_LIFECYCLE_GAP = REPAIRED
```

Phase30-AK9R14 repaired the Phase30-AK9R13 confirmed lifecycle gap where a
stale `BUY_ITEM_SCOPED_REVIEW` Pending containing consumed BUY items, consumed
SELL items, and residual reviewed BUY items failed closed only because the
historical composite plan was not BUY-only.

The repair is lifecycle-only. It does not change Candidate, Buy Quality,
PM, PC, PS, sizing, ranking, Strategy caps, Safety caps, Cash allocation,
Submit quantity, Current Valuation, or Data Readiness semantics.

## Canonical Invariant

```text
If all executable BUY/SELL items are terminal, no unresolved reviewed SELL
remains, and the only unresolved authority is stale non-submitted/non-filled
BUY_ITEM_SCOPED_REVIEW BUY items, the stale residual BUY review authority may
expire on the next business day.
```

The canonical question is now:

```text
What unresolved execution authority remains?
```

The previous shape-specific question:

```text
Was every item in this Pending plan originally BUY?
```

is no longer a gating invariant for this authority.

## Implementation

Updated:

```text
src/ai_fund_lab_v2/runtime_v2/pending/lifecycle_runner.py
```

The stale residual BUY review expiration authority now classifies:

```text
resolved terminal items:
  approved BUY state=CONSUMED
  approved SELL state=CONSUMED

unresolved items:
  REVIEW_REQUIRED BUY ids
  REVIEW_REQUIRED SELL ids
```

It expires only when:

```text
state = REVIEW_REQUIRED
review_scope = BUY_ITEM_SCOPED_REVIEW
target_session_date < current business_date
approved/review ids are disjoint and internally consistent
all approved BUY items are known and CONSUMED
all approved SELL items are known and CONSUMED
all approved executable BUY/SELL items are terminal
review_required_sell_item_ids is empty
known REVIEW_REQUIRED item ids exactly match review ids
reviewed BUY items remain REVIEW_REQUIRED and unapproved
reviewed BUY items have no submit/fill evidence
the whole plan is not already consumed
```

The explicit `all_items_buy` gating check was removed from the stale
next-day residual BUY review expiration authority.

## AK9R13 Equivalent Sentinel

Added:

```text
test_phase30_ak9r14_mixed_consumed_buy_sell_residual_buy_review_expires
```

Covered shape:

```text
BUY CONSUMED = 5
SELL CONSUMED = 5
BUY REVIEW_REQUIRED = 6
SELL REVIEW_REQUIRED = 0
```

Result:

```text
AK9R13_MIXED_PENDING_SENTINEL_PASS = YES
terminal_state = EXPIRED
reviewed BUY submitted = FALSE
reviewed BUY filled = FALSE
reviewed BUY auto-approved = FALSE
history preserved = YES
```

## Negative Sentinels

Added fail-closed sentinels:

```text
test_phase30_ak9r14_mixed_unresolved_reviewed_sell_fails_closed
test_phase30_ak9r14_mixed_unconsumed_sell_fails_closed
test_phase30_ak9r14_reviewed_buy_fill_evidence_fails_closed
test_phase30_ak9r14_malformed_mixed_pending_id_overlap_fails_closed
```

Existing AK9R8 negative sentinels continue to cover:

```text
approved BUY not consumed
reviewed BUY submitted
reviewed SELL exists
same-day review visibility
```

## Preservation

```text
CONSUMED_BUY_SELL_ITEMS_TREATED_AS_TERMINAL = YES
UNRESOLVED_ITEM_CLASSIFICATION_IMPLEMENTED = YES
MIXED_CONSUMED_BUY_SELL_RESIDUAL_BUY_EXPIRATION_IMPLEMENTED = YES
CONSUMED_SELL_DOES_NOT_BLOCK_RESIDUAL_BUY_EXPIRATION = YES
UNRESOLVED_REVIEWED_SELL_FAIL_CLOSED_PRESERVED = YES
BUY_SELL_LIFECYCLE_INDEPENDENCE_ACTION_EFFECTIVE = YES
MANDATORY_SELL_INDEPENDENCE_PRESERVED = YES
REVIEWED_BUY_NOT_AUTO_APPROVED = YES
REVIEWED_BUY_NOT_AUTO_SUBMITTED = YES
REVIEWED_BUY_NOT_AUTO_FILLED = YES
REVIEWED_BUY_HISTORY_PRESERVED = YES
NEW_DAY_BUY_REQUIRES_FRESH_AUTHORITY = YES
STALE_REVIEW_PRIORITY_NOT_INHERITED = YES
CURRENT_STATE_AND_EXECUTION_HISTORY_PRESERVED = YES
AK9R8_BUY_ONLY_EXPIRATION_PRESERVED = YES
AK9R12_PRE_DATA_READINESS_WIRING_PRESERVED = YES
PENDING_LIFECYCLE_INVARIANT_DOCUMENTED = YES
```

## Decision-to-Fill Preservation

```text
NEW_BUY_FILTER_CREATED = NO
NEW_ADD_FILTER_CREATED = NO
PC_PS_EXECUTABLE_QUANTITY_UNCHANGED = YES
SUBMIT_VALID_BUY_BEHAVIOR_UNCHANGED = YES
PRODUCTION_STRATEGY_CHANGED = NO
```

The repair does not create an upstream BUY/ADD filter. It only decides whether
a stale residual reviewed BUY Pending may be expired after all executable BUY
and SELL items from the previous session are already terminal.

## Tests

```text
env PYTHONPYCACHEPREFIX=/private/tmp/pycache-ak9r14 python3 -m compileall \
  src/ai_fund_lab_v2/runtime_v2/pending/lifecycle_runner.py \
  tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py
PASS

python3 -m pytest tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py -k 'ak9r8 or ak9r14' -q
PASS - 11 passed, 26 deselected

python3 -m pytest tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py -q
PASS - 37 passed

python3 -m pytest \
  tests/runtime_v2/test_phase30_ak9r12_pre_data_readiness_pending_lifecycle_orchestration.py \
  tests/runtime_v2/test_phase30_ak9r10_full_day1_day2_pending_lifecycle.py -q
PASS - 4 passed

python3 -m pytest \
  tests/runtime_v2/test_phase15aq_runtime_data_readiness_gate.py \
  tests/runtime_v2/test_phase15as_data_readiness_semantic_consistency.py -q
PASS - 18 passed

python3 -m pytest \
  tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py \
  tests/runtime_v2/test_phase28_d8_sell_pending_authority_merge.py \
  tests/runtime_v2/test_phase28_d3_sell_pending_reconciliation.py -q
PASS - 23 passed

python3 -m pytest \
  tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py \
  tests/runtime_v2/test_phase13_q_fill_classifier.py \
  tests/runtime_v2/test_phase15az_current_valuation_no_fill_producer.py \
  tests/runtime_v2/test_phase17_ab_current_valuation_pre_gate_authority.py \
  tests/runtime_v2/test_phase17_aa_historical_current_valuation_authority.py -q
PASS - 68 passed

python3 -m pytest \
  tests/runtime_v2/test_phase29_l7_sell_quantity_contract_materialization.py \
  tests/runtime_v2/test_phase17_x_historical_sell_planning_authority.py \
  tests/runtime_v2/test_phase17_ag_day2_sell_planning_integration.py \
  tests/runtime_v2/test_phase15m_sell_broker_available_quantity_evidence.py -q
PASS - 43 passed

python3 -m pytest \
  tests/runtime_v2/test_phase26_step5_runtime_planning_authority.py \
  tests/runtime_v2/test_phase26_step6_submit_guard_authority.py -q
PASS - 15 passed

python3 -m pytest \
  tests/strategy/test_phase30_z_reentry_genuine_recovery.py \
  tests/strategy/test_phase29_l21k_prior_exit_materialization.py -q
PASS - 22 passed

python3 -m pytest \
  tests/runtime_v2/test_phase17_bh_current_valuation_refresh_temporal_contract.py \
  tests/runtime_v2/test_phase17_bv12_current_valuation_symbol_identity.py \
  tests/runtime_v2/test_phase17_bv10_historical_sell_execution_projection.py \
  tests/runtime_v2/test_phase17_bv9_historical_sell_quantity_authority.py -q
PASS - 21 passed
```

Initial compileall without `PYTHONPYCACHEPREFIX` hit the local macOS Python
cache permission boundary under `~/Library/Caches`. The same compile target
passed with pycache directed to `/private/tmp`.

## Final Required Judgments

```text
CONSUMED_BUY_SELL_ITEMS_TREATED_AS_TERMINAL = YES
UNRESOLVED_ITEM_CLASSIFICATION_IMPLEMENTED = YES
MIXED_CONSUMED_BUY_SELL_RESIDUAL_BUY_EXPIRATION_IMPLEMENTED = YES
CONSUMED_SELL_DOES_NOT_BLOCK_RESIDUAL_BUY_EXPIRATION = YES
UNRESOLVED_REVIEWED_SELL_FAIL_CLOSED_PRESERVED = YES
BUY_SELL_LIFECYCLE_INDEPENDENCE_ACTION_EFFECTIVE = YES
MANDATORY_SELL_INDEPENDENCE_PRESERVED = YES
REVIEWED_BUY_NOT_AUTO_APPROVED = YES
REVIEWED_BUY_NOT_AUTO_SUBMITTED = YES
REVIEWED_BUY_NOT_AUTO_FILLED = YES
REVIEWED_BUY_HISTORY_PRESERVED = YES
NEW_DAY_BUY_REQUIRES_FRESH_AUTHORITY = YES
STALE_REVIEW_PRIORITY_NOT_INHERITED = YES
CURRENT_STATE_AND_EXECUTION_HISTORY_PRESERVED = YES
AK9R8_BUY_ONLY_EXPIRATION_PRESERVED = YES
AK9R12_PRE_DATA_READINESS_WIRING_PRESERVED = YES
AK9R13_MIXED_PENDING_SENTINEL_PASS = YES
PENDING_LIFECYCLE_INVARIANT_DOCUMENTED = YES
NEW_BUY_FILTER_CREATED = NO
NEW_ADD_FILTER_CREATED = NO
PC_PS_EXECUTABLE_QUANTITY_UNCHANGED = YES
SUBMIT_VALID_BUY_BEHAVIOR_UNCHANGED = YES
PRODUCTION_STRATEGY_CHANGED = NO
KNOWN_RUNTIME_OR_AUTHORITY_DEFECT = YES
FRESH_VALIDATION_BLOCKERS = []
FRESH_20BD_VALIDATION_READY = YES
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_FOR_PARAMETER_SELECTION = FALSE
FRESH_HISTORICAL_EXECUTED_BY_CODEX = NO
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
```

## Recommended Next Task

```text
User-operated fresh 20BD validation
```
