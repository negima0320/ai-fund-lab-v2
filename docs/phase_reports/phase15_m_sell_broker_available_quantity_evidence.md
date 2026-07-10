# Phase15-M SELL Broker Available Quantity Evidence

## Status

`PHASE15M_SELL_BROKER_AVAILABLE_QUANTITY_EVIDENCE_COMPLETE`

Phase15-M replaces the temporary SELL `current_proxy` available quantity with Broker ReadOnly position evidence. SELL Submit now requires Runtime-owned Current quantity and Broker available quantity to pass as separate checks before broker preflight or submit.

## Implementation Summary

Implemented:

- Submit reads the latest Broker ReadOnly positions snapshot from:

```text
.runtime/broker/snapshots/positions/*.json
```

- SELL Guard no longer uses Current quantity as Broker available quantity.
- Missing Broker available evidence blocks before broker preflight / submit.
- Insufficient Broker available quantity blocks before broker preflight / submit.
- Confirmed Broker ReadOnly available quantity allows the existing SELL guard to continue.
- Current quantity and Broker available quantity are emitted separately in guard evidence.
- Broker-only positions remain excluded from SELL source because SELL Planning still uses Runtime-owned Current only.

## Changed Files

Code:

- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`

Tests:

- `tests/runtime_v2/test_phase15m_sell_broker_available_quantity_evidence.py`
- `tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py`
- `tests/runtime_v2/test_phase14e32_sell_runtime_io_contract.py`

Report:

- `docs/phase_reports/phase15_m_sell_broker_available_quantity_evidence.md`
- `reports/phase_reports/phase15_m_sell_broker_available_quantity_evidence.json`

## Broker Available Quantity Source

Source:

```text
Broker ReadOnly Position snapshot
```

Accepted artifact shape:

```text
kind=positions
source=broker_readonly
records[].issue_code / records[].symbol / records[].position_key
records[].quantity
records[].available_quantity
records[].account_type
records[].as_of
records[].review_required
records[].production_equivalent
```

The latest non-manifest JSON under `.runtime/broker/snapshots/positions` is used.

Broker issue code normalization uses the existing Tachibana issue-code normalizer, so internal `65220` can match Broker `6522` when listed-info allows it.

## Missing Behavior

If Broker available quantity evidence is missing:

```text
status=REVIEW_REQUIRED
demo_submit_executed=false
submitted_count=0
pending_consumed=false
broker_available_quantity_checked=false
broker_available_quantity_source=missing
broker_available_quantity=null
sell_quantity_guard_status=BROKER_AVAILABLE_MISSING
violated_policy=broker_available_quantity
```

Current quantity is not used as a substitute.

## Insufficient Behavior

If:

```text
SELL quantity > Broker available quantity
```

Then:

```text
status=REVIEW_REQUIRED
demo_submit_executed=false
submitted_count=0
pending_consumed=false
broker_available_quantity_checked=true
sell_quantity_guard_status=BROKER_AVAILABLE_INSUFFICIENT
violated_policy=broker_available_quantity
```

## Confirmed Behavior

If:

```text
SELL quantity <= Current quantity
SELL quantity <= Broker available quantity
Policy consistency PASS
SELL liquidation policy allows
```

Then:

```text
broker_available_quantity_checked=true
broker_available_quantity_source=broker_readonly
sell_quantity_guard_status=PASS
```

The guard continues to existing submit preflight. Tests use safe fake adapter / dry path only.

## Manifest Fields

Submit Guard item evidence now includes:

```text
broker_available_quantity_checked
broker_available_quantity_source
broker_available_quantity
broker_available_quantity_symbol
broker_available_quantity_issue_code
broker_available_quantity_snapshot_path
broker_available_quantity_snapshot_at
broker_available_quantity_review_required
broker_available_quantity_production_equivalent
broker_total_quantity
broker_restricted_quantity
broker_available_quantity_account_type
current_quantity
current_position_source
sell_quantity
sell_quantity_guard_status
```

## Tests

Executed:

```text
python3 -m pytest tests/runtime_v2/test_phase15m_sell_broker_available_quantity_evidence.py tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py tests/runtime_v2/test_phase14e32_sell_runtime_io_contract.py
python3 -m pytest tests/runtime_v2/test_phase15m_sell_broker_available_quantity_evidence.py tests/runtime_v2/test_phase15l_submit_policy_hash_consistency_guard.py tests/runtime_v2/test_phase15k_morning_policy_propagation_hidden_policy_removal.py tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py tests/runtime_v2/test_phase15h_capital_deployment_policy.py tests/runtime_v2/test_phase14e15_morning_ai_planning_pending_connection.py tests/runtime_v2/test_phase14e36_feature_date_contract_carryover_policy.py tests/runtime_v2/test_phase14e17_submit_pipeline_connection.py tests/runtime_v2/test_phase14e19_submit_issue_code_normalization.py tests/runtime_v2/test_phase14e32_sell_runtime_io_contract.py tests/runtime_v2/test_phase14e50_sell_planning_runtime_connection.py tests/runtime_v2/test_phase14e11_daily_operation_scheduler.py tests/runtime_v2/test_phase13_p_pending_models.py tests/runtime_v2/test_phase13_p_pending_consume.py tests/runtime_v2/test_phase14d14_demo_sell_guarded_preflight.py
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py tests/runtime_v2/test_phase15m_sell_broker_available_quantity_evidence.py
```

Result:

```text
PASS
```

## Still Not Fixed

Intentionally left for later Phase15 subphases:

- Safety formal connection
- Report policy reason propagation
- Notification policy reason propagation
- Operator Review apply path
- Candidate / Opportunity AI direct execution contract
- Position Management AI -> SELL Planning formal connection

## Prohibited Actions Check

Not performed:

- Broker Write
- Demo order
- Production order
- Notification real send
- launchd / plist modification
- Current direct edit
- Runtime bypass creation
- fake adapter Full Runtime PASS declaration
- Safety formal connection
- Report / Notification propagation

## Final Judgment

```text
PHASE15M_SELL_BROKER_AVAILABLE_QUANTITY_EVIDENCE_COMPLETE
```
