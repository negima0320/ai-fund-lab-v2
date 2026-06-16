# Phase9 Scheduler Template

Phase9-G provides scheduler templates only.

It does not automatically register launchd jobs, edit crontab, or copy files into `~/Library/LaunchAgents`.

## Recommendation

Use macOS `launchd` rather than cron for local daily operation. `launchd` integrates better with user sessions and macOS logging behavior.

## Why Manual Install

Scheduler installation changes machine-level user state. Phase9 keeps this manual so the operator can review paths, mode, logs, and timing before enabling automation.

## Manual launchd Install

1. Copy `ops/scheduler/com.aifundlab.phase9.daily.plist.template`.
2. Replace `__WORKING_DIRECTORY__` with the absolute repository path.
3. Replace `__YYYY_MM_DD_OR_WRAPPER_DATE__` with a wrapper script or date argument strategy.
4. Save as `~/Library/LaunchAgents/com.aifundlab.phase9.daily.plist`.
5. Review the file.
6. Manually run:

```bash
launchctl load ~/Library/LaunchAgents/com.aifundlab.phase9.daily.plist
```

## Manual launchd Uninstall

```bash
launchctl unload ~/Library/LaunchAgents/com.aifundlab.phase9.daily.plist
rm ~/Library/LaunchAgents/com.aifundlab.phase9.daily.plist
```

## Cron Example

`ops/scheduler/phase9_daily_cron.example` is a manual sample only. Review and install it yourself with `crontab -e` if you intentionally choose cron.

## Logs

Scheduler stdout/stderr should go under:

```text
.runtime/phase9/scheduler_logs/
```

Operation logs are written under:

```text
.runtime/phase9/operation_logs/
```

## Failure Checks

Check:

- `.runtime/phase9/locks/daily_operation.lock`
- `.runtime/phase9/operation_logs/`
- `.runtime/phase9/scheduler_logs/`
- `reports/phase9/daily/`
- `reports/public/phase9_daily/`

If a stale lock remains after a crash, inspect the operation log first. Use `--force-unlock` only after confirming no active run is still executing.

