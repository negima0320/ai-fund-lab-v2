# Phase9 Ledger Valuation Bug Investigation

Status:

```text
BUG
```

Investigation date:

```text
2026-06-17
```

## Summary

2026-06-17のunified daily runは、2026-06-17の終値でLedger Valuationを行っていない。

実際には、canonical quotesの最新日付が2026-06-16のままだったため、2026-06-17実行でも`data_target_date=2026-06-16`になり、Ledger Valuationも`valuation_date=2026-06-16`で再実行された。

そのため、保有銘柄の`market_value`、`unrealized_pnl`、ledger全体の`cash`、`market_value`、`total_equity`、`unrealized_pnl`が2026-06-16評価後と完全一致した。

## Conclusion

```text
BUG
```

理由:

- 2026-06-17 runで`ledger_valuation: LEDGER_VALUATION_UPDATED`と出ているが、評価対象日は2026-06-17ではなく2026-06-16。
- `--allow-api-fetch`付き運用でも、Unified Runnerはmarket data refreshを実行していない。
- 2026-06-17の終値がcanonical/raw/raw_normalizedのどこにも存在しない。
- 2026-06-17 runが`.runtime/phase9/ledger_valuations/2026-06-16/`を再利用・上書きしている。
- 同一valuation_dateの再評価でも`holding_days`だけ進むため、評価日重複の副作用がある。

## 1. Ledger Valuationの価格ソース

実装:

```text
src/ai_fund_lab_v2/paper_trading/ledger_valuation.py
```

入口:

```text
update_ledger_valuation_from_files(
    ledger_path=...,
    quotes_path=...,
    valuation_date=...,
)
```

Unified Runnerから渡されるデフォルト価格ソース:

```text
.runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet
```

価格読み取り:

```text
_read_close_rows(path, valuation_date)
_close_price_map(rows, valuation_date)
```

参照列:

- `date` または `Date`
- `code` または `Code` または `LocalCode`
- `close` または `Close`

更新式:

```text
market_value = close * quantity
unrealized_pnl = (close - average_cost) * quantity
```

## 2. 2026-06-17実行時の終値取得

2026-06-17 operation log:

```text
.runtime/daily_operation/operation_logs/2026-06-17_operation_log.md
```

Business dates:

```text
run_date: 2026-06-17
data_target_date: 2026-06-16
decision_for: 2026-06-16
virtual_order_date: 2026-06-17
virtual_execution_date: 2026-06-17
```

Market data refresh step:

```text
market_data_refresh: API_FETCH_ALLOWED_BUT_NOT_AUTO_EXECUTED_IN_UNIFIED_RUNNER
canonical_normalized_update: USING_EXISTING_CANONICAL_NORMALIZED
```

つまり、2026-06-17 runではJ-Quants fetchもcanonical rebuildも行われていない。

Unified Runner実装上も、`allow_api_fetch=True`の場合に実fetchへ進まず、次のステータスを設定するだけになっている。

```text
API_FETCH_ALLOWED_BUT_NOT_AUTO_EXECUTED_IN_UNIFIED_RUNNER
```

## 3. 保有銘柄評価額更新処理のスキップ有無

スキップはされていない。

2026-06-17 runでは、Ledger Valuation自体は実行されている。

ただし評価日は2026-06-16。

```text
valuation_date: 2026-06-16
status: LEDGER_VALUATION_UPDATED
missing_price_codes: []
warnings: []
```

2026-06-16終値は全保有銘柄について存在するため、`missing_price_codes`は空になり、正常更新扱いになっている。

問題は「更新がスキップされたこと」ではなく、「2026-06-17 runで2026-06-16終値を再利用していること」。

## 4. 保有銘柄の終値比較

対象:

```text
15790
166A0
213A0
221A0
30630
```

ローカルcanonical source:

```text
.runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet
```

canonical範囲:

```text
min: 2021-06-14
max: 2026-06-16
```

raw / raw_normalized / canonicalのいずれも、2026-06-17行は存在しない。

確認結果:

| code | 2026-06-16 close | 2026-06-17 close |
|---|---:|---:|
| 15790 | 845.8 | MISSING |
| 166A0 | 1112.0 | MISSING |
| 213A0 | 542.5 | MISSING |
| 221A0 | 1530.0 | MISSING |
| 30630 | 1137.0 | MISSING |

補足:

```text
.runtime/data/raw/jquants/equities_bars_daily/data.parquet
max: 2026-06-16

.runtime/data/raw_normalized/jquants/equities_bars_daily/data.parquet
max: 2026-06-16

.runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet
max: 2026-06-16
```

## 5. `LEDGER_VALUATION_UPDATED`なのに値が変わらない理由

直接理由:

```text
2026-06-17 runでも valuation_date=2026-06-16 で評価しているため。
```

2026-06-17 valuation output:

```text
.runtime/phase9/ledger_valuations/2026-06-16/valuation_manifest.json
```

manifest:

```text
status: LEDGER_VALUATION_UPDATED
valuation_date: 2026-06-16
ledger_latest_updated: true
missing_price_codes: []
warnings: []
```

diff:

```text
market_value_change: 0.0
total_equity_change: 0.0
unrealized_pnl_change: 0.0
```

ledger_beforeとledger_after:

```text
before market_value: 709810.0
after  market_value: 709810.0

before total_equity: 993140.0
after  total_equity: 993140.0

before unrealized_pnl: -6860.0
after  unrealized_pnl: -6860.0
```

ただし副作用として、同じ2026-06-16 valuationなのに`holding_days`が進んでいる。

```text
ledger_before holding_days: 4
ledger_after  holding_days: 5
```

これは同一評価日の再実行時に日数が重複加算される別BUG候補。

## 6. operation_log監査

2026-06-16:

```text
run_date: 2026-06-16
data_target_date: 2026-06-16
ledger_valuation: LEDGER_VALUATION_UPDATED
market_data_refresh: API_FETCH_ALLOWED_BUT_NOT_AUTO_EXECUTED_IN_UNIFIED_RUNNER
```

2026-06-17:

```text
run_date: 2026-06-17
data_target_date: 2026-06-16
ledger_valuation: LEDGER_VALUATION_UPDATED
market_data_refresh: API_FETCH_ALLOWED_BUT_NOT_AUTO_EXECUTED_IN_UNIFIED_RUNNER
```

2026-06-17 runのwarning:

```text
market_data_refresh_runner_should_be_called_by_future_launchd_profile_when_enabled
position_feature_empty_no_current_positions
phase9s_no_virtual_fill_until_next_business_day
```

このwarningは、market refreshがUnified Runner内で未接続であることを示している。

## 7. virtual fill監査

2026-06-17 operation log:

```text
virtual_fill: NO_DUE_PENDING_ORDERS
```

2026-06-16 execution record:

```text
.runtime/phase9/ledger/executions/2026-06-16_executions.json
```

内容:

```text
FILLED BUY records: 5
SELL records: 0
```

2026-06-17 runではpending orderがなく、virtual fillは評価額不変の原因ではない。

## 8. position management監査

2026-06-17 runの推論対象:

```text
decision_for: 2026-06-16
data_until: 2026-06-16
```

position artifact:

```text
.runtime/phase9/inference/2026-06-16/position_artifact.json
```

内容:

```text
rows: 5
action: HOLD
```

auto approval:

```text
.runtime/phase9/auto_approval/2026-06-16/auto_approval_artifact.json
items: 0
```

position managementは全保有をHOLDとして扱い、新規売却・新規pending orderを作っていない。

評価額不変の主因ではない。

## 9. Candidate Top50変化について

ローカル証跡では、Candidate Top50は2026-06-15と2026-06-16の間で変化している。

例:

```text
2026-06-15 rank1: 13580
2026-06-16 rank1: 13650
```

ただし2026-06-17 runの`decision_for`は2026-06-16であり、2026-06-17終値を使ったCandidate変化ではない。

## Root Cause

主因:

```text
Unified Runnerがmarket data refreshを実行せず、既存canonicalの最新日付へ自動フォールバックしてLedger Valuationを実行している。
```

関連実装:

```text
src/ai_fund_lab_v2/paper_trading/unified_daily_runner.py
```

該当挙動:

- `resolve_business_dates()` がquotes parquetの最新日付を探す。
- canonical max dateが2026-06-16なので、2026-06-17 runでも`data_target_date=2026-06-16`になる。
- `run_daily_continuation(run_date=dates.data_target_date, ...)` によりLedger Valuationも2026-06-16で実行される。
- `allow_api_fetch=True`でもUnified Runnerはmarket refreshを呼ばない。

## Impact

影響:

- 2026-06-17 runの資産評価が2026-06-17終値を反映していない。
- `LEDGER_VALUATION_UPDATED`というステータスが、利用者には最新評価のように見える。
- `.runtime/phase9/ledger_valuations/2026-06-16/`が再実行で上書きされ、2026-06-16当日の初回評価証跡が失われる。
- 同一評価日再実行で`holding_days`が重複加算される。
- TrackerのDay2が実質的に2026-06-16再評価を記録している。

## Recommended Fix

優先修正:

1. Unified Runnerでmarket data refreshを実際に呼ぶ。
2. `run_date`と`data_target_date`がズレる場合、operation logとblog/reportへ明示する。
3. paper-trading modeでは、run_date営業日の終値が未取得なら`LEDGER_VALUATION_STALE_SOURCE`などで警告またはBLOCKする。
4. Ledger Valuation output pathを`run_date`と`valuation_date`の両方で一意化する。
5. 同一`valuation_date`の再評価では`holding_days`を増やさない。
6. `LEDGER_VALUATION_UPDATED`に加えて、`price_source_date`、`quote_source_path`、`stale_price_source`をmanifestへ出す。

## Light Audit Commands

実行した軽量監査:

```bash
python3 -m json.tool .runtime/daily_operation/runs/2026-06-17/unified_daily_run_manifest.json
python3 -m json.tool .runtime/phase9/ledger_valuations/2026-06-16/valuation_manifest.json
python3 -m json.tool reports/phase9/daily/2026-06-16_daily_performance_report.json
```

価格確認:

```bash
python3 - <<'PY'
import pandas as pd
codes=['15790','166A0','213A0','221A0','30630']
p='.runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet'
f=pd.read_parquet(p, columns=['date','code','close'])
f['date']=f['date'].astype(str)
f['code']=f['code'].astype(str)
print(f[f['code'].isin(codes) & f['date'].isin(['2026-06-16','2026-06-17'])])
PY
```

重いバックテストは実行していない。
