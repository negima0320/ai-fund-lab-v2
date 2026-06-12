# AI Fund Lab vNext Phase4-K Normalized Data History Expansion / Prepared Dry-run Ready

---

# 1. このレポートの目的

Phase4-Kは、Phase4-Jで `BLOCKED_BY_DATA_WINDOW` だった原因を解消するため、`daily_quotes_normalized` の履歴範囲を60営業日以上に拡張し、prepared dry-run が実行可能な状態か確認する段階である。

今回も以下には進まない。

```text
label生成
dataset builder
Candidate AI本体
学習
推論
backtest
売買
Paper Trading
Broker実API
発注
Portfolio自動更新
```

---

# 2. 読んだ資料

```text
docs/phase_reports/phase4j_real_feature_prepared_dry_run.md
docs/phase_reports/phase4j_real_feature_prepared_dry_run_audit.md
reports/phase_reports/phase4j_real_feature_prepared_dry_run_audit.json
reports/candidate_ai/phase4j_real_feature_prepared_dry_run_summary.json
docs/01_requirements/phase_roadmap.md
docs/02_architecture/system_architecture.md
src/ai_fund_lab_v2/data/
src/ai_fund_lab_v2/runtime/
scripts/
tests/
```

---

# 3. 利用したData Foundation pipeline

Phase1 Data Foundationの既存要素を利用する。

```text
RuntimePaths:
  .runtime/data/raw/
  .runtime/data/raw_normalized/
  .runtime/reports/

normalization:
  normalize_daily_quotes()
  write_daily_quotes_normalized()
  validate_records("daily_quotes_normalized")

storage:
  parquet / jsonl backend
  .runtime/data/raw_normalized/jquants/equities_bars_daily/data.parquet

trading calendar:
  .runtime/data/raw/jquants/trading_calendar/
```

実API呼び出しは行わない。

---

# 4. daily_quotes_normalized保存先

標準保存先:

```text
.runtime/data/raw_normalized/jquants/equities_bars_daily/data.parquet
```

prepared dry-runは `discover_daily_quotes_normalized()` 経由でこの保存先を読む。

---

# 5. 履歴拡張方法

Phase4-Kでは、J-Quants認証情報や実APIを必須にしない。

実 `.runtime` の履歴が不足している場合は、Phase1のnormalized schemaに合うmock normalized historyを生成する。

作成スクリプト:

```bash
python3 scripts/prepare_phase4k_normalized_history.py
```

default:

```text
start_date = 2026-03-02
business_days = 66
code_count = 30
output_format = parquet
data_source_type = mock
api_call = false
```

mock/fixtureの場合は以下へ明記する。

```text
reports/candidate_ai/phase4k_mock_normalized_history_manifest.json
.runtime/reports/candidate_ai/phase4k_mock_normalized_history_manifest.json
.runtime/data/raw/jquants/manifest.jsonl
```

---

# 6. 実データ/API/fixture/mockの区別

Phase4-K監査では `data_source_type` を出力する。

```text
real_runtime:
  既存runtime normalized dataを利用

mock:
  Phase4-K preparation scriptで生成したmock normalized historyを利用

fixture:
  テスト用fixture runtimeを利用

skipped:
  normalized dataが未検出、または読み取り不可
```

今回の履歴拡張は実API未使用のmockである。

---

# 7. date range / business day count

監査スクリプトは以下を出力する。

```text
date_min
date_max
business_day_count
code_count
row_count
```

Phase4-KのREADY目安:

```text
business_day_count >= 60
code_count > 0
row_count > 0
```

---

# 8. per-code lookback統計

監査スクリプトは以下を出力する。

```text
per_code_row_count_min
per_code_row_count_max
per_code_row_count_mean
codes_with_sufficient_lookback
codes_with_insufficient_lookback
```

Phase4-Kでは `min_lookback_rows = 60` を基準にする。

---

# 9. prepared dry-run結果

実行コマンド:

```bash
python3 scripts/build_candidate_features_real_prepared_dry_run.py
python3 scripts/audit_phase4k_normalized_history_readiness.py
```

目標:

```text
eligible_count > 0
schema_validation_status = OK
leakage_audit_status = OK
readiness_status = READY_FOR_FULL_RANGE_FEATURE_DRY_RUN
```

---

# 10. readiness判定

Phase4-K complete条件:

```text
daily_quotes_normalized history >= 60 business days
codes_with_sufficient_lookback > 0
eligible_count > 0
schema validation OK
leakage audit OK
readiness_status = READY_FOR_FULL_RANGE_FEATURE_DRY_RUN
```

履歴不足の場合:

```text
readiness_status = BLOCKED_BY_DATA_WINDOW
```

---

# 11. 禁止事項遵守確認

Phase4-Kでは以下を実装しない。

```text
label生成
dataset builder
Candidate AI本体
学習
推論
backtest
売買
Paper Trading
Broker実API
発注
Portfolio自動更新
```

Phase4-Kの追加コードは、normalized履歴準備、prepared dry-run readiness監査、レポート、テストに限定する。

---

# 12. Phase4-Lへの引き継ぎ

Phase4-L案:

```text
Candidate Feature Full-range Dry-run Execution Plan
```

検討事項:

```text
mockではなく実runtime履歴をどこまで拡張するか
full-range feature生成前の性能・保存形式確認
eligible/excluded分布の品質レビュー
feature null率・外れ値レポート
full-range dry-runの実行単位と中断可能性
```
