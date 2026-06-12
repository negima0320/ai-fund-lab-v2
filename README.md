# AI Fund Lab vNext

## Documents

- [要件定義・設計ドキュメント](docs/README.md)
- [システム構成の全体像](docs/ai-found-lab.png)

## Phase1-A Data Foundation

Phase1-A は AI 本体を作らず、J-Quants API から取得した市場データを保存し、後続の Feature Builder / Future Label Builder が使える土台を作る。

### Runtime Storage

生成物は原則としてプロジェクト直下の `.runtime/` に集約する。

```text
.runtime/
  data/
    raw/
    features/
    labels/
  logs/
  cache/
  reports/
  tmp/
```

`.runtime/` は削除可能な実行時ディレクトリであり、Git 管理しない。ローカルの取得データ、ログ、認証キャッシュ、レポート、実験成果物、tmp ファイルをリポジトリ各所に散らばらせない。

保存先は環境変数で変更できる。

```text
AI_FUND_LAB_RUNTIME_DIR=.runtime
AI_FUND_LAB_DATA_DIR=.runtime/data
AI_FUND_LAB_LOG_DIR=.runtime/logs
AI_FUND_LAB_CACHE_DIR=.runtime/cache
AI_FUND_LAB_REPORT_DIR=.runtime/reports
AI_FUND_LAB_TMP_DIR=.runtime/tmp
```

未指定の場合、`AI_FUND_LAB_RUNTIME_DIR` 配下に集約される。コードから保存先を使う場合は `RuntimePaths` を経由する。

### Data Layers

`MarketDataStore` は保存責務を以下に分離する。

```text
Raw Data:
  .runtime/data/raw/

Feature Data:
  .runtime/data/features/

Future Label Data:
  .runtime/data/labels/
```

保存時には `fetched_at`, `target_date`, `code`, `source`, `endpoint` を持たせる。同じ `target_date + code + endpoint` の再保存は upsert として扱い、既存レコードを置き換えて重複を作らない。

`future_return_*`, `future_max_return_*`, `future_max_drawdown_*` は Feature Data ではなく Future Label Data に保存する。推論 feature には使わない。

### J-Quants Credentials

J-Quants V2 API を前提にする。API キーなどの認証情報は `.env` または環境変数で管理し、Git 管理しない。

```text
JQUANTS_API_KEY=
JQUANTS_BASE_URL=https://api.jquants.com
JQUANTS_RATE_LIMIT_PER_MINUTE=60
JQUANTS_TIMEOUT_SECONDS=30
```

`.env.example` は雛形として Git 管理するが、実値を入れた `.env` / `.env.*` は Git 管理しない。

### Commands

```bash
python3 -m pytest
python3 scripts/storage_report.py
python3 scripts/storage_report.py --runtime-dir .runtime
```

`scripts/storage_report.py` は `.runtime/data/raw`, `.runtime/data/features`, `.runtime/data/labels`, `logs`, `cache`, `reports`, `tmp` の容量を表示する。

## Phase1-B J-Quants Raw Fetch

Phase1-B では Light プランで利用可能な J-Quants V2 raw endpoint の取得ユースケースを追加する。AI 本体、broker 連携、注文機能はまだ実装しない。

### Supported Endpoints

```text
daily_quotes:
  GET /v2/equities/bars/daily
  output: .runtime/data/raw/jquants/equities_bars_daily/data.jsonl

listed_issues:
  GET /v2/equities/master
  output: .runtime/data/raw/jquants/listed_issues/data.jsonl

trading_calendar:
  GET /v2/markets/calendar
  output: .runtime/data/raw/jquants/trading_calendar/data.jsonl

fins_summary:
  GET /v2/fins/summary
  output: .runtime/data/raw/jquants/fins_summary/data.jsonl
```

### Daily Fetch CLI

```bash
python3 scripts/fetch_jquants_daily.py --endpoint daily_quotes --date 2026-06-01
python3 scripts/fetch_jquants_daily.py --endpoint all --from-date 2026-06-01 --to-date 2026-06-30
python3 scripts/fetch_jquants_daily.py --endpoint all --date 2026-06-01 --dry-run --runtime-dir .runtime
```

`--dry-run` は実 API 取得も保存も行わず、取得予定 endpoint、対象日、保存先だけを表示する。実行ログは `.runtime/logs/` 配下に出す。

### Pagination Policy

J-Quants response に `pagination_key` が含まれる場合、次 request に `pagination_key` を付与して続きのページを取得する。無限ループ防止のため `--max-pages` を設定できる。pagination 中の失敗は endpoint、target date、取得済みページ数を runtime log に記録する。API key や token はログに出さない。

### Missing Data Log Policy

`daily_quotes` が空だった場合は、欠損または非営業日の可能性として `.runtime/logs/jquants_ingestion.log` に記録する。Phase1-B では厳密な品質判定までは行わず、後続で trading calendar と組み合わせて WARNING / INFO を精緻化する。

### Rate Limit Policy

J-Quants Light プランの基本 rate limit である `60 req/min` を `JQUANTS_RATE_LIMIT_PER_MINUTE` のデフォルトにする。429 を受けた場合は rate limit handling に入り、テストでは sleep を mock して長時間待機しない。

## Phase1-B-LiveSmoke

実 API の疎通確認は通常 pytest から分離し、明示的な手動 CLI のみで行う。`python3 -m pytest` は mock のみで実 API を呼ばない。

### Smoke Dry Run

```bash
python3 scripts/smoke_jquants_api.py --endpoint all --date 2026-06-01 --from-date 2026-06-01 --to-date 2026-06-07 --max-pages 1 --dry-run --runtime-dir .runtime
```

dry-run は実 API 取得も保存も行わず、endpoint、parameter、runtime 保存先、rate limit、max_pages を表示する。

### Smoke Live Commands

```bash
python3 scripts/smoke_jquants_api.py --endpoint daily_quotes --date 2026-06-01 --max-pages 1
python3 scripts/smoke_jquants_api.py --endpoint listed_issues --date 2026-06-01 --max-pages 1
python3 scripts/smoke_jquants_api.py --endpoint trading_calendar --from-date 2026-06-01 --to-date 2026-06-07 --max-pages 1
python3 scripts/smoke_jquants_api.py --endpoint fins_summary --date 2026-06-01 --max-pages 1
python3 scripts/smoke_jquants_api.py --endpoint all --date 2026-06-01 --from-date 2026-06-01 --to-date 2026-06-07 --max-pages 1
```

実行時は `JQUANTS_API_KEY` を `.env` または環境変数から読む。API key、token、Authorization、x-api-key の値は stdout/stderr/log に出さない。取得結果は Phase1-B の raw ingestion 経由で `.runtime/data/raw/jquants/` 配下へ保存する。

## Phase1-C Raw Reliability

Phase1-C では J-Quants raw data の信頼性を上げるため、取引カレンダーに基づく営業日判定、取得計画の自動生成、raw 欠損検査レポートを追加する。AI 本体、feature 計算、label 生成、backtest、paper trading、broker / order 連携には進まない。

### Trading Calendar Service

`.runtime/data/raw/jquants/trading_calendar/data.jsonl` を読み、`HolDiv == "1"` を営業日として扱う。

```text
is_business_day(date)
list_business_days(from_date, to_date)
previous_business_day(date)
next_business_day(date)
```

calendar raw が未取得の場合は、先に `trading_calendar` を取得する必要があることを示すエラーにする。

### Fetch Plan Policy

```text
daily_quotes:
  営業日ごとに取得する。非営業日は skip し INFO log に残す。

trading_calendar:
  from_date から to_date までを range 指定で取得する。

listed_issues:
  指定 date、期間指定時は to_date の snapshot を取得する。

fins_summary:
  営業日ごとに取得する。ただし開示がない日は異常とは限らないため、空でも即 ERROR にしない。
```

dry-run では fetch plan を表示する。

```bash
python3 scripts/fetch_jquants_daily.py --endpoint daily_quotes --from-date 2026-06-01 --to-date 2026-06-07 --dry-run --runtime-dir .runtime
```

### Raw Quality Check

```bash
python3 scripts/check_jquants_raw_quality.py --endpoint all --from-date 2026-06-01 --to-date 2026-06-07 --runtime-dir .runtime --output both
```

レポート保存先:

```text
.runtime/reports/jquants_raw_quality/
```

判定の意味:

```text
OK:
  対象期間の期待データが揃っている、または fins_summary のように空が通常あり得る。

WARNING:
  営業日の daily_quotes が欠損、対象日の listed_issues が欠損、calendar raw が不足、duplicate key がある。

ERROR:
  Phase1-Cでは原則未使用。将来、破損ファイルや読み取り不能などで導入する。
```

レポート、ログ、raw data は `.runtime` 配下に集約する。API key、token、Authorization、x-api-key の値は stdout/stderr/log/report に出さない。

## Phase1-D Raw Store Hardening

Phase1-D では Raw Data Store を堅牢化する。保存抽象、schema validation、再取得 diff、manifest を追加する。AI 本体、feature 計算、label 生成、backtest、paper trading、broker / order 連携には進まない。

### Raw Storage Backend

Raw storage は backend 抽象を経由する。

```text
AI_FUND_LAB_RAW_STORAGE_FORMAT=jsonl
```

デフォルトは `jsonl`。Parquet は Phase1-D では interface と明確な未対応エラーまでに留める。理由は `pandas` / `pyarrow` 依存をこの段階で増やすと Data Foundation の初期検証が重くなるため。後続で schema が安定してから `parquet` backend を有効化する。

### Endpoint Schemas

```text
daily_quotes:
  required: Date, Code, O, H, L, C, Vo
  business key: Date + Code
  empty on business day: WARNING
  required欠損: ERROR

listed_issues:
  required: Date, Code, CoName, Mkt
  business key: Date + Code
  snapshot型

trading_calendar:
  required: Date, HolDiv
  business key: Date
  HolDiv == "1" を営業日扱い

fins_summary:
  required: DiscDate, Code
  business key: DiscDate + Code
  空の日があっても即 ERROR にしない
```

Validation result は `OK / WARNING / ERROR` を返す。required field 欠損や key 欠損は `ERROR`、duplicate key や型正規化警告は `WARNING` とする。ERROR でも自動削除はしない。まず report / log / manifest で可視化する。

### Re-run / Diff Policy

再実行時のデフォルトは安全な upsert。`target_date + business_key + endpoint` で重複を作らず、同じ key は置き換える。自動削除や危険な replace は Phase1-D では導入しない。再取得時は以下を diff summary として残す。

```text
record_count_before
record_count_after
inserted_count
updated_count
unchanged_count
deleted_or_missing_count
duplicate_key_count
changed_keys_sample
```

### Raw Manifest

取得 manifest は以下に追記保存する。

```text
.runtime/data/raw/jquants/manifest.jsonl
```

manifest には `fetched_at`, `endpoint`, `target_date`, `from_date`, `to_date`, `record_count`, `storage_format`, `storage_path`, `status`, `validation_status`, `diff_summary`, sanitized `request_params` を保存する。API key、token、Authorization、x-api-key の値は保存しない。

### CLI Additions

`fetch_jquants_daily.py --dry-run` は保存形式、manifest予定、validation予定を表示する。実保存後は validation summary と diff summary を表示し、manifest を更新する。

`check_jquants_raw_quality.py` の markdown/json report には validation summary も含める。

## Phase1-E Raw Store Operations

Phase1-E では Parquet backend、schema versioning、JSONL から Parquet への安全移行、manifest 表示と再取得対象抽出を追加する。通常 pytest は実 API を呼ばない。

### Parquet Backend

`pandas` / `pyarrow` を利用して Parquet 保存を有効化する。

```bash
AI_FUND_LAB_RAW_STORAGE_FORMAT=parquet python3 scripts/fetch_jquants_daily.py --endpoint daily_quotes --date 2026-06-01
```

保存先例:

```text
.runtime/data/raw/jquants/equities_bars_daily/data.parquet
.runtime/data/raw/jquants/listed_issues/data.parquet
.runtime/data/raw/jquants/trading_calendar/data.parquet
.runtime/data/raw/jquants/fins_summary/data.parquet
```

JSONL の既存動作は維持する。`.parquet` は Git 管理しない。

### Schema Versioning

全 endpoint schema は `schema_version=1` から開始する。schema version は validation result、manifest、quality report に出力する。将来 schema を変更する場合は version を上げ、manifest でどの schema で保存・検査されたか追跡する。

### JSONL to Parquet Migration

移行は元 JSONL を削除しない安全移行とする。

```bash
python3 scripts/migrate_raw_storage.py --endpoint all --from-format jsonl --to-format parquet --runtime-dir .runtime --dry-run --validate
python3 scripts/migrate_raw_storage.py --endpoint all --from-format jsonl --to-format parquet --runtime-dir .runtime --validate
```

実行時は record count と validation を確認し、manifest に `MIGRATED` event を追記する。

### Manifest CLI

```bash
python3 scripts/show_jquants_manifest.py --endpoint all --runtime-dir .runtime --latest --format table
python3 scripts/show_jquants_manifest.py --endpoint all --runtime-dir .runtime --needs-refetch --format table
```

`--needs-refetch` は `validation_status != OK`、`status == ERROR`、`record_count == 0` などから再取得候補を表示する。実 API 再取得は行わない。

Manifest と report には API key、token、Authorization、x-api-key の値を出さない。

## Phase1-F Raw Operations Check

Phase1-F では運用前点検として validation drilldown、refetch plan、Parquet readiness、manifest filter/summary を追加する。実 API は呼ばず、raw data と manifest/report の検査だけを行う。

### Validation Drilldown

```bash
python3 scripts/inspect_raw_validation.py --endpoint daily_quotes --runtime-dir .runtime --storage-format parquet --limit 20 --output table
python3 scripts/inspect_raw_validation.py --endpoint daily_quotes --runtime-dir .runtime --storage-format parquet --output markdown --save-report
```

daily_quotes schema v1 の field mapping:

```text
Date -> Date
Code -> Code
O -> O / Open / AdjustmentOpen / AdjO
H -> H / High / AdjustmentHigh / AdjH
L -> L / Low / AdjustmentLow / AdjL
C -> C / Close / AdjustmentClose / AdjC
Vo -> Vo / Volume / AdjustmentVolume / AdjVo
```

現在の daily_quotes validation=ERROR は、schema v1 が `O/H/L/C/Vo` を required としている一方、実 raw の一部 record で unadjusted 側が null になっているため。`AdjO/AdjH/AdjL/AdjC/AdjVo` には値がある record があるため、schema v2 で adjusted fields を正式に primary にするか、v1 strict schema のまま upstream 欠損として扱うかを次フェーズで決める。Phase1-F では ERROR を安易に OK 扱いしない。

価格 0 は欠損ではなく値として扱う。null / 空文字は欠損扱い。

### Refetch Plan

```bash
python3 scripts/build_jquants_refetch_plan.py --endpoint all --from-date 2026-06-01 --to-date 2026-06-07 --runtime-dir .runtime --reason all --output markdown --dry-run
```

priority:

```text
daily_quotes 営業日欠損: HIGH
trading_calendar 欠損: HIGH
listed_issues 欠損: MEDIUM
fins_summary 空日: LOW
```

この CLI は実 API を呼ばず、suggested command を出すだけ。

### Parquet Readiness

```bash
python3 scripts/check_parquet_readiness.py --runtime-dir .runtime
```

READY 条件:

```text
jsonl/parquet record_count 一致
schema validation status 一致
latest manifest が parquet
migration event が manifest にある
parquet が .runtime/data/raw 配下
pandas / pyarrow が利用可能
secret leak なし
```

Parquet infrastructure が READY でも、daily_quotes schema validation ERROR が残る場合は、Parquet 既定化前に schema v2 方針を確認する。

### Manifest Filter / Summary

```bash
python3 scripts/show_jquants_manifest.py --endpoint all --runtime-dir .runtime --summary
python3 scripts/show_jquants_manifest.py --endpoint all --runtime-dir .runtime --validation-status ERROR --storage-format parquet
python3 scripts/show_jquants_manifest.py --endpoint all --runtime-dir .runtime --needs-refetch
```

manifest / report / log には API key、token、Authorization、x-api-key の値を出さない。

## Phase1-G Daily Quotes Normalized Raw

Phase1-G では `daily_quotes` raw schema v1 を変更せず、後続処理が使いやすい normalized raw schema v2 を別レイヤーに追加する。これは feature 計算でも label 生成でもなく、raw data foundation の正規化層である。AI 本体、broker 連携、注文機能には進まない。

### 保存先

raw は引き続き以下に保存する。

```text
.runtime/data/raw/jquants/equities_bars_daily/
```

normalized raw は raw と分離して以下に保存する。

```text
.runtime/data/raw_normalized/jquants/equities_bars_daily/data.parquet
.runtime/data/raw_normalized/jquants/equities_bars_daily/data.jsonl
```

`.runtime/data/raw_normalized` は `.runtime` 配下の削除可能な生成物であり、Git 管理しない。

### Daily Quotes Normalized Schema v2

必須フィールド:

```text
Date
Code
Open
High
Low
Close
Volume
PriceSource
SchemaVersion
```

business key は `Date + Code`。`SchemaVersion` は `2`。

正規化方針:

```text
AdjO/AdjH/AdjL/AdjC/AdjVo が揃っている場合:
  Open/High/Low/Close/Volume = AdjO/AdjH/AdjL/AdjC/AdjVo
  PriceSource = adjusted

調整後フィールドが揃わず、O/H/L/C/Vo が揃っている場合:
  Open/High/Low/Close/Volume = O/H/L/C/Vo
  PriceSource = unadjusted

どちらも揃わない場合:
  normalized output から除外し、normalization report の ERROR sample に記録する
```

null / 空文字の price・volume は `ERROR`。price 0 / volume 0 は欠損ではないが `WARNING` として検査対象にする。

### Normalize CLI

```bash
python3 scripts/normalize_jquants_raw.py --endpoint daily_quotes --runtime-dir .runtime --input-format auto --output-format parquet --dry-run --validate
python3 scripts/normalize_jquants_raw.py --endpoint daily_quotes --runtime-dir .runtime --input-format parquet --output-format parquet --validate
python3 scripts/normalize_jquants_raw.py --endpoint daily_quotes --runtime-dir .runtime --input-format jsonl --output-format jsonl --validate --limit-errors 20
```

`--dry-run` は実 API を呼ばず、保存も manifest 更新もしない。通常実行時も実 API は呼ばず、既存 raw file を読み込んで normalized raw を生成する。

### Manifest

正規化実行時は `.runtime/data/raw/jquants/manifest.jsonl` に `NORMALIZED` event を追記する。

```text
event_type=NORMALIZED
source_endpoint=/v2/equities/bars/daily
normalized_endpoint=daily_quotes_normalized
raw_schema_version=1
normalized_schema_version=2
input_storage_format
output_storage_format
input_record_count
output_record_count
validation_status
normalization_report
storage_path
```

request params は sanitized して保存する。API key、token、Authorization、x-api-key の値は manifest / stdout / stderr / report / log に出さない。

### Quality Report

`scripts/check_jquants_raw_quality.py` は `daily_quotes` について raw schema v1 と normalized schema v2 の status を分けて表示する。

```bash
python3 scripts/check_jquants_raw_quality.py --endpoint daily_quotes --from-date 2026-06-01 --to-date 2026-06-07 --runtime-dir .runtime --output both
```

raw v1 が `ERROR` でも、normalized v2 が `OK` であれば、raw の原本性を保ったまま後続の Data Foundation に進める状態として扱える。ただし raw v1 の ERROR は隠さず、品質レポート上に残す。

## Phase1-H Final Audit

Phase1-H は Phase1 の最終監査、daily_quotes 正規化除外レコードの品質分類、Phase2 への引き継ぎ資料作成を行う。新しい AI、feature 本体、future label、backtest、paper trading、broker/order は実装しない。

Phase1 の完了レポート:

```text
docs/phase_reports/phase1_completion_report.md
.runtime/reports/phase1_final/phase1_completion_report.md
```

主要CLI:

```bash
python3 scripts/inspect_daily_quote_exclusions.py --runtime-dir .runtime --save-report
python3 scripts/audit_phase1_completion.py --runtime-dir .runtime
python3 scripts/write_phase1_completion_report.py --runtime-dir .runtime
python3 scripts/storage_report.py --runtime-dir .runtime
python3 scripts/check_jquants_raw_quality.py --endpoint all --from-date 2026-06-01 --to-date 2026-06-07 --runtime-dir .runtime
python3 scripts/show_jquants_manifest.py --endpoint all --runtime-dir .runtime --summary
python3 scripts/check_parquet_readiness.py --runtime-dir .runtime
```

Phase2へ進む前の注意:

```text
Phase2のfeature builderは daily_quotes_normalized を読む。
raw daily_quotes v1 は原本証跡として残す。
正規化から除外されたdaily_quotes recordは、根拠ある品質ルールができるまでfeature/AI入力へ混入させない。
future_return_* は引き続きlabel専用でありfeatureに入れない。
```

## プロジェクトの目的

AI Fund Lab の目的は、AIを活用した株式売買システムを構築し、

```text
なるべく年率50%以上の利益を出すこと
```

を目指すことである。

ただし、

```text
年率50%を達成すること
```

だけが目的ではない。

以下も同時に満たすことを目標とする。

```text
なぜ買うのか説明できる

なぜ保有するのか説明できる

なぜ売るのか説明できる

システムを信頼して感情に流されず運用できる
```

また、売買状況をブログなどで情報共有する。

---

# 最重要原則

## AIは未来を予言しない

AI Fund Lab は、

```text
未来を当てる
```

システムではない。

AIは、

```text
候補の中から

期待値が高い銘柄を順位付けし、

期待値が上がりきった所で売却（利確）

または、過剰に下がったところで売却（損切り）

の判断を行う。
```

ために利用する。

---

# 投資哲学

## 投資スタイル

```text
スイングモメンタム
```

---

## 基本思想

市場は短期的には非効率であり、

良い企業が市場に評価され始めると、

その上昇トレンドは一定期間継続する傾向がある。

AI Fund Lab は、

```text
良い企業

かつ

上昇が始まり

かつ

まだ上昇余地がある
```

銘柄を発見し、

その上昇トレンドから利益を得ることを目的とする。

---

## 狙う期間

基本保有期間

```text
5〜30営業日
```

中心。

デイトレードは行わない。

長期投資も主目的としない。

---

## 買わない銘柄

以下は原則として避ける。

```text
単に安いだけの銘柄

下落中の銘柄

出来高が少ない銘柄

市場から評価されていない銘柄
```

---

## 買う銘柄

以下を満たす銘柄を狙う。

```text
企業品質が良い

市場が評価し始めている

価格モメンタムが発生している

出来高モメンタムが発生している

上昇余地が残っている
```

---

# システムの役割

AI Fund Lab は以下の判断を行う。

---

## Candidate AI

役割

```text
上昇候補発見

概要
全銘柄候補から、上昇候補を発見する
```

問い

```text
どの銘柄にモメンタムが発生しているか？
```

Input:

- 全銘柄リスト

- 株価OHLCV

- 出来高

- 移動平均

- 高値更新

- 出来高急増

- 市場/セクター情報

- 財務・業績情報

Output:

- candidate_list

- momentum_score

- quality_score

- candidate_reason

- excluded_reason

---

## Opportunity AI

役割

```text
期待値判定

概要
Candidate AIで抽出した銘柄の期待値を判定する
```

問い

```text
どの銘柄が最も大きな利益機会を持つか？
```

Input:

- candidate_list

- momentum_score

- quality_score

- opportunity features

- downside features

- 市場環境

Output:

- buy_rank

- expected_edge_score

- expected_return_horizon

- upside_score

- downside_risk_score

- buy_reason

- no_buy_reason

---

## Position Management AI

役割

```text
保有継続判定

概要
今持っているポジションをどう扱うか？を継続して判断する。
保有する、売却するの判断を行う
```

問い

```text
上昇トレンドは継続しているか？（保有）
上昇トレンドは終了したか？（利確）
急激な下げトレンドか？（損切）
```



Input:

- position_list

- entry_price

- current_price

- holding_days

- unrealized_return

- peak_return

- momentum_status

- downside_risk

- market_environment

Output:

- position_action

  - HOLD

  - EXIT

  - REDUCE

  - ADD

- action_reason

- exit_reason

- stop_loss_flag

- profit_take_flag

- trend_break_flag

---

## Capital Allocation Engine

役割

```text
資金管理
```

問い

```text
Candidate AI、Opportunity AIの結果から
どれだけ買うべきか？いくら買うべきか？を判断する
```

Input:

- buy_rank

- expected_edge_score

- downside_risk_score

- cash_available

- current_positions

- max_positions

- risk_limits

Output:

- order_plan

- buy_amount

- share_quantity

- position_size

- allocation_reason

- skip_reason

---

## Order Manager

役割

```text
注文管理
```

問い

```text
どの注文を発行するか？
```

責務
```text
新規注文

売却注文

注文状態管理

約定確認

取消処理

二重注文防止
```

Input:

- order_plan

- broker_account_state

- market_price

- trading_calendar

- risk_check_result

Output:

- order_request

- order_id

- order_status

- filled_quantity

- average_fill_price

- cancel_result

- order_error

---

## Broker Sync Manager

役割

```text
証券口座同期
```

問い

```text
実際の口座状態はどうなっているか？
```

責務
```text
現金残高取得

保有銘柄取得

注文一覧取得

約定履歴取得

システム状態との照合
```

Input:

- 立花証券APIの残高

- 保有株

- 注文一覧

- 約定履歴

- system_portfolio_state

Output:

- synced_cash

- synced_positions

- synced_orders

- reconciliation_result

- discrepancy_report

- sync_error

---

## Portfolio State Manager

役割

```text
保有資産管理
```

責務
```text
現在資産

評価損益

ポジション一覧

購入単価

保有日数

期待リターン管理
```

Input:

- synced_cash

- synced_positions

- filled_orders

- market_price

- AI判断履歴

Output:

- current_assets

- unrealized_profit_loss

- realized_profit_loss

- position_list

- holding_days

- entry_price

- current_return

- portfolio_snapshot

---

## Safety Guard

役割

```text
異常検知
```

責務
```text
APIエラー検知

口座不整合検知

想定外ポジション検知

異常損失検知

自動売買停止
```

Input:

- broker_sync_result

- order_status

- portfolio_snapshot

- daily_loss

- drawdown

- API error logs

- discrepancy_report

Output:

- safety_status

  - OK

  - WARNING

  - HALT

- halt_reason

- alert_message

- allowed_to_trade

---

## Reporting System

役割

```text
監査・分析
```

責務
```text
売買履歴

AI判断履歴

パフォーマンス分析

バックテスト結果

運用レポート
```

Input:

- AI判断履歴

- order history

- trade history

- portfolio snapshots

- performance metrics

- safety events

Output:

- daily_report

- trade_report

- performance_report

- AI decision audit

- backtest_report

- live_operation_report

---

## システムの判断フロー

```text
Candidate AI
↓
Opportunity AI
↓
Capital Allocation Engine
↓
Order Manager
↓
Broker Sync Manager
↓
Portfolio State Manager
↓
Position Management AI
↓
Safety Guard
```

---

# このプロジェクトで作らないもの

```text
- デイトレードAI

- 長期バリュー投資AI

- バックテスト結果を学習するAI

- AIを増やすためのAI

- 理由を説明できない売買ロジック

- current modelをいきなり上書きする実験
```

---

# AI開発の原則

## 市場を学習する

AIは、

```text
市場結果
```

を学習する。

---

## システム結果を学習しない

以下は学習禁止。

```text
backtest result

trade result

trade profit

selected

bought

sold

cash

portfolio

annual_return

final_assets

allocation result

pm result
```

---

## 学習に利用可能

以下は利用可能。

```text
主にJ-Quants APIから情報を取得する 

価格

出来高

財務情報

業績情報

テクニカル指標

市場指標

future_return_*

future_max_return_*

future_max_drawdown_*
```

ただし、

```text
future系はラベルのみ
```

であり、

featureとして利用してはならない。

---

# 評価指標

## Primary Metric

最重要指標

```text
Annual Return
```

---

## Secondary Metrics

以下は診断用。

```text
Profit Factor

Drawdown

Win Rate

Capital Utilization

Trade Count

Holding Period
```

これらは目的ではない。

---

# Reality Audit原則

新しいAIを作る前に必ず確認する。

```text
本当に必要か？

既存AIで代替できないか？

投資哲学と整合しているか？
```

---

# Strict OOS原則

Train / Validation / Test を厳格に分離する。

基本構成

```text
Train:
2023

Validation:
2024

Test:
2025
```

未来情報の混入は禁止。

---

# 最後に

AI Fund Lab の目的は、

```text
AIを作ること
```

ではない。

```text
信頼できる投資システムを作ること
```

である。

すべての実装は、

```text
この変更は

年率50%達成にどう繋がるのか？
```

を説明できなければならない。
