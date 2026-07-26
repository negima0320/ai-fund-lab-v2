# Phase20-BL Historical Market Evidence Source Contract

## Status

```text
PHASE20_BL_HISTORICAL_MARKET_EVIDENCE_SOURCE_CONTRACT_FIXED
```

Supporting judgments:

```text
PHASE20_BL_ROOT_CAUSE_CONFIRMED
PHASE20_BL_HISTORICAL_SOURCE_ALIGNMENT_PASS
PHASE20_BL_MARKET_EVIDENCE_LINEAGE_PASS
PHASE20_BL_FUTURE_LEAKAGE_GUARD_PASS
PHASE20_BL_PRODUCTION_NON_REGRESSION_PASS
PHASE20_BL_DEMO_NON_REGRESSION_PASS
PHASE20_BL_DATA_READINESS_TRUTHFULNESS_PASS
PHASE20_BL_USER_RANGE_RERUN_READY
```

## Incident Run

```text
run_id = runtime-test-historical-extended-smoke-20260724T014457911285Z
profile = historical-extended-smoke
start_date = 2022-08-01
planned_business_days = 20
completed_days = 0
final_status = HALT
stop_point = 2022-08-01:data_readiness
runtime_cli_exit_code = 20
runtime_test_exit_code = 30
```

The run is treated as abandoned. It was not resumed.

## Evidence

Market Refresh passed up to feature generation:

```text
market_refresh exit_code = 0
market_refresh pipeline status = PASS
historical_asof_status = PASS
historical_logical_input_status = PASS
feature_refresh_status = FEATURES_READY
data_quality_status = PASS
candidate_feature_rows = 4258
selected_feature_date = 2022-08-01
```

Historical as-of selected:

```text
selected_source_role = acquisition_staging
selected_normalized_ohlcv_path = .runtime/market_data_acquisition/runs/jquants-acquisition-20210802-20260714-bh/raw_normalized/jquants/equities_bars_daily/data.parquet
selected_raw_ohlcv_path = .runtime/market_data_acquisition/runs/jquants-acquisition-20210802-20260714-bh/raw/jquants/equities_bars_daily/data.parquet
selected_trading_calendar_path = .runtime/market_data_acquisition/runs/jquants-acquisition-20210802-20260714-bh/raw/jquants/trading_calendar/data.parquet
feature_lookback_coverage.status = PASS
future_rows_excluded_from_consumer = true
```

Market Evidence before the fix:

```text
market_status = REVIEW_REQUIRED
market_evidence_reason = quote_source_empty
quote_source = .runtime/operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet
quote_count = 0
symbol_count = 0
```

The operations canonical quote source starts at `2026-02-16`, so it has no `2022-08-01` rows.

## Root Cause

```text
HISTORICAL_MARKET_EVIDENCE_CONSUMER_BYPASSED_HISTORICAL_ASOF_LOGICAL_INPUT
```

Feature Refresh consumed the Historical as-of logical input selected by the resolver. Market Evidence independently read operations canonical OHLCV from:

```text
.runtime/operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet
```

That created a Historical-only Consumer wiring gap:

```text
Feature Refresh -> Historical as-of resolver -> acquisition_staging logical input -> PASS
Market Evidence -> operations canonical direct read -> 2022 rows absent -> quote_source_empty
```

Classification:

```text
A. Historical限定のConsumer接続漏れ
```

Production and Demo were not switched to acquisition staging.

## Source Contract

Production:

```text
Feature source = operations canonical / feature artifacts
Market Evidence quote source = operations canonical normalized OHLCV
Safety market input = Market Evidence artifact
Judgment = unchanged
```

Demo:

```text
Feature source = operations canonical / feature artifacts
Market Evidence quote source = operations canonical normalized OHLCV
Safety market input = Market Evidence artifact
Judgment = unchanged
```

Historical:

```text
Feature source = Historical as-of logical input
Market Evidence quote source = Historical as-of logical input
Safety market input = Market Evidence artifact produced from the same logical authority
Judgment = fixed
```

Architecture alignment:

```text
Historical Runtime consumer input must be a logical as-of view.
Historical consumers must not consume the unbounded physical source for a replay business date.
Operations canonical remains the Production/Demo authority.
Acquisition staging is selected only by Historical as-of resolver when operations canonical lacks required lookback.
Fail-closed behavior remains required for missing, empty, stale, future-leaking, or unresolved sources.
```

## Fix

Changed files:

```text
src/ai_fund_lab_v2/runtime_v2/market_refresh/evidence.py
src/ai_fund_lab_v2/runtime_v2/market_refresh/pipeline.py
src/ai_fund_lab_v2/runtime_v2/data_readiness.py
tests/runtime_v2/test_phase15aw_market_quote_evidence_producer.py
tests/runtime_v2/test_phase17_l_historical_asof_and_evidence_isolation.py
```

Implementation:

1. `produce_market_quote_evidence` now accepts optional `quote_source_path` and `source_authority`.
2. Default behavior remains operations canonical, preserving Production/Demo.
3. Historical Market Refresh passes the resolver-materialized logical normalized OHLCV path to Market Evidence.
4. Historical Market Evidence records lineage fields:

```text
source_role
quote_source
quote_source_authority
source_business_date
logical_cutoff
historical_asof_status
historical_logical_input_manifest_path
historical_logical_input_manifest_hash
future_rows_excluded
source_authority
```

5. Data Readiness now distinguishes an existing `REVIEW_REQUIRED` Market Evidence artifact from a missing artifact. It reports the artifact reason, such as `quote_source_empty`, and does not put existing invalid artifacts in `missing_evidence`.

No date-specific branch, 2022-only branch, BK-RANGE branch, Historical Extended Smoke skip, status override, PM/Candidate/Opportunity change, threshold change, Accepted Generation change, broker connection, training, or calibration was added.

## Probe

Isolated short probe:

```text
target_date = 2022-08-01
runtime_mode = historical
probe type = resolver materialize + Market Evidence producer
20BD fresh-run = not executed
```

Result:

```text
historical_logical_input_status = PASS
historical_asof_status = PASS
selected_source_role = acquisition_staging
market_evidence_status = READY
market_evidence_reason = market_evidence_ready
quote_count = 4067
symbol_count = 4067
quote_source = /private/tmp/phase20_bl_probe/.../raw_normalized/jquants/equities_bars_daily/data.parquet
quote_source_authority = .runtime/market_data_acquisition/runs/jquants-acquisition-20210802-20260714-bh/raw_normalized/jquants/equities_bars_daily/data.parquet
market_date = 2022-08-01
latest_available_market_date = 2022-08-01
future_rows_after_business_date_in_logical_quote_source = 0
future_rows_excluded = true
```

Probe artifact:

```text
reports/phase20_bl_historical_market_evidence_source_contract/probe_summary.json
```

`candidate_universe_symbol_count` was `0` in the isolated Market Evidence probe because no candidate symbols were passed to the producer at this stage. This is treated as valid empty for the producer-level probe, not as a candidate universe readiness assertion.

## Validation

Executed:

```text
PYTHONPYCACHEPREFIX=/private/tmp/pycache PYTHONPATH=src:. python3 -m pytest -q tests/runtime_v2/test_phase15aw_market_quote_evidence_producer.py tests/runtime_v2/test_phase17_l_historical_asof_and_evidence_isolation.py
PYTHONPYCACHEPREFIX=/private/tmp/pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/market_refresh/evidence.py src/ai_fund_lab_v2/runtime_v2/market_refresh/pipeline.py src/ai_fund_lab_v2/runtime_v2/data_readiness.py
```

Result:

```text
20 passed
py_compile PASS
```

Coverage:

```text
Historical old-date logical source used by Market Evidence = PASS
Historical pipeline passes resolver-selected quote_source_path = PASS
Production/Demo default operations canonical source preserved = PASS
Historical future rows excluded = PASS
Unresolved source remains fail-closed = PASS
Empty selected source remains REVIEW_REQUIRED = PASS
Data Readiness existing REVIEW_REQUIRED artifact not mislabeled missing = PASS
```

## Not Executed

```text
20BD Historical fresh-run
resume
Bull rerun
Bear rerun
Range rerun
Broker connection
Training
Calibration
Accepted Generation change
```

## User Rerun Command

Use a fresh run, not resume:

```bash
cd /Users/negishi/work/ai-fund-lab-v2
export PYTHONPATH=src:.

python3 scripts/runtime_test.py fresh-run \
  --profile historical-extended-smoke \
  --business-days 20 \
  --start-date 2022-08-01 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

Expected first-day checks:

```text
2022-08-01 market_refresh PASS
market_evidence_status READY
quote_count > 0
2022-08-01 data_readiness PASS
completed_days advances beyond first day
Corporate Action HALTなし
completed_days = 20
final_judgment = PASS
```

## Residual Risk

- Full Data Readiness was not executed as an end-to-end 2022-08-01 Runtime job by Codex; unit coverage and isolated Market Evidence probe passed.
- `AdjFactor` Corporate Action fail-closed behavior remains unchanged. A later campaign date may still correctly halt if an actually traded symbol intersects a non-1.0 adjustment event.
- Market Evidence now records source lineage, but no separate schema file was introduced in this phase because the JSON artifact remains backward-compatible with additive fields.

## Acceptance

```text
BL-R1 Historical Market Evidence source is resolver-selected logical authority = PASS
BL-R2 Feature and Market Evidence use the same Historical logical authority = PASS
BL-R3 2022-08-01 Market Evidence produces non-empty valid quote summary = PASS
BL-R4 No future rows are visible to Historical consumers = PASS
BL-R5 Production source contract is verified and not unintentionally changed = PASS
BL-R6 Demo source contract is verified and not unintentionally changed = PASS
BL-R7 Empty or unresolved source remains fail-closed = PASS
BL-R8 No date-specific or test-profile-specific hack exists = PASS
BL-R9 Data Readiness reports artifact existence and invalid status truthfully = PASS
BL-R10 Codex did not execute the 20BD Historical fresh-run = PASS
```

Final judgment:

```text
PHASE20_BL_HISTORICAL_MARKET_EVIDENCE_SOURCE_CONTRACT_FIXED
```
