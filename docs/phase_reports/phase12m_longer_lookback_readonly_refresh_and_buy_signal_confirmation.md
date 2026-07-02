# Phase12-M Longer Lookback Read-only Refresh & BUY Signal Confirmation

## Status

`PHASE12M_LONGER_LOOKBACK_READONLY_REFRESH_AND_BUY_SIGNAL_CONFIRMATION_COMPLETE`

Phase12-Lで特定した`insufficient_lookback`起因のBUY=0を確認するため、Operations default lookback 140 calendar daysの状態でJ-Quants read-only refreshを実行した。

Demo Order Wire Execution、Demo注文、Production注文、LINE実送信、AI再学習、Backtest再実行は実施していない。

## Execution

実行したread-only / smoke CLI:

```bash
python3 scripts/run_market_refresh.py --trade-date 2026-06-29 --root .runtime/operations --allow-api-fetch
python3 scripts/run_daily_plan.py --trade-date 2026-06-29 --root .runtime/operations
python3 scripts/run_daily_report.py --trade-date 2026-06-29 --root .runtime/operations
python3 scripts/run_operation_audit.py --root .runtime/operations
```

`run_market_refresh.py`ではJ-Quants実APIをread-onlyで呼び出した。Broker order API、CLMKabuNewOrder、Production unlockは呼び出していない。

## Market Refresh Result

| Item | Value |
| --- | --- |
| lookback calendar days | 140 |
| requested from date | 2026-02-09 |
| requested to date | 2026-06-29 |
| latest available market date | 2026-06-26 |
| data until | 2026-06-26 |
| J-Quants API fetch | executed |
| market refresh status | PASS |
| data quality status | PASS |
| feature freshness status | FEATURE_READY |
| raw daily quote rows | 168,997 |
| normalized rows | 160,349 |
| listed info rows | 4,436 |
| trading calendar rows | 141 |

2026-06-29分のdaily quotesは未提供だったため、`latest_available_market_date`と`data_until`は2026-06-26になった。これは当日未提供データを無理に使わず、利用可能な最新市場日でfeatureを生成する挙動。

Market detailには`daily_quotes_normalization_status=ERROR` warningが残ったが、canonical normalized rowsは160,349件存在し、feature refreshはPASSした。

## Feature / Candidate Path

| Item | Value |
| --- | --- |
| candidate feature path | `.runtime/operations/feature_artifacts/2026-06-26/candidate_features.parquet` |
| opportunity feature path | `.runtime/operations/feature_artifacts/2026-06-26/opportunity_feature_input.parquet` |
| feature rows | 4,303 |
| universe rows before hard gate | 4,303 |
| universe rows after hard gate | 3,681 |
| candidate count | 3,681 |
| opportunity count | 4,303 |
| BUY order plan count | 1 |
| BUY zero reason | empty |

BUY signalは復元した。Phase12-Lの`universe after gate=0`から、Phase12-Mでは`3,681`まで復元している。

## Candidate Gate Details

candidate universe exclusion reason counts:

| Reason | Count |
| --- | ---: |
| eligible | 3,681 |
| disallowed_product | 504 |
| insufficient_lookback | 6 |
| insufficient_lookback,disallowed_product | 10 |
| insufficient_lookback,not_current_listed,missing_name,stale_price,disallowed_product | 15 |
| insufficient_lookback,stale_price | 3 |
| insufficient_lookback,stale_price,disallowed_product | 21 |
| not_current_listed,missing_name,disallowed_product | 4 |
| not_current_listed,missing_name,stale_price,disallowed_product | 17 |
| stale_price | 30 |
| stale_price,disallowed_product | 12 |

Phase12-Lでは`insufficient_lookback`が主要因でeligible rowsが0件だった。Phase12-Mではeligible rowsが3,681件となり、lookback不足は局所的な除外理由に縮小した。

## Daily Report / Audit Reflection

Daily Report:

- status: PASS
- J-Quants API fetch: true
- latest_available_market_date: 2026-06-26
- feature rows: 4,303
- universe before / after gate: 4,303 / 3,681
- candidate count: 3,681
- opportunity count: 4,303
- BUY count: 1
- BUY zero reason: empty
- submit status: STALE_IGNORED
- Demo Order Wire Execution: false
- LINE send: false

Operation Audit:

- status: PASS
- BUY count: 1
- broker_order_api_called: false
- demo_order_wire_execution: false
- line_send_executed: false
- Phase9 isolation audit: PASS

## Safety / Data Use

維持したルール:

- AI再学習なし
- Backtest再実行なし
- Broker Snapshot / Paper Ledger / Safety Result / Audit Result / PnL / cash / portfolio / selected / bought / affordable dataをAI学習へ混入していない
- raw broker response保存なし
- secrets保存なし
- Phase9 artifact / launchd / CLI / moduleの変更なし

## Judgement

Phase12-Mの目的である「140 calendar days lookbackによるread-only refreshでcandidate hard gate後のeligible rowsとBUY candidateが復元するか」はPASS。

Demo Wire Unlock前のBUY判断材料は、少なくともpath不一致やlookback不足による全滅状態からは復旧した。

## Remaining Gaps

- 2026-06-29のdaily quotesは未提供のため、feature data_untilは2026-06-26
- market detailに`daily_quotes_normalization_status=ERROR` warningが残るため、次フェーズでwarningの実害有無を監視する
- Demo Order Wire Executionは引き続きロック

## Next Phase

`PHASE12-N_DEMO_WIRE_UNLOCK_PREFLIGHT_REVIEW`

推奨する次タスク:

1. Demo Wire Unlock前の最終preflight review
2. BUY itemのApproval / Safety / MAX_EXPOSURE接続確認
3. Submit pathがstubからwireへ切り替わる条件を再確認
4. CLMKabuNewOrderが明示unlockなしに呼ばれないことを監査
5. Demo注文wire executionを解禁するか最終判断する
