# Phase5-C Opportunity Feature Design / Expansion

作成日: 2026-06-14

## 1. 目的

この資料は、Phase5 Opportunity AI が `expected_edge_label_20d` を推定し、Candidate Top50 から Opportunity Top5 / Top10 / Top20 を順位付けするための feature 設計を定義する。

Phase5-C では「どの feature を使うか」だけを設計する。feature 生成、dataset 生成、学習、推論、backtest、Paper Trading、Broker API、発注、資金配分は行わない。

最重要方針:

```text
AI Fund Lab vNext の学習データソースは J-Quants API のみ。
Opportunity AI の feature は J-Quants API から取得可能なデータ、または J-Quants データから算出可能な派生 feature のみを利用する。
```

例外として、Phase4 Candidate AI の当該 `target_date` における Candidate Top50 推論出力のうち、以下だけを Opportunity AI の入力として許可する。

```text
candidate_score
candidate_rank
candidate_reason
```

これらは Candidate Top50 を順位付けするための上流 prior / 説明補助であり、売買結果、過去のAI判断結果、Candidate評価結果、Opportunity出力結果ではない。

## 2. Feature 設計の責務境界

Opportunity feature がやること:

```text
Candidate Top50 内で期待値を比較するための観測可能情報を定義する
J-Quants daily quotes 由来の価格・出来高・トレンド・ボラティリティ・流動性 feature を定義する
J-Quants fins 由来の fundamental feature を定義する
Candidate AI の candidate_score / candidate_rank / candidate_reason の扱いを定義する
as_of_date 時点で観測可能な feature に限定する
```

Opportunity feature がやらないこと:

```text
future label を feature にしない
backtest 結果を feature にしない
売買履歴由来 feature を使わない
Portfolio 由来 feature を使わない
Paper Trading 結果を使わない
実運用結果を使わない
過去のAI判断結果を使わない
Opportunity 出力結果を使わない
Candidate 評価結果を使わない
```

## 3. 利用可能データソース

正式に許可するデータソース:

```text
J-Quants daily quotes
  Date
  Code
  Open
  High
  Low
  Close
  Volume
  AdjustmentFactor / adjustment related fields if available

J-Quants listed issue master
  Code
  market segment
  sector / industry classification
  listed status fields available as_of_date

J-Quants fins / statements / announcement data
  sales
  operating profit
  ordinary profit
  net income
  equity
  total assets
  disclosed forecasts / revisions if available
  disclosure_date

J-Quants index / market data if available
  TOPIX
  market index OHLCV
  sector / industry index or sector aggregation derivable from listed issue master and daily quotes
```

J-Quants データから算出可能な派生 feature:

```text
returns
moving averages
volume moving averages
volume ratios
trend ratios
volatility
range
liquidity / trading value
sector relative strength
market trend
fundamental growth rates
profitability ratios
financial soundness ratios
```

## 4. Opportunity Feature Schema

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
feature_set_name
source_data_start_date
source_data_end_date
candidate_inference_run_id
candidate_model_version
candidate_feature_version
created_at
```

feature categories:

```text
candidate_features
price_features
volume_features
momentum_features
trend_features
volatility_features
liquidity_features
fundamental_features
market_environment_features
sector_strength_features
data_quality_features
```

Phase5-D join key:

```text
target_date
code
```

Phase5-D では、この feature table を Phase5-B label table と `target_date + code` で結合する。ただし推論時には label table を読まない。

## 5. Candidate AI 由来 Feature

利用可能:

```text
candidate_score
candidate_rank
candidate_reason
```

### 5.1 candidate_score

定義:

```text
Phase4 Candidate AI が target_date に出した候補抽出スコア
```

扱い:

```text
expected_edge_score の prior として使える
buy_rank に直結させない
candidate_score だけで Opportunity TopN を決めない
score が高いほど安全とは仮定しない
```

禁止:

```text
Candidate AI の future label を参照しない
Candidate quality audit 結果を feature にしない
CandidateTop50 の実後日成績を feature にしない
過去 target_date の AI 判断結果を累積 feature にしない
```

### 5.2 candidate_rank

定義:

```text
Phase4 Candidate AI が target_date に出した Candidate Top50 内順位
```

扱い:

```text
上流候補抽出の強さを表す補助 feature
buy_rank に直結させない
candidate_score と同様に prior として扱う
```

### 5.3 candidate_reason

定義:

```text
Phase4 Candidate AI が target_date に付与した候補理由
```

扱い:

```text
J-Quants由来 feature に基づく理由だけを許可する
必要に応じて reason flag / reason category に encode する
```

禁止:

```text
future label 由来の reason
backtest 結果由来の reason
売買結果由来の reason
Opportunity 出力由来の reason
```

## 6. Price Feature

すべて J-Quants daily quotes から算出する。

| feature_name | 定義 | 使用データ | as_of_date ルール |
| --- | --- | --- | --- |
| close | `Close_t` | daily quotes | `t <= as_of_date` |
| high | `High_t` | daily quotes | `t <= as_of_date` |
| low | `Low_t` | daily quotes | `t <= as_of_date` |
| open | `Open_t` | daily quotes | `t <= as_of_date` |
| return_1d | `Close_t / Close_{t-1} - 1` | daily quotes | `t` 以前のみ |
| return_5d | `Close_t / Close_{t-5} - 1` | daily quotes | `t` 以前のみ |
| return_20d | `Close_t / Close_{t-20} - 1` | daily quotes | `t` 以前のみ |
| return_60d | `Close_t / Close_{t-60} - 1` | daily quotes | `t` 以前のみ |
| close_to_20d_high | `Close_t / max(High_{t-19..t}) - 1` | daily quotes | `t` 以前のみ |
| close_to_60d_high | `Close_t / max(High_{t-59..t}) - 1` | daily quotes | `t` 以前のみ |

注意:

```text
future_return_20d とは別物。
return_20d は target_date 以前の過去20営業日 return。
future_return_20d は Phase5-B label であり feature にはしない。
```

## 7. Volume Feature

すべて J-Quants daily quotes の `Volume` から算出する。

| feature_name | 定義 | 使用データ | as_of_date ルール |
| --- | --- | --- | --- |
| volume | `Volume_t` | daily quotes | `t <= as_of_date` |
| volume_ma_5 | `MA(Volume, 5)` | daily quotes | `t` 以前のみ |
| volume_ma_20 | `MA(Volume, 20)` | daily quotes | `t` 以前のみ |
| volume_ma_60 | `MA(Volume, 60)` | daily quotes | `t` 以前のみ |
| volume_ratio_5d | `volume_ma_5 / volume_ma_20` | daily quotes | `t` 以前のみ |
| volume_ratio_20d | `Volume_t / volume_ma_20` | daily quotes | `t` 以前のみ |
| volume_ratio_1d_20d | `Volume_t / MA(Volume,20)` | daily quotes | `t` 以前のみ |
| volume_trend_20d | `MA(Volume,10) / MA(Volume,20) - 1` | daily quotes | `t` 以前のみ |

扱い:

```text
volume surge は単純加点しない
過熱・材料一巡リスクの可能性もあるため、momentum / trend / volatility と併せて評価する
```

## 8. Momentum Feature

価格・出来高の持続性を J-Quants daily quotes から算出する。

| feature_name | 定義 | 使用データ | as_of_date ルール |
| --- | --- | --- | --- |
| momentum_return_5d | `return_5d` | daily quotes | `t` 以前のみ |
| momentum_return_20d | `return_20d` | daily quotes | `t` 以前のみ |
| momentum_return_60d | `return_60d` | daily quotes | `t` 以前のみ |
| momentum_consistency_5_20 | `sign(return_5d) == sign(return_20d)` 等 | daily quotes | `t` 以前のみ |
| momentum_consistency_20_60 | `sign(return_20d) == sign(return_60d)` 等 | daily quotes | `t` 以前のみ |
| short_term_overheat_5d_20d | `return_5d - return_20d` | daily quotes | `t` 以前のみ |
| volume_price_confirm_20d | `return_20d` と `volume_ratio_5d` の組み合わせ | daily quotes | `t` 以前のみ |

目的:

```text
future_max_return_20d 型の上昇余地を推定する
一時的な急騰だけではなく、複数 horizon の方向性を確認する
```

## 9. Trend Feature

移動平均と終値の関係を J-Quants daily quotes から算出する。

| feature_name | 定義 | 使用データ | as_of_date ルール |
| --- | --- | --- | --- |
| ma_5 | `MA(Close,5)` | daily quotes | `t` 以前のみ |
| ma_20 | `MA(Close,20)` | daily quotes | `t` 以前のみ |
| ma_60 | `MA(Close,60)` | daily quotes | `t` 以前のみ |
| close_over_ma20 | `Close_t / ma_20 - 1` | daily quotes | `t` 以前のみ |
| close_over_ma60 | `Close_t / ma_60 - 1` | daily quotes | `t` 以前のみ |
| ma5_over_ma20 | `ma_5 / ma_20 - 1` | daily quotes | `t` 以前のみ |
| ma20_over_ma60 | `ma_20 / ma_60 - 1` | daily quotes | `t` 以前のみ |
| trend_alignment_score | `close_over_ma20`, `close_over_ma60`, `ma5_over_ma20`, `ma20_over_ma60` の合成 | daily quotes | `t` 以前のみ |

目的:

```text
上昇基調の確認
expected_edge_label_20d の高い候補を推定する
```

## 10. Volatility Feature

価格変動リスクを J-Quants daily quotes から算出する。

| feature_name | 定義 | 使用データ | as_of_date ルール |
| --- | --- | --- | --- |
| return_std_20d | `std(daily_return,20)` | daily quotes | `t` 以前のみ |
| return_std_60d | `std(daily_return,60)` | daily quotes | `t` 以前のみ |
| high_low_range | `High_t / Low_t - 1` | daily quotes | `t <= as_of_date` |
| avg_high_low_range_20d | `MA(High / Low - 1,20)` | daily quotes | `t` 以前のみ |
| downside_volatility_20d | `std(min(daily_return,0),20)` | daily quotes | `t` 以前のみ |
| abnormal_price_move_flag | `abs(return_1d)` が閾値超過 | daily quotes | `t` 以前のみ |

目的:

```text
downside_risk_score の推定材料
過熱・荒さ・ドローダウン proxy の推定
```

禁止:

```text
future_max_drawdown_20d を volatility feature として使わない
```

## 11. Liquidity Feature

売買可能性を J-Quants daily quotes から算出する。

| feature_name | 定義 | 使用データ | as_of_date ルール |
| --- | --- | --- | --- |
| avg_volume_20d | `MA(Volume,20)` | daily quotes | `t` 以前のみ |
| avg_volume_60d | `MA(Volume,60)` | daily quotes | `t` 以前のみ |
| avg_trading_value_20d | `MA(Close * Volume,20)` | daily quotes | `t` 以前のみ |
| avg_trading_value_60d | `MA(Close * Volume,60)` | daily quotes | `t` 以前のみ |
| trading_value | `Close_t * Volume_t` | daily quotes | `t <= as_of_date` |
| low_liquidity_flag | `avg_trading_value_20d` または `avg_volume_20d` が閾値未満 | daily quotes | `t` 以前のみ |

目的:

```text
実運用可能性の確認
極端な低流動性候補のリスク評価
```

注意:

```text
資金配分や購入株数は Phase5 では決めない
liquidity feature は Opportunity ranking の期待値・リスク評価に限定して使う
```

## 12. Fundamental Feature

J-Quants で取得可能な財務情報からのみ算出する。

必須ルール:

```text
disclosure_date <= as_of_date
```

| feature_name | 定義 | 使用データ | as_of_date ルール |
| --- | --- | --- | --- |
| sales_growth_rate | `(当期売上 - 前年同期売上) / 前年同期売上` | J-Quants fins | `disclosure_date <= as_of_date` |
| operating_profit_growth_rate | `(当期営業利益 - 前年同期営業利益) / abs(前年同期営業利益)` | J-Quants fins | `disclosure_date <= as_of_date` |
| ordinary_profit_growth_rate | `(当期経常利益 - 前年同期経常利益) / abs(前年同期経常利益)` | J-Quants fins | `disclosure_date <= as_of_date` |
| net_income_growth_rate | `(当期純利益 - 前年同期純利益) / abs(前年同期純利益)` | J-Quants fins | `disclosure_date <= as_of_date` |
| roe | `純利益 / 自己資本` | J-Quants fins | `disclosure_date <= as_of_date` |
| equity_ratio | `自己資本 / 総資産` | J-Quants fins | `disclosure_date <= as_of_date` |
| operating_margin | `営業利益 / 売上高` | J-Quants fins | `disclosure_date <= as_of_date` |

欠損時:

```text
財務情報が未公表なら missing または neutral とする
未来の開示値で補完しない
決算発表日以前にその決算値を使わない
```

## 13. Market / Sector Feature

J-Quants から取得可能な市場指数、または J-Quants daily quotes と listed issue master から算出可能な集計のみを使う。

| feature_name | 定義 | 使用データ | as_of_date ルール |
| --- | --- | --- | --- |
| topix_return_5d | `TOPIX_t / TOPIX_{t-5} - 1` | J-Quants index data | `t` 以前のみ |
| topix_return_20d | `TOPIX_t / TOPIX_{t-20} - 1` | J-Quants index data | `t` 以前のみ |
| topix_return_60d | `TOPIX_t / TOPIX_{t-60} - 1` | J-Quants index data | `t` 以前のみ |
| topix_ma5_over_ma20 | `MA(TOPIX,5) / MA(TOPIX,20) - 1` | J-Quants index data | `t` 以前のみ |
| topix_volatility_20d | `std(TOPIX daily_return,20)` | J-Quants index data | `t` 以前のみ |
| market_trend_regime | TOPIX return / MA / volatility による as-of-date 分類 | J-Quants index data | `t` 以前のみ |
| sector_return_20d | 同一 sector の20d return 集計 | daily quotes + listed issue master | `t` 以前のみ |
| sector_rank_20d | sector_return_20d の横断順位 | daily quotes + listed issue master | `t` 以前のみ |
| stock_vs_sector_return_20d | `return_20d - sector_return_20d` | daily quotes + sector aggregation | `t` 以前のみ |

禁止:

```text
評価後にしか分からない regime label
future return で分類した up / flat / down
post-selection return による市場環境 label
```

## 14. Data Quality Feature

J-Quants データの観測可能性だけを示す補助 feature。

| feature_name | 定義 | 使用データ | as_of_date ルール |
| --- | --- | --- | --- |
| insufficient_history_flag | 必要 window 日数に満たない | daily quotes | `t` 以前のみ |
| missing_price_flag | target_date の価格欠損 | daily quotes | `t <= as_of_date` |
| missing_volume_flag | target_date の出来高欠損 | daily quotes | `t <= as_of_date` |
| missing_fundamental_flag | `as_of_date` 時点で財務情報がない | J-Quants fins | `disclosure_date <= as_of_date` |
| market_unknown_flag | 市場指数 feature が欠損 | J-Quants index | `t` 以前のみ |

目的:

```text
欠損や履歴不足を model が識別できるようにする
未来データ補完を避ける
```

## 15. Feature 禁止事項

feature として利用禁止:

```text
future_return_*
future_max_return_*
future_max_drawdown_*
downside_bad_*
top_decile_*
expected_edge_label_*
risk_adjusted_future_return_*
opportunity_rank_label_*
```

売買・運用・評価由来で利用禁止:

```text
バックテスト結果
trade_result
trade_profit
selected
bought
sold
cash
portfolio
annual_return
final_assets
PM倍率
売買履歴由来feature
過去のAI判断結果
Opportunity出力結果
Candidate評価結果
Paper Trading結果
実運用結果
```

禁止理由:

```text
J-Quants API 由来ではない
推論時点で観測不能
売買結果や評価結果を学習 feature に混入させると leakage になる
Opportunity AI の責務を超える
```

## 16. as_of_date ルール

全 feature 共通ルール:

```text
feature は target_date 時点で観測可能であること
as_of_date <= target_date
target_date の日次確定後処理では as_of_date = target_date を許可する
target_date より後の価格・出来高・高値・安値を使わない
target_date より後に公表された財務情報を使わない
future 情報を参照しない
```

価格・出来高:

```text
daily quotes の target_date 以前だけを使う
lookback window は過去営業日だけを含める
future window を feature 計算に使わない
```

財務:

```text
disclosure_date <= as_of_date
公表前の財務値を使わない
将来の訂正・実績値で過去 feature を上書きしない
```

市場・セクター:

```text
TOPIX / market index は as_of_date 以前のみ
sector aggregation は as_of_date 以前の銘柄情報と価格だけで作る
future return に基づく regime を使わない
```

## 17. Feature Audit

必須 audit:

```text
feature_row_count
candidate_top50_row_count
feature_coverage_rate
forbidden_feature_column_count
future_column_in_feature_count
trade_result_column_in_feature_count
backtest_column_in_feature_count
ai_output_column_in_feature_count
paper_trading_column_in_feature_count
portfolio_column_in_feature_count
as_of_date_violation_count
missing_feature_rate
nan_rate
inf_rate
duplicate_target_date_code_count
candidate_feature_join_missing_count
fundamental_disclosure_date_violation_count
market_feature_as_of_violation_count
```

禁止列検査 pattern:

```text
future_return_
future_max_return_
future_max_drawdown_
downside_bad_
top_decile_
expected_edge_label_
risk_adjusted_future_return_
trade_result
trade_profit
selected
bought
sold
cash
portfolio
annual_return
final_assets
backtest
paper_trading
pm_multiplier
opportunity_output
candidate_evaluation
```

監査ステータス候補:

```text
OK
WARNING_MISSING_FEATURE_HIGH
WARNING_NAN_RATE_HIGH
FAIL_FORBIDDEN_FEATURE_COLUMN
FAIL_FUTURE_LEAKAGE_RISK
FAIL_TRADE_RESULT_LEAKAGE_RISK
FAIL_BACKTEST_LEAKAGE_RISK
FAIL_AI_OUTPUT_LEAKAGE_RISK
FAIL_AS_OF_DATE_VIOLATION
FAIL_DUPLICATE_KEY
```

## 18. Phase5-D への引き継ぎ

Phase5-D に渡す feature schema:

```text
target_date
as_of_date
code
feature_version
feature_set_name
source_data_start_date
source_data_end_date
candidate_inference_run_id
candidate_model_version
candidate_feature_version
candidate_score
candidate_rank
candidate_reason_features
price_features
volume_features
momentum_features
trend_features
volatility_features
liquidity_features
fundamental_features
market_environment_features
sector_strength_features
data_quality_features
created_at
```

join key:

```text
target_date
code
```

feature version:

```text
opportunity_feature_v1
```

Phase5-D dataset builder の前提:

```text
Candidate Top50 list と Opportunity feature table は target_date + code で結合する
Opportunity feature table と Phase5-B label table も target_date + code で結合する
training dataset 作成時は feature columns と label columns を明示的に分離する
inference dataset では label table を読まない
Phase4 成果物を上書きしない
mock path を上書きしない
```

## 19. Phase5-C 結論

Phase5-C では、Opportunity AI の feature を J-Quants API から取得可能なデータ、または J-Quants データから算出可能な派生 feature に限定して設計した。

許可する feature は、Candidate Top50 推論出力の `candidate_score / candidate_rank / candidate_reason` と、J-Quants 由来の price、volume、momentum、trend、volatility、liquidity、fundamental、market / sector、data quality feature である。

future 系 label、backtest 結果、売買結果、Portfolio、PM倍率、過去のAI判断結果、Opportunity出力結果、Candidate評価結果、Paper Trading結果、実運用結果は feature として使わない。

この資料により、Phase5-D Candidate Top50 to Opportunity Dataset Builder の設計へ進める状態になった。
