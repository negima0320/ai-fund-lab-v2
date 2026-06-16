# Phase9-L1 Training Dataset Safety Audit

- status: TRAINING_DATASETS_READY
- data_until: 2026-06-15
- safe_train_until: 2026-05-18
- train_until: 2026-05-18
- label_horizon: 20
- dataset_manifest_path: `.runtime/phase9/training_dataset_candidates/2026-05-18/training_dataset_manifest.json`

## Datasets

| AI | status | rows | min_date | max_date | code_count | schema_hash | forbidden | leakage |
| --- | --- | ---: | --- | --- | ---: | --- | --- | --- |
| candidate | TRAINING_DATASET_READY | 4974436 | 2021-06-14 | 2026-05-18 | 4780 | `2d530e6e6b30d7d2` | OK/OK | OK |
| opportunity | TRAINING_DATASET_READY | 4974436 | 2021-06-14 | 2026-05-18 | 4780 | `2d530e6e6b30d7d2` | OK/OK | OK |

## Blockers

- none

## Safety

- model_retraining_executed: False
- inference_executed: False
- order_plan_generation_executed: False
- broker_order_api_called: False
- virtual_fill_executed: False

## Next Action

- Proceed to Phase9-L2 controlled retrain execution plan; do not promote models automatically.
