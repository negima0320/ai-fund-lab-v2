# Phase27-D2-C Legacy ADD Non-decision Conversion and Double-authority Prevention

## 1. Scope

Phase27-D2-C converts the legacy Runtime path from executable PM ADD order generation to compatibility telemetry only.

```text
Implementation Change: true
Canonical BUY_ADD Activation: false
Strategy / PM / Portfolio Construction / Position Sizing Change: false
Pending / Approval / Submit / Execution Logic Change: false
Historical / 100BD / Long Regression: PROHIBITED_NOT_EXECUTED
```

## 2. Primary Judgment

```text
PHASE27_D2C_LEGACY_ADD_NON_DECISION_CONVERSION_COMPLETE_D2D_READY
```

Supporting judgments:

```json
{
  "legacy_caller_inventory": "COMPLETE",
  "legacy_migration_state": "NON_DECISION_COMPATIBILITY",
  "legacy_quantity_authority": "ZERO_CONFIRMED",
  "legacy_pending_authority": "ZERO_CONFIRMED",
  "legacy_approval_submit_authority": "ZERO_CONFIRMED",
  "double_authority_guard": "PASS",
  "sell_pipeline": "UNCHANGED_FOR_SELL_REDUCE_EXIT_CONFIRMED",
  "downstream_non_change": "CONFIRMED",
  "mode_parity": "CONFIRMED",
  "degression": "PASS",
  "next_entry": "D2-D_APPROVED"
}
```

## 3. What Changed

- `add_consumer` now emits `legacy_pm_add_compatibility.v1` telemetry for PM ADD inputs.
- Legacy ADD no longer resolves ADD-specific cash exposure, position sizing, quantity, lot rounding, Pending, Approval, or Submit authority.
- The old `pm_add_order_plan.json` executable path is no longer reached by PM ADD input because `accepted_items` is always empty in compatibility mode.
- Empty Pending no-order evidence records `pm_add_non_decision_compatibility`.
- Common architecture SoT files now freeze the D2-C migration state outside phase-local documentation.

## 4. Authority Before / After

| Object | Before | After |
|---|---|---|
| Decision Effect | Legacy ADD could become BUY Pending | `NONE` |
| Quantity | `add_consumer` calculated quantity | `NONE` |
| Pending | `pm_add_order_plan` could produce Pending | `NONE` |
| Approval | PM ADD Pending could be approved | `NONE` |
| Submit | PM ADD Pending could reach Submit | `NONE` |
| Runtime Meaning | Legacy executable ADD | Compatibility telemetry only |

## 5. Double-authority Guard

The canonical/legacy dedup key is:

```text
run_id, business_date, symbol, position_campaign_id, decision_id
```

Duplicate legacy compatibility records, lineage mismatches, or any legacy/canonical overlap where both sides claim executable authority must produce `REVIEW_REQUIRED` or `BLOCKED`; fail-open is prohibited.

## 6. Evidence Files

Evidence was written under:

```text
reports/phase27_d2c_legacy_add_non_decision_conversion_and_double_authority_prevention
```

Key artifacts:

- `summary.json`
- `legacy_add_migration_state.json`
- `compatibility_artifact_contract.json`
- `double_authority_guard_results.json`
- `legacy_pending_zero_proof.json`
- `legacy_quantity_authority_zero_proof.json`
- `legacy_approval_submit_zero_proof.json`
- `sell_pipeline_non_change_proof.json`
- `test_results.json`

## 7. Test Results

```text
python3 -m pytest -q tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py
13 passed

python3 -m pytest -q tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py tests/strategy/test_phase27_d2a_position_intent.py tests/strategy/test_phase27_d2b_target_portfolio_decision.py tests/strategy/test_phase22_g_runtime_planning.py
68 passed

python3 -m pytest -q tests/strategy/test_phase27_d2a_position_intent.py tests/strategy/test_phase27_d2b_target_portfolio_decision.py tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase22_g_runtime_planning.py tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py
127 passed
```

No fresh-run, resume, Historical, 100BD, or long regression was executed.
