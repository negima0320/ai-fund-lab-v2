# Phase14-E7 Runtime v2 Daily Operation Rehearsal Design

作成日: 2026-07-07

## 最終判定

**PHASE14E7_DAILY_OPERATION_REHEARSAL_DESIGN_COMPLETE**

Phase14-DまででRuntime CoreはDemo BUY/SELL、Current SoT、Ledger、Asset、Reconcile、Report、Auditまで確認済みである。Phase14-E1からE6で、Operation Entry、Safety、Restart / Recovery、Manual Intervention、Business Day Carryover、Markdown/Public Reportを設計・確認した。

本資料では、launchd接続前に人間が毎日実施するRuntime v2日次運用リハーサルを設計する。今回は設計のみであり、コード変更、Broker API Write、Submit、Notification送信、launchd/plist変更は行っていない。

## Current状態

| 項目 | 状態 | 備考 |
| --- | --- | --- |
| Runtime Core | READY | D15/D16でDemo BUY/SELL E2E成立 |
| Current SoT | READY | D21/D22で固定Current Pathとwrite/read-back確認 |
| Ledger / Asset | READY | OrderList + Position + Cash evidence policyで反映 |
| Reconcile / Audit | READY | D15/D22で確認済み |
| Report | READY | Runtime v2 Report Artifact生成済み |
| Markdown/Public Report | READY | E6でRuntime v2-native writer確認 |
| AI Input Pipeline | READY | 日次入力として利用可能 |
| launchd | 未接続 | E7以降で手動リハーサル後に接続判断 |
| Production | 未開始 | Production注文は禁止継続 |

## 基本原則

1. launchd接続前は人間が正規Operation Entry相当の順序で手動実行する。
2. Currentは固定Pathのみを読む。
3. phase番号配下artifact、`.runtime/demo/...`、Report、Blog、Audit、Notification PayloadからCurrentを復元しない。
4. Submit sourceは `.runtime/pending_order_plan/pending_order_plan.json` のみ。
5. Submitは原則disabledで開始し、Demo Submit有効化条件を満たす日だけ明示的に許可する。
6. Production注文、本番Broker API Write、実資金運用は禁止継続。
7. Notificationはpayload-onlyを原則とし、実送信しない。
8. `REVIEW_REQUIRED` / `BLOCKED` / `HALT` は人間確認なしに解除しない。
9. 不明なら `REVIEW_REQUIRED`、危険なら `HALT`。
10. 日次リハーサルscriptやPhase14検証scriptを正規entryへ昇格しない。

## Daily Operation Rehearsal Flow

標準の日次順序:

```text
Morning
  -> Business Day / Carryover Check
  -> Market Refresh
  -> Feature Refresh
  -> AI Inference
  -> Current SoT Read
  -> Broker ReadOnly
  -> Safety Precheck
  -> Reconcile Before Planning
  -> Planning
  -> Pending Promotion
  -> Approval
  -> Safety Pre-submit Check
  -> Runtime Operation
  -> Submit Preflight
  -> Demo Submit if explicitly enabled
  -> Broker ReadOnly Status Sync
  -> Ledger Reflection
  -> Asset Reflection
  -> Reconcile After Reflection
  -> Runtime Report
  -> Markdown/Public Report
  -> Notification Payload only
  -> Audit
  -> Human End-of-day Review
```

### 1. Morning / Business Day Check

目的:

- 対象日が営業日か確認する。
- 前営業日からのPending、Open Order、Review状態を確認する。
- Current固定Pathの存在と鮮度を確認する。

読むもの:

- `.runtime/runtime_state/current_state.json`
- `.runtime/persistent_ledger/state.json`
- `.runtime/persistent_ledger/*.jsonl`
- `.runtime/pending_order_plan/pending_order_plan.json`
- business calendar

停止条件:

- Calendar不明: `BLOCKED` または `REVIEW_REQUIRED`
- `REVIEW_REQUIRED`残存: Manual Reviewへ
- `BLOCKED`残存: blocking reason解消まで停止
- `HALT`残存: emergency reviewのみ
- `POST_SEND_UNKNOWN`残存: Broker ReadOnly確認とManual Reviewへ

### 2. Market Refresh

目的:

- 当日市場データを更新する。

許可:

- Read / Refresh系処理。
- Refresh結果のHistory / Evidence保存。

停止条件:

- market data stale。
- data source failure。
- business date mismatch。

停止先:

- `REVIEW_REQUIRED` または `BLOCKED`

### 3. Feature Refresh

目的:

- AI inference用featureを更新する。

停止条件:

- Feature欠損。
- feature date mismatch。
- stale input。
- future information疑い。

停止先:

- `REVIEW_REQUIRED` または `BLOCKED`

### 4. AI Inference

目的:

- AI判断結果をPlanning入力として生成する。

Runtime原則:

- RuntimeはAI判断ロジックを持たない。
- Runtimeは5銘柄固定制御を持たない。
- AI結果はPlanning inputでありSubmit authorityではない。

停止条件:

- inference artifact欠損。
- artifact hash不明。
- business date mismatch。
- Safety上のReview flag。

### 5. Current SoT Read

目的:

- Planning前にCurrent Asset / Pending / Runtime Stateを固定Pathから読む。

Canonical Current:

```text
.runtime/persistent_ledger/state.json
.runtime/persistent_ledger/orders.jsonl
.runtime/persistent_ledger/executions.jsonl
.runtime/persistent_ledger/positions.jsonl
.runtime/persistent_ledger/cash.jsonl
.runtime/persistent_ledger/events.jsonl
.runtime/pending_order_plan/pending_order_plan.json
.runtime/runtime_state/current_state.json
.runtime/notification_delivery/delivery_ledger.jsonl
```

禁止:

- `.runtime/phase14d*/...` をCurrent扱いすること。
- `.runtime/demo/...` をCurrent扱いすること。
- Report / Blog / AuditからCurrentを復元すること。

### 6. Broker ReadOnly

目的:

- BrokerをSource of Truthとしてcash、buying power、positions、orders、executions相当の状態を確認する。

許可:

- Demo Broker ReadOnly。
- 既存注文のstatus sync。
- Position / Cash / Buying Power取得。

禁止:

- Broker API Write。
- Submit。
- Cancel API。
- Modify API。

停止条件:

- ReadOnly取得失敗。
- Broker状態不明。
- Position / Cash drift。
- Order status unknown。

停止先:

- `REVIEW_REQUIRED`、重大なら `HALT`

### 7. Safety Precheck

目的:

- Planning前にCurrent / Broker / Pending / Runtime Stateが運用継続可能か確認する。

Runtime動作:

- `ALLOW`: Planningへ進む。
- `REVIEW_REQUIRED`: 停止。
- `BLOCK`: `BLOCKED`停止。
- `EMERGENCY_STOP`: `HALT`停止。

RuntimeはSafety判断を再実装しない。

### 8. Reconcile Before Planning

目的:

- Planning前にCurrent SoTとBroker evidenceの整合を確認する。

停止条件:

- BrokerOrderのみからAssetを作る必要が出る状態。
- Execution / Position / Cash evidence不足。
- Current / Broker drift未分類。

### 9. Planning

目的:

- AI inference、Current SoT、Safety contextからOrder Plan候補を作る。

注意:

- Planning artifactはSubmit sourceではない。
- Planning結果から直接Submitしない。
- PlanningがReview flagを出す場合はApprovalへ進めず停止する。

### 10. Pending Promotion

目的:

- Planning結果のうち、Submit候補をCurrent Pendingへ昇格する。

Contract:

- Submit sourceは `.runtime/pending_order_plan/pending_order_plan.json` のみ。
- 既存 `CONSUMED` Pendingを再Submitしない。
- stale Pendingは `EXPIRED` または `REVIEW_REQUIRED`。

### 11. Approval

目的:

- 人間がPendingを確認し、Approval artifactとPending hashを紐付ける。

必須確認:

- 対象銘柄。
- side。
- quantity。
- estimated amount。
- order type。
- max order amount。
- BUYならcash / buying power。
- SELLならposition quantity / available quantity。
- approval hashとpending plan hash。

ApprovalなしではSubmit不可。

### 12. Safety Pre-submit Check

目的:

- Submit直前にPending / Approval / Duplicate / Environment / Demo-only / Position / Cashを再確認する。

Demo Submitがdisabledならここで停止してReportへ進む。

Submit-enabledでも以下を満たさなければ停止:

- Pending state `APPROVED`。
- Approval guard PASS。
- Duplicate guard PASS。
- Demo-only guard PASS。
- Production endpoint block PASS。
- BUY/SELL数量guard PASS。
- max order amount guard PASS。
- Safety `ALLOW`。

### 13. Runtime Operation / Submit Preflight

目的:

- Runtime v2 pure submit pathで、実Submit直前までのguardを確認する。

通常リハーサル:

- `--submit-enabled false`
- `--preflight-only`
- Notification `payload-only`

Demo Submitを行う日は、別途Demo Submit有効化条件を満たした上で1件ずつ実施する。

### 14. Demo Submit if Explicitly Enabled

Demo Submitを許可する条件:

1. 当日リハーサルでCurrent / Broker ReadOnly / Safety / ReconcileがPASS。
2. Pendingが1件のみ、または `--max-orders` 以下。
3. Approval guard PASS。
4. Duplicate guard PASS。
5. Demo-only guard PASS。
6. Production endpoint / production credentialに到達しない。
7. BUYなら小額・最小単位。
8. SELLならposition quantityおよびavailable quantity以下。
9. `POST_SEND_UNKNOWN`時に自動再送しない運用者確認済み。
10. 失敗時に追加Submitしない。

禁止:

- Production注文。
- 本番Broker API Write。
- 複数注文の無計画Submit。
- `CONSUMED` Pending再Submit。
- `POST_SEND_UNKNOWN`からの自動再Submit。

### 15. Broker ReadOnly Status Sync

目的:

- Submit後または既存注文について、Broker ReadOnlyで状態を確認する。

分類:

- filled。
- partial filled。
- unfilled / monitoring。
- canceled。
- expired。
- unknown。

unknownは `REVIEW_REQUIRED`。

### 16. Ledger / Asset Reflection

目的:

- Execution-equivalent evidenceをLedger / Assetへ反映する。

Evidence policy:

- `CLMOrderListDetail`はoptional。
- OrderList-derived fillはPosition / Cash evidenceとセットの場合のみExecution-equivalent evidence。
- BrokerOrder単体からAssetを作らない。
- Asset Current writerはAsset Runtimeのみ。
- Ledger JSONL writerはLedger Runtimeのみ。

### 17. Reconcile After Reflection

目的:

- Ledger / Asset / Broker evidenceの整合を確認する。

PASS条件:

- Position / Cash / Buying PowerがBroker evidenceと整合。
- Pending terminal stateが適切。
- Duplicate / stale / unknownがない。

不整合は `REVIEW_REQUIRED` または `BLOCKED`。

### 18. Report / Markdown / Public Report

目的:

- Runtime v2 Report Artifactと人間向けMarkdown/Public Reportを生成する。

出力:

- `reports/runtime_v2/YYYY-MM-DD/runtime_report.json`
- `reports/runtime_v2/YYYY-MM-DD/runtime_report.md`
- `reports/public/runtime_v2/YYYY-MM-DD/public_report.md`
- `reports/public/runtime_v2/latest.md`

禁止:

- Phase9 writerを呼ばない。
- Phase9 daily runtimeを呼ばない。
- Public Reportにsecret / raw response / broker internal idを出さない。
- ReportをSubmit sourceにしない。

### 19. Notification Payload / Audit

目的:

- 通知payloadを生成し、Auditを残す。

初期方針:

- Notificationはpayload-only。
- 実送信しない。
- Delivery Send / retryは行わない。

Audit確認:

- Submit有無。
- Broker API Write有無。
- Production endpoint未到達。
- Current fixed path維持。
- Phase9未使用。
- `REVIEW_REQUIRED` / `BLOCKED` / `HALT`有無。

## Runtime State遷移

標準成功系:

```text
IDLE
  -> MARKET_DATA_READY
  -> FEATURE_READY
  -> CURRENT_STATE_LOADED
  -> AI_INFERENCE_DONE
  -> DAILY_PLAN_CREATED
  -> PENDING_PROMOTED
  -> APPROVAL_PENDING
  -> APPROVED
  -> SUBMITTING or PRE_SUBMIT_CHECKED
  -> SUBMITTED or SUBMIT_SKIPPED
  -> MONITORING_FILL
  -> LEDGER_UPDATED
  -> RECONCILED
  -> REPORT_READY
  -> AUDIT_READY
  -> IDLE
```

Submit-disabledリハーサル:

```text
APPROVED
  -> PRE_SUBMIT_CHECKED
  -> SUBMIT_SKIPPED
  -> Broker ReadOnly / Reconcile / Report / Audit
```

停止系:

| State / Result | 停止先 | Exit code設計 | 人間対応 |
| --- | --- | --- | --- |
| Safety `REVIEW_REQUIRED` | `REVIEW_REQUIRED` | 20 | Review Event確認 |
| Safety `BLOCK` | `BLOCKED` | 10 | blocking reason解消 |
| Safety `EMERGENCY_STOP` | `HALT` | 30 | emergency review |
| Broker ReadOnly failure | `REVIEW_REQUIRED` | 50 | Broker状態確認 |
| Submit guard failure | `BLOCKED` or `REVIEW_REQUIRED` | 60 | guard原因確認 |
| `POST_SEND_UNKNOWN` | `REVIEW_REQUIRED` | 20 | Broker ReadOnly確認、自動再送禁止 |
| Reconcile mismatch | `REVIEW_REQUIRED` or `BLOCKED` | 20 / 10 | evidence確認 |
| unexpected error | `HALT`相当 | 70 | Audit確認 |

## 人間確認ポイント

| 確認ポイント | 確認内容 | 進行条件 |
| --- | --- | --- |
| Current SoT | cash、buying power、positions、runtime state、pending state | stale / unknownなし |
| Broker ReadOnly | orders、positions、cash、buying power | BrokerとCurrentの差分が分類済み |
| Planning | AI input、候補、数量、金額、side | RuntimeがAI判断を持たないこと |
| Approval | pending item、hash、expiry、数量guard | Approval PASS |
| Safety | decision、reason、allowed/blocked actions | `ALLOW` |
| Submit Preflight | pending-only、duplicate、environment、demo-only | Submit-disabledなら停止、enabledなら明示確認 |
| Ledger / Asset | evidence policy、writer、Current更新 | BrokerOrder単体でAssetを作っていない |
| Reconcile | findings、drift、review flag | PASSまたはReview分類済み |
| Report | Runtime Report / Markdown / Public Report | secret/raw/internal idなし |
| Audit | 禁止事項、state、exit code | PASSまたは停止理由明記 |

## Daily Checklist

### Start-of-day

- [ ] business date / calendar確認。
- [ ] 前回Runtime state確認。
- [ ] `REVIEW_REQUIRED` / `BLOCKED` / `HALT`残存確認。
- [ ] fixed Current Path存在確認。
- [ ] Pending state確認。
- [ ] Broker ReadOnly可能性確認。

### Pre-planning

- [ ] Market Refresh完了。
- [ ] Feature Refresh完了。
- [ ] AI Inference完了。
- [ ] Current SoT read完了。
- [ ] Broker ReadOnly確認。
- [ ] Safety Precheck `ALLOW`。
- [ ] Reconcile Before Planning PASS。

### Planning / Approval

- [ ] Planning artifact確認。
- [ ] Pending promotion確認。
- [ ] Approval必要項目確認。
- [ ] Approval hash一致確認。
- [ ] BUY cash / buying power guard確認。
- [ ] SELL quantity / available quantity guard確認。

### Runtime / Submit Preflight

- [ ] submit-enabledが意図通り。
- [ ] Pending-only submit guard PASS。
- [ ] duplicate guard PASS。
- [ ] demo-only guard PASS。
- [ ] Production endpoint block PASS。
- [ ] `POST_SEND_UNKNOWN`自動再送禁止確認。

### End-of-run

- [ ] Broker ReadOnly status sync完了。
- [ ] Ledger / Asset reflection確認。
- [ ] Reconcile PASSまたはReview分類済み。
- [ ] Runtime Report生成。
- [ ] Markdown/Public Report生成。
- [ ] Notification payload-only確認。
- [ ] Audit PASSまたは停止理由明記。
- [ ] 翌営業日carryover対象確認。

## Failure時Runbook

| Failure | Runtime State | 許可 | 禁止 |
| --- | --- | --- | --- |
| Current missing / stale | `REVIEW_REQUIRED` or `BLOCKED` | Current path確認、Report/Audit | Submit |
| Broker ReadOnly failure | `REVIEW_REQUIRED` | 再ReadOnly、Broker画面確認、Audit | Submit / Cancel / Modify |
| Planning artifact mismatch | `REVIEW_REQUIRED` | 再Planning、AI artifact確認 | Pending直接Submit |
| Approval mismatch | `REVIEW_REQUIRED` | Approval再作成、hash確認 | Submit |
| Duplicate guard failure | `BLOCKED` | orders/events確認 | Submit |
| SELL quantity over position | `BLOCKED` | Position再取得、Manual Review | SELL Submit |
| POST_SEND_UNKNOWN | `REVIEW_REQUIRED` | Broker ReadOnly確認 | 自動再Submit |
| Broker status unknown | `REVIEW_REQUIRED` | Broker ReadOnly再取得、Manual Review | Asset反映 |
| Position / Cash drift | `REVIEW_REQUIRED` or `HALT` | Reconcile、Broker evidence確認 | BrokerOrder単体Asset反映 |
| Report redaction failure | `REVIEW_REQUIRED` | Public Report再生成、Audit | Public公開 |
| Safety emergency | `HALT` | emergency review | 自動復帰、Submit、Notification Send |

## launchd接続前チェック

launchdへ進む前に必要:

1. 正規CLI entry実装。
2. Safety Integration接続。
3. Restart / Recovery Matrixの実装反映。
4. Manual Intervention Runbookの運用確認。
5. Business Day / Carryover判定の運用確認。
6. Markdown/Public Report生成の手動日次運用確認。
7. Notificationはpayload-onlyで安定。
8. `REVIEW_REQUIRED` / `BLOCKED` / `HALT`時のexit code確認。
9. Submit-disabled日次リハーサルが連続PASS。
10. Demo Submit-enabled日は明示承認付きで1件ずつ安全に実施。

## Demo Submitを有効化する条件

通常の日次リハーサルはsubmit-disabledで行う。

Demo Submitを有効化できるのは以下を全て満たす場合のみ:

- Demo環境である。
- Production endpoint / production credentialへ到達しない。
- Broker ReadOnlyがPASS。
- Current / Broker / Reconcileが整合。
- Safetyが`ALLOW`。
- PendingはAPPROVED。
- Approval hash一致。
- Duplicate guard PASS。
- BUY/SELL guard PASS。
- `--max-orders`以内。
- 操作者が当日のSubmitを明示承認。
- 失敗時に追加Submitしない。
- Notificationはpayload-only。

## 1週間連続運用Acceptance

launchd接続前に、少なくとも5営業日相当の手動リハーサルを行う。

Acceptance:

- 5営業日連続でStart-of-day checklistを完了。
- Current fixed pathのみを使用。
- phase artifact / mode-rooted Current未使用。
- Broker ReadOnlyを毎日確認。
- Safety precheckを毎日確認。
- Reconcile Before Planningを毎日確認。
- Runtime Report / Markdown / Public Reportを毎日生成。
- Notificationはpayload-only。
- Auditを毎日生成。
- `REVIEW_REQUIRED` / `BLOCKED` が発生した場合、Runbook通りに停止し、解除なしにSubmitしない。
- Demo Submitを行う場合は1日1シナリオ単位で明示承認し、結果をBroker ReadOnlyで確認。
- Production注文、本番Broker API Write、実資金運用なし。

成功分類:

- `DAILY_REHEARSAL_PASS`: submit-disabledで日次一連PASS。
- `DAILY_REHEARSAL_DEMO_SUBMIT_PASS`: 明示承認付きDemo Submitを含めPASS。
- `DAILY_REHEARSAL_REVIEW_REQUIRED`: Review停止したが安全に止まった。
- `DAILY_REHEARSAL_BLOCKED`: Block条件で安全停止。
- `DAILY_REHEARSAL_HALT`: emergency停止。launchd移行不可。

## launchdへ移行する条件

launchd接続へ進める条件:

1. 1週間連続運用AcceptanceがPASS。
2. 正規CLI entryが実装済み。
3. submit-disabled launchd dry-run設計が完了。
4. Safety resultとexit codeが接続済み。
5. Restart / Recovery Matrixが実装に反映済み。
6. Business Day判定とCarryoverが実装に反映済み。
7. Manual Review解除がlaunchdで自動化されない。
8. Notificationはpayload-onlyで開始する。
9. launchd初期運用ではSubmit disabledをdefaultにする。
10. Productionは禁止継続。

## Phase14-E8以降への引き継ぎ

次フェーズ候補:

- Phase14-E8: Runtime v2正規CLI Entry軽量実装。
- Phase14-E9: Submit-disabled Manual Daily Rehearsal実行。
- Phase14-E10: 5営業日連続Daily Rehearsal。
- Phase14-E11: launchd demo dry-run設計。
- Phase14-E12: launchd demo dry-run実装。

## Acceptance Criteria

| Criteria | 判定 |
| --- | --- |
| 日次運用フローが整理されている | PASS |
| 人間確認ポイントが定義されている | PASS |
| Runtime Stateが整理されている | PASS |
| launchd前条件が整理されている | PASS |
| Demo Submitを有効化する条件が整理されている | PASS |
| Daily Checklistが定義されている | PASS |
| Failure時Runbookが定義されている | PASS |
| 1週間連続運用Acceptanceが定義されている | PASS |
| launchdへ移行する条件が定義されている | PASS |
| コード変更なし | PASS |
| Submitなし | PASS |
| Broker API Writeなし | PASS |
| launchd/plist変更なし | PASS |

## Final Decision

PHASE14E7_DAILY_OPERATION_REHEARSAL_DESIGN_COMPLETE
