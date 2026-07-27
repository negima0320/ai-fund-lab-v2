# AI Fund Lab vNext Position Management AI 設計書

関連するStrategy Layer最上位SoT:

```text
docs/02_architecture/strategy_architecture_v1.md
```

Phase21-D以降、Position Management AIは単体の保有判断だけでなく、Portfolio Policy、Market Context、Portfolio Constructionと明示Contractで接続される。ただし、PMはBroker quantity、lot rounding、final submit permission、Safety overrideを判断しない。

Phase21-FA以降、Corporate Event Authorityをreason inputとして利用できる。ただし、Corporate Event Authorityは事実を提供するだけであり、Position Management AIの判断を代行しない。

---

# 1. このドキュメントの目的

本ドキュメントは、

```text
Position Management AI
```

の役割、責務、入力、出力、成功条件を定義する。

---

# 2. Position Management AI の役割

## 一言で言うと

```text
保有ポジションを管理するAI
```

---

Candidate AIは、

```text
候補発見
```

---

Opportunity AIは、

```text
購入判断
```

---

Position Management AIは、

```text
購入後
```

を担当する。

---

# 3. Position Management AI が解く問題

問いは以下。

```text
この銘柄を

保有し続けるべきか？

売却するべきか？

買い増しするべきか？

減らすべきか？
```

---

重要。

Position Management AIは、

```text
何を買うか
```

を決めない。

---

Position Management AIは、

```text
持っている銘柄をどう扱うか
```

だけを判断する。

---

# 4. Position Management AI の位置付け

```text
Candidate AI

↓

Opportunity AI

↓

Capital Deployment

↓

購入

↓

Position Management AI

↓

HOLD
EXIT
ADD
REDUCE
```

---

# 5. 投資哲学との関係

AI Fund Lab の投資哲学は、

```text
良い企業

+

上昇開始

+

上昇継続
```

を取ること。

---

したがって、

Position Management AIの目的は、

```text
利益を最大化すること
```

ではない。

---

目的は、

```text
上昇トレンドが続く限り持つ
```

こと。

---

# 6. Position Management AI の思想

## やらないこと

```text
天井を当てる

底を当てる

最高値で売る
```

---

これは不可能。

---

## やること

```text
上昇継続中なら持つ

失速したら売る

シナリオ崩壊なら損切りする
```

---

# 7. Input

## Portfolio情報

```text
entry_price

holding_days

position_size

current_return

peak_return
```

---

## 市場データ

```text
現在価格

高値

安値

終値

出来高
```

---

## テクニカル

```text
価格モメンタム

出来高モメンタム

移動平均

トレンド強度

ボラティリティ
```

---

## Opportunity情報

```text
expected_edge_score

downside_risk_score
```

---

## 市場環境

```text
TOPIX

市場トレンド

セクター強弱
```

## Corporate Event

```text
listed_status
delisting_status
supervision_status
liquidation_status
final_trading_date
scheduled_earnings_date
scheduled_earnings_time
earnings_disclosed
forecast_revision_status
dividend_revision_status
corporate_action_type
effective_date
```

---

# 8. 利用禁止データ

禁止。

```text
future_return_*

future_max_return_*

future_max_drawdown_*

top_decile_*

downside_bad_*
```

---

また禁止。

```text
trade_result

future_profit

future_sell_price

future_best_price
```

ここでの禁止は、

```text
入力featureとして使うこと

推論時に参照すること
```

を指す。

学習・評価ラベルとしての利用は、

```text
system_requirements.md の学習データ要件
```

に従う。

---

Position Management AI は未来を見ない。

---

# 9. Output

---

## HOLD

意味

```text
上昇継続中
```

---

## EXIT

意味

```text
上昇終了

シナリオ崩壊
```

---

## ADD

意味

```text
強い上昇継続

追加購入候補
```

注意:

```text
ADD は買い増し命令ではない。

ADD は買い増し候補シグナルである。

最終的なTarget Portfolio採否はPortfolio Constructionが行う。購入金額候補、保有上限・cash・exposureの実行可能性評価はCapital Deploymentが行う。

含み損ポジションへのナンピン目的ADDは禁止。
```

Runtime IO contract:

- ADD は PM output から Planning へ渡る candidate signal であり、直接 Broker order にはならない。
- ADD-derived BUY は Capital Deployment policy、Current Position、cash / exposure、lot size、Safety、Submit Guard を通過した場合のみ Pending item になる。
- ADD-derived Pending item は `source_decision_type=ADD`、`source_pm_decision_id`、`source_pm_business_date`、`source_position_symbol`、`add_candidate_signal=true`、capital allocation status / reason、requested / approved notional、quantity を保持する。
- ADD reject は Evidence として残す。代表 reason は `MAX_POSITION_WEIGHT`、`MAX_EXPOSURE`、`INSUFFICIENT_CASH`、`LOT_SIZE_NOT_VIABLE`、`DUPLICATE_PENDING_ORDER`、`NO_LOSS_AVERAGING_GUARD`、`OPPORTUNITY_NO_LONGER_ELIGIBLE`、`INVALID_CURRENT_POSITION`、`AUTHORITY_NOT_ACCEPTED` である。

---

## REDUCE

意味

```text
上昇継続だが

リスク増大
```

---

## action_reason

例

```text
トレンド継続

出来高維持

失速検知

ストップ条件発動
EARNINGS_APPROACHING
HOLD_THROUGH_EARNINGS_ALLOWED
REDUCE_BEFORE_EARNINGS
EXIT_BEFORE_EARNINGS
POST_EARNINGS_MOMENTUM_CONFIRMED
POST_EARNINGS_GAP_REVERSAL
FORECAST_REVISION
DIVIDEND_REVISION
DELISTING_PENDING
```

Corporate Eventはreasonとして利用する。Position Management AIの正式Outputは `HOLD`、`ADD`、`REDUCE`、`EXIT` の4つを維持し、新しいActionを暗黙追加しない。

---

# 10. Position Management AI が判断しないこと

---

## 候補抽出

担当

```text
Candidate AI
```

---

## 購入順位

担当

```text
Opportunity AI
```

---

## Target Portfolio

担当

```text
Portfolio Construction
```

---

## 購入金額候補

担当

```text
Capital Deployment
```

---

## 注文実行

担当

```text
Order Manager
```

---

## Corporate Event事実生成

担当

```text
Corporate Event Authority
```

Position Management AIは、決算予定、上場状態、業績修正、配当修正、TOB、最終売買日などをPIT factとして受け取る。PMはその事実をreasonとして使えるが、Corporate Event Authorityの代替や補完をしない。

---

# 11. Position Management AI が見るもの

重要。

Position Management AIは、

```text
利益
```

ではなく、

```text
トレンド
```

を見る。

---

例

悪い考え方

```text
+5%

だから売る
```

---

良い考え方

```text
+5%

でも上昇継続

↓

保有
```

---

例

```text
+2%

失速

↓

売却
```

---

# 12. 成功条件

成功条件は、

```text
利益保持率向上
```

である。

---

評価例

```text
profit_retention_rate

winner_to_loser_rate

profit_decay_before_exit
```

---

目標

```text
上昇トレンドを取り切る

不要な損失を防ぐ
```

---

# 13. 失敗条件

---

## 利益確定AIになる

例

```text
+5%で売る

+10%で売る
```

だけ。

---

これは失敗。

---

## 損切りAIになる

例

```text
損切りしかしない
```

---

これも失敗。

---

## Opportunity AIと重複

Position Management AIが、

```text
どの銘柄を買うか
```

を判断したら失敗。

---

# 14. Position Management AI vNext 仮説

現時点の仮説。

---

保有継続条件

```text
価格モメンタム継続

出来高維持

市場環境良好
```

---

売却条件

```text
モメンタム失速

トレンド崩壊

市場環境悪化

ストップ条件発動
```

---

# 15. 将来の拡張

候補。

```text
モメンタム失速AI

利益保持AI

トレンド寿命推定

市場レジーム判定
```

---

ただし、

```text
Position Management AI

=
保有ポジション管理
```

という責務は変えない。

---

# 16. 最終原則

Position Management AIは、

```text
最高値で売るAI
```

ではない。

---

Position Management AIは、

```text
上昇トレンドが続く限り保有し、

上昇トレンドが終わったら売却するAI
```

である。

---

利益を最大化するのではなく、

トレンドを最大限活用することを目的とする。

---

# 17. Phase13検討事項: Portfolio Rotation / Position Management v2

Phase12-Hで、SELL統合は5年では年率50%を超えた一方、直近1年では大幅に悪化し、早売りリスクも確認された。

このためPhase13では、Position Management AIの隣接領域として以下を検討する。

```text
保有銘柄単体の健康診断

vs

保有銘柄と新規候補の期待値比較
```

現時点では、Position Management AIを拡張するとは決めない。

Phase13では、以下のいずれが適切かを設計レビューで判断する。

```text
Portfolio Rotation AIとして分離

Position Management AI v2として拡張

Portfolio Construction側の入力として扱う
```

新しいSELL理由候補として、以下を検討する。

```text
ROTATE
```

`ROTATE`は現在の正式Outputではない。Phase21-F時点のPosition Management AI正式Outputは `HOLD`、`ADD`、`REDUCE`、`EXIT` の4つである。

`ROTATE`相当の考え方は、Target Portfolio / Portfolio Constructionで既存position intentと新規候補を比較する将来検討に吸収する。Position Management AIの新actionとして暗黙追加しない。

この検討は資料上のロードマップ追加であり、AI再学習、Backtest再実行、Runtime変更、Broker接続、注文送信は行わない。
