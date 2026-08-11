# Phase29-L Multi-Year Historical Validation Preflight and Handoff

Task ID: `Phase29-L`

Status:

```text
COMPLETE
READ_ONLY PREFLIGHT / HANDOFF
DATA ACQUISITION REQUIRED
FRESH LONG-HORIZON RUN NOT READY
NO PRODUCTION CODE CHANGE
NO RUNTIME MUTATION
NO HISTORICAL EXECUTION
```

Primary Judgment:

```text
PHASE29_L_MULTI_YEAR_HISTORICAL_VALIDATION_PREFLIGHT_DATA_ACQUISITION_REQUIRED
```

## 1. Scope

Phase29-L performs the preflight for a multi-year Historical validation from
the requested window `2022-08-10` through `2026-08-09`, with initial cash
`1,000,000` JPY.

Codex did not run the long-horizon Historical. Codex did not perform long
J-Quants acquisition, mutate `.runtime`, change Production code/config/schema,
or tune strategy thresholds.

## 2. Requested and Resolved Period

Requested:

```text
start_date: 2022-08-10
end_date:   2026-08-09
cash:       1,000,000 JPY
```

Resolved by the combined J-Quants/repo trading calendar:

```text
first_business_date: 2022-08-10
last_business_date:  2026-08-07
business_days:       979
```

`2026-08-09` is not a business day, so the last business day on or before the
requested end is `2026-08-07`.

Calendar authority:

```text
.runtime/operations/jquants/historical_snapshots/trading_calendar/data.parquet
.runtime/data/raw/jquants/trading_calendar/data.parquet
```

The combined calendar spans `2021-07-16` through `2026-12-31` and has no missing
calendar dates in the requested window.

## 3. Runtime Dry-Run Observation

The read-only fresh-run dry-run command completed without mutation:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-smoke \
  --date-from 2022-08-10 \
  --date-to 2026-08-09 \
  --initial-cash 1000000 \
  --dry-run \
  --json
```

Dry-run result:

```text
status: DRY_RUN
dry_run_no_mutation: true
request_conformance_status: NOT_PASS
resolved_date_from: 2022-08-10
resolved_date_to: 2026-08-03
resolved_business_day_count: 973
```

This does not override the true calendar resolution. It shows that the current
runtime/source authority cannot yet resolve the full requested period through
the true last trading day `2026-08-07`.

## 4. Runtime Profile Decision

Selected profile:

```text
historical-smoke
config/runtime_tests/historical_smoke_5bd.json
```

Reason:

```text
Phase29-K validated the current 100BD performance stack on historical-smoke.
The long-horizon validation should keep the same Production-common smoke
execution contract and apply explicit date/cash overrides.
```

Rejected alternative:

```text
historical-extended-smoke
config/runtime_tests/historical_extended_smoke_10bd.json
official_status: pre_continuity_smoke_profile
```

Caveat:

```text
Both inspected profiles use smoke_limited_execution_model and are not marked as
official_long_term_performance_model. This is a runtime-profile limitation, not
a Phase29-L implementation change.
```

## 5. Lookback Requirement

Production runtime market-data bootstrap authority requires:

```text
required_lookback_business_days: 61
first_target_business_date:      2022-08-10
earliest_required_source_date:   2022-05-17
```

Authority:

```text
src/ai_fund_lab_v2/runtime_v2/market_data_bootstrap.py
REQUIRED_LOOKBACK_BUSINESS_DAYS = 61
build_market_data_warmup_sufficiency(...)
```

The source used to prepare the long-horizon runtime must therefore cover at
least `2022-05-17` through `2026-08-07`.

## 6. Source Coverage

Price coverage is not ready.

Current useful sources include:

```text
.runtime/market_data_acquisition/runs/jquants-acquisition-20210802-20260714-bh/raw_normalized/jquants/equities_bars_daily/data.parquet
coverage: 2021-08-02 to 2026-07-14
rows:     5,026,858

.runtime/market_data_acquisition/runs/jquants-acquisition-20260718-20260803/raw_normalized/jquants/equities_bars_daily/data.parquet
coverage: 2026-07-21 to 2026-08-03
rows:     42,037
```

Missing terminal business dates:

```text
2026-08-04
2026-08-05
2026-08-06
2026-08-07
```

There is currently no single supported bootstrap source covering the required
warmup-plus-target period `2022-05-17` through `2026-08-07`.

Listed Issues coverage is partial.

```text
.runtime/operations/jquants/historical_snapshots/listed_issues/snapshots/*
snapshot_count: 1,221
coverage:       2021-07-16 to 2026-07-15
requested-window snapshots: 961
```

The requested runtime target still lacks Listed Issues authority through
`2026-08-07`.

Corporate Event coverage is partial.

```text
.runtime/strategy_artifacts/corporate_event/*
available_dates: 2026-07-06, 2026-07-14, 2026-07-15

.runtime/data/raw/jquants/fins_summary/data.parquet
coverage: 2026-06-01 to 2026-08-03

.runtime/data/raw/jquants/earnings_calendar/data.parquet
coverage: 2026-07-29 to 2026-08-03
```

Optional operations corporate sources expected by historical source foundation
were not present under `.runtime/operations/jquants/raw/jquants/` for
`corporate_actions`, `earnings_schedule`, and `financial_statements`.

## 7. Data Acquisition Plan

Data acquisition is required before any long-horizon fresh-run.

Plan audit for the required warmup-plus-target source:

```text
start_date:              2022-05-17
end_date:                2026-08-07
chunk:                   month
status:                  PASS
final_judgment:          ACQUISITION_PLAN_READY
estimated_date_chunks:   52
estimated_request_units: 1104
run_id:                  jquants-acquisition-20220517-20260807
```

Operator acquisition command:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py market-data-acquisition run \
  --profile historical-smoke \
  --start-date 2022-05-17 \
  --end-date 2026-08-07 \
  --chunk month \
  --confirm \
  --yes-i-understand-this-fetches-large-market-data \
  --write-evidence \
  --json
```

If interrupted:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py market-data-acquisition resume \
  --profile historical-smoke \
  --run-id jquants-acquisition-20220517-20260807 \
  --confirm \
  --yes-i-understand-this-fetches-large-market-data \
  --write-evidence \
  --json
```

Bootstrap command after acquisition PASS:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py market-data-bootstrap run \
  --profile historical-smoke \
  --source-path .runtime/market_data_acquisition/runs/jquants-acquisition-20220517-20260807/raw_normalized/jquants/equities_bars_daily/data.parquet \
  --target-start-date 2022-08-10 \
  --target-end-date 2026-08-07 \
  --confirm \
  --yes-i-understand-this-mutates-market-data \
  --write-evidence \
  --json
```

Phase29-L intentionally does not release a fresh-run command as ready. A
Phase29-L2 readiness recheck should confirm coverage after acquisition and
bootstrap before the long-horizon Historical is started.

## 8. Resume and Evaluation Contracts

Resume contract is confirmed at the CLI level:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py resume \
  --profile historical-smoke \
  --run-id <ACTUAL_RUN_ID> \
  --confirm \
  --yes-i-understand-this-mutates-trading-state \
  --json
```

Long-horizon evaluation contract is `NOT_READY` because no accepted
long-horizon run exists yet. After readiness passes and the run completes, the
evaluation must include:

```text
total_return_pct
final_equity_jpy
max_drawdown_pct
average_actual_exposure_pct
average_cash_jpy
unused_deployable_capital_days
BUY_NEW fill_count/notional
BUY_ADD fill_count/notional
SELL/REDUCE/EXIT independence
negative_cash_count
exposure_over_100_pct_count
compound-capital integrity
winner-dependency monitoring
```

## 9. Gate Result

```text
Fresh-run Ready:                  NO
Data Acquisition Required:        YES
Long-horizon Evaluation Contract: NOT_READY
Resume Contract Confirmed:        YES
Production Code Changed:          NO
Runtime Mutated:                  NO
Historical Executed:              NO
```

Recommended next action:

```text
Operator performs market-data acquisition and bootstrap, then Phase29-L2
readiness recheck. Only after Phase29-L2 passes should the long-horizon
Historical fresh-run command be released.
```

## 10. Deliverables

```text
docs/phase_reports/phase29_l_multi_year_historical_validation_preflight_and_handoff.md
reports/phase29_l_multi_year_historical_validation_preflight_and_handoff/
```
