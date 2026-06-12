# AI Fund Lab vNext Phase4-B Candidate Training Data Design Report

---

# 1. このレポートの目的

本レポートは、Phase4-B Candidate Training Data Design の完了条件を確認する。

今回のゴールは、Candidate AIを学習させる前に、学習データの形、正解ラベル、未来リーク防止ルールを固定することである。

Phase4-Bでは設計のみを行い、実装本体には入らない。

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
docs/phase_reports/phase4a_candidate_ai_design.md
reports/phase_reports/phase4a_candidate_ai_design_audit.json
```

---

# 3. Phase4-B設計内容の要約

Phase4-Bでは以下を定義した。

```text
feature table schema
label table schema
training dataset schema
audit table schema
as_of_date rule
target_date rule
lookback window rule
future label isolation
train/validation/test split rule
leakage audit rule
candidate selection evaluation rule
```

Candidate AIの責務は、全銘柄から見る価値がある上昇候補を抽出することに限定する。

---

# 4. 利用可能データ

```text
2021-06以降の実市場データ
daily_quotes_normalized
listed issue master
trading calendar
fins summary
market index data
sector aggregation data
```

`daily_quotes_normalized` を価格・出来高featureの正規入力とする。

---

# 5. feature table schema

主キー:

```text
target_date
code
feature_version
```

必須メタ列:

```text
target_date
as_of_date
code
feature_version
source_snapshot_id
data_start_date
data_end_date
created_at
feature_set_name
```

featureカテゴリ:

```text
Quality
Price Momentum
Volume Momentum
Liquidity / Tradability
Market Environment
Sector Relative Strength
Exclusion / Risk Filter
```

feature table には future 系、backtest、trade、portfolio、order、profit/loss/pnl 系を入れない。

---

# 6. label table schema

主キー:

```text
target_date
code
label_version
```

ラベル候補:

```text
future_return_5d
future_return_10d
future_return_20d
future_max_return_20d
future_max_drawdown_20d
top_decile_20d
downside_bad_20d
momentum_candidate_label
```

label table は評価・学習時のみ使う。推論時には読まない。

---

# 7. training dataset schema

training dataset は feature table と label table を学習用に結合した論理datasetとする。

必須メタ列:

```text
target_date
as_of_date
code
dataset_version
feature_version
label_version
split
created_at
```

feature columns と label columns はprefixまたはschemaで明示的に分離する。

---

# 8. audit table schema

audit table は、学習データ生成とleakage確認の証跡を保持する。

必須列:

```text
audit_id
target_date
as_of_date
code
feature_version
label_version
dataset_version
source_snapshot_id
feature_generated_at
label_generated_at
dataset_generated_at
leakage_check_status
leakage_check_messages
forbidden_feature_detected
future_label_isolated
split
excluded_reason
candidate_reason_coverage_ready
created_at
```

---

# 9. as_of_date / target_date rule

最重要ルール:

```text
featureは as_of_date 時点で観測可能な情報のみで作る
```

`target_date` は候補抽出対象営業日である。

原則:

```text
as_of_date <= target_date
target_dateより後の情報はfeatureに使わない
当日OHLCVを使う場合は日次確定後に限定する
財務情報は公表日 <= as_of_date のものだけ使う
```

---

# 10. train/validation/test split

分割は時系列順に行う。

ランダム分割は禁止。

推奨分割:

```text
Train:      2021-06 ～ 2024-12
Validation: 2025-01 ～ 2025-12
Test:       2026-01 ～
```

実データ範囲に応じて調整してよいが、未来方向の時系列分割を必須とする。

---

# 11. leakage防止ルール

必須チェック:

```text
as_of_date <= target_date
feature table に future_return_* を含めない
feature table に future_max_return_* を含めない
feature table に future_max_drawdown_* を含めない
feature table に top_decile_* を含めない
feature table に downside_bad_* を含めない
feature table に backtest/trade/portfolio/order/execution/profit/loss/pnl を含めない
財務featureは公表日 <= as_of_date のデータだけを使う
価格・出来高featureは target_date 以前の daily_quotes_normalized だけを使う
split は時系列分割でありランダム分割ではない
推論用datasetに label columns を含めない
```

leakage audit が ERROR の場合、学習に進まない。

---

# 12. 利用禁止feature

```text
future_return_*
future_max_return_*
future_max_drawdown_*
top_decile_*
downside_bad_*
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

# 13. Candidate AI責務境界

Candidate AIがやること:

```text
全銘柄から見る価値がある上昇候補を抽出する
candidate_scoreを出す
candidate_reasonを出す
excluded_reasonを出す
```

Candidate AIがやらないこと:

```text
買い判断
期待値判断
購入金額判断
保有判断
売却判断
資金配分
Paper Trading
発注
売買
Portfolio更新
```

---

# 14. Phase4-Bで実装していないこと

```text
feature builder本体
dataset builder本体
label生成本体
Candidate AI本体
学習処理
推論処理
バックテスト
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

# 15. Phase4-B完了判定

Phase4-Bは完了可能である。

理由:

```text
feature / label / training dataset / audit schema を定義した
as_of_date / target_date rule を定義した
future label isolation を定義した
時系列splitとランダム分割禁止を定義した
leakage audit rule を定義した
candidate selection evaluation rule を定義した
禁止feature一覧を明記した
実装本体には進んでいない
```

---

# 16. Phase4-C案

次に進むべきPhase4-C:

```text
Candidate Feature Builder Design
```

Phase4-Cで決めること:

```text
feature builderの入出力設計
daily_quotes_normalized からのfeature生成仕様
fins summary の公表日反映仕様
sector aggregation の生成仕様
feature_version管理
runtime保存先
leakage auditの実装計画
mock fixture設計
```
