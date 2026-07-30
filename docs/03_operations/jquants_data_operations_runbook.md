# J-Quants Data Operations Runbook

## 1. Purpose

This runbook defines permanent operator procedures for J-Quants data acquisition, raw storage validation, and Corporate Event source materialization.

Phase reports are evidence. This runbook is the reusable operator procedure.

## 2. Applicable Environments

The fetch and validation CLIs are Production-common data operations. They do not submit orders, write Broker state, change Runtime trading state, or perform a Runtime Switch.

Historical Runtime must use pre-materialized data. Do not fetch J-Quants data from inside a Historical run.

## 3. Preconditions

Before running a network fetch, confirm:

- You are at the repository root.
- The branch and commit are the intended operator version.
- The worktree state is understood.
- Python is available as `python3`.
- The target Runtime root is correct, normally `.runtime`.
- `.env` or environment variables provide J-Quants authentication.
- The J-Quants plan includes the endpoint being fetched.
- Disk space is sufficient for parquet output.
- The target date range is known.
- `trading_calendar` raw data exists before using a range fetch plan for `fins_summary` or `all`.
- No active Runtime Test should be resumed, abandoned, deleted, or closed by this procedure.
- The operation is limited to J-Quants data files and manifests.

Read-only preflight:

```bash
pwd
git status --short
python3 --version
python3 scripts/fetch_jquants_daily.py --help
```

## 4. Authentication

`load_settings()` reads `.env` when present and otherwise uses process environment variables.

Required for live J-Quants fetch:

```text
JQUANTS_API_KEY
```

Optional settings:

```text
JQUANTS_BASE_URL=https://api.jquants.com
JQUANTS_RATE_LIMIT_PER_MINUTE=60
JQUANTS_TIMEOUT_SECONDS=30
AI_FUND_LAB_RAW_STORAGE_FORMAT=parquet
AI_FUND_LAB_RUNTIME_DIR=.runtime
```

Never put API keys or tokens into this runbook, shell history examples, reports, logs, or Evidence. Do not print `.env`.

## 5. Source Inventory

Implemented sources:

| Endpoint Name | API Path | Raw Collection | Normal Use |
| --- | --- | --- | --- |
| `daily_quotes` | `/v2/equities/bars/daily` | `jquants/equities_bars_daily` | OHLCV and adjusted prices |
| `listed_issues` | `/v2/equities/master` | `jquants/listed_issues` | Listed company universe |
| `earnings_calendar` | `/v2/equities/earnings-calendar` | `jquants/earnings_calendar` | Earnings announcement schedule |
| `trading_calendar` | `/v2/markets/calendar` | `jquants/trading_calendar` | Business day calendar |
| `fins_summary` | `/v2/fins/summary` | `jquants/fins_summary` | Financial disclosure fact |

Optional or not implemented for this repo:

| Source | Status |
| --- | --- |
| TDnet | Optional; no deterministic consumer classification implemented |
| corporate_actions | Optional; no dedicated repo fetcher/consumer implemented |
| fins_details | Optional detail source; not implemented |

## 6. Normal Fetch Procedure

Set variables first:

```bash
export RUNTIME_DIR=.runtime
export FROM_DATE=YYYY-MM-DD
export TO_DATE=YYYY-MM-DD
export OPERATOR_BUSINESS_DATE=YYYY-MM-DD
```

Dry-run, no network and no write:

```bash
AI_FUND_LAB_RAW_STORAGE_FORMAT=parquet python3 scripts/fetch_jquants_daily.py \
  --endpoint all \
  --from-date "$FROM_DATE" \
  --to-date "$TO_DATE" \
  --runtime-dir "$RUNTIME_DIR" \
  --dry-run
```

Fetch only the intended source when possible. Do not use `all` for Corporate Event repair unless the operator intentionally wants every implemented source.

## Corporate Event Source Materialization

Corporate Event currently requires:

```text
listed_issues
earnings_calendar
fins_summary
```

Existing operational sources should already provide:

```text
equities_bars_daily
listed_issues
trading_calendar
```

For the Phase23 10BD candidate window, do not decide the range from `2026-07-06` alone. Use the Runtime Test plan's requested evaluation range. For a 10BD run starting `2026-07-06`, `FROM_DATE` is the first test business date and `TO_DATE` is the last test business date. Keep older raw history if it already exists; never truncate it.

### Trading Calendar Fetch

`trading_calendar` is the planning authority for range fetches such as `fins_summary`. Fetch or materialize calendar coverage before any range fetch that depends on business-day expansion.

Dry-run:

```bash
AI_FUND_LAB_RAW_STORAGE_FORMAT=parquet python3 scripts/fetch_jquants_daily.py \
  --endpoint trading_calendar \
  --from-date "$FROM_DATE" \
  --to-date "$TO_DATE" \
  --runtime-dir "$RUNTIME_DIR" \
  --dry-run
```

Live fetch:

```bash
AI_FUND_LAB_RAW_STORAGE_FORMAT=parquet python3 scripts/fetch_jquants_daily.py \
  --endpoint trading_calendar \
  --from-date "$FROM_DATE" \
  --to-date "$TO_DATE" \
  --runtime-dir "$RUNTIME_DIR"
```

Coverage validation:

```bash
python3 scripts/check_jquants_raw_quality.py \
  --endpoint trading_calendar \
  --from-date "$FROM_DATE" \
  --to-date "$TO_DATE" \
  --runtime-dir "$RUNTIME_DIR" \
  --output both

python3 scripts/show_jquants_manifest.py \
  --endpoint trading_calendar \
  --runtime-dir "$RUNTIME_DIR" \
  --latest
```

### Earnings Calendar Fetch

`earnings_calendar` is a snapshot-style endpoint in this repo. The CLI accepts `--date` for manifest/operator traceability, but the endpoint capability does not send a date or code parameter to J-Quants.

Dry-run:

```bash
AI_FUND_LAB_RAW_STORAGE_FORMAT=parquet python3 scripts/fetch_jquants_daily.py \
  --endpoint earnings_calendar \
  --date "$OPERATOR_BUSINESS_DATE" \
  --runtime-dir "$RUNTIME_DIR" \
  --dry-run
```

Live fetch:

```bash
AI_FUND_LAB_RAW_STORAGE_FORMAT=parquet python3 scripts/fetch_jquants_daily.py \
  --endpoint earnings_calendar \
  --date "$OPERATOR_BUSINESS_DATE" \
  --runtime-dir "$RUNTIME_DIR"
```

### Fins Summary Fetch

`fins_summary` is fetched per business day according to the repo fetch plan. The range plan depends on the local `trading_calendar` raw source. If the range dry-run fails with `CalendarDataNotFoundError`, fetch or materialize `trading_calendar` first; do not replace the range with a guessed calendar.

If the range is outside local `trading_calendar` coverage, the fetch plan is empty. Empty plan is a failed operator precondition, not a successful materialization. The CLI exits with code `2`, writes an `ERROR fetch plan is empty` message to stderr, and performs no API request, storage write, or manifest append.

Raw identity is one J-Quants disclosure, not one company per disclosure date. The Production-common business key is:

```text
DiscDate + Code + DiscNo
```

If `DiscNo` is absent, the fallback identity uses available disclosure attributes:

```text
DiscDate + Code + DiscTime + DocType + CurPerType + CurPerSt + CurPerEn + CurFYSt + CurFYEn
```

Do not collapse `fins_summary` to latest-only, `DiscDate + Code`, or `Code` only. Multiple disclosures by the same company on the same date, including forecast revisions, dividend revisions, corrections, and financial statements, must be retained for PIT Corporate Event authority.

Dry-run:

```bash
AI_FUND_LAB_RAW_STORAGE_FORMAT=parquet python3 scripts/fetch_jquants_daily.py \
  --endpoint fins_summary \
  --from-date "$FROM_DATE" \
  --to-date "$TO_DATE" \
  --runtime-dir "$RUNTIME_DIR" \
  --dry-run
```

Live fetch:

```bash
AI_FUND_LAB_RAW_STORAGE_FORMAT=parquet python3 scripts/fetch_jquants_daily.py \
  --endpoint fins_summary \
  --from-date "$FROM_DATE" \
  --to-date "$TO_DATE" \
  --runtime-dir "$RUNTIME_DIR"
```

Normal live success must print at least one line like:

```text
fins_summary: saved <N> records to <path>
```

and must append one `/v2/fins/summary` manifest entry per planned business day. Exit code `0` with no operator output and no new manifest entry is not a successful fetch.

Duplicate warning interpretation:

```text
duplicate_key_count > 0
```

means incoming source rows shared the active raw business key. Inspect:

```text
exact_source_duplicate_count
business_key_collision_count
```

`exact_source_duplicate_count > 0` means repeated identical source rows were collapsed. `business_key_collision_count > 0` means distinct source rows shared a key and must be investigated before promotion. Do not silence the warning without preserving Evidence.

## 8. Raw Storage

Fetch output is stored under:

```text
.runtime/data/raw/jquants/earnings_calendar/data.parquet
.runtime/data/raw/jquants/fins_summary/data.parquet
```

Raw manifest:

```text
.runtime/data/raw/jquants/manifest.jsonl
```

Manifest entries contain sanitized request parameters, storage path, record count, schema version, validation status, and diff summary. They must not contain API keys, tokens, `Authorization`, or `x-api-key` values.

## 9. Canonical / As-Of Materialization

Corporate Event producer reads operational parquet paths:

```text
.runtime/operations/jquants/raw/jquants/earnings_calendar/data.parquet
.runtime/operations/jquants/raw/jquants/fins_summary/data.parquet
```

There is no separate Corporate Event canonical transform CLI in this repo. For these two sources, materialization means promoting the validated parquet raw files into the operations raw path without deleting prior source history.

Dry-run path check:

```bash
python3 - <<'PY'
from pathlib import Path
for path in [
    Path(".runtime/data/raw/jquants/earnings_calendar/data.parquet"),
    Path(".runtime/data/raw/jquants/fins_summary/data.parquet"),
]:
    print(path, "exists=", path.is_file())
PY
```

Promote after validation:

```bash
mkdir -p \
  .runtime/operations/jquants/raw/jquants/earnings_calendar \
  .runtime/operations/jquants/raw/jquants/fins_summary

install -m 0644 \
  .runtime/data/raw/jquants/earnings_calendar/data.parquet \
  .runtime/operations/jquants/raw/jquants/earnings_calendar/data.parquet

install -m 0644 \
  .runtime/data/raw/jquants/fins_summary/data.parquet \
  .runtime/operations/jquants/raw/jquants/fins_summary/data.parquet
```

This writes data files only. It must not mutate Current, Ledger, Pending, Runtime State, Registry, Accepted Generation, Broker, or active Runtime Test state.

## 10. Validation

CLI contract:

```bash
python3 scripts/fetch_jquants_daily.py --help
python3 scripts/show_jquants_manifest.py --help
python3 scripts/check_jquants_raw_quality.py --help
python3 scripts/inspect_raw_validation.py --help
python3 scripts/build_jquants_refetch_plan.py --help
```

Raw schema validation:

```bash
python3 scripts/inspect_raw_validation.py \
  --endpoint earnings_calendar \
  --runtime-dir "$RUNTIME_DIR" \
  --storage-format parquet \
  --output table

python3 scripts/inspect_raw_validation.py \
  --endpoint fins_summary \
  --runtime-dir "$RUNTIME_DIR" \
  --storage-format parquet \
  --output table
```

Successful fetch confirmation for `fins_summary`:

```bash
python3 scripts/show_jquants_manifest.py \
  --endpoint fins_summary \
  --runtime-dir "$RUNTIME_DIR" \
  --latest
```

If the latest manifest does not include `/v2/fins/summary` for the requested business dates, treat the materialization as incomplete.

Raw quality:

```bash
python3 scripts/check_jquants_raw_quality.py \
  --endpoint earnings_calendar \
  --from-date "$FROM_DATE" \
  --to-date "$TO_DATE" \
  --runtime-dir "$RUNTIME_DIR" \
  --output both

python3 scripts/check_jquants_raw_quality.py \
  --endpoint fins_summary \
  --from-date "$FROM_DATE" \
  --to-date "$TO_DATE" \
  --runtime-dir "$RUNTIME_DIR" \
  --output both
```

Manifest validation:

```bash
python3 scripts/show_jquants_manifest.py \
  --endpoint earnings_calendar \
  --runtime-dir "$RUNTIME_DIR" \
  --latest

python3 scripts/show_jquants_manifest.py \
  --endpoint fins_summary \
  --runtime-dir "$RUNTIME_DIR" \
  --latest
```

Row count and date inspection:

```bash
python3 - <<'PY'
from pathlib import Path
import pandas as pd
for name in ["earnings_calendar", "fins_summary"]:
    path = Path(".runtime/operations/jquants/raw/jquants") / name / "data.parquet"
    print("source=", name, "path=", path, "exists=", path.is_file())
    if not path.is_file():
        continue
    frame = pd.read_parquet(path)
    print("row_count=", len(frame))
    for column in ["PublicationDate", "ScheduledDate", "Date", "DiscDate", "DisclosedDate", "Code", "LocalCode"]:
        if column in frame.columns:
            values = frame[column].dropna().astype(str)
            print(column, "min=", values.min() if len(values) else "", "max=", values.max() if len(values) else "")
PY
```

Hash inspection:

```bash
python3 - <<'PY'
from pathlib import Path
from hashlib import sha256
for path in [
    Path(".runtime/operations/jquants/raw/jquants/earnings_calendar/data.parquet"),
    Path(".runtime/operations/jquants/raw/jquants/fins_summary/data.parquet"),
]:
    if not path.is_file():
        print(path, "MISSING")
        continue
    h = sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    print(path, h.hexdigest())
PY
```

## 11. Rerun And Idempotency

Raw ingestion uses `(target_date, business_key, endpoint)` keys in storage. Re-running the same source/date updates matching keys instead of blindly duplicating the same key.

For `earnings_calendar`, schedule revisions must be retained. The source can contain multiple records over time for the same issue and fiscal period. Do not delete old rows to force a single current schedule.

For `fins_summary`, re-run failed or missing business days. Do not delete a non-empty parquet file unless a validation report proves it is corrupt and the operator has made a backup.

The manifest is append-only for fetch/migration events. A repeated fetch should create another manifest entry.

After a `fins_summary` business-key repair, do not trust previously collapsed raw parquet for the affected range. Use a backup and re-materialize only the affected source/date range:

```bash
mkdir -p "$RUNTIME_DIR/data/raw/jquants/backups"
cp "$RUNTIME_DIR/data/raw/jquants/fins_summary/data.parquet" \
  "$RUNTIME_DIR/data/raw/jquants/backups/fins_summary_data_before_business_key_repair.parquet"

AI_FUND_LAB_RAW_STORAGE_FORMAT=parquet python3 scripts/fetch_jquants_daily.py \
  --endpoint fins_summary \
  --from-date "$FROM_DATE" \
  --to-date "$TO_DATE" \
  --runtime-dir "$RUNTIME_DIR"
```

Keep existing manifest history. After re-fetch, validate raw quality and latest manifest entries, then promote the validated parquet to operations paths. Do not delete prior manifest entries.

If a repaired re-fetch was performed after legacy code-only rows already existed in the same parquet, clean only the affected legacy rows with the reusable repair CLI.

Dry-run:

```bash
python3 scripts/repair_jquants_raw_business_keys.py \
  --endpoint fins_summary \
  --from-date "$FROM_DATE" \
  --to-date "$TO_DATE" \
  --runtime-dir "$RUNTIME_DIR" \
  --dry-run
```

The dry-run must show:

```text
target_range_legacy_rows
target_range_repaired_rows
target_range_unknown_rows
legacy_rows_removed
post_summary.total_rows
pre_hash
```

Live cleanup:

```bash
python3 scripts/repair_jquants_raw_business_keys.py \
  --endpoint fins_summary \
  --from-date "$FROM_DATE" \
  --to-date "$TO_DATE" \
  --runtime-dir "$RUNTIME_DIR" \
  --confirm
```

The cleanup removes only rows matching all of:

```text
endpoint == /v2/fins/summary
DiscDate or target_date within FROM_DATE..TO_DATE
business_key == Code
```

It keeps repaired disclosure-identity rows, out-of-range rows, unknown key formats, manifest history, and all other endpoints. The CLI creates a backup under:

```text
$RUNTIME_DIR/backups/phase23_x_fins_summary_legacy_key_cleanup/<timestamp>/
```

Backup contents:

```text
data.parquet
manifest.jsonl
pre_cleanup_summary.json
pre_cleanup_hashes.json
repair_result.json
```

Manifest handling:

```text
manifest is append-only and is not deleted or rewritten by cleanup
cleanup evidence is written to the backup directory
```

Post-cleanup validation:

```bash
python3 scripts/inspect_raw_validation.py \
  --endpoint fins_summary \
  --runtime-dir "$RUNTIME_DIR" \
  --storage-format parquet \
  --output table

python3 scripts/check_jquants_raw_quality.py \
  --endpoint fins_summary \
  --from-date "$FROM_DATE" \
  --to-date "$TO_DATE" \
  --runtime-dir "$RUNTIME_DIR" \
  --output both
```

Expected clean state:

```text
target_range_legacy_rows = 0
target_range_unknown_rows = 0
duplicate_key_count = 0
business_key_collision_count = 0 for latest repaired fetch manifests
validation_status = OK
```

Rollback:

```bash
cp "$RUNTIME_DIR/backups/phase23_x_fins_summary_legacy_key_cleanup/<timestamp>/data.parquet" \
  "$RUNTIME_DIR/data/raw/jquants/fins_summary/data.parquet"
```

Do not roll back or edit the manifest unless a separate incident procedure explicitly requires it.

Promotion condition:

```text
legacy cleanup PASS
raw quality PASS
disclosure identity PASS
Corporate Event short validation PASS
backup PASS
```

When promoting, back up the existing operations file first, copy the cleaned raw parquet to the operations path, then verify source/destination hashes and row counts. Do not promote before Evidence Review if the Corporate Event validation gate remains `REVIEW_REQUIRED`.

## 12. Error Handling

| Case | Symptom | Check | Rerun | Do Not Delete |
| --- | --- | --- | --- | --- |
| Auth failure | CLI raises missing/failed `JQUANTS_API_KEY` | confirm env key exists without printing value | yes after auth fix | `.env`, existing raw |
| Endpoint unavailable or plan shortage | HTTP 403/400 or zero rows for entitled source | manifest, logs, provider plan | yes after plan fix | old raw history |
| Rate limit | HTTP 429 retry/error | logs and manifest | yes after wait | manifests |
| Network timeout | request failed timeout | logs | yes | existing parquet |
| Schema mismatch | validation `ERROR` | `inspect_raw_validation.py` | yes after code/source review | raw until backed up |
| Zero rows | quality `record_count=0` | quality report and manifest | yes | prior non-empty source |
| Empty fetch plan | stderr contains `ERROR fetch plan is empty`; exit code `2`; no manifest entry | check `trading_calendar` coverage and requested range | after calendar materialization or corrected range | existing raw and manifest |
| Fins Summary duplicate warning | manifest `duplicate_key_count > 0` | compare `exact_source_duplicate_count` and `business_key_collision_count`; inspect `DiscNo` coverage | yes after key/coverage review | existing raw and manifest |
| Partial fetch | some business days missing | refetch plan | yes for missing dates | successful days |
| Manifest inconsistency | latest manifest path/status mismatch | `show_jquants_manifest.py` | maybe | manifest history |
| Future availability rows | Corporate Event rejects future publication | Corporate Event validation | no unless source is wrong | source history |
| Availability column missing | `earnings_calendar_availability_date_missing` | column inspection | Codex review likely needed | raw evidence |
| Raw exists but consumer cannot read | Corporate Event `REVIEW_REQUIRED` or read error | path and parquet inspection | after path/schema fix | source raw |

Call Codex for investigation when schema changed, availability authority is ambiguous, TDnet/corporate_actions are required, or a validation failure cannot be explained by auth/rate/network issues.

## 13. Rate Limit

Default policy is `JQUANTS_RATE_LIMIT_PER_MINUTE=60`. Pagination is supported by the client where the endpoint returns `pagination_key`. The client records secret-safe diagnostics and does not log the API key.

## 14. Security

Do not:

- commit `.env`,
- paste API keys into commands,
- print credentials,
- store tokens in Evidence,
- add Broker credentials to data fetch commands.

## 15. Historical Runtime Usage

Historical Runtime uses the materialized operations files. It must not fetch J-Quants data during a Historical run.

Before 10BD/20BD:

1. Fetch and validate J-Quants sources.
2. Promote validated parquet to `.runtime/operations/jquants/raw/jquants/...`.
3. Run the Corporate Event validation gate below.
4. Use the Runtime Test runbook for the actual Runtime Test command.

## Corporate Event Validation Gate

Before a 10BD run, validate the Corporate Event producer for `2026-07-06` or the first requested Runtime Test business date.

Coverage interpretation:

```text
SOURCE_AVAILABLE
```

means the source file exists and the producer can read it.

```text
PIT_COVERAGE_AVAILABLE
```

means usable rows remain after applying the business-date availability boundary.

```text
PIT_COVERAGE_INCOMPLETE
```

means the source exists, but all or part of its rows are unavailable as of the requested business date. Do not convert this state to `KNOWN_NO_EVENT`.

For `earnings_calendar`, the current repo endpoint is a snapshot-style fetch. The CLI accepts `--date` for operator and manifest traceability, but the repo client does not send that date to J-Quants for this endpoint.

Phase23-Z establishes one explicit exception contract for Historical Runtime validation:

```text
authority_type = CURRENT_SNAPSHOT_CALENDAR_ONLY
exception_scope = earnings_scheduled_date_only
```

Only the earnings scheduled date may use the latest materialized `earnings_calendar` snapshot when validating historical business dates. The consumer may use only the issue code, scheduled date, snapshot target date, and snapshot fetched timestamp for earnings event-window avoidance. It must not consume publication dates, financial metrics, disclosure contents, forecast revisions, market data, candidate/opportunity inputs, portfolio data, or any other current snapshot field under this exception.

Artifacts must disclose the exception:

```text
earnings_calendar_authority_type = CURRENT_SNAPSHOT_CALENDAR_ONLY
earnings_calendar_historical_pit_compliant = false
earnings_calendar_exception_scope = earnings_scheduled_date_only
approved_non_pit_calendar_exception_used = true
future_leakage_used = false
non_calendar_future_leakage_used = false
latest_fallback_used = false
non_calendar_latest_fallback_used = false
```

`future_earnings_calendar_row_rejected` is no longer expected for the approved schedule-only snapshot exception. It remains forbidden to generalize this behavior to `fins_summary`, `listed_issues`, `daily_quotes`, `corporate_actions`, market context, candidates, PM, broker snapshots, or any financial result content.

Corporate actions and TDnet-style direct action sources are optional until a deterministic producer contract is connected. Missing optional corporate-action sources are reported source-scoped, but do not by themselves make the top-level gate `REVIEW_REQUIRED`. Symbols must remain `UNKNOWN_DUE_TO_MISSING_COVERAGE` when required PIT coverage is incomplete.

```bash
PYTHONPATH=src python3 - <<'PY'
from pathlib import Path
import json
from ai_fund_lab_v2.strategy.corporate_event import (
    default_runtime_artifact_path,
    produce_corporate_event_artifact,
    resolve_default_input_paths,
)

business_date = "2026-07-06"
runtime_root = Path(".runtime")
output_path = default_runtime_artifact_path(runtime_root, business_date)
result = produce_corporate_event_artifact(
    business_date=business_date,
    input_paths=resolve_default_input_paths(runtime_root / "operations"),
    output_path=output_path,
    as_of=f"{business_date}T00:00:00+00:00",
    require_full_source_coverage=True,
)
print(json.dumps({
    "status": result.status,
    "reason": result.reason,
    "artifact_path": result.artifact_path,
    "earnings_calendar_coverage": result.payload.get("source_scoped_coverage", {}).get("earnings_calendar_coverage", {}),
    "financial_statement_coverage": result.payload.get("source_scoped_coverage", {}).get("financial_statement_coverage", {}),
    "listing_status_coverage": result.payload.get("source_scoped_coverage", {}).get("listing_status_coverage", {}),
    "known_event_count": len(result.payload.get("known_event_symbols", [])),
    "known_no_event_count": len(result.payload.get("known_no_event_symbols", [])),
    "unknown_count": len(result.payload.get("unknown_symbols", [])),
    "pit_validation": result.payload.get("pit_validation", {}),
    "earnings_calendar_authority": result.payload.get("earnings_calendar_authority", {}),
}, ensure_ascii=False, indent=2, sort_keys=True))
PY
```

Gate interpretation:

- `earnings_calendar_coverage.coverage_status` should be `AVAILABLE` after materialization.
- `financial_statement_coverage.coverage_status` should be `AVAILABLE` after materialization.
- `listing_status_coverage.coverage_status` should be `AVAILABLE`.
- `latest_fallback_used` must be `false`.
- `non_calendar_future_leakage_used` must be `false`.
- `non_calendar_latest_fallback_used` must be `false`.
- Earnings Calendar `historical_pit_compliant=false` is acceptable only when `authority_type=CURRENT_SNAPSHOT_CALENDAR_ONLY` and `exception_scope=earnings_scheduled_date_only`.
- Missing earnings availability authority is acceptable for this schedule-only exception; missing scheduled date remains fail-closed.
- `UNKNOWN_DUE_TO_MISSING_COVERAGE` must be reviewed before 10BD.

Do not start 10BD until this gate is PASS or the symbol-scoped state is formally accepted for the test.

Daily refresh contract for `earnings_calendar`:

- Fetch the current snapshot daily during operations preparation.
- Record snapshot target date, `fetched_at`, row count, source hash, manifest path, and promoted operations path.
- Promote only validated parquet to `.runtime/operations/jquants/raw/jquants/earnings_calendar/data.parquet`.
- Treat stale or missing scheduled-date snapshot metadata as `REVIEW_REQUIRED`.
- Preserve the exception label in all Historical performance evidence:

```text
earnings_calendar_authority = CURRENT_SNAPSHOT_CALENDAR_ONLY
calendar_pit_compliant = false
all_other_inputs_pit_compliant = true
```

## 16. Update History

| Date | Change |
| --- | --- |
| 2026-07-29 | Phase23-U created permanent J-Quants operations runbook and promoted Phase23-T Corporate Event materialization procedure. |
