# Phase20-BE J-Quants Acquisition Normalization Connection

## Final Status

```text
PHASE20_BE_JQUANTS_ACQUISITION_NORMALIZATION_CONNECTION_FIXED
```

Phase20の最上位目的は、データ基盤拡張ではなく、上げ相場・下げ相場・横ばい相場でPosition Managementの実挙動を通常Runtime経路で確認し、PMを維持・部分修正・再設計のどれに進めるか判断することです。本Phaseは、その代表相場Replayに必要なAcquisition正規化接続だけを修正しました。

Codexは実API probe、複数日取得、5年取得、Bootstrap本実行、Historical Run、Training、Calibration、Broker接続、Demo/Production発注を実行していません。Runtime共通OHLCVも変更していません。

## Finding

Phase20-BDでrequest contractは正常化済みでした。

```text
GET /v2/equities/bars/daily?date=YYYY-MM-DD
```

2026-07-01単日probeではfetch自体は成功していましたが、AcquisitionがV2 responseをそのまま`O/H/L/C/Vo`必須列検査へ渡していたため、以下で停止していました。

```text
raw_required_fields_missing:O,H,L,C,Vo
```

旧run `jquants-acquisition-20260701-bd-probe` はrequest state上は取得済みでもRaw artifactを持たないため、resume禁止です。

## Existing Success Path

既存の日次Market Refresh成功経路は以下です。

```text
JQuantsClient
-> JQuantsAPIFetcher.fetch_daily_quotes_for_date
-> market_data_refresh
-> Raw record metadata/merge
-> normalize_daily_quotes
-> Runtime Normalized OHLCV
```

`normalize_daily_quotes`の正式contractは以下です。

```text
AdjO/AdjH/AdjL/AdjC/AdjVo if complete
else O/H/L/C/Vo
```

## Fix

Acquisition側で新しいOHLCV schemaや専用normalizerは作らず、既存Raw schema authorityを再利用しました。

```text
ai_fund_lab_v2.data_store.schema.RAW_SCHEMAS["daily_quotes"]
```

V2列は既存Raw schema aliasに従ってRaw v1へ接続されます。

```text
Open -> O
High -> H
Low -> L
Close -> C
Volume -> Vo
AdjustmentOpen -> AdjO
AdjustmentHigh -> AdjH
AdjustmentLow -> AdjL
AdjustmentClose -> AdjC
AdjustmentVolume -> AdjVo
```

その後、既存の`normalize_daily_quotes`をそのまま再利用します。

## State Contract

Acquisition connection version:

```text
phase20_be_acquisition_normalization_connection.v1
```

状態は最低限以下を区別します。

```text
FETCH_FAILED
RAW_READY
NORMALIZATION_FAILED
COMPLETED
```

API fetch成功後、Raw chunk parquetを書き、content hashを記録してから`RAW_READY`になります。Normalized検証に失敗してもRaw artifactは残ります。最終`COMPLETED`はNormalized staging validation PASS後です。

## Evidence

Evidence root:

```text
reports/phase20_be_jquants_acquisition_normalization_connection/
```

Machine-readable report:

```text
reports/phase_reports/phase20_be_jquants_acquisition_normalization_connection.json
```

## Validation

Executed:

```text
py_compile PASS
targeted pytest PASS: 32 passed
CLI help PASS
JSON validation PASS
git diff --check PASS
```

## User Single-Day Probe

```bash
cd /Users/negishi/work/ai-fund-lab-v2
export PYTHONPATH=src:.

python3 scripts/runtime_test.py market-data-acquisition run   --start-date 2026-07-01   --end-date 2026-07-01   --run-id jquants-acquisition-20260701-be-probe   --confirm   --yes-i-understand-this-fetches-large-market-data   --write-evidence   --json
```

Expected:

```text
final_judgment = ACQUISITION_SOURCE_READY
request_count >= 1
page_count >= 1
row_count > 0
raw artifact exists
normalized artifact exists
duplicate_key_count = 0
runtime_market_data_mutated = false
```

単日probe成功後も直ちに5年取得へ進まず、代表相場期間ごとに最大warmup 61BD + PM評価期間だけを取得して、通常Historical RuntimeでPM挙動確認へ戻ります。
