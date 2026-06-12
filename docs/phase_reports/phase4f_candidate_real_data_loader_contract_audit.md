# AI Fund Lab vNext Phase4-F Candidate Real Data Loader Contract Audit

## Audit Result

- phase: `Phase4-F Candidate Real Data Loader Contract / Adapter Design`
- status: `complete`

## Checks

- `daily_quotes_normalized_adapter_exists`: OK
- `dropped_future_row_count_recorded`: OK
- `future_rows_filtered`: OK
- `input_manifest_hash_rule_exists`: OK
- `input_schema_validation_exists`: OK
- `non_implementation_boundary_present`: OK
- `phase4e_mock_builder_compatible`: OK
- `phase4f_files_present`: OK
- `real_data_dry_run_script_exists`: OK
- `real_data_loader_contract_exists`: OK
- `required_input_docs_present`: OK
- `runtime_outputs_written`: OK
- `schema_mapping_documented`: OK
- `source_snapshot_id_rule_exists`: OK
- `standard_input_columns_defined`: OK
- `trading_calendar_window_rule_documented`: OK

## Summary

Phase4-F fixes the adapter contract between Phase1 daily_quotes_normalized and Candidate Feature Builder standard input.
It validates schema, filters future rows, records loader manifest/audit metadata, and keeps Phase4-E mock builder compatible.
It does not implement full real-data feature generation, labels, training, inference, backtest, Paper Trading, ordering, or portfolio auto-update.

## pytest

`python3 scripts/check_candidate_real_data_loader_contract.py && python3 scripts/audit_phase4f_candidate_real_data_loader_contract.py && python3 scripts/build_candidate_features_mock.py && python3 scripts/audit_phase4e_candidate_feature_builder_mock.py && python3 -m pytest tests/test_phase4f_candidate_real_data_loader_contract.py && python3 -m pytest -q`
