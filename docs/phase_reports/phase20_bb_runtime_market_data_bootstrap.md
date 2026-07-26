# Phase20-BB Runtime Market Data Bootstrap

## Final Status

```text
PHASE20_BB_RUNTIME_MARKET_DATA_BOOTSTRAP_BLOCKED
```

Reason:

```text
Existing candidate source artifact is not a five-year Runtime OHLCV source.
```

No Runtime market data was mutated. No Historical Smoke, Broker connection, Training, Calibration, or model change was executed.

## Scope

Phase20-BB implemented a common Runtime OHLCV bootstrap contract and CLI for `.runtime/operations/jquants/`, plus a system-status warmup guard. This is a Runtime market data Source-of-Truth bootstrap path, not a backtest-only path and not a training dataset shortcut.

## Current Runtime Authority

Current common Runtime OHLCV authority:

```text
.runtime/operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet
```

Observed inventory:

| Item | Value |
| --- | ---: |
| earliest_date | 2026-02-16 |
| latest_date | 2026-07-14 |
| row_count | 426,689 |
| unique_business_days | 101 |
| duplicate Date/Code keys | 0 |
| source | J-Quants normalized |
| price source | adjusted |

Raw J-Quants daily quotes are under:

```text
.runtime/operations/jquants/raw/jquants/equities_bars_daily/data.parquet
```

Listed issues are under:

```text
.runtime/operations/jquants/raw/jquants/listed_issues/data.parquet
```

Daily refresh currently uses `src/ai_fund_lab_v2/paper_trading/market_data_refresh.py`; it merges incoming records into existing records by date/code/business key/endpoint and normalizes daily quotes with adjusted prices when available.

## Existing Five-Year Source Investigation

Candidate source inspected:

```text
.runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/data.parquet
```

Observed inventory:

| Item | Value |
| --- | ---: |
| exists | true |
| earliest_date | 2026-06-01 |
| latest_date | 2026-06-26 |
| row_count | 84,307 |
| unique_business_days | 20 |
| schema_match_runtime | true |
| duplicate Date/Code keys | 0 |
| J-Quants lineage | PASS |

Judgment:

```text
COVERAGE_INSUFFICIENT
```

The artifact schema is merge-compatible, but it is not the expected 2021-2026 five-year source. It must not be treated as five-year bootstrap authority.

## Warmup Requirement

Runtime Candidate Feature generation uses `src/ai_fund_lab_v2/paper_trading/feature_refresh.py`.

Key implementation evidence:

```text
_build_formal_candidate_rows:
  insufficient_history = len(visible) < 61

_formal_feature_values:
  price_momentum_return_60d uses close_values[-61]
  trend_ma_20_60_ratio uses a 60-day moving average
```

Therefore the bootstrap guard uses:

```text
maximum_required_warmup_business_days = 61
```

For 2026-03-24, current Runtime OHLCV starts at 2026-02-16, so the warmup guard returns:

```text
HISTORICAL_SOURCE_WARMUP_INSUFFICIENT
```

## Bootstrap Contract

Implemented in:

```text
src/ai_fund_lab_v2/runtime_v2/market_data_bootstrap.py
```

CLI:

```bash
PYTHONPATH=src:. python3 scripts/runtime_test.py market-data-bootstrap plan \
  --years 5 \
  --write-evidence \
  --json
```

Run command requires explicit market data mutation confirmation:

```bash
PYTHONPATH=src:. python3 scripts/runtime_test.py market-data-bootstrap run \
  --years 5 \
  --source-path <VERIFIED_JQUANTS_NORMALIZED_5Y_PARQUET> \
  --confirm \
  --yes-i-understand-this-mutates-market-data \
  --write-evidence \
  --json
```

The implementation is fail-closed on missing source, schema incompatibility, non-J-Quants lineage, training/future columns, duplicate keys, insufficient coverage, warmup insufficiency, latest-date loss, and merged duplicate/schema failure.

Atomicity:

```text
source/current read
-> merge by Date/Code
-> existing Runtime row wins duplicate Date/Code
-> write temporary parquet
-> validate merged artifact
-> os.replace target only after validation
```

## fresh-run and Historical as-of

`fresh-run` does not delete shared `.runtime/operations/jquants` market data. Historical isolated roots symlink the shared `operations/jquants` authority. Historical consumers remain responsible for as-of cutoff, so a bootstrapped physical source may contain future rows while decision-time views must only expose rows at or before the target business date.

## system-status Warmup Guard

Added:

```bash
PYTHONPATH=src:. python3 scripts/runtime_test.py system-status \
  --scope data \
  --target-start-date 2026-03-24 \
  --target-end-date 2026-03-24 \
  --json
```

The JSON now includes:

```text
runtime_market_data_warmup_sufficiency
```

Fields include target start/end, required warmup days, required source start date, actual source range, missing warmup business days, judgment, reason, and affected components.

## Evidence

Evidence root:

```text
reports/phase20_bb_runtime_market_data_bootstrap/
```

Generated files:

```text
current_runtime_ohlcv_inventory.json
existing_five_year_source_inventory.json
schema_comparison.json
bootstrap_plan.json
bootstrap_contract.json
fresh_run_market_data_preservation_audit.json
historical_asof_contract_audit.json
warmup_requirement_inventory.json
system_status_warmup_guard_test.json
test_summary.json
```

Phase report JSON:

```text
reports/phase_reports/phase20_bb_runtime_market_data_bootstrap.json
```

## Validation

Executed:

```text
py_compile PASS
targeted pytest PASS: 4 passed
market-data-bootstrap plan EXPECTED_BLOCK
```

Not executed:

```text
5-year J-Quants fetch
real bootstrap commit into common Runtime OHLCV
20BD Historical Run
long Historical Smoke
Broker connection
Training
Calibration
model changes
Runtime trading-state mutation
```

## Operator Next Step

Provide or generate a verified J-Quants-derived normalized OHLCV artifact covering at least:

```text
required_source_start_date = 2021-04-20
target_end_date = 2026-07-14
```

Then run the bootstrap `plan` command first. Only if the plan returns `BOOTSTRAP_PLAN_READY`, run the explicit `run` command.
