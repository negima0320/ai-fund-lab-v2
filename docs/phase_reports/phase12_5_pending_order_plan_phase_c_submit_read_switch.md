# Phase12.5 Pending Order Plan Phase C Submit Read Switch

## Summary

Phase Cとして、`run_submit_operation()` のSubmit対象を日付別 `order_plan/YYYY-MM-DD` / `approval_artifact/YYYY-MM-DD` の自動解決から、固定パスの `pending_order_plan` 参照へ切り替えた。

今回はSubmit read switchのみであり、実Submit、実Broker注文、Phase D consume本線接続は行っていない。

## Implemented

変更ファイル:

- `src/ai_fund_lab_v2/operations/pending_order_plan.py`
- `src/ai_fund_lab_v2/operations/operations.py`
- `tests/phase12/test_pending_order_plan_phase_c_submit_read_switch.py`
- `tests/phase12/test_pending_order_plan_phase_a.py`
- `tests/phase12/test_pending_order_plan_phase_b_approval_linkage.py`
- `tests/phase12/test_phase12_demo_submit_guard.py`

実装内容:

- `load_pending_order_plan_for_submit()` を追加
- `run_submit_operation()` のSubmit入力を `.runtime/operations/pending_order_plan/pending_order_plan.json` 固定に変更
- 日付別 `order_plan` / `approval_artifact` はSubmit対象選択には使わず、pending内のpath/hash検証対象としてのみ読む
- `_resolve_submit_order_plan_date()` は残したが、Submit本線からは外した
- guard失敗時は日付別fallbackせず、`submitted_orders` artifactへ理由を残す
- stale `SUBMITTING` は自動再送せず `REVIEW_REQUIRED`
- `submitted_orders` にpending source metadataを保存

## Submit Source

Submit source:

```text
.runtime/operations/pending_order_plan/pending_order_plan.json
```

日付別fallback:

```text
dated_order_plan_fallback_used = false
```

互換用に `order_plan_source_date` / `approval_source_date` は残すが、選定元はpending固定。

## Guards

Submit前guard:

- pending artifact exists
- `pending.state == APPROVED`
- `pending.intended_submit_date == submit_run_date`
- `pending.target_session_date == submit_run_date`
- `pending.approval.status == APPROVED`
- `pending.approval.path` exists
- `pending.approval.hash` matches current approval artifact hash
- `pending.source_order_plan.path` exists
- `pending.source_order_plan.hash` matches current order_plan hash
- pending approval item ids are contained in `pending.items[].item_id`
- approval artifact item ids are contained in `pending.items[].item_id`
- pending approval item ids match approval artifact item ids
- `approval_expires_at` exists, parses, and is not expired
- `submit_constraints.allow_dated_order_plan_fallback == false`
- terminal states `SUBMITTED` / `CONSUMED` / `EXPIRED` block resubmit
- `SUBMITTING` returns `REVIEW_REQUIRED` instead of automatic resend
- Phase12.5 production order disabled remains enforced

Guard failure behavior:

- Broker注文しない
- 日付別fallbackしない
- `status = BLOCK` or `REVIEW_REQUIRED`
- reasonを `submitted_orders` artifactに保存

## submitted_orders Metadata

Submit resultに追加/維持したmetadata:

- `pending_plan_id`
- `pending_plan_path`
- `plan_created_date`
- `intended_submit_date`
- `target_session_date`
- `source_order_plan.path`
- `source_order_plan.hash`
- `approval.path`
- `approval.hash`
- `submit_source = pending_order_plan`
- `dated_order_plan_fallback_used = false`
- `uses_pending_order_plan = true`
- `pending_order_plan_submit_guard`

## _resolve_submit_order_plan_date

`_resolve_submit_order_plan_date()` は互換のため残しているが、`run_submit_operation()` 本線では使っていない。

テストで `run_submit_operation()` のsourceに `_resolve_submit_order_plan_date` が存在しないこと、`load_pending_order_plan_for_submit` が存在することを確認した。

## Tests

実行:

```bash
PYTHONPATH=src python3 -m pytest tests/phase12/test_pending_order_plan_phase_c_submit_read_switch.py -q
PYTHONPATH=src python3 -m pytest tests/phase12/test_phase12_demo_submit_guard.py -q
PYTHONPATH=src python3 -m pytest \
  tests/phase12/test_pending_order_plan_phase_a.py \
  tests/phase12/test_pending_order_plan_phase_b_approval_linkage.py \
  tests/phase12/test_pending_order_plan_phase_c_submit_read_switch.py \
  tests/phase12/test_phase12_approval.py \
  tests/phase12/test_phase12_demo_submit_guard.py \
  -q
```

結果:

```text
12 passed
13 passed
46 passed
```

確認したこと:

- pending `APPROVED` + intended date一致でSubmit対象として読まれる
- pending missingならSubmit `BLOCK`
- pending.state != `APPROVED` なら `BLOCK`
- intended_submit_date不一致なら `BLOCK`
- target_session_date不一致なら `BLOCK`
- approval hash mismatchなら `BLOCK`
- order_plan hash mismatchなら `BLOCK`
- approved_item_ids不一致なら `BLOCK`
- approval expiredなら `BLOCK`
- consumed pendingなら再Submit `BLOCK`
- stale `SUBMITTING` なら `REVIEW_REQUIRED`
- 当日 `order_plan` / `approval` が存在しても、pendingが前営業日由来ならpendingを使う
- 日付別fallbackが使われない
- `submitted_orders` にpending metadataが出る
- unit testsではFakeAdapterまたは `execute_order=False` のみ
- raw request / raw response / secret保存なし

## Prohibited Actions

今回は以下を実施していない。

- 実Submit実行なし
- 実Broker注文なし
- Production接続なし
- Production注文なし
- artifact削除なし
- notification送信なし
- Phase D consume本線実装なし
- AI再学習なし
- フルバックテストなし

## Remaining Work

- Phase D: Submit開始/成功/失敗に応じたpending state transition
- `SUBMITTING` stale recovery runbook
- consumed copy保存
- Report / Audit / Notificationへpending source / guard / consume状態を表示
- launchd自然運用でpending生成、approval linkage、Submit read switchの連続確認

## Result

判定: PASS

Submit対象はpending固定になり、日付別artifact fallbackはSubmit本線から外れた。
