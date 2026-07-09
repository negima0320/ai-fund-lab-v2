# Phase14-E10 Runtime v2 Daily Operation Schedule Design

作成日: 2026-07-07

## 最終判定

**PHASE14E10_DAILY_OPERATION_SCHEDULE_COMPLETE**

Phase14-E9でlaunchd登録準備は完了した。ただしE7/E9時点のplistは、08:45にRuntime v2を1回起動する単一Jobである。実運用では、市場データ更新、AI推論、売買判断、注文、約定確認、レポート生成は同じタイミングではない。

本資料では、市場ライフサイクルに合わせたRuntime v2 Daily Scheduleを正式設計する。今回は設計のみであり、コード変更、Broker API Write、Production注文、Notification送信、launchd load/bootstrapは行っていない。

## 基本方針

1. Runtime v2日次運用は4つのlaunchd Jobに分離する。
2. launchdは判断しない。各JobはRuntime v2正規CLIのみを起動する。
3. 旧Phase9 Runtime、旧Runtime entry、Phase9 writer、`run_phase14d*` scriptは使わない。
4. Currentは固定Pathのみを使う。
5. `.runtime/demo/...` やphase artifactをCurrent扱いしない。
6. MorningはAI推論と計画まで。Submitしない。
7. OpenはSubmitのみ。
8. ExecutionはBroker同期と反映のみ。
9. After CloseはMarket / Feature更新のみ。AI推論は翌朝。
10. Notificationは当面payload-onlyを原則とする。

## Daily Schedule Overview

| Session | 推奨時刻 | 主目的 | Submit | 主な出力 |
| --- | --- | --- | --- | --- |
| Morning Session | 08:45 | 寄付き前準備、AI推論、Planning、Approval、Pending生成 | しない | Pending、pre-open report、audit |
| Open Session | 08:58-08:59 | PendingをBrokerへ送信 | Demoのみ明示許可時。Productionは将来 | Submit result、submit audit |
| Execution Session | 09:05-09:10 | 約定確認、Ledger/Asset/Reconcile/Report | しない | Ledger、Asset、Report、Notification Payload、Audit |
| Market Close Session | 15:30以降 | 翌営業日AI入力更新 | しない | J-Quants/Canonical/Feature/Input artifacts |
| Night Session | 原則なし | Maintenanceのみ | しない | maintenance audit |

## Morning Session

推奨時刻:

```text
08:45
```

目的:

- 寄付き前準備。
- 前日からのCarryover確認。
- Current SoTとBroker ReadOnlyの整合確認。
- 当日朝のAI推論。
- Planning、Approval、Pending生成。
- Submit直前で停止。

実施順序:

```text
Broker ReadOnly
  -> Current SoT確認
  -> Business Day
  -> Carryover
  -> Safety
  -> Reconcile
  -> AI inference
  -> Planning
  -> Approval
  -> Pending生成
  -> STOP
```

禁止:

- Submitしない。
- Broker API Writeしない。
- Production注文しない。
- Notification実送信しない。

Runtime State目安:

- `CURRENT_STATE_LOADED`
- `AI_INFERENCE_DONE`
- `DAILY_PLAN_CREATED`
- `PENDING_PROMOTED`
- `APPROVAL_PENDING` または `APPROVED`
- submit-disabledなら `PRE_SUBMIT_CHECKED` / `SUBMIT_SKIPPED` 相当で停止

launchd Job案:

```text
com.aifundlab.runtime_v2.morning
```

CLI案:

```text
python -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation \
  --mode demo \
  --session morning \
  --submit-enabled false \
  --notification-mode payload-only \
  --stop-on-review-required \
  --stop-on-blocked
```

## Open Session

推奨時刻:

```text
08:58-08:59
```

目的:

- Morningで作成・承認されたPendingをBrokerへ送信する。
- Submit専用Jobとし、PlanningやAI推論を行わない。

実施順序:

```text
Pending
  -> Approval再確認
  -> Safety
  -> Demo Submit
     (Productionでは将来Production Submit)
  -> 終了
```

Demo初期方針:

- Phase14-E10時点では設計のみ。
- Demo Submitを行う場合も、`submit-enabled true`はOpen Session専用。
- 1件ずつ、Pending-only、Approval、Duplicate、Demo-only、9000番台BLOCK、max amount guardを必須にする。

Production:

- Production Submitは別Production Acceptanceまで禁止。
- Productionでは同じRuntime flowでBrokerCapabilityのみ切り替える。

Runtime State目安:

- `APPROVED`
- `SUBMITTING`
- `SUBMITTED`
- `POST_SEND_UNKNOWN`なら自動再送せず `REVIEW_REQUIRED`

launchd Job案:

```text
com.aifundlab.runtime_v2.submit
```

CLI案:

```text
python -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation \
  --mode demo \
  --session open_submit \
  --submit-enabled false \
  --notification-mode payload-only \
  --stop-on-review-required \
  --stop-on-blocked
```

補足:

- 初期launchdでは`--submit-enabled false`のdry rehearsalを推奨。
- 実Demo Submitを許可する日は、別Acceptance後にOpen Sessionだけで明示的に`true`へ切り替える。

## Execution Session

推奨時刻:

```text
09:05-09:10
```

目的:

- 寄付き後の注文状態・約定状態を確認する。
- Broker ReadOnly evidenceからExecution Reflection、Ledger、Asset、Reconcile、Report、Auditへ進める。

実施順序:

```text
Broker ReadOnly
  -> Execution Reflection
  -> Ledger
  -> Asset
  -> Reconcile
  -> Runtime Report
  -> Notification Payload
  -> Audit
```

禁止:

- Submitしない。
- Cancel / Modifyしない。
- Broker API Writeしない。
- Notification実送信しない。

Runtime State目安:

- `MONITORING_FILL`
- `LEDGER_UPDATED`
- `RECONCILED`
- `REPORT_READY`

launchd Job案:

```text
com.aifundlab.runtime_v2.execution
```

CLI案:

```text
python -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation \
  --mode demo \
  --session execution \
  --submit-enabled false \
  --notification-mode payload-only \
  --stop-on-review-required \
  --stop-on-blocked
```

## Market Close Session

推奨時刻:

```text
15:30以降
```

目的:

- 翌営業日のAI入力を更新する。
- 市場データとFeature更新を行う。
- AI推論は行わない。

実施順序:

```text
J-Quants取得
  -> Canonical更新
  -> Feature Refresh
  -> Candidate Feature生成
  -> Opportunity Input生成
  -> Position Input生成
  -> Capital Input生成
  -> 終了
```

禁止:

- AI inferenceしない。
- Planningしない。
- Pending生成しない。
- Submitしない。
- Broker API Writeしない。

Runtime State目安:

- `MARKET_DATA_READY`
- `FEATURE_READY`

launchd Job案:

```text
com.aifundlab.runtime_v2.market_refresh
```

CLI案:

```text
python -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation \
  --mode demo \
  --session market_refresh \
  --submit-enabled false \
  --notification-mode payload-only \
  --stop-on-review-required \
  --stop-on-blocked
```

## Night Session

基本なし。

必要な場合のみMaintenanceを行う。

許可:

- disk / artifact inspection。
- log rotation設計。
- report integrity check。
- backup確認。

禁止:

- AI inference。
- Planning。
- Pending生成。
- Submit。
- Broker API Write。
- Production注文。

## Design Rules

| Rule | 内容 |
| --- | --- |
| Morning | AI推論のみ。Planning/Approval/Pendingまで。Submitしない |
| Open | Submitのみ。AI推論やPlanningをしない |
| Execution | Broker同期のみ。Submitしない |
| After Close | Market / Feature更新のみ。AI推論しない |
| AI inference | 翌朝に実施 |
| J-Quants | 15:30以降に取得 |
| Report | Execution後に正式Report。Morningはpre-open report扱い |
| Notification | payload-only。実送信は別Acceptance後 |

## launchd Multi-Job Design

正式運用では以下4つを別Jobとして持つ。

| Job | Label案 | 時刻 | Session |
| --- | --- | --- | --- |
| Morning | `com.aifundlab.runtime_v2.morning` | 08:45 | morning |
| Open Submit | `com.aifundlab.runtime_v2.submit` | 08:58-08:59 | open_submit |
| Execution Sync | `com.aifundlab.runtime_v2.execution` | 09:05-09:10 | execution |
| Market Refresh | `com.aifundlab.runtime_v2.market_refresh` | 15:30以降 | market_refresh |

各JobはRuntime v2正規CLIのみを起動する。

禁止:

- 旧Phase9 RuntimeをJobにしない。
- 旧Runtime entryをJobにしない。
- `run_phase14d*` scriptをJobにしない。
- `reports/*` をCurrent sourceにしない。

## E9単一Jobとの関係

E9の `com.aifundlab.runtime_v2.daily_operation_rehearsal` は、launchd登録準備用の単一rehearsal jobである。

E10以降の正式Daily Scheduleでは、この単一Jobをそのまま本番日次運用に使わない。複数Job設計へ移行する。

移行方針:

1. まずE9単一Jobは登録せず、E10設計を正とする。
2. Runtime v2 CLIへ `--session` 概念を追加する。
3. 4つのplistを生成する。
4. 各plistをsubmit-disabledでdry-run確認する。
5. Morning -> Open -> Execution -> After Closeの順に手動kickstart rehearsalを行う。
6. 全Jobのmanifestとreportを確認してからlaunchd登録へ進む。

## Failure / Stop Policy

| Session | Stop Condition | Stop State | Next Action |
| --- | --- | --- | --- |
| Morning | Current/Broker/Safety/Reconcile不整合 | `REVIEW_REQUIRED` / `BLOCKED` / `HALT` | Open Submitへ進まない |
| Open | Approval mismatch / duplicate / POST_SEND_UNKNOWN | `REVIEW_REQUIRED` | 自動再Submit禁止 |
| Execution | Broker status unknown / reflection mismatch | `REVIEW_REQUIRED` / `BLOCKED` | Report/Auditで停止理由明記 |
| After Close | J-Quants/Feature更新失敗 | `BLOCKED` / `REVIEW_REQUIRED` | 翌朝AI inferenceへ進む前に解消 |

## Future CLI Requirements

E10は設計のみだが、次フェーズでRuntime v2 CLIに以下が必要。

- `--session morning/open_submit/execution/market_refresh`
- session別許可操作のenforcement
- session別manifest
- session別exit code
- session別report/audit
- Open Session以外でSubmitをBLOCK
- Market Close SessionでAI inferenceをBLOCK
- Morning SessionでSubmitをBLOCK

## Acceptance Criteria

| Criteria | 判定 |
| --- | --- |
| Morning/Open/Execution/After Closeを定義 | PASS |
| J-Quantsは15:30以降 | PASS |
| AI推論は朝 | PASS |
| Submitは寄付き直前 | PASS |
| 約定確認は寄付き後 | PASS |
| Market更新とAI推論を分離 | PASS |
| Runtime v2正規CLIのみ使用 | PASS |
| 旧Phase9 Runtimeを使わない | PASS |
| launchdは複数Job設計 | PASS |
| コード変更なし | PASS |
| Broker API Writeなし | PASS |
| Production注文なし | PASS |
| launchd bootstrapなし | PASS |

## Final Decision

PHASE14E10_DAILY_OPERATION_SCHEDULE_COMPLETE
