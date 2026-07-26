# Phase20-BF Production Market Refresh Reuse

## Final Status

```text
PHASE20_BF_PRODUCTION_MARKET_REFRESH_REUSE_READY
```

Phase20の最上位目的は、5年バックテスト基盤や独自データ取得基盤を新設することではありません。上げ相場・下げ相場・横ばい相場でPMの実挙動を通常Runtime経路で確認し、PMを維持・部分修正・再設計のどれに進むべきか判断することです。

Codexは実API probe、複数日取得、代表期間取得、5年取得、Bootstrap run、Historical Run、Training、Calibration、Broker接続、Demo/Production発注を実行していません。Runtime共通OHLCVも変更していません。

## Authority

Production/Demoの日次Market Refresh authorityは以下です。

```text
src/ai_fund_lab_v2/paper_trading/market_data_refresh.py::run_market_data_refresh
```

この経路が以下を担当します。

```text
J-Quants V2 request
per-date fetch
Raw schema coercion
Raw merge
Raw artifact write
normalize_daily_quotes
Normalized merge/write
manifest/evidence generation
```

Acquisitionはこの処理を再実装しません。

## Adapter Design

Historical Acquisitionは以下だけを担当します。

```text
plan
chunking
run_id / staging root
resume state
Production Market Refresh core呼び出し
staging validation
```

Adapter version:

```text
phase20_bf_production_market_refresh_adapter.v1
```

Processing authority:

```text
PRODUCTION_MARKET_REFRESH_CORE
```

出力先は専用stagingのみです。

```text
.runtime/market_data_acquisition/runs/<run_id>/
```

Production共通OHLCVへは書き込みません。

```text
.runtime/operations/jquants/
```

## Production Core Reuse

既存`run_market_data_refresh`はすでに以下のoverrideを持つため、新規core抽出は不要でした。

```text
raw_output_root
normalized_output_root
manifest_output_root
fetch_mode
fetcher
```

Historical adapterはこれらにstaging pathを渡します。

## schema.py Judgment

Phase20-BEで追加した`AdjustmentOpen`等のaliasは維持します。ただしAcquisition都合ではなく、Production Market Refresh coreの`_coerce_raw_schema`が`RAW_SCHEMAS`を使うための共有契約として維持します。既存`O/H/L/C/Vo`および`AdjO/AdjH/AdjL/AdjC/AdjVo`の挙動は変えない加算的aliasです。

## Legacy Runs

以下は新adapter contractと互換性がないためresume禁止です。

```text
jquants-acquisition-20260701-bd-probe
jquants-acquisition-20260701-be-probe
```

新しいrun_idを使用してください。

## Evidence

```text
reports/phase20_bf_production_market_refresh_reuse/
reports/phase_reports/phase20_bf_production_market_refresh_reuse.json
```

## Validation

Executed:

```text
py_compile PASS
targeted pytest PASS: 41 passed
CLI help PASS
JSON validation PASS
git diff --check PASS
```

## User Single-Day Probe

```bash
cd /Users/negishi/work/ai-fund-lab-v2
export PYTHONPATH=src:.

python3 scripts/runtime_test.py market-data-acquisition run   --start-date 2026-07-01   --end-date 2026-07-01   --run-id jquants-acquisition-20260701-bf-probe   --confirm   --yes-i-understand-this-fetches-large-market-data   --write-evidence   --json
```

Expected:

```text
final_judgment = ACQUISITION_SOURCE_READY
processing_authority = PRODUCTION_MARKET_REFRESH_CORE
request_count >= 1
page_count >= 1
row_count > 0
raw artifact exists
normalized artifact exists
runtime_market_data_mutated = false
production_market_data_hash_unchanged = true
```

単日probe成功後も5年取得へは進まず、PM判断に必要な代表相場期間を確定し、各期間について最大warmup 61BD + PM評価期間だけを取得します。
