# Phase7 Pre-study: Opportunity TopN Persistence Analysis

## 1. Purpose

Phase7 Capital Allocation Engine では Replacement Exit を導入予定である。

その前に、Phase5 Opportunity AI の Top3 / Top5 / Top10 が日次でどの程度継続するのかを定量化する。

本調査は分析のみであり、実装、Broker API接続、Paper Trading、実発注、live order、立花証券API呼び出しは行っていない。

## 2. Read Documents

事前に以下を確認した。

- `docs/phase_reports/phase5_final_handoff_for_phase6.md`
- `docs/phase_reports/phase6_final_summary_and_phase7_handoff.md`

補足:

ユーザー指定の `docs/phase_reports/phase5_final_summary_and_phase6_handoff.md` はリポジトリ上に存在しなかったため、Phase6ハンドオフ内で参照されている `docs/phase_reports/phase5_final_handoff_for_phase6.md` をPhase5最終引き継ぎとして確認した。

## 3. Source Data

使用データ:

- `reports/opportunity_ai/phase5i/full_history_opportunity_dataset.parquet`
- `reports/opportunity_ai/phase5i/models/opportunity_model.pkl`

集計期間:

| item | value |
| --- | ---: |
| start_date | 2021-09-08 |
| end_date | 2026-05-15 |
| target_date_count | 1,143 |
| row_count | 56,995 |
| years | 2021, 2022, 2023, 2024, 2025, 2026 |

注意:

```text
2021-2026のうち、実際に特徴量・ラベル・Opportunity dataset が存在する検証可能期間で集計した。
```

## 4. Method

`full_history_opportunity_dataset.parquet` には日次 `buy_rank` は保存されていない。

そのため、Phase5-I の保存済み Opportunity model を使い、既存の Phase5 scoring logic と同じ前処理で `expected_edge_score` を復元し、日次で降順rankを付け直した。

出力した分析用artifact:

- `reports/phase7_prestudy/opportunity_ranked_daily.parquet`
- `reports/phase7_prestudy/opportunity_top20_daily.csv`
- `reports/phase7_prestudy/persistence_runs.csv`
- `reports/phase7_prestudy/persistence_summary.csv`
- `reports/phase7_prestudy/rank1_rank2_rank3_persistence.csv`
- `reports/phase7_prestudy/replacement_frequency_top3.csv`
- `reports/phase7_prestudy/daily_topn_stability.csv`
- `reports/phase7_prestudy/topn_stability_summary.csv`
- `reports/phase7_prestudy/top3_rank_migration_detail.csv`
- `reports/phase7_prestudy/top3_rank_migration_summary.csv`
- `reports/phase7_prestudy/opportunity_decay_summary.csv`
- `reports/phase7_prestudy/topn_stability_by_year.csv`
- `reports/phase7_prestudy/analysis_summary.json`

Safety boundary:

```text
broker_api_executed: false
paper_trading_executed: false
order_executed: false
live_order_executed: false
tachibana_api_called: false
capital_allocation_executed: false
```

## 5. Definitions

Persistence:

```text
同一銘柄がTopN内に連続して滞在した営業日run長
```

Rank1 / Rank2 / Rank3 Persistence:

```text
同一銘柄が同じrankに連続して滞在した営業日run長
```

Replacement Frequency:

```text
ある日のTop3銘柄が、h営業日後にTop3外へ脱落している割合
```

TopN Stability:

```text
隣接営業日でTopN集合がどれだけ重なるか
例: Day N Top3 = A/B/C, Day N+1 Top3 = A/B/D の場合は 2/3
```

Rank Migration:

```text
Top3選定銘柄が、h営業日後にどのrank bucketへ移動したか
```

Opportunity Decay:

```text
Top3選定後、5bd / 10bd / 20bdでOpportunity順位とscoreがどれだけ低下するか
```

## 6. Top3 Persistence

### Rank1 / Rank2 / Rank3 exact-rank continuation

| rank | run_count | mean_continuation_bd | median | p75 | p90 | max |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 889 | 1.286 | 1.0 | 1.0 | 2.0 | 10 |
| 2 | 991 | 1.153 | 1.0 | 1.0 | 2.0 | 5 |
| 3 | 1,039 | 1.100 | 1.0 | 1.0 | 1.0 | 4 |

Interpretation:

```text
Exact rankは非常に不安定。
Rank1でさえ中央値は1営業日、p90でも2営業日。
```

### Top3 membership persistence

| bucket | run_count | mean_run_length_bd | median | p75 | p90 | max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Top3 | 2,316 | 1.481 | 1.0 | 1.0 | 3.0 | 10 |

Interpretation:

```text
Top3集合として見ても、多くの銘柄は1営業日で入れ替わる。
ただし、まれに10営業日程度Top3内に残る銘柄も存在する。
```

## 7. Top5 Persistence

| bucket | run_count | mean_run_length_bd | median | p75 | p90 | max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Top5 | 3,557 | 1.607 | 1.0 | 2.0 | 3.0 | 17 |

Interpretation:

```text
Top5に広げると平均滞在は少し伸びる。
ただし中央値は1営業日のままで、安定集合とは言いにくい。
```

## 8. Top10 Persistence

| bucket | run_count | mean_run_length_bd | median | p75 | p90 | max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Top10 | 6,458 | 1.770 | 1.0 | 2.0 | 3.0 | 26 |

Interpretation:

```text
Top10に広げると最大滞在は26営業日まで伸びる。
それでも中央値は1営業日で、日次rankはかなり変動する。
```

## 9. Replacement Frequency

Top3銘柄がTop3から脱落する率。

| horizon_bd | checked_events | drop_count | drop_rate |
| ---: | ---: | ---: | ---: |
| 1 | 3,426 | 2,313 | 67.5% |
| 3 | 3,420 | 2,789 | 81.5% |
| 5 | 3,414 | 2,992 | 87.6% |
| 10 | 3,399 | 3,140 | 92.4% |
| 20 | 3,369 | 3,236 | 96.1% |

Interpretation:

```text
単純に「Top3から落ちたらReplace」とすると、翌営業日だけで約67.5%が入れ替え候補になる。
これはPhase7で毎日大量Replacementを発生させる危険がある。
```

## 10. TopN Stability

隣接営業日の平均継続率。

| metric | Top3 | Top5 | Top10 |
| --- | ---: | ---: | ---: |
| mean adjacent continuation rate | 32.5% | 37.8% | 43.5% |

Yearly view:

| year | Top3 | Top5 | Top10 | day_pairs |
| ---: | ---: | ---: | ---: | ---: |
| 2021 | 29.9% | 32.8% | 35.8% | 78 |
| 2022 | 35.0% | 40.7% | 44.2% | 244 |
| 2023 | 36.7% | 38.5% | 40.6% | 246 |
| 2024 | 29.7% | 36.0% | 44.7% | 245 |
| 2025 | 31.1% | 38.4% | 45.3% | 243 |
| 2026 | 27.5% | 35.6% | 48.7% | 86 |

Interpretation:

```text
Top3は日次で平均1銘柄程度しか継続しない。
Top10まで広げても、隣接営業日の継続率は平均43.5%にとどまる。
```

## 11. Rank Migration

Top3選定銘柄が、その後どのbucketへ移動したか。

| horizon_bd | Top3維持 | Top5へ低下 | Top10へ低下 | Top20以下 / Top50外 |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 32.5% | 10.4% | 11.2% | 45.9% |
| 3 | 18.5% | 7.3% | 10.6% | 63.6% |
| 5 | 12.4% | 5.3% | 7.7% | 74.6% |
| 10 | 7.6% | 4.2% | 5.8% | 82.3% |
| 20 | 3.9% | 2.0% | 3.9% | 90.2% |

Interpretation:

```text
Top3維持率は5営業日後で12.4%、20営業日後で3.9%まで低下する。
Top3から落ちた後、Top5 / Top10内に緩やかに残るケースもあるが、多くはTop20以下またはCandidate Top50外へ落ちる。
```

## 12. Opportunity Decay

Top3選定後のrank decay。

`future_rank_candidate_only` は、将来日にもCandidate Top50内に残っている銘柄だけで計算したrankである。

`future_rank_filled_51` は、Candidate Top50外へ消えた銘柄をrank 51相当として扱ったrankである。

| horizon_bd | checked_events | Top50外率 | mean_future_rank_filled_51 | median_future_rank_filled_51 | p75 | p90 | mean_rank_delta_filled_51 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 3,426 | 32.9% | 21.8 | 8.0 | 51.0 | 51.0 | 19.8 |
| 3 | 3,420 | 49.8% | 30.4 | 50.0 | 51.0 | 51.0 | 28.4 |
| 5 | 3,414 | 60.2% | 35.5 | 51.0 | 51.0 | 51.0 | 33.5 |
| 10 | 3,399 | 69.1% | 39.8 | 51.0 | 51.0 | 51.0 | 37.8 |
| 20 | 3,369 | 79.4% | 44.2 | 51.0 | 51.0 | 51.0 | 42.2 |

Score decay, Candidate Top50内に残存したもののみ。

| horizon_bd | mean_score_delta | median_score_delta |
| ---: | ---: | ---: |
| 1 | -0.0163 | -0.0104 |
| 3 | -0.0242 | -0.0186 |
| 5 | -0.0284 | -0.0237 |
| 10 | -0.0335 | -0.0285 |
| 20 | -0.0415 | -0.0363 |

Interpretation:

```text
Top3銘柄のOpportunity順位はかなり速くdecayする。
5営業日後には60.2%がCandidate Top50外になり、中央値rankも51相当になる。
```

## 13. Phase7 Implications

### Replacement Exitは頻繁に発生しそうか

発生しやすい。

```text
Top3から落ちたらReplace
```

という単純ルールでは、翌営業日で約67.5%、5営業日で約87.6%がReplace候補になる。

### 保有寿命はどの程度か

Opportunity rankだけを見ると、Top3滞在寿命の中央値は1営業日である。

ただしPhase6では、

```text
Top3の20bd fixed holdが強い
早売りは利益を壊す可能性がある
```

と確認されている。

したがって、rank寿命と実際の保有寿命を同一視してはいけない。

### 毎日入れ替え型になるのか

閾値なしでは毎日入れ替え型になりやすい。

特に日次Top3の平均継続率は32.5%しかないため、単純なTop3同期型運用は高回転になる。

### HOLD中心になりそうか

Phase6の知見を踏まえると、初期Phase7はHOLD中心にすべきである。

Opportunity順位の低下だけで売ると、Top3 fixed 20bd holdの強さを壊す可能性が高い。

### Replacement Thresholdが必要そうか

必要である。

少なくとも以下が必要。

```text
minimum_holding_days
replacement_rank_degradation_threshold
replacement_edge_margin
new_candidate_score_gap
confirmation_days
risk_guard / downside_risk condition
```

### Top3維持戦略は有効そうか

「Top3に残っている間だけ持つ」という意味では有効とは言いにくい。

理由:

```text
Top3維持率が低すぎる
```

一方で、

```text
Top3で買った銘柄を20bd寄りに持つ
```

という意味では、Phase6-L / Phase6-M の結果から引き続き有力である。

## 14. Recommended Phase7-A Policy Direction

初期Phase7-Aでは、以下を推奨する。

```text
BUY:
Opportunity Top3 primary

HOLD:
minimum holding periodを置く
Top3から1日落ちただけでは売らない

REPLACE:
rank degradationだけではなく、
new Top3とのexpected_edge_score gapと確認日数を要求する

DEFENSIVE:
Phase6 EXIT / REDUCEはreview signal
sell_amountは初期0

EMERGENCY:
-X% ruleのみ機械的full exit候補
```

Replacement候補ルールの初期案。

```text
保有銘柄がTop10外またはTop20以下へ低下
かつ
新規Top3候補のexpected_edge_scoreが明確に高い
かつ
最低保有日数を満たす
かつ
1日だけではなく複数営業日確認する
```

## 15. Limitations

本調査の制限。

```text
Opportunity rankのPersistence調査であり、実売買損益ではない
Broker API / Paper Trading / Capital Allocationは未実行
Top50外の銘柄はrank 51相当として扱った
Phase5 baseline Opportunity modelのrankに基づく
market_only / market_sector / simple_rule policyのPersistenceは未比較
```

## 16. Phase7実装前に分かったこと

1. Opportunity Top3のexact rankは非常に短命で、Rank1でも中央値は1営業日だった。
2. Top3 membershipの平均滞在は1.48営業日、中央値は1営業日だった。
3. Top5 / Top10へ広げても中央値は1営業日で、Opportunity順位は日次で大きく動く。
4. Top3からの翌営業日脱落率は67.5%、5営業日以内脱落率は87.6%だった。
5. 隣接営業日のTop3継続率は平均32.5%で、毎日1銘柄程度しか残らない。
6. Top3銘柄の5営業日後Top3維持率は12.4%、20営業日後は3.9%だった。
7. Top3銘柄の5営業日後Top50外率は60.2%、20営業日後は79.4%だった。
8. 単純なTop3同期Replacementは高回転になり、Phase6で確認したTop3 fixed holdの強さを壊す可能性が高い。
9. Phase7にはReplacement Threshold、minimum holding days、score gap、confirmation daysが必要である。
10. 初期Phase7は日次入れ替え型ではなく、HOLD中心 + 強いReplacement条件 + Emergencyのみ機械的exit、という設計が自然である。
