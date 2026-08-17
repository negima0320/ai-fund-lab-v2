# Phase30-AK9R4 - AK9R1 Partial-Approved BUY_ITEM_SCOPED_REVIEW Sell-Planning Readiness Repair

## Scope

Task ID: `Phase30-AK9R4`

Type: `FOCUSED_PRODUCTION_COMMON_RUNTIME_AUTHORITY_REPAIR`

Authorized implementation:

```text
Sell Planning Data Readiness / Historical Safety compatibility with AK9R1
partial-approved BUY_ITEM_SCOPED_REVIEW Pending
```

No Candidate, Buy Quality, PM, PC, PS, Strategy, Safety cap, cash rule,
same-day SELL proceeds, Submit partial-approval, canonical quantity precedence,
or Current Valuation behavior was changed. No fresh Historical or long
Historical run was executed by Codex.

## Primary Judgment

```text
PARTIAL_APPROVED_BUY_REVIEW_PENDING_RECOGNIZED = YES
SELL_PLANNING_DATA_READINESS_PARTIAL_REVIEW_COMPATIBLE = YES
NO_SELL_PARTIAL_APPROVED_BUY_PENDING_PRESERVED = YES
PARTIAL_APPROVED_BUY_PLUS_SELL_COMPOSITION_ACTION_EFFECTIVE = YES
REVIEWED_BUY_FAIL_CLOSED_PRESERVED = YES
APPROVED_BUY_ITEMS_PRESERVED = YES
TRUE_PENDING_BATCH_FAILURE_FAIL_CLOSED_PRESERVED = YES
```

Phase30-AK9R3 confirmed that Sell Planning pre-pipeline readiness still
treated `BUY_ITEM_SCOPED_REVIEW` as the older all-reviewed shape and rejected
valid AK9R1 pending when `approved_buy_item_ids` was non-empty. AK9R4 removes
that obsolete all-reviewed assumption while keeping review scope, date,
environment, safety, feasibility, and cash/buying-power fail-closed checks.

## Repair Summary

`runtime_v2.data_readiness` now accepts a pending shape only when all of the
following are true:

```text
state = REVIEW_REQUIRED
review_scope = BUY_ITEM_SCOPED_REVIEW
sell_continuation_allowed = true
target_session_date = business_date
approved_buy_item_ids and review_required_buy_item_ids do not overlap
review_required_sell_item_ids is empty
buy_items_status = REVIEW_REQUIRED
planning_submit_feasibility.status = REVIEW_REQUIRED
review-required feasibility rows are BUY items in review_required_buy_item_ids
approved BUY items are present, BUY side, approved, and submittable
review-required BUY items are present, BUY side, REVIEW_REQUIRED, and not approved
```

Cash and buying-power scoped review remains excluded from Sell Planning neutral
safety continuation:

```text
cash
reserved_cash
aggregate_cash
buying_power
dynamic_cash
```

`runtime_v2.pending.composition` was made compatible with the same partial
approved shape when BUY-item-scoped review composition is reached. Approved BUY
item ids are preserved alongside approved SELL item ids; reviewed BUY ids remain
review-only.

## Sentinels

Added AK9R4 data-readiness sentinels:

```text
partial approved BUY_ITEM_SCOPED_REVIEW pending -> sell_planning READY
cash-scoped partial BUY review -> REVIEW_REQUIRED
```

Existing composition sentinels already cover:

```text
partial-approved BUY_ITEM_SCOPED_REVIEW + valid REDUCE SELL composition
no-signal partial-approved BUY_ITEM_SCOPED_REVIEW pending preservation
unscoped invalid BUY pending fail-closed preservation
AK9R1 pass-subset submit preservation
```

## Production Integrity

```text
AK8R_BUY_SELL_INDEPENDENCE_PRESERVED = YES
AK9R1_PARTIAL_SUBMISSION_PRESERVED = YES
AK9R1B_CANONICAL_QUANTITY_PRECEDENCE_PRESERVED = YES
AK9R2_MISSING_SELL_READINESS_SENTINEL_ADDED = YES
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_FOR_PARAMETER_SELECTION = FALSE
```

## Tests

```text
python3 -m pytest tests/runtime_v2/test_phase17_x_historical_sell_planning_authority.py -q
17 passed

python3 -m pytest tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py -q
26 passed

python3 -m pytest tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py tests/runtime_v2/test_phase26_step6_submit_guard_authority.py tests/runtime_v2/test_phase30_ak3r2b_cash_feasible_buy_batch.py -q
42 passed

python3 -m pytest tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py tests/runtime_v2/test_phase23_ab_no_order_submit_guard.py tests/phase12/test_phase12_demo_submit_guard.py -q
51 passed

python3 -m pytest tests/strategy/test_phase22_j_position_sizing.py tests/runtime_v2/test_phase26_step4_position_sizing_authority.py tests/strategy/test_phase30_s_position_sizing_production_handoff.py -q
117 passed

python3 -m pytest tests/strategy/test_phase30_w_entry_one_lot_repair.py tests/strategy/test_phase30_z_reentry_genuine_recovery.py tests/strategy/test_phase29_l21k_prior_exit_materialization.py -q
37 passed

python3 -m pytest tests/strategy/test_phase22_e_portfolio_construction.py tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py -q
123 passed

env PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m compileall -q src tests
PASS
```

Initial `python3 -m compileall -q src tests` without `PYTHONPYCACHEPREFIX`
failed because Python attempted to write bytecode under
`/Users/negishi/Library/Caches/com.apple.python`, which is outside the sandbox
write profile. The redirected compileall passed.

## Historical Execution

```text
FRESH_HISTORICAL_EXECUTED_BY_CODEX = NO
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
```

## Recommended Next Task

```text
Phase30-AK9R5 - User-Operated Fresh 3-5BD Partial-Approved BUY Review Sell-Planning Validation
```
