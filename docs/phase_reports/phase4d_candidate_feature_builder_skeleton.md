# AI Fund Lab vNext Phase4-D Candidate Feature Builder Skeleton / Schema Contracts Report

---

# 1. このレポートの目的

本レポートは、Phase4-D Candidate Feature Builder Skeleton / Schema Contracts の完了条件を確認する。

今回のゴールは、Candidate Feature Builder本体実装前に、壊れにくいschema contractと監査可能な骨格を作ることである。

Phase4-Dでは以下だけを実装する。

```text
feature schema contract
manifest schema contract
audit schema contract
runtime path helper
mock fixture
schema validation
leakage audit minimal code
phase report
phase audit
pytest
```

Phase4-Dでは、daily_quotes_normalizedからの実feature生成、fins_summary結合、market index集計、sector aggregation生成、label生成、dataset builder、Candidate AI本体、学習、推論、backtest、Historical Evaluation、Paper Trading、Order Manager、Broker実API接続、発注、売買、Portfolio自動更新は実装しない。

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
reports/phase_reports/phase4a_candidate_ai_design_audit.json
reports/phase_reports/phase4b_candidate_training_data_design_audit.json
reports/phase_reports/phase4c_candidate_feature_builder_design_audit.json
```

---

# 3. Phase4-D実装内容の要約

`src/ai_fund_lab_v2/candidate_ai/` にCandidate AI用package skeletonを追加した。

作成した要素:

```text
schemas.py:
  feature schema contract
  manifest schema contract
  audit schema contract
  必須列
  許可feature prefix
  禁止feature / 禁止語

paths.py:
  runtime path helper

validation.py:
  feature table schema validation

leakage_audit.py:
  列名ベースのleakage audit最小コード

__init__.py:
  public export
```

---

# 4. Feature Schema Contract

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

許可feature prefix:

```text
price_momentum_
volume_momentum_
volatility_
trend_
relative_strength_
market_regime_
sector_relative_
fundamental_
liquidity_
missing_flags_
```

任意メタ列:

```text
feature_set_name
created_at
data_start_date
data_end_date
```

禁止feature / 禁止語:

```text
future_return_
future_max_return_
future_max_drawdown_
top_decile_
downside_bad_
momentum_candidate_label
backtest
trade
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

# 5. Manifest Schema Contract

manifest schema contract は以下を含む。

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
code_hash_optional
```

---

# 6. Audit Schema Contract

audit schema contract は以下を含む。

```text
status
feature_version
as_of_date
target_date
row_count
forbidden_feature_detected
forbidden_columns
future_column_detected
label_column_detected
post_as_of_data_detected
fins_publication_violation_detected
target_date_leakage_detected
missing_required_columns
invalid_prefix_columns
eligible_count
excluded_count
excluded_reason_counts
```

---

# 7. Runtime Path Helper

Candidate AIの生成物はruntime dir配下に集約する。

```text
.runtime/candidate_ai/
.runtime/candidate_ai/features/
.runtime/candidate_ai/manifests/
.runtime/candidate_ai/audit/
.runtime/candidate_ai/reports/
.runtime/candidate_ai/tmp/
```

Phase4-Dではpath helperとディレクトリ作成関数まで実装し、feature保存本体は実装しない。

---

# 8. Schema Validation内容

最小validationは以下を確認する。

```text
必須列が存在する
禁止列名が存在しない
許可prefix以外のfeature列を検出できる
as_of_date <= target_date
universe_eligibleがboolとして扱える
excluded_reasonが存在する
```

対象はmock fixtureの `list[dict]` またはDataFrame-like objectである。

---

# 9. Leakage Audit最小実装内容

Phase4-Dのleakage auditは列名・日付contractで検査できる最小範囲に限定する。

検出対象:

```text
future/top_decile/downside/label/pnl/profit/loss 系列の列名
backtest/trade/portfolio/cash/order 系列の列名
禁止feature
as_of_date > target_date
```

実データの過去参照検証、fins_summary公開日検証、market/sector元データ検証はPhase4-Dでは本実装しない。

---

# 10. Mock Fixture / Test内容

pytestでは以下を確認する。

```text
valid feature table がvalidation OKになる
forbidden column を検出する
as_of_date > target_date を検出する
invalid prefix column を検出する
runtime path helper が .runtime/candidate_ai/ 配下を返す
manifest/audit schema contract が必須項目を持つ
phase audit script がcompleteになる
```

---

# 11. Phase4-D完了判定

Phase4-Dは完了可能である。

理由:

```text
Candidate AI package skeleton が存在する
feature schema contract が存在する
manifest schema contract が存在する
audit schema contract が存在する
runtime path helper が存在する
schema validation が存在する
leakage audit minimal code が存在する
valid / forbidden / date violation のmock fixture testがある
実feature生成・label生成・学習・推論・backtest・売買系を実装していない
```

---

# 12. Phase4-E案

次に進むべきPhase4-E:

```text
Candidate Feature Builder Mock Implementation
```

Phase4-Eで検討すること:

```text
mock daily_quotes_normalized fixtureからの価格・出来高feature生成
feature schema validationの統合
leakage auditの統合
manifest/audit JSON出力
runtime pathへのdry-run保存
実データ取得やAI学習にはまだ進まない
```
