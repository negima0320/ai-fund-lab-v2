# Phase19-AD-U2-E Rolling Split Policy Evidence Review

## Final Judgment

```text
PHASE19_AD_U2_E_ROLLING_SPLIT_POLICY_REVIEW_PACKAGE_READY
PHASE19_AD_U2_HUMAN_DECISION_REQUIRED
PHASE19_AD_U2_NOT_COMPLETE
PHASE19_AD_U3_NOT_READY
```

U2-EではRolling Split Policyを承認していません。既存split、実Dataset統計、方式比較、推奨案、未承認draft、Human Review packageを作成しました。reviewerはnull、decisionは`HUMAN_REVIEW_REQUIRED`です。

## Existing Split Evidence

既存ArtifactではCandidateに852BD train、Opportunityに793BD trainの実績があります。Validationは222BD、Testは39BD、Recent Holdoutは29BD、target horizonとembargoは20BDです。これは`TRAINING_IMPLEMENTATION_DEFAULT`であり、正式Policyではありません。

## Candidate Dataset Statistics

Candidate datasetは2021-06-14から2026-05-15まで、1202営業日、4970227行、4780銘柄です。主label `label__momentum_candidate_label` のpositiveは477192、negativeは4493035です。

## Opportunity Dataset Statistics

Opportunity datasetは2021-09-08から2026-05-15まで、1143営業日、56995行、2323銘柄です。主label `label__opportunity_positive_20d` のpositiveは25828、negativeは31167です。

## Window Method Comparison

Expanding、Fixed Rolling、Capped Expanding / Hybridを比較しました。比較根拠はPIT安全性、label-safe、約5年学習前提、データ量、再現性、市場構造変化への耐性、Candidate/Opportunity整合、計算可能性、初回Generation成立性です。収益結果は使っていません。

## Training Window Evidence

「約5年」はまだ正式定義が必要です。既存train営業日は証拠として使えますが、Policy値として昇格していません。

## Validation / Test / Holdout Evidence

Validation、Test、Recent Holdoutの役割を分離しました。minimum business days、rows、distinct issues、positive/negative labelsはDataset/Split成立条件としてHuman Review対象です。class balanceはModel Quality scopeです。

## Embargo Result

既存Evidenceでは`target_horizon_business_days = 20`、`embargo_business_days = 20`です。20BD forward labelの漏洩防止には少なくともtarget horizon相当のembargoが必要です。

## Minimum Sufficiency Options

単一のminimum rowsでは不足します。minimum business days、rows、distinct issues、positive labels、negative labels、missing ratioを分類しました。未承認値は`HUMAN_DECISION_REQUIRED`です。

## Candidate / Opportunity Policy Boundary

推奨境界は`COMMON_TEMPORAL_POLICY_PLUS_COMPONENT_SPECIFIC_MINIMUMS`です。時間整合、target horizon、embargo、calendar identityは共通化し、row/issue/label最低条件はcomponent-specificにするのが妥当です。

## Bootstrap / Retraining Boundary

Bootstrapではprevious revisionとの差分を必須にしません。Retrainingではminimum incremental label-safe business days、incremental rows、schema/lineage continuity、drift/health triggerを別契約にします。

## Policy Options

3案を作成しました。

- Option A: Expanding Window
- Option B: Fixed Rolling Window
- Option C: Capped Expanding / Hybrid

## Recommended Option

Codex推奨は`OPTION_C_CAPPED_EXPANDING_HYBRID`です。これはHuman Review decisionではありません。理由は、約5年学習前提、初回Generation成立性、将来計算量、Candidate/Opportunity差分吸収のバランスがよいためです。

## Human Decision Required Items

未解決値は、約5年の定義、training cap、validation/test/holdout window、component別minimum rows/issues/positive/negative labels、maximum missing ratioです。

## Prohibited Performance Input Audit

Backtest profit、Runtime PnL、Paper PnL、Broker Snapshot、portfolio value等はPolicy推奨根拠に使っていません。Test/Audit resultも収益・性能根拠としては使っていません。

## Non-Mutation

Runtime/Trading Stateは不変。Broker writeは0。Training、Calibration、Unified Generation、Accepted Decision、Runtime Transition、BUY restartは実行していません。

## Failure Injection

FI-1からFI-12までPASSです。Draft policyからのsplit生成、runtime threshold override、review hash mismatchは拒否扱いです。

## Regression

最終回帰結果は`test_results.json`に記録します。

## Evidence Paths

Evidence root: `reports/phase19_ad_u2_e_rolling_split_policy_evidence_review/`

Summary: `reports/phase_reports/phase19_ad_u2_e_rolling_split_policy_evidence_review.json`

## Remaining AD-U2 Work

Rolling Split PolicyのHuman Review decisionが必要です。承認後にのみapproved policy hashをmaterializeし、versioned split生成へ進めます。
