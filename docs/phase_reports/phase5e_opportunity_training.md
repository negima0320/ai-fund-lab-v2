# Phase5-E Opportunity AI Training

## 1. Purpose

Phase5-E implements the first Opportunity AI training pipeline.

Opportunity AI is an expected-value ranking AI. It does not extract the initial universe, decide holdings, sell positions, size positions, allocate capital, call Broker API, run Paper Trading, place orders, or evaluate portfolio-level performance.

The Phase5-E model ranks Phase4 Candidate Top50 rows by expected edge and evaluates whether Opportunity Top5 / Top10 / Top20 improves over Candidate Top50.

## 2. Inputs

Primary dataset:

- `reports/opportunity_ai/phase5d/opportunity_dataset.parquet`

Required dataset readiness:

- `READY_FOR_OPPORTUNITY_TRAINING`
- feature/label columns separated by prefix
- train / validation / test split already assigned by `target_date`
- leakage audit OK in Phase5-D

Training feature contract:

- Only columns prefixed with `feature__` are used as model input.
- Target label is `label__expected_edge_label_20d`.
- Future columns are used only as label/evaluation columns.

Evaluation labels:

- `label__future_return_20d`
- `label__future_max_return_20d`
- `label__future_max_drawdown_20d`
- `label__downside_bad_20d`
- `label__top_decile_20d`

## 3. Forbidden Training Inputs

The training pipeline blocks these from feature columns:

- `future_return_*`
- `future_max_return_*`
- `future_max_drawdown_*`
- `downside_bad_*`
- `top_decile_*`
- expected-edge labels and relative opportunity labels
- `trade_result`
- `trade_profit`
- `selected`
- `bought`
- `sold`
- `cash`
- `portfolio`
- `annual_return`
- `final_assets`
- `backtest`
- `paper_trading`
- `pm_multiplier`
- Opportunity output columns
- Candidate evaluation output columns
- `expected_edge_score`
- `buy_rank`

Phase5-E does not use annual return, final assets, profit factor, or portfolio drawdown as evaluation metrics.

## 4. Implementation

Added files:

- `src/ai_fund_lab_v2/opportunity_ai/training.py`
- `scripts/train_phase5e_opportunity_model.py`
- `tests/opportunity_ai/test_phase5e_opportunity_training.py`

Updated:

- `src/ai_fund_lab_v2/opportunity_ai/__init__.py`

Generated artifacts:

- `models/opportunity_ai/phase5e/opportunity_model.pkl`
- `reports/opportunity_ai/phase5e/opportunity_training_metrics.json`
- `reports/opportunity_ai/phase5e/opportunity_training_audit.json`

## 5. Model

Initial model:

- `sklearn_hist_gradient_boosting_regressor`
- target: `label__expected_edge_label_20d`
- feature set: `feature__*` columns only

Categorical and non-numeric handling:

- boolean features are converted to numeric values
- string features such as `feature__candidate_reason` are encoded from train split categories
- numeric missing values use train split medians
- unknown categories at validation/test/inference preparation time are mapped to `-1`

## 6. Baselines

Phase5-E evaluates these ranking baselines:

- Candidate score baseline: rank by `feature__candidate_score`
- Candidate rank baseline: rank by inverse `feature__candidate_rank`
- Simple rule baseline: momentum/trend/liquidity minus volatility and single-day volume surge

The simple rule baseline is intentionally transparent and does not use future labels, trade results, backtest results, portfolio results, or prior Opportunity outputs.

## 7. Evaluation

Evaluation is performed per split and per `target_date`.

For each target date:

- Candidate Top50 average is computed across all candidate rows.
- Each ranker selects Opportunity Top5 / Top10 / Top20.
- Selected rows are aggregated across target dates.

Metrics:

- `selected_mean_future_return`
- `selected_mean_future_max_return`
- `selected_top_decile_rate`
- `selected_downside_bad_rate`
- `selected_mean_future_max_drawdown`
- `win_rate_20d`
- lift versus Candidate Top50 average
- candidate score baseline versus model
- validation/test gap
- overfit warning

## 8. Current Training Result

Dataset:

- rows: 2,846
- train rows: 1,998
- validation rows: 598
- test rows: 250
- feature columns: 16
- label columns: 14

Audit:

- leakage audit: OK
- forbidden feature column count: 0
- future feature column count: 0
- trade result feature column count: 0
- portfolio feature column count: 0
- model trained: true
- validation/test metrics available: true

Readiness:

- `TRAINING_COMPLETE_WITH_WARNINGS`

The warning is intentional for the first Phase5-E run because the training sample is small and validation/test behavior is not yet stable enough to treat this as a final production-quality model.

Validation summary:

- Candidate Top50 mean future return: 0.036628
- Model Top5 mean future return: 0.067688
- Model Top10 mean future return: 0.043377
- Model Top20 mean future return: 0.048660
- Candidate score baseline Top5 mean future return: 0.112356
- Simple rule baseline Top20 mean future return: 0.061652

Test summary:

- Candidate Top50 mean future return: 0.011373
- Model Top5 mean future return: 0.033236
- Model Top10 mean future return: 0.001802
- Model Top20 mean future return: 0.020817
- Candidate score baseline Top5 mean future return: -0.034538
- Simple rule baseline Top5 mean future return: 0.126059

Regression summary:

- train RMSE: 0.209650
- validation RMSE: 0.256974
- test RMSE: 0.295810
- validation/test Top10 future-return gap: -0.041575

## 9. Phase5-F Handoff

Phase5-F can proceed only as an inference pipeline implementation, not as promotion.

Handoff artifacts:

- model artifact: `models/opportunity_ai/phase5e/opportunity_model.pkl`
- metrics: `reports/opportunity_ai/phase5e/opportunity_training_metrics.json`
- audit: `reports/opportunity_ai/phase5e/opportunity_training_audit.json`

Phase5-F must:

- load the Phase5-E artifact
- apply the same feature preprocessing
- read Candidate Top50 and feature columns only
- never read label tables on inference path
- output `expected_edge_score`, `buy_rank`, `expected_return_horizon`, `downside_risk_score`, `buy_reason`, and `no_buy_reason`

Recommended next action:

- Implement Phase5-F inference behind the same leakage boundary.
- Treat the current model as a first training artifact with warnings, not a promoted production model.
