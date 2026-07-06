# Phase12.5 Pending Order Plan Phase A

## Summary

`order_plan/YYYY-MM-DD` をSubmit対象SoTとして直接使う設計をやめる準備として、固定パスの `pending_order_plan` schema / writer / reader を追加した。

今回はPhase Aのみであり、Submit本線はまだ切り替えていない。

## Implemented

追加:

- `src/ai_fund_lab_v2/operations/pending_order_plan.py`
  - pending schema builder
  - writer / reader
  - schema validation
  - source order plan hash保存
  - state管理の初期実装
  - promotion guard

更新:

- `src/ai_fund_lab_v2/operations/operations.py`
  - `run_daily_plan()` が従来通り `order_plan/YYYY-MM-DD/order_plan.json` を履歴として書く
  - 条件を満たす場合のみ `.runtime/operations/pending_order_plan/pending_order_plan.json` へ昇格する
  - Submit本線、`_resolve_submit_order_plan_date()`、Approval本線は未変更

追加テスト:

- `tests/phase12/test_pending_order_plan_phase_a.py`

## Pending Schema

保存先:

```text
.runtime/operations/pending_order_plan/pending_order_plan.json
.runtime/operations/pending_order_plan/history/YYYY-MM-DD/<plan_id>.json
.runtime/operations/pending_order_plan/consumed/YYYY-MM-DD/<plan_id>.json
```

Phase Aで保存する主なフィールド:

- `artifact_type = pending_order_plan`
- `schema_version = 1`
- `pending_plan_id`
- `state`
- `environment`
- `created_at`
- `updated_at`
- `plan_created_date`
- `intended_submit_date`
- `target_session_date`
- `source_order_plan.path`
- `source_order_plan.hash`
- `source_order_plan.status`
- `source_order_plan.buy_item_count`
- `source_order_plan.sell_item_count`
- `approval.required`
- `approval.status`
- `approval.path`
- `approval.hash`
- `items`
- `submit_constraints.allow_dated_order_plan_fallback = false`
- `promotion.source`
- `promotion.promoted`
- `promotion.promotion_policy`
- `promotion.blocked_reason`
- `consume`
- `raw_request_saved = false`
- `raw_response_saved = false`
- `secret_saved = false`

State:

- `PENDING_APPROVAL`
- `APPROVED`
- `SUBMITTING`
- `SUBMITTED`
- `CONSUMED`
- `EXPIRED`
- `BLOCKED`

## Promotion Conditions

`run_daily_plan()` は日付別 `order_plan` を常に履歴として生成する。

pending昇格は以下を満たす場合のみ行う。

- Daily Plan statusが `PASS`
- Plan作成日とJST実行日が一致
- JST 15:30以降
- `intended_submit_date` が `market_calendar.next_business_day`
- `target_session_date == intended_submit_date`
- 未消費の `PENDING_APPROVAL` / `APPROVED` / `SUBMITTING` pendingが競合していない

朝の手動 `run_daily_plan` は、日付別履歴は作るが pending には昇格しない。

## Friday To Monday

Friday evening caseをテストした。

- `plan_created_date = 2026-07-03`
- `intended_submit_date = 2026-07-06`
- `target_session_date = 2026-07-06`
- pending昇格あり

これにより、金曜夜Planから月曜朝Submitへの意図をpending上で明示できる。

## Submit Mainline

今回はSubmit本線を切り替えていない。

- `run_submit_operation()` は引き続き `_resolve_submit_order_plan_date()` を使う
- `pending_order_plan` はSubmitから読まない
- `_resolve_submit_order_plan_date()` は削除していない
- consume処理は本線未接続
- Approval linkage本実装は未接続

## Tests

実行:

```bash
PYTHONPATH=src python3 -m pytest tests/phase12/test_pending_order_plan_phase_a.py -q
PYTHONPATH=src python3 -m pytest tests/phase12/test_phase12_demo_submit_guard.py tests/phase12/test_phase12_approval.py tests/phase12/test_operations_market_refresh.py -q
```

結果:

```text
5 passed
28 passed
```

補足:

最初に既存テストを1件名指定で実行したが、該当テスト名が存在せず `no tests ran` だったため、ファイル単位で再実行してPASSを確認した。

## Prohibited Actions

今回は以下を実施していない。

- Submit実行なし
- Broker注文なし
- Production接続なし
- Production注文なし
- artifact削除なし
- notification送信なし
- Daily Plan以外のRuntime本線切替なし
- AI再学習なし
- フルバックテストなし

## Remaining Work

- Phase B: Approval artifactとpendingの本格linkage
- Phase C: `run_submit_operation()` をpending参照へ切替
- Phase D: Submit成功後のconsume本線接続
- Report / Audit / Notificationへpending source / consume情報を表示
- 既存日付別artifactからのmigration

## Result

判定: PASS

Pending Order Plan Phase Aとして、schema / writer / reader / validation / hash / promotion guardを追加し、Submit本線未接続のままDaily Planからの条件付き昇格まで確認した。
