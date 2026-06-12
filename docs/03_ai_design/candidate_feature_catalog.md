# Candidate Feature Catalog

---

# 1. このドキュメントの目的

このドキュメントは、AI Fund Lab vNext の Candidate AI が利用する特徴量候補を定義する。

Phase2-A では先行設計として特徴量候補を整理した。Phase4-A では正式ロードマップ上の `Candidate AI vNext` 開始に合わせて、このcatalogをCandidate AI設計の参照資料として再確認する。

Phase4-A では設計のみを行う。特徴量実装、学習データ生成、future label 生成、AI 学習、推論処理、backtest、paper trading、broker 連携、注文機能は行わない。

目的は、Phase4-B 以降の Training Data Design に進む前に、Candidate AI が何を観測し、何を観測してはいけないかを固定することである。

---

# 2. Candidate AIの責務確認

Candidate AI の責務は、全銘柄から「見る価値がある銘柄」を抽出することである。

```text
4000銘柄
↓
50銘柄程度
```

Candidate AI は「上昇候補発見」を担当する。市場が評価し始めた銘柄、価格と出来高に上昇開始の兆候がある銘柄、かつ最低限の企業品質と売買可能性を持つ銘柄を候補として残す。

Candidate AI がしないこと:

```text
何を買うか決めない
期待値ランキングを作らない
利益予測をしない
保有判断をしない
売却判断をしない
購入株数を決めない
```

Opportunity AI との境界:

```text
Candidate AI:
  見る価値がある銘柄を抽出する

Opportunity AI:
  候補の中から期待値を評価し、買い順位を決める
```

Candidate AI の出力は `candidate_list`, `candidate_score`, `candidate_reason`, `excluded_reason` までに留める。`candidate_score` は候補抽出の強さであり、利益予測や買い順位ではない。

---

# 3. 利用可能データ

Phase4-A で想定する利用可能データは以下である。

```text
J-Quants daily quotes normalized raw
  Date
  Code
  Open
  High
  Low
  Close
  Volume
  PriceSource
  SchemaVersion

J-Quants listed issue master
  Code
  銘柄名
  市場区分
  業種区分
  上場状態に関する情報

J-Quants trading calendar
  営業日
  非営業日

J-Quants fins summary
  売上
  営業利益
  経常利益
  純利益
  自己資本
  ROE算出に必要な財務項目
  業績予想修正に関する項目

市場指数データ
  TOPIX等の市場環境指標

業種・セクター集計データ
  同一業種内の相対モメンタム
```

daily quotes は Phase1で作成した `daily_quotes_normalized` を読む。raw v1 は原本証跡として残すが、Candidate AI の特徴量入力には原則として normalized raw を使う。

---

# 4. 利用禁止データ

以下は Candidate AI の feature として使わない。

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
```

禁止対象は、feature としての利用、推論時の参照、候補抽出ロジックへの混入である。future 系は学習・評価ラベルとして別設計で扱う可能性はあるが、Candidate AI の入力 feature には含めない。

---

# 5. Featureカテゴリ一覧

| category | 目的 | Candidate AIでの役割 |
| --- | --- | --- |
| Quality | 良い企業を候補に残す | 単なる価格急騰ではなく、企業品質を伴う上昇候補を優先する |
| Price Momentum | 上昇開始を検知する | 価格が短中期で強くなり始めた銘柄を見つける |
| Volume Momentum | 市場の気付き始めを検知する | 出来高増加で関心の高まりを捉える |
| Liquidity / Tradability | 売買可能性を確認する | 低流動性や実運用困難銘柄を除外する |
| Market Environment | 地合いを把握する | 市場全体の追い風・逆風を候補抽出に反映する |
| Sector Relative Strength | 業種内の強さを確認する | 強いセクター内で相対的に強い銘柄を残す |
| Exclusion / Risk Filter | 明確な対象外を除外する | 監理・整理、異常値、履歴不足などを候補外にする |

---

# 6. Feature定義詳細

各 feature は以下の項目を持つ。

```text
feature_name
category
定義
計算方法
使用データ
利用目的
Candidate AIで使う理由
leakage確認
欠損時の扱い
注意点
```

## 6.1 Quality

| feature_name | category | 定義 | 計算方法 | 使用データ | 利用目的 | Candidate AIで使う理由 | leakage確認 | 欠損時の扱い | 注意点 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sales_growth_rate | Quality | 売上成長率 | `(当期売上 - 前年同期売上) / 前年同期売上` | fins summary | 成長企業を識別する | 市場が評価し始める前提として売上成長を見る | target date 時点で公表済みの財務情報のみ使う | 欠損なら neutral、連続欠損なら insufficient_fundamental_data | 決算期変更や分割開示に注意 |
| operating_profit_growth_rate | Quality | 営業利益成長率 | `(当期営業利益 - 前年同期営業利益) / abs(前年同期営業利益)` | fins summary | 本業利益の改善を見る | 価格モメンタムに企業改善が伴うか確認する | 公表日以前には使わない | 欠損なら neutral | 前年赤字から黒字化する場合は上限クリップを検討 |
| ordinary_profit_growth_rate | Quality | 経常利益成長率 | `(当期経常利益 - 前年同期経常利益) / abs(前年同期経常利益)` | fins summary | 財務・営業外含む利益改善を見る | 日本株で一般的な利益指標として候補品質を補強する | 公表済み値のみ使用 | 欠損なら neutral | 一時要因で過大になる場合がある |
| net_income_growth_rate | Quality | 純利益成長率 | `(当期純利益 - 前年同期純利益) / abs(前年同期純利益)` | fins summary | 最終利益の改善を見る | 利益改善を伴う上昇候補を残す | 公表済み値のみ使用 | 欠損なら neutral | 特別損益の影響を受ける |
| roe | Quality | 自己資本利益率 | `純利益 / 自己資本` | fins summary | 資本効率を見る | 良い企業を候補に残すための品質指標 | 公表済み財務だけで算出 | 欠損なら neutral | 自己資本が小さい場合の極端値をクリップする |
| equity_ratio | Quality | 自己資本比率 | `自己資本 / 総資産` | fins summary | 財務健全性を見る | 脆弱な財務銘柄を候補から弱める | 公表済み財務だけで算出 | 欠損なら neutral | 業種差が大きいので単独過信しない |
| operating_margin | Quality | 営業利益率 | `営業利益 / 売上高` | fins summary | 収益性を見る | 高収益企業の上昇開始を見つけやすくする | 公表済み財務だけで算出 | 欠損なら neutral | 売上が小さい銘柄は極端値になりやすい |
| earnings_revision_signal | Quality | 業績予想修正シグナル | 直近公表予想と前回予想の増減方向を符号化 | fins summary | 業績改善の新情報を捉える | 市場が評価し始めるきっかけを捉える | 修正公表日以後のみ有効化する | 欠損なら 0 | futureの実績結果ではなく、公表済み予想修正だけを使う |

## 6.2 Price Momentum

| feature_name | category | 定義 | 計算方法 | 使用データ | 利用目的 | Candidate AIで使う理由 | leakage確認 | 欠損時の扱い | 注意点 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| return_5d | Price Momentum | 5営業日リターン | `Close_t / Close_t-5 - 1` | daily_quotes_normalized | 短期上昇開始を見る | 初動の価格反応を検知する | t時点以前の終値のみ使用 | 5営業日未満なら missing | 1日急騰だけに引っ張られないよう他featureと併用 |
| return_20d | Price Momentum | 20営業日リターン | `Close_t / Close_t-20 - 1` | daily_quotes_normalized | 中期モメンタムを見る | スイングモメンタムの候補抽出に使う | t時点以前のみ | 履歴不足なら missing | 極端値はクリップ検討 |
| return_60d | Price Momentum | 60営業日リターン | `Close_t / Close_t-60 - 1` | daily_quotes_normalized | 3か月程度の基調を見る | 長めの上昇基調を確認する | t時点以前のみ | 履歴不足なら missing | すでに上がり切った銘柄を過大評価しない |
| ma_5_20_ratio | Price Momentum | 5日移動平均と20日移動平均の比率 | `MA(Close,5) / MA(Close,20) - 1` | daily_quotes_normalized | 短期トレンド転換を見る | 上昇開始を滑らかに捉える | t時点以前の価格のみ | 20営業日未満なら missing | 小型株の飛び値に注意 |
| ma_20_60_ratio | Price Momentum | 20日移動平均と60日移動平均の比率 | `MA(Close,20) / MA(Close,60) - 1` | daily_quotes_normalized | 中期トレンドを見る | 価格基調が上向きか確認する | t時点以前のみ | 60営業日未満なら missing | 遅行指標なので初動検知だけに使わない |
| close_to_20d_high | Price Momentum | 20日高値への近さ | `Close_t / max(High,t-19..t) - 1` | daily_quotes_normalized | 高値圏接近を見る | 市場が評価し始めた銘柄を拾う | 当日までのHighのみ使用 | 20営業日未満なら missing | 当日Highを使う場合は日次確定後の処理に限定 |
| close_to_60d_high | Price Momentum | 60日高値への近さ | `Close_t / max(High,t-59..t) - 1` | daily_quotes_normalized | 中期高値圏を見る | 強い銘柄を候補に残す | 当日までのHighのみ使用 | 60営業日未満なら missing | すでに過熱した銘柄に注意 |
| new_20d_high_flag | Price Momentum | 20日高値更新フラグ | `Close_t >= max(High,t-19..t)` | daily_quotes_normalized | 短期ブレイク検知 | 上昇開始のわかりやすい理由になる | t時点以前のみ | 20営業日未満なら false または missing | 終値基準か高値基準かをPhase3で固定 |
| new_60d_high_flag | Price Momentum | 60日高値更新フラグ | `Close_t >= max(High,t-59..t)` | daily_quotes_normalized | 中期ブレイク検知 | 強い上昇候補を抽出する | t時点以前のみ | 60営業日未満なら false または missing | 値幅制限や低流動性の高値に注意 |
| breakout_strength | Price Momentum | ブレイクの強さ | `(Close_t - max(High,t-20..t-1)) / ATR_20 or volatility_20d` | daily_quotes_normalized | 高値突破の強度を見る | 単なる高値更新より強いシグナルを得る | t-1までの過去高値とtの確定終値のみ | 履歴不足なら missing | 当日中リアルタイム判断には使わない |
| volatility_20d | Price Momentum | 20日ボラティリティ | `std(daily_return,20)` | daily_quotes_normalized | 価格変動リスクを見る | 異常に荒い銘柄を抑制する | t時点以前のリターンのみ | 20営業日未満なら missing | 高ボラは機会でもリスクでもあるため除外featureと併用 |

## 6.3 Volume Momentum

| feature_name | category | 定義 | 計算方法 | 使用データ | 利用目的 | Candidate AIで使う理由 | leakage確認 | 欠損時の扱い | 注意点 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| volume_ratio_5d_20d | Volume Momentum | 5日平均出来高と20日平均出来高の比率 | `MA(Volume,5) / MA(Volume,20)` | daily_quotes_normalized | 出来高増加の持続を見る | 市場の関心増加を捉える | t時点以前の出来高のみ | 20営業日未満なら missing | 分割・市場変更の影響に注意 |
| volume_ratio_1d_20d | Volume Momentum | 当日出来高と20日平均出来高の比率 | `Volume_t / MA(Volume,20)` | daily_quotes_normalized | 出来高急増を見る | 市場が気付き始めた兆候を拾う | 日次確定後の出来高のみ | 20営業日未満なら missing | 一日だけの材料株を過大評価しない |
| volume_surge_flag | Volume Momentum | 出来高急増フラグ | `volume_ratio_1d_20d >= threshold` | daily_quotes_normalized | 異常な関心増加を検知 | candidate_reason に使いやすい | t時点以前のみ | 算出不能なら false または missing | threshold はPhase3で検証する |
| volume_trend_20d | Volume Momentum | 20日出来高トレンド | 直近20日の出来高回帰傾き、または `MA(Volume,10)/MA(Volume,20)-1` | daily_quotes_normalized | 出来高増加の方向を見る | 価格上昇に伴う継続的な関心を捉える | t時点以前のみ | 20営業日未満なら missing | 低流動性銘柄では不安定 |

## 6.4 Liquidity / Tradability

| feature_name | category | 定義 | 計算方法 | 使用データ | 利用目的 | Candidate AIで使う理由 | leakage確認 | 欠損時の扱い | 注意点 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| avg_volume_20d | Liquidity / Tradability | 20日平均出来高 | `MA(Volume,20)` | daily_quotes_normalized | 売買量を見る | 運用可能な銘柄だけ残す | t時点以前のみ | 履歴不足なら missing | 株価水準と併せて見る |
| avg_turnover_20d | Liquidity / Tradability | 20日平均売買代金 | `MA(Close * Volume,20)` | daily_quotes_normalized | 売買代金を見る | 実運用で売買可能か判断する | t時点以前のみ | 履歴不足なら missing | split補正済み価格・出来高の整合性を確認 |
| low_liquidity_flag | Liquidity / Tradability | 低流動性フラグ | `avg_turnover_20d < threshold` または `avg_volume_20d < threshold` | daily_quotes_normalized | 対象外候補を検出 | 流動性不足銘柄を候補から落とす | t時点以前のみ | 算出不能なら true 寄り | threshold は実運用資金量で変わる |
| tradable_flag | Liquidity / Tradability | 売買可能フラグ | `low_liquidity_flag == false` かつ normalized raw が存在し、上場銘柄情報が有効 | daily_quotes_normalized, listed issue master | 候補対象として扱えるか確認 | Candidate AIの前段フィルタになる | t時点で入手可能な銘柄情報のみ | 不明なら false | 売買停止・監理整理は別filterでも確認 |

## 6.5 Market Environment

| feature_name | category | 定義 | 計算方法 | 使用データ | 利用目的 | Candidate AIで使う理由 | leakage確認 | 欠損時の扱い | 注意点 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| topix_return_5d | Market Environment | TOPIX 5営業日リターン | `TOPIX_Close_t / TOPIX_Close_t-5 - 1` | market index data | 短期地合いを見る | 市場全体の追い風・逆風を反映する | t時点以前の指数のみ | 欠損なら market_unknown | 個別銘柄featureと混同しない |
| topix_return_20d | Market Environment | TOPIX 20営業日リターン | `TOPIX_Close_t / TOPIX_Close_t-20 - 1` | market index data | 中期地合いを見る | モメンタムが市場全体要因か把握する | t時点以前のみ | 欠損なら market_unknown | TOPIX以外の指数候補はPhase3で検討 |
| topix_ma_5_20_ratio | Market Environment | TOPIX短期/中期移動平均比 | `MA(TOPIX,5) / MA(TOPIX,20) - 1` | market index data | 市場トレンド方向を見る | 地合い悪化時の候補抽出を抑制する | t時点以前のみ | 欠損なら market_unknown | 市場環境は候補除外ではなく補助に留める |
| market_regime | Market Environment | 市場レジーム | TOPIX return, MA ratio, volatility から `uptrend/neutral/downtrend` 等に分類 | market index data | 地合いをカテゴリ化 | 候補抽出の強弱を調整する | t時点以前のみ | 欠損なら `unknown` | regime定義は過剰最適化に注意 |
| market_risk_flag | Market Environment | 市場リスクフラグ | TOPIX急落や高ボラ条件で true | market index data | リスク地合いを検出 | 悪地合いで候補数を抑える | t時点以前のみ | 欠損なら false ではなく unknown | 売買停止判断ではない |

## 6.6 Sector Relative Strength

| feature_name | category | 定義 | 計算方法 | 使用データ | 利用目的 | Candidate AIで使う理由 | leakage確認 | 欠損時の扱い | 注意点 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sector_return_20d | Sector Relative Strength | セクター20日リターン | 同一セクター銘柄または業種指数の20日リターン | daily_quotes_normalized, listed issue master, sector index | 強い業種を把握 | 上昇し始めたテーマ・業種を捉える | t時点以前のみ | セクター不明なら missing | セクター定義を固定する |
| sector_rank_20d | Sector Relative Strength | セクターリターン順位 | 全セクターの `sector_return_20d` を順位化 | sector_return_20d | 相対的に強いセクターを見る | 強い市場テーマ内の候補を拾う | t時点以前のみ | セクター不明なら missing | 順位は同日断面内で算出 |
| stock_vs_sector_return_20d | Sector Relative Strength | 銘柄のセクター対比リターン | `stock_return_20d - sector_return_20d` | daily_quotes_normalized, sector_return_20d | セクター内での強さを見る | 業種全体ではなく銘柄固有の強さを確認 | t時点以前のみ | セクター不明なら missing | 強すぎる乖離は過熱の可能性 |
| sector_momentum_flag | Sector Relative Strength | セクターモメンタムフラグ | `sector_rank_20d` が上位、かつ `sector_return_20d > threshold` | sector_return_20d, sector_rank_20d | 強いセクターを識別 | 候補抽出理由を補強する | t時点以前のみ | 欠損なら false または unknown | セクターだけで候補化しない |

## 6.7 Exclusion / Risk Filter

| feature_name | category | 定義 | 計算方法 | 使用データ | 利用目的 | Candidate AIで使う理由 | leakage確認 | 欠損時の扱い | 注意点 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| supervision_flag | Exclusion / Risk Filter | 監理銘柄フラグ | listed issue master の状態情報から判定 | listed issue master | 明確な対象外を検出 | 投資哲学の除外候補に該当 | t時点で公表済みの状態のみ | 不明なら unknown、保守的に除外候補 | 情報項目名はPhase3で実データに合わせる |
| delisting_risk_flag | Exclusion / Risk Filter | 整理・上場廃止リスクフラグ | listed issue master の整理銘柄・上場廃止関連情報から判定 | listed issue master | 上場廃止リスクを避ける | Candidate AIの対象外理由になる | t時点で公表済みの状態のみ | 不明なら unknown、保守的に除外候補 | 噂や未来の廃止結果は使わない |
| extreme_low_price_flag | Exclusion / Risk Filter | 極端な低位株フラグ | `Close_t < threshold` | daily_quotes_normalized | 低位株リスクを検出 | 投資哲学の除外候補に該当 | t時点の終値のみ | 欠損なら true 寄り | threshold はPhase3で決める |
| abnormal_price_move_flag | Exclusion / Risk Filter | 異常値動きフラグ | `abs(return_1d)` や `volatility_20d` が上限超過 | daily_quotes_normalized | データ異常・過熱を検出 | 誤検知や仕手的な動きを抑える | t時点以前のみ | 算出不能なら unknown | 値幅制限・分割・権利落ちを考慮 |
| insufficient_history_flag | Exclusion / Risk Filter | 履歴不足フラグ | 必要window日数に満たない場合 true | daily_quotes_normalized, trading calendar | 計算不能銘柄を識別 | 不完全なfeatureで候補化しない | t時点以前の履歴のみ | true | 新規上場銘柄を完全排除するかはPhase3で検討 |

---

# 7. Leakageチェック方針

Candidate AI feature の leakage チェックは以下を必須とする。

```text
1. target_date時点で存在しない情報を使わない
2. future_return_* や future_max_* をfeatureにしない
3. backtest/trade/portfolio/order由来データを使わない
4. 財務情報は公表日以後にだけ利用する
5. 移動平均、リターン、高値更新はtarget_date以前の時系列だけで計算する
6. 当日終値・当日出来高を使う場合は日次確定後のcandidate生成に限定する
7. normalized rawから除外されたrecordをfeature入力へ混入させない
8. Phase3でfeature生成時にas_of_dateを必ず持たせる
```

学習・評価で future 系ラベルを使う場合でも、feature table と label table は物理的・論理的に分離する。

---

# 8. 欠損値・異常値方針

欠損値方針:

```text
価格・出来高feature:
  daily_quotes_normalized がない場合は missing。
  raw v1から直接補完しない。

財務feature:
  公表済み財務がない場合は neutral または missing。
  欠損そのものを品質不足として扱うかはPhase3で決める。

市場・セクターfeature:
  指数やセクターが取れない場合は unknown。

除外filter:
  監理・整理・流動性・履歴不足など安全側に倒す。
```

異常値方針:

```text
極端なreturn
極端なvolume ratio
極端な財務成長率
低すぎる価格
不自然なOHLCV
```

はクリップ、flag化、または除外候補化する。Phase2-Aではthresholdを固定しない。Phase3でtraining data designとともに決める。

Phase1-Hで確認された daily_quotes 正規化除外recordは、OHLCV/adjusted OHLCV が全欠損だったため、Phase2 featureには入れない。

---

# 9. Phase4-Aでやらないこと

Phase4-Aでは以下を行わない。

```text
feature計算実装
future_return_* label生成
AI学習
推論処理
期待値ランキング作成
利益予測
backtest
Historical Evaluation
paper trading
broker連携
注文機能
Opportunity AI実装
Position Management AI実装
Capital Allocation実装
Order Manager実装
Portfolio自動更新
```

---

# 10. Phase4-A完了条件

Phase4-Aは以下を満たせば完了とする。

```text
candidate_feature_catalog.md が存在する
Candidate AIの責務から逸脱していない
Opportunity AIの責務と混ざっていない
featureごとにleakage確認がある
使用禁止データが明記されている
daily_quotes_normalized 利用前提が明記されている
Phase4-BでTraining Data Designに進める
```

---

# 11. Phase4-Bへの引き継ぎ

Phase4-Bで決めること:

```text
feature table の物理保存先とschema
as_of_date / target_date の扱い
各featureのwindowとthreshold
財務情報の公表日反映ルール
セクター定義
market index の採用対象
欠損値の具体的な埋め方
異常値clipルール
Candidate AIの教師ラベル設計
candidate_score の意味と校正方法
候補数を50銘柄程度に制御する方法
```

Phase4-Bでは、このcatalogをもとに Training Data Design を作る。ただし、future系はlabelとしてのみ扱い、Candidate AIのfeatureには混入させない。
