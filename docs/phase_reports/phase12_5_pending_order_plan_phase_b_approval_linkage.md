# Phase12.5 Pending Order Plan Phase B Approval Linkage

## Summary

Phase Aで追加した `pending_order_plan` を、日付別 `approval_artifact` と正式に紐付けた。

今回はPhase Bのみであり、Submit本線の切替は行っていない。

## Implemented

変更ファイル:

- `src/ai_fund_lab_v2/operations/pending_order_plan.py`
- `src/ai_fund_lab_v2/operations/operations.py`
- `tests/phase12/test_pending_order_plan_phase_b_approval_linkage.py`

実装内容:

- `link_approval_to_pending_order_plan()` を追加
- `run_approval_prepare()` が日付別approval artifact生成後、対応するpendingがあればApproval結果をpendingへ書き戻す
- pendingが無い場合は既存approval flowを壊さず `SKIPPED_PENDING_MISSING`
- 日付別 `approval_artifact/YYYY-MM-DD/approval_artifact.json` は従来通り生成
- Submit本線は未接続のまま維持

## Pending Approval Linkage

pendingに追記/更新する項目:

- `approval.status`
- `approval.approval_id`
- `approval.path`
- `approval.hash`
- `approval.approved_item_ids`
- `approval.approval_expires_at`
- `approval.approval_max_notional`
- `approval.approval_max_notional_source`
- `approval.source_order_plan_hash`
- `approval.linkage_status`
- `approval.linkage_reasons`
- `updated_at`

Approvalが `APPROVED` かつ整合性検証がPASSした場合のみ、pendingの `state` を `APPROVED` に更新する。

不一致または `REVIEW_REQUIRED` / `BLOCK` 系の場合は、pendingを `APPROVED` にせず `BLOCKED` とし、`promotion.blocked_reason` / `approval.review_reason` / `approval.linkage_reasons` に理由を残す。

## Hash Validation

linkage時に以下を検証する。

- `pending.source_order_plan.path` が今回の `order_plan` path と一致
- `pending.source_order_plan.hash` が現在の `order_plan` hash と一致
- `approval.plan_id` が `pending.source_order_plan.plan_id` と一致
- `approval.production_order_allowed == false`
- `approval.status == APPROVED` の場合、`approval_expires_at` が存在

保存するhash:

- `approval.hash = stable_hash(approval_artifact_payload)`
- `approval.source_order_plan_hash = stable_hash(order_plan_payload)`

## Approved Item Validation

`approval.approved_item_ids` はpendingの `items[].item_id` に含まれる必要がある。

含まれない場合:

- pendingは `APPROVED` にならない
- `approval.linkage_reasons` に `approved_item_ids_not_in_pending_items` を残す

## Submit Mainline

今回はSubmit本線を切り替えていない。

- `run_submit_operation()` は引き続き `_resolve_submit_order_plan_date()` を使う
- `run_submit_operation()` は `read_pending_order_plan()` を呼ばない
- consume処理は未接続
- Broker注文なし
- Submit実行なし

## Tests

実行:

```bash
PYTHONPATH=src python3 -m pytest tests/phase12/test_pending_order_plan_phase_b_approval_linkage.py -q
PYTHONPATH=src python3 -m pytest tests/phase12/test_pending_order_plan_phase_a.py tests/phase12/test_phase12_approval.py tests/phase12/test_phase12_demo_submit_guard.py -q
```

結果:

```text
6 passed
28 passed
```

確認したこと:

- pending存在 + approval `APPROVED` で pending.state が `APPROVED`
- approval hash / path / approved_item_ids がpendingに保存される
- order_plan hash mismatchなら pending.state は `APPROVED` にならない
- approved_item_ids がpending.itemsに無い場合は `APPROVED` にならない
- approval `REVIEW_REQUIRED` なら pendingは `BLOCKED`
- pendingが無い場合でも既存approval_prepareは壊れない
- 日付別approval artifactは従来通り生成される
- Submit本線は未接続
- raw request / raw response / secret は保存されない

## Prohibited Actions

今回は以下を実施していない。

- Submit実行なし
- Broker注文なし
- Production接続なし
- Production注文なし
- artifact削除なし
- notification送信なし
- `run_submit_operation` 切替なし
- consume本線接続なし
- AI再学習なし
- フルバックテストなし

## Remaining Work

- Phase C: `run_submit_operation()` をpending-only参照へ切替
- pending `APPROVED` / intended date / target session / hash / expiry guardをSubmit前に強制
- Submit成功後の `SUBMITTING` -> `SUBMITTED` / `CONSUMED` state transition
- consumed copy保存
- Report / Audit / Notificationへのpending source表示

## Result

判定: PASS

Approval linkageは実装済み。Submit本線はまだ既存日付解決のままなので、Phase C前にSubmit guard設計をそのまま実装する必要がある。
