# Phase12-AI Notification Delivery and Parity Audit

## Status

```text
PHASE12AI_NOTIFICATION_DELIVERY_AND_PARITY_AUDIT_COMPLETE
```

Phase12-AI implemented Production-equivalent Operations notification delivery for LINE and Discord, updated Daily Report launchd execution, and fixed audit parity so notification delivery is no longer treated as a leakage violation.

## Implementation Summary

- Added `src/ai_fund_lab_v2/operations/notifications.py`.
- Added `scripts/run_daily_report.py --send-notifications`.
- Updated `tools/launchd/com.aifundlab.operations.daily_report.plist` to pass `--send-notifications`.
- Added notification result artifact:

```text
.runtime/operations/notifications/YYYY-MM-DD/notification_result.json
```

- Updated Daily Report refs and `line_payload.json` with redacted notification status.
- Added Demo / Production parity audit to Operations Audit.
- Updated exit code behavior:
  - Daily Report returns 0 when report artifacts are generated.
  - Demo Special Fill safe no-op / not applicable cases return 0.
- Updated leakage audit so `line_send_executed=true` is allowed after Phase12-AI, while raw response, secret, and production-order markers remain blocked.

## Notification Configuration

LINE Messaging API:

```text
AIFUNDLAB_LINE_CHANNEL_ACCESS_TOKEN
AIFUNDLAB_LINE_TO_ID
LINE_CHANNEL_ACCESS_TOKEN
LINE_MESSAGING_API_TOKEN
LINE_USER_ID
LINE_TO
```

Discord:

```text
AIFUNDLAB_DISCORD_WEBHOOK_URL
DISCORD_WEBHOOK_URL
```

Secrets are loaded only at the final send boundary. No token value, token hash, token length, raw request, or raw response is saved.

## 2026-06-30 Smoke Result

`run_daily_report.py --send-notifications` was executed.

```text
line.config_present=true
line.send_attempted=true
line.send_executed=true
line.status=PASS
discord.config_present=true
discord.send_attempted=true
discord_send_executed=true
discord.status=PASS
```

Artifact:

```text
.runtime/operations/notifications/2026-06-30/notification_result.json
```

## Demo / Production Parity Audit

Allowed differences:

```text
demo_special_fill_simulation
persistent_demo_ledger
tachibana_api_env_demo
production_order_disabled
```

Unexpected differences:

```text
none
```

Operation Audit result after the fix:

```text
status=PASS
line_send_executed=true
discord_send_executed=true
leakage_audit=PASS
demo_production_parity_audit=PASS
```

## Safety Confirmation

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

## Tests

```bash
python3 -m pytest tests/phase12 -q
PYTHONPYCACHEPREFIX=/tmp/aifundlab_pycache python3 -m py_compile src/ai_fund_lab_v2/operations/notifications.py src/ai_fund_lab_v2/operations/operations.py src/ai_fund_lab_v2/operations/guards.py scripts/run_daily_report.py scripts/run_demo_special_fill_simulation.py
python3 -m json.tool reports/phase_reports/phase12ai_notification_delivery_and_parity_audit.json
```

## User Re-registration Step

Codex did not run `launchctl bootstrap` or `launchctl bootout`.

After review, copy and reload the updated plist manually:

```bash
cp tools/launchd/com.aifundlab.operations.daily_report.plist ~/Library/LaunchAgents/
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.aifundlab.operations.daily_report.plist 2>/dev/null || true
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.aifundlab.operations.daily_report.plist
```
