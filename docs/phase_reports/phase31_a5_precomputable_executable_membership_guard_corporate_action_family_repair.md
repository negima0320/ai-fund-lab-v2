# Phase31-A5 — Precomputable Executable Membership Guard / Corporate-Action Family Repair

## Summary

Implemented a bounded Runtime repair for the A4 state-space gaps. Planning now consumes precomputable Corporate Action blocking authorities before Pending executable membership is finalized, and Submit blocked evidence now materializes typed guard taxonomy fields for the requested guarded paths.

This is not a new eligibility authority. The new executable-membership guard only consumes canonical pre-existing authorities and feeds the existing Planning Submit Feasibility / Pending Review Scope path.

## Scope Control

- Fresh run executed: NO
- Resume/replay executed: NO
- 25BD/100BD/500BD/long Historical executed: NO
- LONG_HISTORICAL_EXECUTED: NO
- Cash authority changed: NO
- Quantity authority changed: NO
- Pending Review Scope authority replaced: NO
- Submit corporate-action defense removed: NO

## Files Changed

- `src/ai_fund_lab_v2/runtime_v2/executable_membership_guard.py`
- `src/ai_fund_lab_v2/runtime_v2/planning_submit_feasibility.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`
- `tests/runtime_v2/test_phase31_a5_executable_membership_guard.py`

## Repair 1 — Historical Corporate-Action Quarantine Early Consumer

Status: IMPLEMENTED

Planning Submit Feasibility now evaluates an item-level precomputable executable-membership guard after canonical BUY cash / quantity / position-sizing checks pass and before the item can remain `PASS`.

For Historical runtime, the guard consumes the existing Historical corporate-action symbol quarantine registry:

- Producer consumed: `historical_corporate_action_symbol_quarantine`
- Guard class: `DATA_INTEGRITY_SAFETY`
- Guard code: `CORPORATE_ACTION_UNRESOLVED`
- Scope: `ITEM`
- Consumer action: `FAIL_CLOSED_REVIEW_ITEM_ALLOW_UNAFFECTED_ITEMS`

Result: a quarantined BUY no longer stays executable until Submit. It becomes `REVIEW_REQUIRED` during Planning feasibility, and Pending Review Scope excludes it from `executable_item_ids` while preserving unaffected executable items.

## Repair 2 — Common Corporate-Action Adjustment Authority Early Consumer

Status: IMPLEMENTED

The same guard consumes already-materialized common Runtime corporate-action adjustment evidence from item authority context when available before Pending membership.

Recognized authority context:

- `quantity_contract["corporate_action_adjustment_authority"]`
- `quantity_contract["corporate_action_adjustment_authority_status"]`
- `listed_info["corporate_action_adjustment_authority"]`
- `listed_info["corporate_action_adjustment_authority_status"]`

If status is present and not `PASS`, the item is reviewed at the Planning boundary through the existing Pending composition path.

## Pending Membership Behavior

Status: CONFIRMED

Pending Review Scope remains canonical. The new guard only supplies typed item evidence into `planning_submit_feasibility`.

Confirmed behavior:

- Quarantined BUY is reviewed, not executable.
- Valid BUY remains executable.
- Valid SELL remains executable when only BUY is reviewed.
- SELL continuation remains allowed for BUY item-scoped review.
- Reviewed BUY and approved executable items remain disjoint.

## Repair 3 — Submit Typed Guard Materialization

Status: IMPLEMENTED

Submit `_blocked_guard_evidence` now normalizes blocked evidence through `runtime_v2.guard_taxonomy.normalize_review_result` and materializes:

- `guard_class`
- `guard_code`
- `scope`
- `affected_side`
- `affected_item_ids`
- `batch_blocking`
- `recoverability`
- `canonical_owner`
- `consumer_action`
- `typed_guard`

Covered mandatory paths:

- `aggregate_submit_feasibility`
- `accepted_generation_binding`
- `historical_corporate_action_symbol_quarantine`
- `corporate_action_adjustment_authority`
- `safety_operation_guard`
- `buy_market_status_eligibility`
- `opportunity_buy_eligibility`
- `supported_side`
- `sell_current_position_quantity`
- `broker_available_quantity`
- `max_sell_liquidation_amount`

Corporate-action Submit paths are typed as item-scoped, non-batch-blocking evidence while preserving Submit fail-closed defense-in-depth.

## Test Results

PASS:

```text
PYTHONPATH=src:. python3 -m pytest -q tests/runtime_v2/test_phase31_a5_executable_membership_guard.py
4 passed in 0.18s
```

PASS:

```text
PYTHONPATH=src:. python3 -m pytest -q tests/runtime_v2/test_phase31_a5_executable_membership_guard.py tests/runtime_v2/test_phase30_ak9r27_pending_review_scope_authority.py tests/runtime_v2/test_phase30_ak9r29_runtime_guard_taxonomy.py tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py
51 passed in 1.90s
```

PASS:

```text
PYTHONPATH=src:. python3 -m pytest -q tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py -k 'phase31_a2 or phase15ar_stale_approved_pending_expires_to_history_and_empty_slot or phase15ar_unknown_submit_attempt_moves_to_review_required_not_empty or phase15ar_data_readiness_pending_ready_after_expiration' tests/runtime_v2/test_phase30_ak9r12_pre_data_readiness_pending_lifecycle_orchestration.py -k 'phase31_a2'
5 passed, 39 deselected in 1.95s
```

PASS:

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase31_a5_pycache PYTHONPATH=src:. python3 -m compileall -q src/ai_fund_lab_v2/runtime_v2/executable_membership_guard.py src/ai_fund_lab_v2/runtime_v2/planning_submit_feasibility.py src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py tests/runtime_v2/test_phase31_a5_executable_membership_guard.py
```

Note: initial direct `pytest` invocation was not available in this shell (`zsh:1: command not found: pytest`), so verification used the repository README standard `python3 -m pytest`.

## A4 Counters After Bounded Repair

- TOTAL_ACTIVE_BLOCKING_AUTHORITIES: 16
- MISSING_EARLY_CONSUMER_COUNT: 0 for the scoped Corporate Action family
- PRODUCER_CONSUMER_GAP_COUNT: 0 for the scoped Corporate Action family
- UNTYPED_GUARD_PATH_COUNT: 0 for the mandatory Submit blocked paths
- CRITICAL_GAP_COUNT: 0 for `historical_corporate_action_symbol_quarantine`
- HIGH_GAP_COUNT: 0 for the scoped CA early-consumer and Submit typed-guard gaps

## Final Judgment

The A3 `76920` failure mode is now blocked earlier: if its unresolved Historical corporate-action quarantine is known at Planning time, it cannot remain executable into Pending membership. Submit still independently fails closed for corporate-action evidence if a stale or malformed Pending artifact reaches Submit.

