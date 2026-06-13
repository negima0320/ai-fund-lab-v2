# Phase4 Candidate AI Final Summary

作成日: 2026-06-14

## 1. Phase4の目的

Phase4 Candidate AI vNext の目的は、全銘柄から「見る価値があるモメンタム投資候補」を50銘柄程度に抽出することです。

Candidate AIは候補発掘AIであり、売買判断AIではありません。買うかどうか、売るかどうか、保有するか、資金をいくら配分するか、発注するかはPhase4の責務外です。これらはPhase5 Opportunity AI、Phase6 Position Management AI、Phase7 Capital Allocation、Phase8 Order Manager以降の責務です。

## 2. Phase4で実施したこと

- raw J-Quants daily quotes取得
- long history raw coverage audit
- isolated real_runtime normalized rebuild
- historical feature regeneration
- label regeneration
- dataset rebuild
- formal LightGBM training
- formal candidate inference
- candidate quality audit
- random date win-rate audit
- robustness test
- winner/loser case study
- momentum capture audit
- score/top10/regime proxy audit

Phase4後半では、2021-06-14から2026-06-12までのlong historyを使い、正式なTrain / Validation / Test splitに基づくCandidate AI検証まで到達しました。

## 3. 途中で発生した課題

- 60営業日history不足により、smoke training時のfeatureがnullまたはconstantに近い状態になった。
- その結果、LightGBMがone-leaf modelになり、Candidate scoreが全銘柄でほぼ同一になった。
- 当初のfetch計画が2021-03-09開始になっており、J-Quants daily quotes取得可能期間外を含んでHTTP400を発生させた。
- 2021-06-01から2021-06-11の境界日ではHTTP400が残り、最終的な有効取得開始日は2021-06-14になった。
- 事前検証とdry-runを細かく刻んだため、安全性は高まった一方、Phase4全体の進行は重くなった。
- Candidate score単体では、Winner / Loserを十分に分離できなかった。
- Candidate Top50は上昇候補を拾う一方、downside_bad_rateも高めだった。
- down regimeでは候補品質が大きく悪化した。

## 4. 解決したこと

- long history raw daily quotesを再取得し、2021-06-14から2026-06-12の実データ履歴を構築した。
- isolated real_runtime normalizedを再構築し、mock pathとは分離した。
- historical feature tableを再生成し、training期間のnull/constant問題を解消した。
- label tableをfeature tableとは物理的に分離して再生成した。
- feature tableとlabel tableをtarget_date + codeで結合し、正式datasetを構築した。
- leakage audit、feature quality gate、responsibility boundaryを各段階で確認した。
- Phase4-BIからBMで、勝率、robustness、winner/loser、momentum capture、score順位、regime proxyの追加検証を行った。

主要な再構築結果:

- normalized row count: 5,066,399
- feature row count: 5,066,399
- label row count: 4,970,227
- dataset row count: 4,970,227
- feature column count: 13
- label column count: 8

## 5. 主要成果

### Formal Training

- model_type: LightGBM
- dataset_row_count: 4,970,227
- train_row_count: 3,581,207
- validation_row_count: 1,022,775
- test_row_count: 366,245
- validation AUC: 0.658141
- test AUC: 0.681583
- validation precision@50: 0.28
- test precision@50: 0.14
- all_same_score: false
- effective_split_count: 4,800
- feature_importance_nonzero_count: 10

### Formal Inference

- target_date: 2026-06-12
- input_feature_row_count: 4,212
- eligible_input_count: 4,164
- scored_count: 4,164
- candidate_count: 50
- candidate_score min/max/mean/std: 0.05275475 / 0.77225751 / 0.49145138 / 0.14799808
- unique_candidate_score_count: 4,164
- ranking_effective: true

### Candidate Quality Audit

- candidate_quality_pass: true
- readiness_status: PHASE4_COMPLETE_WITH_IMPROVEMENT_OPPORTUNITIES
- validation_top50_top_decile_rate: 0.28
- test_top50_top_decile_rate: 0.22
- validation_top50_mean_future_max_return_20d: 0.214404
- test_top50_mean_future_max_return_20d: 0.149494
- main weakness: top50_downside_bad_rate_is_worse_than_market

### Robustness Test

- sampled_date_count: 50
- total_candidate_count_top50: 2,500
- Top50 win_rate_5d / 10d / 20d: 0.4100 / 0.4336 / 0.4156
- Top50 avg_future_max_return_20d: 0.137238
- Top50 top_decile_rate_20d: 0.243690
- Top50 downside_bad_rate_20d: 0.470522
- 20d win rateは市場平均を下回ったが、future_max_returnとtop_decile_rateは候補抽出として有効性を示した。

### Momentum Capture Audit

- CandidateTop50 vs FutureReturnTop50 capture_count: 157
- CandidateTop50 vs FutureReturnTop50 capture_rate: 0.0628
- random_capture_rate: 0.0128
- enrichment_vs_random: 4.90625
- CandidateTop50 vs FutureMaxTop50 capture_count: 180
- CandidateTop50 vs FutureMaxTop50 capture_rate: 0.0720
- random_capture_rate: 0.0096
- enrichment_vs_random: 7.5
- momentum_capture_pass: true

### Score / Top10 / Regime Proxy Audit

- CandidateTop50 vs FutureReturnTop10 capture_rate: 0.076
- random_future_return_top10_capture_rate: 0.010
- enrichment_vs_random_future_return_top10: 7.6
- CandidateTop50 vs FutureMaxTop10 capture_rate: 0.072
- random_future_max_top10_capture_rate: 0.014
- enrichment_vs_random_future_max_top10: 5.142857
- score_rank_monotonicity_status: PARTIAL
- score_future_return_correlation: -0.099365
- score_future_max_return_correlation: 0.212481
- score_downside_bad_correlation: 0.295943

Regime proxyでは、up regimeで品質が改善し、down regimeで大きく悪化しました。これはPhase5で相場環境別の絞り込みや閾値調整が必要であることを示します。

## 6. Phase4で分かったこと

Candidate AIは「勝率を上げるAI」ではなく、「20営業日以内に大きく吹く可能性がある銘柄を広く拾うAI」です。

有効だった点:

- 未来の上位銘柄をランダムより高い確率で捕捉できる。
- future_max_return_20dの捕捉が特に強い。
- 最新推論では4,000銘柄超からTop50を安定して生成できる。
- scoreは全同一ではなく、ランキングとして機能している。

限界:

- Candidate scoreをそのまま買い順位として使うのは危険。
- Best / Worstの平均Candidate score差はほぼなく、score単体では大当たりと大ハズレを分けきれない。
- upside候補と同時にdrawdownリスクが高い候補も拾う。
- down regimeではwin rate、return、downside_bad_rateが悪化する。

結論として、Phase4 Candidate AIは候補抽出器として成立しました。ただし実運用可能な買い判断には、Phase5 Opportunity AIによる地雷除去、持続性確認、entry timing確認が必要です。

## 7. Phase4最終判定

- Phase4 final status: SUCCESS
- final_readiness_status: PHASE4_COMPLETE_WITH_IMPROVEMENT_OPPORTUNITIES
- purpose_achieved: true
- Candidate AI role: candidate extraction only

Phase4の目的である「全銘柄からモメンタム候補50銘柄を抽出するAI」は成立しました。

ただしPhase4はbacktestではなく、売買戦略でもありません。annual return、final assets、portfolio drawdown、約定、手数料、資金配分は評価対象外です。Phase4の成果をそのまま売買に接続してはいけません。

## 8. 禁止事項遵守

以下はPhase4最終資料作成時点で未実行です。

- backtest
- trading
- Paper Trading
- Broker API
- order execution
- promotion
- reader switch
- Portfolio自動更新

future/label dataは評価フェーズでのみ使用し、candidate選定時には使用していません。leakage audit statusはOKです。

## 9. Phase5への引き継ぎ要点

Phase5 Opportunity AIでは、Candidate Top50を買い候補へ直接変換するのではなく、さらに絞り込みます。

重要な設計方針:

- Candidate scoreはpriorとして扱い、買い判断には直接使わない。
- downside_badとdrawdown riskを強く抑制する。
- 一時的な吹き上げと持続上昇を区別する。
- price momentum 60d / 20d / 5d、liquidity、trend系は加点候補にする。
- 短期volume surgeは単純加点しない。
- up / flat / down regimeに応じて閾値や候補数を変える。
- down regimeでは特に強く絞る。
- Opportunity AIは「地雷除去AI」として設計する。

## 10. 推奨するPhase5計画

1. Phase5-A: Opportunity AI Design Document
2. Phase5-B: Downside / Drawdown Label Design
3. Phase5-C: Opportunity Feature Expansion
4. Phase5-D: Candidate Top50 to Opportunity TopN Dataset
5. Phase5-E: Opportunity AI Training
6. Phase5-F: Opportunity Quality Audit
7. Phase5-G: Candidate + Opportunity Combined Validation

## 11. 参照した主な資料

- docs/phase_reports/phase4_completion_summary.md
- docs/phase_reports/phase4bh_formal_candidate_quality_audit.md
- docs/phase_reports/phase4bi_random_date_candidate_winrate_audit.md
- docs/phase_reports/phase4bj_candidate_robustness_audit.md
- docs/phase_reports/phase4bk_winner_loser_case_study.md
- docs/phase_reports/phase4bl_momentum_capture_audit.md
- docs/phase_reports/phase4bm_score_top10_regime_audit.md
- reports/candidate_ai/full_range/phase4bf_formal_lightgbm_training_summary.json
- reports/candidate_ai/full_range/phase4bg_formal_candidate_inference_summary.json
- reports/candidate_ai/full_range/phase4bh_formal_candidate_quality_summary.json
- reports/candidate_ai/final_check/phase4bi_random_date_candidate_winrate_summary.json
- reports/candidate_ai/final_check/phase4bj_candidate_robustness_summary.json
- reports/candidate_ai/final_check/phase4bk_winner_loser_cases_summary.json
- reports/candidate_ai/final_check/phase4bl_momentum_capture_summary.json
- reports/candidate_ai/final_check/phase4bm_score_top10_regime_summary.json
