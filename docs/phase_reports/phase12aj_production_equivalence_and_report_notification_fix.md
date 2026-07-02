# Phase12-AJ Production Equivalence and Report Notification Fix

## Status

```text
PHASE12AJ_PRODUCTION_EQUIVALENCE_AND_REPORT_NOTIFICATION_FIX_COMPLETE
```

Phase12-AJ fixed the remaining Production-equivalence gaps around Daily Report quality, LINE / Discord delivery, launchd exit-code behavior, and explicit Demo / Production difference tracking.

## Production Equivalence Checklist

Daily Report now writes a `production_equivalence_checklist` into:

```text
.runtime/operations/daily_report_refs/YYYY-MM-DD/daily_report_refs.json
.runtime/operations/reports/YYYY-MM-DD/blog_draft.md
.runtime/operations/reports/YYYY-MM-DD/public_report.md
```

2026-06-30 result:

```text
status=PASS
unexpected_demo_production_differences=[]
```

Allowed Demo differences:

```text
demo_special_fill_simulation
persistent_demo_ledger
tachibana_api_env_demo
production_order_disabled
```

One non-blocking item remains:

```text
Capital Allocation接続状況=REVIEW_REQUIRED
```

This is a known deferred integration, not a Demo-only behavioral difference.

## Daily Report Writer Quality

The Daily Report writer now generates human-readable Markdown instead of Python dict / repr output.

Included sections:

- 今日の運用サマリー
- BUY候補
- SELL候補
- Broker / Ledger
- 注文結果 / Fill
- Safety / Reconcile / Audit
- Phase12固有の確認
- データ更新
- Production Equivalence Checklist
- 明日の確認ポイント

The writer also enriches report display with J-Quants listed issue names and market names.

## Today Report Regeneration

Regenerated:

```text
.runtime/operations/reports/2026-06-30/blog_draft.md
.runtime/operations/reports/2026-06-30/public_report.md
.runtime/operations/reports/2026-06-30/safety_report.md
.runtime/operations/reports/2026-06-30/line_payload.json
.runtime/operations/reports/2026-06-30/discord_payload.json
.runtime/operations/daily_report_refs/2026-06-30/daily_report_refs.json
```

Metadata:

```text
regenerated=true
regenerated_reason=phase12aj_daily_report_writer_quality_fix
```

## Notification

`src/ai_fund_lab_v2/operations/notifications.py` provides LINE / Discord delivery from the Operations Daily Report boundary.

2026-06-30 smoke:

```text
line.config_present=true
line.send_attempted=true
line.send_executed=true
line.status=PASS
discord.config_present=true
discord.send_attempted=true
discord.send_executed=true
discord.status=PASS
```

Artifact:

```text
.runtime/operations/notifications/2026-06-30/notification_result.json
```

No token, webhook URL, token hash, token length, raw request, or raw response is saved.

## Exit Code

- `run_daily_report.py` returns exit code 0 when report artifacts are generated.
- `run_demo_special_fill_simulation.py` returns exit code 0 for expected safe no-op states such as not applicable, already simulated, and market closed.
- True unsafe failures remain non-zero.

## Runbook / launchd

Updated:

```text
docs/operations/demo_daily_operation_runbook.md
tools/launchd/com.aifundlab.operations.daily_report.plist
```

The daily report plist runs with:

```text
--send-notifications
```

Codex did not run `launchctl bootstrap` or `launchctl bootout`.

## Verification

```bash
python3 -m pytest tests/phase12 -q
PYTHONPYCACHEPREFIX=/tmp/aifundlab_pycache python3 -m py_compile src/ai_fund_lab_v2/operations/operations.py src/ai_fund_lab_v2/operations/notifications.py scripts/run_daily_report.py scripts/run_demo_special_fill_simulation.py
python3 scripts/run_daily_report.py --trade-date 2026-06-30 --root .runtime/operations --send-notifications
python3 scripts/run_operation_audit.py --root .runtime/operations
python3 -m json.tool reports/phase_reports/phase12aj_production_equivalence_and_report_notification_fix.json
```

Results:

```text
pytest=74 passed
py_compile=PASS
daily_report_smoke=PASS
operation_audit=PASS
json_validation=PASS
```

## Safety

```text
production_order_executed=false
production_unlock_executed=false
ai_retraining_executed=false
backtest_rerun=false
raw_request_saved=false
raw_response_saved=false
secret_saved=false
launchctl_bootstrap_executed=false
```
