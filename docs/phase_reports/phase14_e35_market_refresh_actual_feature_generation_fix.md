# Phase14-E35 Runtime v2 Market Refresh Actual Feature Generation Fix

## Purpose

Phase14-E35 fixes the Runtime v2 `market_refresh` job so it is no longer a checkpoint-only success path.

The job must execute the actual operations market refresh pipeline and require the four feature artifacts needed by the next Morning job:

- `.runtime/operations/feature_artifacts/{feature_date}/candidate_features.parquet`
- `.runtime/operations/feature_artifacts/{feature_date}/opportunity_feature_input.parquet`
- `.runtime/operations/feature_artifacts/{feature_date}/position_feature_input.parquet`
- `.runtime/operations/feature_artifacts/{feature_date}/capital_policy_input.parquet`

If those artifacts are not generated, Runtime v2 must not report `exit_code=0` as if the job completed successfully.

## Changes

Added Runtime v2 market refresh pipeline:

- `src/ai_fund_lab_v2/runtime_v2/market_refresh/pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/market_refresh/__init__.py`

Updated Runtime v2 daily operation CLI:

- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`

The CLI now runs `runtime_v2_market_refresh_pipeline` for `--job market_refresh`, records generated feature artifacts in the run manifest, and maps missing artifacts or blocked market refresh status to non-success exit states.

Added tests:

- `tests/runtime_v2/test_phase14e35_market_refresh_actual_feature_generation.py`

Updated scheduler tests to stub the market refresh pipeline where the test is not intended to perform actual market refresh work:

- `tests/runtime_v2/test_phase14e11_daily_operation_scheduler.py`

## Contract

Runtime v2 market refresh PASS requires:

- operations market refresh invoked
- canonical normalized market data update attempted
- feature refresh invoked
- all four required feature artifacts present for the requested business date
- generated artifact paths recorded in manifest

Runtime v2 market refresh must stop with `BLOCKED` or `REVIEW_REQUIRED` when:

- operations market refresh returns `BLOCK`
- any required feature artifact is missing
- feature refresh is not executed

Checkpoint-only success is no longer accepted.

## Actual Run

Command executed:

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

- `.runtime/runtime_state/run_manifest/2026-07-08/runtime-v2-market_refresh-2026-07-08-20260708T124800.205096+0000.json`

Result:

- `exit_code=10`
- `final_state=BLOCKED`
- `runtime_v2_market_refresh_pipeline=BLOCKED`
- `reason=market_refresh_blocked`
- `feature_artifact_dir=.runtime/operations/feature_artifacts/2026-07-08`
- `generated_feature_artifacts={}`
- missing artifacts:
  - `candidate_features.parquet`
  - `opportunity_feature_input.parquet`
  - `position_feature_input.parquet`
  - `capital_policy_input.parquet`

Market refresh detail:

- `.runtime/operations/market_refresh/2026-07-08/market_data_refresh_detail.json`
- `status=API_PARAM_ERROR`
- `allow_api_fetch=true`
- `blocked_reasons=["api_fetch_failed:JQuantsClientError", "data_until_before_decision_for"]`
- `data_until=2026-07-07`
- `not_yet_available_dates=["2026-07-08"]`

Feature refresh marker:

- `.runtime/operations/feature_refresh/2026-07-08/latest_features.json`
- `decision_for=2026-07-08`
- `data_until=2026-07-07`
- `latest_available_market_date=2026-07-07`
- `feature_freshness_status=MARKET_DATA_NOT_YET_AVAILABLE`
- `candidate_feature_path=.runtime/operations/feature_artifacts/2026-07-07/candidate_features.parquet`

This confirms Runtime v2 no longer reports a checkpoint-only PASS. It also confirms the required 2026-07-08 feature artifacts were not generated because the J-Quants/API/data freshness path did not provide 2026-07-08 market data.

## Morning Verification

Command executed after the blocked market refresh:

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

- `.runtime/runtime_state/run_manifest/2026-07-09/runtime-v2-morning-2026-07-09-20260708T125201.305595+0000.json`

Result:

- `exit_code=0`
- `final_state=CURRENT_STATE_LOADED`
- `morning_ai_planning_pending_pipeline=NO_SIGNAL`
- `reason=feature_input_missing:candidate,opportunity,position,capital`
- `pending_plan_id=pending-order-plan-morning-no-signal-2026-07-09`
- `items=0`

This confirms the operational acceptance item "the next Morning does not become `feature_input_missing`" is still unmet because the 2026-07-08 feature artifacts were not produced.

## Tests

Passed:

```bash
python3 -m pytest tests/runtime_v2/test_phase14e35_market_refresh_actual_feature_generation.py \
  tests/runtime_v2/test_phase14e11_daily_operation_scheduler.py \
  tests/runtime_v2/test_phase13_v_import_graph_cycle_guard.py
```

Result:

- `12 passed`

Full Runtime v2 suite:

```bash
python3 -m pytest tests/runtime_v2
```

Result:

- `338 passed`

## Prohibited Actions

Confirmed:

- Submit was not executed.
- Production order was not executed.
- Notification was not sent.
- launchd/plist was not changed.
- Phase9 Runtime was not called.
- Phase9 writer was not called.
- `.runtime/demo/...` Current path was not restored.
- Checkpoint-only success is no longer accepted by the market refresh job.

## Remaining Gap

Runtime v2 market refresh is now connected and fail-closed, but the actual 2026-07-08 feature artifact generation did not complete.

The remaining blocker is not the previous checkpoint-only CLI behavior. The remaining blocker is the upstream market data refresh path:

- J-Quants API fetch failed with `JQuantsClientError`.
- normalized market data was available only through `2026-07-07`.
- feature refresh produced/pointed to `2026-07-07` artifacts, not the required `2026-07-08` artifacts.
- 2026-07-09 Morning still stopped with `feature_input_missing`.

## Next Required Fix

Before Level2/Level3 daily operation can be accepted:

1. Resolve the J-Quants fetch/API parameter failure or define an explicit market-data-not-yet-available carryover contract.
2. Decide whether market refresh for business date `D` should generate artifacts for `D` only when `D` market data exists, or whether it should generate a named carryover artifact for the next Morning using `latest_available_market_date`.
3. Ensure Morning consumes the same artifact date contract that market refresh writes.
4. Re-run `market_refresh` and confirm `.runtime/operations/feature_artifacts/2026-07-08` contains all four required parquet files, or update the contract to a different explicit feature date without fallback ambiguity.
5. Re-run the next Morning and confirm it does not stop with `feature_input_missing`.

## Final Judgment

`PHASE14E35_REVIEW_REQUIRED`

