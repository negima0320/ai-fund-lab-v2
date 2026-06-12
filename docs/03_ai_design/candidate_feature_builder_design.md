# AI Fund Lab vNext Candidate Feature Builder Design

---

# 1. このドキュメントの目的

本ドキュメントは、Phase4-C Candidate Feature Builder Design として、Candidate AI向けfeature生成仕様、保存仕様、監査仕様を定義する。

Phase4-Cでは設計のみを行う。feature builder本体、dataset builder本体、label生成本体、Candidate AI本体、学習処理、推論処理、バックテスト、Historical Evaluation、Paper Trading、Order Manager、Broker実API接続、発注、売買、Portfolio自動更新は実装しない。

---

# 2. Feature Builder Responsibility

Candidate Feature Builder の責務は以下である。

```text
as_of_date時点で観測可能な市場データだけを使い、
Candidate AIが候補抽出に使うfeature tableを生成するための仕様を提供する
```

Feature Builder がやること:

```text
daily_quotes_normalized を中心に価格・出来高featureを作る
listed issue master からuniverse eligibilityを作る
trading calendar で営業日windowを揃える
fins_summary を公開日ベースでas_of_date以前に限定して使う
market index data からmarket regime featureを作る
sector aggregation data からsector relative featureを作る
missing_flags と excluded_reason を付与できる設計にする
feature_version と source_snapshot_id を付与する
manifest と audit に生成証跡を残す
```

Feature Builder がやらないこと:

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
label生成
AI学習
AI推論
backtest
```

---

# 3. Candidate AIの責務境界

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

# 4. Input Source

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

入力ごとの役割:

| input source | role | leakage note |
| --- | --- | --- |
| daily_quotes_normalized | price / volume / volatility / trend feature の正規入力 | as_of_date以前の営業日だけを使う |
| listed issue master | universe eligibility, market segment, sector mapping | as_of_date時点で有効な情報だけを使う |
| trading calendar | 営業日window, 非営業日skip | future営業日情報はcalendar用途に限定し、価格featureには使わない |
| fins_summary | quality / fundamental freshness feature | disclosed_dateまたはequivalentな公開日がas_of_date以前のものだけを使う |
| market index data | market regime feature | as_of_date以前の指数だけを使う |
| sector aggregation data | sector relative feature | as_of_date以前に作られた集計だけを使う |

---

# 5. Output Schema

Candidate feature table は、Candidate AIが観測可能なfeatureだけを保持する。

主キー:

```text
as_of_date
target_date
code
feature_version
```

必須列:

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

代表列:

```text
price_momentum_return_5d
price_momentum_return_20d
price_momentum_return_60d
trend_ma_5_20_ratio
trend_ma_20_60_ratio
trend_close_to_20d_high
trend_close_to_60d_high
trend_new_20d_high_flag
trend_new_60d_high_flag
trend_breakout_strength
volatility_20d
volume_momentum_ratio_5d_20d
volume_momentum_ratio_1d_20d
volume_momentum_surge_flag
volume_momentum_trend_20d
relative_strength_stock_vs_market_20d
market_regime_topix_return_5d
market_regime_topix_return_20d
market_regime_topix_ma_5_20_ratio
market_regime_label
sector_relative_return_20d
sector_relative_rank_20d
sector_relative_stock_vs_sector_return_20d
sector_relative_momentum_flag
fundamental_sales_growth_rate
fundamental_operating_profit_growth_rate
fundamental_roe
fundamental_equity_ratio
fundamental_operating_margin
fundamental_disclosed_days_ago
fundamental_freshness_flag
liquidity_avg_volume_20d
liquidity_avg_turnover_20d
liquidity_low_liquidity_flag
universe_eligibility_listed_flag
universe_eligibility_supervision_flag
universe_eligibility_delisting_risk_flag
universe_eligibility_insufficient_history_flag
missing_flags_price
missing_flags_volume
missing_flags_fundamental
missing_flags_market
missing_flags_sector
```

出力に含めない列:

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

# 6. Feature Category

Phase4-Cでは、Candidate Feature Catalogと整合する形で以下のfeatureカテゴリを使う。

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

対応関係:

| Phase4-C category | Catalog category |
| --- | --- |
| price momentum features | Price Momentum |
| volume momentum features | Volume Momentum |
| volatility features | Price Momentum / Exclusion Risk |
| trend features | Price Momentum |
| relative strength features | Market Environment / Sector Relative Strength |
| market regime features | Market Environment |
| sector relative features | Sector Relative Strength |
| fundamental freshness features | Quality |
| liquidity features | Liquidity / Tradability |
| universe eligibility features | Exclusion / Risk Filter |

---

# 7. as_of_date / lookback rule

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
非営業日はlookback営業日に数えない
必要windowに満たない場合はmissing_flagsとexcluded_reasonに記録する
```

基本window:

```text
5営業日
10営業日
20営業日
60営業日
```

日次確定後に生成する場合:

```text
as_of_date = target_date を許可する
ただし当日OHLCVは日次確定済み daily_quotes_normalized のみ使う
```

---

# 8. fins_summary publication date rule

`fins_summary` は未来リークが起きやすい。

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

または、実データで `disclosed_date` と同等の公開日項目が別名の場合:

```text
equivalent_publication_date <= as_of_date
```

禁止:

```text
決算期末日だけでas_of_dateに結合する
公表日前のfins_summaryを使う
将来の修正後データで過去featureを上書きする
```

公表日が不明な場合:

```text
fundamental_missing_flag = true
fundamental_freshness_flag = unknown
必要なら excluded_reason = fundamental_publication_date_missing
```

---

# 9. Market Index Feature Rule

market index feature は、市場全体の地合いを表す補助featureである。

候補:

```text
market_regime_topix_return_5d
market_regime_topix_return_20d
market_regime_topix_ma_5_20_ratio
market_regime_label
market_regime_risk_flag
```

ルール:

```text
as_of_date以前のmarket index dataのみ使用
target_date以降の指数を使わない
market regimeは候補抽出の補助であり、売買停止判断ではない
市場指数欠損時はmissing_flags_marketに記録する
```

---

# 10. Sector Aggregation Rule

sector aggregation は、銘柄の相対的な強さを測るために使う。

候補:

```text
sector_relative_return_20d
sector_relative_rank_20d
sector_relative_stock_vs_sector_return_20d
sector_relative_momentum_flag
```

ルール:

```text
sector aggregation data はas_of_date以前に生成されたものだけ使う
sector aggregation の元データもas_of_date以前に限定する
listed issue master のsector mappingはas_of_date時点で有効なものだけ使う
sector不明ならmissing_flags_sectorに記録する
sectorだけで候補化しない
```

---

# 11. Missing Value Rule

欠損値は隠さず、featureと監査に残す。

基本方針:

```text
必要最小window不足はexcluded_reason
一部欠損はmissing_flagsに記録
欠損補完は明示的にfeature_versionへ反映
raw v1から直接補完しない
補完方法を変更したらfeature_versionを上げる
```

欠損時の例:

| condition | handling |
| --- | --- |
| daily_quotes_normalized がない | universe_eligible=false, excluded_reason=price_data_missing |
| 20営業日未満 | missing_flags_price=true, excluded_reason=insufficient_history |
| 出来高欠損 | missing_flags_volume=true |
| fins_summary欠損 | missing_flags_fundamental=true, neutral or unknown |
| disclosed_date欠損 | missing_flags_fundamental=true, excluded_reason=fundamental_publication_date_missing |
| market index欠損 | missing_flags_market=true, market_regime_label=unknown |
| sector不明 | missing_flags_sector=true |

---

# 12. Universe Filter Rule

universe filter は候補抽出のための前処理であり、買い判断ではない。

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

出力:

```text
universe_eligible
excluded_reason
universe_eligibility_*
missing_flags_*
```

注意:

```text
除外は候補抽出のための前処理であり、買い判断ではない
universe_eligible=false は発注禁止や売却判断を意味しない
```

---

# 13. Feature Version Rule

`feature_version` は、feature定義、window、threshold、欠損補完、source schemaが変わった場合に更新する。

versionを上げる条件:

```text
feature列の追加・削除
計算式の変更
lookback windowの変更
thresholdの変更
欠損補完方針の変更
fins_summary公開日ルールの変更
sector aggregation定義の変更
market regime定義の変更
入力source schemaの変更
```

manifestには以下を記録する。

```text
feature_version
feature_set_name
target_date
as_of_date
source_snapshot_id
input_sources
row_count
universe_eligible_count
excluded_count
created_at
leakage_audit_status
```

---

# 14. Runtime Output Path

既存のRuntime集約方針に合わせ、実生成物はruntime dir配下に集約する。

設計上の保存先:

```text
.runtime/candidate_ai/features/
.runtime/candidate_ai/manifests/
.runtime/candidate_ai/audit/
.runtime/candidate_ai/reports/
.runtime/candidate_ai/tmp/
```

保存対象:

| path | content |
| --- | --- |
| `.runtime/candidate_ai/features/` | candidate feature table |
| `.runtime/candidate_ai/manifests/` | feature generation manifest |
| `.runtime/candidate_ai/audit/` | leakage audit result |
| `.runtime/candidate_ai/reports/` | feature quality report |
| `.runtime/candidate_ai/tmp/` | 一時ファイル |

トップレベルの `reports/candidate_ai/` は実生成物保存先にしない。フェーズ監査レポートだけ既存形式に合わせて `docs/phase_reports/` と `reports/phase_reports/` に保存する。

---

# 15. Manifest / Audit Integration

Feature Builder は、feature table本体だけでなくmanifestとauditを必ず生成する設計にする。

manifest項目:

```text
manifest_id
feature_version
feature_set_name
target_date
as_of_date
input_sources
source_snapshot_id
row_count
universe_eligible_count
excluded_count
missing_flag_counts
created_at
output_path
audit_path
```

audit項目:

```text
audit_id
target_date
as_of_date
feature_version
leakage_audit_status
leakage_audit_messages
forbidden_feature_detected
future_column_detected
publication_date_violation_detected
post_target_data_detected
runtime_path_check_status
created_at
```

---

# 16. Leakage Audit Rule

leakage audit は、feature生成前後で実施する。

検出対象:

```text
feature列名にfuture/top_decile/downside/label/pnl/profit/loss等が含まれる
feature生成にas_of_dateより後のデータが使われる
fins_summaryが公開日前に結合される
target_date以降のデータがfeatureに混入する
backtest/trade/portfolio/cash/order系列が混入する
```

禁止feature:

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

ERROR条件:

```text
forbidden feature column detected
as_of_dateより後の入力データを参照
fins_summary disclosed_date > as_of_date
target_date以降の価格・出来高を参照
backtest/trade/portfolio/cash/order系列の混入
runtime外へのfeature出力
```

leakage audit が ERROR の場合、学習・推論に進まない。

---

# 17. Mock Fixture Design

Phase4-Cではmock fixtureの設計のみを行う。

fixtureカテゴリ:

```text
daily_quotes_normalized fixture
listed issue master fixture
trading calendar fixture
fins_summary fixture
market index fixture
sector aggregation fixture
expected feature rows fixture
expected manifest fixture
expected leakage audit fixture
```

fixture必須ケース:

```text
正常な20営業日window
60営業日window不足
daily_quotes_normalized欠損
出来高欠損
fins_summary disclosed_date <= as_of_date
fins_summary disclosed_date > as_of_date
sector不明
market index欠損
低流動性
監理・整理銘柄
forbidden feature列混入
runtime外出力
```

fixtureに実口座情報、broker情報、portfolio情報、trade result、backtest resultは含めない。

---

# 18. Phase4-C完了条件

Phase4-Cは以下を満たせば完了とする。

```text
feature builder responsibility が明記されている
input source が明記されている
output schema が明記されている
feature category が明記されている
daily_quotes_normalized が中心入力として明記されている
as_of_date以前のデータのみを使うことが明記されている
lookback window が過去方向のみであることが明記されている
fins_summary の公開日ベース結合ルールが明記されている
market index / sector aggregation の扱いが明記されている
missing value rule が明記されている
universe filter rule が明記されている
feature_version rule が明記されている
runtime output path が明記されている
manifest/audit integration が明記されている
leakage audit rule が明記されている
mock fixture design が明記されている
禁止feature一覧が明記されている
feature builder本体、学習、推論、backtest、Paper Trading、発注をまだ実装していない
```

---

# 19. Phase4-Dへの引き継ぎ

Phase4-D案:

```text
Candidate Feature Builder Skeleton / Schema Contracts
```

Phase4-Dで検討すること:

```text
feature schema dataclassまたはcontract
manifest schema
audit schema
runtime path helper
mock fixture
leakage auditの最小コード
feature builder本体に入る前のschema validation
```

Phase4-Dでも、AI学習、推論、backtest、Paper Trading、発注はまだ実装しない。
