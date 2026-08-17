# Phase30-AK9R23 - Sell Planning Historical Safety Temporal Authority for BUY_ITEM_SCOPED_REVIEW Pending Focused Repair

## Primary Judgment

```text
SUBMIT / BUY_ITEM_SCOPED_REVIEW pending remained fail-closed for BUY execution, while Sell Planning can now reuse the existing Historical Safety temporal authority when the same-day BUY review is explicitly item-scoped and sell_continuation_allowed=true.
```

## Root Cause

AK9R22 reproduced a Sell Planning halt where a same-day partial BUY review pending had:

```text
review_scope = BUY_ITEM_SCOPED_REVIEW
sell_continuation_allowed = true
approved SELL present
approved BUY present
reviewed BUY present
reviewed SELL absent
```

Data Readiness still treated the reviewed BUY cash/reserved-cash reason as invalidating Sell Planning Historical Safety authority, producing:

```text
historical_safety_temporal_authority_missing
pending_review_required
```

Separately, real Sell Planning orchestration could route this scoped pending through the generic active BUY composition path, which risked approving reviewed BUY items during BUY/SELL composition.

## Repair

Implemented a scoped repair in:

```text
src/ai_fund_lab_v2/runtime_v2/data_readiness.py
src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py
src/ai_fund_lab_v2/runtime_v2/pending/composition.py
```

Data Readiness now passes `readiness_scope` into Historical Safety authority checks. For `sell_planning` only, a valid same-day `BUY_ITEM_SCOPED_REVIEW` pending with no reviewed SELL and `sell_continuation_allowed=true` can materialize the existing Historical Daily Neutral safety authority even when the reviewed BUY reason is cash-like.

Sell Planning now prioritizes `compose_with_buy_item_scoped_review_pending` for scoped review pending before the generic active BUY composition path. The specialized composition keeps reviewed BUY items as `REVIEW_REQUIRED`, preserves only approved BUY ids plus SELL ids in `approved_item_ids`, and leaves the final pending top-level state as `REVIEW_REQUIRED`.

No Strategy, Candidate, PM, PC, PS, cap, threshold, Safety policy, BUY submit approval, or fresh/long Historical execution was changed.

## Sentinel Coverage

Added/updated focused sentinels in:

```text
tests/runtime_v2/test_phase17_x_historical_sell_planning_authority.py
tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py
```

Covered:

- exact AK9R22-shaped cash-scoped partial BUY review allows Sell Planning safety readiness;
- `sell_continuation_allowed=false` remains fail-closed;
- reviewed SELL remains fail-closed;
- malformed/stale/unscoped pending remains fail-closed;
- real Sell Planning orchestration reaches PM SELL and preserves reviewed BUY as review-only;
- normal BUY/SELL composition remains unchanged;
- no-signal invalid active BUY remains fail-closed.

## Required Final Judgments

```text
AK9R22_SELL_PLANNING_HALT_CLASS_REPRODUCED = YES
CANONICAL_SELL_HISTORICAL_SAFETY_AUTHORITY_REUSED = YES
BUY_REVIEW_DOES_NOT_INVALIDATE_SELL_TEMPORAL_AUTHORITY = YES
BUY_ITEM_SCOPED_REVIEW_REMAINS_FAIL_CLOSED_FOR_BUY = YES
SELL_PLANNING_CONTINUES_WITH_VALID_BUY_ITEM_SCOPED_REVIEW = YES
REVIEWED_SELL_FAIL_CLOSED_PRESERVED = YES
TEMPORAL_AUTHORITY_FAIL_CLOSED_PRESERVED = YES
HISTORICAL_SAFETY_FAIL_CLOSED_PRESERVED = YES
SELL_SAFETY_BOUNDARIES_PRESERVED = YES
PM_SELL_INTENT_REACHES_SELL_PLANNING = YES
AK8R_BUY_SELL_PENDING_COMPOSITION_PRESERVED = YES
VALID_BUY_PENDING_NOT_DROPPED = YES
REVIEWED_BUY_REMAINS_REVIEW_ONLY = YES
MANDATORY_SELL_INDEPENDENCE_PRESERVED = YES
MANDATORY_SELL_SAFETY_WEAKENED = NO
AK9R21_CAPITAL_DEPLOYMENT_REPAIR_PRESERVED = YES
REAL_SELL_PLANNING_ORCHESTRATION_SENTINEL = YES
ORCHESTRATION_FIDELITY = FULL
CROSS_REPAIR_INTERACTION_STATUS = PASS
NEW_BUY_FILTER_CREATED = NO
NEW_SELL_FILTER_CREATED = NO
FORCED_BUY_CREATED = NO
FORCED_SELL_CREATED = NO
STRATEGY_CHANGED = NO
PC_CHANGED = NO
PS_CHANGED = NO
CAP_VALUES_CHANGED = NO
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
python3 -m pytest tests/runtime_v2/test_phase17_x_historical_sell_planning_authority.py -k 'ak9r23 or phase24_hv or phase17_x_pending_safety_authority_mismatch or phase23_ax'
11 passed

python3 -m pytest tests/runtime_v2/test_phase17_bj_historical_daily_neutral_safety_authority.py tests/runtime_v2/test_phase17_x_historical_sell_planning_authority.py -k 'ak9r23 or phase24_hv or phase17_x_pending_safety_authority_mismatch or phase23_ax or historical'
31 passed

python3 -m pytest tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py
26 passed

python3 -m pytest tests/runtime_v2/test_phase30_ak9r10_full_day1_day2_pending_lifecycle.py tests/runtime_v2/test_phase30_ak9r12_pre_data_readiness_pending_lifecycle_orchestration.py tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py -k 'ak9r21 or ak9r1b or one_lot or selected_position_amount or lifecycle or orchestration'
17 passed

PYTHONPYCACHEPREFIX=.pytest_cache/pycache python3 -m compileall -q src/ai_fund_lab_v2/runtime_v2/data_readiness.py src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py src/ai_fund_lab_v2/runtime_v2/pending/composition.py
PASS

git diff --check
PASS
```

## Recommended Next Task

```text
Phase30-AK9R24 - User-Operated Fresh 20BD Validation
```
