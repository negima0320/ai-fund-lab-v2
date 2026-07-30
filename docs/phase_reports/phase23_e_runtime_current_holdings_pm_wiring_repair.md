# Phase23-E: Runtime-owned Current Holdings to Strategy Position Management Wiring Repair

Generated: 2026-07-28T00:00:00+09:00

## Primary Judgment

`PHASE23_E_RUNTIME_CURRENT_HOLDINGS_PM_WIRING_REPAIR_COMPLETE_SHORT_VALIDATION_PASS`

## Secondary Judgment

- `LONG_RUNTIME_VALIDATION_NOT_RUN`
- `READY_FOR_CHATGPT_EVIDENCE_REVIEW`

## 修正内容

Phase23-Aで確認された `POSITION_LIFECYCLE_INPUT_WIRING_GAP` を修正した。Runtime Currentに保有があるのにStrategy PMが `positions=[]` になる経路を、Production / Demo / Historical共通のAdapter Contractで接続した。

- Strategy ShadowがRuntime Current summary rowsを `runtime_current_positions` としてStrategy PM producerへ渡す。
- Strategy PM producerが `runtime_current_holdings_to_strategy_pm.v1` AdapterでPM positionsへ正規化する。
- 既存PM decisionが無い保有はHOLD固定せず `UNRESOLVED` として保持する。
- quantity等のRuntime Current情報はPM top-level quantity decisionにせず、`adapter_source_contract` にlineageとして保持する。
- Accepted Generationはbusiness-date-bound resolver由来の `PMAcceptedGenerationReference` を維持する。

## PM Contract確認結果

PASS。PM artifactの既存schemaを維持し、top-level quantity fieldsは禁止のまま。`positions=[]` 固定、`shadow_positions=null` 固定、HOLD固定fallbackは追加していない。

## Runtime SoT確認結果

PASS。正式SoTは `persistent_ledger/state.json`。Current Portfolio SummaryはStrategy Shadow内部のread-side carrierであり、SoT置換ではない。

## Accepted Generation確認結果

PASS。Strategy Shadowは `resolve_accepted_generation(runtime_root, business_date=business_date)` を使い、PM Adapter contractにも accepted generation id/hash を保持する。latest fallbackなし。

## Horizontal Audit結果

PASS。Runtime Current / Persistent Ledger / Position Lifecycle / Current Portfolio Summary / Position Management / Shadow Runtime / Accepted Generation / Current Valuation / Data Readiness を確認。

## 修正対象ファイル

- `src/ai_fund_lab_v2/strategy/position_management.py`
- `src/ai_fund_lab_v2/strategy/shadow_runtime.py`
- `tests/strategy/test_phase22_d_position_management.py`
- `tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py`

## 成果物

- `docs/phase_reports/phase23_e_runtime_current_holdings_pm_wiring_repair.md`
- `reports/phase_reports/phase23_e_runtime_current_holdings_pm_wiring_repair.json`
- `reports/phase23_e_runtime_current_holdings_pm_wiring_repair/`

## 短時間テスト結果

- Phase23-E targeted regressions: `2 passed`
- Strategy PM + Shadow: `15 passed`
- Runtime PM connection: `6 passed`
- Phase23-B/C/D regressions: `26 passed`
- compileall with `/tmp` pycache: PASS

## 未実施長時間テスト

10BD / 20BD / 1y / 3y Runtime Test は未実施。Runtime Switch、Broker Write、Production/Demo Submitも未実施。

## 残存Gap

Corporate Event source coverage と Candidate downstream blockers は本Task対象外で未修正。

## 次Task候補

1. Corporate Event / Candidate downstream repair.

## 10BD再実行可否

`NOT_READY_FOR_10BD_RERUN`
