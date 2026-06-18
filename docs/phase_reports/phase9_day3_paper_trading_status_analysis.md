# Phase9 Day3 Paper Trading Status Analysis

作成日: 2026-06-18

対象:

```text
Phase9 30営業日Paper Trading検証
Day3付近の状況解析
```

この解析は既存ログ・既存レポート・既存artifactの読み取りのみで実施した。Broker注文、OpenD起動、unlock_trade、実売買、virtual fill、AI再学習、推論、OrderPlan生成、scheduler変更、ledger変更、tracker変更は行っていない。

## Summary

総評:

```text
注意
```

Paper Tradingの運用基盤は動いている。Ledger、Tracker、Blog Report、Operation Log、禁止フラグはいずれも確認できる。一方で、AI判断品質にはまだ明確な注意点が残る。

最大の懸念:

```text
Candidate / Opportunity raw scoreが最新Dayでも全件100に張り付いている。
```

Day1で見つかったscore saturationは、2026-06-16 decision_forの最新inference artifactでも解消していない。公開レポート側では順位ベースの補助スコアで`100, 99, 98...`のように見えるが、元artifactのraw scoreはCandidate Top50 / Opportunity Top20 / public_confidence_scoreすべて`100.0`である。

Day2で確認された主なバグ:

1. 2026-06-17 runが2026-06-17終値ではなく、2026-06-16価格でvaluationしていた。
2. Candidate Universeが古い価格履歴だけを見ており、最新listed_infoに存在しない`1400`を候補に入れていた。

Day3時点の影響:

- Ledger valuation bugはrecoveryにより2026-06-17終値へ更新済み。
- Candidate Universe hard gateにより`1400`は除外済み。
- ただしscore saturationは継続。
- 3063の高値掴み影響は残っており、保有5銘柄の中で唯一大きくマイナス。

保存済みTrackerは現在`2/30`であり、Day3の正式entryはまだ存在しない。したがって本レポートは、2026-06-17 recovery後の最新状態をDay3判断用の直近状態として扱う。

## Performance

基準:

- initial equity: `1,000,000円`
- latest valuation date: `2026-06-17`
- latest ledger: `.runtime/phase9/ledger/latest.json`
- tracker: `.runtime/phase9/tracker/phase9_30bd_tracker.json`

| 指標 | 値 |
| --- | ---: |
| current equity | 998,060円 |
| cumulative pnl | -1,940円 |
| cumulative return | -0.194% |
| realized pnl | 0円 |
| unrealized pnl | -1,940円 |
| cash | 283,330円 |
| market value | 714,730円 |
| positions | 5 |
| pending orders | 0 |
| trade count | 5 |

資産推移:

| 日付 | 状態 | total_equity | 補足 |
| --- | --- | ---: | --- |
| 2026-06-16 | First Virtual Fill直後 | 1,000,000円 | Tracker Day1。約定直後snapshot |
| 2026-06-16 | EOD valuation | 993,140円 | 初日終値評価。評価損益 -6,860円 |
| 2026-06-17 | Recovery後EOD valuation | 998,060円 | Day2 recovery後。評価損益 -1,940円 |

Tracker:

```text
progress: 2/30
pipeline_success_rate: 1.0000
data_readiness_rate: 1.0000
report_generation_rate: 1.0000
ledger_integrity: OK
no_broker_order_violation: OK
```

## Holdings

最新Ledger上の保有銘柄:

| code | name | qty | avg cost | latest price | market value | unrealized pnl | pnl rate | days |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1579 | 日経平均ブル2倍上場投信 | 200 | 846.8 | 859.9 | 171,980円 | +2,620円 | +1.55% | 2 |
| 166A | タスキホールディングス | 100 | 1,091.0 | 1,120.0 | 112,000円 | +2,900円 | +2.66% | 2 |
| 213A | 上場インデックスファンド日経半導体株 | 300 | 544.7 | 550.0 | 165,000円 | +1,590円 | +0.97% | 2 |
| 221A | MAXIS日経半導体株上場投信 | 100 | 1,538.0 | 1,553.5 | 155,350円 | +1,550円 | +1.01% | 2 |
| 3063 | ジェイグループホールディングス | 100 | 1,210.0 | 1,104.0 | 110,400円 | -10,600円 | -8.76% | 2 |

所見:

- 5銘柄中4銘柄は含み益に回復している。
- 3063のみ大きく含み損で、ポートフォリオ全体の足を引っ張っている。
- 3063はDay1の高値掴み問題が継続している。
- 保有日数は2日であり、Position Managementの短期売却抑制・初期評価期間という観点ではHOLD自体は理解できる。
- ただし3063の下落率は`-8.76%`で、明示的な損切り/危険判定ルールがないままHOLDしている可能性がある。

売却条件への近さ:

- 3063は損切り候補として監視が必要。
- 現状のPosition artifact / Blog Reportでは売却理由や危険度が十分に説明されていない。
- `-8%`超の含み損を「初回購入後の評価期間中」とだけ扱うのは、人間の運用判断には情報が粗い。

## Trades

初回購入:

| code | name | qty | fill date | fill price | amount | status |
| --- | --- | ---: | --- | ---: | ---: | --- |
| 1579 | 日経平均ブル2倍上場投信 | 200 | 2026-06-16 | 846.8 | 169,360円 | FILLED |
| 166A | タスキホールディングス | 100 | 2026-06-16 | 1,091.0 | 109,100円 | FILLED |
| 213A | 上場インデックスファンド日経半導体株 | 300 | 2026-06-16 | 544.7 | 163,410円 | FILLED |
| 221A | MAXIS日経半導体株上場投信 | 100 | 2026-06-16 | 1,538.0 | 153,800円 | FILLED |
| 3063 | ジェイグループホールディングス | 100 | 2026-06-16 | 1,210.0 | 121,000円 | FILLED |

直近Dayの売買:

```text
new buy: 0
sell: 0
pending orders: 0
```

売却なしの理由:

- Operation log上、virtual fillは`NO_DUE_PENDING_ORDERS`。
- Position Managementは保有継続寄りで、売却orderは作成されていない。
- 現在は5銘柄保有済みで、CAP5上限により新規購入余地がない。

売らなくてよかったか:

- 4銘柄は含み益に回復しており、HOLDは妥当。
- 3063は`-8.76%`で、HOLD妥当性は要注意。最低限、損切り閾値・急落判定・高値掴み後の撤退判定が必要。

## AI Decision Quality

### Score Distribution

元artifactのスコア分布:

| decision_for | Candidate score | Candidate unique | Opportunity score | Opportunity unique | public confidence unique |
| --- | --- | ---: | --- | ---: | ---: |
| 2026-06-15 | 100.0 - 100.0 | 1 | 100.0 - 100.0 | 1 | 1 |
| 2026-06-16 | 100.0 - 100.0 | 1 | 100.0 - 100.0 | 1 | 1 |

判定:

```text
SCORE_SATURATION_UNRESOLVED
```

公開Blog Report v4では順位ベースの補助スコアで`100, 99, 98...`と表示されるが、これは表示補正であり、AIのraw score分布が改善したわけではない。

影響:

- rankingの意味が弱い。
- Top5 / Top20が実質的に同点銘柄の並び替えになっている。
- selectionがコード順やフィルタ順に寄る可能性がある。
- public_confidence_scoreも全件100で、読者向け信頼度としては過信を招く。

### Ranking Quality

Day1:

- Candidate Top50の上位にETF/ETNや高額銘柄が混在。
- 上位候補の多くが100株単位・資金制約で買えず、3063が20位から5銘柄目として採用された。

Day2:

- Candidate Universe hard gate後、ETF/ETN/REIT/上場廃止相当・ stale price は除外された。
- 2026-06-16 decision_forのCandidate/Opportunityは普通株中心へ改善。
- ただしscoreはまだ全件100。

最新Top5:

| rank | code | name | note |
| ---: | --- | --- | --- |
| 1 | 166A | タスキホールディングス | 既存保有 |
| 2 | 1948 | 弘電社 | 未保有 |
| 3 | 212A | フィットイージー | 未保有 |
| 4 | 215A | タイミー | 未保有 |
| 5 | 2393 | 日本ケアサプライ | 未保有 |

新規購入がない理由:

- 既に5銘柄保有中。
- 売却がないため、CAP5上限で新規買い枠がない。
- pending orderも0。

## High Chase Audit

初回購入5銘柄について、判断日終値`2026-06-15`、翌営業日始値`2026-06-16`、判断日までの高値比で確認。

| code | name | decision close | fill open | gap | 20d high比 | 60d high比 | 52w high比 | first day return | 判定 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1579 | 日経平均ブル2倍上場投信 | 845.2 | 846.8 | +0.19% | -0.61% | -0.61% | -0.61% | -0.12% | HIGH_CHASE_RISK |
| 166A | タスキHD | 1,099.0 | 1,091.0 | -0.73% | -4.72% | -4.72% | -4.72% | +1.92% | NORMAL |
| 213A | 日経半導体株ETF | 537.9 | 544.7 | +1.26% | +1.26% | +1.26% | +1.26% | -0.40% | HIGH_CHASE_RISK / BREAKOUT_BUY |
| 221A | MAXIS日経半導体株ETF | 1,512.0 | 1,538.0 | +1.72% | +1.72% | +1.72% | +1.72% | -0.52% | HIGH_CHASE_RISK / BREAKOUT_BUY |
| 3063 | ジェイグループHD | 1,199.0 | 1,210.0 | +0.92% | +0.83% | +0.83% | +0.83% | -6.03% | HIGH_CHASE_RISK / BREAKOUT_BUY |

所見:

- 5銘柄中4銘柄が高値圏またはブレイクアウト買い。
- 3063は判断日時点の20日/60日/52週高値を翌営業日始値で上抜けて購入し、その日の終値で大きく反落した。
- 高値追い傾向はDay1購入群に明確に存在する。
- Day2以降は新規購入がないため、傾向が継続しているかはまだ追加検証不可。

## Capital Allocation Audit

Day1の採用構造:

- CAP5
- cash buffer: 5%
- max position weight: 20%
- lot size: 100
- max buy orders: 5

Day1の問題:

- Top20上位に高額ETF/ETNが多く、100株単位では予算超過。
- その結果、AI上位順位よりも「100株単位で買えるか」が強く効いた。
- 3063はOpportunity 20位だが、100株で119,900円と予算内だったため5銘柄目に採用された。

Day2の改善:

- Candidate Universe hard gateにより、ETF/ETN/REITやstale price候補は除外。
- 最新Candidate Top50 / Opportunity Top20はordinary_or_equity_likeのみ。
- `1400`のような非現行銘柄は除外済み。

残課題:

- Score saturationが残っているため、Capital Allocationに渡る順位自体の信頼性が低い。
- 保有5銘柄満杯時の新規買い停止は妥当だが、含み損が大きい銘柄の入れ替え判断が弱い。
- 3063のような高値追い銘柄を買う前に、gap-up / high-chase no-fill policyが必要。

## Day2 Bug Impact

### Bug 1: Ledger Valuation stale source

内容:

- 2026-06-17のunified daily runで、canonical quotes最新日付が2026-06-16のままだった。
- Unified Runnerは`--allow-api-fetch`でもmarket data refreshを実行せず、`API_FETCH_ALLOWED_BUT_NOT_AUTO_EXECUTED_IN_UNIFIED_RUNNER`を出すだけだった。
- そのため、2026-06-17 runで2026-06-16価格を再利用してvaluationしていた。

影響:

- Day2初回runの評価額が2026-06-17終値を反映していなかった。
- 同一valuation_date再実行でholding_daysが進む副作用があった。
- Tracker Day2が一時的に古い評価を記録した可能性がある。

修正/復旧:

- recovery run `recovery_2026_06_17` により、quote_source_max_date `2026-06-17`、valuation_date `2026-06-17`で再評価済み。
- latest ledgerは`total_equity=998,060円`、`stale_price_source=false`へ回復。
- Tracker entry Day2も`UNIFIED_DAILY_RUN_DONE_RECOVERED`として更新されている。

残影響:

- 運用コード上、Unified Runnerがmarket refreshを自動実行しない設計は残課題。
- stale price source時のBLOCK/警告強化が必要。

### Bug 2: Candidate Universe stale / delisted security

内容:

- 2026-06-17 Blog Reportに`1400 名称未取得`が出現。
- `14000`はlatest listed_infoに存在せず、canonical priceも2023-12-29で止まっていた。
- Candidate Universeがlisted_infoではなく価格履歴中心で作られていた。

修正:

- Candidate Universe hard gateを追加。
- 条件:
  - current listed
  - nameあり
  - fresh price
  - allowed product
  - allowed market
- eligible universeは`4,780 -> 3,706`へ減少。
- `1400`はCandidate Top50 / Opportunity Top5から除外。

残影響:

- Blog Report v4 / latest featureでは修正済み。
- ただし、Day1購入済みポジションにはETFが含まれており、Day1時点のUniverse設計の影響は保有に残っている。

## Known Issues

### Day1 Score 100

状態:

```text
未解消
```

2026-06-15、2026-06-16の両方で、Candidate / Opportunity / public confidenceのraw scoreが全件100。

### 3063 High Chase

状態:

```text
影響継続
```

3063は購入後2営業日で`-8.76%`。ポートフォリオ全体はほぼ回復したが、3063の単独損失が大きい。

### Day2 Ledger Valuation Bug

状態:

```text
復旧済み / 再発防止未完
```

Recoveryによりlatest ledgerは2026-06-17終値で更新済み。ただしUnified Runnerのmarket refresh非実行問題は残る。

### Candidate Universe Bug

状態:

```text
修正済み / 監視継続
```

Hard gate後、stale price / listed_info unmatched / disallowed productは0。

## Recommendations

### High

1. Score Saturation Audit

Candidate / Opportunityのraw scoreが全件100になる原因を最優先で調査する。clip前スコア、式の寄与、feature分布、rank tie-breakを保存する。

2. High Chase Penalty / No-Fill Policy

購入予定価格が20日/60日/52週高値の98%以上、または前日終値比gap upが一定以上なら、減点・サイズ縮小・NO_FILL候補にする。

3. Unified Runner Market Refresh Fix

`--allow-api-fetch`時にmarket data refreshを実際に呼ぶか、呼ばないなら`LEDGER_VALUATION_STALE_SOURCE`で明示的にBLOCKする。

### Medium

4. Position Management Risk Exit

3063のように短期で`-8%`超の含み損になった銘柄に、HOLD以外の警告状態を追加する。

5. Affordable Universe Pre-Filter

100株単位で購入不能な銘柄をCandidate/Opportunity段階で別枠扱いにする。特に高額ETF/ETNの混入を避ける。

6. Raw Score Retention

公開用scoreとは別に、内部raw score、clip前score、rank reasonをartifactへ残す。

### Low

7. Blog Report / Daily ReportでKnown Issueを見える化

score_all_same_flag、stale_price_source、high_chase_risk、large_unrealized_lossを人間向けに出す。

8. Trackerにrecovery履歴を明示

Day2のようなrecoveryが入った日は、通常runとrecovery後値の両方が追えるようにする。

## Final Judgment

```text
DAY3_NEEDS_ATTENTION
```

運用基盤:

```text
概ね正常
```

AI判断品質:

```text
注意
```

理由:

- Tracker / Ledger / Report / prohibited flagsは安定しつつある。
- Day2バグは復旧済み。
- Candidate Universe hard gateは効いている。
- しかしscore saturationが未解消。
- 3063の高値掴みと含み損が残る。
- 高値追い・gap-up・損切りの安全装置が不足している。

