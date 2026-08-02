# Phase24-IM Corporate Action Adjustment Authority Runtime Materialization and Consumer Wiring Repair

## 1. Primary Judgment

`PHASE24_IM_AUTHORITY_MATERIALIZATION_AND_CONSUMER_WIRING_REPAIRED_SHORT_VALIDATION_PASS_OPERATOR_RESUME_REQUIRED`

## 2. Implementation Summary

Added Runtime materialization for Corporate Action Adjustment Authority before Submit Guard evaluates impacted historical items.

Implemented:

- `materialize_corporate_action_adjustment_authority`
- `HistoricalSubmitAdapter.corporate_action_event_evidence`
- Submit pipeline materialization before `_submit_guard_item_evidence`
- Submit Guard consumer wiring to pass canonical event evidence into `evaluate_corporate_action_adjustment_authority`

No Strategy, Ranking, Eligibility, PM, Position Sizing policy, Capital Deployment parameter, Submit Guard threshold, Corporate Action Guard relaxation, or Safety relaxation was introduced.

## 3. Canonical Producer

Producer:

`src/ai_fund_lab_v2/runtime_v2/corporate_action_adjustment.py::materialize_corporate_action_adjustment_authority`

Artifact:

`.runtime/runtime_state/corporate_action_adjustments/<business_date>/<symbol>.json`

For impacted but unresolved events, the producer writes:

```text
status = REVIEW_REQUIRED
event_status = IMPACT_DETECTED
event_type = UNKNOWN_ADJFACTOR_IMPACT
already_applied_status = UNKNOWN
quantity_reconciliation_status = REVIEW_REQUIRED
price_reconciliation_status = REVIEW_REQUIRED
```

This is intentional fail-closed materialization.

## 4. Consumer Consistency

Submit Guard and HistoricalSubmitAdapter now use the same PIT event evidence and same authority artifact path/hash for impacted historical submit items.

The inconsistency:

```text
Guard: NOT_DETECTED / PASS
Adapter: IMPACT_DETECTED / REVIEW_REQUIRED
```

is repaired.

## 5. Target Case Expected Behavior

For `2023-10-04 / 65730 / SELL 200`, the corrected Runtime behavior is:

- authority artifact materialized: `YES`
- authority status: `REVIEW_REQUIRED`
- submit allowed: `NO`
- direct reason: unresolved corporate action event type / unknown already-applied status

This does not make the target SELL pass. It makes the halt earlier, clearer, and consistent across consumers.

## 6. Regression

Targeted regression:

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase24_im_pycache PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py tests/runtime_v2/test_phase17_bv8_historical_submit_pit_universe_authority.py tests/runtime_v2/test_phase22_pu_historical_submit_source_identity.py tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py
```

Result:

```text
33 passed
```

Runtime executed:

`NO`

## 7. Recommended Next Task

`Phase24-IN Operator Resume Corporate Action Runtime Validation`
