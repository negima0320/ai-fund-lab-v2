# Phase5 Final Handoff for Phase6

## 1. Executive Summary

Phase5 の目的は、Phase4 Candidate AI が抽出した Candidate Top50 を入力として、20 営業日期待値が高い順に銘柄を順位付けする Opportunity AI を設計・実装・評価することだった。

最終判定:

```text
PHASE5_COMPLETE_WITH_DOCUMENTED_DESIGN_DEVIATIONS
```

Phase5 は完了扱いとする。ただし「Opportunity AI 設計書の全 feature family を完全接続した」という意味ではない。Phase5 v1 は、Candidate Top50 の期待値順位付けという core responsibility を満たし、leakage / safety / full-history validation / final schema の監査を通過した。一方で Fundamental、TOPIX / market trend、sector strength、raw high/low/range/trading value には設計との差分が残る。

Promotion 状態:

```text
promotion_ready=false
promotion_performed=false
reader_switch_performed=false
```

Phase5 では実売買、Paper Trading、Broker API、発注、資金配分、promotion、reader switch は行っていない。

## 2. Opportunity AIとは何か

Opportunity AI は「買う / 買わないを最終決定する AI」ではない。Phase5 における Opportunity AI は、Candidate Top50 の中で 20 営業日期待値が高い順に並べる ranking AI である。

Candidate AI との境界:

| Component | Responsibility |
| --- | --- |
| Candidate AI | 全銘柄から上昇候補を抽出し、Candidate Top50 を作る |
| Opportunity AI | Candidate Top50 内で期待値を比較し、`expected_edge_score` と `buy_rank` を付ける |

対象 horizon:

```text
20 business days
```

主要出力:

- `expected_edge_score`
- `buy_rank`
- `expected_return_horizon`
- `downside_risk_score`
- `buy_reason`
- `no_buy_reason`
- `risk_guard_status`
- `calibration_policy_name`

Phase5 は「何銘柄買うか」「いくら買うか」「いつ売るか」を決めない。それらは Phase6 以降の Position Management / Capital Allocation / Broker integration 側の責務である。

## 3. 実装したもの

| Phase | What Was Done | Main Outcome | Important Artifacts |
| --- | --- | --- | --- |
| Phase5-A | Opportunity AI の責務・境界・入出力を設計 | 地雷除去専用ではなく期待値 ranking AI と明確化 | `docs/phase_reports/phase5a_opportunity_ai_design.md` |
| Phase5-B | 20 営業日 label 設計 | `expected_edge_label_20d` と future 系 label の feature 禁止境界を定義 | `docs/phase_reports/phase5b_opportunity_label_design.md` |
| Phase5-C | J-Quants 由来 feature schema 設計 | Candidate / price / volume / momentum / trend / volatility / liquidity / fundamental / market / sector を設計 | `docs/phase_reports/phase5c_opportunity_feature_design.md` |
| Phase5-D | Candidate Top50 -> Opportunity dataset builder | feature / label prefix 分離、split、leakage audit を実装 | `src/ai_fund_lab_v2/opportunity_ai/dataset_builder.py` |
| Phase5-D2 | Historical Candidate Top50 generation | label が存在する過去 target_date の Candidate Top50 を生成 | `reports/opportunity_ai/phase5d2/` |
| Phase5-E | Opportunity model training | 初回 model を学習、warning 付き完了 | `models/opportunity_ai/phase5e/opportunity_model.pkl` |
| Phase5-F | Latest inference | latest Candidate Top50 に inference output を生成 | `reports/opportunity_ai/phase5f/latest_opportunity_inference.parquet` |
| Phase5-G | Quality audit | CandidateTop50 vs OpportunityTopN を検証 | `reports/opportunity_ai/phase5g/` |
| Phase5-H | Combined validation | target_date 単位で Candidate + Opportunity を結合検証 | `reports/opportunity_ai/phase5h/` |
| Phase5-I | Full history expansion | 月次ではなく全 target_date へ拡張 | `reports/opportunity_ai/phase5i/` |
| Phase5-J | Model improvement / calibration | 29 戦略を比較し、simple rule が強いが risk issue ありと判明 | `reports/opportunity_ai/phase5j/` |
| Phase5-K | Policy finalization | final output schema と policy candidates を固定 | `reports/opportunity_ai/phase5k/` |
| Phase5-L | Completion audit | Phase5 完了判定、promotion disabled を確認 | `reports/opportunity_ai/phase5l/` |
| Phase5-M | Design compliance review | 実 feature coverage と既知 gap を整理 | `reports/opportunity_ai/phase5m/` |
| Phase5-N | Design deviation decision record | 設計差分付き完了を正式記録 | `docs/phase_reports/phase5n_design_deviation_decision_record.md` |
| Phase5-O | Random date outcome check | 各年 1 日、合計 5 日で直感的 outcome check | `reports/opportunity_ai/phase5o/` |
| Phase5-O2 | Expanded random outcome check | 各年 10 日、合計 50 日へ拡張 | `reports/opportunity_ai/phase5o2/` |
| Phase5-P | Market / sector feature completion | market / sector feature を追加し v1.1 相当を評価 | `reports/opportunity_ai/phase5p/` |
| Phase5-P2 | Market / sector split impact audit | market_only / sector_only / market_sector の寄与を分離 | `reports/opportunity_ai/phase5p2/` |
| Phase5-R | Ranking quality audit | TopN 平均ではなく ranking AI として評価 | `reports/opportunity_ai/phase5r/` |

## 4. Full History規模

Phase5-I full history expansion の最終規模:

| Item | Value |
| --- | ---: |
| target dates | 1,202 |
| candidate rows | 57,150 |
| opportunity dataset rows | 56,995 |
| train rows | 40,559 |
| validation rows | 12,106 |
| test rows | 4,330 |
| leakage status | OK |
| model score collapse | false |
| model unique score count | 15,540 |

Phase5 は monthly sample だけでは完了扱いにしていない。Full history dataset / training / quality audit / combined validation / calibration / ranking quality audit まで実施済みである。

## 5. 実際に学習したFeature

Phase5 baseline Opportunity model が実際に使った feature は 16 列である。

### Candidate

- `feature__candidate_rank`
- `feature__candidate_reason`
- `feature__candidate_score`

### Momentum

- `feature__price_momentum_return_5d`
- `feature__price_momentum_return_20d`
- `feature__price_momentum_return_60d`
- `feature__volume_momentum_ratio_1d_20d`
- `feature__volume_momentum_ratio_5d`

### Trend

- `feature__trend_close_over_ma_20d`
- `feature__trend_ma_5_20_ratio`
- `feature__trend_ma_20_60_ratio`

### Volatility

- `feature__volatility_return_std_20d`

### Liquidity

- `feature__liquidity_avg_volume_20d`

### Data Quality

- `feature__missing_flags_insufficient_history`
- `feature__missing_flags_price`
- `feature__missing_flags_volume`

Feature audit:

| Item | Value |
| --- | ---: |
| baseline feature count | 16 |
| forbidden feature count | 0 |
| future feature count | 0 |
| trade / backtest / portfolio feature count | 0 |

Phase5-P では追加評価用として market / sector feature を 16 列追加し、合計 32 features の market_sector model も作成した。ただし Phase5 本線の推奨状態は baseline Opportunity AI のまま据え置く。

Market features added in Phase5-P:

- `feature__market_breadth_5d`
- `feature__market_breadth_20d`
- `feature__market_downtrend_flag`
- `feature__market_ma_5_20_ratio`
- `feature__market_return_5d`
- `feature__market_return_20d`
- `feature__market_risk_flag`
- `feature__market_volatility_20d`

Sector features added in Phase5-P:

- `feature__sector_return_5d`
- `feature__sector_return_20d`
- `feature__sector_rank_20d`
- `feature__sector_breadth_20d`
- `feature__stock_vs_sector_return_20d`
- `feature__sector_momentum_flag`
- `feature__sector_weak_flag`
- `feature__market_downtrend_context`

## 6. 設計との差分

Phase5-N の結論は以下。

```text
Phase5 remains complete with documented design deviations.
```

これは「設計通り完全実装」ではない。正確には、Phase5 は「core design compliant with documented deviations」である。

| Feature / Family | Status | Classification | Blocker |
| --- | --- | --- | --- |
| `close` | direct raw feature 未接続、return/trend 派生 feature は使用 | replaced by derived feature | no |
| `volume` | direct raw feature 未接続、volume momentum / avg volume は使用 | replaced by derived feature | no |
| `high` / `low` | 未接続 | future enhancement | no |
| `high_low_range` | 未接続 | future enhancement | no |
| `avg_trading_value_20d` | 未接続 | acceptable implementation gap | no |
| Fundamental | 未接続 | true design deviation | no |
| TOPIX | 未接続 | true design deviation | no |
| market_trend | Phase5-P で proxy feature を追加評価、baseline本線には未採用 | true design deviation reduced, not fully closed | no |
| sector_strength | Phase5-P で proxy feature を追加評価、historical sector master は未接続 | true design deviation reduced, not fully closed | no |

Fundamental 未接続 feature:

- `sales_growth_rate`
- `operating_profit_growth_rate`
- `ordinary_profit_growth_rate`
- `net_income_growth_rate`
- `roe`
- `equity_ratio`
- `operating_margin`

Phase5 completion blocker としなかった理由:

- Candidate Top50 の期待値順位付けという core responsibility は実装・評価済み。
- leakage / forbidden feature / final schema / full-history validation / safety boundary に問題がない。
- Phase5-C は feature design / expansion document であり、列挙した全 feature family の接続を Phase5 完了条件にする明示 gate ではなかった。
- 未接続 feature は成果を無効化するものではなく、Opportunity AI v2 / Phase6 以降の改善 backlog として記録済み。

## 7. Opportunity AI性能評価

### Ranking Quality

Phase5-R の readiness:

```text
RANKING_QUALITY_CONFIRMED
```

Test split の代表値:

| Strategy | Spearman risk-adjusted 20d | NDCG@20 risk-adjusted 20d | Precision@20 future return | Top decile capture@20 | Downside bad top20 |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline Opportunity | 0.008697 | 0.570633 | 0.406322 | 0.095402 | 0.436782 |
| candidate_score baseline | -0.057680 | 0.528635 | 0.375862 | 0.092529 | 0.487931 |
| market_only | 0.001330 | 0.561783 | 0.399425 | 0.105747 | 0.445402 |
| market_sector | -0.052238 | 0.558837 | 0.388506 | 0.105172 | 0.459770 |
| simple_rule_baseline | 0.095720 | 0.601076 | 0.447701 | 0.151149 | 0.485632 |

解釈:

- baseline Opportunity は candidate_score baseline より ranking quality が良い。
- simple_rule は非常に強いが downside_bad が増えるため、そのまま promotion しない。
- market_only / market_sector は random outcome では有効な場面があるが、Full History ranking quality では baseline を明確には超えない。

### 50日 Random Date Outcome Check

Phase5-O2 は `seed=42`、2021〜2025 各年 10 日、合計 50 target dates で実施した。

20 営日での勝ち数:

| Comparison | Win Count | Win Rate |
| --- | ---: | ---: |
| OpportunityBaselineTop5 > CandidateTop50 | 36 / 50 | 0.72 |
| OpportunityBaselineTop5 > CandidateScoreTop5 | 41 / 50 | 0.82 |
| MarketOnlyTop5 > OpportunityBaselineTop5 | 23 / 50 | 0.46 |
| MarketSectorTop5 > OpportunityBaselineTop5 | 30 / 50 | 0.60 |

50 日平均の `mean_return_20bd`:

| Selection Group | mean_return_20bd |
| --- | ---: |
| CandidateTop50 | -0.006112 |
| CandidateScoreTop5 | -0.028349 |
| OpportunityBaselineTop5 | 0.072080 |
| MarketOnlyTop5 | 0.065313 |
| MarketSectorTop5 | 0.077971 |

2022 型失敗日:

| Item | Value |
| --- | ---: |
| failure_2022_like_count | 7 |
| down_regime_proxy_failure_overlap_count | 7 |

### Full History Validation / Calibration

Phase5-I full history:

| Metric | Status |
| --- | --- |
| Top5 lift | MIXED |
| Top10 lift | MIXED |
| Top20 lift | CONFIRMED |
| Top10 underperformance | PERSISTENT_BUT_INVESTIGATED |

Phase5-J calibration:

- 29 strategy candidates were compared.
- recommended policy candidate: `simple_rule_top5`
- `simple_rule_top5` test mean future return 20d: `0.143511`
- `simple_rule_top5` test lift vs CandidateTop50: `0.097664`
- downside_bad delta vs CandidateTop50: `0.075134`
- Result: strong return, but risk guard required; no promotion.

## 8. 重要な発見

### Candidate AI

Candidate AI の候補抽出能力は十分高い。Phase4 の知見どおり、future_max_return_20d 型の上昇候補捕捉に強い。一方で Candidate score 単体では、Best / Worst、downside risk、期待値の細かな順位付けを分離しきれない。

### Opportunity AI

Candidate score より良い順位付けが可能である。Phase5-R では baseline Opportunity が candidate_score baseline を ranking quality で上回った。Phase5-O2 でも OpportunityBaselineTop5 は CandidateTop50 平均に 36/50 日、CandidateScoreTop5 に 41/50 日で勝った。

### simple_rule

simple_rule 系は非常に強い。特に `simple_rule_top5` は test return が高い。ただし downside_bad_rate が悪化するため、そのまま promotion してはいけない。risk guard 付き候補として扱う。

### Top6-10 Tail Dilution

Top6-10 tail dilution は確認済み。fixed Top10 は品質を薄める傾向がある。Phase6 で Top10 を使う場合も「10 銘柄固定で買う」ではなく、score gap / risk guard / variable count の入力情報として扱うべき。

### Market / Sector

Market / sector feature は失敗日改善には有効だった。Phase5-P では `2022-01-13` の OpportunityTop5 mean return 20bd が baseline `-0.144510` から market_sector `-0.079166` へ改善した。

一方で Full History test の Top5 / Top10 / Top20 mean_return_20d では baseline を明確に超えず、Phase5-R ranking quality でも baseline 超えは確認できなかった。したがって Phase5 本線は baseline Opportunity AI、market_only / market_sector は採用保留とする。

### Sector

Sector feature は `2026-06-01` listed issue master snapshot proxy を使っている。

```text
sector_master_snapshot_proxy_warning=true
```

historical sector master が未接続なので、sector feature の評価結果は注意して扱う。Phase6 以降で sector を使うなら、as_of_date 管理された historical sector master 接続を優先する。

## 9. 現時点の推奨状態

Phase5本線:

```text
baseline Opportunity AI
```

採用保留:

- `market_only`
- `market_sector`

改善候補:

- `simple_rule + risk guard`
- `risk_adjusted_model`
- `simple_rule_blend_model`
- variable Top10 / gap threshold policy

理由:

- baseline Opportunity は candidate_score baseline より ranking quality が良い。
- market / sector は一部失敗日改善には効くが、Full History ranking quality で baseline を安定的に超えていない。
- simple_rule は return が強いが downside_bad 増加があるため、risk guard なしでは危険。

## 10. Phase6へ渡すべき前提

Phase6 で最も重要な注意:

```text
Opportunity AI is a ranking AI, not a buy-count / allocation / order AI.
```

Phase6 では「何銘柄買うか」を Opportunity AI 単体の責務として決めないこと。Opportunity AI の出力は、Position Management AI / Capital Allocation Engine が判断するための ranking signal / risk signal として扱う。

Phase6 が使うべき Opportunity output:

- `expected_edge_score`
- `buy_rank`
- `downside_risk_score`
- `risk_guard_status`
- `calibration_policy_name`
- `buy_reason`
- `no_buy_reason`

Phase6 で避けるべき誤解:

- `is_top5=true` は「必ず買う」ではない。
- `buy_rank <= 10` は「10 銘柄固定で買う」ではない。
- Opportunity AI は売却判断をしない。
- Opportunity AI は購入金額・株数・資金配分を決めない。
- Phase5 の metrics は portfolio return ではない。

## 11. 未解決課題

### High Priority

1. Fundamental feature connection
   - `sales_growth_rate`
   - `operating_profit_growth_rate`
   - `ordinary_profit_growth_rate`
   - `net_income_growth_rate`
   - `roe`
   - `equity_ratio`
   - `operating_margin`
   - J-Quants fins の `disclosure_date <= as_of_date` 管理が必要。

2. Market trend improvement
   - TOPIXそのもの、または J-Quants universe proxy の as_of_date 管理を強化する。
   - down-regime proxy 日での OpportunityTop5 の一括悪化を抑える。

3. Sector strength improvement
   - historical sector master を接続する。
   - `sector_master_snapshot_proxy_warning=true` を解消する。

### Medium Priority

4. Top6-10 tail dilution mitigation
   - fixed Top10 ではなく、score gap / risk guard / variable count を検討する。
   - Phase6 の buy-count decision と混同しない。

5. Risk guard design
   - simple_rule_top5 を使う場合は downside_bad 抑制条件を必須にする。
   - `downside_risk_score` / `risk_guard_status` の説明性を高める。

### Low Priority

6. Raw OHLCV / range / trading value expansion
   - `high`
   - `low`
   - `high_low_range`
   - `avg_trading_value_20d`
   - direct `close` / `volume`
   - 既に return / trend / volume momentum / avg volume があるため優先度は Fundamental / Market / Sector より低い。

## 12. Phase6開始時に読むべき資料

最重要:

1. `docs/phase_reports/phase5_final_handoff_for_phase6.md`
2. `docs/phase_reports/phase5r_opportunity_ranking_quality_audit.md`
3. `docs/phase_reports/phase5n_design_deviation_decision_record.md`
4. `docs/03_ai_design/opportunity_ai_design.md`

次に読む:

5. `docs/phase_reports/phase5k_policy_finalization.md`
6. `docs/phase_reports/phase5o2_expanded_random_date_outcome_check.md`
7. `docs/phase_reports/phase5p2_market_sector_split_impact_audit.md`
8. `docs/phase_reports/phase5i_full_history_expansion.md`

詳細確認用:

9. `docs/phase_reports/phase5b_opportunity_label_design.md`
10. `docs/phase_reports/phase5c_opportunity_feature_design.md`
11. `docs/phase_reports/phase5m_design_compliance_review.md`
12. `docs/phase_reports/phase5l_completion_audit.md`

## 13. Source Artifacts

Key artifacts for Phase6:

- `reports/opportunity_ai/phase5i/full_history_opportunity_dataset.parquet`
- `reports/opportunity_ai/phase5i/models/opportunity_model.pkl`
- `reports/opportunity_ai/phase5r/ranking_quality_metrics.json`
- `reports/opportunity_ai/phase5r/ranking_quality_by_strategy.csv`
- `reports/opportunity_ai/phase5r/rank_bucket_analysis.csv`
- `reports/opportunity_ai/phase5o2/random_date_outcome_check_50days.json`
- `reports/opportunity_ai/phase5o2/random_date_outcome_by_year.csv`
- `reports/opportunity_ai/phase5p2/split_impact_metrics.json`
- `reports/opportunity_ai/phase5n/design_deviation_decision_record.json`

## 14. Final Handoff Statement

Phase5 は、Candidate Top50 内の 20 営業日期待値 ranking AI として Opportunity AI を実装し、full history validation、ranking quality audit、random date outcome check、design compliance review、design deviation decision record まで完了した。

Phase5 の成功:

- Candidate score より良い ranking quality を確認した。
- CandidateTop50 から Top5 へ絞ることで、50 日 random outcome check では 20 営業日平均で明確な改善を確認した。
- Feature / label separation と leakage audit を維持した。
- Promotion disabled のまま安全に完了した。

Phase5 の失敗または限界:

- Top5 / Top10 lift は full history で MIXED。
- fixed Top10 は tail dilution がある。
- simple_rule は強いが downside_bad が悪化する。
- Fundamental / TOPIX / historical sector master は未接続。
- market / sector feature は失敗日改善に効くが、baseline ranking quality を安定的には超えていない。

Phase6 は、この Opportunity ranking output を「買い数・資金配分・保有判断の入力」として扱うこと。Opportunity AI 単体に実運用判断を背負わせないこと。
