# Phase18-Y Accepted Atomic BUY AI Bundle Contract Completion

- Run ID: `phase18y-contract-completion-20260717T000000Z`
- Final judgment: `PHASE18_Y_CONTRACT_COMPLETION_BLOCKED`
- Contract completion status: `BLOCK`
- Superseding transaction: `promotion-tx-phase18y-contract-completion-1081babc49b5d26b`
- Registry unchanged: `True`
- Runtime accepted state unchanged: `True`

## Materialized Runtime Baseline

- Path: `.runtime/artifact_registry/promotion_candidates/transactions/promotion-tx-phase18y-contract-completion-1081babc49b5d26b/runtime_baseline.json`
- Baseline identity: `buy_ai_bundle_phase18h_1081babc49b5d26b:recent_holdout_materialized_baseline`
- Baseline hash: `f4da2ae99fae014cb7bc9982cc75e591524c102b953212835cb3722e0777cd16`
- Row count: `1440`
- Date range: `{'authority_split': 'recent_holdout', 'start': '2026-04-01', 'end': '2026-05-15'}`
- Current Runtime evidence used: `False`

## Freshness Metadata

- model_training_cutoff: `2024-12-02`
- label_safe_cutoff: `2026-06-04`
- training_dataset_max_date: `2026-05-15`
- formal_trading_calendar_ref: `artifact:.runtime/data/raw/jquants/trading_calendar/data.parquet`
- model_training_lag_business_days: `69`
- model_training_lag_status: `BLOCK`

## Eligibility

- Decision: `RUNTIME_USE_ELIGIBILITY_BLOCKED`
- runtime_use_eligible: `False`
- registry_accepted_event_requested: `False`

## Authority Review

- approval_scope: `ACCEPTED_EVENT_PRECHECK_ONLY`
- registry_accepted_event_authorized: `False`
- reviewer: `AI Lifecycle Authority Simulator Phase18-Y`
- blocking_items: `['model_training_lag_status']`

## Non-Execution Confirmation

- phase18j_report_value_copied: `False`
- synthetic_baseline: `False`
- current_runtime_evidence_used_as_baseline: `False`
- promotion_candidate_direct_runtime_adoption: `False`
- latest_or_manual_fallback: `False`
- registry_accepted_state_updated: `False`
- runtime_accepted_state_created: `False`
- bv15_relaxed: `False`
- forced_buy: `False`
- broker_write: `False`
- production_runtime_executed: `False`
- historical_fresh_run_executed: `False`

## Validation

- `PYTHONPATH=src PYTHONPYCACHEPREFIX=/tmp/phase18y_pycache python3 -m pytest tests/ai_lifecycle/test_phase18y_contract_completion.py -q`: `4 passed, 1 sandbox CPU-count warning`
- `PYTHONPATH=src PYTHONPYCACHEPREFIX=/tmp/phase18y_pycache python3 -m py_compile scripts/phase18y_accepted_atomic_buy_ai_bundle_contract_completion.py`: `PASS`
- `python3 -m json.tool reports/phase_reports/phase18_y_accepted_atomic_buy_ai_bundle_contract_completion.json`: `PASS`

## Final

`PHASE18_Y_CONTRACT_COMPLETION_BLOCKED`
