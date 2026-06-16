# Phase9-H Preflight Data / Model Freshness Audit

- decision_for: 2026-06-16
- judgment: DATA_UPDATE_REQUIRED

## Summary

- raw daily_quotes response latest: 2026-06-12
- raw daily_quotes table latest: 2026-06-01
- normalized daily_quotes latest: 2026-06-01
- listed_info latest: 2026-06-01
- trading_calendar latest: 2026-06-07
- data_until candidate: 2026-06-01
- Paper Ledger latest: MISSING

## Market Data

| target | status | latest_date | rows | path |
| --- | --- | ---: | ---: | --- |
| raw_daily_quotes | PRICE_ANOMALY_DETECTED | 2026-06-01 | 4449 | `.runtime/data/raw/jquants/equities_bars_daily/data.parquet` |
| normalized_daily_quotes | OK | 2026-06-01 | 1980 | `.runtime/data/raw_normalized/jquants/equities_bars_daily/data.parquet` |
| listed_info | OK | 2026-06-01 | 4449 | `.runtime/data/raw/jquants/listed_issues/data.parquet` |
| trading_calendar | OK | 2026-06-07 | 72 | `.runtime/data/raw/jquants/trading_calendar/data.parquet` |

## Feature Artifacts

| AI | status | feature_data_until | rows | feature_schema_hash | path |
| --- | --- | ---: | ---: | --- | --- |
| Candidate AI | AVAILABLE | 2026-06-01 | 1800 | 5dee5f671b19abe3 | `.runtime/candidate_ai/tmp/candidate_loader_contract_rows_2026-06-01.json` |
| Opportunity AI | AVAILABLE | 2026-06-12 | 20 | a83bcb0c0ce03633 | `reports/opportunity_ai/phase5f/latest_opportunity_top20.csv` |
| Position Management AI | AVAILABLE | 2026-06-12 | 6 | e3d4333d9ad3c4f6 | `reports/position_management_ai/phase6b_position_feature_dry_run.csv` |
| Capital Allocation AI / policy | AVAILABLE | 2026-06-15 | 7 | 3174a720c1f80bad | `reports/capital_allocation_ai/phase7a/fixture_inputs/position_signals.csv` |

## Models / Policies

| AI | model_version / policy | train_until | data_until | leakage | eligibility | manifest |
| --- | --- | ---: | ---: | --- | --- | --- |
| Candidate AI |  |  |  | OK | NOT_ELIGIBLE | `reports/candidate_ai/full_range/phase4u_controlled_batch_expansion_summary.json` |
| Opportunity AI | opportunity_model_phase5e_v1 |  |  | OK | NOT_ELIGIBLE | `reports/opportunity_ai/phase5p2/market_sector/training/opportunity_training_metrics.json` |
| Position Management AI | position_management_policy_phase6i_winner_holding_v1 |  |  | OK | NOT_ELIGIBLE | `reports/position_management_ai/phase6m_top3_fixed_vs_position_summary.json` |
| Capital Allocation AI / policy | phase7d_realistic_execution_constraints_v1 |  |  | PASS | NOT_ELIGIBLE | `reports/capital_allocation_ai/phase7d/validation_summary.json` |

## Phase9 Operation Readiness

- Daily Operation Runner importable: True
- Daily operation dry-run executed by this audit: False
- dry-run execution skipped reason: Phase9-H audit forbids inference and only checks static executability.
- Market Data Readiness Checker READY: False
- Model Eligibility Checker available: True
- Daily Report output root creatable: True
- Paper Ledger latest exists: False

## Next Actions

- J-Quants daily_quotes/listed_info を更新し、normalized data を decision_for 以上まで再生成する。
- market data 更新後に feature artifact を生成し、feature data_until を揃える。
- active model / policy manifest の train_until, data_until, feature_schema_hash, leakage_audit_status, artifact path を確認し、必要なら再学習または eligibility review を行う。
- Phase9運用開始用の initial Paper Ledger を作成し latest.json として保存する。

## Prohibited Actions

- jquants_api_fetch_executed: False
- feature_generation_executed: False
- model_retraining_executed: False
- inference_executed: False
- paper_ledger_fill_executed: False
- virtual_fill_executed: False
- broker_order_api_called: False
- open_d_started: False
- unlock_trade_called: False
- live_order_allowed: False
- scheduler_auto_registered: False
- full_backtest_executed: False
