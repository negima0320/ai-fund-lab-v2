# Phase14-E4 Manual Intervention / External Broker Action Runbook

作成日: 2026-07-07

## 最終判定

**PHASE14E4_MANUAL_INTERVENTION_RUNBOOK_COMPLETE**

Phase14-D7では、Broker画面で人手取消された9432 BUY注文をRuntime v2がBroker ReadOnly同期で検知し、Pendingを`CONSUMED`、Asset変化なし、Reconcile PASSとして扱えた。E4では、この経験を一般化し、手動介入・Broker外部操作・Review解除・Current SoT補正をRuntime v2運用Runbookとして定義する。

今回は設計のみであり、コード変更、Broker API呼び出し、Submit、Cancel API呼び出し、Notification送信、launchd/plist変更、Current SoT追加writeは行っていない。

## 基本原則

1. BrokerをSource of Truthとする。
2. RuntimeはBroker状態を上書きしない。
3. 外部操作はBroker ReadOnly evidenceで確認してから取り込む。
4. 人間操作はReview Eventとして記録する。
5. 手動操作から自動Submitへ直行しない。
6. 不明なら`REVIEW_REQUIRED`。
7. 危険なら`HALT`。
8. Current補正はLedger / Asset writerのみが行う。
9. Report / Audit / Blog / Notification PayloadはCurrentを書かない。
10. BrokerOrder単体からAssetを作らない。

## Manual Intervention分類

| Type | 説明 | Runtime分類 | Broker ReadOnly必須 | Manual approval必須 | Current反映 |
| --- | --- | --- | --- | --- | --- |
| `broker_manual_cancel` | Broker画面で注文取消 | External Broker Action | YES | 状況次第。未約定取消のみならreview記録で可 | 注文状態/Pending終端。Asset原則変化なし |
| `broker_manual_buy` | Runtime外で手動買付 | External Broker Action | YES | YES | Execution / Position / Cash evidence後にLedger/Asset |
| `broker_manual_sell` | Runtime外で手動売却 | External Broker Action | YES | YES | Execution / Position / Cash evidence後にLedger/Asset |
| `broker_manual_deposit_withdrawal` | Broker口座への入出金 | External Broker Action | YES | YES | Cash evidence後にLedger/Asset |
| `broker_order_expired` | Broker側で注文失効 | External Broker Action | YES | NOまたはreview | Order status/Pending終端。Assetは約定なしなら変化なし |
| `broker_correction_or_modify` | Broker側訂正・条件変更 | External Broker Action | YES | YES | 注文状態と必要ならledger event |
| `runtime_stopped_broker_changed` | Runtime停止中にBroker状態変化 | Recovery / Review | YES | YES | Reconcile後に反映 |
| `review_required_manual_review` | REVIEW_REQUIREDの人間確認 | Manual Review | reason次第 | YES | 承認済みRecovery actionのみ |
| `blocked_clearance` | BLOCKED解除 | Manual Review | reason次第 | YES if unresolved/safety-related | 原則Current補正なし。preflight再実行 |
| `halt_unlock` | HALT解除 | Emergency Manual Review | YES | YES | Recovery record / Safety OK後のみ |
| `current_sot_correction` | Current SoT補正 | Manual Migration / Correction | YESまたはmigration evidence | YES | Ledger/Asset writerのみ |
| `position_drift_correction` | Position Drift補正 | Reconcile / Recovery | YES | YES | Position/Cash evidence後にLedger/Asset |

## External Broker Action分類

| Action | Evidence | Runtime handling | Asset handling | Next state |
| --- | --- | --- | --- | --- |
| 手動取消 | Broker order listで取消済み、executed_quantity=0、remaining_quantity=0 | Pendingを終端化。注文event記録 | 変化なし | `RECONCILED` or `REPORT_READY` |
| 手動売却 | Broker order/execution/position/cash | Runtime外SELLとしてreview event記録 | Position減少、cash更新、PnL可能なら記録 | `REVIEW_REQUIRED`後、承認で`LEDGER_UPDATED` |
| 手動購入 | Broker order/execution/position/cash | Runtime外BUYとしてreview event記録 | Position増加、cash更新 | `REVIEW_REQUIRED`後、承認で`LEDGER_UPDATED` |
| 手動入金 | Broker cash/buying power | external cash eventとして記録 | cash増加 | `LEDGER_UPDATED` |
| 手動出金 | Broker cash/buying power | external cash eventとして記録 | cash減少 | `LEDGER_UPDATED` or `REVIEW_REQUIRED` |
| Broker側失効 | Broker order list | Pending終端、order event | 約定なしなら変化なし | `RECONCILED` |
| Broker側訂正 | Broker order list/detail可能ならdetail | order modification evidenceとしてReview | 状況次第。AssetはExecution/Position/Cashまで待つ | `REVIEW_REQUIRED` |
| Broker側約定遅延 | Order filledだがPosition/Cash未反映 | `MONITORING_FILL`継続または`REVIEW_REQUIRED` | Asset反映保留 | `MONITORING_FILL` |

## Runtime State別Runbook

| Runtime State | Manual / External action handling | Required evidence | Allowed actions | Prohibited actions |
| --- | --- | --- | --- | --- |
| `REVIEW_REQUIRED` | reasonを特定し、Broker ReadOnly / Safety / Reconcile / manual decisionで解除可否を判断 | review event, broker evidence, current state, safety result | ReadOnly, Report, Audit, Review approval | Submit, auto-clear |
| `BLOCKED` | blocking reasonを解消し、preflightを再実行 | blocked event, config/current/pending/approval/safety evidence | preflight, report, audit | unblockなしのSubmit |
| `HALT` | manual emergency reviewのみ。Safety OKとBroker再照合が必須 | halt event, safety report, broker evidence, audit | ReadOnly, report, audit, manual unlock request/apply | Submit, Cancel, Modify, auto recovery |
| `POST_SEND_UNKNOWN` | Broker ReadOnlyで注文有無を確認。自動再送禁止 | submit attempt, orders ledger, broker order status | ReadOnly, review, report, audit | re-submit, auto cancel/modify |
| `MONITORING_FILL` | Broker状態変化をReadOnly同期。約定遅延は監視継続またはreview | broker orders/executions/positions/cash | ReadOnly, reflection dedup, reconcile | submit retry |
| `SUBMITTED` | 送信済み注文の外部取消/失効/約定をReadOnlyで確認 | orders ledger, broker orders | ReadOnly, fill monitoring, pending terminal update | submit retry |
| `RECONCILED` | 外部操作が後から見つかれば新規Review Eventを開く | reconcile result, broker evidence | report/audit regeneration, review event | Current direct write by report/audit |

## Current SoT反映条件

Current SoTへ反映するには、以下を満たす。

1. Broker ReadOnly evidenceがある。
2. Reconcileを実行し、差分を分類している。
3. Safety checkを実行している。
4. Manual approvalが必要な条件では承認済みである。
5. Ledger writerがappend-only recordを書く。
6. Asset writerがLedger / Position / Cash evidenceから`persistent_ledger/state.json`を再構築する。
7. Report / AuditはCurrentを書かない。

Manual approval必須条件:

- Runtime外の手動BUY/SELL。
- 手動入出金。
- Broker側訂正。
- Position Drift補正。
- HALT解除。
- Safety由来`REVIEW_REQUIRED` / `BLOCKED`解除。
- Broker evidenceが部分的または矛盾している場合。

Manual approval不要または軽量reviewでよい条件:

- D7型の未約定手動取消で、Broker order list上で取消済み、executed_quantity=0、remaining_quantity=0、Position/Cash変化なし、Reconcile PASSの場合。
- Broker側失効で約定なし、Asset変化なし、Reconcile PASSの場合。

## Review Event schema案

```json
{
  "schema_version": "runtime_v2_review_event_v1",
  "event_id": "review_...",
  "business_date": "YYYY-MM-DD",
  "runtime_state": "REVIEW_REQUIRED",
  "action_type": "broker_manual_cancel",
  "operator": "manual_operator_or_system_detected",
  "reason": "external broker cancellation detected",
  "broker_evidence_refs": [],
  "current_sot_before": {
    "state_ref": ".runtime/persistent_ledger/state.json",
    "hash": "..."
  },
  "current_sot_after": {
    "state_ref": ".runtime/persistent_ledger/state.json",
    "hash": "...",
    "required": false
  },
  "approval_required": false,
  "approval_status": "not_required",
  "created_at": "..."
}
```

必須field:

- `event_id`
- `business_date`
- `runtime_state`
- `action_type`
- `operator`
- `reason`
- `broker_evidence_refs`
- `current_sot_before`
- `current_sot_after`
- `approval_required`
- `approval_status`
- `created_at`

## Manual Unlock Policy

### REVIEW_REQUIRED解除条件

- Review Eventが存在する。
- reasonが分類済み。
- Broker ReadOnlyまたはCurrent evidenceで事実確認済み。
- Reconcile結果がPASS、または差分に対するmanual decisionがある。
- Safety resultが`ALLOW`またはmanual-approved equivalent。
- 承認者、承認時刻、理由、証跡が保存されている。
- Submitが必要な場合は新しいpending plan idを使う。

解除後の再開state:

- 操作なしで解消: `RECONCILED` または `REPORT_READY`
- Ledger/Asset反映が必要: `LEDGER_UPDATED` 後に `RECONCILED`
- 新規計画が必要: `IDLE` または `CURRENT_STATE_LOADED`

### BLOCKED解除条件

- blocking reasonが解消済み。
- config/env/current/pending/approval/safety preflightがPASS。
- Safety由来の場合はSafety再評価またはmanual approval。
- Submitが必要な場合はPendingが`APPROVED`でduplicate guard PASS。

解除後の再開state:

- `APPROVED`ならSubmit preflightへ。
- planning系なら `CURRENT_STATE_LOADED` または `DAILY_PLAN_CREATED` へ。

### HALT解除条件

- 自動解除禁止。
- 最新Broker ReadOnly evidenceで再照合。
- SafetyReport / SafetyResultがOKまたはmanual-approved。
- Reconciliation OK、または差分に対するapproved recovery actionがある。
- Unlock request / approval / apply auditが保存されている。
- 解除後もSubmit直前にSafety再評価する。

解除後の再開state:

- 原則 `IDLE` または `CURRENT_STATE_LOADED`。
- 直接`SUBMITTING` / `SUBMITTED`へ戻さない。

## launchd Behavior

launchdは手動解除を自動化しない。

launchdが外部Broker Actionを検知した場合:

1. Runtime stateとCurrent SoTを読む。
2. Broker ReadOnly evidenceがある場合のみ分類する。
3. Review Eventを開く。
4. Reconcile / Report / Audit / Notification Payloadを生成する。
5. Submitへ進まない。
6. Exit codeは状態に応じて `20` / `10` / `30`。

launchdがやってはいけないこと:

- HALT解除。
- REVIEW_REQUIRED解除。
- BLOCKED解除。
- 手動操作の結果だけでSubmit。
- Broker画面操作をRuntime artifactだけで推測。
- Cancel API / Modify API / Submit。

## 禁止事項

- 手動確認なしでHALT解除しない。
- REVIEW_REQUIREDをlaunchdが自動解除しない。
- 手動操作の結果だけでSubmitしない。
- Broker画面操作をRuntime artifactだけで推測しない。
- Report / Blog / AuditをCurrent補正sourceにしない。
- BrokerOrder単体からAssetを作らない。
- POST_SEND_UNKNOWNから自動再送しない。
- Cancel APIをRecoveryの通常手段にしない。
- Currentをphase配下artifactから復元しない。
- 破壊的削除で整合性を戻さない。

## D7からの一般化

D7の外部取消同期は、次の条件を満たしたため軽量reviewでRuntime反映できた。

- Broker order listで対象注文を検出。
- 状態が取消完了。
- executed_quantity=0。
- remaining_quantity=0。
- Position / Cashに変化なし。
- Pendingを`CONSUMED`へ終端化。
- Asset変化なし。
- Reconcile PASS。
- Audit PASS。

この条件を満たさない外部取消、特に部分約定後取消、Position/Cash変化あり、Broker evidence不足、order status unknownは`REVIEW_REQUIRED`へ止める。

## Phase14-E5以降への引き継ぎ

1. **Phase14-E5: Business Day / Carryover Contract**
   - 未約定carry、翌営業日、失効、approval expiryを整理する。

2. **Phase14-E5/E6: Position Drift Classification**
   - drift severity、許容差、manual correction条件を定義する。

3. **Phase14-E6: Runtime v2 CLI Skeleton**
   - Review Event schemaとmanual intervention stateをCLI skeletonへ接続する。

4. **Phase14-E7: launchd Demo Dry-run Design**
   - launchdがReview/HALT/BLOCKEDを自動解除しないことを検証する。

5. **Demo Operation Runbook**
   - Demo Broker固有の約定遅延、9000番台除外、外部取消確認を日次手順化する。

## Acceptance Criteria

| Criteria | 判定 |
| --- | --- |
| Manual Intervention分類が定義されている | PASS |
| External Broker Action分類が定義されている | PASS |
| BrokerをSource of Truthとする方針が明記されている | PASS |
| Runtime State別の手動対応が定義されている | PASS |
| Review Event schemaが定義されている | PASS |
| REVIEW_REQUIRED / BLOCKED / HALT解除条件が定義されている | PASS |
| Broker ReadOnly evidenceなしにCurrentを補正しない | PASS |
| Asset / Ledger writer以外がCurrentを書かない | PASS |
| launchdが手動解除を自動化しない | PASS |
| コード変更していない | PASS |
| Broker API呼び出ししていない | PASS |
| Submitしていない | PASS |
| Cancel APIを呼んでいない | PASS |
| Notification送信していない | PASS |
| launchd/plist変更していない | PASS |

## 結論

Runtime v2は、手動介入やBroker外部操作をBroker ReadOnly evidenceで確認し、Review Eventとして記録し、Reconcile / Safety / Manual approvalを経てLedger / Asset writerだけがCurrentへ反映する。

launchdは手動解除を自動化しない。

したがって最終判定は **PHASE14E4_MANUAL_INTERVENTION_RUNBOOK_COMPLETE** とする。
