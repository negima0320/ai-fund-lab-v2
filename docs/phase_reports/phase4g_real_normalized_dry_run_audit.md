# AI Fund Lab vNext Phase4-G Real Normalized Data Dry-run Audit

## Audit Result

- phase: `Phase4-G Real Normalized Data Dry-run / Trading Calendar Window`
- status: `complete`

## Checks

- `daily_quotes_normalized_discovery_implemented`: OK
- `dry_run_script_exists`: OK
- `future_row_exclusion_recorded`: OK
- `jsonl_or_parquet_supported`: OK
- `lookback_business_day_window_defined`: OK
- `max_codes_and_max_rows_limit_scope`: OK
- `missing_data_skips_safely`: OK
- `non_business_as_of_date_defined`: OK
- `non_implementation_boundary_present`: OK
- `normalized_data_reader_exists`: OK
- `phase4e_mock_builder_compatible`: OK
- `phase4f_loader_contract_connected`: OK
- `phase4g_files_present`: OK
- `required_input_docs_present`: OK
- `small_range_read_implemented`: OK
- `trading_calendar_window_helper_exists`: OK

## Summary

Phase4-G connects small-range normalized raw discovery/read to the Candidate AI loader contract with a trading-calendar window.
It keeps missing-data environments safe with SKIPPED status and does not implement full feature generation, labels, training, inference, backtest, trading, or ordering.

## pytest

`python3 scripts/check_candidate_real_normalized_dry_run.py && python3 scripts/audit_phase4g_real_normalized_dry_run.py && python3 scripts/build_candidate_features_mock.py && python3 scripts/audit_phase4e_candidate_feature_builder_mock.py && python3 -m pytest tests/test_phase4g_real_normalized_dry_run.py && python3 -m pytest -q`
