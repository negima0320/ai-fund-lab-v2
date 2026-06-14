# AI Fund Lab vNext Phase7 Capital Allocation Policy Design

---

# 1. このドキュメントの目的

本ドキュメントは、

```text
Phase7 Capital Allocation Engine
```

を、単なる資金配分エンジンではなく、

```text
Buy / Hold / Replace / Defensive Exit / Emergency Exit
```

を整理する最終売買ポリシー層として定義する。

---

ただし、Phase7初期版では以下を行わない。

```text
Broker API接続
Paper Trading
実発注
live order
立花証券API呼び出し
AIによる自動資金配分
```

---

# 2. Phase7の基本思想

Phase7は、

```text
何を買うか
```

を決めるAIではない。

---

買い候補は、

```text
Phase5 Opportunity AI
```

が決める。

---

Phase7は、Phase5とPhase6の出力を受け取り、以下を判断する。

```text
どれだけ買うか

どれだけ売るか

何銘柄保有するか

既存保有を継続するか

新しいTop3候補へ入れ替えるか

防御的に売却候補にするか

大事故防止として強制終了候補にするか

現金比率をどう持つか
```

---

つまりPhase7は、

```text
Capital Allocation Engine
```

でありつつ、

```text
最終売買ポリシー層
```

として扱う。

---

# 3. 既存AIとの責務分離

## Phase4 Candidate AI

問い。

```text
何を監視するか？
```

役割。

```text
全銘柄からCandidate Top50を抽出する
```

---

## Phase5 Opportunity AI

問い。

```text
何を買うべきか？
```

役割。

```text
Candidate Top50からOpportunity順位を作る
```

---

## Phase6 Position Management AI

問い。

```text
保有をどう扱うべきか？
```

役割。

```text
HOLD / EXIT / ADD / REDUCE のシグナルを出す
```

ただしPhase6完了時点では、

```text
自動売却AIではない
防御 / 監視AIである
```

---

## Phase7 Capital Allocation Policy

問い。

```text
どれだけ買い、何を持ち続け、何を入れ替え候補にするか？
```

役割。

```text
資金配分
売却金額候補の算出
保有銘柄数の管理
保有継続判断
入れ替え候補判断
防御レビュー判断
緊急終了候補判断
現金比率管理
```

---

# 4. 重要な前提

Phase6までの検証では、以下が分かっている。

```text
Phase5 Opportunity Top3 が非常に強い

Top3の20営業日平均リターンは強い

Top4-5はBackup / Watch

Top6-10は通常買わない

Phase6 Position AIは防御AIとしては有効

Phase6 EXITを即売却に使うと利益を壊す可能性がある
```

---

したがって、Phase7初期版では、

```text
Phase6 EXIT
Phase6 REDUCE
```

を自動売却命令として扱わない。

---

これらは、

```text
review signal
defensive signal
monitoring signal
```

として記録する。

---

# 5. Top3 Persistence Pre-study の反映

Phase7実装前調査で、Opportunity Top3 は日次rankとしては非常に短命であることが分かった。

参照。

- `docs/phase_reports/phase7_prestudy_top3_persistence_analysis.md`

---

重要な結果。

```text
Top3 membership 平均滞在:
約1.48営業日

Top3 membership 中央値:
1営業日

Top3からの翌営業日脱落率:
67.5%

5営業日以内脱落率:
87.6%

隣接営業日のTop3継続率:
平均32.5%

Top3銘柄の5営業日後Top3維持率:
12.4%

Top3銘柄の20営業日後Top3維持率:
3.9%

5営業日後にCandidate Top50外:
60.2%
```

---

したがって、単純な以下のルールは採用しない。

```text
Top3から落ちたらReplace
```

---

理由。

```text
高回転になり、
Phase6で確認した Top3 fixed 20bd hold の強さを壊す可能性が高い
```

---

Phase7は日次Top3同期型ではなく、以下の方針にする。

```text
Top3で買う
ただしTop3から1日落ちただけでは売らない
原則HOLD中心
Replacementは強い条件を満たした時だけ
Emergency Exitだけは機械的即時候補
```

---

# 6. Phase7の入力

## Opportunity入力

```text
symbol
trade_date
buy_rank
expected_edge_score
downside_risk_score
risk_guard_status
buy_reason
no_buy_reason
```

---

## Position入力

```text
symbol
entry_date
entry_price
current_price
unrealized_return
holding_days
current_position_size
position_action
exit_signal
reduce_signal
add_signal
exit_confirmation_count
position_risk_status
```

---

## Portfolio入力

```text
initial_assets
current_assets
total_assets
invested_value
cash
cash_available
available_cash
current_positions
current_position_value
current_weight
cash_buffer
cash_buffer_ratio
max_positions
max_position_weight
min_position_value
max_position_size
max_position_value
target_position_weight
target_position_value
minimum_order_size
min_buy_amount
lot_size
```

---

## 運用設定

```text
primary_buy_rank_cutoff
watch_rank_cutoff
max_positions
max_holdings_reference
max_position_weight_candidates
target_position_weight
min_position_value
max_position_value
min_buy_amount
lot_size
cash_buffer_ratio_candidates
rebalance_interval_bd
emergency_exit_threshold_candidates
emergency_exit_pct_candidates
minimum_holding_days_candidates
confirmation_days_candidates
replacement_edge_margin
replacement_edge_margin_candidates
replacement_rank_degradation_threshold
replacement_rank_degradation_threshold_candidates
```

---

# 7. Phase7の出力

Phase7は、発注ではなく売買ポリシー案を出力する。

```text
policy_date
code
symbol
policy_action
action
current_position_value
target_position_value
buy_amount
sell_amount
lot_size_adjusted_buy_amount
target_weight
current_weight
expected_edge_score
buy_rank
opportunity_rank
downside_risk_score
risk_guard_status
position_signal
allocation_reason
hold_reason
replacement_reason
defensive_reason
emergency_reason
skip_reason
review_required
cash_after_action
validation_notes
```

---

`policy_action` / `action` の候補。

```text
BUY
HOLD
REPLACE_SELL
REPLACE_BUY
EMERGENCY_EXIT
DEFENSIVE_REVIEW
NO_ACTION
```

---

重要。

```text
Phase7初期版の出力はorderではない
```

---

# 8. 保有数とポジションサイズの考え方

Phase7では、固定の最大保有数だけを主役にしない。

---

理由。

```text
資金が複利で増える前提では、
総資産額に応じて自然に保有数が変わる設計が望ましい
```

---

主役にする制約。

```text
max_position_weight
min_position_value
max_position_value
available_cash
lot_size
target_position_value
```

---

例。

```text
総資産100万円
max_position_weight 20%

1銘柄最大20万円
```

```text
総資産500万円
max_position_weight 20%

1銘柄最大100万円
```

---

ただし、

```text
max_position_value
```

を設定する場合、資金増加に伴って保有銘柄数が自然に増える。

---

例。

```text
総資産500万円
max_position_weight 20%
max_position_value 50万円

1銘柄最大50万円
結果として保有銘柄数は増えやすくなる
```

---

初期検証では、比較用に以下を扱う。

```text
max_position_weight = 20%
max_position_weight = 15%
max_position_weight = 10%
```

---

参考比較として、固定保有数も扱ってよい。

```text
max_holdings 3
max_holdings 5
max_holdings 7
max_holdings 10
```

---

ただし本命は、

```text
max_position_weight / target_position_value ベース
```

である。

---

# 9. 買付金額の判断

Phase7は、Opportunity Top3に対して実際の買付金額候補を決める。

---

初期仕様ではAI配分をしない。

---

候補。

```text
equal_weight
rank_weighted
score_weighted
```

---

初期版は、

```text
simple / equal + cap制約
```

を採用する。

---

`rank_weighted` と `score_weighted` は将来検討とする。

---

必要な概念。

```text
target_position_weight
target_position_value
current_position_value
buy_amount
available_cash
cash_buffer
min_buy_amount
lot_size_adjusted_buy_amount
```

---

買付金額候補の基本式。

```text
target_position_value
=
min(
  total_assets * target_position_weight,
  total_assets * max_position_weight,
  max_position_value
)
```

---

既存保有がない場合。

```text
buy_amount
=
min(
  target_position_value,
  available_cash
)
```

---

既存保有がある場合。

```text
buy_amount
=
max(
  target_position_value - current_position_value,
  0
)
```

---

最後に、

```text
lot_size
minimum_order_size
min_buy_amount
available_cash
```

で調整する。

---

調整後に最低買付額を満たさない場合は、

```text
action: NO_ACTION
skip_reason: below_min_buy_amount
```

として記録する。

---

# 10. 売却金額の判断

Phase7は、売却も全売却だけでなく、売却理由ごとに扱いを分ける。

---

## Replacement Exit

基本は、

```text
保有銘柄を売って新規Top3へ入れ替える
```

である。

---

ただし、Top3 Persistence Pre-study の結果から、以下は本採用しない。

```text
Top3から落ちたら即Replace
```

---

Replacement Exit は、以下のような強い条件を満たした場合だけ候補にする。

```text
rank degradation
edge margin
minimum holding days
confirmation days
risk / defensive context
```

---

初期仕様では単純化し、

```text
full replacement
```

を採用する。

---

```text
full replacement:
既存銘柄を全売却して新候補へ資金移動
```

---

## Replacement Execution Constraint

Phase7-Aでは、dry-run / validation 用の decision record として、

```text
REPLACE_SELL
REPLACE_BUY
```

を同時に出力できる。

ただし、これは論理上の same-day replacement 比較であり、実注文の同時実行を意味しない。

---

実運用では、REPLACE_SELL と REPLACE_BUY を同時実行しない。

理由は、現物株の乗り換えでは売却注文が約定してから買付余力を再確認し、その後に新規買付を行う必要があるためである。

---

実運用の順序。

```text
1. REPLACE_SELL 候補を出す
2. 売り注文を出す
3. 売り約定を確認する
4. broker snapshot / buying power / cash を再取得する
5. REPLACE_BUY 候補を再評価する
6. 買付可能額・ロット・価格を確認してから買い注文を出す
```

---

Phase7-A / Phase7-B の dry-run / validation では、比較検証のために論理上 same-day replacement として扱ってよい。

ただし、将来の Broker / Paper Trading / live integration では、必ず以下の二段階実行にする。

```text
replacement_sequence:
SELL_FIRST_BUY_AFTER_FILL
```

---

将来の decision notes / schema 拡張候補。

```text
execution_constraint
requires_fill_confirmation
paired_replacement_id
replacement_sequence
```

初期Phase7-Aでは、これらは実注文制御ではなく設計上の制約として扱う。

---

将来検討。

```text
partial replacement:
既存銘柄の一部を売却して新候補へ資金移動
```

---

## Emergency Exit

Emergency Exitは、大暴落・大事故防止の最終防衛ラインである。

---

初期仕様。

```text
-X%到達時は原則full exit
```

---

Xは以下を比較検証する。

```text
-10%
-12%
-15%
-20%
-25%
```

---

## Defensive Exit

Phase6 EXIT / REDUCE / risk悪化は、初期では即売却しない。

---

初期仕様。

```text
sell_amount: 0
defensive_review_flag: true
action: DEFENSIVE_REVIEW
```

---

将来検討。

```text
partial reduce
```

---

# 11. 現金管理

Phase7では、現金比率も管理対象にする。

---

必要な概念。

```text
total_assets
invested_value
cash
available_cash
cash_buffer
cash_buffer_ratio
```

---

初期値候補。

```text
cash_buffer_ratio = 0%
cash_buffer_ratio = 5%
```

---

初期Phase7では複雑にしすぎない。

---

まずは、

```text
cash_buffer 0% / 5%
```

を比較候補として整理する。

---

`available_cash` は以下で定義する。

```text
available_cash
=
cash - cash_buffer
```

---

買付候補は、

```text
available_cash >= min_buy_amount
```

を満たす範囲に制限する。

---

# 12. 初期Buyポリシー

## BUY

Primary対象。

```text
Opportunity Top3
```

---

Watch / Backup。

```text
Top4-5
```

---

No Buy。

```text
Top6-10
```

---

## 資金配分

初期版はAI配分を行わない。

```text
均等配分
```

を基本とする。

---

ただし、Phase7-Aの検証では、

```text
1,000,000 JPY / Top3 equal-weight
```

を開始点とする。

---

既存のCapital Allocation基本設計にある、

```text
最大保有5銘柄
1銘柄20万円
```

は、通常運用における集中上限・保有枠の基本制約として扱う。

---

Phase7-Aでは、以下を明示的に比較対象として扱う。

```text
Top3 equal-weight
Top5 equal-weight
max_positions=5 under Top3 primary policy
max_position_weight=20%
max_position_weight=15%
max_position_weight=10%
cash_buffer_ratio=0%
cash_buffer_ratio=5%
```

---

# 13. 初期Holdポリシー

保有銘柄が引き続き以下を満たす場合は、原則HOLDとする。

```text
Opportunity Top3に残っている

または

expected_edge_scoreが強い状態を維持している

または

Opportunity rankが大きく劣化していない
```

---

特にTop3由来の勝ち銘柄は、

```text
Winnerを早売りしない
```

ことを優先する。

---

Phase7-Aでは、以下を初期方針とする。

```text
minimum_holding_days 未満では、Emergency Exit以外では売らない

Top3から1日落ちただけでは売らない

Opportunity rankの日次変動だけで売却しない
```

---

含み益が出ていること自体は売却理由にしない。

```text
+10%
+15%
+20%
```

のような固定利確は初期採用しない。

---

# 14. Replacement Exit

## 目的

```text
資金効率最大化
```

---

## 基本思想

保有銘柄を売る理由は、

```text
利益が出たから
```

ではない。

---

売る理由は、

```text
現在の保有銘柄より
新しいOpportunity Top3候補の期待値が明確に高いから
```

である。

---

これは、

```text
Take Profit
```

ではなく、

```text
Replacement Exit
```

である。

---

## 例

HOLD例。

```text
保有Aが +18%
現在もOpportunity Rank 2

判断:
HOLD
```

---

Replacement候補例。

```text
保有Aが +18%
現在Rank 20以下に低下
新しいRank 1候補Bのexpected_edge_scoreが明確に高い

判断:
AをREPLACE_CANDIDATEとして記録
BをBUY_CANDIDATEとして記録
```

---

## 初期Replacement条件案

Replacement Exit は、以下の全条件を満たす場合のみ候補にする。

```text
minimum_holding_days を満たしている

保有銘柄のOpportunity順位が明確に劣化している
例:
Top10外
Top20以下
Candidate Top50外

新規Top3候補の expected_edge_score が保有銘柄より明確に高い

replacement_edge_margin を満たしている

confirmation_days を満たしている
例:
1日だけではなく2-3営業日確認

Phase6 / risk_guard / downside_risk が保有継続を強く支持していない
```

---

重要。

```text
単純なTop3脱落ではReplaceしない
```

---

## Replacement判定の入力候補

```text
current_holding_rank
new_top3_rank
current_expected_edge_score
new_expected_edge_score
rank_degradation
expected_edge_score_degradation
downside_risk_score
risk_guard_status
holding_days
minimum_holding_days
confirmation_days
capital_available
```

---

## 初期仕様で未確定の閾値

以下はPhase7検証で決める。

```text
minimum_holding_days
replacement_edge_margin
replacement_rank_degradation_threshold
confirmation_days
replacement_recheck_interval
```

---

# 15. Defensive Exit

## 目的

```text
危険シグナルの検出
```

---

## 入力

```text
Phase6 Position AI
risk_guard_status
downside_risk_score
Opportunity rank degradation
expected_edge_score degradation
```

---

## 初期仕様

Defensive Exitは、初期Phase7では即売却しない。

---

以下として扱う。

```text
review candidate
defensive warning
monitoring signal
```

---

## Defensive signalの例

```text
Phase6 EXITが連続

Phase6 REDUCEが連続

risk_guard_statusが悪化

downside_risk_scoreが悪化

Opportunity順位が大きく低下

expected_edge_scoreが大きく低下
```

---

## 出力

```text
policy_action: DEFENSIVE_REVIEW
review_required: true
defensive_reason: detected signals
```

---

重要。

```text
Phase6 EXIT単発での自動売却は禁止
```

---

# 16. Emergency Exit

## 目的

```text
大暴落・大事故からの資産防衛
```

---

## 基本思想

Emergency ExitはAI判断ではない。

---

これは、

```text
機械的な最終防衛ライン
```

である。

---

## 初期ルール

含み損が一定ラインに到達したら、

```text
EMERGENCY_EXIT
```

として原則full exit候補にする。

---

売却金額。

```text
sell_amount = current_position_value
```

---

ただし、Xは固定しない。

---

Phase7検証では以下を比較する。

```text
-10%
-12%
-15%
-20%
-25%
```

---

評価の目的。

```text
期待値を壊さず最大DDを抑えられるラインを決める
```

---

# 17. Take Profitの扱い

固定利確は初期採用しない。

---

初期仕様に入れないもの。

```text
+10%で利確
+15%で利確
+20%で利確
```

---

理由。

```text
利益が出たから売るのではなく、
より期待値の高い候補がある場合に資金を移すべきだから
```

---

したがって、Phase7では、

```text
利確
```

という言葉より、

```text
Replacement Exit
```

として整理する。

---

# 18. 初期ポリシー一覧

## BUY

```text
Opportunity Top3をPrimary対象
Top4-5はWatch / Backup
Top6-10はNo Buy
```

---

## HOLD

```text
原則HOLD中心
保有銘柄が引き続きTop3または強いOpportunity状態なら原則HOLD
minimum_holding_days 未満では、Emergency Exit以外では売らない
Top3から1日落ちただけでは売らない
Winnerを早売りしない
```

---

## REPLACE

```text
単純なTop3脱落ではReplaceしない
保有銘柄より新規Top3候補が明確に高期待値なら入れ替え候補
minimum_holding_days + rank degradation + edge margin + confirmation を満たす場合のみ候補
単なる含み益では売らない
```

---

## DEFENSIVE

```text
Phase6 EXIT / REDUCE / risk悪化はreview signal
初期仕様では即売却しない
sell_amount = 0
自動売却命令にしない
```

---

## EMERGENCY

```text
-X%到達時のみ強制終了候補
Xは検証で決める
```

---

## TAKE PROFIT

```text
固定利確は初期採用しない
本命ポリシーではReplacement Exitとして扱う
```

---

# 19. 比較検証したいPolicy

## Policy A

```text
Opportunity Top3 primary buy + equal allocation baseline
```

目的。

```text
Capital Allocationの最小基準線を確認する
```

---

## Policy B1

```text
Top3 fixed 20bd hold
```

目的。

```text
Phase6で強かった基準線を再現する
```

---

## Policy B2

```text
Top3 + minimum_holding_days + conservative replacement
```

目的。

```text
Top3 fixed 20bd holdを壊さず、明確な劣化時だけ入れ替えられるか確認する
```

---

## Policy B3

```text
B2 + confirmation_days
```

目的。

```text
1日だけのrank変動による過剰Replacementを抑制できるか確認する
```

---

## Policy C

```text
B3 + Emergency Exit
```

目的。

```text
期待値を壊さず最大DDを抑えられるか確認する
```

---

## Policy D

```text
C + Defensive review signal
```

目的。

```text
Phase6防御シグナルを自動売却ではなくレビュー層として使う効果を確認する
```

---

## Policy E

```text
日次Top3同期Replacement
```

位置付け。

```text
参考比較のみ
本命ではない
高回転リスク確認用の比較対象
単純なTop3脱落Replacementの本採用ではない
```

---

# 20. 評価指標

Phase7では、少なくとも以下を評価する。

```text
CAGR / 年率換算
final_assets
cumulative_return
profit_factor
max_drawdown
worst_trade
average_trade_return
win_rate
average_winner
average_loser
capital_utilization
turnover
average_holding_days
median_holding_days
replacement_count
replacement_rate
emergency_exit_count
defensive_signal_count
defensive_review_count
sold_then_up_rate
sold_then_down_rate
early_exit_loss_count
missed_winner_rate
transaction_cost_sensitivity
```

---

## 特に重要な指標

利益を壊していないか。

```text
CAGR
final_assets
cumulative_return
average_trade_return
```

---

防御として効いているか。

```text
max_drawdown
worst_trade
emergency_exit_count
sold_then_down_rate
```

---

勝者を早売りしていないか。

```text
sold_then_up_rate
missed_winner_rate
average_winner
```

---

売買しすぎていないか。

```text
turnover
average_holding_days
median_holding_days
replacement_count
replacement_rate
capital_utilization
transaction_cost_sensitivity
```

---

早売りで勝者を壊していないか。

```text
early_exit_loss_count
missed_winner_rate
sold_then_up_rate
```

---

# 21. 禁止事項

Phase7初期版では以下を行わない。

```text
Broker API接続
Paper Trading実装
実発注
live order
立花証券API呼び出し
AIによる資金配分
Kelly基準
レバレッジ
信用取引
ナンピン
Phase6 EXIT単発での自動売却
単純なTop3脱落Replacementの本採用
固定利確の本採用
```

---

# 22. Phase7-A実装前に決めるべき論点

Phase7-A実装前に、以下を確認する。

---

## 1. Top3 equal-weightとポジションサイズ制約の扱い

基本設計では、

```text
最大保有5銘柄
```

が定義されている。

一方、Phase6ハンドオフでは、

```text
Top3 primary allocation
```

が推奨されている。

---

Phase7-Aでは、

```text
Top3をPrimary
最大5銘柄は参考比較 / 集中上限
Top4-5はWatch / Backup
本命はmax_position_weight / target_position_valueベース
```

として扱うのが自然である。

---

## 2. max_position_weight

比較候補。

```text
20%
15%
10%
```

確認したいこと。

```text
集中を抑えつつTop3の強さを壊さない上限
資産増加時に自然に保有銘柄数が増えるか
```

---

## 3. min_position_value / max_position_value

未決定。

```text
min_position_value
max_position_value
```

確認したいこと。

```text
小さすぎるポジションを避ける
大きすぎるポジション集中を避ける
資産増加時の保有銘柄数増加を許容する
```

---

## 4. cash_buffer_ratio

比較候補。

```text
0%
5%
```

確認したいこと。

```text
資金効率を壊さず注文余力を残せるか
```

---

## 5. min_buy_amount / lot_size

未決定。

```text
min_buy_amount
lot_size
lot_size_adjusted_buy_amount
```

確認したいこと。

```text
小さすぎる買付を避ける
実取引単位を後続Phaseで接続しやすくする
```

---

## 6. minimum_holding_days

初期候補。

```text
5
10
20
```

確認したいこと。

```text
Top3 fixed 20bd holdの強さを壊さず、
明確な劣化時だけReplacementできるか
```

---

## 7. replacement_rank_degradation_threshold

初期候補。

```text
Top10外
Top20以下
Candidate Top50外
```

確認したいこと。

```text
単純なTop3脱落より強い劣化条件として機能するか
```

---

## 8. replacement_edge_margin

初期候補。

```text
0.00
0.01
0.02
0.03
```

確認したいこと。

```text
新規Top3候補が保有銘柄より明確に高期待値か
```

---

## 9. confirmation_days

初期候補。

```text
1
2
3
```

確認したいこと。

```text
1日だけのrankノイズでReplacementしないようにできるか
```

---

## 10. Replacementの明確な閾値

以下を検証で決める必要がある。

```text
何rank落ちたら入れ替え候補か
expected_edge_score差がどれだけあれば明確に高いとするか
保有何日未満なら入れ替えを抑制するか
```

---

## 11. Replacementの売却方式

初期仕様。

```text
full replacement
```

将来検討。

```text
partial replacement
```

確認したいこと。

```text
full replacementで回転率が上がりすぎないか
partial replacementを導入する必要があるか
```

---

## 12. emergency_exit_pct

比較候補。

```text
-10%
-12%
-15%
-20%
-25%
```

選定基準。

```text
期待値を壊さず
最大DDとworst_tradeを改善する
```

---

## 13. Defensive signalの扱い

初期仕様では、

```text
自動売却しない
review signalとして記録する
sell_amountは原則0
```

ただし、検証上は以下を測る。

```text
Defensive signal後に下落した割合
Defensive signal後に上昇した割合
false warning率
```

---

## 14. 20bd固定保有の再評価タイミング

以下を比較する。

```text
20bdまで完全固定
10bdで中間再評価
5bdごとに再評価
毎営業日再評価
```

ただし、Phase6の残課題として、

```text
full daily close path validation
```

が残っているため、日次評価は将来拡張として段階的に扱う。

---

# 23. 完了条件

Phase7初期版の設計完了条件。

```text
Buy / Hold / Replace / Defensive / Emergency の責務が分離されている

固定利確を本命ポリシーにしていない

Phase6 EXIT / REDUCEを自動売却命令にしていない

単純なTop3脱落Replacementを本採用していない

Top3 primary / Top4-5 watch / Top6-10 no buy が明文化されている

minimum_holding_days / replacement_edge_margin / confirmation_days が検証対象として扱われている

Emergency ExitのXが検証対象として扱われている

Broker / Paper / live / order が範囲外として明記されている

売却金額の判断がReplacement / Emergency / Defensiveで分離されている

固定保有数ではなくmax_position_weight / target_position_valueを本命制約としている

cash_buffer_ratioが検証対象として扱われている
```

---

# 24. 最終原則

Phase7は、

```text
利益を作るAI
```

ではない。

---

利益を作る主役は、

```text
Phase4 Candidate AI
Phase5 Opportunity AI
Phase6 Position Management AI
```

である。

---

Phase7は、

```text
資金を壊さず
勝者を早売りせず
より強い候補へ必要なときだけ資金を移す
```

ためのポリシー層である。
