# Phase14-E5 Business Day / Carryover Contract

作成日: 2026-07-07

## 最終判定

**PHASE14E5_BUSINESS_DAY_CARRYOVER_COMPLETE**

Phase14-E1からE4で、Operation Entry、Safety Integration、Restart / Recovery Matrix、Manual Intervention / External Broker Action Runbookを定義した。E5では、営業日・休日・祝日・週末・未約定注文・Pending・Review状態を翌営業日へどう引き継ぐかを固定する。

今回は設計のみであり、コード変更、Broker API呼び出し、Submit、Cancel API呼び出し、Notification送信、launchd/plist変更は行っていない。

## 基本原則

1. 日付変更だけではCurrentを切り替えない。
2. Currentは固定Pathから読む。
3. History / phase artifact / Report / Blog / Audit / Notification PayloadからCurrentを推測しない。
4. 営業日開始時は、Current Read、Broker ReadOnly、Safety、ReconcileをPlanning前に行う。
5. Pendingは状態ごとにcarryover可否を判定する。
6. 未約定・部分約定・失効・外部取消はBroker ReadOnlyで確認する。
7. 不明なら`REVIEW_REQUIRED`。
8. 危険なら`HALT`。
9. Runtime mode差分はpathではなくmetadata / broker adapter / configで扱う。

## Business Day定義

| Term | 定義 | Runtime扱い |
| --- | --- | --- |
| 営業日 | 対象市場が通常取引を行う日 | Daily operation対象 |
| 非営業日 | 市場休場日 | Submit禁止。ReadOnly / Report / Auditは必要に応じて可 |
| 祝日 | 日本市場休場日 | 非営業日 |
| 土日 | 週末 | 非営業日 |
| 半日取引 | 市場が短縮取引を行う日 | 営業日だがSubmit window / monitoring windowを短縮扱い |
| 市場休場 | 臨時休場、災害、取引所停止等 | Submit禁止。Safety/Report/Auditへ |

Calendar source:

- Primary: 正規market calendar / J-Quants trading calendar相当。
- Fallback: 明示的なJP market holiday table。
- Calendar record missingは「休場」と即断しない。partial/stale calendarの可能性があるため、fallback確認または`BLOCKED` / `REVIEW_REQUIRED`にする。

## Day Boundary

### 前営業日終了

前営業日終了時に行うこと:

1. Broker ReadOnly status sync。
2. Pending state確認。
3. Open order / unfilled / partial fill確認。
4. Ledger / Asset / Reconcile。
5. Report / Notification Payload / Audit。
6. Carryover candidatesをHistory / Evidenceとして記録。

禁止:

- Reportを翌営業日のCurrentにする。
- `order_plan/YYYY-MM-DD` を翌営業日のSubmit sourceにする。
- Pendingを日付だけで自動更新する。

### 翌営業日開始

翌営業日開始時に行うこと:

1. Calendar / business day判定。
2. Current SoT read。
3. Broker ReadOnly。
4. Pending state read。
5. Runtime State read。
6. Safety precheck。
7. Reconcile。
8. Pending carryover判定。
9. Planning。

日付が変わっても、`.runtime/persistent_ledger/state.json` や `.runtime/pending_order_plan/pending_order_plan.json` は固定PathのCurrentであり続ける。

## Pending Carryover Policy

| Pending State | 翌営業日扱い | Auto submit | Required evidence | Policy |
| --- | --- | --- | --- | --- |
| `APPROVED` | approval expiry / intended_submit_date / target_session_dateを再確認 | 条件付き。すべてPASSかつsubmit-enabledのみ | pending, approval hash, current, safety, business day | 日付がズレたら`EXPIRED`または`REVIEW_REQUIRED` |
| `SUBMITTED` | Broker ReadOnlyで注文状態確認 | NO | orders ledger, broker orders | Monitoringへ。再Submit禁止 |
| `POST_SEND_UNKNOWN` | Broker ReadOnlyとManual Review | NO | submit attempt, orders/events, broker orders | 自動再送禁止。`REVIEW_REQUIRED`基本 |
| `MONITORING_FILL` | Broker ReadOnlyで未約定/部分約定/約定/失効確認 | NO | broker orders/executions/positions/cash | Reflection/Reconcileへ。Submit retry禁止 |
| `REVIEW_REQUIRED` | 人間確認まで停止 | NO | review event, broker/current evidence, safety | 解除後にPlanningまたはRecovery |
| `BLOCKED` | blocking reason解消まで停止 | NO | blocked event, preflight evidence | 解消後preflight |
| `CONSUMED` | terminal。再Submit不可 | NO | consumed metadata, orders/events | 次計画は新pending plan id |
| `EXPIRED` | terminal。再Submit不可 | NO | expiry evidence | 新しいplan/approvalが必要 |
| `PENDING_APPROVAL` | 承認待ち。日付/期限を再確認 | NO | pending, approval request | 古ければ`EXPIRED`または`REVIEW_REQUIRED` |

## Unfilled Order Policy

| Case | 翌営業日扱い | Asset反映 | Required action |
| --- | --- | --- | --- |
| 未約定持ち越し | Broker ReadOnlyで注文が生きているか確認 | なし | `MONITORING_FILL`継続またはReview |
| 部分約定 | execution/position/cash evidenceで反映 | 約定分のみ | Ledger/Asset/Reconcile。残数量はMonitoring |
| 全部約定 | position/cash evidenceで反映 | 反映 | Ledger/Asset/Reconcile |
| 失効 | Broker order statusで確認 | 約定なしなら変化なし | Pending terminal / Reconcile |
| Broker取消 | Broker order statusで確認 | 約定なしなら変化なし | D7型ならConsumed / Reconcile |
| 外部取消 | Broker ReadOnly + Review Event | 状況次第 | E4 Runbookへ |
| order status unknown | 不明 | 反映保留 | `REVIEW_REQUIRED` |

## Current SoT読込順

翌営業日開始時の読込順:

1. `.runtime/runtime_state/current_state.json`
2. `.runtime/persistent_ledger/state.json`
3. `.runtime/persistent_ledger/orders.jsonl`
4. `.runtime/persistent_ledger/executions.jsonl`
5. `.runtime/persistent_ledger/positions.jsonl`
6. `.runtime/persistent_ledger/cash.jsonl`
7. `.runtime/persistent_ledger/events.jsonl`
8. `.runtime/pending_order_plan/pending_order_plan.json`
9. `.runtime/notification_delivery/delivery_ledger.jsonl`
10. Broker ReadOnly evidence
11. Safety result
12. Reconcile result

History / Evidenceは、hash確認、説明、監査、手動Reviewのために参照できるが、Current推測元にしない。

## Business Day開始時の必須処理

Planning前に必須:

1. Calendar判定。
2. Current Read。
3. Broker ReadOnly。
4. Safety precheck。
5. Reconcile。
6. Pending carryover判定。

これらがPASSしない場合:

- Current不明: `REVIEW_REQUIRED`または`BLOCKED`。
- Broker ReadOnly失敗: `REVIEW_REQUIRED`またはexit code `50`。
- Safety `REVIEW_REQUIRED`: exit code `20`。
- Safety `BLOCK`: exit code `10`。
- Safety `EMERGENCY_STOP`: exit code `30`。
- Calendar不明: `BLOCKED`または`REVIEW_REQUIRED`。

## Carryover禁止

翌営業日のCurrentとして使ってはいけないもの:

- Report。
- Blog。
- Audit。
- Notification Payload。
- phase artifact。
- `order_plan/YYYY-MM-DD`。
- `approval_artifact/YYYY-MM-DD`。
- `submitted_orders/YYYY-MM-DD`。
- `broker_positions/YYYY-MM-DD`だけをCurrentとすること。
- `ledger/YYYY-MM-DD` daily summary。

## Review状態の翌営業日扱い

`REVIEW_REQUIRED` が残っている場合:

```text
REVIEW_REQUIRED
↓
Manual Review
↓
Broker ReadOnly / Current evidence confirmation
↓
Safety recheck
↓
Reconcile
↓
manual approval
↓
Planning or Recovery
```

解除なしにPlanningやSubmitへ進まない。

`BLOCKED` が残っている場合:

- blocking reasonを確認。
- 解消後にpreflightを再実行。
- Safety由来ならSafety再評価。
- Submitへ進むにはPending `APPROVED` とduplicate guard PASSが必要。

`HALT` が残っている場合:

- 翌営業日でも自動復帰しない。
- Manual emergency reviewが必須。
- 原則 `IDLE` または `CURRENT_STATE_LOADED` へ戻す。
- 直接 `SUBMITTING` / `SUBMITTED` へ戻さない。

## launchd Business Day Policy

launchd営業日開始時に読むもの:

1. Runtime State Current。
2. Persistent Ledger Current。
3. Pending Current。
4. Ledger JSONL。
5. Notification Delivery Ledger。
6. Calendar state。
7. Broker ReadOnly evidence。
8. Safety result。
9. Reconcile result。

launchdが読まないもの:

- phase artifactをCurrentとして読まない。
- Report / Blog / Audit / Notification PayloadをCurrentとして読まない。
- `order_plan/YYYY-MM-DD`からSubmitしない。
- `approval_artifact/YYYY-MM-DD`からSubmitしない。

launchd exit条件:

| Condition | Exit code |
| --- | --- |
| Normal success | 0 |
| Non-business day safe skip | 0 |
| BLOCKED | 10 |
| REVIEW_REQUIRED | 20 |
| HALT | 30 |
| Config / env / calendar error | 40 |
| Broker ReadOnly failure | 50 |
| Submit blocked | 60 |
| Unexpected error | 70 |

Non-business day safe skip:

- Submitしない。
- 必要ならReport / Audit / Notification Payloadだけ生成。
- Pendingを日付だけで変更しない。
- Open ordersがある可能性がある場合は、次営業日のReadOnlyまで`MONITORING_FILL`または`REVIEW_REQUIRED`。

## Runtime Mode

| Mode | Business Day扱い | Path |
| --- | --- | --- |
| `demo` | 実営業日calendarを使う。Demo brokerの約定仕様差はmetadataで扱う | fixed Current path |
| `simulation` | simulation clock / scenario calendarを使う。実Broker禁止 | fixed Current path conceptまたはsimulation artifact。Production/Demo Currentに混ぜない |
| `production` | 実営業日calendarとProduction Broker evidenceを使う。Production Submitは別Acceptanceまで禁止 | fixed Current path |

runtime mode差分はpathではなく、runtime request、broker adapter、clock/calendar adapter、config、metadataで表現する。

## launchd Dry-runへ引き継ぐ条件

Phase14-E7以降のlaunchd dry-runへ進む条件:

1. E1 Operation Entry Contract完了。
2. E2 Safety Integration Contract完了。
3. E3 Restart / Recovery Matrix完了。
4. E4 Manual Intervention Runbook完了。
5. E5 Business Day / Carryover Contract完了。
6. Current SoT read/write-backがD22同等にPASS。
7. 正規CLI skeletonがfixed Current pathを読む。
8. launchd初期設定はsubmit-disabled / notification payload-only。
9. Non-business day safe skipがSubmitしない。
10. Friday evening pending / Monday morning handlingがtest対象になる。

## Acceptance Criteria

| Criteria | 判定 |
| --- | --- |
| Business Dayが定義されている | PASS |
| Pending Carryoverが定義されている | PASS |
| 未約定持ち越しが定義されている | PASS |
| Current SoT読込順が定義されている | PASS |
| HistoryからCurrentを推測しない | PASS |
| phase artifactからCurrent復元しない | PASS |
| launchd開始時の読込順が定義されている | PASS |
| Runtime Mode差分をpathで表現しない | PASS |
| コード変更なし | PASS |
| Broker API呼び出しなし | PASS |
| Submitなし | PASS |
| Notification送信なし | PASS |
| launchd/plist変更なし | PASS |

## 結論

Runtime v2は、営業日境界を跨いでも固定Current Pathを維持し、翌営業日開始時にCurrent Read、Broker ReadOnly、Safety、Reconcileを行ってからPlanningへ進む。

Pendingや未約定注文は状態別にcarryover可否を判定し、`POST_SEND_UNKNOWN`、`REVIEW_REQUIRED`、`BLOCKED`、`HALT`、`CONSUMED`、`EXPIRED`を自動Submitへ戻さない。

したがって最終判定は **PHASE14E5_BUSINESS_DAY_CARRYOVER_COMPLETE** とする。
