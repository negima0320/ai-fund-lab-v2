# Phase32-BT — BQ Lot-Blocked REDUCE Reconsideration Fail-Closed Scope Repair

## Objective

Repair the Phase32-BQ sell-planning control-path defect identified by Phase32-BS:

```text
PM REDUCE
-> REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT
-> BO = SHADOW_INSUFFICIENT_EVIDENCE / SHADOW_HOLD
-> incorrectly escalated to FAIL_CLOSED: MISSING_CAMPAIGN_ID
-> sell_planning HALT
```

Target halted run for readiness assessment:

```text
runtime-test-historical-extended-smoke-20260831T224727109611Z
halt = 2022-10-04:sell_planning
```

No resume, resume dry-run, recover, replay, fresh-run, long Historical, or target runtime state mutation was executed.

## Root Cause Confirmed

Phase32-BS conclusions were preserved.

The BQ path applied promotion-grade campaign-id validation to every lot-blocked REDUCE before BO semantic classification. On 2022-10-04, symbols `92420` and `33700` were structurally inspectable lot-blocked REDUCE rows, but their BO result was non-promoted:

```text
BO = SHADOW_INSUFFICIENT_EVIDENCE
expected Production result = NO_ORDER
```

The previous implementation failed before reaching that non-promoted classification because the sell-planning handoff did not carry `position_campaign_id` / `campaign_id`.

## Repair Boundary

Changed file:

```text
src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py
```

The repair is limited to `_lot_blocked_reduce_full_exit_reconsideration`.

Implemented contract:

1. Capture the explicit handoff campaign id separately as `handoff_campaign_id`.
2. If the handoff lacks campaign id but current run-scoped Strategy Intelligence lifecycle context has a campaign id for the same symbol, use that only as semantic input authority for BO classification.
3. Preserve mismatch fail-closed when both handoff and Strategy Intelligence campaign ids exist and disagree.
4. Allow non-promoted BO outcomes to remain `NOT_PROMOTED` / `NO_ORDER`:

```text
SHADOW_HOLD
SHADOW_INSUFFICIENT_EVIDENCE
```

5. Require explicit handoff campaign authority again before actual `SHADOW_FULL_EXIT` promotion. If BO asks for FULL EXIT and the handoff campaign is missing, fail closed with `MISSING_CAMPAIGN_ID`.

This changes control-path ordering only. It does not alter BO/BQ Strategy semantics, thresholds, weights, models, reason-family logic, profit cushion semantics, SELL thresholds, REDUCE thresholds, or PM behavior.

## Why This Is Not a Safety Bypass

The repair does not let missing campaign identity create a SELL_EXIT.

For non-promoted outcomes, promotion-only campaign requirements no longer halt the runtime. The row remains a non-executable REDUCE no-order, which is the pre-BQ behavior.

For promoted outcomes, complete promotion authority remains mandatory:

```text
BO = SHADOW_FULL_EXIT
handoff campaign id missing
-> FAIL_CLOSED: MISSING_CAMPAIGN_ID
-> no SELL_EXIT
```

Stale, future-dated, cross-run, missing, malformed, or mismatched BO evidence remains fail-closed through the existing evidence source checks and mismatch checks.

## Campaign Identity Propagation

BT repairs campaign identity propagation for the BQ semantic classification input by accepting only current run-scoped Strategy Intelligence lifecycle context as fallback semantic authority when the sell-planning handoff is incomplete.

No symbol-only campaign id generation was added.

No downstream campaign id regeneration was added.

The fallback does not invent a campaign; it uses already-materialized source evidence from the same BQ input authority family. Actual FULL_EXIT promotion still requires the explicit sell-planning handoff campaign id.

## Files Changed

- `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py`
- `tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py`
- `docs/phase_reports/phase32_bt_bq_lot_blocked_reduce_reconsideration_fail_closed_scope_repair.md`

## Focused Test Coverage Added

Added focused regressions in `tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py`:

```text
test_phase32_bt_45750_bq_full_exit_regression_promotes_with_complete_campaign_authority
test_phase32_bt_missing_handoff_campaign_bo_hold_preserves_no_order
test_phase32_bt_92420_33700_missing_handoff_campaign_bo_insufficient_preserves_no_order
test_phase32_bt_bo_full_exit_missing_handoff_campaign_still_fails_closed
```

These prove:

- 45750-like BQ FULL_EXIT remains promotable with complete authority.
- BO HOLD without handoff campaign remains NO_ORDER.
- 92420 / 33700 BO INSUFFICIENT without handoff campaign remains NO_ORDER.
- FULL_EXIT with missing handoff campaign still fails closed and creates no SELL_EXIT.

## Validation

Compile:

```text
PYTHONPYCACHEPREFIX=/private/tmp/pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py
PASS
```

BQ/BT direct test file:

```text
PYTHONPATH=src python3 -m pytest tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py -q
23 passed
```

Adjacent focused regression suite:

```text
PYTHONPATH=src python3 -m pytest \
  tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py \
  tests/runtime_v2/test_phase31_f1l_same_day_sell_pending_idempotency.py \
  tests/runtime_v2/test_phase31_f1w_item_scoped_partial_submit.py \
  tests/runtime_v2/test_phase17_ab_current_valuation_pre_gate_authority.py \
  tests/runtime_v2/test_phase30_ak9r27_pending_review_scope_authority.py \
  tests/runtime_v2/test_phase30_ak9r28_historical_safety_temporal_authority.py \
  tests/strategy/test_phase31_c0d_unrepresentable_reduce_exit_shadow.py \
  tests/strategy/test_phase31_g115_add_marginal_authoritative_binding.py \
  tests/strategy/test_phase22_g_runtime_planning.py::test_phase32_f_runtime_does_not_resurrect_buy_wait_add_when_ps_delta_zero \
  tests/strategy/test_phase32_x_recoverable_deterioration_episode.py -q

147 passed
```

Diff hygiene:

```text
git diff --check src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py
PASS
```

## Target Run READ-ONLY Assessment

Target run:

```text
runtime-test-historical-extended-smoke-20260831T224727109611Z
```

Current state remains:

```text
completed_business_days = [2022-10-03]
halted_at = 2022-10-04:sell_planning
safe continuation point = 2022-10-04:sell_planning
```

2022-10-04 has no inspected submit/execution stage artifact in the target run evidence. The halt occurred before submit/execution side effects for that date.

Under the repaired source, the two Phase32-BS failing rows are expected to behave as:

| symbol | BO result | expected BT result |
|---|---|---|
| 92420 | SHADOW_INSUFFICIENT_EVIDENCE | NOT_PROMOTED / NO_ORDER / no MISSING_CAMPAIGN_ID HALT |
| 33700 | SHADOW_INSUFFICIENT_EVIDENCE | NOT_PROMOTED / NO_ORDER / no MISSING_CAMPAIGN_ID HALT |

Therefore `2022-10-04:sell_planning` is expected to pass the specific BT-repaired boundary. The run may still encounter unrelated later defects; none were evaluated by this phase.

## Required Final Answers

1. `BQ_FAIL_CLOSED_SCOPE_REPAIRED`

```text
YES
```

2. `BO_INSUFFICIENT_NO_ORDER_PRESERVED`

```text
YES
```

3. `BO_HOLD_NO_ORDER_PRESERVED`

```text
YES
```

4. `BO_FULL_EXIT_PROMOTION_PRESERVED`

```text
YES
```

5. `FULL_EXIT_MISSING_CAMPAIGN_FAILS_CLOSED`

```text
YES
```

6. `92420_REGRESSION_PASS`

```text
YES
```

7. `33700_REGRESSION_PASS`

```text
YES
```

8. `45750_BQ_FULL_EXIT_REGRESSION_PASS`

```text
YES
```

9. `CAMPAIGN_IDENTITY_PROPAGATION_REPAIRED`

```text
YES, for BQ semantic classification input via current run-scoped Strategy Intelligence lifecycle authority. FULL_EXIT promotion still requires explicit handoff campaign authority.
```

10. `SYMBOL_ONLY_JOIN_ADDED`

```text
NO
```

11. `DOWNSTREAM_CAMPAIGN_ID_REGENERATION_ADDED`

```text
NO
```

12. `DUPLICATE_SELL_GUARD_PRESERVED`

```text
YES
```

13. `PENDING_REVIEW_SAFETY_PRESERVED`

```text
YES
```

14. `HISTORICAL_TEMPORAL_SAFETY_PRESERVED`

```text
YES
```

15. `STRATEGY_SEMANTICS_CHANGED`

```text
NO
```

16. `NEW_FEATURE_ADDED`

```text
NO
```

17. `NEW_MODEL_ADDED`

```text
NO
```

18. `NEW_THRESHOLD_ADDED`

```text
NO
```

19. `TARGET_RUN_MUTATED`

```text
NO
```

20. `RESUME_EXECUTED`

```text
NO
```

21. `FRESH_RUN_EXECUTED`

```text
NO
```

22. `TARGET_2022_10_04_SELL_PLANNING_EXPECTED_PASS`

```text
YES for the Phase32-BS / BT repaired MISSING_CAMPAIGN_ID boundary.
```

23. `SAME_RUN_CONTINUATION_SAFE`

```text
YES, expected after operator-run continuation, because the target run is stopped at 2022-10-04:sell_planning and no 2022-10-04 submit/execution side effects were found.
```

24. `SAFE_CONTINUATION_POINT`

```text
2022-10-04:sell_planning
```

25. `FRESH_RUN_REQUIRED`

```text
NO by current evidence.
```

26. `NEXT_RECOMMENDED_STEP`

```text
User/operator should continue the existing run from 2022-10-04:sell_planning using the canonical runtime_test continuation command. Do not start a new fresh-run solely for BT.
```

27. `FINAL_JUDGMENT`

```text
PHASE32_BT_BQ_LOT_BLOCKED_REDUCE_RECONSIDERATION_FAIL_CLOSED_SCOPE_REPAIRED_SAME_RUN_CONTINUATION_READY
```

## Final Judgment

`PHASE32_BT_BQ_LOT_BLOCKED_REDUCE_RECONSIDERATION_FAIL_CLOSED_SCOPE_REPAIRED_SAME_RUN_CONTINUATION_READY`
