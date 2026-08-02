# Phase24-IE Aggregate Feasibility BUY Item Review / SELL Continuation Implementation

## 1. Primary Judgment

`PHASE24_IE_BUY_ITEM_SCOPED_REVIEW_SELL_CONTINUATION_REPAIRED_SHORT_VALIDATION_PASS_RUNTIME_RERUN_REQUIRED`

## 2. Runtime Evidence

Target run: `runtime-test-historical-extended-smoke-20260801T212223711617Z`

Business date: `2023-01-31`

Direct halt reason: `historical_safety_temporal_authority_missing` at `sell_planning`.

The Phase24-ID aggregate feasibility result was expected: BUY `77760` passed, BUY `93180` breached aggregate `max_exposure` after sequential reservation and became `REVIEW_REQUIRED`.

## 3. Root Cause

Primary root cause: the Historical Safety resolver did not treat valid `BUY_ITEM_SCOPED_REVIEW` Pending as sell-continuation-ready when it evaluated pending lifecycle state, so `REVIEW_REQUIRED` became `pending_lifecycle_state` mismatch.

Secondary root cause: Pending materialization kept the feasibility-PASS BUY item in `approved_buy_item_ids`, while the top-level batch was non-submittable. This made the review scope evidence inconsistent with the Phase24-HV continuation contract.

## 4. Implementation Summary

- Preserved Phase24-ID aggregate Planning Submit Feasibility.
- Preserved batch atomicity by keeping `approved_item_ids`, `approved_buy_item_ids`, and `approved_sell_item_ids` empty on aggregate feasibility review.
- Added item-level evidence fields:
  - `feasibility_status`
  - `batch_submit_status`
  - `item_review_reason`
- Marked feasibility-PASS BUY items as non-submittable by batch review rather than approved.
- Allowed Historical Safety resolver to recognize valid same-date `BUY_ITEM_SCOPED_REVIEW` as sell-continuation-ready.
- Kept fail-closed behavior for missing authority, ambiguous scope, SELL review, stale date, global Safety review, and non-empty approved BUY IDs.

## 5. Non-Changes

No Strategy, Ranking, PM decision logic, Position Sizing policy, BUY quantity, max exposure, cash reserve, target exposure, Submit Guard, or SELL Submit Guard was changed.

Runtime was not executed.

## 6. Regression

Short validation passed:

```text
44 passed in 2.70s
```

Command:

```text
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_x_historical_sell_planning_authority.py tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py tests/runtime_v2/test_phase24_h_cost_basis_authority.py tests/runtime_v2/test_phase23_i_strategy_planning_authority.py
```

## 7. Recommended Next Task

Run the Operator historical extended smoke rerun and confirm `2023-01-31` proceeds through SELL Planning while BUY `93180` remains non-submittable.
