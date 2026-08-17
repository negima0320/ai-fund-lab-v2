# Phase30-AK9R1 - Non-Cash BUY Review Batch Submit Boundary Focused Repair

Task ID: `Phase30-AK9R1`

Type: `FOCUSED_PRODUCTION_COMMON_RUNTIME_REPAIR`

## Primary Judgment

```text
NON_CASH_BUY_REVIEW_BATCH_BOUNDARY_REPAIRED = YES
```

Phase30-AK9R1 repaired the AK9R0-confirmed
`SUBMIT_BUY_ITEM_SCOPED_REVIEW_ATOMIC_BATCH_NO_SUBMISSION_REGRESSION`.

The repaired boundary is deliberately narrow:

- non-cash item-scoped `REVIEW_REQUIRED` BUY items stay fail-closed and are not
  submitted;
- independently approved/PASS BUY items in the same pending plan remain
  submit-eligible;
- reviewed BUY evidence remains visible in submit output;
- true batch-level failures, including cash/aggregate-cash review, still
  fail-closed.

No Candidate, PM, PC ranking, AK7R sizing, Strategy/Safety cap, cash-pruning,
same-day SELL proceeds, or Current Valuation behavior was changed.

## Root Cause Authority

Primary root cause authority remains:

```text
docs/phase_reports/phase30_ak9r0_post_ak9_fresh_zero_buy_regression_root_cause_audit.md
```

AK9R0 showed that a fresh run produced 16 pending BUY items on 2022-08-10:

```text
PASS-like / cash-feasible subset = 8
non-cash position_sizing REVIEW_REQUIRED = 8
submitted_count = 0
```

Submit treated the reviewed BUY items as atomic BUY batch blockers via
`BUY_ITEM_SCOPED_REVIEW_NO_SUBMISSION`, preventing otherwise valid PASS BUY
items from reaching the broker boundary.

## Repair Summary

### Pending Approval / Promotion

`runtime_v2.pending.promotion.attach_approval_link()` now preserves approved
PASS item IDs for `BUY_ITEM_SCOPED_REVIEW` only when the review is non-cash.
Those items are materialized as:

```text
approved = true
state = APPROVED
feasibility_status = PASS
batch_submit_status = PASS_ITEM_SUBMITTABLE
```

Reviewed BUY items remain:

```text
approved = false
state = REVIEW_REQUIRED
batch_submit_status = ITEM_REVIEW_REQUIRED
```

Cash review items are explicitly excluded from partial approval and keep the
previous fail-closed batch behavior.

### Submit Boundary

Submit now allows `PendingPlanState.REVIEW_REQUIRED` only for the narrow
submittable shape:

```text
review_scope = BUY_ITEM_SCOPED_REVIEW
approval = APPROVED
approved_item_ids non-empty
approved_item_ids do not intersect reviewed ids
review_required_sell_item_ids empty
no reviewed item has violated_policy = cash / reserved_cash / aggregate_cash
```

The submit pipeline submits approved PASS items through normal preflight,
final guard, adapter preflight, and adapter submit. It does not recalculate
quantity or bypass existing submit guards.

Reviewed BUY items are appended to submit evidence as not-submitted review
items with:

```text
authority_type = BUY_ITEM_SCOPED_REVIEW_ITEM_NOT_SUBMITTED
not_submitted_reason = item_scoped_review_required
blocked_other_items = false
```

If any PASS items are accepted while reviewed BUY items remain, submitted items
are marked `CONSUMED`, the pending plan remains `REVIEW_REQUIRED`, and the
reviewed items stay visible for later authority refresh / retry flow.

## Mandatory Sentinel Coverage

### Case 1 - 8 PASS + 8 REVIEW BUY

Added AK9R0-equivalent focused sentinel:

```text
test_phase30_ak9r1_ak9r0_equivalent_eight_pass_eight_review_buy_subset_submits
```

Result:

```text
submitted_count = 8
reviewed_item_count = 8
submitted_candidate_count = 8
reviewed BUY submitted = false
blocked_other_items = false
```

### Case 2 - All PASS BUY

Existing normal BUY submit and mixed BUY/SELL submit tests continue to pass.

### Case 3 - All REVIEW BUY

All-review `BUY_ITEM_SCOPED_REVIEW_NO_SUBMISSION` behavior is preserved:
submitted count remains zero and execution accepts the no-submission authority.

### Case 4 - PASS + True Batch-Level Failure

Cash / aggregate cash review remains atomic fail-closed. The planning submit
feasibility tests continue to require `approved_item_ids == ()` for cash
batch review.

### Case 5 - PASS + Cash-Pruned Items

AK3R2B cash-feasible batch tests continue to pass. Cash-pruned items remain
outside the active submit batch and are not converted into item-scoped review
submit blockers.

### Case 6 - PASS BUY + REVIEW BUY + Mandatory SELL

Mandatory SELL continuation remains active. PASS BUY items and SELL items can
coexist in the composite pending plan while reviewed BUY items remain
`ITEM_REVIEW_REQUIRED`.

### Case 7 - Reviewed Item Later Becomes Valid

The same submit does not re-evaluate reviewed BUY items into PASS. Reviewed
items remain pending for the existing later authority / retry contract.

### Case 8 - AK7R Larger Quantity

Submit consumes the canonical pending quantity for approved PASS items and does
not recalculate or shrink quantity. If the item is reviewed for
`selected_position_amount`, that item remains review-only.

## Required Final Judgments

```text
NON_CASH_BUY_REVIEW_BATCH_BOUNDARY_REPAIRED = YES
BUY_ITEM_SCOPED_REVIEW_PRESERVED = YES
ITEM_REVIEW_DOES_NOT_ESCALATE_TO_BATCH_FAILURE = YES
TRUE_BATCH_FAILURE_ATOMICITY_PRESERVED = YES
PARTIAL_PASS_BUY_SUBMISSION_ACTION_EFFECTIVE = YES
REVIEWED_BUY_ITEM_EVIDENCE_PRESERVED = YES
AK3R2B_CASH_PRUNING_PRESERVED = YES
AK7R_EXECUTABLE_QUANTITY_PRESERVED = YES
AK8R_BUY_SELL_INDEPENDENCE_PRESERVED = YES
MANDATORY_SELL_CONTINUATION_PRESERVED = YES
SUBMIT_FINAL_FAIL_CLOSED_PRESERVED = YES
AK9_MISSING_SENTINEL_ADDED = YES
NO_FORCED_BUY = YES
SELL_SAFETY_WEAKENED = NO
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_FOR_PARAMETER_SELECTION = FALSE
FRESH_HISTORICAL_EXECUTED_BY_CODEX = NO
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
```

## Tests

Executed:

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase30_ak9r1_pycache python3 -m compileall -q src/ai_fund_lab_v2/runtime_v2 src/ai_fund_lab_v2/strategy tests/runtime_v2 tests/strategy

PYTHONPYCACHEPREFIX=/private/tmp/phase30_ak9r1_pycache python3 -m pytest tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py -q
26 passed

PYTHONPYCACHEPREFIX=/private/tmp/phase30_ak9r1_pycache python3 -m pytest tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py tests/runtime_v2/test_phase26_step6_submit_guard_authority.py tests/runtime_v2/test_phase30_ak3r2b_cash_feasible_buy_batch.py tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py -q
64 passed

PYTHONPYCACHEPREFIX=/private/tmp/phase30_ak9r1_pycache python3 -m pytest tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase30_s_position_sizing_production_handoff.py tests/runtime_v2/test_phase26_step4_position_sizing_authority.py tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py tests/runtime_v2/test_phase23_ab_no_order_submit_guard.py tests/phase12/test_phase12_demo_submit_guard.py -q
142 passed

git diff --check
PASS
```

## Historical

```text
FRESH_HISTORICAL_EXECUTED_BY_CODEX = NO
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
```

## Recommended Next Task

```text
Phase30-AK9R2 - Consolidated Post-Repair Fresh Readiness Regression
```

