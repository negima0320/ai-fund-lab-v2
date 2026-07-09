# Phase14-E9 Runtime v2 launchd Registration Readiness / Install Plan

作成日: 2026-07-07

## 最終判定

**PHASE14E9_LAUNCHD_REGISTRATION_READY**

Phase14-E8でDemo Operation初期状態を100万円・保有0へ修正した。Phase14-E9では、Runtime v2正規CLIを明日朝launchd/plistで自動起動するため、登録前の最終確認と登録・rollback手順を整理した。

今回は確認と手順作成のみであり、launchd `bootstrap` / `load` / `bootout` は実行していない。Submit、Broker API Write、Production注文、Notification実送信も行っていない。

## 対象plist

```text
tools/launchd/com.aifundlab.runtime_v2.daily_operation_rehearsal.plist
```

Label:

```text
com.aifundlab.runtime_v2.daily_operation_rehearsal
```

構文確認:

```text
python3 -m plistlib tools/launchd/com.aifundlab.runtime_v2.daily_operation_rehearsal.plist
```

Result:

```text
PASS
```

## plist確認結果

| Item | Result |
| --- | --- |
| plist構文 | PASS |
| Label | `com.aifundlab.runtime_v2.daily_operation_rehearsal` |
| WorkingDirectory | `/Users/negishi/work/ai-fund-lab-v2` |
| EnvironmentVariables | `PYTHONPATH=/Users/negishi/work/ai-fund-lab-v2/src`, `TACHIBANA_API_ENV=demo` |
| ProgramArguments | Runtime v2正規CLIのみ |
| StartCalendarInterval | Weekday 2-6, 08:45 |
| stdout | `/tmp/aifundlab.runtime_v2.daily_operation_rehearsal.out.log` |
| stderr | `/tmp/aifundlab.runtime_v2.daily_operation_rehearsal.err.log` |

ProgramArguments:

```text
/usr/bin/python3
-m
ai_fund_lab_v2.runtime_v2.cli.run_daily_operation
--mode demo
--submit-enabled false
--notification-mode payload-only
--stop-on-review-required
--stop-on-blocked
--runtime-root .runtime
--reports-root reports/runtime_v2
--public-reports-root reports/public/runtime_v2
--manifest-root .runtime/runtime_state/run_manifest
--log-root .runtime/runtime_state/logs
```

禁止entry未使用:

- 旧Phase9 runtime: 未使用
- 旧Runtime entry: 未使用
- `run_phase14d` script: 未使用
- Phase9 writer: 未使用
- `.runtime/demo/...` Current: 未使用
- phase artifact Current: 未使用

## Current SoT確認

確認対象:

```text
.runtime/persistent_ledger/state.json
reports/public/runtime_v2/latest.md
```

Current SoT:

| Field | Value |
| --- | --- |
| cash | 1,000,000 |
| buying_power | 1,000,000 |
| market_value | 0 |
| total_equity | 1,000,000 |
| positions | [] |
| environment | demo |
| source | `phase14e8_demo_operation_initial_state` |
| review_required | false |
| current_state_confirmed_empty | true |

Public Report:

- Cash: JPY 1,000,000
- Buying power: JPY 1,000,000
- Market value: JPY 0
- Total equity: JPY 1,000,000
- Holdings: No active positions

## Demo Broker Capability確認

Phase14-E8でmodeから自動決定するBrokerCapabilityを実装済み。

Demo capability:

- `supports_daily_reset = true`
- `cash_as_truth = false`
- `buying_power_as_truth = false`
- `positions_as_truth = false`
- `executions_as_truth = true`
- `order_status_as_truth = true`
- `supports_9000_series_orders = false`
- `default_evaluation_capital = 1000000`
- `broker_cash_is_evidence_only = true`
- `broker_positions_are_evidence_only_after_reset = true`

9000番台BLOCK guard:

- Demo Submit preflightで9000番台はBLOCK。
- Planning helperでもCapability filterを利用可能。
- Capability外部設定ファイルは不要。

## launchctl登録状態

確認コマンド:

```text
launchctl print gui/$(id -u)/com.aifundlab.runtime_v2.daily_operation_rehearsal
```

Result:

```text
Could not find service "com.aifundlab.runtime_v2.daily_operation_rehearsal" in domain for user gui: 501
```

判定:

```text
NOT_REGISTERED
```

これは登録前状態として期待通り。Phase14-E9では登録は実行していない。

## Install Plan

実行予定コマンド。Phase14-E9では未実行。

```text
mkdir -p ~/Library/LaunchAgents
cp tools/launchd/com.aifundlab.runtime_v2.daily_operation_rehearsal.plist ~/Library/LaunchAgents/com.aifundlab.runtime_v2.daily_operation_rehearsal.plist
plutil -lint ~/Library/LaunchAgents/com.aifundlab.runtime_v2.daily_operation_rehearsal.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.aifundlab.runtime_v2.daily_operation_rehearsal.plist
launchctl print gui/$(id -u)/com.aifundlab.runtime_v2.daily_operation_rehearsal
```

手動即時dry rehearsalを行う場合:

```text
launchctl kickstart -k gui/$(id -u)/com.aifundlab.runtime_v2.daily_operation_rehearsal
```

ただし、kickstart前にCurrent SoTとPublic Reportを再確認する。

## Rollback Plan

登録解除:

```text
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.aifundlab.runtime_v2.daily_operation_rehearsal.plist
```

plist退避:

```text
mv ~/Library/LaunchAgents/com.aifundlab.runtime_v2.daily_operation_rehearsal.plist ~/Library/LaunchAgents/com.aifundlab.runtime_v2.daily_operation_rehearsal.plist.disabled
```

登録状態確認:

```text
launchctl print gui/$(id -u)/com.aifundlab.runtime_v2.daily_operation_rehearsal
```

期待:

```text
Could not find service
```

## Log Check Commands

launchd stdout:

```text
tail -n 200 /tmp/aifundlab.runtime_v2.daily_operation_rehearsal.out.log
```

launchd stderr:

```text
tail -n 200 /tmp/aifundlab.runtime_v2.daily_operation_rehearsal.err.log
```

Runtime v2 manifest:

```text
ls -lt .runtime/runtime_state/run_manifest/$(date +%F)/
```

Runtime v2 internal log:

```text
ls -lt .runtime/runtime_state/logs/$(date +%F)/
tail -n 200 .runtime/runtime_state/logs/$(date +%F)/*.log
```

Public Report:

```text
sed -n '1,120p' reports/public/runtime_v2/latest.md
```

確認ポイント:

- `exit_code`
- `final_state`
- `current_sot_preflight`
- `markdown_public_report`
- `notification_payload`
- `audit`
- `REVIEW_REQUIRED` / `BLOCKED` / `HALT`
- Submitが実行されていないこと
- Notificationが実送信されていないこと

## Command Safety Status

| Check | Result |
| --- | --- |
| Runtime v2正規CLIのみ起動 | PASS |
| `--mode demo` | PASS |
| `--submit-enabled false` | PASS |
| `--notification-mode payload-only` | PASS |
| `--stop-on-review-required` | PASS |
| `--stop-on-blocked` | PASS |
| Production endpoint指定なし | PASS |
| Phase9 / 旧Runtime / run_phase14d未使用 | PASS |

## Readiness

| Item | Result |
| --- | --- |
| plist構文PASS | PASS |
| Runtime v2正規CLIのみ起動 | PASS |
| submit-enabled=false | PASS |
| notification payload-only | PASS |
| Current SoT 100万円・保有0 | PASS |
| Demo capability有効 | PASS |
| 9000番台BLOCK guard有効 | PASS |
| Public Report 100万円・保有0 | PASS |
| launchd登録状態確認 | PASS, NOT_REGISTERED |
| install手順明記 | PASS |
| rollback手順明記 | PASS |
| launchd load/bootstrap未実行 | PASS |
| Submitなし | PASS |
| Broker API Writeなし | PASS |

## Final Decision

PHASE14E9_LAUNCHD_REGISTRATION_READY
