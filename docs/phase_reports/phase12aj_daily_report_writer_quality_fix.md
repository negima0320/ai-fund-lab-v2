# Phase12-AJ Daily Report Writer Quality Fix

## Status

```text
PHASE12AJ_DAILY_REPORT_WRITER_QUALITY_FIX_COMPLETE
```

Phase12 Daily Report writer was updated so future launchd-generated reports use human-readable operations blog formatting instead of Python dict / JSON-style log dumps.

## What Changed

- Reworked `run_daily_report()` output generation in `src/ai_fund_lab_v2/operations/operations.py`.
- Added a structured Daily Report model used by:
  - `blog_draft.md`
  - `public_report.md`
  - `line_payload.json`
  - `discord_payload.json`
- Updated notification delivery to prefer the report writer's summary text.
- Added display enrichment from J-Quants listed info for issue name and market.
- Displayed submitted order normalization results when available.
- Displayed unsubmitted zero-price planned items as `submit時に正規化` rather than showing misleading `0`.

## Report Content

The generated Markdown now includes:

- Daily operations summary
- BUY candidate table
- SELL candidate table
- Broker / Ledger section
- Safety / Reconcile / Audit section
- Phase12-specific section:
  - Demo Special Fill
  - Persistent Demo Ledger
  - Market Calendar
- Data freshness / candidate count section

Direct Python repr / dict dumps are no longer written to Markdown.

## Smoke Result

Executed:

```bash
python3 scripts/run_daily_report.py --trade-date 2026-06-30 --root .runtime/operations
```

Generated:

```text
.runtime/operations/reports/2026-06-30/blog_draft.md
.runtime/operations/reports/2026-06-30/public_report.md
.runtime/operations/reports/2026-06-30/line_payload.json
.runtime/operations/reports/2026-06-30/discord_payload.json
```

The Markdown output is now narrative plus tables, and the notification payloads contain `summary_text` and section summaries suitable for LINE / Discord delivery.

## Tests

```bash
python3 -m pytest tests/phase12 -q
PYTHONPYCACHEPREFIX=/tmp/aifundlab_pycache python3 -m py_compile src/ai_fund_lab_v2/operations/operations.py src/ai_fund_lab_v2/operations/notifications.py scripts/run_daily_report.py
python3 -m json.tool reports/phase_reports/phase12aj_daily_report_writer_quality_fix.json
```

## Safety

```text
demo_order_executed=false
production_order_executed=false
ai_retraining_executed=false
backtest_rerun=false
raw_request_saved=false
raw_response_saved=false
secret_saved=false
```
