# Phase14-E13 Day1 Demo Submit Enable / launchd Registration Plan

作成日: 2026-07-07

## 最終判定

**PHASE14E13_DAY1_DEMO_OPERATION_READY**

## 目的

2026-07-08から注文ありのRuntime v2 Demo運用テストを開始できる状態へ修正した。

今回実施したのは、submit jobのみのSubmit有効化、CLI guard更新、Pending待機状態の整理、launchd登録手順の最終化、テストである。
Submit、Broker API Write、Production注文、Notification実送信、launchd bootstrap/loadは実行していない。

## 実施内容

### 1. submit plistのみSubmit有効化

変更:

- `tools/launchd/com.aifundlab.runtime_v2.submit.plist`
- `--submit-enabled false` から `--submit-enabled true` へ変更

維持:

- `--mode demo`
- `--job submit`
- `--notification-mode payload-only`
- Runtime v2正規CLIのみ起動
- Phase9 Runtime / Phase9 writer / run_phase14d script未使用

### 2. 他3JobはSubmit禁止を維持

| Job | plist | submit-enabled |
| --- | --- | --- |
| morning | `tools/launchd/com.aifundlab.runtime_v2.morning.plist` | false |
| execution | `tools/launchd/com.aifundlab.runtime_v2.execution.plist` | false |
| market_refresh | `tools/launchd/com.aifundlab.runtime_v2.market_refresh.plist` | false |

### 3. Runtime v2 CLI guard更新

対象:

- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`

変更:

- `--submit-enabled true` は `--job submit` のみ許可。
- `morning` / `execution` / `market_refresh` / `daily_rehearsal` で `--submit-enabled true` の場合はconfig errorで停止。

これにより、plistだけでなくCLI側でもsubmit job以外のSubmit有効化を拒否する。

### 4. Pending状態整理

E12時点ではPhase14-D15由来の `CONSUMED` Pendingがcanonical pathに残っていた。
E13ではDay1 morning jobが新しいPendingを生成するまでの待機状態として、Pending Currentを以下へ整理した。

Path:

- `.runtime/pending_order_plan/pending_order_plan.json`

状態:

```text
state = PENDING_APPROVAL
pending_plan_id = pending-phase14e13-day1-awaiting-morning-plan
intended_submit_date = 2026-07-08
target_session_date = 2026-07-08
items = []
approval = null
consume.consumed = false
submit_constraints.allow_post_send_unknown_resubmit = false
```

確認:

- stale pendingなし
- consumed pendingなし
- submitted pendingなし
- post_send_unknownなし
- monitoring_fill相当なし
- raw request / raw response / secret保存なし

この待機Pendingは承認済み注文を持たないため、そのままではSubmit対象にならない。
Day1では08:45のmorning jobが当日Planning / Approval / Pending生成を行い、08:58のsubmit jobが当日Pendingのみを対象にする。

### 5. Current SoT再確認

対象:

- `.runtime/persistent_ledger/state.json`

確認結果:

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
| production_equivalent | false |

Asset Current SoTは変更していない。

### 6. Demo Capability / 9000番台Guard確認

確認対象:

- `src/ai_fund_lab_v2/runtime_v2/broker_adapter/capability.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/guards.py`
- `tests/runtime_v2/test_phase14e13_day1_demo_submit_enable.py`

Demo capability:

```text
default_evaluation_capital = 1000000
cash_as_truth = false
positions_as_truth = false
supports_9000_series_orders = false
```

確認:

- mode=demo capability有効。
- Demo broker cash 2,000万円はRuntime cash SoTにしない。
- Demo positions resetでCurrent positionsを自動消去しない。
- 9432のような9000番台はSubmit preflightでBLOCK。
- Production capabilityでは9000番台除外しない。

## launchd登録手順

注意:

- E13では登録コマンドを明記するだけで、bootstrap/loadは実行していない。
- 登録前に必ずplist内容とCurrent/Pending状態を再確認する。

登録:

```bash
launchctl bootstrap "gui/$(id -u)" tools/launchd/com.aifundlab.runtime_v2.morning.plist
launchctl bootstrap "gui/$(id -u)" tools/launchd/com.aifundlab.runtime_v2.submit.plist
launchctl bootstrap "gui/$(id -u)" tools/launchd/com.aifundlab.runtime_v2.execution.plist
launchctl bootstrap "gui/$(id -u)" tools/launchd/com.aifundlab.runtime_v2.market_refresh.plist
```

登録確認:

```bash
launchctl print "gui/$(id -u)/com.aifundlab.runtime_v2.morning"
launchctl print "gui/$(id -u)/com.aifundlab.runtime_v2.submit"
launchctl print "gui/$(id -u)/com.aifundlab.runtime_v2.execution"
launchctl print "gui/$(id -u)/com.aifundlab.runtime_v2.market_refresh"
```

ログ確認:

```bash
tail -n 200 /tmp/aifundlab.runtime_v2.morning.out.log
tail -n 200 /tmp/aifundlab.runtime_v2.morning.err.log
tail -n 200 /tmp/aifundlab.runtime_v2.submit.out.log
tail -n 200 /tmp/aifundlab.runtime_v2.submit.err.log
tail -n 200 /tmp/aifundlab.runtime_v2.execution.out.log
tail -n 200 /tmp/aifundlab.runtime_v2.execution.err.log
tail -n 200 /tmp/aifundlab.runtime_v2.market_refresh.out.log
tail -n 200 /tmp/aifundlab.runtime_v2.market_refresh.err.log
```

manifest確認:

```bash
ls -la .runtime/runtime_state/run_manifest/2026-07-08
```

Public Report確認:

```bash
sed -n '1,200p' reports/public/runtime_v2/latest.md
```

## Rollback手順

登録解除:

```bash
launchctl bootout "gui/$(id -u)" tools/launchd/com.aifundlab.runtime_v2.morning.plist
launchctl bootout "gui/$(id -u)" tools/launchd/com.aifundlab.runtime_v2.submit.plist
launchctl bootout "gui/$(id -u)" tools/launchd/com.aifundlab.runtime_v2.execution.plist
launchctl bootout "gui/$(id -u)" tools/launchd/com.aifundlab.runtime_v2.market_refresh.plist
```

確認:

```bash
launchctl print "gui/$(id -u)/com.aifundlab.runtime_v2.morning"
launchctl print "gui/$(id -u)/com.aifundlab.runtime_v2.submit"
launchctl print "gui/$(id -u)/com.aifundlab.runtime_v2.execution"
launchctl print "gui/$(id -u)/com.aifundlab.runtime_v2.market_refresh"
```

## 現在のlaunchd登録状態

E13実施時点では4 Jobとも未登録。

| Job | Registered |
| --- | --- |
| morning | false |
| submit | false |
| execution | false |
| market_refresh | false |

## Tests

追加/更新:

- `tests/runtime_v2/test_phase14e11_daily_operation_scheduler.py`
- `tests/runtime_v2/test_phase14e13_day1_demo_submit_enable.py`

実行結果:

```text
python3 -m pytest tests/runtime_v2/test_phase14e11_daily_operation_scheduler.py tests/runtime_v2/test_phase14e13_day1_demo_submit_enable.py
6 passed

python3 -m pytest tests/runtime_v2
312 passed
```

## 禁止事項確認

| Item | Result |
| --- | --- |
| Submit | Not executed |
| Broker API Write | Not executed |
| Production注文 | Not executed |
| Notification実送信 | Not executed |
| launchd bootstrap/load | Not executed |
| Phase9 Runtime | Not used |
| Phase9 writer | Not used |
| `.runtime/demo` Current path | Not used |

## Acceptance

| Criteria | Result |
| --- | --- |
| submit jobのみ submit-enabled=true | PASS |
| 他3Jobは submit-enabled=false | PASS |
| mode=demo | PASS |
| notification-mode=payload-only | PASS |
| Demo Capability有効 | PASS |
| 9000番台BLOCK guard確認 | PASS |
| launchd登録コマンド明記 | PASS |
| rollbackコマンド明記 | PASS |
| tests/runtime_v2 PASS | PASS |

