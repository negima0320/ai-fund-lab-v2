# Phase14-E11 Runtime v2 Daily Operation Scheduler Implementation

## Final Decision

PHASE14E11_DAILY_OPERATION_SCHEDULER_IMPLEMENTATION_COMPLETE

## Purpose

Phase14-E10で定義したDaily Operation Scheduleを、Runtime v2正規CLIとlaunchd plistへ接続した。

今回の実装は、launchdが判断を持たず、Runtime v2 CLIを起動するだけの構造を維持する。
Broker API Write、Demo Submit、Production注文、Notification実送信、launchd bootstrap/loadは実行していない。

## Implemented Scope

### Runtime v2 CLI

Runtime v2正規CLIに `--job` を追加した。

対象CLI:

- `python -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation`

追加Job:

- `daily_rehearsal`
- `morning`
- `submit`
- `execution`
- `market_refresh`

`daily_rehearsal` はPhase14-E7互換の既定値として残した。
E11の4分割スケジューラでは以下を使う。

| Job | Purpose | Submit |
| --- | --- | --- |
| `morning` | Broker ReadOnly / Current / Business Day / Safety / AI inference / Planning / Approval / Pending | 禁止 |
| `submit` | Pending / Approval再確認 / Safety / Demo Submit checkpoint | 今回は `--submit-enabled false` |
| `execution` | Broker ReadOnly / Execution Reflection / Ledger / Asset / Reconcile / Report / Markdown / Public Report / Audit | 禁止 |
| `market_refresh` | J-Quants / Canonical / Feature / Candidate / Opportunity / Position / Capital Input | AI inference禁止 |

実装では各Jobのcheckpointをmanifestへ記録する。
E11時点では外部Writeを伴う処理は実行せず、`--submit-enabled false` と `--notification-mode payload-only` を必須guardとしている。

## launchd plist

以下の4つのplistを作成した。

| Label | File | Schedule |
| --- | --- | --- |
| `com.aifundlab.runtime_v2.morning` | `tools/launchd/com.aifundlab.runtime_v2.morning.plist` | Mon-Fri 08:45 |
| `com.aifundlab.runtime_v2.submit` | `tools/launchd/com.aifundlab.runtime_v2.submit.plist` | Mon-Fri 08:58 |
| `com.aifundlab.runtime_v2.execution` | `tools/launchd/com.aifundlab.runtime_v2.execution.plist` | Mon-Fri 09:05 |
| `com.aifundlab.runtime_v2.market_refresh` | `tools/launchd/com.aifundlab.runtime_v2.market_refresh.plist` | Mon-Fri 15:30 |

すべてのplistはRuntime v2正規CLIのみを呼ぶ。

共通引数:

```bash
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

## Safety Boundary

維持した禁止事項:

- Phase9 Runtimeを呼ばない
- Phase9 writerを呼ばない
- 旧 `run_phase14d` scriptを日次運用entryにしない
- `.runtime/demo/...` をCurrent pathとして使わない
- phase artifactをCurrentとして扱わない
- Submit sourceを変更しない
- Current固定Pathを変更しない
- Notification実送信をしない
- launchd bootstrap/loadをしない

## Output / Logging

各Jobはstdout/stderr log pathを持つ。

- `/tmp/aifundlab.runtime_v2.morning.out.log`
- `/tmp/aifundlab.runtime_v2.morning.err.log`
- `/tmp/aifundlab.runtime_v2.submit.out.log`
- `/tmp/aifundlab.runtime_v2.submit.err.log`
- `/tmp/aifundlab.runtime_v2.execution.out.log`
- `/tmp/aifundlab.runtime_v2.execution.err.log`
- `/tmp/aifundlab.runtime_v2.market_refresh.out.log`
- `/tmp/aifundlab.runtime_v2.market_refresh.err.log`

CLIはrun manifestを以下へ出力する。

- `.runtime/runtime_state/run_manifest/<business_date>/runtime-v2-<job>-*.json`

## Tests

追加テスト:

- `tests/runtime_v2/test_phase14e11_daily_operation_scheduler.py`

検証内容:

- 4つのplistがRuntime v2正規CLIのみを起動する
- `--job` が各Jobに対応する
- `--submit-enabled false`
- `--notification-mode payload-only`
- `.runtime/demo` をCurrentとして使わない
- Phase9 / 旧Phase14D scriptを呼ばない
- 各Jobのcheckpointがmanifestに記録される
- `market_refresh` では `ai_inference_blocked` を記録し、`ai_inference` を実行しない
- external write / notification send / production order / mode-rooted Current path がすべてfalse

実行結果:

```text
python3 -m pytest tests/runtime_v2/test_phase14e11_daily_operation_scheduler.py
3 passed

python3 -m pytest tests/runtime_v2/test_phase14e7_launchd_daily_operation_rehearsal.py
3 passed

python3 -m pytest tests/runtime_v2
309 passed
```

## Acceptance Check

| Criteria | Result |
| --- | --- |
| 4 Job実装 | PASS |
| CLI実装 | PASS |
| plist作成 | PASS |
| unit test | PASS |
| integration test | PASS |
| Broker API Writeなし | PASS |
| Notification送信なし | PASS |
| launchd bootstrapなし | PASS |

## Remaining Notes

E11はscheduler wiringの実装であり、実際のlaunchd登録・bootstrapは行っていない。
`submit` JobもE11時点では `--submit-enabled false` のcheckpoint運用であり、Broker Writeを行わない。

