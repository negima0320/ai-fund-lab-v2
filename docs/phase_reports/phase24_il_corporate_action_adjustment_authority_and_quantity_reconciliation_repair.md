# Phase24-IL Corporate Action Adjustment Authority and Quantity Reconciliation Repair

## 1. Primary Judgment

`PHASE24_IL_CORPORATE_ACTION_ADJUSTMENT_AUTHORITY_IMPLEMENTED_SHORT_VALIDATION_PASS_OPERATOR_RESUME_REQUIRED`

## 2. Implementation Summary

Added a Runtime common Corporate Action Adjustment Authority evaluator:

`src/ai_fund_lab_v2/runtime_v2/corporate_action_adjustment.py`

The evaluator:

- treats `AdjFactor` as an impact signal, not event-type authority
- requires a Runtime-owned adjustment authority for impacted symbols
- validates PIT source hash, business date, symbol, effective date, event status, event type, future data flag, adjustment factor, Ledger / Current / Pending status, already-applied status, and double-adjustment flag
- reconciles SELL submit quantity against adjusted Runtime-owned and broker-available quantity
- returns explicit reason codes such as `corporate_action_authority_missing`, `corporate_action_type_unresolved`, `corporate_action_pending_quantity_stale`, and `corporate_action_double_adjustment_risk`

## 3. Runtime Connections

Historical Submit Adapter:

- now calls the shared adjustment authority when PIT raw OHLCV `AdjFactor` impact is detected
- remains fail-closed when authority is missing or unresolved
- can pass an impacted item only when the adjustment authority proves quantity and lineage consistency

Submit Guard:

- now emits Corporate Action Adjustment Authority evidence per item
- keeps existing BUY/SELL policy guard behavior
- does not change Submit Guard thresholds or order quantities

## 4. Target Case Result

Target:

- run: `runtime-test-historical-extended-smoke-20260801T223117629647Z`
- business_date: `2023-10-04`
- job: `submit`
- symbol: `65730`
- side: `SELL`
- quantity: `200`

Post-repair expected target behavior:

`REVIEW_REQUIRED` / fail-closed until a valid `2023-10-04` `65730` Corporate Action Adjustment Authority is materialized.

This is correct because current evidence still has:

- Corporate Action Status: `IMPACT_DETECTED`
- Corporate Action Type: `UNKNOWN_ADJFACTOR_IMPACT`
- Adjustment Factor: `0.3333333333333333`
- Current Quantity: `200`
- Pending Quantity: `200`
- Corporate Action Already Applied: `NO_EVIDENCE`

## 5. Validation

Short regression:

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase24_il_pycache PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_bv8_historical_submit_pit_universe_authority.py tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py
```

Result:

```text
15 passed
```

Additional related regression:

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase24_il_pycache PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_bv8_historical_submit_pit_universe_authority.py tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py tests/runtime_v2/test_phase22_pu_historical_submit_source_identity.py tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py
```

Result:

```text
32 passed
```

Runtime executed:

`NO`

## 6. Files

Updated:

- `src/ai_fund_lab_v2/runtime_v2/historical_support/environment.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`
- `tests/runtime_v2/test_phase17_bv8_historical_submit_pit_universe_authority.py`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/autonomous_ai_operations_architecture.md`
- `docs/01_requirements/phase_roadmap.md`

Added:

- `src/ai_fund_lab_v2/runtime_v2/corporate_action_adjustment.py`
- `docs/phase_reports/phase24_il_corporate_action_adjustment_authority_and_quantity_reconciliation_audit.md`
- `docs/phase_reports/phase24_il_corporate_action_adjustment_authority_and_quantity_reconciliation_design.md`
- `docs/phase_reports/phase24_il_corporate_action_adjustment_authority_and_quantity_reconciliation_repair.md`

## 7. Recommended Next Task

`Phase24-IM Operator Resume Corporate Action Adjustment Authority Validation`
