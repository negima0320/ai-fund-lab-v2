# Phase18-E — Opportunity AI Design Review and Root-Cause Investigation

- Run ID: `phase18e-opportunity-design-review-20260717T000000Z`
- Dataset hash: `3258c6f8e328cd08ad8154db70bc3f24ba1423b616dd9a4a05476f1fab7a7c09`
- Training model hash: `7ed4902872eaf3b353c9a7b9128cc4bb02a100b636c09f775a7a625e0c04652e`
- Primary judgment: `PHASE18_E_OPPORTUNITY_MODEL_OR_TRAINING_REDESIGN_REQUIRED`
- Secondary judgment: `OPPORTUNITY_DESIGN_CONTRACT_REUSE_WITH_TRAINING_REDESIGN`

## Executive Finding

Phase18-DのOpportunity Challengerは、正式なPIT Dataset/Target/Feature契約の上で、RankingとCalibrationの両方が運用不能です。ただしTarget oracleは直近holdoutでも正の上位リターンを表現でき、Candidate接続も絶対Pathを含まないDataset Identity参照で成立しています。したがって主因はTarget/Feature/BUY条件の変更ではなく、OpportunityのModel Spec、Calibration、Training Window検証不足です。

## Phase18-D Inventory

- Recent Spearman: `-0.072977`
- Recent Top5 mean realized return: `-0.029478`
- Recent Top20 mean realized return: `0.004662`
- Recent no-buy day ratio: `1.0`
- Recent positive score coverage: `0.0`
- Runtime files: `10`, Runtime positive expected-edge rate: `0.0`

## Layer Judgments

- A Dataset population: `PASS`
- B Candidate to Opportunity connection: `CANDIDATE_CONNECTION_VALID_FOR_PHASE18E`
- C Feature validity: `PASS`
- D Target validity: `TARGET_CAN_EXPRESS_POSITIVE_OPPORTUNITY`
- E/F/G Model, Calibration, Training window: `MODEL_SPEC_AND_CALIBRATION_FAILURE`
- H Regime sensitivity: `REGIME_SENSITIVITY_PRESENT_BUT_NOT_SOLE_ROOT_CAUSE`
- I Operational utility: `CURRENT_OPPORTUNITY_MODEL_HAS_NO_BUY_UTILITY_UNDER_BV15`
- BV15 compatibility: `BV15_IS_COMPATIBLE_BUT_CURRENT_SCORES_ARE_NON_ACTIONABLE`

## Evidence Highlights

- Target oracle recent Top5 mean return: `0.596868`
- Best same-contract diagnostic: `{'experiment': 'same_features_standardized_ridge', 'recent_spearman': 0.17601, 'recent_top5_mean': 0.074486, 'recent_top20_mean': 0.074111, 'recent_no_buy_day_ratio': 0.0, 'recent_positive_score_coverage': 0.174306}`
- Runtime no-buy reasons: `{'below_opportunity_top20|non_positive_expected_edge_score': 296, 'non_positive_expected_edge_score': 196, 'high_downside_risk_score|non_positive_expected_edge_score': 4, 'below_opportunity_top20|high_downside_risk_score|non_positive_expected_edge_score': 4}`
- Feature evidence file: `reports/phase18_e_opportunity_ai_design_review_and_root_cause_investigation/phase18e-opportunity-design-review-20260717T000000Z/feature_validity_rows.json`

## Acceptance Evidence

- Metrics inventory: `PASS`; validation/test/recent/monthly, calibration, prediction distribution, Runtime distributionをJSONに記録。
- Dataset population: `PASS`; rows `56995`, target dates `1143`。
- Candidate connection: `PASS`; absolute source refs `0`。
- Target validity: `PASS`; recent target/future-return Spearman `0.975178`。
- Feature validity: `PASS`; stable/useful `12`, drifted `8`。
- Ranking/Calibration: `PASS`; Phase18-D ranking bad `True`, calibration bad `True`。
- Operational/BV15: `PASS` / `PASS`; BV15 preserved and no forced BUY。
- Root cause classification: `PASS`; `E_MODEL_SPEC + F_CALIBRATION + G_TRAINING_WINDOW`。

## Next Implementation Target

Opportunity Training Pipeline: replace unscaled SGDRegressor challenger with a PIT-safe scaled/nonlinear model family and explicit calibration validation, preserving target/features/BV15.

## Non-Mutation Confirmation

- Registry accepted update: `False`
- Runtime switch: `False`
- BUY restart: `False`
- Broker write: `False`
- BV15 / BUY condition change: `False`

## Final Judgment

`PHASE18_E_OPPORTUNITY_MODEL_OR_TRAINING_REDESIGN_REQUIRED`
