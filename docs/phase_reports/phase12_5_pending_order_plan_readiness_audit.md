# Phase12.5 Pending Order Plan Readiness Audit

## Summary

判定: REVIEW_REQUIRED

Phase Aで `pending_order_plan` schema / writer / reader は追加済みだが、現時点では本線のApproval / Submitはまだpendingを読んでいない。

この状態で放置しても既存Submit経路には直接影響しない。一方で、pendingが「未承認の準備artifact」のまま残り得るため、次に進むなら Phase B Approval linkage を先に実装する必要がある。

## Checked Files / Artifacts

コード:

- `src/ai_fund_lab_v2/operations/pending_order_plan.py`
- `src/ai_fund_lab_v2/operations/operations.py`
- `scripts/run_daily_plan.py`
- `scripts/run_approval_prepare.py`
- `scripts/run_submit_operation.py`
- `tests/phase12/test_pending_order_plan_phase_a.py`

Runtime artifact:

- `.runtime/operations/pending_order_plan/`
- `.runtime/operations/order_plan/2026-07-06/order_plan.json`
- `.runtime/operations/approval_artifact/2026-07-06/approval_artifact.json`

確認時点では `.runtime/operations/pending_order_plan/` 配下に実artifactは存在しなかった。

## 1. run_daily_plan Pending Generation

`run_daily_plan()` はPhase A実装により、日付別 `order_plan/YYYY-MM-DD/order_plan.json` を従来通り履歴として生成した後、条件付きで `promote_order_plan_to_pending_if_allowed()` を呼ぶ。

昇格条件:

- Daily Plan statusが `PASS`
- JST実行日が `plan_created_date` と一致
- JST 15:30以降
- `intended_submit_date` が `market_calendar.next_business_day`
- `target_session_date == intended_submit_date`
- 未消費の `PENDING_APPROVAL` / `APPROVED` / `SUBMITTING` pendingが競合していない

statusが `BLOCK` のPlanはpendingへ昇格しない。

現Runtimeでは `order_plan/2026-07-06/order_plan.json` は存在するが、statusは `BLOCK`、buy/sellとも0件だった。そのためpending未生成はPhase Aの条件上は正常。

## 2. run_approval_prepare Pending Readiness

現状の `run_approval_prepare()` はpendingを読んでいない。

現在読むもの:

- `order_plan/<trade_date>/order_plan.json`
- `safety_result/<trade_date>/safety_result.json`
- `broker_snapshot_summary/<trade_date>/broker_snapshot_summary.json`
- broker readonly bundle

不足しているもの:

- pendingを読む処理
- `pending_plan_id` と `approval_artifact` の紐付け
- `source_order_plan.hash` とApproval対象Planの一致検証
- `approval.status` / `approval.path` / `approval.hash` をpendingへ書き戻す処理
- `approved_item_ids` がpending itemsに含まれることの検証
- `approval_expires_at` と `intended_submit_date` の整合チェック

このため、Phase Aのpendingは現在 `PENDING_APPROVAL` の器であり、Approval済みSubmit SoTとしてはまだ使えない。

## 3. run_submit_operation Status

`run_submit_operation()` はまだpendingを読んでいない。

現在のSubmit対象解決:

```text
_resolve_submit_order_plan_date()
  1. 当日 order_plan + approval があれば当日を採用
  2. なければ previous_business_day の order_plan + approval を採用
  3. それもなければ当日にfallback
```

したがって、Phase Aのpending artifactが存在してもSubmit本線には影響しない。

ただし、このままではpendingを作ってもSubmit混線問題は解消しない。Submit切替までは従来の当日Plan優先リスクが残る。

## 4. Inconsistency Risks

pendingと日付別artifactが不一致になり得る箇所:

- pending作成後に日付別 `order_plan` が再生成される
- pending作成後に `approval_artifact` が別Planを承認する
- pendingが `PENDING_APPROVAL` のまま、日付別approvalだけが `APPROVED` になる
- pendingが競合により更新されず、日付別Planだけ新しくなる
- 現在のSubmitはpendingを無視するため、pendingと実Submit sourceがズレる
- Report/AuditがpendingをまだSoTとして扱っていないため、不一致を検知しきれない

現Runtime例:

- `order_plan/2026-07-06`: `status=BLOCK`, `buy_item_count=0`
- `approval_artifact/2026-07-06`: `status=APPROVED`, `approved_item_ids=0`
- pending artifact: missing

この例では実害は限定的だが、PlanがBLOCKでもApproval artifactがAPPROVEDという日付別artifact上の見た目のズレがある。pending導入後は、Approval linkageでこの種のズレを明示的にBLOCK/REVIEWへ寄せるべき。

## 5. Natural Operation Risk While Unconnected

本線未接続のまま自然運用した場合:

- 既存Submitはpendingを読まないため、pendingが壊れていてもSubmitは止まらない
- 既存Submitは引き続き当日Plan優先の `_resolve_submit_order_plan_date()` に依存する
- pendingが作られても、Approvalがpendingに反映されない
- pendingが作られても、Submit後に消費されない
- pendingが未消費のまま残ると、次のDaily Plan昇格を競合として止める可能性がある
- Report/Auditがpending未接続なので、pendingと実Submit sourceの乖離が見えにくい

結論:

短期間のPhase A放置は既存Runtimeを壊さないが、Production Equivalent Runtimeとしては未完成。次フェーズへ進む前にApproval linkageが必要。

## 6. Next Minimal Step

次に実装すべき最小ステップは Phase B Approval linkage。

理由:

- Submit切替には `state=APPROVED` のpendingが必要
- 現pendingはApproval情報が空のまま
- Approval hash / source_order_plan hash / approved_item_ids整合がない状態でSubmitをpendingへ切り替えると、未承認PlanをSubmit対象にする危険がある

Phase C Submit切替は、Phase B完了後に行うべき。

## 7. Guards / Tests Required Before Submit Switch

Submit切替前に必要なguard:

- pendingが存在しない場合はBLOCK
- `state != APPROVED` はBLOCK
- `intended_submit_date != submit_run_date` はBLOCK
- `target_session_date != submit_run_date` はBLOCK
- `source_order_plan.hash` が日付別Planと一致しない場合はBLOCK/REVIEW
- `approval.hash` が日付別Approvalと一致しない場合はBLOCK/REVIEW
- `approval.status != APPROVED` はBLOCK
- `approved_item_ids` がpending itemsに含まれない場合はBLOCK
- `approval_expires_at` 切れはBLOCK
- `submit_constraints.allow_dated_order_plan_fallback != false` はBLOCK
- `state in SUBMITTED/CONSUMED/EXPIRED` は再Submit禁止
- `SUBMITTING` staleは自動再送せずREVIEW_REQUIRED

必要なテスト:

- Approval linkageでpendingが `APPROVED` になる
- Approval linkageでapproval hashが保存される
- mismatched plan hashでBLOCK
- approved_item_ids不一致でBLOCK
- Friday evening pending + Monday morning submit guard PASS
- Monday morning手動PlanがあってもpendingだけをSubmit sourceにする
- pending missingでSubmit BLOCK
- pending consumedで再Submit BLOCK
- stale SUBMITTINGでREVIEW_REQUIRED
- Submit本線が日付別order_plan fallbackを使わない

## Prohibited Actions

今回は以下を実施していない。

- 実装なし
- Submit実行なし
- Broker注文なし
- artifact削除なし
- notification送信なし

## Conclusion

判定: REVIEW_REQUIRED

Phase Aのpendingは「作れる・読める」状態だが、Approval / Submit本線はまだ未接続。次はPhase B Approval linkageを実装し、pendingを承認済みSubmit SoTへ昇格できる状態にしてから、Phase C Submit切替へ進むべき。
