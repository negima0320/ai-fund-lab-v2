# Phase17-AF Day2 Morning Temporal Authority Closure

## 判定

`PHASE17_AF_DAY2_MORNING_TEMPORAL_AUTHORITY_ACCEPTED`

Frozen Run `runtime-test-historical-smoke-20260715T031756327500Z` は変更・resume・再実行していない。

## Frozen Evidence

Day2 `2026-07-07:data_readiness` は `readiness_scope=morning` で停止した。

- `current_valuation_not_ready`
- `historical_safety_temporal_authority_missing`

観測値は `position_state_as_of=2026-07-06`、`valuation_as_of=2026-07-06`、`current_expected_as_of=2026-07-07`、`current_actual_as_of=2026-07-06`。評価時刻は `2026-07-07T08:05:00+09:00` であり、当日終値はまだ正式に存在しない。

## Root Cause

`current_valuation_not_ready` は Temporal Authority Bug。Morning readinessでもCurrent Valuation期待日が `business_date` として扱われ、前営業日終値が最新正式valuationである時間帯をSTALEとしていた。Position stateのcarry policyとValuation stateのclose authorityが分離されていなかった。

`historical_safety_temporal_authority_missing` は Integration Bug。Day1でCONSUMEDになったpending slotのhistorical safety contextはDay1 `target_session_date` に属するが、Day2 morningでも `safety_business_date == business_date` を要求していたため、消費済み安全Authorityの継続性が途切れていた。

## 修正

`src/ai_fund_lab_v2/runtime_v2/data_readiness.py` にProduction/Demo/Historical共通のCurrent Valuation temporal authorityを追加した。

- Morning scope: previous trading day closeをREADYとして許可
- Morning scope: same-day valuation refresh済みならREADY
- Morning scope: previous trading dayより古ければREVIEW_REQUIRED
- Evidence欠落はREVIEW_REQUIRED
- Future dateはHALT
- `current_valuation` scopeなど非Morningではbusiness_date closeを維持

Evidence fields:

- `current_valuation_expected_date`
- `current_valuation_expected_date_policy`
- `current_valuation_previous_trading_date`
- `current_valuation_same_day_allowed`
- `current_valuation_previous_close_carry_allowed`
- `current_valuation_temporal_authority`
- `current_valuation_temporal_reason`

また、consumed prior-session pendingについては、`target_session_date < business_date` かつCONSUMEDの場合、historical safety contextの期待 `safety_business_date` をpendingの `target_session_date` として評価する。これはHistorical専用緩和ではなく、消費済みpending evidenceのidentity/temporal ownershipを維持するためのRuntime統合修正である。

## Verification

- `PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_af_day2_morning_temporal_authority.py`
  - `3 passed`
- `PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_af_day2_morning_temporal_authority.py tests/runtime_v2/test_phase17_ab_current_valuation_pre_gate_authority.py tests/runtime_v2/test_phase17_aa_historical_current_valuation_authority.py tests/runtime_v2/test_phase17_x_historical_sell_planning_authority.py`
  - `24 passed`
- `PYTHONPYCACHEPREFIX=/private/tmp/phase17af_pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/data_readiness.py tests/runtime_v2/test_phase17_af_day2_morning_temporal_authority.py`
  - PASS

Runtime Test Runnerは実行していない。Frozen Runおよび実 `.runtime` は変更していない。
