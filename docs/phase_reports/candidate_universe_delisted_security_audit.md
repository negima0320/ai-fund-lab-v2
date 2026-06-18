# Candidate Universe Delisted Security Audit

## 結論

```text
BUG
```

2026-06-17 Blog ReportのCandidate Top50 / Opportunity Top5に出現した`1400 名称未取得`は、J-Quants listed_info最新スナップショットに存在しない。

ローカルJ-Quants canonical daily quotesには`14000`として過去価格が残っているが、最終価格日は`2023-12-29`であり、2026-06-16時点の売買候補に入れてはいけない。

## 監査対象

対象実行:

```text
decision_for: 2026-06-16
blog execution_date: 2026-06-17
```

主な入力:

```text
.runtime/data/raw/jquants/listed_issues/data.parquet
.runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet
.runtime/phase9/features/2026-06-16/candidate_features.parquet
.runtime/phase9/features/2026-06-16/opportunity_feature_input.parquet
.runtime/phase9/inference/2026-06-16/candidate_artifact.json
.runtime/phase9/inference/2026-06-16/opportunity_artifact.json
```

監査JSON:

```text
.runtime/phase9/audits/candidate_universe_delisted_security_audit.json
```

## 1400確認

J-Quants listed_info:

```text
latest target_date: 2026-06-17
latest listed rows: 4,446
14000 listed rows: 0
14000 in latest listed master: false
```

Canonical daily quotes:

```text
code: 14000
display code: 1400
rows: 627
first date: 2021-06-14
last date: 2023-12-29
```

Feature / artifact:

```text
candidate_features row: 1
universe_eligible: true
feature data_end_date: 2023-12-29
Candidate Top50 rank: 2
Opportunity Top20 rank: 2
Opportunity Top5 rank: 2
```

判定:

```text
1400 is not current-listed in local J-Quants listed_info as of 2026-06-17.
1400 has stale canonical prices ending at 2023-12-29.
Candidate Universe is incorrectly allowing the stale historical code.
```

厳密には、listed_infoだけでは「上場廃止日」そのものは保持していない。しかし、最新listed masterに存在せず、2023-12-29以降の価格もないため、Paper Tradingの買付候補としては上場廃止または非現行銘柄として除外すべき。

## 混入状況

### Candidate Top50

```text
total: 50
名称未取得: 1
現行listed_info未一致: 1
普通株/株式相当: 39
ETF: 9
ETN: 1
REIT: 0
```

名称未取得:

```text
rank 2: 1400 / canonical code 14000 / score 100 / listed_info未一致
```

ETF / ETN:

```text
ETF: 9 / 50 = 18%
ETN: 1 / 50 = 2%
ETF+ETN: 10 / 50 = 20%
```

### Opportunity Top20

```text
total: 20
名称未取得: 1
現行listed_info未一致: 1
普通株/株式相当: 9
ETF: 9
ETN: 1
REIT: 0
```

ETF / ETN:

```text
ETF: 9 / 20 = 45%
ETN: 1 / 20 = 5%
ETF+ETN: 10 / 20 = 50%
```

### Opportunity Top5

```text
total: 5
名称未取得: 1
現行listed_info未一致: 1
普通株/株式相当: 0
ETF: 4
ETN: 0
REIT: 0
```

Top5内訳:

```text
rank 1: 1365 ETF
rank 2: 1400 listed_info未一致 / 名称未取得
rank 3: 1458 ETF
rank 4: 1570 ETF
rank 5: 1579 ETF
```

ETF比率:

```text
ETF: 4 / 5 = 80%
listed_info未一致: 1 / 5 = 20%
普通株: 0 / 5 = 0%
```

## Universe件数

2026-06-16の`candidate_features.parquet`で`universe_eligible == true`の行を集計した。

```text
eligible universe total: 4,780
普通株/株式相当: 3,734
ETF: 382
ETN: 32
REIT: 87
上場廃止または非現行listed_info未一致: 525
名称未取得: 525
other: 20
target_dateより古い最終価格: 581
```

補足:

- `名称未取得`は今回の監査では全件が最新listed_info未一致と一致した。
- `target_dateより古い最終価格`は、`data_end_date < 2026-06-16`のUniverse eligible行。
- `other`は主に`ProdCat=023`のうち、名称文字列からETN判定できなかった外国籍ETF/商品系上場商品など。

## 原因

Candidate feature refreshはlisted_infoを読み込んではいるが、Universe構築には使っていない。

該当箇所:

```text
src/ai_fund_lab_v2/paper_trading/feature_refresh.py
```

監査上の問題点:

```text
listed_info is loaded only for row count / source refs.
candidate feature frame is built from quotes only.
```

コード上の流れ:

```text
feature_refresh.py:272-275
listedを読む
candidate = _build_candidate_feature_frame(quotes=quotes, ...)
```

`_build_candidate_feature_frame`はquotesから`date/code/close/volume`だけを渡している。

```text
feature_refresh.py:322-337
source_rows = quotes target_date/code/Close/Volume
build_candidate_features_mock_with_audit(...)
```

Candidate feature builder側では、各コードの過去visible rowsを集め、行数がlookbackを満たせばeligibleにしている。

```text
candidate_ai/feature_builder.py:73-87
as_of_date以前の価格をcodeごとにgroup

candidate_ai/feature_builder.py:100-114
eligible = len(visible_rows) >= MIN_LOOKBACK_ROWS
```

このため、2023-12-29で価格が止まった`14000`でも、十分な過去行数があるため`universe_eligible=true`になる。

さらにdaily inferenceは`universe_eligible`だけを見て候補化している。

```text
daily_inference_runner.py:296-297
frame = frame[frame["universe_eligible"].astype(bool)]
```

artifactの`issue_name`は空文字で出力される。

```text
daily_inference_runner.py:309-312
issue_name: ""
```

Blog Report側は後段でlisted_infoから名称補完するが、14000は最新listed_infoに存在しないため`名称未取得`になる。

```text
blog_report_v2_writer.py:775-783
name_mapで引けなければ "名称未取得"
```

## Candidate Universe母集団の現状

現在の母集団は実質的に以下。

```text
canonical normalized daily quotesに存在し、
as_of_date以前に十分な価格履歴があるコード
```

不足している条件:

```text
latest listed_infoに存在すること
銘柄名が取得できること
data_end_dateがtarget_dateと一致すること
Product Categoryが許可対象であること
```

そのため、上場廃止または非現行銘柄、ETF、ETN、REITが混入する。

## 修正案

### 必須

Candidate Universeに以下のhard gateを入れる。

```text
current_listed_only:
  listed_info latest snapshotに存在するCodeのみ許可

fresh_price_only:
  data_end_date == target_data_until のCodeのみ許可

name_required:
  CoNameが空でないCodeのみ許可
```

これにより、1400のような古い価格履歴だけの銘柄はCandidate / Opportunityへ進めなくなる。

### 推奨

プロジェクト目的が「日本株AI運用システム」で、現物のみかつ個別株運用を意図しているなら、当面は普通株に絞る。

推奨Universe:

```text
ProdCat in {011, 021}
MktNm in {プライム, スタンダード, グロース}
TOKYO PRO MARKETは除外候補
ProdCat 012は別扱いで原則除外
ProdCat 013 REIT除外
ProdCat 014 ETF除外
ProdCat 023 ETN/外国籍ETF/商品系上場商品除外
```

ただし、ETF戦略を明示的に持つなら別Universeとして分離する。

```text
ordinary_stock_universe
etf_universe
reit_universe
etn_universe
```

Candidate AIの同一ランキング内で普通株・ETF・ETNを混ぜるのは、ボラティリティ、制度、リスク、板特性、投資対象が異なるため非推奨。

### Blog側

Blog Reportは表示層なので、根本修正場所ではない。

ただし防御的には以下を出してよい。

```text
名称未取得またはlisted_info未一致の候補が存在した場合、公開レポート生成前に警告またはBLOCK
```

## 優先度

```text
High
```

理由:

- 売買不能な非現行銘柄がOpportunity Top5に入っている。
- Top5で普通株が0件、ETFが4件、非現行が1件になっている。
- AI性能以前に候補母集団の品質が崩れている。
- Paper Tradingの発注候補品質と30営業日検証の妥当性に直接影響する。

## 推奨判定

```text
BUG
```

最小修正は以下。

```text
Candidate feature refresh時点で、
latest listed_infoに存在しないCode、
CoNameが空のCode、
data_end_date < target_data_until のCodeを universe_eligible=false にする。
```

運用目的に合わせた推奨修正は以下。

```text
普通株Universeを明示定義し、ETF/ETN/REITを初期状態では除外する。
```

## 実行した軽量監査

重いバックテスト、再学習、実売買API、OpenD起動は実行していない。

実行内容:

```text
J-Quants listed_info parquet確認
canonical daily quotes parquet確認
candidate_features parquet確認
opportunity_feature_input parquet確認
candidate_artifact / opportunity_artifact JSON確認
Universe分類集計
```

