# Phase14-E2 Runtime v2 Safety Integration Contract

作成日: 2026-07-07

## 最終判定

**PHASE14E2_SAFETY_INTEGRATION_CONTRACT_COMPLETE**

Phase14-E1でRuntime v2 Operation Entry Contractを定義した。E2では、Phase11 Safety LayerをRuntime v2の正規フローへ接続する契約を定義する。

本Contractの中心原則は、RuntimeはSafety判断を実装しない、という点である。Runtime v2はSafety Layerから受け取った結果をRuntime State Machine、Submit guard、Report、Notification Payload、Auditへ反映する制御層に徹する。

今回は設計のみであり、コード変更、Broker API呼び出し、Submit、Notification送信、launchd/plist変更は行っていない。

## 参照前提

Phase11 Safety Layerの既存原則:

- Safety Layerは利益最大化ではなく、致命的事故防止を目的とする。
- 分からない時は止まる。
- BrokerをSource of Truthとして扱う。
- Fail Closed / Default Denyを徹底する。
- Human Reviewを優先する。
- 自動売却、自動復旧、自動再発注、自動retryを行わない。
- Safety結果をAI学習へ使わない。

Phase11 Refined Designの補正:

- 相場下落、market crash、daily lossは原則System Emergencyではない。
- システム事故、発注事故、Broker不整合、重複注文、critical stale、secret/raw response保存疑いをSystem Emergencyとして扱う。
- market stressやbuy opportunityはRuntimeで投資判断せずHuman Reviewへ送る。

E1 Operation Entry前提:

- 正規entryは `python -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation`。
- 初期launchdはpayload-only通知を原則とする。
- submit-enabledでもSafety / Operation GuardがALLOWでなければSubmitしない。
- `REVIEW_REQUIRED`、`BLOCKED`、`HALT` は停止状態として扱う。

## 1. Safety責務

### Safety Layerが行うこと

Safety Layerは、Runtime v2から渡されたCurrent / Pending / Approval / Broker evidence / Runtime contextを評価し、運用可否を分類する。

評価対象:

- Broker / Runtime / Ledger / Pending / Approvalの不整合。
- duplicate order risk。
- position mismatch。
- execution mismatch。
- cash / buying power異常。
- critical stale data。
- Broker ReadOnly失敗または証跡不足。
- raw request / raw response / secret保存疑い。
- manual emergency stop。
- market stress / buy opportunity review / high risk review。

### Runtime v2が行うこと

Runtime v2はSafety結果を受け取り、次の運用制御へ反映する。

- `ALLOW`: 次のRuntime stepへ進む。
- `REVIEW_REQUIRED`: Runtime stateを`REVIEW_REQUIRED`へ止める。
- `BLOCK`: Runtime stateを`BLOCKED`へ止める。
- `EMERGENCY_STOP`: Runtime stateを`HALT`へ止める。

Runtime v2はSafety reasonをReport、Notification Payload、Audit、Review Queueへ渡すが、Safetyの中身を再計算しない。

### Runtime v2がやらないこと

Runtimeへ以下を持ち込まない。

- AI判断。
- スコアリング。
- 銘柄選定。
- Opportunity順位付け。
- Position Management判断。
- Capital Allocationの収益判断。
- Safety guardロジックの再実装。
- market stressを理由にRuntime側で独自に候補を破棄すること。
- Safety結果をAI学習データへ渡すこと。

## 2. Safety接続ポイント

| 接続ポイント | Safety Input | 評価内容 | Runtime動作 |
| --- | --- | --- | --- |
| Planning前 | Current SoT、runtime mode、business date、cash、buying power、positions、open events | Current欠損、stale、Broker/ledger不明、emergency lock | `ALLOW`ならPlanningへ。その他は停止 |
| Planning後 | daily plan、order plan candidate、current asset、cash、positions、Safety context | 過大注文、cash/buying power逸脱、position/candidate不整合、market stress review | `ALLOW`ならPending promotion候補へ。review/blockはPending promotion前に停止 |
| Approval前 | pending candidate、approval request、current asset、risk flags | 承認対象がSafety上許容か、manual review必要か | `ALLOW`ならApproval linkageへ。review/blockは承認前停止 |
| Submit前 | `pending_order_plan/pending_order_plan.json`、approval linkage、orders ledger、runtime mode、broker adapter capability | pending-only、approval、duplicate、POST_SEND_UNKNOWN、environment、system emergency | `ALLOW`のみSubmit可。その他はSubmit禁止 |
| Broker ReadOnly後 | broker orders、executions、positions、cash、buying power、submitted refs | Broker divergence、position/cash mismatch、order unknown、critical stale | `ALLOW`ならReflection/Reconcileへ。review/haltは停止 |
| Reconcile後 | reconcile findings、ledger state、broker evidence、pending consume state | drift severity、repair/manual review要否 | findingsなしならReportへ。review/block/haltは停止またはReviewへ |
| Manual Review | review decision、manual evidence、broker snapshot、safety report、audit | 解除条件、人間承認、復旧可否 | manual approvedなら該当stateへ復帰。自動解除は禁止 |

## 3. Safety Result分類

Runtime v2へ返す最低分類:

| Safety decision | 意味 | Runtime State | Exit code | Submit | Notification |
| --- | --- | --- | --- | --- | --- |
| `ALLOW` | 運用継続可 | 次stateへ進む | 0 if final success | 条件付き可 | payload生成可 |
| `REVIEW_REQUIRED` | 人間確認が必要 | `REVIEW_REQUIRED` | 20 | 禁止 | payload-only可 |
| `BLOCK` | 条件未充足または禁止 | `BLOCKED` | 10 | 禁止 | payload-only可 |
| `EMERGENCY_STOP` | system emergency | `HALT` | 30 | 禁止 | payload-only可 |

補足:

- `WARNING`、`MARKET_STRESS`、`BUY_REVIEW_REQUIRED`、`BUY_OPPORTUNITY_REVIEW`、`SELL_REVIEW_REQUIRED`、`HIGH_RISK_REVIEW` などのrefined classificationは、互換decisionとして `REVIEW_REQUIRED` または `ALLOW with warning` に正規化してRuntimeへ渡す。
- `SYSTEM_EMERGENCY_STOP` は `EMERGENCY_STOP` へ正規化する。
- Runtimeはこれらのrefined classificationを投資判断として使わず、Report / Review Queueの説明材料として扱う。

## 4. Runtime State対応

```text
Safety ALLOW
  -> Runtime continues

Safety REVIEW_REQUIRED
  -> Runtime state REVIEW_REQUIRED
  -> Exit code 20
  -> Submit prohibited
  -> Broker ReadOnly / Report / Audit / Manual Review only

Safety BLOCK
  -> Runtime state BLOCKED
  -> Exit code 10
  -> Submit prohibited
  -> reason must be recorded

Safety EMERGENCY_STOP
  -> Runtime state HALT
  -> Exit code 30
  -> Submit / Cancel / Modify / Notification Send prohibited
  -> Manual Review only
```

## 5. launchd運用時の扱い

launchdはSafety結果を自動判断で上書きしない。

| Safety result | launchd behavior | Exit code | Artifact |
| --- | --- | --- | --- |
| `ALLOW` | 次stepへ進む | final resultによる | run manifest / report |
| `REVIEW_REQUIRED` | 自動停止。次回自動Submitへ進まない | 20 | review event、report、notification payload |
| `BLOCK` | 自動停止。条件解消まで進まない | 10 | blocked event、report、notification payload |
| `EMERGENCY_STOP` | 自動停止。manual recoveryのみ | 30 | halt event、safety report、audit |

launchd初期運用ではNotificationはpayload-onlyを原則とする。Safety停止時も実送信はしない。Notification Sendを使う場合は、別途Notification Send / Ack ContractとDelivery Ledger Acceptanceが必要である。

## 6. Safety Input

Runtime v2からSafety Layerへ渡す情報:

| Field | 内容 |
| --- | --- |
| `runtime_mode` | `demo` / `simulation` / `production` |
| `business_date` | 対象business date |
| `operation_stage` | `pre_planning` / `post_planning` / `pre_approval` / `pre_submit` / `post_broker_readonly` / `post_reconcile` / `manual_review` |
| `current_state` | fixed Current pathから読んだAsset state |
| `cash` | Current SoTまたはBroker evidence由来のcash |
| `buying_power` | Current SoTまたはBroker evidence由来のbuying power |
| `positions` | Current positions |
| `pending_plan` | `.runtime/pending_order_plan/pending_order_plan.json` |
| `approval` | approval linkage / hash / expiry / status |
| `submitted_orders` | `persistent_ledger/orders.jsonl` の関連order |
| `broker_orders` | Broker ReadOnly evidence |
| `broker_executions` | Broker ReadOnly evidence |
| `broker_positions` | Broker ReadOnly evidence |
| `broker_cash` | Broker ReadOnly evidence |
| `reconcile_findings` | Reconcile result |
| `runtime_state` | `runtime_state/current_state.json` |
| `operation_guard_context` | business day、run lock、duplicate guard、environment guard |

禁止:

- secret。
- raw request / raw response。
- plaintext broker ids。
- Safety resultをAI学習用feature/labelとして渡すこと。

## 7. Safety Output

Runtime v2へ返すSafety Result:

| Field | 必須 | 内容 |
| --- | --- | --- |
| `decision` | YES | `ALLOW` / `REVIEW_REQUIRED` / `BLOCK` / `EMERGENCY_STOP` |
| `severity` | YES | `info` / `warning` / `review` / `block` / `emergency` |
| `reason_code` | YES | machine-readable reason |
| `review_message` | YES if review/block/emergency | 人間確認用説明 |
| `stop_reason` | YES if block/emergency | Runtime停止理由 |
| `allowed_actions` | YES | 次に許可される操作 |
| `blocked_actions` | YES | 禁止操作 |
| `evidence_refs` | YES | Current / Broker / Reconcile / Audit evidence references |
| `refined_classification` | NO | `MARKET_STRESS`等の詳細分類 |
| `requires_manual_approval` | YES | manual approval要否 |
| `created_at` | YES | 判定時刻 |

## 8. Safety Runtime Interface

設計上のinterface:

```text
SafetyRuntime.evaluate(request: SafetyRequest) -> SafetyResult
```

`SafetyRequest`の概念schema:

```json
{
  "schema_version": "runtime_v2_safety_request_v1",
  "runtime_mode": "demo",
  "business_date": "YYYY-MM-DD",
  "operation_stage": "pre_submit",
  "current_state_ref": ".runtime/persistent_ledger/state.json",
  "pending_plan_ref": ".runtime/pending_order_plan/pending_order_plan.json",
  "runtime_state_ref": ".runtime/runtime_state/current_state.json",
  "cash": 0,
  "buying_power": 0,
  "positions": [],
  "approval": {
    "status": "APPROVED",
    "hash_match": true,
    "expires_at": "..."
  },
  "broker_evidence_refs": [],
  "reconcile_findings": [],
  "operation_guard_context": {
    "business_day_ok": true,
    "duplicate_guard_passed": true,
    "environment_guard_passed": true
  }
}
```

`SafetyResult`の概念schema:

```json
{
  "schema_version": "runtime_v2_safety_result_v1",
  "decision": "ALLOW",
  "severity": "info",
  "reason_code": "SAFETY_ALLOW",
  "review_message": "",
  "stop_reason": "",
  "allowed_actions": ["continue"],
  "blocked_actions": [],
  "evidence_refs": [],
  "refined_classification": null,
  "requires_manual_approval": false,
  "created_at": "..."
}
```

## 9. Stage別必須Safety Gate

launchd前に必須化するgate:

1. `pre_planning`
   - Current SoTが読めない場合は `REVIEW_REQUIRED` または `BLOCK`。
2. `post_planning`
   - planがcash / buying_power / positionsと整合しない場合は `BLOCK`。
3. `pre_approval`
   - review-required riskがあればApprovalへ進めない。
4. `pre_submit`
   - Safety `ALLOW` 以外はSubmit禁止。
5. `post_broker_readonly`
   - Broker divergenceやcritical staleは `REVIEW_REQUIRED` または `EMERGENCY_STOP`。
6. `post_reconcile`
   - Reconcile findingをSafety/Reviewへ接続。
7. `manual_review`
   - 人間承認なしにHALT/REVIEW_REQUIREDを解除しない。

## 10. 禁止事項

Safety Integrationで禁止すること:

- Runtime v2にSafety判断ロジックを再実装すること。
- Safety結果をRuntimeが投資判断として上書きすること。
- market stressをRuntime側で自動売買判断へ変換すること。
- Safety `REVIEW_REQUIRED` を無視してSubmitすること。
- Safety `BLOCK` を無視してSubmitすること。
- Safety `EMERGENCY_STOP` 中にSubmit、Cancel、Modify、自動復旧すること。
- Safety resultをAI学習へ混入すること。
- Safety Report / Audit / Review QueueをSubmit sourceにすること。

## 11. launchd前Acceptance

Safety未接続ならlaunchdを開始しない。

launchd前Acceptance:

1. 正規CLIが各stageでSafetyRuntime Interfaceを呼ぶ設計になっている。
2. `pre_submit`でSafety `ALLOW` 以外ならSubmitしない。
3. `REVIEW_REQUIRED` はexit code 20で停止する。
4. `BLOCK` はexit code 10で停止する。
5. `EMERGENCY_STOP` はexit code 30で停止する。
6. Report / Notification Payload / AuditへSafety decision, reason, evidence refsが出る。
7. launchdはSafety停止を自動復旧しない。
8. Notificationは初期payload-only。
9. Manual Review Runbookへ引き継げる。

## 12. Phase14-E3以降への引き継ぎ

次に必要な設計:

1. **Phase14-E3: Restart / Recovery Matrix**
   - Safety停止後の再開条件、manual approval、review解除条件を整理する。

2. **Phase14-E4: Manual Intervention / External Broker Action Runbook**
   - Safety `REVIEW_REQUIRED` / `HALT` からの人間確認手順をRuntime v2 artifactへ接続する。

3. **Phase14-E6: Runtime v2 CLI Skeleton**
   - E1/E2 Contractに沿ったCLI skeletonとSafety interface呼び出しを実装する。

4. **Phase14-E7: launchd Demo Dry-run Design**
   - Safety-connected CLIをsubmit-disabled / payload-onlyでlaunchdへ接続する設計を行う。

## Acceptance Criteria

| Criteria | 判定 |
| --- | --- |
| RuntimeはSafety判断を持たない | PASS |
| Safety責務が明確 | PASS |
| Runtime Stateとの対応が明確 | PASS |
| launchd前条件が明記 | PASS |
| Safety Interfaceが定義されている | PASS |
| コード変更なし | PASS |
| Broker APIなし | PASS |
| Submitなし | PASS |
| Notification送信なし | PASS |
| launchd/plist変更なし | PASS |

## 結論

Runtime v2はPhase11 Safety Layerを正規Safety Runtime Interfaceとして呼び、`ALLOW` / `REVIEW_REQUIRED` / `BLOCK` / `EMERGENCY_STOP` をRuntime State Machineへ反映する。

Safetyが未接続の状態ではlaunchdへ進まない。

したがって最終判定は **PHASE14E2_SAFETY_INTEGRATION_CONTRACT_COMPLETE** とする。
