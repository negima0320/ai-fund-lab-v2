# Phase9 2026-06-17 Recovery

## 結論

```text
PHASE9_2026_06_17_RECOVERY_COMPLETE
```

2026-06-17分のPaper Tradingは、2026-06-17終値をcanonical quotesへ反映したうえでLedger Valuationを再実行し、Ledger / Blog Report / Trackerを回復した。

## 背景

2026-06-17のUnified Runnerでは、`--allow-api-fetch`相当の運用意図があったにもかかわらず、market data refreshがUnified Runner内で実行されなかった。

そのため実行時点のcanonical quotes最大日付が2026-06-16に留まり、2026-06-17 runでも以下の状態でLedger Valuationが実行された。

```text
data_target_date: 2026-06-16
valuation_date: 2026-06-16
quote_source_max_date: 2026-06-16
```

この結果、2026-06-16と2026-06-17のLedger評価値が完全一致した。

## Backup

回復前に以下へバックアップを作成した。

```text
.runtime/phase9/recovery_backups/2026-06-17_20260617T202729
```

対象:

```text
.runtime/phase9/ledger/latest.json
.runtime/phase9/tracker/
.runtime/daily_operation/runs/2026-06-17/
.runtime/daily_operation/operation_logs/2026-06-17_operation_log.json
.runtime/daily_operation/operation_logs/2026-06-17_operation_log.md
reports/public/phase9_daily/2026-06-17_blog_report_v4.md
reports/public/phase9_daily/2026-06-17_blog_report_v4.json
```

## Market Data Recovery

J-Quantsから2026-06-17分を取得し、raw / raw_normalized / canonical quotesを更新した。

```text
market_data_refresh_status: MARKET_DATA_READY_FOR_LATEST_AVAILABLE
latest_successful_daily_quotes_date: 2026-06-17
latest_normalized_daily_quotes_date: 2026-06-17
canonical_max_date: 2026-06-17
```

Canonical source:

```text
.runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet
```

## Holding Close Verification

保有銘柄5件について、2026-06-16終値と2026-06-17終値を確認した。

```text
15790: 2026-06-16 close 845.8 -> 2026-06-17 close 859.9
166A0: 2026-06-16 close 1112.0 -> 2026-06-17 close 1120.0
213A0: 2026-06-16 close 542.5 -> 2026-06-17 close 550.0
221A0: 2026-06-16 close 1530.0 -> 2026-06-17 close 1553.5
30630: 2026-06-16 close 1137.0 -> 2026-06-17 close 1104.0
```

## Ledger Recovery

2026-06-17終値でLedger Valuationを再実行した。

```text
run_id: recovery_2026_06_17
valuation_date: 2026-06-17
expected_valuation_date: 2026-06-17
quote_source_max_date: 2026-06-17
stale_price_source: false
status: LEDGER_VALUATION_UPDATED
```

Valuation output:

```text
.runtime/phase9/ledger_valuations/run_date=2026-06-17/valuation_date=2026-06-17_recovery_2026_06_17/
```

Ledger差分:

```text
market_value: 709,810 -> 714,730
total_equity: 993,140 -> 998,060
unrealized_pnl: -6,860 -> -1,940
change: +4,920
```

回復後の保有:

```text
15790 qty 200 market_value 171,980 unrealized_pnl +2,620 holding_days 2
166A0 qty 100 market_value 112,000 unrealized_pnl +2,900 holding_days 2
213A0 qty 300 market_value 165,000 unrealized_pnl +1,590 holding_days 2
221A0 qty 100 market_value 155,350 unrealized_pnl +1,550 holding_days 2
30630 qty 100 market_value 110,400 unrealized_pnl -10,600 holding_days 2
```

## Holding Days

2026-06-17 runのstale再評価で`holding_days`が不正に進んだ可能性があったため、回復前に補正用staging ledgerを作成した。

方針:

```text
2026-06-16 EOD: holding_days = 1
2026-06-17 EOD: holding_days = 2
同一 valuation_date 再実行では holding_days を増やさない
```

回復後、全5銘柄で以下を確認した。

```text
holding_days: 2
last_valuation_date: 2026-06-17
```

## Blog Report

2026-06-17のv4ブログレポートを再生成した。

```text
reports/public/phase9_daily/2026-06-17_blog_report_v4.md
reports/public/phase9_daily/2026-06-17_blog_report_v4.json
```

確認:

```text
valuation_date: 2026-06-17
quote_source_max_date: 2026-06-17
stale_price_source: False
現在資産: 998,060円
含み損益: -1,940円
Data Quality: 出力なし
```

## Tracker Recovery

30営業日TrackerのDay2を回復後Ledgerに合わせて補正した。

```text
status: UNIFIED_DAILY_RUN_DONE_RECOVERED
paper_total_equity: 998060.0
market_value: 714730.0
unrealized_pnl: -1940.0
valuation_date: 2026-06-17
quote_source_max_date: 2026-06-17
stale_price_source: false
progress: 2/30
```

## Recovery Operation Log

回復操作ログを作成した。

```text
.runtime/daily_operation/recovery_logs/2026-06-17_recovery_operation_log.json
.runtime/daily_operation/recovery_logs/2026-06-17_recovery_operation_log.md
```

## 実行コマンド

Market data refresh:

```bash
python3 scripts/run_phase9i_market_data_refresh.py --from-date 2026-06-17 --to-date 2026-06-17 --no-dry-run --allow-api-fetch --fetch-mode per-date --markdown-report-path docs/phase_reports/phase9_2026_06_17_market_data_refresh.md --json-report-path reports/phase_reports/phase9_2026_06_17_market_data_refresh.json
```

Canonical update:

```bash
python3 scripts/run_phase9q_update_canonical_normalized_for_date.py --target-date 2026-06-17 --execute
```

Ledger recovery:

```text
update_ledger_valuation_from_files(... valuation_date=2026-06-17, expected_valuation_date=2026-06-17, run_id=recovery_2026_06_17 ...)
```

## 検証結果

軽量検証のみ実施した。重いバックテストは実行していない。

```text
canonical_max_date: 2026-06-17
holding_close_prices: 5/5 confirmed
ledger_latest_updated: true
valuation_manifest stale_price_source: false
blog_report_v4 regenerated: true
tracker Day2 recovered: true
```

## 再開可否

2026-06-17分のPaper Trading結果は回復済み。

ただし、Unified Runner単独ではmarket refresh実接続がまだ本実装されていない。翌営業日以降の30営業日検証は、事前にmarket refreshとcanonical updateを実行する運用手順を組み込むか、Unified Runnerへ実refresh接続を実装したうえで再開する。

