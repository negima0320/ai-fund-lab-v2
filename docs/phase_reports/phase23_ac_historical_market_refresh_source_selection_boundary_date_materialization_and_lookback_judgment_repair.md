# Phase23-AC: Historical Market Refresh Source Selection, Boundary-Date Materialization, and Lookback Judgment Repair

## 1. Primary Judgment

`PHASE23_AC_HISTORICAL_MARKET_REFRESH_BOUNDARY_DATE_AND_LOOKBACK_AUTHORITY_REPAIRED_SHORT_VALIDATION_PASS`

## 2. Phase23継続確認

Phase23は継続。Phase完了、Phase24移行、Production ready、10BD ready とは判定しない。

## 3. Exact Root Cause

Primary root causeは `BOUNDARY_DATE_QUOTE_SOURCE_MISSING_FOR_2026_07_15`。

保存済みHistorical OHLCV sourceは、operations canonical / acquisition stagingのいずれも `2026-07-15` quote rowsを持たない。一方で、listed issues と trading calendar は `2026-07-15` authorityを持っていた。

Secondary root causeは以下。

- `HALT_PATH_SKIPPED_PASS_AUTHORITY_MATERIALIZATION`
- `LOOKBACK_REASON_COLLAPSED_TARGET_DATE_MISSING_INTO_WARMUP_INSUFFICIENT`
- `API_NOT_REQUESTED_CLASSIFIED_AS_API_ERROR`
- `GENERIC_MARKET_REFRESH_BLOCKED_REASON_MASKED_DIRECT_BLOCKER`

## 4. Historical Source Inventory

`reports/phase23_ac_historical_market_refresh_source_selection_boundary_date_materialization_and_lookback_judgment_repair/historical_source_inventory.json` に保存。

確認結果:

- operations normalized OHLCV: latest `2026-07-14`, `2026-07-15` rows `0`
- operations raw OHLCV: latest `2026-07-14`, `2026-07-15` rows `0`
- acquisition `jquants-acquisition-20210802-20260714-bh`: latest `2026-07-14`, `2026-07-15` rows `0`
- operations listed issues snapshot: `2026-07-15` rowsあり
- operations trading calendar: `2026-07-15` rowsあり

## 5. Boundary-date Semantics

Historical market_refreshは `Date <= business_date` の保存済み入力だけを使用する。ただし `2026-07-15` feature buildを `2026-07-14` quoteで同日扱いにすることは許可しない。

今回の直接理由は `QUOTE_TARGET_DATE_MISSING`。

## 6. Historical As-of Source Resolution

`resolve_historical_market_data_asof(..., require_feature_lookback=True)` のsource selectionを修正。

選択順:

1. PASS candidateを優先
2. PASSが無い場合、target-date availability / calendar target availability / lookback business-day count / row count / latest dateで最良候補を選ぶ

`2026-07-15` の孤立再現では `acquisition_staging` が最良候補として選ばれ、statusはHALT、coverage reasonは `QUOTE_TARGET_DATE_MISSING`。

## 7. Operations vs Acquisition Authority

operations canonicalはRuntime SoTのまま維持。acquisition stagingは、Historical logical inputのread-only候補としてas-of検証を通してのみ参照する。

Runtime market data mutation、Broker Write、J-Quants live fetchは未実施。

## 8. Empty Materialization Audit

HALT時でも、個別AuthorityがPASSしているものはlogical inputへmaterializeするよう修正。

孤立再現では以下が全て存在:

- `normalized_ohlcv`
- `raw_ohlcv`
- `trading_calendar`
- `listed_issues`

これにより、listed/calendar欠損という二次誤報ではなく、OHLCV境界日欠損が直接見える。

## 9. Lookback Sufficiency Contract

`missing_warmup_business_days` と `target_date_missing` を分離。

新しい直接理由:

- `SOURCE_ROWS_EMPTY`
- `QUOTE_TARGET_DATE_MISSING`
- `HISTORICAL_SOURCE_WARMUP_INSUFFICIENT`

`2026-07-15` 選択sourceは `missing_warmup_business_days=0` かつ `target_date_available=false` のため `QUOTE_TARGET_DATE_MISSING`。

## 10. Feature Builder Requirements

Candidate / Opportunity / PM technical featuresは、requested feature dateまでの61 business-day OHLCV windowを要求する。

`2026-07-15` はtarget-date quoteが無いためfail-closed。`2026-07-14` をsilent carryoverして `2026-07-15` feature inputとして扱わない。

## 11. Market Evidence Truthfulness

API未実行のlocal source blockを `API_ERROR` と分類しないよう修正。

`QUOTE_TARGET_DATE_MISSING` / historical source blockでは `LOCAL_SOURCE_UNAVAILABLE` を返す。

## 12. Market Refresh Judgment

genericな `market_refresh_blocked` を直接理由で置き換える経路を追加。

今回のdirect blockerは `QUOTE_TARGET_DATE_MISSING`。

## 13. Safety Propagation

Market refreshはfail-closedのまま維持。既存HALT runの `safety_status=SAFETY_MISSING` / `safety_reason=safety decision evidence missing` はPASSへ書き換えない。

## 14. Previous Seven-day Regression

既存run `runtime-test-historical-extended-smoke-20260729T065337151378Z` を読み取り監査。

`2026-07-06` から `2026-07-14` のmarket_refresh manifestsは存在。既存runは再実行・変更していない。

## 15. 2026-07-15 Short Reproduction

Resolver + logical input materializationのみ実施。長時間Runtimeは未実施。

結果:

- logical status: `HALT`
- logical reason: `historical_feature_lookback_insufficient`
- coverage reason: `QUOTE_TARGET_DATE_MISSING`
- selected source latest date: `2026-07-14`
- selected source target rows: `0`

## 16. Modified Files

- `src/ai_fund_lab_v2/runtime_v2/market_data_bootstrap.py`
- `src/ai_fund_lab_v2/runtime_v2/historical_support/asof.py`
- `src/ai_fund_lab_v2/runtime_v2/market_refresh/pipeline.py`
- `tests/runtime_v2/test_phase20_bb_runtime_market_data_bootstrap.py`
- `tests/runtime_v2/test_phase17_l_historical_asof_and_evidence_isolation.py`

## 17. Short Validation

PASS。

- `py_compile`: PASS
- `pytest tests/runtime_v2/test_phase20_bb_runtime_market_data_bootstrap.py tests/runtime_v2/test_phase17_l_historical_asof_and_evidence_isolation.py -q`: `16 passed`

## 18. 未実施事項

以下は未実施。

- 10BD
- 20BD
- 1年 / 3年
- fresh-run / resume
- Runtime Switch
- Broker Write
- Tachibana API
- J-Quants live fetch

## 19. Existing HALT Evidence Preservation

既存HALT evidenceは読み取りのみ。`reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260729T065337151378Z/` は変更していない。

preservation hashは `existing_halt_evidence_preservation.json` に保存。

## 20. 10BD Rerun Gate

`READY_FOR_OPERATOR_PRODUCTION_EQUIVALENT_10BD_RERUN` ではない。

理由: `2026-07-15` OHLCV sourceが保存済みRuntime inputに存在せず、Operatorによる正規Materialization判断が必要。

## 21. 次のOperator Action

Operatorは `2026-07-15` OHLCVの正規取得・Materialization方針を決めること。

候補:

- 既存J-Quants保存sourceに `2026-07-15` quoteを正規Materializeする
- `2026-07-15` を評価対象外にする明示的run boundaryを定義する
- feature-date carryoverを許可する別Contractを設計する

このTaskでは10BD再実行に進まない。
