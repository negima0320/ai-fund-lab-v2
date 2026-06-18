# Phase9-J Feature Refresh Report

- status: FEATURES_READY
- target_data_until: 2026-06-16
- dry_run: False
- execute: True
- manifest_path: `.runtime/phase9/feature_refresh/2026-06-16/feature_refresh_manifest.json`

## Artifacts

| AI | status | rows | max_date | schema_hash | artifact |
| --- | --- | ---: | --- | --- | --- |
| candidate | FEATURES_READY | 4989 | 2026-06-16 | `1ede9c508b3a16cb` | `.runtime/phase9/features/2026-06-16/candidate_features.parquet` |
| opportunity | FEATURES_READY | 4989 | 2026-06-16 | `944e345929c4d2c9` | `.runtime/phase9/features/2026-06-16/opportunity_feature_input.parquet` |
| position | FEATURES_READY | 0 | 2026-06-16 | `3ddf67ff43f207fb` | `.runtime/phase9/features/2026-06-16/position_feature_input.parquet` |
| capital | FEATURES_READY | 1 | 2026-06-16 | `d66489c1ef814918` | `.runtime/phase9/features/2026-06-16/capital_policy_input.parquet` |

## Blocked Reasons

- none

## Warnings

- position_feature_empty_no_current_positions

## Safety Flags

- feature_generation_executed: True
- model_retraining_executed: False
- inference_executed: False
- order_plan_generation_executed: False
- broker_order_api_called: False
- open_d_started: False
- unlock_trade_called: False
- paper_ledger_fill_executed: False
- virtual_fill_executed: False
