# Phase4-AS Candidate Model Quality Root Cause Analysis

## Result

- status: OK
- readiness_status: `READY_FOR_MODEL_FIX_PLAN`
- model_type: `sklearn.LogisticRegression`
- blocking_issue: `candidate_scores_are_all_same_and_ranking_is_ineffective`

## Direct Cause

Latest inference feature distribution falls into the same model output path for every eligible row.

## Key Metrics

- train_positive_rate: 0.25
- validation_positive_rate: 0.25
- feature_importance_nonzero_count: 3
- tree_count: 0
- effective_split_count: 3
- latest_prediction_unique_count: 1
- latest_prediction_std: 0.0

## Likely Root Causes

- latest_inference_predictions_are_constant
- only_60_business_days_available_for_smoke_training
- formal_train_validation_periods_are_missing

## Recommended Fix Plan

- Design Phase4-AT model fix plan before any retraining.
- Tune LightGBM smoke parameters such as min_child_samples, num_leaves, class_weight or scale_pos_weight.
- Train only on appropriate eligible rows or explicitly test eligible/excluded treatment.
- Add diagnostics for feature variance, null handling, and target-date grouped evaluation.
- Plan longer historical coverage before formal Candidate Quality Audit.
- Review whether current price/volume features explain momentum_candidate_label.

## Scope Guard

- This phase performs root cause analysis only.
- It does not add features, change labels, retrain, run inference, backtest, trade, promote a model, or place orders.
