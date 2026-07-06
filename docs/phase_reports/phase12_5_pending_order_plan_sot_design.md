# Phase12.5 Pending Order Plan SoT Design

## Scope

今回は設計のみ。実装、Submit実行、Broker注文、artifact削除、notification送信は行っていない。

目的は、`order_plan/YYYY-MM-DD` をSubmit対象として直接使う設計をやめ、Submit対象を固定パスの `pending_order_plan` に統一すること。

## 1. Current Order Plan Resolution

現在の主な流れ:

- `run_daily_plan(trade_date=YYYY-MM-DD)`
  - `.runtime/operations/order_plan/YYYY-MM-DD/order_plan.json` を生成する
  - `business_date` は渡された `trade_date`
  - launchdは `--trade-date` を渡さないため、script defaultの実行日になる

- `run_approval_prepare(trade_date=YYYY-MM-DD)`
  - `.runtime/operations/order_plan/YYYY-MM-DD/order_plan.json` を読み込む
  - `.runtime/operations/approval_artifact/YYYY-MM-DD/approval_artifact.json` を生成する

- `run_submit_operation(trade_date=YYYY-MM-DD)`
  - `_resolve_submit_order_plan_date()` でSubmit対象日を解決する
  - 現在の優先順位:
    1. `order_plan/<submit_run_date>/order_plan.json` と `approval_artifact/<submit_run_date>/approval_artifact.json` があれば当日を採用
    2. なければ `market_calendar.previous_business_day` のPlan/Approvalを採用
    3. それもなければ当日にfallback

このため、朝Submit前に当日Plan/Approvalが存在すると、前営業日夜に作ったPlanより当日Planが優先される。

## 2. Weekend / Morning Mixing Risk

混線パターン:

- 金曜夜 `2026-07-03` に月曜朝Submit用Planを作る
- 月曜朝 `2026-07-06` のSubmitは本来、金曜夜Planを使うべき
- しかし月曜朝に手動または誤実行で `order_plan/2026-07-06` と `approval_artifact/2026-07-06` ができる
- `_resolve_submit_order_plan_date()` は当日Planを優先する
- Submit対象が「金曜夜に承認された月曜Submit用Plan」から「月曜朝に作られた当日Plan」へ混線する

根本原因:

- `trade_date` がPlan作成日、Report日、Submit日、対象セッション日を兼ねている
- 日付別 `order_plan` が履歴であると同時にSubmit SoTでもある
- Submitが「どのPlanが承認済みで未消費か」を状態として持っていない

## 3. New Source of Truth

日付別artifactは履歴/証跡に降格する。

Submit対象のSource of Truthは固定パスにする。

推奨パス:

```text
.runtime/operations/pending_order_plan/pending_order_plan.json
.runtime/operations/pending_order_plan/history/YYYY-MM-DD/<plan_id>.json
.runtime/operations/pending_order_plan/consumed/YYYY-MM-DD/<plan_id>.json
```

互換名が必要なら `latest_pending` symlink/aliasを追加してよいが、実体は `pending_order_plan/pending_order_plan.json` に一本化する。

## 4. Pending Order Plan Schema

案:

```json
{
  "artifact_type": "pending_order_plan",
  "schema_version": 1,
  "pending_plan_id": "pending_2026-07-03_operation_plan_...",
  "state": "PENDING_APPROVAL | APPROVED | SUBMITTING | SUBMITTED | CONSUMED | EXPIRED | BLOCKED",
  "environment": "demo",
  "created_at": "...",
  "updated_at": "...",
  "plan_created_date": "2026-07-03",
  "intended_submit_date": "2026-07-06",
  "target_session_date": "2026-07-06",
  "source_order_plan": {
    "plan_id": "operation_plan_2026-07-03_...",
    "path": "order_plan/2026-07-03/order_plan.json",
    "hash": "...",
    "status": "PASS",
    "buy_item_count": 2,
    "sell_item_count": 0
  },
  "approval": {
    "required": true,
    "status": "APPROVED",
    "approval_id": "operation_approval_2026-07-03_...",
    "path": "approval_artifact/2026-07-03/approval_artifact.json",
    "hash": "...",
    "approved_item_ids": [],
    "approval_expires_at": "...",
    "approval_max_notional": "850000",
    "approval_max_notional_source": "dynamic_max_exposure"
  },
  "items": [],
  "submit_constraints": {
    "submit_source": "pending_order_plan_only",
    "allow_dated_order_plan_fallback": false,
    "production_order_allowed": false,
    "requires_unconsumed_state": true,
    "requires_intended_submit_date_match": true
  },
  "promotion": {
    "source": "launchd_daily_plan | manual",
    "promoted": true,
    "promotion_policy": "after_close_next_business_session_only",
    "blocked_reason": ""
  },
  "consume": {
    "consumed_at": "",
    "submit_run_date": "",
    "submitted_orders_path": "",
    "submitted_order_count": 0,
    "accepted_order_count": 0,
    "status": ""
  },
  "raw_request_saved": false,
  "raw_response_saved": false,
  "secret_saved": false
}
```

日付意味:

- `plan_created_date`: Daily Planを作った日
- `intended_submit_date`: Submitを実行する予定日
- `target_session_date`: 注文対象の取引セッション日
- `business_date`: 互換目的以外では新schemaの主語にしない

## 5. Approval Linkage

Approvalは日付別履歴として残しつつ、pendingに紐付ける。

必要な検証:

- `approval.plan_id == source_order_plan.plan_id`
- `approval.source_order_plan_hash == source_order_plan.hash`
- `approval.approved_item_ids` が pending items の `item_id` に含まれる
- `approval.status == APPROVED`
- `approval.approval_expires_at` がSubmit時点で有効
- `approval.production_order_allowed == false` をPhase12.5中は維持
- `approval.approval_max_notional_source != manual_override`

Approval artifactにも以下を追加する設計にする。

```json
{
  "pending_plan_id": "...",
  "plan_created_date": "2026-07-03",
  "intended_submit_date": "2026-07-06",
  "target_session_date": "2026-07-06",
  "source_order_plan_hash": "..."
}
```

## 6. Submit Consume Flow

朝Submitは以下のみを見る。

```text
.runtime/operations/pending_order_plan/pending_order_plan.json
```

Submit前ガード:

- pending artifactが存在する
- `state == APPROVED`
- `intended_submit_date == submit_run_date`
- `target_session_date == submit_run_date`
- `approval.status == APPROVED`
- `approval.hash` が保存時と一致
- `source_order_plan.hash` が保存時と一致
- `state` が `SUBMITTED` / `CONSUMED` / `EXPIRED` ではない
- `promotion.promoted == true`
- `submit_constraints.allow_dated_order_plan_fallback == false`

Submit処理:

1. pendingを読む
2. `state` を `SUBMITTING` として更新する
3. pending items と approved ids だけをSubmitする
4. `submitted_orders/YYYY-MM-DD/submitted_orders.json` を生成する
5. 成功/部分成功/Review Requiredをpendingの `consume` に記録する
6. `state` を `SUBMITTED` または `CONSUMED` に更新する
7. consumed copyを `pending_order_plan/consumed/YYYY-MM-DD/<plan_id>.json` に保存する

二重Submit防止:

- `state=SUBMITTING` が一定時間以上残った場合は自動再送せず `REVIEW_REQUIRED`
- `state=SUBMITTED/CONSUMED` のpendingは再Submit不可
- 再実行時は `submitted_orders_path` と `accepted_order_count` を見てBLOCK/REVIEWする

## 7. Manual Morning Plan Guard

手動で当日Planを作った場合でもSubmit対象へ混入させない。

設計:

- `order_plan/YYYY-MM-DD` は常に履歴として書いてよい
- pendingへの昇格は `promotion_policy` で制御する
- 通常launchd daily_planは引け後に次営業日Submit用としてpendingを更新する
- 朝Submit前の手動Daily Planは、履歴artifactは作ってもpendingへ昇格しない

推奨ガード:

```text
auto promote allowed only when:
- current local time is after configured planning cutoff, e.g. 15:30
- intended_submit_date is the next business day after plan_created_date
- target_session_date == intended_submit_date
- no APPROVED unconsumed pending exists for the same or earlier target_session_date
```

手動でpending昇格が必要な場合は、将来の明示オプションに限定する。

```text
--promote-pending
--intended-submit-date YYYY-MM-DD
--target-session-date YYYY-MM-DD
```

ただしPhase12.5の通常運用ではlaunchd引け後Planのみ昇格可とする。

## 8. Migration Plan

Phase A: Schema / writer only

- `pending_order_plan` schemaとwriter/readerを追加
- `run_daily_plan` は従来の `order_plan/YYYY-MM-DD` を書き続ける
- 条件を満たす場合のみ `pending_order_plan/pending_order_plan.json` も書く
- Submit本線はまだ切り替えない

Phase B: Approval linkage

- `run_approval_prepare` がpendingを読み、pendingにapproval情報を書き戻す
- Approval artifactにも `pending_plan_id` / `intended_submit_date` / hashを保存
- 日付別approvalは履歴として維持

Phase C: Submit read switch

- `run_submit_operation` の入力をpending固定に切り替える
- `_resolve_submit_order_plan_date()` はSubmit本線から外す
- 日付別Plan fallbackは禁止
- pending missing / stale / consumed / intended date mismatch は `BLOCK` または `REVIEW_REQUIRED`

Phase D: Consume / report integration

- Submit成功後にpendingを `SUBMITTED` / `CONSUMED` へ更新
- submitted_ordersに `pending_plan_id` / `plan_created_date` / `intended_submit_date` を保存
- Daily Report / Auditはpending consume情報を参照して、どのPlanをSubmitしたか表示する

Phase E: Historical migration

- 既存の `order_plan/YYYY-MM-DD` と `approval_artifact/YYYY-MM-DD` から未Submitの最新承認Planをpendingへ移行する
- 候補が複数、または当日Planと前営業日Planが競合する場合は自動選択せず `BLOCK_MIGRATION_REVIEW_REQUIRED`
- 既存日付別artifactは削除せず履歴として残す

## 9. Required Fix Before Runtime Switch

Submit本線を切り替える前に必須:

- pending schema validation
- pending approval hash validation
- consume state transition validation
- morning manual plan non-promotion test
- Friday evening to Monday morning test
- stale pending / consumed pending / missing pending tests
- Report / Notificationで `submitted_orders` と `pending/source_order_plan` を分ける表示

## 10. Conclusion

判定: DESIGN_REQUIRED

現状の `order_plan/YYYY-MM-DD` は履歴とSubmit SoTを兼ねており、土日跨ぎや朝の手動実行で混線する。Submit SoTは `pending_order_plan/pending_order_plan.json` に固定し、日付別Planは履歴/証跡として扱う設計へ移行するべき。
