# AI Fund Lab vNext Phase4-C Candidate Feature Builder Design Report

---

# 1. このレポートの目的

本レポートは、Phase4-C Candidate Feature Builder Design の完了条件を確認する。

今回のゴールは、Candidate AIのfeature生成実装に入る前に、featureの作り方、保存先、監査条件、未来リーク防止条件を固定することである。

Phase4-Cでは設計のみを行い、feature builder本体には入らない。

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
docs/phase_reports/phase4a_candidate_ai_design.md
docs/phase_reports/phase4b_candidate_training_data_design.md
reports/phase_reports/phase4a_candidate_ai_design_audit.json
reports/phase_reports/phase4b_candidate_training_data_design_audit.json
```

---

# 3. Phase4-C設計内容の要約

Phase4-Cでは以下を定義した。

```text
feature builder responsibility
input source
output schema
feature category
lookback window
as_of_date rule
fins_summary publication date rule
market index feature rule
sector aggregation rule
missing value rule
universe filter rule
feature_version rule
runtime output path
manifest/audit integration
leakage audit rule
mock fixture design
```

---

# 4. Feature Builder Responsibility

Candidate Feature Builder の責務は以下である。

```text
as_of_date時点で観測可能な市場データだけを使い、
Candidate AIが候補抽出に使うfeature tableを生成するための仕様を提供する
```

Feature Builder は、買い判断、期待値判断、購入金額判断、保有判断、売却判断、資金配分、Paper Trading、発注、売買、Portfolio更新を行わない。

---

# 5. Input Source

中心入力:

```text
daily_quotes_normalized
```

利用可能データ:

```text
daily_quotes_normalized
listed issue master
trading calendar
fins_summary
market index data
sector aggregation data
```

---

# 6. Output Schema

Candidate feature table の必須列:

```text
as_of_date
target_date
code
feature_version
source_snapshot_id
feature_set_name
universe_eligible
excluded_reason
created_at
data_start_date
data_end_date
```

feature列prefix:

```text
price_momentum_*
volume_momentum_*
volatility_*
trend_*
relative_strength_*
market_regime_*
sector_relative_*
fundamental_*
liquidity_*
universe_eligibility_*
missing_flags_*
```

---

# 7. Feature Category

```text
price momentum features
volume momentum features
volatility features
trend features
relative strength features
market regime features
sector relative features
fundamental freshness features
liquidity features
universe eligibility features
```

---

# 8. as_of_date / lookback rule

最重要ルール:

```text
featureはas_of_date時点で見えている情報のみで生成する
```

lookback rule:

```text
featureはas_of_date以前のデータのみで生成
lookback windowはas_of_dateから過去方向のみ
target_date以降のデータ参照禁止
trading calendarで営業日ベースに揃える
```

基本window:

```text
5営業日
10営業日
20営業日
60営業日
```

---

# 9. fins_summary publication date rule

必須ルール:

```text
決算情報は公表日ベースでas_of_date以前に利用可能なもののみ使用
period end dateのみで結合しない
未公表情報をfeatureに入れない
```

使用可能条件:

```text
disclosed_date <= as_of_date
```

または:

```text
equivalent_publication_date <= as_of_date
```

---

# 10. Missing Value Rule

```text
必要最小window不足はexcluded_reason
一部欠損はmissing_flagsに記録
欠損補完は明示的にfeature_versionへ反映
raw v1から直接補完しない
補完方法を変更したらfeature_versionを上げる
```

---

# 11. Universe Filter Rule

候補対象外条件:

```text
上場廃止済み
取引停止相当
監理銘柄
整理銘柄
流動性不足
価格欠損
出来高欠損
必要lookback不足
異常値
daily_quotes_normalized の正規化除外record
```

除外は候補抽出のための前処理であり、買い判断ではない。

---

# 12. Runtime Output Path

実生成物はruntime dir配下に集約する。

```text
.runtime/candidate_ai/features/
.runtime/candidate_ai/manifests/
.runtime/candidate_ai/audit/
.runtime/candidate_ai/reports/
.runtime/candidate_ai/tmp/
```

トップレベルの `reports/candidate_ai/` は実生成物保存先にしない。フェーズ監査レポートだけ既存形式に合わせて `docs/phase_reports/` と `reports/phase_reports/` に保存する。

---

# 13. Leakage Audit Rule

検出対象:

```text
feature列名にfuture/top_decile/downside/label/pnl/profit/loss等が含まれる
feature生成にas_of_dateより後のデータが使われる
fins_summaryが公開日前に結合される
target_date以降のデータがfeatureに混入する
backtest/trade/portfolio/cash/order系列が混入する
```

leakage audit が ERROR の場合、学習・推論に進まない。

---

# 14. 利用禁止feature

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

# 15. Phase4-Cで実装していないこと

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

# 16. Phase4-C完了判定

Phase4-Cは完了可能である。

理由:

```text
feature builder responsibility が明記されている
input source が明記されている
output schema が明記されている
feature category が明記されている
daily_quotes_normalized が中心入力として明記されている
as_of_date / lookback rule が明記されている
fins_summary publication date rule が明記されている
market index / sector aggregation rule が明記されている
missing value rule が明記されている
universe filter rule が明記されている
feature_version rule が明記されている
runtime output path が明記されている
manifest/audit integration が明記されている
leakage audit rule が明記されている
mock fixture design が明記されている
実装本体には進んでいない
```

---

# 17. Phase4-D案

次に進むべきPhase4-D:

```text
Candidate Feature Builder Skeleton / Schema Contracts
```

Phase4-Dで決めること:

```text
feature schema dataclassまたはcontract
manifest schema
audit schema
runtime path helper
mock fixture
leakage auditの最小コード
feature builder本体に入る前のschema validation
```
