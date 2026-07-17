# Phase17-BV16 Opportunity AI Expected Edge Semantics and Runtime Distribution Investigation

## Executive Summary

Target run: `runtime-test-historical-extended-smoke-20260716T230100525117Z`.

The 10 business day Historical Extended Smoke produced no BUY orders because every Runtime Opportunity candidate from `2026-06-29` through `2026-07-10` had `expected_edge_score <= 0`. This is not a BV15 regression and not a Runtime feature-schema connection failure. The Runtime adapter is consuming the formal Opportunity model/metrics/schema pair, the model/metrics validation passes, and the producer reports no missing model feature columns after the formal unprefixed-artifact-to-prefixed-model mapping.

Exact root cause:

```text
formal_opportunity_model_predicts_non_positive_expected_edge_for_every_runtime_candidate_in_2026_06_29_to_2026_07_10_extended_smoke
```

Final classifications:

```text
MODEL_OUTPUT_SEMANTICS_VALID
RUNTIME_FEATURE_DRIFT_NOT_DETECTED
MODEL_METRICS_MATCH
EXPECTED_EDGE_SIGN_OR_SCALE_VALID
BV15_CONTRACT_VALID
AI_RETRAIN_REQUIRED
RUNTIME_CONNECTION_FIX_NOT_REQUIRED
BUY_REMAINS_BLOCKED
REVIEW_REQUIRED
```

## Runtime Score Distribution

Across the replay window, Runtime Opportunity ranking artifacts contain `500` candidates. Positive expected edge count is `0`. Top20 positive expected edge count is `0` out of `200`.

Supplemental CSV: `reports/phase17_bv16_opportunity_expected_edge_semantics_and_runtime_distribution_investigation/runtime_score_distribution_by_date.csv`.

Representative evidence:

- `2026-06-29`: top rank `33500`, `expected_edge_score=-0.06417033`, `no_buy_reason=non_positive_expected_edge_score`.
- `2026-07-06`: top rank `69710`, `expected_edge_score=-0.11839238`, `no_buy_reason=non_positive_expected_edge_score`.
- `2026-07-10`: top rank `13820`, `expected_edge_score=-0.04742415`, `no_buy_reason=non_positive_expected_edge_score`.

## Expected Edge Semantics

`src/ai_fund_lab_v2/opportunity_ai/training.py:17` defines `MODEL_VERSION = "opportunity_model_phase5e_v1"` and `src/ai_fund_lab_v2/opportunity_ai/training.py:18` defines `TARGET_LABEL = "label__expected_edge_label_20d"`.

`src/ai_fund_lab_v2/opportunity_ai/inference.py:329` assigns raw model predictions directly to `expected_edge_score`. `src/ai_fund_lab_v2/opportunity_ai/inference.py:340` ranks descending by `expected_edge_score`. `src/ai_fund_lab_v2/opportunity_ai/inference.py:387` adds `non_positive_expected_edge_score` when the score is `<= 0`.

`src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py:660` writes the same value as `expected_edge_score`, `src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py:661` writes it as `opportunity_score`, and `src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py:664` writes it as `expected_return`.

No sign inversion or percent/decimal conversion was found in this path.

## Model And Metrics Authority

Formal artifacts inspected:

- model: `.runtime/artifacts/ai/opportunity/model/formal_opportunity_model/sha256-140e350bd9b12bf0/model.pkl`
- model hash: `140e350bd9b12bf0c595184587fa2a3bd74236e4bdf1818df481022980dd6acd`
- metrics: `.runtime/artifacts/ai/opportunity/metrics/formal_opportunity_metrics/sha256-8428f2327e773747/metrics.json`
- metrics hash: `8428f2327e77374743f69e2ebc956a97a9d718880ef2acfc26571f94d9fd9511`
- schema: `.runtime/artifacts/ai/opportunity/schema/formal_opportunity_schema/sha256-8428f2327e773747/feature_schema.json`
- schema hash: `8428f2327e77374743f69e2ebc956a97a9d718880ef2acfc26571f94d9fd9511`

Runtime ranking artifacts report `metrics_validation.status=PASS`, `metrics_model_path_authority=legacy_metrics_path_content_matches_runtime_model`, and `metrics_model_path_hash` equal to the Runtime model hash.

Classification: `MODEL_METRICS_MATCH`.

## Feature Contract And Drift

Runtime feature artifacts are stored with unprefixed feature names. The BUY AI producer contract maps artifact columns to model columns once:

- `src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py:1094-1099` builds prefixed present columns.
- `src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py:1108-1111` requires all model columns to be present and no prefixed artifact double-prefix.
- `src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py:1137` records `artifact_unprefixed_consumer_maps_feature_prefix_once`.

For inspected Runtime dates (`2026-06-29`, `2026-07-06`, `2026-07-10`), ranking artifacts show `missing_columns=[]`, `present_columns=32`, and `double_prefix_detected=false`.

Classification: `RUNTIME_FEATURE_DRIFT_NOT_DETECTED`.

## Training And Validation Distribution

The formal model is capable of producing positive predictions on the training-era datasets, but positives are sparse:

- Phase5P dataset predictions: `4862` positive out of `56995`.
- Phase5P test split predictions: `1177` positive out of `4330`.
- Phase5P prediction/target correlation: `0.28751135965612096`.

The 10bd runtime replay distribution has zero positives, so BUY remains correctly blocked under the BV15 contract.

## BV15 Validity

BV15 fixed a real contract error: rank/top20 membership was being used as BUY permission. The current replay proves the fixed behavior: ranked candidates with negative expected edge are no-action BUY-ineligible candidates.

`src/ai_fund_lab_v2/runtime_v2/buy_ai/opportunity_eligibility.py:243-249` blocks `expected_edge_score <= 0` as `non_positive_expected_edge_score`.

Classification: `BV15_CONTRACT_VALID`.

## Required Boundary Before BUY Re-enable

Do not relax `expected_edge_score > 0`, ignore `no_buy_reason`, or force Top-N BUY. BUY can be re-enabled only after formal Opportunity model validation, recalibration, or retraining demonstrates that positive expected-edge candidates are produced on point-in-time Runtime distributions and that those positives satisfy the artifact registry, model/metrics/schema, eligibility, market-status, and no-leakage contracts.

## Answers To Required Questions

1. **What is expected_edge_score?**  
It is the raw regression prediction for label__expected_edge_label_20d, copied without sign inversion into expected_edge_score. It is used as an absolute expected edge estimate, not only a relative rank.

2. **Training target and units**  
Training TARGET_LABEL is label__expected_edge_label_20d. Dataset evidence shows the same values as label__risk_adjusted_future_return_20d, bounded approximately -0.47 to 0.54. It is decimal return-like/risk-adjusted 20 business day edge, not percent points.

3. **Does positive mean BUY advantage?**  
Yes by current contract: inference buy_reason marks positive_expected_edge only when score > 0, no_buy_reason adds non_positive_expected_edge_score when score <= 0, and BV15 BUY eligibility blocks score <= 0.

4. **Is zero threshold statistically validated?**  
Contractually valid, but model acceptance evidence does not prove an operational hit-rate/calibration threshold sufficient for production BUY. This requires review/retraining/calibration evidence.

5. **Are all negative runtime scores expected?**  
They are valid model outputs, but operationally concerning. The formal model predicts positives on training/validation/test datasets, yet none on the 10bd runtime candidate set.

6. **Sign or scale bug?**  
No sign inversion or scale conversion bug was found in code. scores are assigned directly to expected_edge_score and expected_return copies the same value in Runtime adapter.

7. **Model/metrics/schema mismatch?**  
No. Runtime opportunity rankings show metrics_validation PASS with model hash matching metrics legacy model content hash; feature schema count is 32 and missing_columns is empty.

8. **Runtime feature drift?**  
No schema drift detected. Runtime artifacts are intentionally unprefixed and producer maps them once to model feature columns; selected inspected dates show producer missing_columns=[] and 32 present columns.

9. **Did BV15 cause BUY 0?**  
BV15 did not create negative scores. It correctly stopped treating rank/top20 as BUY permission and enforced the already-present no_buy_reason/non-positive expected edge.

10. **Should BV15 threshold be relaxed?**  
No. Relaxing expected_edge_score > 0 would permit trades that the AI output explicitly marks no-buy.

11. **Is retraining needed?**  
Yes, before BUY can be re-enabled with production safety. The model produces sparse positives on historical datasets but zero positives for the actual 10bd replay distribution.

12. **Runtime connection fix needed?**  
Not based on current evidence. Runtime connection fixes are not indicated; model acceptance/calibration is the next boundary.

13. **BUY re-enable condition**  
BUY remains blocked until formal model validation/retraining/calibration produces positive expected_edge candidates on PIT runtime distributions and passes metrics/feature/artifact authority checks.

14. **Historical smoke semantics**  
The 10bd run is valid as a negative-signal replay. It demonstrates Runtime no-action behavior, not successful BUY opportunity generation.

15. **Final root cause**  
The formal Opportunity model score distribution, when applied to the 2026-06-29..2026-07-10 runtime candidate distribution, is entirely non-positive. The downstream BUY 0 result is correct under the current contract.

## Evidence Files

- `reports/phase17_bv16_opportunity_expected_edge_semantics_and_runtime_distribution_investigation/summary.json`
- `reports/phase17_bv16_opportunity_expected_edge_semantics_and_runtime_distribution_investigation/runtime_score_distribution_by_date.csv`
- `reports/phase17_bv16_opportunity_expected_edge_semantics_and_runtime_distribution_investigation/historical_artifact_score_distribution.csv`
- `reports/phase17_bv16_opportunity_expected_edge_semantics_and_runtime_distribution_investigation/training_validation_prediction_distribution.json`
- `reports/phase17_bv16_opportunity_expected_edge_semantics_and_runtime_distribution_investigation/feature_distribution_comparison.json`
- `reports/phase17_bv16_opportunity_expected_edge_semantics_and_runtime_distribution_investigation/model_metrics_feature_contract.json`
- `reports/phase17_bv16_opportunity_expected_edge_semantics_and_runtime_distribution_investigation/expected_edge_lineage.json`
- `reports/phase17_bv16_opportunity_expected_edge_semantics_and_runtime_distribution_investigation/root_cause_matrix.json`
- `reports/phase_reports/phase17_bv16_opportunity_expected_edge_semantics_and_runtime_distribution_investigation.json`

## Commands Executed

Read-only/source-analysis commands only:

- `sed` / `nl` inspections of BV16 attachment and relevant source files.
- `rg` inspections for expected edge, no-buy, and runtime adapter paths.
- Python/pandas read-only analysis of existing Runtime artifacts, formal AI artifacts, and training datasets.
- JSON/CSV report generation under `reports/phase17_bv16_opportunity_expected_edge_semantics_and_runtime_distribution_investigation` and `reports/phase_reports`.

No Runtime Test run/resume/reset/rollback/close, Frozen Run edit, `.runtime` manual edit, model retraining, broker write, J-Quants fetch, or external notification was executed.

## Final Judgment

```text
REVIEW_REQUIRED
```

BUY remains blocked. The next phase should be a formal Opportunity model validation/retraining/calibration phase, not a Runtime eligibility relaxation.
