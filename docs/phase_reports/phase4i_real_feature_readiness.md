# AI Fund Lab vNext Phase4-I Real Feature Dry-run Readiness Report

---

# 1. このレポートの目的

本レポートは、Phase4-Hで生成した real feature dry-run 出力をレビューし、次に full-range feature dry-run へ進める条件を明確にする。

Phase4-Iでは監査のみを行う。label生成、dataset builder、Candidate AI本体、学習、推論、backtest、売買、Paper Trading、Broker実API、発注、Portfolio自動更新は実装しない。

---

# 2. 読んだドキュメント/出力

```text
docs/phase_reports/phase4h_real_feature_dry_run.md
docs/phase_reports/phase4h_real_feature_dry_run_audit.md
reports/phase_reports/phase4h_real_feature_dry_run_audit.json
reports/candidate_ai/phase4h_real_feature_dry_run_summary.json
.runtime/candidate_ai/features/candidate_features_real_dry_run_2026-06-01.json
.runtime/candidate_ai/manifests/candidate_features_real_dry_run_manifest_2026-06-01.json
.runtime/candidate_ai/audit/candidate_features_real_dry_run_audit_2026-06-01.json
docs/03_ai_design/candidate_feature_builder_design.md
docs/03_ai_design/candidate_training_data_design.md
src/ai_fund_lab_v2/candidate_ai/feature_builder.py
src/ai_fund_lab_v2/candidate_ai/normalized_data_reader.py
src/ai_fund_lab_v2/candidate_ai/trading_calendar_window.py
src/ai_fund_lab_v2/candidate_ai/validation.py
src/ai_fund_lab_v2/candidate_ai/leakage_audit.py
```

---

# 3. Phase4-H dry-run結果レビュー

現在の実 `.runtime` 出力では以下を確認した。

```text
row_count = 10
eligible_count = 0
excluded_count = 10
excluded_reason_counts = {"insufficient_lookback": 10}
schema_validation_status = OK
leakage_audit_status = OK
storage_format = parquet
normalized_as_of_date = 2026-06-01
window_start_date = 2026-06-01
```

---

# 4. eligible/excluded分布

すべてのfeature rowが `insufficient_lookback` で除外されている。

```text
eligible: 0
excluded: 10
excluded_reason: insufficient_lookback
```

Candidate Feature Builder の `MIN_LOOKBACK_ROWS` は21である。今回のdry-runでは各銘柄の `data_start_date` と `data_end_date` が同じ `2026-06-01` であり、1営業日分しかfeature計算に渡っていない。

---

# 5. insufficient_lookback原因分析

原因は以下の可能性が高い。

```text
小範囲dry-run設定による想定内の除外
normalized data自体が現時点では1日分に近い
trading calendar windowが2026-06-01から2026-06-01になっている
as_of_dateが実データ内の十分後方日付ではない
```

現時点で可能性が低いもの:

```text
schema validation問題
leakage audit問題
feature builder lookback判定問題
```

理由:

```text
schema validationはOK
leakage auditはOK
feature builderは21 rows未満をinsufficient_lookbackにしており、今回の入力は各code 1 row程度である
```

---

# 6. feature completeness

必須feature列は出力に存在する。

```text
price_momentum_return_5d
price_momentum_return_20d
volume_momentum_ratio_5d
volatility_return_std_20d
trend_close_over_ma_20d
liquidity_avg_volume_20d
missing_flags_insufficient_lookback
```

ただし `insufficient_lookback` のため、数値featureはnullである。これは想定内であり、full-range dry-run前に十分なlookback windowを確保する必要がある。

---

# 7. readiness判定

現在の判定:

```text
BLOCKED_BY_DATA_WINDOW
```

理由:

```text
feature output / manifest / audit は存在する
schema validation は OK
leakage audit は OK
必須feature列は存在する
ただし eligible_count = 0
全rowが insufficient_lookback
```

---

# 8. full-range feature dry-runへ進む条件

次に進む前の条件:

```text
as_of_date を実データ内の十分後方日付にする
lookback_business_days >= 60 を確保する
max_rows を code_count x lookback に十分な値へ増やす
readerが各codeごとにlookback分を保持できるようにする
eligible_count > 0 を確認する
schema validation OK を維持する
leakage audit OK を維持する
```

---

# 9. Phase4-Iでやらないこと

```text
実データ全量feature生成
label生成
dataset builder
Candidate AI本体
学習
推論
backtest
Historical Evaluation
Opportunity AI
Position Management AI
Capital Allocation
Paper Trading
Order Manager
Broker実API接続
発注
売買
Portfolio自動更新
```

---

# 10. Phase4-Jへの引き継ぎ

Phase4-J案:

```text
Candidate Feature Full-range Dry-run Preparation
```

検討事項:

```text
十分な過去日数があるas_of_date選択
max_rows / max_codes / lookback の拡張
per-code lookback保持の検証
eligible_count > 0 の確認
feature品質レポートの拡張
```
