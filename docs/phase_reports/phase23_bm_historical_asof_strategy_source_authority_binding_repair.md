# Phase23-BM Historical As-of Strategy Source Authority Binding Repair

## Primary Judgment

`PHASE23_BM_HISTORICAL_ASOF_STRATEGY_SOURCE_BINDING_SHORT_VALIDATION_PASS`

## Root Cause

Phase23-BLで確定したRoot Causeは、Historical As-of materializationには`2022-07-01`時点のrun-scoped PIT sourceが存在する一方、Strategy producersが`.runtime/operations/jquants/...`を直接参照していたsource authority binding gapである。

対象Run: `runtime-test-historical-smoke-20260730T082859880393Z` / business_date `2022-07-01`。

## Repair

共通resolver `_resolve_strategy_source_authority` をStrategy shadow wiringへ追加し、Historical As-ofの `logical_input_manifest.json` が存在する場合は、そのauthorized logical pathsをStrategy source authorityとして解決するようにした。manifest欠損・invalidの場合はoperationsへfallbackせずfail-closedする。

Production / Demo相当でHistorical As-of view/manifestが無い場合は、従来どおりoperations canonical source authorityを使用する。

## Producer Binding

- Market Context: `normalized_ohlcv` / `listed_issues` / `trading_calendar` をresolver結果から受け取る。
- Corporate Event: `listed_issues` / `trading_calendar` をresolver結果から受け取り、Historicalでは未承認のearnings/fins/actionsへlatest fallbackしない。
- Technical Features: resolver済み `normalized_ohlcv` からmaterialized strategy inputを生成する。
- Price Volatility: resolver済み `normalized_ohlcv` からmaterialized strategy inputを生成する。
- Source Manifest: `input_manifest.strategy_source_authority`を参照し、PIT集計も同じsource authorityで行う。

## Canonical 2022 Reproduction

`/private/tmp/phase23_bm_repro_run` で既存Runを変更せず短時間再現した。

- Market Context: `PASS`
- Corporate Event: `PASS`
- Technical Features: `PASS` / coverage `FULL`
- Price Volatility: `PASS` / coverage `FULL`
- Portfolio Policy: `PASS`
- Runtime Planning: `PASS`
- Source Manifest PIT: `PASS`
- future source row rejection: `0`
- latest fallback: `false`

Strategy shadow summary自体はisolated reproductionで`REVIEW_REQUIRED`が残るが、source binding由来ではない。`root_blocker_components=[]`、`root_reason_codes=[]`、source PITは`PASS`。

## Negative / Regression

- Historical manifest missing: fail-closed、operations fallbackなし。
- Production/Demo no-asof: operations canonical source preserved。
- Hash mismatch:既存Market Context/Corporate Event producerの`expected_source_hashes` contractでBLOCK。BMではrun-scoped manifest hashをこの経路へ配線。
- Future rows: Producer/Source Manifest PIT検証でreject維持。

## Modified Files

- `src/ai_fund_lab_v2/strategy/shadow_runtime.py`
- `src/ai_fund_lab_v2/strategy/source_manifest.py`
- `tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py`

## Short Validation

- `py_compile`: PASS
- `tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py`: 10 passed
- Targeted regression: 67 passed
- Isolated 2022 reproduction: PASS for BM source binding path

Long Runtime / fresh-run / 1BD / 10BD / J-Quants fetch / Broker Writeは実施していない。

## Evidence

- `reports/phase23_bm_historical_asof_strategy_source_authority_binding_repair/`
- `reports/phase_reports/phase23_bm_historical_asof_strategy_source_authority_binding_repair.json`

## Existing Run Preservation

BL時点hashと現在hashを比較し、指定3Runの既存artifact mutationは検出されなかった。

## Next Operator Action

`READY_FOR_2022_10BD_RUNTIME_RERUN = YES`。Operator側で2022年10BD Runtime rerunへ進める。
