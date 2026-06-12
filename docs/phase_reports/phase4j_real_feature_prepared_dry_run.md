# AI Fund Lab vNext Phase4-J Candidate Feature Full-range Dry-run Preparation Report

---

# 1. このレポートの目的

本レポートは、Phase4-J Candidate Feature Full-range Dry-run Preparation の完了条件を確認する。

Phase4-Jの目的は、Phase4-Iで `BLOCKED_BY_DATA_WINDOW` となった原因を踏まえ、十分な履歴を持つ小〜中範囲dry-run条件を準備し、`eligible_count > 0` を確認できる導線を作ることである。

Phase4-Jでは実データ全量feature生成は実装しない。

---

# 2. 読んだドキュメント/出力

```text
docs/phase_reports/phase4h_real_feature_dry_run.md
docs/phase_reports/phase4i_real_feature_readiness.md
docs/phase_reports/phase4i_real_feature_readiness_audit.md
reports/phase_reports/phase4h_real_feature_dry_run_audit.json
reports/phase_reports/phase4i_real_feature_readiness_audit.json
reports/candidate_ai/phase4h_real_feature_dry_run_summary.json
src/ai_fund_lab_v2/candidate_ai/normalized_data_reader.py
src/ai_fund_lab_v2/candidate_ai/trading_calendar_window.py
src/ai_fund_lab_v2/candidate_ai/data_loader.py
src/ai_fund_lab_v2/candidate_ai/feature_builder.py
src/ai_fund_lab_v2/candidate_ai/validation.py
src/ai_fund_lab_v2/candidate_ai/leakage_audit.py
```

---

# 3. Phase4-J実装内容の要約

作成した要素:

```text
scripts/build_candidate_features_real_prepared_dry_run.py:
  as_of_date自動選定
  lookback/max_codes/max_rows拡張
  per-code lookback保持確認
  prepared dry-run summary
  readiness_status出力

scripts/audit_phase4j_real_feature_prepared_dry_run.py:
  Phase4-J completion audit
```

---

# 4. as_of_date自動選定

`select_prepared_as_of_date()` は normalized data 内の日付分布を確認し、少なくとも1銘柄が `MIN_LOOKBACK_ROWS` 以上の履歴を持つ末尾側の日付を選ぶ。

十分な履歴がある日付が見つからない場合は、データ内の最新日付を返し、dry-run readiness は `BLOCKED_BY_DATA_WINDOW` となる。

---

# 5. lookback / max_rows / max_codes設定

default設定:

```text
lookback_business_days = 60
max_codes = 30
max_rows = 1800
```

方針:

```text
lookback_business_days >= 60
max_codes は小〜中範囲に制限
max_rows >= max_codes x lookback_business_days
```

---

# 6. per-code lookback保持確認

prepared dry-run summaryには以下を出力する。

```text
per_code_row_count_min
per_code_row_count_max
per_code_row_count_mean
codes_with_sufficient_lookback
codes_with_insufficient_lookback
```

これにより、feature builderへ渡る時点で各codeに必要履歴が残っているか確認できる。

---

# 7. readiness判定

判定候補:

```text
READY_FOR_FULL_RANGE_FEATURE_DRY_RUN
BLOCKED_BY_DATA_WINDOW
BLOCKED_BY_SCHEMA
BLOCKED_BY_LEAKAGE
BLOCKED_BY_RUNTIME_OUTPUT
```

判定ルール:

```text
eligible_count > 0 かつ schema validation OK かつ leakage audit OK
  -> READY_FOR_FULL_RANGE_FEATURE_DRY_RUN

eligible_count = 0
  -> BLOCKED_BY_DATA_WINDOW
```

---

# 8. real runtimeでの注意

現 `.runtime` の `daily_quotes_normalized` は `2026-06-01` の1日分のみである。

そのため、real runtime上では引き続き `BLOCKED_BY_DATA_WINDOW` となる可能性が高い。

Phase4-Jは、十分な履歴があるデータに対して eligible_count > 0 を確認できる prepared dry-run導線を作る段階である。

---

# 9. runtime出力先

prepared dry-run生成物:

```text
.runtime/candidate_ai/features/candidate_features_real_prepared_dry_run_{as_of_date}.json
.runtime/candidate_ai/manifests/candidate_features_real_prepared_dry_run_manifest_{as_of_date}.json
.runtime/candidate_ai/audit/candidate_features_real_prepared_dry_run_audit_{as_of_date}.json
reports/candidate_ai/phase4j_real_feature_prepared_dry_run_summary.json
```

---

# 10. 禁止事項

Phase4-Jでは以下を実装しない。

```text
実データ全量feature生成は実装しない
label生成は実装しない
dataset builderは実装しない
Candidate AI本体は実装しない
学習は実装しない
推論は実装しない
backtestは実装しない
Historical Evaluationは実装しない
Opportunity AIは実装しない
Position Management AIは実装しない
Capital Allocationは実装しない
Paper Tradingは実装しない
Order Managerは実装しない
Broker実API接続は実装しない
発注は実装しない
売買は実装しない
Portfolio自動更新は実装しない
```

---

# 11. Phase4-Kへの引き継ぎ

Phase4-K案:

```text
Candidate Feature Broader Real Dry-run Execution
```

検討事項:

```text
十分な履歴を持つnormalized dataの投入
prepared dry-runを実runtimeでREADYにする
eligible/excluded分布の品質レビュー
feature null率レポート
full-range前のparquet/jsonl性能確認
```
