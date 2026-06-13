# Phase4 Candidate AI to Phase5 Opportunity AI Handoff

作成日: 2026-06-14

## 1. 引き継ぎ目的

この資料は、Phase4 Candidate AIの成果をPhase5 Opportunity AIへ引き継ぐための設計メモです。

Phase4で作ったCandidate AIは、全銘柄から「見る価値がある上昇候補」をTop50として抽出します。Phase5では、このTop50をそのまま買うのではなく、Opportunity AIでさらに絞り込みます。

## 2. Phase4の最終結論

- Phase4 final status: SUCCESS
- final_readiness_status: PHASE4_COMPLETE_WITH_IMPROVEMENT_OPPORTUNITIES
- Candidate AIは候補抽出器として成立した。
- FutureTop50 / FutureTop10の捕捉率はrandom baselineを大きく上回った。
- ただしCandidate score単体ではBest / Worstを分離しきれない。
- downside_bad_rateが高く、down regimeでは品質が悪化する。

Phase5は、Candidate AIが拾った「上にも下にも動きうる銘柄」から、実際に買い検討に進める銘柄を選別する段階です。

## 3. Phase5で解くべき問い

Phase5 Opportunity AIが答える問い:

「Candidate Top50のうち、今買い検討に進める価値が高い銘柄はどれか？」

Phase5でやること:

- Candidate Top50からOpportunity TopNを抽出する。
- downside_bad / drawdown riskが高い候補を落とす。
- 一時的な吹き上げと持続上昇を区別する。
- Candidate scoreを補助情報として使う。
- 相場環境に応じた閾値調整を設計する。

Phase5でまだやらないこと:

- 購入株数の決定
- 資金配分
- 保有判断
- 売却判断
- 発注
- Broker接続
- Paper Trading

## 4. Candidate AIから受け取る入力

主入力:

- Candidate Top50 list
- candidate_score
- candidate_rank
- candidate_reason
- excluded_reason
- target_date
- code
- Phase4 feature tableの主要feature

補助情報:

- price_momentum_return_5d
- price_momentum_return_20d
- price_momentum_return_60d
- volatility_return_std_20d
- trend_close_over_ma_20d
- trend_ma_5_20_ratio
- trend_ma_20_60_ratio
- volume_momentum_ratio_5d
- volume_momentum_ratio_1d_20d
- liquidity_avg_volume_20d
- universe_eligible

Candidate scoreは、買い順位ではなく「上流の候補抽出スコア」として扱います。

## 5. Phase4から見えた強み

- CandidateTop50はFutureReturnTop50をrandomより約4.9倍多く捕捉した。
- CandidateTop50はFutureMaxTop50をrandomより7.5倍多く捕捉した。
- FutureTop10捕捉でもrandomを明確に上回った。
- future_max_return_20dの捕捉力がfuture_return_20dより強い。
- liquidity、60d momentum、20d momentum、trend系にWinner側の傾向が見えた。

Phase5では、この「吹く銘柄を拾う力」を残しながら、下振れリスクを落とす必要があります。

## 6. Phase4から見えた弱み

- 20d win rateはmarket baselineを下回る場面があった。
- downside_bad_rateが高い。
- Candidate scoreはBest / Worstの分離に弱い。
- score_downside_bad_correlationが正であり、高score候補にもdownside riskが混ざる。
- down regimeではwin rate、return、downside_bad_rateが悪化する。
- volume surgeはWinnerよりWorstで高い傾向があり、単純加点には向かない。

Phase5は「地雷除去AI」として設計するのが自然です。

## 7. Phase5のラベル候補

Phase5では、Candidate Top50内の良し悪しを学ぶために、以下のラベルを検討します。

Positive系:

- opportunity_label
- sustained_upside_20d
- future_return_20d_positive
- future_max_return_20d_high
- risk_adjusted_opportunity_label

Risk / exclusion系:

- downside_bad_20d
- future_max_drawdown_20d
- whipsaw_after_spike
- failed_breakout_label
- high_drawdown_candidate_label

重要: これらは学習ラベルまたは評価用であり、推論時featureへ混入させません。

## 8. Phase5のfeature仮説

加点候補:

- price_momentum_return_60d
- price_momentum_return_20d
- price_momentum_return_5d
- trend_close_over_ma_20d
- trend_ma_5_20_ratio
- trend_ma_20_60_ratio
- liquidity_avg_volume_20d

減点または注意候補:

- excessive volume_momentum_ratio_1d_20d
- excessive volume_momentum_ratio_5d
- high volatility_return_std_20d
- too steep short-term spike
- down regime candidate

Phase4-BKでは、Best群はWorst群よりprice momentumとtrendが強く、短期volume ratioはむしろ低い傾向がありました。Phase5では短期出来高急増を単純な強気材料として扱わない方が安全です。

## 9. Regime別方針

Phase4-BMのregime proxyでは、up regimeで候補品質が改善し、down regimeで大きく悪化しました。

Phase5方針:

- up regime: 候補数をやや広めに残す。
- flat regime: 標準的な絞り込みを行う。
- down regime: 候補数を大きく絞り、drawdown filterを強くする。

Regime proxyはPhase4-BMでは評価後ラベルとして使いました。Phase5で推論featureにする場合は、as_of_date時点で観測可能なmarket featureとして再設計する必要があります。

## 10. Phase5-Aで作るべき設計

Phase5-A Opportunity AI Design Documentで最低限定義すること:

- Opportunity AIの責務境界
- Candidate Top50からOpportunity TopNへの変換方針
- 入力feature
- 出力形式
- 利用禁止データ
- downside / drawdown label設計
- regime別方針
- leakage audit方針
- Candidate scoreの扱い
- Phase6以降との責務分離

## 11. 推奨Phase5ロードマップ

1. Phase5-A: Opportunity AI Design Document
2. Phase5-B: Downside / Drawdown Label Design
3. Phase5-C: Opportunity Feature Expansion
4. Phase5-D: Candidate Top50 to Opportunity TopN Dataset
5. Phase5-E: Opportunity AI Training
6. Phase5-F: Opportunity Quality Audit
7. Phase5-G: Candidate + Opportunity Combined Validation

## 12. Phase5で守るべき禁止事項

Phase5初期では以下を行わない:

- backtest
- Paper Trading
- live trading
- Broker API
- order execution
- capital allocation
- portfolio update
- final assets / annual return評価

Phase5はOpportunity品質の判定までに留め、売買や資金配分へ進めるのは後続Phaseにします。

## 13. 引き継ぎ結論

Phase4 Candidate AIは、上昇候補を拾う役割として成功しました。

Phase5では、Candidate AIの出力を「買い候補」ではなく「精査対象」として受け取り、Opportunity AIでdownside risk、持続性、entry timingを確認します。Phase5の中心課題は、上昇捕捉力を維持しながら、大ハズレ候補を落とすことです。
