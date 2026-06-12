# AI Fund Lab vNext Phase4-G Real Normalized Data Dry-run / Trading Calendar Window Report

---

# 1. このレポートの目的

本レポートは、Phase4-G Real Normalized Data Dry-run / Trading Calendar Window の完了条件を確認する。

Phase4-Gの目的は、Phase1 Data Foundation の `.runtime/data/raw_normalized/...` 配下にある `daily_quotes_normalized` を小範囲 dry-run で読み、Candidate AI loader contractへ接続できることを確認することである。

Phase4-Gでは実データ全量feature生成は実装しない。

---

# 2. 読んだ資料

```text
docs/00_vision/investment_philosophy.md
docs/01_requirements/system_requirements.md
docs/01_requirements/success_metrics.md
docs/01_requirements/phase_roadmap.md
docs/02_architecture/system_architecture.md
docs/03_ai_design/candidate_ai_design.md
docs/03_ai_design/candidate_feature_catalog.md
docs/03_ai_design/candidate_training_data_design.md
docs/03_ai_design/candidate_feature_builder_design.md
docs/phase_reports/phase4a_candidate_ai_design.md
docs/phase_reports/phase4b_candidate_training_data_design.md
docs/phase_reports/phase4c_candidate_feature_builder_design.md
docs/phase_reports/phase4d_candidate_feature_builder_skeleton.md
docs/phase_reports/phase4e_candidate_feature_builder_mock.md
docs/phase_reports/phase4f_candidate_real_data_loader_contract.md
reports/phase_reports/phase4a_candidate_ai_design_audit.json
reports/phase_reports/phase4b_candidate_training_data_design_audit.json
reports/phase_reports/phase4c_candidate_feature_builder_design_audit.json
reports/phase_reports/phase4d_candidate_feature_builder_skeleton_audit.json
reports/phase_reports/phase4e_candidate_feature_builder_mock_audit.json
reports/phase_reports/phase4f_candidate_real_data_loader_contract_audit.json
```

---

# 3. Phase4-G実装内容の要約

作成した要素:

```text
normalized_data_reader.py:
  RuntimePaths経由の daily_quotes_normalized discovery
  jsonl / parquet input support
  small-range read
  Phase4-F loader contract接続
  SKIPPED安全終了

trading_calendar_window.py:
  trading calendar window helper
  非営業日as_of_dateの直前営業日正規化
  weekday fallback

scripts/check_candidate_real_normalized_dry_run.py:
  real normalized data small-range dry-run

scripts/audit_phase4g_real_normalized_dry_run.py:
  Phase4-G completion audit
```

---

# 4. normalized data discovery結果

実装上の探索先:

```text
.runtime/data/raw_normalized/jquants/equities_bars_daily/data.parquet
.runtime/data/raw_normalized/jquants/equities_bars_daily/data.jsonl
```

`input_format=auto` では `parquet` を優先し、存在しなければ `jsonl` を探す。

データが存在しない場合、dry-runは失敗せず以下を返す。

```text
status = SKIPPED
message = daily_quotes_normalized data not found under runtime raw_normalized path
```

---

# 5. 対応形式 jsonl/parquet

対応形式:

```text
jsonl
parquet
```

parquet読み込み時に依存ライブラリ不足や読み込み失敗がある場合は `SKIPPED` としてauditに理由を残す。

---

# 6. small-range read条件

dry-runは実データ全量をfeature生成へ流さない。

制限:

```text
lookback_business_days: default 60
max_codes: default 10
max_rows: default 1000
```

処理:

```text
1. normalized dataをdiscover
2. requested as_of_dateを決定
3. trading calendar windowを作成
4. window_start_date <= Date <= normalized_as_of_date の銘柄候補を抽出
5. max_codesで銘柄数を制限
6. max_rowsでsource rowsを制限
7. Phase4-F adapterへ渡す
```

---

# 7. trading calendar window rule

Phase4-Gでは trading calendar raw が存在する場合はそれを利用する。

方針:

```text
as_of_dateが営業日ならそのまま
as_of_dateが非営業日なら直前営業日に正規化
lookbackは営業日ベース
window_start_date <= date <= normalized_as_of_date
```

trading calendar raw がない場合は weekday fallback を使う。fallbackは後続Phaseで既存TradingCalendarServiceへ完全差し替え可能な最小実装である。

---

# 8. as_of_date正規化ルール

例:

```text
requested_as_of_date = 2026-06-07
2026-06-07 が非営業日
normalized_as_of_date = 2026-06-05
```

正規化有無は `TradingCalendarWindow.as_of_date_was_normalized` に保持する。

---

# 9. future row exclusion audit

Phase4-Gでは、window source rowsにfuture rowが含まれてもPhase4-F adapterで除外される。

記録項目:

```text
dropped_future_row_count
input_row_count
filtered_row_count
source_snapshot_id
input_hash_optional
input_source_path
input_manifest_path
```

---

# 10. runtime出力先

dry-run生成物:

```text
.runtime/candidate_ai/tmp/
.runtime/candidate_ai/manifests/
.runtime/candidate_ai/audit/
reports/candidate_ai/
```

`.runtime/candidate_ai/tmp/` は dry-run rows、`.runtime/candidate_ai/manifests/` は loader manifest、`.runtime/candidate_ai/audit/` は loader audit、`reports/candidate_ai/` はdry-run summaryを保存する。

---

# 11. Phase4-E互換確認

以下が引き続き通ることを確認する。

```bash
python3 scripts/build_candidate_features_mock.py
python3 scripts/audit_phase4e_candidate_feature_builder_mock.py
```

---

# 12. 禁止事項

Phase4-Gでは以下を実装しない。

```text
実データ全量feature生成は実装しない
実fins_summary結合は実装しない
実market index処理は実装しない
実sector aggregation処理は実装しない
label生成は実装しない
dataset builderは実装しない
Candidate AI本体は実装しない
学習は実装しない
推論は実装しない
backtestは実装しない
Historical Evaluationは実装しない
Paper Tradingは実装しない
Opportunity AIは実装しない
Position Management AIは実装しない
Capital Allocationは実装しない
Order Managerは実装しない
Broker実API接続は実装しない
発注は実装しない
売買は実装しない
Portfolio自動更新は実装しない
```

---

# 13. Phase4-G完了条件

```text
normalized data readerがある
daily_quotes_normalized discoveryが実装されている
jsonl / parquet の少なくとも存在形式に対応している
small-range readが実装されている
max_codes / max_rows で読み込み範囲を制限できる
trading calendar window helperがある
非営業日as_of_dateの扱いが定義されている
lookback営業日windowが定義されている
Phase4-F loader contractへ接続されている
future row exclusionがaudit/manifestに記録される
dry-run scriptがある
実データがない場合SKIPPEDで安全終了できる
Phase4-E mock builderが壊れていない
実データ全量feature生成、label生成、学習、推論、backtest、売買系に進んでいない
```

---

# 14. Phase4-Hへの引き継ぎ

Phase4-H案:

```text
Candidate Real Data Feature Builder Small-scope Dry-run
```

検討事項:

```text
Phase4-G reader outputを feature_builder へ接続
1〜数銘柄だけの実feature dry-run
manifestに normalized input manifest/hash を連鎖
insufficient lookback / liquidity exclusion の実データ検査
feature JSONを .runtime/candidate_ai/features/ へ保存する条件
```
