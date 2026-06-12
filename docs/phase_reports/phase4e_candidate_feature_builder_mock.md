# AI Fund Lab vNext Phase4-E Candidate Feature Builder Mock Implementation Report

---

# 1. このレポートの目的

本レポートは、Phase4-E Candidate Feature Builder Mock Implementation の完了条件を確認する。

Phase4-Eの目的は、Phase4-Dで作ったschema contract / validation / leakage auditを使い、mock `daily_quotes_normalized` からCandidate AI用feature tableを最小生成し、runtime dry-run保存まで接続することである。

Phase4-Eではmock fixtureだけを扱う。実daily_quotes_normalized読み込みは実装しない。

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
reports/phase_reports/phase4a_candidate_ai_design_audit.json
reports/phase_reports/phase4b_candidate_training_data_design_audit.json
reports/phase_reports/phase4c_candidate_feature_builder_design_audit.json
reports/phase_reports/phase4d_candidate_feature_builder_skeleton_audit.json
```

---

# 3. Phase4-E実装内容の要約

作成した要素:

```text
mock_data.py:
  mock daily_quotes_normalized fixture

feature_builder.py:
  mock fixtureからCandidate feature rowsを生成
  schema validation / leakage audit 接続

manifest.py:
  feature JSON
  manifest JSON
  audit JSON
  runtime保存

scripts/build_candidate_features_mock.py:
  mock専用dry-run生成CLI

scripts/audit_phase4e_candidate_feature_builder_mock.py:
  Phase4-E完了監査
```

---

# 4. 入力

入力はmock `daily_quotes_normalized` fixtureのみである。

必須入力列:

```text
date
code
open
high
low
close
volume
```

Phase4-Eでは、実データストア、J-Quants、parquet、CSV、MarketDataStoreからの読み込みは行わない。

---

# 5. 出力schema

必須列:

```text
as_of_date
target_date
code
feature_version
source_snapshot_id
universe_eligible
excluded_reason
```

任意メタ列:

```text
feature_set_name
created_at
data_start_date
data_end_date
```

---

# 6. 生成するmock feature

Phase4-Eで生成するfeatureは、価格・出来高の最小subsetに限定する。

```text
price_momentum_return_5d
price_momentum_return_20d
volume_momentum_ratio_5d
volatility_return_std_20d
trend_close_over_ma_20d
liquidity_avg_volume_20d
missing_flags_insufficient_lookback
```

すべてPhase4-Dの許可prefixに従う。

---

# 7. as_of_date / target_date rule

feature生成は `date <= as_of_date` のmock行だけを使う。

`date > as_of_date` の行がfixtureに含まれていても、feature計算には使わない。

`target_date` は `as_of_date` 以上である。Phase4-Eのmockでは未指定時に `target_date = as_of_date` とする。

---

# 8. Universe Eligibility

必要lookbackが不足する銘柄は候補対象外にする。

```text
universe_eligible = False
excluded_reason = insufficient_lookback
missing_flags_insufficient_lookback = True
```

lookbackが十分な銘柄は以下とする。

```text
universe_eligible = True
excluded_reason = ""
missing_flags_insufficient_lookback = False
```

---

# 9. Manifest / Audit

Phase4-Eでは生成物ごとにmanifestとauditを保存する。

manifestには以下を含める。

```text
feature_version
created_at
as_of_date
target_date
row_count
eligible_count
excluded_count
source_snapshot_id
input_sources
output_path
audit_path
schema_version
```

auditには以下を含める。

```text
status
row_count
eligible_count
excluded_count
forbidden_feature_detected
forbidden_columns
missing_required_columns
invalid_prefix_columns
excluded_reason_counts
```

---

# 10. Runtime保存先

生成物はruntime dir配下に集約する。

```text
.runtime/candidate_ai/features/
.runtime/candidate_ai/manifests/
.runtime/candidate_ai/audit/
```

`reports/candidate_ai/` は生成物保存先としては使わない。Phase audit reportのみ `docs/phase_reports/` と `reports/phase_reports/` に保存する。

---

# 11. 禁止データ

feature tableには以下を入れない。

```text
future_return_*
future_max_return_*
future_max_drawdown_*
top_decile_*
downside_bad_*
momentum_candidate_label
backtest result
trade result
selected
bought
sold
cash
portfolio
annual_return
final_assets
paper_trade
position
allocation
order
execution
profit
loss
pnl
```

---

# 12. Phase4-Eでやらないこと

Phase4-Eでは以下を実装しない。

```text
実daily_quotes_normalized読み込みは実装しない
fins_summary結合は実装しない
market index結合は実装しない
sector aggregation結合は実装しない
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

# 13. 実行方法

```bash
python3 scripts/build_candidate_features_mock.py
python3 scripts/audit_phase4e_candidate_feature_builder_mock.py
python3 -m pytest tests/test_phase4e_candidate_feature_builder_mock.py
```

---

# 14. Phase4-E完了条件

```text
mock daily_quotes_normalized fixtureがある
mock feature builderがある
schema validationが通る
leakage auditが通る
禁止featureを検出できる
manifest JSONを保存できる
audit JSONを保存できる
runtime配下にfeature JSONを保存できる
実データ読み込み、label生成、学習、推論、backtest、発注に進んでいない
```

---

# 15. Phase4-Fへの引き継ぎ

Phase4-Fでは、実データ読み込みに進む前に以下を検討する。

```text
daily_quotes_normalized loader contract
実データ用のlookback window整合
取引カレンダーとの営業日window整合
feature_version更新ルール
manifestにinput snapshot hashを入れる方針
mockから実データへの差し替え監査
```
