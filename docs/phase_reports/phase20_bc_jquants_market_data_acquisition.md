# Phase20-BC J-Quants Runtime Market Data Acquisition

## Final Status

```text
PHASE20_BC_JQUANTS_MARKET_DATA_ACQUISITION_READY
```

Phase20-BC implemented a safe staging acquisition path for J-Quants daily OHLCV that can feed Phase20-BB bootstrap. Codex did not execute a five-year fetch, did not mutate common Runtime OHLCV, and did not run Historical, Training, Calibration, or Broker operations.

## Scope

This phase adds:

- J-Quants daily quote acquisition into staging only.
- Chunked long-period fetching.
- Pagination handling.
- Bounded retry handling.
- Resume with binding validation.
- Raw staging storage.
- Normalized staging generation using the existing Runtime normalizer.
- Final staging validation.
- Bootstrap handoff commands.

It does not add a backtest-only data path and does not turn a training dataset into Runtime market data.

## Existing Client and Refresh Evidence

J-Quants client:

```text
src/ai_fund_lab_v2/data_sources/jquants/client.py
```

Daily quotes endpoint:

```text
/v2/equities/bars/daily
```

Authentication:

```text
x-api-key from JQUANTS_API_KEY via load_settings()
```

Secret handling:

```text
API key is not written to evidence, reports, or logs.
```

Pagination token:

```text
pagination_key
```

Existing daily refresh:

```text
src/ai_fund_lab_v2/paper_trading/market_data_refresh.py
```

Daily refresh merges existing records with incoming records, then normalizes with:

```text
ai_fund_lab_v2.data_quality.normalization.normalize_daily_quotes
```

The adjusted price contract is preserved:

```text
AdjO / AdjH / AdjL / AdjC / AdjVo if complete, otherwise O / H / L / C / Vo
```

## Acquisition Contract

Implemented in:

```text
src/ai_fund_lab_v2/runtime_v2/market_data_acquisition.py
```

Default staging layout:

```text
.runtime/market_data_acquisition/runs/<acquisition_run_id>/
  plan.json
  state.json
  chunks/<chunk_id>/raw.parquet
  raw/jquants/equities_bars_daily/data.parquet
  raw_normalized/jquants/equities_bars_daily/data.parquet
```

Acquisition writes staging artifacts only. It never writes:

```text
.runtime/operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet
```

## Chunk / Resume / Retry

Default chunking:

```text
month
```

Each chunk records:

```text
chunk_id
start_date
end_date
status
request_count
page_count
row_count
first_date
last_date
content_hash
started_at
completed_at
error
retry_count
```

Resume:

- Completed chunks are skipped only when the chunk parquet exists and the content hash matches state.
- The state binding includes start date, end date, endpoint, chunk strategy, and schema version.
- A run_id cannot be resumed with a different acquisition binding.

Retry:

- Retryable: `API_RATE_LIMIT`, `API_SERVER_ERROR`, `API_NETWORK_ERROR`
- Non-retryable: `API_AUTH_ERROR`, `API_PARAM_ERROR`
- Retries are bounded. Infinite retry is prohibited.
- Pagination token cycles and max page overflow fail closed.

## Validation

Final staging validation checks:

```text
J-Quants lineage
schema
earliest_date
latest_date
row_count
unique_business_days
Date/Code duplicate count
null count
OHLC integrity
negative price count
negative volume count
requested range coverage
future date contamination
training-only column contamination
content hash
```

Final success judgment:

```text
ACQUISITION_SOURCE_READY
```

Final failure judgment:

```text
ACQUISITION_SOURCE_BLOCKED
```

## Evidence

Evidence root:

```text
reports/phase20_bc_jquants_market_data_acquisition/
```

Generated contract evidence:

```text
existing_jquants_client_inventory.json
existing_daily_refresh_contract.json
api_pagination_contract.json
acquisition_chunk_contract.json
resume_contract.json
retry_and_rate_limit_contract.json
raw_storage_contract.json
normalization_contract.json
staging_validation_contract.json
bootstrap_handoff_contract.json
security_and_secret_audit.json
test_summary.json
```

Machine-readable report:

```text
reports/phase_reports/phase20_bc_jquants_market_data_acquisition.json
```

## Validation Executed

```text
py_compile PASS
targeted pytest PASS: 8 passed
CLI plan PASS: ACQUISITION_PLAN_READY
JSON validation PASS
git diff --check PASS
```

Not executed:

```text
J-Quants five-year fetch
common Runtime OHLCV bootstrap run
20BD / 1Y / 5Y Historical
Training
Calibration
Broker connection
Demo / Production order
```

## User Commands

### 1. Acquisition Plan

```bash
cd /Users/negishi/work/ai-fund-lab-v2
export PYTHONPATH=src:.

python3 scripts/runtime_test.py market-data-acquisition plan \
  --start-date 2021-04-20 \
  --end-date 2026-07-14 \
  --write-evidence \
  --json
```

### 2. Acquisition Run

```bash
cd /Users/negishi/work/ai-fund-lab-v2
export PYTHONPATH=src:.

python3 scripts/runtime_test.py market-data-acquisition run \
  --start-date 2021-04-20 \
  --end-date 2026-07-14 \
  --confirm \
  --yes-i-understand-this-fetches-large-market-data \
  --write-evidence \
  --json
```

### 3. Resume

```bash
cd /Users/negishi/work/ai-fund-lab-v2
export PYTHONPATH=src:.

python3 scripts/runtime_test.py market-data-acquisition resume \
  --run-id jquants-acquisition-20210420-20260714 \
  --confirm \
  --yes-i-understand-this-fetches-large-market-data \
  --write-evidence \
  --json
```

### 4. Progress

```bash
cd /Users/negishi/work/ai-fund-lab-v2
export PYTHONPATH=src:.

python3 scripts/runtime_test.py market-data-acquisition status \
  --run-id jquants-acquisition-20210420-20260714 \
  --json
```

Review:

```text
completed_chunks
remaining_chunks
request_count
page_count
row_count
earliest_date
latest_date
last_error
retry_count
```

### 5. Acquisition Result Verification

```bash
cd /Users/negishi/work/ai-fund-lab-v2
export PYTHONPATH=src:.

python3 scripts/runtime_test.py market-data-acquisition status \
  --run-id jquants-acquisition-20210420-20260714 \
  --json
```

Expected after successful run:

```text
final_judgment = ACQUISITION_SOURCE_READY
normalized_output_path = .runtime/market_data_acquisition/runs/jquants-acquisition-20210420-20260714/raw_normalized/jquants/equities_bars_daily/data.parquet
```

### 6. Phase20-BB Bootstrap Plan

```bash
cd /Users/negishi/work/ai-fund-lab-v2
export PYTHONPATH=src:.

python3 scripts/runtime_test.py market-data-bootstrap plan \
  --years 5 \
  --source-path .runtime/market_data_acquisition/runs/jquants-acquisition-20210420-20260714/raw_normalized/jquants/equities_bars_daily/data.parquet \
  --write-evidence \
  --json
```

### 7. Phase20-BB Bootstrap Run

```bash
cd /Users/negishi/work/ai-fund-lab-v2
export PYTHONPATH=src:.

python3 scripts/runtime_test.py market-data-bootstrap run \
  --years 5 \
  --source-path .runtime/market_data_acquisition/runs/jquants-acquisition-20210420-20260714/raw_normalized/jquants/equities_bars_daily/data.parquet \
  --confirm \
  --yes-i-understand-this-mutates-market-data \
  --write-evidence \
  --json
```

### 8. system-status Warmup Check

```bash
cd /Users/negishi/work/ai-fund-lab-v2
export PYTHONPATH=src:.

python3 scripts/runtime_test.py system-status \
  --scope data \
  --target-start-date 2026-03-24 \
  --target-end-date 2026-03-24 \
  --json
```

### 9. Rollback

Acquisition staging rollback:

```bash
cd /Users/negishi/work/ai-fund-lab-v2
mv .runtime/market_data_acquisition/runs/jquants-acquisition-20210420-20260714 \
   .runtime/market_data_acquisition/runs/jquants-acquisition-20210420-20260714.disabled
```

Bootstrap rollback:

```text
Use the backup_path emitted by market-data-bootstrap run and restore only after operator review.
```

Bootstrap and acquisition rollback are separate because acquisition staging does not mutate common Runtime OHLCV.
