# Phase23-AD J-Quants OHLCV Materialization Operator Runbook

## 1. Preconditions

Use this runbook only from the repository root.

Required environment:

```bash
export PYTHONPATH=src
export RUNTIME_ROOT=.runtime
export EXTENSION_RUN_ID=jquants-acquisition-20260715-20260717-ad-extension
```

For live J-Quants fetch, `JQUANTS_API_KEY` must be present in the environment or `.env`. Do not print the secret value.

This procedure does not authorize Broker Write, Runtime Switch, resume of the stopped HALT run, or 10BD execution by Codex.

## 2. Read-only Preflight

```bash
pwd
git status --short
python3 --version
df -h . .runtime
```

```bash
PYTHONPATH=src python3 scripts/runtime_test.py run-status --json
```

```bash
PYTHONPATH=src python3 - <<'PY'
import os
print("JQUANTS_API_KEY_present=", bool(os.environ.get("JQUANTS_API_KEY")))
PY
```

```bash
PYTHONPATH=src python3 - <<'PY'
from pathlib import Path
import hashlib
import pandas as pd

paths = {
    "operations_raw_ohlcv": Path(".runtime/operations/jquants/raw/jquants/equities_bars_daily/data.parquet"),
    "operations_normalized_ohlcv": Path(".runtime/operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet"),
    "listed_issues_snapshot_2026_07_15": Path(".runtime/operations/jquants/historical_snapshots/listed_issues/snapshots/2026-07-15/data.parquet"),
    "trading_calendar": Path(".runtime/operations/jquants/raw/jquants/trading_calendar/data.parquet"),
}

for name, path in paths.items():
    print(f"[{name}] path={path} exists={path.is_file()}")
    if not path.is_file():
        continue
    frame = pd.read_parquet(path)
    date_col = next((c for c in ("Date", "target_date", "date", "business_date", "as_of_date") if c in frame.columns), "")
    code_col = next((c for c in ("Code", "code", "LocalCode", "symbol") if c in frame.columns), "")
    dates = frame[date_col].astype(str).str[:10] if date_col else []
    print("  rows=", len(frame), "date_col=", date_col, "code_col=", code_col)
    if date_col:
        print("  min=", dates.min() if len(frame) else "", "max=", dates.max() if len(frame) else "")
        for day in ("2026-07-15", "2026-07-16", "2026-07-17"):
            print("  rows", day, "=", int((dates == day).sum()))
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    print("  sha256=", h.hexdigest())
PY
```

## 3. Acquisition Command

Plan first:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py market-data-acquisition plan \
  --start-date 2026-07-15 \
  --end-date 2026-07-17 \
  --run-id "$EXTENSION_RUN_ID" \
  --chunk day \
  --write-evidence \
  --json
```

Live acquisition, operator only:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py market-data-acquisition run \
  --start-date 2026-07-15 \
  --end-date 2026-07-17 \
  --run-id "$EXTENSION_RUN_ID" \
  --chunk day \
  --confirm \
  --yes-i-understand-this-fetches-large-market-data \
  --write-evidence \
  --json
```

If interrupted:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py market-data-acquisition resume \
  --run-id "$EXTENSION_RUN_ID" \
  --confirm \
  --yes-i-understand-this-fetches-large-market-data \
  --write-evidence \
  --json
```

## 4. Normalization Command

For `market-data-acquisition`, no separate normalization command is required. The Runtime v2 acquisition adapter calls the Production Market Refresh core and writes both:

```text
.runtime/market_data_acquisition/runs/<RUN_ID>/raw/jquants/equities_bars_daily/data.parquet
.runtime/market_data_acquisition/runs/<RUN_ID>/raw_normalized/jquants/equities_bars_daily/data.parquet
```

Legacy normalization exists but is not the selected AD path:

```bash
python3 scripts/normalize_jquants_raw.py \
  --endpoint daily_quotes \
  --runtime-dir .runtime \
  --input-format auto \
  --output-format parquet \
  --validate
```

## 5. Coverage Validation

```bash
PYTHONPATH=src python3 scripts/runtime_test.py market-data-acquisition status \
  --run-id "$EXTENSION_RUN_ID" \
  --json
```

```bash
PYTHONPATH=src python3 - <<'PY'
from pathlib import Path
import hashlib
import pandas as pd

run_id = "jquants-acquisition-20260715-20260717-ad-extension"
paths = {
    "staging_raw_ohlcv": Path(".runtime/market_data_acquisition/runs") / run_id / "raw/jquants/equities_bars_daily/data.parquet",
    "staging_normalized_ohlcv": Path(".runtime/market_data_acquisition/runs") / run_id / "raw_normalized/jquants/equities_bars_daily/data.parquet",
}

for name, path in paths.items():
    print(f"[{name}] path={path} exists={path.is_file()}")
    if not path.is_file():
        continue
    frame = pd.read_parquet(path)
    date_col = next((c for c in ("Date", "target_date", "date") if c in frame.columns), "")
    code_col = next((c for c in ("Code", "code") if c in frame.columns), "")
    dates = frame[date_col].astype(str).str[:10] if date_col else []
    print("  rows=", len(frame), "date_col=", date_col, "code_col=", code_col)
    print("  duplicate_keys=", int(frame.duplicated([date_col, code_col]).sum()) if date_col and code_col else "UNKNOWN")
    if date_col:
        print("  min=", dates.min() if len(frame) else "", "max=", dates.max() if len(frame) else "")
        for day in ("2026-07-15", "2026-07-16", "2026-07-17"):
            print("  rows", day, "=", int((dates == day).sum()))
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    print("  sha256=", h.hexdigest())
PY
```

Acceptance before any promotion discussion:

```text
raw max date >= 2026-07-17
normalized max date >= 2026-07-17
2026-07-15 rows > 0
2026-07-16 rows > 0
2026-07-17 rows > 0
duplicate Date+Code keys = 0
required OHLCV columns present
```

## 6. Canonical Promotion

Stop here.

Phase23-AD found no existing AD-compliant command that atomically promotes both staged raw OHLCV and staged normalized OHLCV into:

```text
.runtime/operations/jquants/raw/jquants/equities_bars_daily/data.parquet
.runtime/operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet
```

The existing `market-data-bootstrap run` promotes normalized OHLCV only, with backup and `os.replace`.

Review-only command:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py market-data-bootstrap plan \
  --source-path ".runtime/market_data_acquisition/runs/$EXTENSION_RUN_ID/raw_normalized/jquants/equities_bars_daily/data.parquet" \
  --target-start-date 2026-07-15 \
  --target-end-date 2026-07-17 \
  --write-evidence \
  --json
```

Do not execute `market-data-bootstrap run` for Phase23-AD until the raw+normalized promotion safety gap is resolved.

## 7. Post-promotion Verification

After a future approved raw+normalized promotion command exists and is executed by the Operator, repeat the Read-only Preflight inventory. Expected:

```text
operations raw OHLCV max date >= 2026-07-17
operations normalized OHLCV max date >= 2026-07-17
2026-07-15 rows > 0
2026-07-16 rows > 0
2026-07-17 rows > 0
QUOTE_TARGET_DATE_MISSING absent
```

## 8. 2026-07-15 Isolated Verification

First run read-only plan:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py plan \
  --profile historical-smoke \
  --start-date 2026-07-15 \
  --business-days 1 \
  --json
```

Do not run the isolated Runtime replay until canonical promotion is approved and completed.

## 9. Existing HALT Run Abandon

Do not resume:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260729T065337151378Z/
```

The source baseline changes after materialization. Use a new fresh-run after the materialization gate passes.

## 10. 10BD Fresh-run Command

Only after promotion gap closure, post-promotion verification, and 2026-07-15 isolated verification PASS:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-smoke \
  --start-date 2026-07-06 \
  --business-days 10 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

Codex must not run this command.

## 11. Failure時の停止条件

Stop and request Codex review if any condition appears:

```text
JQUANTS_API_KEY missing
acquisition status != PASS
raw or normalized staging file missing
2026-07-15 / 2026-07-16 / 2026-07-17 row count = 0
duplicate Date+Code keys > 0
manifest missing or not PASS
bootstrap plan attempts normalized-only promotion
raw+normalized atomic promotion command still absent
```

## 12. 取得するEvidence

Preserve:

```text
.runtime/market_data_acquisition/runs/<RUN_ID>/plan.json
.runtime/market_data_acquisition/runs/<RUN_ID>/state.json
.runtime/market_data_acquisition/runs/<RUN_ID>/raw/jquants/equities_bars_daily/data.parquet
.runtime/market_data_acquisition/runs/<RUN_ID>/raw_normalized/jquants/equities_bars_daily/data.parquet
.runtime/market_data_acquisition/runs/<RUN_ID>/market_refresh_manifests/
preflight stdout
coverage validation stdout
post-promotion inventory stdout, after a future approved promotion
```
