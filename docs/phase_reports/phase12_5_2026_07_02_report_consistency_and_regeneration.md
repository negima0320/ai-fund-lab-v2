# Phase12.5 2026-07-02 Report Consistency and Regeneration

## Scope

2026-07-02 の public report / blog / notification payload / daily report refs が、Phase12.5 修正後ロジックと現在の Runtime artifact に整合しているか確認した。

今回は Report 系 artifact のみ再生成した。Submit / Broker / Fill / Reconcile / Approval / Order Plan / demo ledger / notification_result は変更していない。

## Checked Artifacts

- `.runtime/operations/reports/2026-07-02/public_report.md`
- `.runtime/operations/reports/2026-07-02/blog_draft.md`
- `.runtime/operations/reports/2026-07-02/line_payload.json`
- `.runtime/operations/reports/2026-07-02/discord_payload.json`
- `.runtime/operations/daily_report_refs/2026-07-02/daily_report_refs.json`
- `.runtime/operations/submitted_orders/2026-07-02/submitted_orders.json`
- `.runtime/operations/broker_orders/2026-07-02/orders.json`
- `.runtime/operations/broker_executions/2026-07-02/executions.json`
- `.runtime/operations/broker_positions/2026-07-02/positions.json`
- `.runtime/operations/fill_events/2026-07-02/fill_events.json`
- `.runtime/operations/reconciliation_result/2026-07-02/reconciliation_result.json`
- `.runtime/operations/approval_artifact/2026-07-02/approval_artifact.json`
- `.runtime/operations/demo_ledger/state.json`

## Pre-Regeneration Finding

7/2 の public report / blog draft / daily_report_refs は古かった。

- `public_report.md` / `blog_draft.md` は `2026-07-02 20:19:29 +0900` 生成だった。
- 最新の `submitted_orders.json` は `2026-07-02 21:48:46 +0900` 生成で、launchd 由来の共通 Submit 結果だった。
- 古い report には「本日約定した銘柄」と「Broker約定は0件、Broker保有は0件です。」が同居していた。
- 古い daily refs は `submit=STALE_IGNORED` / `reconcile=PASS_WITH_BLOCKED_ITEMS` など、最新 Runtime state と一致していなかった。

## Current Runtime State

現在の 2026-07-02 Runtime state は以下。

- Submit: `BLOCK`
- Submit accepted order count: `0`
- Submit blocked item count: `5`
- Submit invocation source: `launchd`
- Submit common entry: `run_submit_operation`
- Broker order API called: `false`
- Production order submitted: `false`
- Approval manual override detected: `true`
- Approval max notional: `600000`
- Approval max notional source: `manual_override`
- Broker executions count: `0`
- Broker positions count: `0`
- Reconcile: `PASS`
- Broker read-only mock source detected: `false`

## Regeneration

Report 系 artifact のみ再生成した。

Regenerated files:

- `.runtime/operations/reports/2026-07-02/public_report.md`
- `.runtime/operations/reports/2026-07-02/blog_draft.md`
- `.runtime/operations/reports/2026-07-02/safety_report.md`
- `.runtime/operations/reports/2026-07-02/line_payload.json`
- `.runtime/operations/reports/2026-07-02/discord_payload.json`
- `.runtime/operations/daily_report_refs/2026-07-02/daily_report_refs.json`

Regeneration result:

- Daily report status: `REVIEW_REQUIRED`
- Report mode: `REVIEW_REQUIRED_REPORT`
- Notification mode: `REVIEW_REQUIRED_NOTICE`
- Notification status: `NOT_REQUESTED`
- `send_notifications_requested=false`
- `line_send_executed=false`
- `discord_send_executed=false`
- Source of Truth consistency: `false`
- Review reasons shown in report:
  - `source_of_truth:approval_manual_override_detected`
  - `source_of_truth:broker_orders_used_as_execution_fallback_requires_report_label`

## Post-Regeneration Consistency

再生成後の `public_report.md` は、現在の Submit artifact を Source of Truth として以下を表示している。

- `Brokerへ送信済みの注文はありません。`
- `Item単位でBLOCKされた候補は5件です。`
- BLOCK 理由に `manual_override_approval_not_allowed_for_runtime_submit` を表示。
- 通常ブログ形式の Candidate Top50 / Top5 / 本日注文章は生成しない。
- Production注文は無効と表示。

古い表現のうち、少なくとも以下は解消された。

- 「本日約定した銘柄」セクションは消えた。
- Broker約定0件 / Broker保有0件 と約定断定の同居は解消された。
- `manual_override` は Review 理由および各BLOCK候補理由として見える化された。
- `source: mock` は検出されず、`mock_source_detected=false` として daily refs に残っている。

## Mtime Verification

Report 系のみ更新された。

- Report artifacts: `2026-07-02 21:58:42 +0900`
- `submitted_orders.json`: `2026-07-02 21:48:46 +0900`
- `broker_orders/orders.json`: `2026-07-02 15:40:04 +0900`
- `broker_executions/executions.json`: `2026-07-02 15:40:04 +0900`
- `broker_positions/positions.json`: `2026-07-02 15:40:04 +0900`
- `fill_events.json`: `2026-07-02 21:48:55 +0900`
- `reconciliation_result.json`: `2026-07-02 21:48:55 +0900`
- `approval_artifact.json`: `2026-07-02 19:05:00 +0900`
- `demo_ledger/state.json`: `2026-07-02 21:48:55 +0900`

## Notification

通知は送信していない。

- LINE送信なし。
- Discord送信なし。
- `notification_result` は再生成していない。
- payload 生成のみ実施。

## Prohibited State Changes

以下は変更していない。

- submitted_orders
- broker_orders
- broker_executions
- broker_positions
- fill_events
- reconciliation_result
- approval_artifact
- order_plan
- demo_ledger
- notification_result

Production接続、Production注文、実API発注、Submit再実行、Broker再取得、Fill再実行、Reconcile再実行は行っていない。

## Remaining Concern

Report再生成時、既存レンダラは `broker_orders` fallback を表示行に反映し得るため、今回は Report artifact 生成時に current `submitted_orders` を Submit Source of Truth として表示を再構成した。

根本的には、Report writer側で `broker_orders` fallback を「送信済み注文」または「本日約定」に見せない恒久修正を入れるのが望ましい。
