# Phase14-E7 launchd Runtime v2 Full Daily Operation Rehearsal

作成日: 2026-07-07

## 最終判定

**PHASE14E7_LAUNCHD_REHEARSAL_READY**

Phase14-E7では、launchd/plistからRuntime v2正規CLIを起動するFull Daily Operation Rehearsalの設計・軽量実装を行った。

launchdは判断しない。launchdはRuntime v2正規CLIを起動するだけである。Runtime v2 CLIがmode、submit可否、notification mode、Current固定Path、Report、Audit、exit code、run manifestを管理する。

今回、plistのload/unloadや`launchctl`操作は行っていない。Demo Submit、Production注文、Notification実送信、Broker API Writeも行っていない。

## 実装内容

追加:

- `src/ai_fund_lab_v2/runtime_v2/cli/__init__.py`
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`
- `tools/launchd/com.aifundlab.runtime_v2.daily_operation_rehearsal.plist`
- `tests/runtime_v2/test_phase14e7_launchd_daily_operation_rehearsal.py`

成果物:

- `docs/phase_reports/phase14_e7_launchd_full_daily_operation_rehearsal.md`
- `reports/phase_reports/phase14_e7_launchd_full_daily_operation_rehearsal.json`

## launchd / plist Contract

plist:

```text
tools/launchd/com.aifundlab.runtime_v2.daily_operation_rehearsal.plist
```

Label:

```text
com.aifundlab.runtime_v2.daily_operation_rehearsal
```

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

Environment:

```text
PYTHONPATH=/Users/negishi/work/ai-fund-lab-v2/src
TACHIBANA_API_ENV=demo
```

stdout/stderr:

```text
/tmp/aifundlab.runtime_v2.daily_operation_rehearsal.out.log
/tmp/aifundlab.runtime_v2.daily_operation_rehearsal.err.log
```

Schedule:

- Monday to Friday
- 08:45
- launchd only starts the Runtime v2 CLI.

## Runtime v2 CLI Contract

正規CLI:

```text
python -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation
```

Initial rehearsal settings:

| Setting | Value |
| --- | --- |
| `--mode` | `demo` |
| `--submit-enabled` | `false` |
| `--notification-mode` | `payload-only` |
| `--stop-on-review-required` | enabled |
| `--stop-on-blocked` | enabled |

Guard behavior:

- `--mode production` is not allowed for Phase14-E7 launchd rehearsal.
- `--submit-enabled true` is blocked with exit code `40`.
- `--notification-mode send-enabled` is blocked with exit code `40`.
- `.runtime/demo/...` as Current root is blocked.
- Report / Public Report / Audit are Derived and are not Submit sources.

## Daily Rehearsal Flow

The CLI records the following stage checkpoints:

1. `cli_start`
2. `operation_contract`
3. `jquants_market_refresh`
4. `feature_refresh`
5. `ai_inference`
6. `planning`
7. `approval`
8. `safety`
9. `broker_readonly`
10. `current_sot_preflight`
11. `ledger_asset_reconcile_report`
12. `markdown_public_report`
13. `notification_payload`
14. `audit`

The initial implementation wires the launchd entry and Runtime v2 checkpoint boundary. The current connected executable actions are:

- fixed Current SoT read
- Runtime v2 preflight
- run manifest output
- Runtime v2 Markdown/Public Report generation
- notification payload artifact generation only
- audit artifact generation
- stdout/stderr launchd log paths
- Runtime v2 internal log path

The J-Quants / Feature / AI / Planning / Approval / Safety / Broker ReadOnly stages are recorded as Runtime v2 operation checkpoints for this launchd rehearsal. Broker API Write and Submit remain disabled.

## Current固定Path

The CLI reads Current only through fixed Runtime v2 paths:

```text
.runtime/persistent_ledger/state.json
.runtime/persistent_ledger/orders.jsonl
.runtime/persistent_ledger/executions.jsonl
.runtime/persistent_ledger/positions.jsonl
.runtime/persistent_ledger/cash.jsonl
.runtime/persistent_ledger/events.jsonl
.runtime/pending_order_plan/pending_order_plan.json
.runtime/runtime_state/current_state.json
```

Forbidden:

- `.runtime/phase14d*/...` as Current.
- `.runtime/demo/...` as Current.
- Phase9 ledger / report as Runtime v2 source.
- `order_plan/YYYY-MM-DD` direct Submit.
- `approval_artifact/YYYY-MM-DD` direct Submit.

## Run Manifest

実Currentで正規CLIをsubmit-disabled / payload-onlyで実行し、run manifestを生成した。

Command:

```text
PYTHONPATH=src python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation --mode demo --business-date 2026-07-07 --submit-enabled false --notification-mode payload-only --stop-on-review-required --stop-on-blocked
```

Exit:

```text
0
```

Manifest:

```text
.runtime/runtime_state/run_manifest/2026-07-07/runtime-v2-daily-2026-07-07-20260707T115826.578167+0000.json
```

Manifest records:

- `run_id`
- `business_date`
- mode
- submit_enabled
- notification_mode
- stages
- generated artifacts
- prohibited actions
- final_state
- exit_code
- warnings
- errors

Observed result:

| Field | Value |
| --- | --- |
| final_state | `CURRENT_STATE_LOADED` |
| exit_code | `0` |
| submit_enabled | `false` |
| notification_mode | `payload-only` |
| errors | `[]` |
| warnings | `[]` |

## Log確認ポイント

launchd stdout/stderr:

```text
/tmp/aifundlab.runtime_v2.daily_operation_rehearsal.out.log
/tmp/aifundlab.runtime_v2.daily_operation_rehearsal.err.log
```

Runtime v2 internal log:

```text
.runtime/runtime_state/logs/2026-07-07/runtime-v2-daily-2026-07-07-20260707T115826.578167+0000.log
```

確認ポイント:

- `stage=cli_start`
- run id
- mode
- exit code
- manifest path
- `current_sot_preflight`
- `markdown_public_report`
- `notification_payload`
- `audit`
- `REVIEW_REQUIRED` / `BLOCKED` / `HALT` occurrence

## Report / Public Report

Generated:

```text
reports/runtime_v2/2026-07-07/runtime_report.md
reports/runtime_v2/2026-07-07/runtime_report.json
reports/runtime_v2/2026-07-07/notification_payload.json
reports/runtime_v2/2026-07-07/audit_result.json
reports/public/runtime_v2/2026-07-07/public_report.md
reports/public/runtime_v2/2026-07-07/public_report.json
reports/public/runtime_v2/latest.md
reports/public/runtime_v2/latest.json
```

`reports/public/runtime_v2/latest.md` was generated.

Public Report redaction scan:

- secret: not output
- raw request / raw response: not output
- plain broker internal id: not output
- Phase9 source: not used
- mode-rooted Current: not used

## Exit Code Design

| Exit code | Meaning |
| --- | --- |
| `0` | success |
| `10` | blocked |
| `20` | review required |
| `30` | halt |
| `40` | config / environment guard error |
| `70` | unexpected error |

For Phase14-E7:

- `--submit-enabled true` returns `40`.
- non-demo mode returns `40`.
- non-payload notification mode returns `40`.
- report redaction failure returns `20`.

## 禁止事項確認

| Item | Result |
| --- | --- |
| Demo Submit | Not executed |
| Production注文 | Not executed |
| Notification実送信 | Not executed |
| Broker API Write | Not executed |
| 旧Phase9 runtime | Not used |
| Phase9 writer | Not used |
| run_phase14d script | Not used |
| phase artifact Current | Not used |
| `.runtime/demo` Current | Not used |
| launchd load/unload | Not executed |

## Verification

Commands:

```text
python3 -m pytest tests/runtime_v2/test_phase14e7_launchd_daily_operation_rehearsal.py
python3 -m pytest tests/runtime_v2
```

Results:

- Phase14-E7 focused tests: 3 passed
- Runtime v2 tests: 297 passed

plist validation:

```text
python3 -m plistlib tools/launchd/com.aifundlab.runtime_v2.daily_operation_rehearsal.plist
```

Result:

- plist parse: PASS

## Acceptance

| Criteria | Result |
| --- | --- |
| launchd starts Runtime v2 regular CLI only | PASS |
| launchd does not decide | PASS |
| old Phase9 plist not reused | PASS |
| old Runtime entry not used | PASS |
| run_phase14d script not used | PASS |
| `--mode demo` | PASS |
| `--submit-enabled false` | PASS |
| `--notification-mode payload-only` | PASS |
| `--stop-on-review-required` | PASS |
| `--stop-on-blocked` | PASS |
| stdout/stderr paths defined | PASS |
| run manifest output | PASS |
| exit code recorded | PASS |
| fixed Current path used | PASS |
| `reports/public/runtime_v2/latest.md` generated | PASS |
| failure stops as REVIEW_REQUIRED/BLOCKED/HALT | PASS by contract |
| log checkpoints documented | PASS |
| Demo Submit not executed | PASS |
| Production order not executed | PASS |
| Notification not sent | PASS |

## Next Handoff

Next phases should connect actual daily pipeline components behind the same Runtime v2 CLI boundary:

- J-Quants refresh adapter hook
- Feature refresh hook
- AI inference hook
- Planning hook
- Approval linkage hook
- Safety runtime hook
- Broker ReadOnly sync hook

The launchd/plist contract should not change when these hooks are filled in. launchd remains a starter only.

## Final Decision

PHASE14E7_LAUNCHD_REHEARSAL_READY
