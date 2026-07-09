# Phase14-E36 Market Data Feature-Date Contract / Carryover Policy Fix

## Purpose

Phase14-E36 fixes the mismatch between Runtime v2 `market_refresh` output and Morning feature input.

Phase14-E35 made `market_refresh` fail closed instead of checkpoint-only PASS, but the next Morning still became `feature_input_missing` because `feature_artifacts/2026-07-08` was absent while the latest available market data and artifacts were for `2026-07-07`.

E36 defines an explicit feature-date contract:

- Market Refresh records the requested feature date.
- Market Refresh records the selected feature date.
- Morning reads the same selected feature date.
- Carryover is allowed only when explicit, fresh enough, and fully evidenced.
- Feature input missing is no longer a normal `NO_SIGNAL`.

## Feature-Date Contract

Runtime v2 now distinguishes:

- `requested_feature_date`: the feature date originally requested by operation schedule.
- `selected_feature_date`: the feature date Morning must actually read.
- `latest_available_market_date`: latest market date confirmed by the market data pipeline.
- `carryover_used`: whether selected date differs from requested date.
- `carryover_reason`: why carryover was selected.
- `freshness_lag_business_days`: business-day lag between latest/selected and requested date.
- `freshness_limit_business_days`: maximum acceptable carryover lag.

Carryover is allowed when:

- requested feature artifacts are missing;
- latest available artifacts exist;
- all four required feature inputs are present for the selected date;
- selected price source date matches `selected_feature_date`;
- business-day lag is within the configured limit, currently `1`.

Carryover is not silent fallback. It is written to artifact, manifest, OrderPlan, Pending, Report, and Audit-derived report outputs.

## Required Feature Artifacts

The selected feature date must contain all four files:

- `candidate_features.parquet`
- `opportunity_feature_input.parquet`
- `position_feature_input.parquet`
- `capital_policy_input.parquet`

If these are missing and no valid carryover exists, Morning must stop as `REVIEW_REQUIRED` or `BLOCKED`, not `NO_SIGNAL`.

## Implementation

Added:

- `src/ai_fund_lab_v2/runtime_v2/market_refresh/feature_date_contract.py`
- `tests/runtime_v2/test_phase14e36_feature_date_contract_carryover_policy.py`

Updated:

- `src/ai_fund_lab_v2/runtime_v2/market_refresh/pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/market_refresh/__init__.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`
- `src/ai_fund_lab_v2/runtime_v2/pending/models.py`
- `src/ai_fund_lab_v2/runtime_v2/pending/reader.py`
- `src/ai_fund_lab_v2/runtime_v2/report/markdown_writer.py`
- `tests/runtime_v2/test_phase14e15_morning_ai_planning_pending_connection.py`
- `tests/runtime_v2/test_phase14e35_market_refresh_actual_feature_generation.py`

## Market Refresh Output Contract

`market_refresh` now writes:

- `.runtime/operations/feature_date_contract/{requested_feature_date}.json`

For the actual 2026-07-08 case:

- `requested_feature_date=2026-07-08`
- `selected_feature_date=2026-07-07`
- `latest_available_market_date=2026-07-07`
- `carryover_used=true`
- `carryover_reason=requested_feature_date_missing_latest_available_within_freshness_limit`
- `freshness_lag_business_days=1`
- `status=PASS`

The run manifest also records the same contract details.

## Morning Input Contract

Morning resolves feature input as follows:

1. If `--feature-date` is explicitly provided, that date is treated as the requested and selected date.
2. Otherwise, requested date defaults to the previous calendar day.
3. Morning reads `.runtime/operations/feature_date_contract/{requested_feature_date}.json` when present.
4. Morning uses `selected_feature_date` from the contract.
5. Morning requires all selected feature artifacts and selected-date price source.
6. Missing feature input or missing reliable price source becomes `REVIEW_REQUIRED`, not `NO_SIGNAL`.

This keeps E28 price source contract aligned with feature-date selection: `price_as_of` must match `selected_feature_date`.

## Actual Market Refresh Verification

Command:

```bash
PYTHONPATH=src python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation \
  --mode demo \
  --job market_refresh \
  --business-date 2026-07-08 \
  --submit-enabled false \
  --notification-mode payload-only \
  --stop-on-review-required \
  --stop-on-blocked \
  --market-refresh-allow-api-fetch true
```

Manifest:

- `.runtime/runtime_state/run_manifest/2026-07-08/runtime-v2-market_refresh-2026-07-08-20260708T130831.523598+0000.json`

Result:

- `exit_code=0`
- `final_state=CURRENT_STATE_LOADED`
- `runtime_v2_market_refresh_pipeline=PASS`
- `requested_feature_date=2026-07-08`
- `selected_feature_date=2026-07-07`
- `latest_available_market_date=2026-07-07`
- `carryover_used=true`
- `freshness_lag_business_days=1`
- generated artifacts:
  - `candidate_features.parquet`
  - `opportunity_feature_input.parquet`
  - `position_feature_input.parquet`
  - `capital_policy_input.parquet`

J-Quants fetch still recorded:

- `api_fetch_failed:JQuantsClientError`

This is no longer hidden. It is preserved as upstream market refresh evidence while the selected feature input is explicitly carried over.

## Actual Morning Verification

Command:

```bash
PYTHONPATH=src python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation \
  --mode demo \
  --job morning \
  --business-date 2026-07-09 \
  --submit-enabled false \
  --notification-mode payload-only \
  --stop-on-review-required \
  --stop-on-blocked
```

Manifest:

- `.runtime/runtime_state/run_manifest/2026-07-09/runtime-v2-morning-2026-07-09-20260708T131208.558338+0000.json`

Result:

- `exit_code=0`
- `morning_ai_planning_pending_pipeline=PASS`
- `feature_date=2026-07-07`
- `requested_feature_date=2026-07-08`
- `selected_feature_date=2026-07-07`
- `carryover_used=true`
- `freshness_lag_business_days=1`
- `selected_count=5`
- `price_source_status=PASS`
- `feature_input_missing` did not occur.

Pending:

- `state=APPROVED`
- `items=5`
- `feature_date_contract.requested_feature_date=2026-07-08`
- `feature_date_contract.selected_feature_date=2026-07-07`
- `feature_date_contract.carryover_used=true`
- all pending item `price_as_of=2026-07-07`

## Report / Audit Output

`reports/public/runtime_v2/latest.md` now includes market data freshness:

- requested feature date
- selected feature date
- latest available market date
- carryover flag
- carryover reason
- freshness lag
- contract status/reason

`reports/public/runtime_v2/latest.json` includes the same data under the warning summary.

## Stale Carryover Policy

If carryover lag exceeds `freshness_limit_business_days`, Morning stops with:

- `REVIEW_REQUIRED`
- no submit-capable Pending items

This was covered by test with selected `2026-07-06` for requested `2026-07-08`, where `freshness_lag_business_days=2`.

## Tests

Targeted tests:

```bash
python3 -m pytest \
  tests/runtime_v2/test_phase14e36_feature_date_contract_carryover_policy.py \
  tests/runtime_v2/test_phase14e35_market_refresh_actual_feature_generation.py \
  tests/runtime_v2/test_phase14e15_morning_ai_planning_pending_connection.py
```

Result:

- `11 passed`

Full Runtime v2 tests:

```bash
python3 -m pytest tests/runtime_v2
```

Result:

- `341 passed`

## Prohibited Actions

Confirmed:

- Submit was not executed.
- Production order was not executed.
- Notification was not sent.
- launchd/plist was not changed.
- Phase9 Runtime was not used.
- Phase9 writer was not used.
- Checkpoint-only PASS was not restored.

## Acceptance Mapping

- Market Refresh and Morning feature-date contract are aligned: PASS.
- `feature_input_missing` is not normal `NO_SIGNAL`: PASS.
- Carryover metadata is recorded: PASS.
- Stale carryover stops as `REVIEW_REQUIRED`: PASS.
- E28 price source contract is aligned with `selected_feature_date`: PASS.
- Report/Audit-derived output includes market data freshness: PASS.
- tests/runtime_v2 PASS: PASS.

## Final Judgment

`PHASE14E36_FEATURE_DATE_CONTRACT_FIXED`

