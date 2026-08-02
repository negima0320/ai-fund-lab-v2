# Phase24-IK Historical Submit Corporate Action Guard Repair

## 1. Primary Judgment

`PHASE24_IK_CORPORATE_ACTION_GUARD_FAIL_CLOSED_VALID_OBSERVABILITY_REPAIRED_OPERATOR_CORPORATE_ACTION_AUTHORITY_REQUIRED`

## 2. Repair Scope

The repair is observability-only for the Historical Submit Corporate Action Guard.

No changes were made to:

- Strategy
- Ranking
- Eligibility
- PM decision logic
- Position Sizing policy
- Submit Guard thresholds
- Safety Guard
- Broker write contract
- Historical Runtime resume behavior

## 3. Code Change

Updated `src/ai_fund_lab_v2/runtime_v2/historical_support/environment.py`:

- Replaced the internal guard call with `_corporate_action_evidence`.
- Kept `_corporate_action_status` as a compatibility wrapper.
- Preserved fail-closed behavior for:
  - missing raw OHLCV
  - unreadable raw OHLCV
  - missing code column
  - missing target-symbol row
  - missing `AdjFactor`
  - target-date target-symbol `AdjFactor != 1.0`

## 4. Evidence Added

When the Corporate Action Guard blocks, response classification now includes:

- `corporate_action_guard_version`
- `corporate_action_artifact_path`
- `corporate_action_source`
- `corporate_action_business_date`
- `corporate_action_symbol`
- `corporate_action_type`
- `corporate_action_type_authority`
- `corporate_action_effective_date`
- `corporate_action_record_date`
- `corporate_action_adjustment_factor`
- `corporate_action_adjustment_factors`
- `corporate_action_old_symbol`
- `corporate_action_new_symbol`
- `corporate_action_old_quantity`
- `corporate_action_new_quantity`
- `corporate_action_old_price`
- `corporate_action_new_price`
- `corporate_action_listing_continuity_status`
- `corporate_action_rows`
- `corporate_action_impact_detected_condition`

## 5. 65730 Repair Result

For `65730` on `2023-10-04`, the repaired classifier resolves:

- `corporate_action_status`: `IMPACT_DETECTED`
- `corporate_action_type`: `UNKNOWN_ADJFACTOR_IMPACT`
- `corporate_action_effective_date`: `2023-10-04`
- `corporate_action_adjustment_factor`: `0.3333333333333333`
- `corporate_action_impact_detected_condition`: `target_date_target_symbol_adjfactor_not_1`

This does not convert the submit to PASS. It makes the fail-closed reason inspectable.

## 6. Validation

- `PYTHONPYCACHEPREFIX=/private/tmp/phase24_ik_pycache PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_bv8_historical_submit_pit_universe_authority.py tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py tests/runtime_v2/test_phase22_pu_historical_submit_source_identity.py`: `26 passed`
- `PYTHONPYCACHEPREFIX=/private/tmp/phase24_ik_pycache PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_bv8_historical_submit_pit_universe_authority.py tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py tests/runtime_v2/test_phase22_pu_historical_submit_source_identity.py tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py`: `30 passed`
- `PYTHONPYCACHEPREFIX=/private/tmp/phase24_ik_pycache PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase15n_safety_operation_guard_runtime_connection.py::test_phase15n_safety_missing_blocks_submit_before_broker tests/runtime_v2/test_phase15n_safety_operation_guard_runtime_connection.py::test_phase15n_safety_halt_stops_submit`: `2 passed`
- Python compile: `PASS`
- Runtime executed: `NO`

## 7. Remaining Required Work

Formal Corporate Action Adjustment Authority is still required. The current repair does not decide adjusted quantity, adjusted average price, or adjusted Pending quantity. It only exposes the fail-closed evidence needed for the next implementation task.
