# Phase14-E14 Notification / Blog Delivery Readiness Audit

作成日: 2026-07-07

## 最終判定

**PHASE14E14_GAP_FOUND**

## 目的

2026-07-08のDemo運用テスト開始前に、Runtime v2の出力系であるReport / Markdown / Public Report / Blog相当 / LINE / Discord / Notificationが設計どおり接続されているか監査した。

今回実施したのは監査のみである。
コード変更、Broker API呼び出し、Submit、Notification実送信、launchd変更は行っていない。

## 結論

Runtime v2のReport / Markdown / Public Report / latest.md / latest.json / Notification Payload生成は実装済みかつRuntime v2正規CLIから接続済みで、Day1 Demo運用の人間向け出力としてREADYである。

一方、LINE / Discordの実送信adapter、および送信用Notification SchedulerはRuntime v2正規経路には未実装・未接続である。
`--notification-mode payload-only` により実送信は安全に止まっているが、「実運用開始したらLINE/Discordが自動送信される状態」にはまだ到達していない。

したがって最終判定は `PHASE14E14_GAP_FOUND` とする。

## Audit Matrix

| Item | Implemented | Connected | Ready | 判定 |
| --- | --- | --- | --- | --- |
| Runtime Report | yes | yes | yes | READY |
| Markdown Report | yes | yes | yes | READY |
| Public Report / Blog相当 | yes | yes | yes | READY |
| latest.md更新 | yes | yes | yes | READY |
| latest.json更新 | yes | yes | yes | READY |
| Notification Payload生成 | yes | yes | yes, payload-only | READY |
| LINE通知接続 | no sender | no | no | NOT_IMPLEMENTED |
| Discord通知接続 | no sender | no | no | NOT_IMPLEMENTED |
| Notification Scheduler | delivery ledger only | no send scheduler | no | NOT_CONNECTED |
| Market Refresh後のReport生成 | yes | yes via common CLI tail | yes | CONNECTED |
| Execution後のReport生成 | yes | yes via common CLI tail | yes | CONNECTED |
| launchd Jobとの接続 | yes | yes | payload-only | READY |
| Runtime v2正規CLIから呼ばれているか | yes | yes | yes | READY |
| Phase9 writer未使用 | yes | yes | yes | READY |
| Phase9 runtime未使用 | yes | yes | yes | READY |
| Runtime v2 Report / Currentのみsource | yes | yes | yes | READY |

## Evidence

### Runtime v2正規CLI接続

対象:

- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`

確認内容:

- `generate_public_report_from_current(...)` をRuntime v2 CLIから呼んでいる。
- 実行後stageとして以下を記録する。
  - `ledger_asset_reconcile_report`
  - `markdown_public_report`
  - `notification_payload`
  - `audit`
- manifestの `prohibited_actions.notification_sent` は `False`。
- manifestの `prohibited_actions.phase9_runtime_called` は `False`。
- manifestの `prohibited_actions.phase9_writer_called` は `False`。
- `--notification-mode` はCLI引数として存在するが、E14時点では `payload-only` 以外をconfig errorで拒否する。

### Report / Markdown / Public Report

対象:

- `src/ai_fund_lab_v2/runtime_v2/report/public_report_writer.py`
- `src/ai_fund_lab_v2/runtime_v2/report/markdown_writer.py`

確認内容:

- `generate_public_report_from_current(...)` がRuntime v2 fixed Current SoTからcontextを読む。
- `load_runtime_v2_report_context(...)` の入力は以下に限定される。
  - `persistent_ledger/state.json`
  - `persistent_ledger/orders.jsonl`
  - `persistent_ledger/executions.jsonl`
  - `persistent_ledger/positions.jsonl`
  - `persistent_ledger/cash.jsonl`
  - `persistent_ledger/events.jsonl`
  - `pending_order_plan/pending_order_plan.json`
  - `runtime_state/current_state.json`
- `.runtime/demo` やPhase9 artifactをCurrent sourceにしないguardがある。
- Public Report redaction scanがある。

既存artifact:

- `reports/runtime_v2/2026-07-07/runtime_report.json`
- `reports/runtime_v2/2026-07-07/runtime_report.md`
- `reports/runtime_v2/2026-07-07/notification_payload.json`
- `reports/runtime_v2/2026-07-07/audit_result.json`
- `reports/public/runtime_v2/2026-07-07/public_report.md`
- `reports/public/runtime_v2/2026-07-07/public_report.json`
- `reports/public/runtime_v2/latest.md`
- `reports/public/runtime_v2/latest.json`

`latest.md` は100万円・保有0を表示し、Notificationは「payload summary only; no delivery was sent」と明記している。

### Notification Payload

対象:

- `src/ai_fund_lab_v2/runtime_v2/notification/payload.py`
- `src/ai_fund_lab_v2/runtime_v2/notification/delivery_ledger.py`
- `reports/runtime_v2/2026-07-07/notification_payload.json`

確認内容:

- Runtime v2のpayload builderは存在する。
- channel指定のpayloadを作るmodelはある。
- delivery ledger modelは `line` / `discord` channelを表現できる。
- `POST_SEND_UNKNOWN` などのdelivery statusも表現できる。
- ただしRuntime v2配下にLINE/Discordの実送信adapterは存在しない。
- `DeliveryLedgerRecord` にsender methodはなく、送信処理を持たない。
- Runtime v2 import guardではnotification payloadがsender/send moduleをimportしないことを固定している。

既存payload:

```json
{
  "business_date": "2026-07-07",
  "mode": "payload-only",
  "send_executed": false
}
```

### LINE / Discord

Runtime v2配下で確認されたNotification関連ファイル:

- `src/ai_fund_lab_v2/runtime_v2/notification/__init__.py`
- `src/ai_fund_lab_v2/runtime_v2/notification/delivery_ledger.py`
- `src/ai_fund_lab_v2/runtime_v2/notification/models.py`
- `src/ai_fund_lab_v2/runtime_v2/notification/payload.py`

未確認/未実装:

- Runtime v2 LINE sender
- Runtime v2 Discord sender
- Runtime v2 webhook adapter
- Runtime v2 notification send CLI
- Runtime v2 notification send scheduler

旧 `ai_fund_lab_v2.operations` 側にはLINE/Discord送信系の痕跡があるが、Runtime v2正規経路としては使っていない。
Phase9 writer / Phase9 runtimeを復活させない方針に沿い、E14では旧実装を接続済みとは扱わない。

## launchd接続

対象:

- `tools/launchd/com.aifundlab.runtime_v2.morning.plist`
- `tools/launchd/com.aifundlab.runtime_v2.submit.plist`
- `tools/launchd/com.aifundlab.runtime_v2.execution.plist`
- `tools/launchd/com.aifundlab.runtime_v2.market_refresh.plist`

確認内容:

- 4 JobすべてRuntime v2正規CLIのみを起動する。
- `--notification-mode payload-only`。
- Phase9 runtime / Phase9 writer / `run_phase14d` script未使用。
- 実送信は行わない。

## Verification

実行:

```text
python3 -m pytest tests/runtime_v2/test_phase14e6_runtime_v2_public_report_output.py tests/runtime_v2/test_phase13_t_delivery_ledger.py tests/runtime_v2/test_phase13_v_import_graph_cycle_guard.py
```

結果:

```text
14 passed
```

確認したartifact:

```text
reports/runtime_v2/2026-07-07/runtime_report.json
reports/runtime_v2/2026-07-07/runtime_report.md
reports/runtime_v2/2026-07-07/notification_payload.json
reports/runtime_v2/2026-07-07/audit_result.json
reports/public/runtime_v2/2026-07-07/public_report.md
reports/public/runtime_v2/2026-07-07/public_report.json
reports/public/runtime_v2/latest.md
reports/public/runtime_v2/latest.json
```

## Blocker List

Day1 Demo運用のReport/Blog相当/notification payload-onlyに対するblocker:

- なし

LINE/Discord自動実送信を開始するためのblocker:

- Runtime v2 LINE sender未実装。
- Runtime v2 Discord sender未実装。
- Runtime v2 notification send scheduler未接続。
- Delivery ledgerはmodelのみで、実送信のidempotency適用箇所が未接続。
- `--notification-mode send-enabled` はCLIで拒否される。

## Readiness

| Area | Readiness |
| --- | --- |
| Runtime Report | GREEN |
| Markdown Report | GREEN |
| Public Report / Blog相当 | GREEN |
| latest.md / latest.json | GREEN |
| Notification Payload | GREEN, payload-only |
| LINE | RED |
| Discord | RED |
| Notification Scheduler | RED |
| Day1 Demo運用 | GREEN for payload-only |
| Day1 LINE/Discord実送信 | NOT READY |

## Acceptance

| Criteria | Result |
| --- | --- |
| 実装状況を証拠付きで整理 | PASS |
| Runtime v2正規経路か確認 | PASS |
| Phase9未使用確認 | PASS |
| 実送信していない | PASS |
| コード変更していない | PASS |
| launchd変更していない | PASS |

