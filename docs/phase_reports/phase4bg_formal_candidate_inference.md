# Phase4-BG Formal Candidate Inference

- status: `OK`
- readiness_status: `READY_FOR_FORMAL_CANDIDATE_QUALITY_AUDIT`
- purpose: score the latest long-history feature table with the Phase4-BF formal Candidate AI model and generate a top 50 candidate list.

## Scope

Phase4-BG performs formal Candidate inference and output audit only.

- backtest_executed: `False`
- trading_executed: `False`
- paper_trading_executed: `False`
- broker_api_called: `False`
- order_executed: `False`
- production_model_promoted: `False`
- reader_switch_performed: `False`

## Input

- model: `.runtime/candidate_ai/models/phase4bf_formal_candidate_model.pkl`
- model manifest: `.runtime/candidate_ai/models/phase4bf_formal_candidate_model_manifest.json`
- feature table: `.runtime/candidate_ai/features/phase4bc_long_history_features_2021-06-14_2026-06-12.parquet`
- model input: `feature__*` columns only
- model_type: `lightgbm.LGBMClassifier`
- model_version: `phase4bf_formal_candidate_model`
- feature_column_count: `13`

## Candidate Rule

- Score only `universe_eligible = true` rows without `excluded_reason`.
- Use the latest `target_date` in the feature table.
- `candidate_score` is the positive-class probability from the formal model.
- `candidate_rank` is sorted by `candidate_score` descending.
- The top 50 rows are the Candidate AI output.

Candidate rank is not a buy rank. Candidate score is not a buy signal. Candidate AI does not decide purchase, sale, holding, allocation, order placement, Paper Trading, or broker actions.

## Inference Result

- target_date: `2026-06-12`
- input_feature_row_count: `4212`
- eligible_input_count: `4164`
- excluded_input_count: `48`
- scored_count: `4164`
- candidate_count: `50`
- top_n: `50`

Score distribution:

- candidate_score_min: `0.05275475`
- candidate_score_max: `0.77225751`
- candidate_score_mean: `0.49145138`
- candidate_score_std: `0.14799808`
- unique_candidate_score_count: `4164`
- all_same_score: `False`
- ranking_effective: `True`

Output quality:

- candidate_rank_valid: `True`
- candidate_rank_unique: `True`
- candidate_reason_coverage: `1.0`
- excluded_reason_available: `True`
- feature_snapshot_id_present: `True`
- audit_flags_present: `True`
- leakage_audit_status: `OK`
- responsibility_boundary_status: `OK`

## Output

Runtime outputs:

- `.runtime/candidate_ai/inference/`
- `.runtime/candidate_ai/candidates/`

Reports:

- `reports/candidate_ai/full_range/phase4bg_formal_candidate_inference_summary.json`
- `reports/candidate_ai/full_range/phase4bg_formal_candidate_inference_top50.json`
- `reports/candidate_ai/full_range/phase4bg_formal_candidate_inference_top50.csv`
- `reports/phase_reports/phase4bg_formal_candidate_inference_audit.json`

## Leakage Rule

The model input must not use:

- `future_return_*`
- `future_max_return_*`
- `future_max_drawdown_*`
- `top_decile_*`
- `downside_bad_*`
- `momentum_candidate_label`
- any `label__*` column

## Readiness

Success readiness:

- `READY_FOR_FORMAL_CANDIDATE_QUALITY_AUDIT`

Next phase:

- Phase4-BH Formal Candidate Quality Audit.
