# Phase7 Final Summary and Phase8 Handoff

## 1. Phase7完了判定

Phase7 Capital Allocation Engine は、過去データ検証上は以下の状態に到達した。

```text
PHASE7_COMPLETED_WITH_VALIDATED_CAPITAL_ALLOCATION_POLICY
```

ただし、この完了判定は **Broker API / Paper Trading / 実売買を含まない**。

Phase7で完了したのは、ローカル既存artifactを使ったCapital Allocation Policyの設計、実装、検証、監査、ユーザー向けレポート作成である。実際の証券会社接続、買付余力照会、注文、約定、Paper TradingはPhase8以降の対象とする。

未実施。

```text
Broker API接続
Paper Trading
実発注
live order
立花証券API呼び出し
新規J-Quants API取得
```

## 2. Phase7の目的

Phase7は「何を買うか」を決めるAIではない。

役割分担。

```text
何を買うか
↓
Phase5 Opportunity AI

保有をどう見るか
↓
Phase6 Position AI

いくら買うか
どれを売るか
どれだけ保有するか
資金をどう使うか
↓
Phase7 Capital Allocation Engine
```

Phase7は、Opportunity Top3を主な買付対象としつつ、保有継続、Replacement、現金比率、100株単位、T+2、SELL_FIRST_BUY_AFTER_FILL、コスト感応度を扱う最終売買ポリシー層として整理した。

## 3. Phase7-A〜Gの経緯

### Phase7-A

Capital Allocation Engine の最小実装を行った。

実装内容。

```text
BUY / HOLD / REPLACE / EMERGENCY / DEFENSIVE decision
position sizing
cash buffer
max_position_weight
minimum_holding_days
decision schema
audit
```

重要制約。

```text
SELL_FIRST_BUY_AFTER_FILL
```

Phase7-Aのdry-runでは `REPLACE_SELL` と `REPLACE_BUY` をdecision recordとして同日に出せるが、実運用では売却約定後にbuying powerを再取得し、買付を再評価する二段階実行が必須とした。

実APIは未実行。

### Phase7-B

Conservative Replacement Validation を軽量に実施した。

分かったこと。

```text
Top3 fixed 20bd hold が非常に強い
単純なTop3脱落Replacementは高回転になりすぎる
Phase7-A default replacementはTop3 fixed holdの強さを壊す
Daily Top3 Syncはreplacement_rateがほぼ100%で本命ではない
```

この時点ではforward label近似が中心で、full daily close pathではなかった。

### Phase7-C

Full Daily Path Validation を実施した。

内容。

```text
日次終値パスでEmergency Exitを検証
Replacement途中売却returnを日次終値で計算
same-day replacementとSELL_FIRST_BUY_AFTER_FILLを比較
decisionとevaluationを分離
```

結果。

```text
Top3 fixed 20bd hold は日次終値パスでも強い
C3_TOP50OUT_MIN10が強く見えた
Daily Top3 Syncは高回転すぎる
cash timingの影響は非常に大きい
```

### Phase7-D

Realistic Execution Constraint Validation を実施した。

反映した制約。

```text
100株単位
min_position_value
cash buffer
max_position_weight
transaction cost / slippage
replacement cooldown
replacement cap per month
weekly / monthly reevaluation
SELL_FIRST_BUY_AFTER_FILL
```

結果。

```text
C3_MIN15が有力化
C3_MIN10 / C3_MIN15 の優位は現実的制約後も残った
ただしreplacement_rateはまだ高い
100株単位とmin_position_valueによる買い逃しは無視できない
```

### Phase7-E

Strict Long-Term Backtest / Exact Accounting を実施した。

明示した会計。

```text
exact share accounting
exact cash accounting
T+2 settlement
cash / unsettled cash
trade ledger
daily portfolio ledger
holdings ledger
transaction cost / slippage
```

主要結果。

```text
C3_MIN15_T2 は A_FIXED_20BD を大幅に上回った
final_assets_net = 873,471,440円
cumulative_return_net = 872.471
annualized_return_net = 316.5%
```

ただし、

```text
replacement_rate = 0.814
```

であり、Phase8 Broker Test / Paper Trading候補としては高すぎると判断した。

### Phase7-F

Turnover Reduction & Robustness Validation を実施した。

目的。

```text
C3_MIN15_T2の利益をなるべく維持しながら
replacement_rateを0.2〜0.5程度まで下げる
```

結果。

```text
CAP5がPrimary候補
CAP4がConservative候補
POLICY_Y_CAP4_EDGE08_CONF5が2026 weak-regime比較枠
```

CAP5は `replacement_rate` を `0.814` から `0.484` まで下げつつ、Referenceを大きく上回った。

### Phase7-G

Final Integrated Backtest / User Report を実施した。

内容。

```text
初期資金100万円
CAP5 / CAP4 / POLICY_Y / A_FIXED_20BD / C3_MIN15_T2 を統合比較
0bps / 10bps / 30bps cost/slippage比較
年別・月別・複利分析
銘柄名付きユーザー向けレポート
業種別・市場区分別分析
```

CAP5結果。

```text
final_assets_net = 614,731,820円
CAGR = 286.8%
max_drawdown = -33.6%
replacement_rate = 48.4%
```

注意。

```text
Paper Trading / 実売買は未実施
過去データ検証であり将来利益を保証しない
```

## 4. 最終採用候補Policy

### Primary: CAP5

設定。

```text
minimum_holding_days = 15
replacement_rank_threshold = Candidate Top50外
confirmation_days = 2
replacement_edge_margin = 0.02
replacement_cap_per_month = 5
settlement = conservative_T2_cash_unavailable
lot_size = 100
cash_buffer_ratio = 5%
max_position_weight = 20%
SELL_FIRST_BUY_AFTER_FILL
```

評価。

```text
利益と回転率のバランスが最も良い
Phase8 Paper Trading主候補
```

### Conservative: CAP4

設定。

```text
CAP5と同じ
replacement_cap_per_month = 4
```

評価。

```text
CAP5より利益は落ちる
DDと回転率が低い
Phase8ではCAP5のshadow比較候補
```

### Weak-regime comparison: POLICY_Y_CAP4_EDGE08_CONF5

設定。

```text
replacement_cap_per_month = 4
replacement_edge_margin = 0.08
confirmation_days = 5
```

評価。

```text
全期間主候補ではない
2026 weak-regime比較枠
```

### Reference

```text
A_FIXED_20BD
C3_MIN15_T2
```

`A_FIXED_20BD` は強いBaselineとして維持する。`C3_MIN15_T2` は高利益だが高回転すぎるため、採用候補ではなくReference High Turnoverとして扱う。

## 5. Phase7-G主要結果

対象。

```text
Primary Policy:
CAP5_0BPS

initial_capital:
1,000,000 JPY
```

| 項目 | 結果 |
| --- | ---: |
| final_assets_net | 614,731,820円 |
| total_profit | 613,731,820円 |
| cumulative_return | 613.732 |
| CAGR | 286.8% |
| max_drawdown | -33.6% |
| win_rate | 60.7% |
| average_holding_days | 18.5 |
| trade_count | 570 |
| replacement_rate | 48.4% |
| average_cash_ratio | 8.8% |
| average_capital_utilization | 82.1% |

重要な注意。

```text
これは過去データ検証であり、将来の利益を保証しない。
実取引、実約定、Paper Trading、Broker buying power照会は未検証。
税金、部分約定、値幅制限、売買停止、流動性制約も未反映。
```

## 6. 年別結果

CAP5年別結果。

| 年 | 年間収益率 | 年間DD | 取引回数 | replacement_count |
| --- | ---: | ---: | ---: | ---: |
| 2021 | +20.5% | -20.6% | 26 | 19 |
| 2022 | +535.2% | -18.4% | 106 | 60 |
| 2023 | +245.3% | -16.4% | 104 | 60 |
| 2024 | +837.3% | -33.6% | 121 | 57 |
| 2025 | +126.6% | -19.3% | 148 | 60 |
| 2026 | -5.5% | -25.7% | 65 | 20 |

2026は検証期間途中かつPhase6から継続して見えている weak-regime として扱う。Phase8ではPolicy Yや市場環境監視を併走させるが、2026だけに過剰最適化しない。

## 7. 銘柄分析まとめ

利益貢献上位。

```text
大東港運
ジャパンディスプレイ
木徳神糧
川西倉庫
山一電機
```

損失貢献上位。

```text
トーシンホールディングス
インバウンドテック
REVOLUTION
ビーマップ
ソレイジア・ファーマ
```

業種別。

```text
強い:
電気機器
倉庫・運輸関連業

注意:
情報通信・サービス
グロース市場
```

市場区分。

```text
スタンダード / プライム:
純利益中心

グロース:
大きな勝ちもあるが純損益マイナス
```

銘柄名解決。

| 項目 | 結果 |
| --- | ---: |
| ユニーク銘柄数 | 369 |
| 銘柄名解決済み | 314 |
| 未解決 | 55 |
| 解決率 | 85.1% |

未解決銘柄は、2026-06-01時点のローカルJ-Quants銘柄マスタに存在しないため、上場廃止・コード変更・特殊商品・マスタ時点差の可能性がある。

## 8. 重要な学び

### 学び1

Top3を毎日追いかけると高回転になりすぎる。

Phase7前調査ではTop3 membershipの平均滞在が約1.48営業日、翌営業日脱落率が67.5%だった。単純な日次Top3同期は実運用向きではない。

### 学び2

Top3 fixed 20bd hold は非常に強いBaselineだった。

Phase7-B/C/E/Gを通じて、Referenceとして残す価値が高いことを確認した。

### 学び3

単純なReplacementでは利益を壊す。

Top3から落ちただけで売る、またはrank劣化だけで売る設計は高回転化し、コストやスリッページに弱くなる。

### 学び4

Candidate Top50外 + minimum_holding_days + monthly cap の組み合わせが有効だった。

CAP5は `minimum_holding_days = 15` と `replacement_cap_per_month = 5` により、C3_MIN15_T2より回転率を大幅に下げつつ利益を残した。

### 学び5

SELL_FIRST_BUY_AFTER_FILL は必須。

現物株の乗り換えでは、売却約定前の買付余力を前提にしてはいけない。Phase8でも売却、約定確認、broker snapshot再取得、買付再評価の順序を守る。

### 学び6

Emergency -10% は「-10%で約定できる保証」ではない。

Phase7-E監査で、`A_FIXED_EMERGENCY10` のworst tradeが `-64.3%` になった。Emergencyは日次終値で-10%を超えたら売却するトリガーであり、ギャップダウンやストップ安では-50%以上の損失もあり得る。

### 学び7

低位株・流動性・値幅制限・売買停止はPhase8以降の重要課題。

日次終値ベースの検証では、実際に売れるか、どの価格で約定するか、何株約定するかを保証できない。

### 学び8

Phase7の結果はポテンシャルを示すが、実運用結果を保証しない。

Phase8ではRead-only Broker SyncとPaper Tradingで、机上の売買planが現実の買付余力・約定制約・注文状態と整合するかを検証する。

## 9. 未解決課題

Phase8以降へ残す課題。

```text
Full pipeline backtest未実施の可能性
Phase7では既存 opportunity_ranked_daily.parquet を使った可能性が高く、
raw J-Quants -> Candidate -> Opportunity -> Position -> Capital Allocation
の完全再計算ではない可能性がある

Broker API未接続
Paper Trading未実施
実約定未検証
税金未考慮
部分約定未考慮
値幅制限未考慮
売買停止未考慮
出来高 / 流動性制約未考慮
リーマンショック級暴落未検証
低位株ギャップダウンリスク
グロース市場の損失抑制
2026 weak-regime対策
銘柄名解決率85.1%で未解決銘柄あり
立花証券APIの実際の買付余力・約定・注文状態未検証
```

特に重要なリスク。

```text
1. 実際に約定できるか
2. 約定価格が終値想定からどれだけズレるか
3. 売却代金がいつ買付余力に反映されるか
4. 低位株のギャップダウン / ストップ安をどう扱うか
5. 2026型の弱い相場でCAP5を止めるべきか、続けるべきか
```

## 10. Phase8でやること

Phase8は実売買ではない。まずRead-onlyとPaper Tradingで現実接続の検証を行う。

### Phase8-A Broker Read-only Sync

目的。

```text
証券会社状態を読む
発注しない
```

対象。

```text
login/logout
broker snapshot
cash
buying power
holdings
order list
API応答保存
発注禁止
```

### Phase8-B Paper Trading設計

目的。

```text
CAP5をpaperで日次実行
CAP4 / POLICY_Yもshadow比較
実Broker buying powerと比較
SELL_FIRST_BUY_AFTER_FILL状態管理
```

Paper Tradingでも、売却約定前に買付しない。Broker snapshotとpaper ledgerの差分を記録する。

### Phase8-C Order Plan Generator

目的。

```text
発注はしない
BUY / SELL planだけ生成
Human Review前提
```

Order Planは実注文ではなく、人間が確認するための候補表とする。

### Phase8-D Risk / Crash Guard設計

対象。

```text
低位株フィルタ
流動性フィルタ
前日比急落検知
値幅制限 / ストップ安 / 特売り監視
立花証券リアルタイム監視APIを使う候補
```

Emergency Exitは「損失上限」ではなく「危険検知」なので、板・気配・値幅制限・出来高を見ない限り実運用の防御としては不十分。

### Phase8-E Human Review Gate

目的。

```text
実注文前に必ず人間承認
live orderはPhase8では禁止、または別Phase扱い
```

## 11. Safety / 禁止事項

Phase8引き継ぎの禁止事項。

```text
いきなり実売買しない
live orderを実装しない
発注系APIを有効化しない
まずRead-only
次にPaper Trading
Order Planは人間確認用
実注文は別Phaseで再承認
```

Phase8開始時の基本姿勢。

```text
Read-only first
Paper next
Order plan only
Human review required
No live order
```

## 12. Phase8で最初に読むべき資料

```text
docs/phase_reports/phase7_final_summary_and_phase8_handoff.md
docs/phase_reports/phase7g_final_integrated_backtest.md
docs/phase_reports/phase7g_user_performance_report.md
docs/phase_reports/phase7g_user_symbol_analysis_report.md
docs/03_ai_design/capital_allocation_phase7_policy_design.md
docs/02_architecture/broker_integration_design.md
docs/02_architecture/safety_guard_design.md
docs/01_requirements/phase_roadmap.md
```

## 13. Audit

Phase7 final audit。

| item | value |
| --- | --- |
| phase7_completion_status | PHASE7_COMPLETED_WITH_VALIDATED_CAPITAL_ALLOCATION_POLICY |
| primary_policy | CAP5 |
| broker_api_executed | false |
| paper_trading_executed | false |
| order_executed | false |
| live_order_executed | false |
| tachibana_api_called | false |
| jquants_api_called | false |
| final_report_created | true |
| phase8_start_recommendation | Broker Read-only Sync + Paper Trading, no live order |

## 14. Final Summary

```text
Phase7 Final Status:
PHASE7_COMPLETED_WITH_VALIDATED_CAPITAL_ALLOCATION_POLICY

Primary Policy:
CAP5

Phase8 Start Recommendation:
Broker Read-only Sync + Paper Trading, no live order
```

