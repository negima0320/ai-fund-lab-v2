# Phase17-B1I-B PM Runtime Adapter Authority Resolution

Final judgment: `PHASE17_B1I_B_PM_ADAPTER_AUTHORITY_ACCEPTED`

## Authority
- Authority mode: `ACCEPTED_CURRENT_PATH`
- Accepted current path: `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py`
- Source hash: `ae3aaae66273d5ed149ef4064659f5ec9f88d4ef05c0770ec6f759311b95e5cc`
- New PM set: `control.position_management.accepted_set@sha256-987be698d39a6887`
- Old PM set: `control.position_management.accepted_set@sha256-c3849b55a8a4f9f4`

## Gates
- PM_CURRENT_SOURCE_REVIEWED: `PASS`
- PM_ACCEPTED_CURRENT_PATH_CONTRACT_ACCEPTED: `PASS`
- PM_ARTIFACT_SET_VALIDATED: `PASS`
- PM_REGRESSION_EVIDENCE_PASS: `PASS`
- SELL_PLANNING_REGRESSION_PASS: `PASS`
- CONSUMER_COMPATIBILITY_PASS: `PASS`
- PM_ARTIFACT_SET_ACCEPTED: `PASS`
- OLD_PM_SET_LEGACY: `PASS`
- EXACTLY_ONE_ACTIVE_PM_SET: `PASS`
- PM_SOURCE_HASH_PREFLIGHT_PASS: `PASS`
- PM_SOURCE_HASH_MISMATCH_FAIL_CLOSED: `PASS`
- REGISTRY_EVENT_LOG_PASS: `PASS`
- REGISTRY_INDEX_PASS: `PASS`
- REGISTRY_CHECKPOINT_PASS: `PASS`
- RESOLVER_RETURNS_NEW_PM_SET: `PASS`
- CURRENT_UNCHANGED: `PASS`
- LEDGER_UNCHANGED: `PASS`
- PENDING_UNCHANGED: `PASS`
- RUNTIME_STATE_UNCHANGED: `PASS`
- DEMO_PM_UNCHANGED: `PASS`
- PRODUCTION_PM_UNCHANGED: `PASS`
- HISTORICAL_PM_SAME_AUTHORITY: `PASS`
- NO_PM_SEMANTIC_CHANGE: `PASS`
- NO_TEST_ONLY_AUTHORITY: `PASS`

## Registry
- Event log: `PASS`
- Index: `PASS`
- Checkpoint: `PASS`
- Active eligible PM set count: `PASS`

## Tests
- `/Applications/Xcode.app/Contents/Developer/usr/bin/python3 -m pytest -q tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py::test_phase32_aa_pm_runtime_adapter_payload_materializes_current_campaign tests/runtime_v2/test_phase23_i_strategy_planning_authority.py::test_phase32_y_strategy_origin_sell_exit_materializes_pm_provenance_for_multiple_symbols tests/runtime_v2/test_phase23_i_strategy_planning_authority.py::test_phase32_y_strategy_origin_sell_exit_materializes_pm_provenance_to_ledger_and_strict_prior tests/runtime_v2/test_phase23_i_strategy_planning_authority.py::test_phase32_aa_strategy_origin_sell_exit_preserves_campaign_with_blank_runtime_pm_projection tests/runtime_v2/test_phase23_i_strategy_planning_authority.py::test_phase32_y_strategy_origin_sell_exit_pm_provenance_fail_closed_controls tests/runtime_v2/test_phase23_i_strategy_planning_authority.py::test_phase32_y_partial_reduce_and_legacy_pending_shape_remain_safe tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py::test_phase32_t_actual_sell_path_populates_persistent_ledger_pm_and_campaign_provenance`: `PASS`
- `/Applications/Xcode.app/Contents/Developer/usr/bin/python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/position_management/producer.py src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py tests/runtime_v2/test_phase23_i_strategy_planning_authority.py tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py`: `PASS`
