# Phase17-BP Clean Reset Plan Feature Date Entry Gate Fix

## Executive Summary

Phase17-BP investigated a Clean Reset -> Backup -> Plan failure where the Runtime Test plan entry gate required materialized Feature Date Contract artifacts immediately after reset. This created a circular dependency: reset correctly removed `.runtime/operations/feature_date_contract`, while `plan` required those contracts before the runtime `market_refresh` producer could recreate them.

Root cause is confirmed and fixed. `plan` now emits non-authoritative schedule expectation evidence when a Feature Date Contract is not yet materialized, while preserving fail-closed validation for any existing materialized contract. Run-time authority remains the normal materialized Feature Date Contract produced by Runtime v2 and validated by Data Readiness.

Final judgment:

```text
PHASE17_BP_PLAN_ENTRY_GATE_FIX_ACCEPTED
```

## Root Cause

`scripts/runtime_test.py` had applied the Phase17-BL Feature Date authority rule too early in the lifecycle. `resolve_feature_date()` loaded `.runtime/operations/feature_date_contract/{business_date}.json`, and `validate_plan_entry_gate()` required:

- `source == normal_feature_date_contract`
- `contract_materialized == true`
- `materialized_contract_exists == true`
- selected feature date matches the profile expectation

After a clean reset, the Feature Date Contract directory is intentionally absent. Because `plan` ran before the normal Runtime producer, every planned day failed with `feature_date_authority_mismatch` / missing materialization even though the reset state was correct.

## Design Contract

The corrected contract separates Plan expectation from Run authority:

- `plan` may compute a non-authoritative schedule expectation for command construction and evidence.
- `plan` must not create or restore normal Runtime Feature Date Contracts.
- If a materialized Feature Date Contract already exists at Plan time, it must be inspected and mismatches must fail closed.
- During Run, the normal Runtime producer remains responsible for materializing the Feature Date Contract.
- Data Readiness remains responsible for rejecting CLI feature date vs materialized contract mismatches.
- Profile values are never restored as Runtime authority; they are only Plan schedule expectations.

## Implementation

Updated `scripts/runtime_test.py`:

- Missing contract now resolves to `source=runtime_test_plan_schedule_expectation`.
- Missing contract evidence uses `feature_date_authority_source=not_yet_materialized_plan_expectation`.
- `contract_materialized=false` and `materialized_contract_exists=false` are valid only for Plan expectation evidence.
- Existing materialized contracts continue to use `source=normal_feature_date_contract`.
- Existing stale/review/mismatched materialized contracts still fail Plan Entry Gate.
- Evidence includes `run_authority_required_stage=runtime_market_refresh_and_data_readiness`.

Updated tests:

- Added Phase17-BP clean reset plan tests.
- Updated AE/AL/L plan-fixture expectations to the new Plan expectation contract.
- Updated scheduler fixture to mock the formal BUY AI producer, keeping the scheduler test scoped to launch/guard behavior.
- Updated `.runtime` hash assertions to match the current clean reset baseline without mutating `.runtime`.

## Plan And Run Authority Separation

Clean Reset removes:

```text
.runtime/operations/feature_date_contract
.runtime/operations/feature_consumer_readiness
.runtime/operations/feature_artifacts
.runtime/operations/feature_refresh
```

Plan after reset now succeeds because this state is treated as:

```text
authority_status=NOT_YET_MATERIALIZED
source=runtime_test_plan_schedule_expectation
feature_date_authority_source=not_yet_materialized_plan_expectation
profile_value_used_as_authority=false
```

Run still fails closed if the materialized Runtime contract later disagrees with the planned CLI feature date. This is verified through Data Readiness `_feature_date_contract_payload()`, which returns `REVIEW_REQUIRED` and `feature_date_authority_mismatch` when CLI and materialized contract differ.

## 2026-07-09 Carryover

The historical smoke profile expectation remains:

```text
2026-07-09 -> 2026-07-08
```

Plan now uses this as schedule evidence only. It does not materialize the 2026-07-09 Runtime contract. The normal Runtime producer must still generate the official carryover authority during Run.

## Regression Results

Commands executed:

```bash
PYTHONPATH=src python3 -m pytest tests/runtime_v2/test_phase17_bp_clean_reset_plan_feature_date_entry_gate.py tests/runtime_v2/test_phase17_ae_reset_scope_plan_gate.py tests/runtime_v2/test_phase17_bl_feature_date_authority_unification.py tests/runtime_v2/test_phase17_m_consumer_wiring_and_feature_temporal_authority.py -q
```

Result:

```text
14 passed
```

```bash
PYTHONPATH=src python3 -m pytest tests/runtime_v2/test_phase17_bl_feature_date_authority_unification.py tests/runtime_v2/test_phase17_bj_historical_daily_neutral_safety_authority.py tests/runtime_v2/test_phase17_bh_current_valuation_refresh_temporal_contract.py tests/runtime_v2/test_phase17_al_runtime_test_clean_baseline_guard.py -q
```

Result:

```text
34 passed
```

```bash
PYTHONPATH=src python3 -m pytest tests/runtime_v2 -q
```

Result:

```text
872 passed
```

```bash
git diff --check
```

Result: PASS.

```bash
PYTHONPATH=src PYTHONPYCACHEPREFIX=.pytest_pycache python3 -m py_compile scripts/runtime_test.py src/ai_fund_lab_v2/runtime_v2/data_readiness.py src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py src/ai_fund_lab_v2/runtime_v2/market_refresh/feature_date_contract.py
```

Result: PASS.

The initial py_compile attempt without `PYTHONPYCACHEPREFIX` failed because macOS Python attempted to write under `/Users/negishi/Library/Caches/com.apple.python/...`; it was rerun with a workspace-local pycache prefix and passed. The temporary pycache directory was removed.

## Registry Impact

No Registry refresh was performed. No producer identity refresh was required by this fix. The change is limited to Runtime Test planning semantics and isolated test fixtures.

## Prohibited Operations Confirmation

Not performed:

- `runtime_test.py run`
- `runtime_test.py resume`
- `runtime_test.py reset`
- `runtime_test.py rollback`
- `runtime_test.py close`
- Frozen Run editing
- Trading State manual editing
- manual generation of `.runtime/operations/feature_date_contract`
- broker write
- order submit
- external notification
- J-Quants fetch
- Registry refresh

## Clean Historical Smoke Re-entry

Clean Historical Smoke can re-enter at the Plan stage after reset/backup. The Plan should now pass with non-authoritative schedule expectations and will not require pre-existing Feature Date Contracts. Run-time materialization and Data Readiness mismatch detection remain fail-closed.
