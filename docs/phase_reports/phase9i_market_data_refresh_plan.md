# Phase9-I Market Data Refresh Plan

## 1. Purpose

Phase9-H judged:

```text
DATA_UPDATE_REQUIRED
```

Phase9-I defines a safe refresh procedure for J-Quants-derived market data before starting the 30 business day Phase9 daily operation tracker.

Phase9-I covers:

```text
J-Quants daily_quotes refresh
listed_info refresh
trading_calendar refresh
raw storage
daily_quotes normalized regeneration
refresh manifest
market data readiness audit
```

Phase9-I does not cover:

```text
feature artifact generation
AI retraining
inference
OrderPlan generation
Paper Ledger virtual fill
Broker order
OpenD startup
unlock_trade
full backtest
```

## 2. Current Gap

Phase9-H local freshness:

```text
raw daily_quotes response latest: 2026-06-12
raw daily_quotes table latest: 2026-06-01
normalized daily_quotes latest: 2026-06-01
listed_info latest: 2026-06-01
trading_calendar latest: 2026-06-07
data_until candidate: 2026-06-01
```

Phase9 daily operation target:

```text
decision_for = 2026-06-16
target data_until >= 2026-06-16
```

Therefore the initial refresh range is:

```text
from_date = 2026-06-02
to_date = 2026-06-16
```

## 3. Storage Paths

Raw storage:

```text
.runtime/data/raw/jquants/equities_bars_daily/data.parquet
.runtime/data/raw/jquants/listed_issues/data.parquet
.runtime/data/raw/jquants/trading_calendar/data.parquet
```

Normalized storage:

```text
.runtime/data/raw_normalized/jquants/equities_bars_daily/data.parquet
```

Phase9 refresh manifest:

```text
.runtime/phase9/market_data_refresh/YYYY-MM-DD/refresh_manifest.json
```

Reports:

```text
docs/phase_reports/phase9i_market_data_refresh_report.md
reports/phase_reports/phase9i_market_data_refresh_report.json
```

## 4. Execution Modes

Default mode is dry-run:

```bash
python3 scripts/run_phase9i_market_data_refresh.py \
  --from-date 2026-06-02 \
  --to-date 2026-06-16
```

Dry-run behavior:

```text
show target date range
show existing latest dates
show required dates
show output paths
write Phase9 refresh report / manifest
do not call J-Quants API
do not overwrite raw data
do not overwrite normalized data
do not run feature generation
do not run inference
```

API fetch mode requires both:

```text
--no-dry-run
--allow-api-fetch
```

Example:

```bash
python3 scripts/run_phase9i_market_data_refresh.py \
  --from-date 2026-06-02 \
  --to-date 2026-06-16 \
  --no-dry-run \
  --allow-api-fetch
```

Without `--allow-api-fetch`, the runner fails closed and records `allow_api_fetch_required`.

## 5. Refresh Procedure

Execution pre-check:

```text
from_date is required
to_date is required
from_date <= to_date
to_date is not in the future
dry-run first
backup_existing default true
API credentials must not be printed or written to manifest
```

API refresh steps:

```text
1. Fetch J-Quants daily_quotes for from_date..to_date
2. Fetch listed_info for to_date
3. Fetch trading_calendar for from_date..to_date
4. Upsert raw records into local raw parquet
5. Backup existing files before overwrite when backup_existing=true
6. Regenerate daily_quotes normalized parquet using Phase1 normalizer
7. Write Phase9 refresh manifest
8. Run market_data_readiness check for to_date
9. Write Markdown / JSON reports
```

Failure handling:

```text
API failure -> fail closed
partial success -> manifest status PARTIAL
readiness NOT_READY -> halt next Phase9 operation step
secret-like fields -> removed from manifest/report
```

## 6. Backup Policy

When `backup_existing=true`, existing raw and normalized parquet files are copied beside the original file before overwrite:

```text
data.parquet.backup_YYYYMMDDTHHMMSSZ
```

Backups are local safety artifacts only. They are not promoted as active inputs.

## 7. Post-check

After refresh:

```text
normalized daily_quotes max Date >= 2026-06-16
listed_info max Date >= 2026-06-16
market_data_readiness status = READY
no future rows
no duplicate date-code in normalized daily_quotes
no secret in manifest/report
```

If post-check fails, Phase9 daily operation remains halted.

## 8. Handoff To Phase9-J

Phase9-I only refreshes market data.

Phase9-J or later should consume the refreshed `data_until` and regenerate:

```text
Candidate AI features
Opportunity AI features/artifacts
Position Management features/artifacts
Capital Allocation inputs/artifacts
model eligibility manifests
```

Only after feature and model eligibility are ready should Phase9 daily operation proceed.
