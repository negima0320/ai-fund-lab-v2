# Phase14-E3 Runtime v2 Restart / Recovery Matrix

作成日: 2026-07-07

## 最終判定

**PHASE14E3_RESTART_RECOVERY_MATRIX_COMPLETE**

Phase14-E1でRuntime v2 Operation Entry Contractを定義し、Phase14-E2でSafety Integration Contractを定義した。E3では、Runtime v2が停止・失敗・再起動した場合に、どの状態から再開でき、どの状態では自動再開してはいけないかを定義する。

今回は設計のみであり、コード変更、Broker API呼び出し、Submit、Notification送信、launchd/plist変更、Current SoT追加writeは行っていない。

## 基本原則

1. Submit / Broker Writeは二重実行防止を最優先する。
2. `POST_SEND_UNKNOWN` は自動再送しない。
3. `SUBMITTING` 以降のBroker Submit再実行は禁止する。
4. `CONSUMED` Pendingから再Submitしない。
5. Broker ReadOnlyで事実確認してから、人間確認またはRecoveryへ進む。
6. Currentは固定Pathのみ読む。
7. phase配下artifactからCurrentを復元しない。
8. Report / Audit / Notification PayloadをCurrentやSubmit sourceにしない。
9. Safety `REVIEW_REQUIRED` / `BLOCK` / `EMERGENCY_STOP` をlaunchdが自動解除しない。
10. 不明な状態は `REVIEW_REQUIRED`、危険な状態は `HALT` へ倒す。

## Restart判定に使うCurrent

launchd再実行・手動再開時は、まず以下を読む。

```text
.runtime/runtime_state/current_state.json
.runtime/pending_order_plan/pending_order_plan.json
.runtime/persistent_ledger/state.json
.runtime/persistent_ledger/orders.jsonl
.runtime/persistent_ledger/executions.jsonl
.runtime/persistent_ledger/positions.jsonl
.runtime/persistent_ledger/cash.jsonl
.runtime/persistent_ledger/events.jsonl
.runtime/notification_delivery/delivery_ledger.jsonl
```

History / Evidence / Derivedとして参照してよいが、Current復元元にしてはいけないもの:

```text
.runtime/phase14d*/...
order_plan/YYYY-MM-DD
approval_artifact/YYYY-MM-DD
reports/*
audit_result/*
notification_payload/*
```

## 自動再開してよい処理

次は、固定CurrentとSafety precheckが通る場合に自動再開してよい。

- Market Refresh
- Feature Refresh
- Current State Read
- AI inference
- Planning dry-run
- Approval linkage verification
- Broker ReadOnly Sync
- Execution Reflection dedup
- Ledger projection dedup
- Reconcile
- Report
- Audit
- Notification Payload生成

## 自動再開してはいけない処理

次は自動再開禁止。

- Broker Submit再実行。
- Cancel API。
- Modify API。
- Production Broker Write。
- Notification Send。
- Delivery Send。
- `POST_SEND_UNKNOWN` からの自動再Submit。
- `CONSUMED` Pendingからの再Submit。
- `REVIEW_REQUIRED`解除なしのSubmit。
- `BLOCKED`解除なしのSubmit。
- `HALT`からの自動復帰。

## Restart / Recovery Matrix

| State | auto_resume_allowed | allowed_next_action | required_current_evidence | required_broker_readonly | required_manual_review | prohibited_actions | exit_code | report_required | audit_required |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `IDLE` | YES | Start normal operation after Safety precheck | runtime_state, asset state, pending state | NO | NO | none beyond normal guards | 0 | NO | NO |
| `MARKET_DATA_READY` | YES | Feature Refresh or re-run Market Refresh if stale | runtime_state, market refresh evidence | NO | NO | Submit, Broker Write | 0 | NO | NO |
| `FEATURE_READY` | YES | Current State Read / AI inference | runtime_state, feature evidence | NO | NO | Submit, Broker Write | 0 | NO | NO |
| `CURRENT_STATE_LOADED` | YES | AI inference / Planning | runtime_state, asset state, pending state | NO | NO unless state unknown | Submit before approval | 0 | NO | NO |
| `AI_INFERENCE_DONE` | YES | Planning rerun from Current + AI artifact if valid | runtime_state, current state, AI artifact hash | NO | NO | Submit, direct Pending overwrite | 0 | NO | NO |
| `DAILY_PLAN_CREATED` | YES | Pending promotion check, or re-plan if stale | runtime_state, current state, daily_plan evidence | NO | NO unless conflict | Direct Submit from order_plan | 0 | Optional | Optional |
| `PENDING_PROMOTED` | YES | Approval prepare / approval linkage verification | pending_order_plan, runtime_state | NO | NO | Direct Submit without approval | 0 | Optional | Optional |
| `APPROVAL_PENDING` | YES | Approval verification or wait for manual approval | pending_order_plan, approval request | NO | YES if approval absent/stale | Submit | 20 if waiting | YES | Optional |
| `APPROVED` | CONDITIONAL | Submit preflight only; Submit only if explicitly enabled and all guards pass | pending_order_plan APPROVED, approval hash, orders ledger, runtime_state | NO before submit; YES if stale orders suspected | YES if stale/ambiguous | Submit if duplicate/Safety/env guard fails | 0 or 60 | YES | YES |
| `SUBMITTING` | NO | Broker ReadOnly investigation; classify as SUBMITTED / POST_SEND_UNKNOWN / REVIEW_REQUIRED | pending SUBMITTING, submit attempt event, orders ledger, events | YES | YES | Broker Submit retry, Cancel, Modify | 20 | YES | YES |
| `SUBMITTED` | NO for Submit, YES for monitoring | Broker ReadOnly status sync, fill monitoring | orders ledger, pending consumed/submitted state, runtime_state | YES | NO unless broker state unknown | Broker Submit retry, consumed pending resubmit | 0 or 20 | YES | YES |
| `POST_SEND_UNKNOWN` | NO | Broker ReadOnly confirmation, Review Required workflow | orders ledger/events, pending state, submit attempt evidence | YES | YES | Automatic resubmit, Cancel/Modify unless separately approved | 20 | YES | YES |
| `MONITORING_FILL` | YES for ReadOnly | Broker ReadOnly sync, Execution Reflection dedup | orders ledger, broker evidence refs, pending state | YES | NO unless order status unknown | Broker Submit retry | 0 or 20 | YES | YES |
| `LEDGER_UPDATED` | YES | Reconcile from fixed Current | state.json, ledger jsonl, runtime_state | Optional if evidence stale | NO unless mismatch | Current rebuild from phase artifact | 0 or 20 | YES | YES |
| `RECONCILED` | YES | Report / Notification Payload / Audit | reconciliation result, state.json, runtime_state | NO | NO unless finding | Current write by Report/Audit | 0 | YES | YES |
| `REPORT_READY` | YES | Audit, Notification Payload regeneration, end run | report refs, runtime_state, state.json | NO | NO unless report has review flags | Notification Send unless enabled and delivery guarded | 0 | YES | YES |
| `REVIEW_REQUIRED` | NO | Manual Review, Broker ReadOnly, Report, Audit | review event, runtime_state, current state, relevant evidence | YES if broker fact needed | YES | Submit, auto-clear, auto-resume to Submit | 20 | YES | YES |
| `BLOCKED` | NO | Resolve blocking condition, preflight again | blocked event, runtime_state, pending/current state | Optional by reason | YES if unresolved or safety-related | Submit before unblock | 10 | YES | YES |
| `HALT` | NO | Manual emergency review only | halt event, safety result, audit, broker/current evidence | YES if broker fact needed | YES | Submit, Cancel, Modify, Notification Send, auto recovery | 30 | YES | YES |

## Non-idempotent Policy

非冪等処理:

- Broker Submit
- Cancel
- Modify
- Broker Write
- Notification Send
- Delivery Send

Policy:

- これらは、同一run / 同一pending / 同一delivery recordで自動再実行しない。
- pre-sendで失敗した場合のみ、Broker APIまたはNotification Sendが未呼び出しである証跡があれば再preflightできる。
- post-send不明は必ずReadOnly / Delivery Ledger確認へ進む。
- 外部副作用済みの可能性がある場合、RetryではなくReviewに送る。

## POST_SEND_UNKNOWN Policy

`POST_SEND_UNKNOWN` は、Broker Submit中に応答不明、通信断、結果未確定が起きた状態である。

必須動作:

1. 自動再Submitしない。
2. Pendingを再Submit可能状態へ戻さない。
3. Broker ReadOnlyで注文状態を確認する。
4. Broker側に注文があるなら `SUBMITTED` / `MONITORING_FILL` へ分類する。
5. Broker側に注文が確認できない場合も、自動再Submitせず `REVIEW_REQUIRED` に止める。
6. Report / Audit / Notification Payloadへ `post_send_unknown` を明示する。

## REVIEW_REQUIRED Policy

`REVIEW_REQUIRED` は人間確認が必要な停止状態である。

解除条件:

- review eventが特定されている。
- Broker ReadOnlyまたはCurrent evidenceで事実確認済み。
- Safety resultが`ALLOW`またはmanual-approved相当へ戻っている。
- 人間承認、承認者、承認時刻、理由、証跡が残っている。
- 必要なら新しいpending plan idを作る。既存`CONSUMED` pendingを再利用しない。

禁止:

- launchdが自動解除すること。
- Review中にSubmitへ進むこと。
- Report / Audit findingだけを解除根拠にすること。

Exit code: `20`

## BLOCKED Policy

`BLOCKED` は条件未充足または禁止による停止状態である。

解除条件:

- blocking reasonが解消済み。
- config/env/current/pending/approval/safety guardが再preflightでPASS。
- Submitが必要な場合は、Pendingが`APPROVED`であり、duplicate guardがPASS。
- Safety由来のBLOCKはSafety再評価またはManual Reviewが必要。

Exit code: `10`

## HALT Policy

`HALT` は重大不整合またはsystem emergencyである。

解除条件:

- 自動解除禁止。
- Manual emergency review必須。
- Broker ReadOnlyまたは外部証跡で実状態確認。
- Safety emergency解除の明示承認。
- Recovery record / audit / reportが生成される。
- 必要な補正はappend-only correction / migrationで行い、破壊的削除で戻さない。

禁止:

- Submit。
- Cancel。
- Modify。
- Notification Send。
- launchd auto recovery。

Exit code: `30`

## launchd Restart Policy

launchd再実行時の標準手順:

1. 正規CLI entryを起動する。
2. `runtime_state/current_state.json` を読む。
3. `pending_order_plan/pending_order_plan.json` を読む。
4. `persistent_ledger/*.jsonl` と `state.json` を読む。
5. `notification_delivery/delivery_ledger.jsonl` を読む。
6. Safety precheckを実行する。
7. 前回状態とCurrent evidenceから再開可否を判定する。
8. 再開可能なら安全な冪等処理だけ再開する。
9. 不明なら `REVIEW_REQUIRED`。
10. 危険なら `HALT`。
11. Report / Audit / Notification Payloadを生成する。

launchdがしてはいけないこと:

- Safety停止の自動解除。
- `SUBMITTING` からBroker Submit再実行。
- `POST_SEND_UNKNOWN` からBroker Submit再実行。
- `CONSUMED` Pendingの再Submit。
- `HALT`からの復帰。
- Notification Sendの自動retry。

## Recovery Runbookとの関係

E3はMatrix設計であり、具体的な人間作業Runbookは後続へ渡す。

- Manual Review: Phase14-E4
- External Broker Action: Phase14-E4
- Position Drift: Phase14-E4またはE5
- Business Day / Carryover: Phase14-E5
- CLI implementation: Phase14-E6
- launchd dry-run design: Phase14-E7

## Acceptance Criteria

| Criteria | 判定 |
| --- | --- |
| Runtime State別の再開可否が定義されている | PASS |
| POST_SEND_UNKNOWN自動再送禁止が明記されている | PASS |
| SUBMITTING / SUBMITTED / CONSUMED Pendingの再Submit禁止が明記されている | PASS |
| launchd再実行時の安全挙動が定義されている | PASS |
| REVIEW_REQUIRED / BLOCKED / HALT解除条件が定義されている | PASS |
| Current固定Pathのみを使う方針が維持されている | PASS |
| Safety結果を自動解除しない方針が明記されている | PASS |
| コード変更していない | PASS |
| Broker API呼び出ししていない | PASS |
| Submitしていない | PASS |
| Notification送信していない | PASS |
| launchd/plist変更していない | PASS |

## 結論

Runtime v2は、冪等処理のみを自動再開し、Submit / Broker Write / Notification Sendなどの外部副作用は自動再実行しない。

`POST_SEND_UNKNOWN`、`REVIEW_REQUIRED`、`BLOCKED`、`HALT` は、安全停止として扱い、Broker ReadOnly、Safety、Manual Review、Report、Auditを経由してのみ復旧する。

したがって最終判定は **PHASE14E3_RESTART_RECOVERY_MATRIX_COMPLETE** とする。
