# Phase27-D2-D Existing Position Quantity Delta Contract Integration

## 1. Scope

Phase27-D2-D adds the shadow `position_sizing_plan.v1` artifact between `target_portfolio_decision.v1` and future Runtime Planning integration.

```text
Implementation Change: true
authority_mode: SHADOW
decision_effect: NONE
Runtime Planning Change: false
Pending / Approval / Submit / Execution Change: false
Legacy ADD Change: false
Historical / fresh-run: PROHIBITED_NOT_EXECUTED
```

## 2. Primary Judgment

```text
PHASE27_D2D_POSITION_SIZING_SHADOW_COMPLETE_D2E_READY
```

Supporting:

```json
{
  "sizing_contract": "READY",
  "delta_mapping": "READY",
  "decision_effect": "ZERO_CONFIRMED",
  "degression": "PASS",
  "next": "D2-E_APPROVED"
}
```

## 3. Contract

`position_sizing_plan.v1` consumes `target_portfolio_decision.v1` and produces shadow quantity candidates only:

- `current_quantity`
- `target_quantity_candidate`
- `quantity_delta_candidate`
- `orderable_quantity_delta`
- `lot_rounding_result`
- `sizing_status`
- `reason_codes`
- `lineage`

PM intent is preserved. Sizing must emit the matching delta or the matching `*_NOT_SIZED` status; it must not silently convert ADD/REDUCE/EXIT to HOLD.

## 4. Mapping Result

```json
{
  "position_count": 4,
  "sizing_status_counts": {
    "FULL_EXIT_DELTA_SIZED": 1,
    "NEGATIVE_DELTA_SIZED": 1,
    "POSITIVE_DELTA_SIZED": 1,
    "ZERO_DELTA_SIZED": 1
  },
  "delta_classification_counts": {
    "FULL_NEGATIVE_DELTA": 1,
    "NEGATIVE_PARTIAL_DELTA": 1,
    "POSITIVE_DELTA": 1,
    "ZERO_DELTA": 1
  },
  "duplicate_dedup_key_count": 0,
  "decision_effect_zero": true,
  "runtime_connected": false,
  "pending_decided": false,
  "submit_decided": false
}
```

## 5. Evidence Files

Evidence was written under:

```text
reports/phase27_d2d_existing_position_quantity_delta_contract_integration
```

## 6. Tests

```text
python3 -m pytest -q tests/strategy/test_phase27_d2d_position_sizing_plan.py
6 passed

python3 -m pytest -q tests/strategy/test_phase27_d2a_position_intent.py tests/strategy/test_phase27_d2b_target_portfolio_decision.py tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py tests/strategy/test_phase27_d2d_position_sizing_plan.py tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase22_g_runtime_planning.py
133 passed
```

No Historical, fresh-run, resume, 100BD, or long regression was executed.
