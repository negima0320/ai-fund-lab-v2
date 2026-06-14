# Phase5-F Opportunity Inference

## 1. Purpose

Phase5-F implements Opportunity AI inference for the latest Phase4 Candidate Top50.

Opportunity AI ranks Candidate Top50 by expected edge. It does not extract candidates from the full universe, decide holdings, sell positions, size positions, allocate capital, call Broker API, run Paper Trading, place orders, promote a model, or switch readers.

The Phase5-E model readiness is `TRAINING_COMPLETE_WITH_WARNINGS`, so Phase5-F can produce an inference artifact for Phase5-G quality audit, but it is not promotion-ready.

## 2. Inputs

Model artifact:

- `models/opportunity_ai/phase5e/opportunity_model.pkl`

Latest Candidate Top50:

- `reports/candidate_ai/full_range/phase4bg_formal_candidate_inference_top50.json`

Inference features:

- `.runtime/candidate_ai/features/phase4bc_long_history_features_2021-06-14_2026-06-12.parquet`

Training metrics reference:

- `reports/opportunity_ai/phase5e/opportunity_training_metrics.json`

No label table is read on the inference path.

## 3. Implementation

Added files:

- `src/ai_fund_lab_v2/opportunity_ai/inference.py`
- `scripts/run_phase5f_opportunity_inference.py`
- `tests/opportunity_ai/test_phase5f_opportunity_inference.py`

Updated:

- `src/ai_fund_lab_v2/opportunity_ai/__init__.py`

Generated artifacts:

- `reports/opportunity_ai/phase5f/latest_opportunity_inference.parquet`
- `reports/opportunity_ai/phase5f/latest_opportunity_top20.csv`
- `reports/opportunity_ai/phase5f/opportunity_inference_summary.json`
- `reports/opportunity_ai/phase5f/opportunity_inference_audit.json`

## 4. Inference Flow

1. Load Phase5-E model artifact.
2. Load latest Candidate Top50.
3. Load only feature rows for the Candidate target date.
4. Join Candidate and feature rows by `target_date` and `code`.
5. Construct model input from the model artifact's `feature__*` columns only.
6. Apply the Phase5-E preprocessing payload.
7. Predict `expected_edge_score`.
8. Rank by `expected_edge_score` descending inside each `target_date`.
9. Emit `buy_rank`, `is_top5`, `is_top10`, and `is_top20`.
10. Emit initial rule-based `downside_risk_score`, `buy_reason`, and `no_buy_reason`.

## 5. Output Schema

Output columns:

- `target_date`
- `code`
- `expected_edge_score`
- `buy_rank`
- `expected_return_horizon`
- `downside_risk_score`
- `buy_reason`
- `no_buy_reason`
- `candidate_score`
- `candidate_rank`
- `model_version`
- `feature_version`
- `inference_run_id`
- `created_at`
- `is_top5`
- `is_top10`
- `is_top20`

## 6. Leakage Boundary

Forbidden on inference path:

- label table reads
- `future_return_*`
- `future_max_return_*`
- `future_max_drawdown_*`
- `downside_bad_*`
- `top_decile_*`
- `trade_result`
- `trade_profit`
- `selected`
- `bought`
- `sold`
- `cash`
- `portfolio`
- `annual_return`
- `final_assets`
- backtest result columns
- Paper Trading result columns
- PM multiplier columns
- past Opportunity output columns
- Candidate evaluation output columns

Inference features are limited to Candidate current outputs plus J-Quants-derived feature columns.

## 7. Current Result

Run summary:

- input candidates: 50
- output rows: 50
- feature columns: 16
- unique score count: 50
- all same score: false
- Top5 count: 5
- Top10 count: 10
- Top20 count: 20
- leakage audit: OK
- label table read flag: false
- future feature column count: 0
- forbidden feature column count: 0
- trade result feature column count: 0
- portfolio feature column count: 0
- backtest feature column count: 0
- AI output leakage column count: 0
- promotion ready: false
- readiness: `READY_FOR_PHASE5G_QUALITY_AUDIT`

Top5 from the latest inference:

| buy_rank | code | expected_edge_score | downside_risk_score | candidate_rank |
| ---: | --- | ---: | ---: | ---: |
| 1 | 58030 | 0.17206654 | 0.73401088 | 18 |
| 2 | 82890 | 0.08013162 | 0.16047563 | 17 |
| 3 | 99840 | 0.05772178 | 0.51540637 | 7 |
| 4 | 20340 | 0.05239505 | 0.53901925 | 10 |
| 5 | 186A0 | 0.05217493 | 0.60216975 | 29 |

## 8. Readiness

Phase5-F is complete and ready for Phase5-G Opportunity Quality Audit.

Important caveat:

- `promotion_ready` is `false` because Phase5-E training completed with warnings.
- Phase5-F output is an audit artifact, not a live trading, Paper Trading, allocation, or production promotion artifact.
