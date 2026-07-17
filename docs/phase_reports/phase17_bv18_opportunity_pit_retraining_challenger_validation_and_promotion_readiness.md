# Phase17-BV18 Opportunity AI PIT Retraining, Challenger Validation, and Promotion Readiness

## Executive Summary

Phase17-BV18 performed PIT-compatible Opportunity AI challenger retraining and Champion/Challenger validation. Retraining and evaluation were performed only into `reports/phase17_bv18_opportunity_pit_retraining_challenger_validation_and_promotion_readiness/`.

No formal Registry promotion, Runtime model switch, metrics/schema replacement, BV15 change, BUY re-enable, Runtime Test execution, `.runtime` manual edit, J-Quants fetch, broker write, order submit, notification, or target redesign was performed.

Final judgment:

```text
CHALLENGER_PROMOTION_NOT_READY
NO_LEAKAGE_PASS
BV15_CONTRACT_VALID
BUY_REMAINS_BLOCKED
```

Best observed Challenger on recent holdout was:

```text
model: challenger_recent_fixed_2y
calibration: none
recent_holdout rank 1-5 mean return: 0.0402196966
recent_holdout rank 1-5 hit rate: 0.4275862069
recent_holdout rank 1-20 mean return: 0.054176
```

This improves over Champion on recent holdout, but does not satisfy BUY re-enable or promotion readiness. Hit rate remains below 50%, median return remains negative, calibration is not robust, and Runtime replay positives have not been checked through full BV14/BV15 eligibility.

## Dataset Contract

Dataset source:

- `reports/opportunity_ai/phase5p/opportunity_dataset_with_market_sector.parquet`
- dataset hash: `f6111be4b81df27270b58d60a89f43808f27bdbbd3afff3bf4524c2537ece539`
- target range: `2021-09-08` to `2026-05-15`
- raw local quote max date: `2026-07-14`
- label-safe max feature date from local quotes: `2026-06-16`
- training dataset max date available with complete Runtime-compatible candidate/feature/label rows: `2026-05-15`

Runtime formal feature contract:

- feature count: `32`
- dataset feature count: `32`
- dataset missing features: `[]`
- dataset extra features: `[]`
- feature names match Runtime formal model: `true`
- target label: `label__expected_edge_label_20d`
- target redesign: not performed

Although raw quote data supports a later label-safe date, continuous Runtime-compatible Opportunity training rows after `2026-05-15` were not available in the existing local Phase5P training dataset. Runtime replay feature artifacts from `2026-06-29` onward were used for prediction distribution only, not 20bd training labels.

## Split Contract

Time-series split, no random split:

- train: `2021-09-08` to `2025-12-30`, `52,665` rows
- validation: `2026-01-05` to `2026-02-27`, `1,840` rows
- test: `2026-03-02` to `2026-03-31`, `1,050` rows
- recent holdout: `2026-04-01` to `2026-05-15`, `1,440` rows
- Runtime replay evaluation: `2026-06-29` to `2026-07-10`, prediction distribution only

Calibration was fit only on validation and evaluated on test/recent holdout/Runtime replay.

## Models Evaluated

Champion:

- `champion_formal`
- formal model hash: `140e350bd9b12bf0c595184587fa2a3bd74236e4bdf1818df481022980dd6acd`

Challengers saved outside formal Registry:

- `challenger_expanding_current`
- `challenger_recent_fixed_2y`
- `challenger_time_decay`
- `challenger_regularized`

Saved under:

```text
reports/phase17_bv18_opportunity_pit_retraining_challenger_validation_and_promotion_readiness/challengers/
```

## Test And Recent Holdout Performance

No calibration, test window:

| model | positive rate | MAE | Spearman |
| --- | ---: | ---: | ---: |
| champion_formal | 0.890476 | 0.209730 | 0.249740 |
| challenger_expanding_current | 0.585714 | 0.206077 | 0.170074 |
| challenger_recent_fixed_2y | 0.335238 | 0.193367 | 0.277695 |
| challenger_time_decay | 0.446667 | 0.194393 | 0.270296 |
| challenger_regularized | 0.701905 | 0.206324 | 0.183518 |

No calibration, recent holdout:

| model | positive rate | MAE | Spearman |
| --- | ---: | ---: | ---: |
| champion_formal | 0.159028 | 0.254274 | 0.098242 |
| challenger_expanding_current | 0.085417 | 0.253540 | 0.137450 |
| challenger_recent_fixed_2y | 0.091667 | 0.255441 | 0.085247 |
| challenger_time_decay | 0.110417 | 0.254281 | 0.098045 |
| challenger_regularized | 0.098611 | 0.253076 | 0.158091 |

Recent holdout rank buckets, no calibration:

| model | rank 1-5 mean | rank 1-5 hit rate | rank 1-20 mean | rank 1-20 hit rate |
| --- | ---: | ---: | ---: | ---: |
| champion_formal | -0.036482 | 0.282759 | 0.019039 | 0.424138 |
| challenger_expanding_current | -0.020319 | 0.324138 | 0.007139 | 0.400000 |
| challenger_recent_fixed_2y | 0.040220 | 0.427586 | 0.054176 | 0.477586 |
| challenger_time_decay | 0.013576 | 0.365517 | 0.020087 | 0.422414 |
| challenger_regularized | -0.035354 | 0.331034 | 0.002823 | 0.393103 |

Interpretation: `challenger_recent_fixed_2y` has the best recent holdout top-k mean return, but the hit rate and median remain weak. `challenger_regularized` has the strongest recent Spearman, but poor top-k return. No model clears promotion.

## Calibration Comparison

Calibration methods:

- none
- linear calibration fit on validation only
- isotonic calibration fit on validation only

Recent holdout observations:

- Linear calibration often reduced positive count sharply and reversed ranking sign for several models. It is not accepted.
- Isotonic calibration increased positive counts for several models, but did not consistently improve MAE or recent holdout rank quality.
- `challenger_recent_fixed_2y` no calibration remains the best top-k recent holdout model.

Calibration is not sufficient by itself. No calibrator was saved for Runtime use.

## Runtime Replay Prediction

Runtime replay dates:

```text
2026-06-29
2026-06-30
2026-07-01
2026-07-02
2026-07-03
2026-07-06
2026-07-07
2026-07-08
2026-07-09
2026-07-10
```

Average positive counts per day:

| model calibration | avg positive count | avg positive rate | avg top1 score |
| --- | ---: | ---: | ---: |
| challenger_recent_fixed_2y__isotonic | 14.7 | 0.294 | 0.046354 |
| challenger_recent_fixed_2y__none | 11.5 | 0.230 | 0.022940 |
| challenger_time_decay__isotonic | 11.5 | 0.230 | 0.111062 |
| challenger_recent_fixed_2y__linear | 7.8 | 0.156 | 0.018029 |
| challenger_time_decay__none | 3.9 | 0.078 | 0.012130 |
| champion_formal__none | 0.0 | 0.000 | -0.082460 |

Positive scores are restored for some challengers, especially `challenger_recent_fixed_2y`. Positive count alone is not success. These candidates have not been passed through full BV14/BV15 eligibility, market status, no-buy reason, and production Runtime authority checks, so BUY remains blocked.

## Leakage Audit

Leakage result:

```text
NO_LEAKAGE_PASS
```

Checked:

- future price leakage
- future market feature leakage
- future sector feature leakage
- target leakage
- same-day close misuse
- label overlap leakage
- split boundary contamination
- normalization fit leakage
- calibration fit leakage
- candidate selection leakage
- selected/bought leakage
- ledger leakage
- PnL leakage
- broker leakage

No forbidden feature columns were found in the model feature set.

## BUY Re-enable Evaluation

BV17 criteria were loaded from:

```text
reports/phase17_bv17_opportunity_formal_model_revalidation_and_calibration_root_cause_investigation/buy_reenable_acceptance_criteria.json
```

Result:

```text
BUY_REENABLE_RESULT = NOT_ACCEPTED
```

Reasons:

- positive Runtime candidates exist for some challengers, but positive sample acceptance is still `REVIEW_REQUIRED`
- top5 recent holdout mean return passes directionally, but hit rate is only `0.427586`
- rank correlation is not strong enough in recent holdout
- calibration acceptance is unresolved
- BV14 compatibility requires formal Runtime eligibility checks on predicted positives
- BV15 compatibility is preserved, but not sufficient alone
- formal Registry readiness is candidate-only, not promoted

## Promotion Readiness

Final:

```text
CHALLENGER_PROMOTION_NOT_READY
```

Recommended model candidate for further review:

```text
challenger_recent_fixed_2y
```

Recommended calibration:

```text
none, with linear/isotonic retained only as analysis candidates pending stronger validation
```

Promotion was not performed.

Runtime model switch was not performed.

BUY was not re-enabled.

## Weekly Retrain And Recency Gate Design

Recommended design, not implemented:

- retrain cadence: weekly candidate build
- label-safe cutoff: latest local trading date minus 20 business days
- minimum new observations: at least 5 new business dates and 250 candidate rows
- minimum validation window: at least 40 business dates
- minimum recent holdout: at least 20 business dates
- model max age: 20 business days after label-safe cutoff
- promotion threshold: top5/top20 return and hit-rate above baseline, positive bucket mean return positive, recent Spearman positive

Alarms:

- all-negative prediction alarm: 3 consecutive business days with `positive_count=0`
- positive-rate collapse alarm: below 25% of baseline for 3 days
- score mean drop alarm: below rolling 20bd mean by more than 2 std, or below `-0.10` for 3 days
- top1 non-positive alarm: `top1_score <= 0` for 3 consecutive days
- feature PSI: review at `>0.20`, halt at `>0.30`
- recent rank correlation alarm: recent PIT Spearman `<= 0`

## Required Answers

1. **Did Challenger beat Champion?**  
   Partially. `challenger_recent_fixed_2y` beat Champion on recent holdout top5/top20 mean return, but not enough for promotion.

2. **Did recent holdout ranking recover?**  
   Partially. Best top-k return improved, but hit rate and median remained weak.

3. **Did positive score recover?**  
   Yes for some challengers, including Runtime replay predictions.

4. **Did positive score bucket correspond to profit?**  
   Not accepted yet. Requires stronger recent holdout and Runtime-compatible eligibility validation.

5. **Is calibration necessary?**  
   Not proven. Calibration did not clearly dominate no calibration.

6. **Is calibration alone sufficient?**  
   No.

7. **Best retraining window?**  
   `recent_fixed_2y` is the current candidate for further review.

8. **Was time weighting effective?**  
   Mixed. It restored some Runtime positives but did not beat recent_fixed on recent holdout top-k.

9. **Did Challenger adapt to Candidate population drift?**  
   Partially. Runtime positives returned, but acceptance criteria are not met.

10. **Runtime replay positives?**  
    Yes. `challenger_recent_fixed_2y__none` averaged 11.5 positives/day.

11. **Do positives satisfy BV14/BV15?**  
    Not yet proven. BV15 threshold can be satisfied by positive scores, but BV14/BV15 full Runtime eligibility was not executed.

12. **Leakage?**  
    `NO_LEAKAGE_PASS`.

13. **BUY re-enable criteria met?**  
    No.

14. **Promotion ready?**  
    No.

15. **Weekly retrain should be introduced?**  
    Yes, as a design proposal with recency gates.

16. **Model max age?**  
    Proposed 20 business days after label-safe cutoff.

17. **All-negative alarm?**  
    Proposed 3 consecutive business days.

18. **Next minimal safe step?**  
    Add more label-safe recent training rows, run formal candidate eligibility validation on Challenger positives, and repeat promotion readiness without changing Runtime.

## Evidence Files

- `reports/phase17_bv18_opportunity_pit_retraining_challenger_validation_and_promotion_readiness/dataset_contract.json`
- `reports/phase17_bv18_opportunity_pit_retraining_challenger_validation_and_promotion_readiness/split_contract.json`
- `reports/phase17_bv18_opportunity_pit_retraining_challenger_validation_and_promotion_readiness/champion_metrics.json`
- `reports/phase17_bv18_opportunity_pit_retraining_challenger_validation_and_promotion_readiness/challenger_metrics.json`
- `reports/phase17_bv18_opportunity_pit_retraining_challenger_validation_and_promotion_readiness/champion_vs_challenger.csv`
- `reports/phase17_bv18_opportunity_pit_retraining_challenger_validation_and_promotion_readiness/score_bucket_comparison.csv`
- `reports/phase17_bv18_opportunity_pit_retraining_challenger_validation_and_promotion_readiness/rank_bucket_comparison.csv`
- `reports/phase17_bv18_opportunity_pit_retraining_challenger_validation_and_promotion_readiness/calibration_comparison.csv`
- `reports/phase17_bv18_opportunity_pit_retraining_challenger_validation_and_promotion_readiness/regime_comparison.csv`
- `reports/phase17_bv18_opportunity_pit_retraining_challenger_validation_and_promotion_readiness/runtime_replay_prediction_comparison.csv`
- `reports/phase17_bv18_opportunity_pit_retraining_challenger_validation_and_promotion_readiness/leakage_audit.json`
- `reports/phase17_bv18_opportunity_pit_retraining_challenger_validation_and_promotion_readiness/buy_reenable_acceptance_result.json`
- `reports/phase17_bv18_opportunity_pit_retraining_challenger_validation_and_promotion_readiness/promotion_readiness.json`
- `reports/phase17_bv18_opportunity_pit_retraining_challenger_validation_and_promotion_readiness/weekly_retrain_design.json`
- `reports/phase17_bv18_opportunity_pit_retraining_challenger_validation_and_promotion_readiness/recency_gate_design.json`
- `reports/phase17_bv18_opportunity_pit_retraining_challenger_validation_and_promotion_readiness/evidence_inventory.json`
- `reports/phase_reports/phase17_bv18_opportunity_pit_retraining_challenger_validation_and_promotion_readiness.json`

## Prohibited Operations Confirmation

Not executed:

- formal Registry promotion
- formal model replacement
- Runtime model path change
- metrics/schema replacement
- BV15 change or disablement
- no-buy reason bypass
- Top-N forced BUY
- BUY re-enable
- Runtime Test run/resume/reset/rollback
- Frozen Run edit
- `.runtime` manual edit
- Ledger/Pending/Current edit
- J-Quants fetch
- broker/Tachibana write
- production/demo order
- notification
- target redesign

## Final Judgment

```text
CHALLENGER_PROMOTION_NOT_READY
```

BUY remains blocked.
