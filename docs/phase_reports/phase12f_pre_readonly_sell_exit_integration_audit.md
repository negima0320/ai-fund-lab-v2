# Phase12-F Pre-ReadOnly SELL / Exit Integration Audit

作成日: 2026-06-29

## Status

```text
PHASE12F_PRE_READONLY_SELL_EXIT_INTEGRATION_AUDIT_COMPLETE
IMPLEMENTATION_CHANGED_FALSE
RUNTIME_CHANGED_FALSE
DEMO_ORDER_WIRE_EXECUTION_FALSE
DEMO_ORDER_EXECUTED_FALSE
PRODUCTION_ORDER_EXECUTED_FALSE
LINE_SEND_EXECUTED_FALSE
AI_RETRAINING_EXECUTED_FALSE
BACKTEST_RERUN_FALSE
```

## 1. Purpose

Broker Read-only実運用およびDemo Order Wire Executionへ進む前に、SELL判断 / Exit統合がPhase12 Operationsの日次運用フローへ接続されているかを監査した。

今回は調査・監査のみであり、実装変更、Runtime変更、Broker API変更、Demo注文、Production注文、LINE実送信、AI再学習、Backtest再実行は行っていない。

## 2. Read Materials / Code

確認した資料:

- `docs/phase_reports/phase12a_demo_full_operation_design.md`
- `docs/phase_reports/phase12b_demo_full_operation_minimal_implementation.md`
- `docs/phase_reports/phase12c_demo_order_wire_execution_unlock_design.md`
- `docs/phase_reports/phase12d_operations_daily_runtime_design.md`
- `docs/phase_reports/phase12d_operations_daily_runtime_implementation.md`
- `docs/phase_reports/phase12e_pre_wire_operations_rehearsal.md`
- `docs/phase_reports/phase11_final_summary_and_phase12_handoff.md`
- `docs/phase_reports/phase11_completion_audit.md`
- `docs/phase_reports/phase11z_fix_g_5y_refined_mainline_full.md`
- `docs/phase_reports/phase11z_fix_h_1y_equity_linked_exposure.md`
- `docs/02_architecture/safety_layer_phase11_refined_design.md`
- `docs/03_ai_design/position_management_ai_design.md`
- `docs/03_ai_design/capital_allocation_design.md`

確認したコード:

- `src/ai_fund_lab_v2/operations/operations.py`
- `src/ai_fund_lab_v2/operations/guards.py`
- `scripts/run_daily_plan.py`
- `scripts/run_approval_prepare.py`
- `scripts/run_demo_submit.py`
- `scripts/run_fill_monitor.py`
- `scripts/run_reconcile.py`
- `scripts/run_daily_report.py`
- `src/ai_fund_lab_v2/position_management_ai/inference.py`
- `src/ai_fund_lab_v2/position_management_ai/calibration.py`
- `src/ai_fund_lab_v2/order_manager/schema.py`
- `src/ai_fund_lab_v2/order_manager/order_plan_generator.py`
- `src/ai_fund_lab_v2/order_manager/allocation_decision_loader.py`
- `src/ai_fund_lab_v2/paper_trading/daily_inference_runner.py`
- `src/ai_fund_lab_v2/paper_trading/virtual_fill_processor.py`
- `src/ai_fund_lab_v2/paper_trading/reporting/`

## 3. SELL Decision Source

Position Management AI:

- `src/ai_fund_lab_v2/position_management_ai/inference.py`
  - `build_position_management_output()` が `action`、`exit_candidate`、`reduce_candidate`、`action_reason`、`exit_reason` を生成する。
  - `classify_position_action()` は `EXIT` / `REDUCE` / `ADD` / `HOLD` を返す。
  - `EXIT` は `hard_stop_current_return`、`profit_retention_break`、`trend_and_opportunity_broken`、`risk_guard_status_bad`、`exit_score_high` などを `exit_reason` として持てる。
- `src/ai_fund_lab_v2/position_management_ai/calibration.py`
  - calibrated outputも `EXIT` / `REDUCE` と `exit_reason` を生成できる。

Phase9 / mainline:

- `src/ai_fund_lab_v2/paper_trading/daily_inference_runner.py`
  - `policy_versions.position_management_ai` はmanifestに残る。
  - ただし `_build_position_rows()` は既存ledger positionを `HOLD` として並べるだけで、Position Management AIの `EXIT` / `REDUCE` 出力を接続していない。
  - `_build_allocation_rows()` はBUY候補のみを生成している。
  - `_with_l2_states()` は `sell_candidates=()` / `hold_candidates=()` にしている。
  - したがって現在のPhase9 daily inference runnerは、Production品質のPosition Management Exit統合ではない。

Phase11 caveat:

- `phase11_final_summary_and_phase12_handoff.md`
- `phase11_completion_audit.md`
- `phase11z_fix_g_5y_refined_mainline_full.md`
- `phase11z_fix_h_1y_equity_linked_exposure.md`

これらに `exit_source=fallback` が残っている。

監査判断:

```text
exit_source=fallback は現在も残存。
Phase12 Operations run_daily_plan.py はPosition Management AIを呼んでSELL判断を生成していない。
SELLを外部plan_itemsとして渡すことは可能だが、Exit統合済みとは言えない。
```

## 4. Order Plan SELL Support

Phase12 Operations:

- `run_daily_plan()` は `plan_items` に `side="SELL"` を渡すと、Order Plan itemとして保存できる。
- `_normalize_plan_item()` は `side` を大文字化し、SELLを保持する。
- `production_order_allowed=false`
- `demo_order_allowed=false`
- `requires_approval=true`

不足:

- `position_id`
- lot reference
- `reason`
- `exit_source`
- `sell_reason`
- `expected_notional`
- Broker position quantity reference
- realized PnL estimate
- partial sell / full close intent

mock SELL dry-run確認:

```text
input item:
side=SELL
exit_source=mock_position_ai
sell_reason=audit_sell_flow

saved order_plan:
side=SELL
exit_source dropped
sell_reason dropped
reason dropped
position reference absent
```

監査判断:

```text
Phase12 Order PlanはSELL side自体は扱える。
ただしExit運用に必要なSELL固有metadataを保持できないため、Demo運用前のblocking gap。
```

## 5. Approval SELL Support

現在のApproval:

- `run_approval_prepare()` はOrder Planの全item idを `approved_item_ids` に入れられる。
- SELL itemもitem idとして承認対象にできる。
- `demo_order_allowed=true` はapproval全体に付く。
- `production_order_allowed=false` は維持される。

不足:

- allowed sidesの明示なし。
- SELL理由 / `exit_source` / `sell_reason` がapproval request / artifactへ出ない。
- `max_quantity` なし。
- SELL時の保有数量超過チェックなし。
- Approval artifactがSELL固有のscopeを持たない。
- Human Reviewで「なぜ売るのか」を確認する材料が足りない。

監査判断:

```text
ApprovalはSELL item idを承認できるが、SELL承認として十分なscopeではない。
```

## 6. Safety / MAX_EXPOSURE

Phase11最終方針:

- SELL / exposure reducing order はMAX_EXPOSUREでは止めない。
- BUYは `max_total_exposure_ratio=0.85` で制限する。
- System / Broker / Order異常はSELLでも止める。

現Operations:

- `evaluate_max_exposure()` は `side != BUY` を `ALLOW` にする。
- mock SELL dry-runでも `reason=sell_or_exposure_reducing_order_not_blocked_by_max_exposure` でALLOW。
- `run_demo_submit()` はapprovalなし、production flag、Safety `BLOCK` / `SYSTEM_EMERGENCY_STOP` をSELLでも止める。

不足:

- SELL時のposition mismatch / over-sellは現状のsubmit guardで検知していない。
- Broker position数量との照合がない。

監査判断:

```text
SELLはMAX_EXPOSUREで不当にBLOCKされない。
ただしSELL数量 / Broker position整合性のguardが未完成。
```

## 7. `run_demo_submit.py` SELL Support

確認結果:

- SELL itemをOrder Planから読み込める。
- approved item idに含まれるSELLを処理対象にできる。
- `_command_from_item()` はBUY以外をSELLとして `OrderCommand` にできる。
- `run_demo_submit()` はstub / dry-run境界でSELLを `DRY_RUN_READY` にできる。
- Demo wire未解禁状態でもSELL dry-runは可能。

mock SELL dry-run結果:

```text
submit_status=PASS
submitted item sell_1 status=DRY_RUN_READY
demo_order_submitted=false
production_order_submitted=false
broker_order_api_called=false
max_exposure.reason=sell_or_exposure_reducing_order_not_blocked_by_max_exposure
```

不足:

- 現物売りとしてのBroker request schema確認はPhase12-C設計止まり。
- 保有数量チェックなし。
- 売却数量がBroker positionを超えないか未確認。
- submitted artifactに `side` / `quantity` / `issue_code` が残らない。
- `exit_source` / `sell_reason` がsubmitted artifactへ伝播しない。

監査判断:

```text
SELL dry-run候補としては扱える。
Demo wire前にBroker Source of Truthによるposition quantity guardとSELL metadata伝播が必要。
```

## 8. Fill Monitor SELL Support

現Operations:

- `run_fill_monitor()` は状態分類をside非依存で扱う。
- `SUBMITTED`
- `ACCEPTED`
- `WAITING_FILL`
- `PARTIALLY_FILLED`
- `FILLED`
- `REJECTED`
- `EXPIRED`
- `CANCELED`
- `UNKNOWN_STATUS`

mock SELL dry-run結果:

```text
fill_status=PASS
fill_event lifecycle=SUBMITTED
```

Phase9 Virtual Fill:

- `virtual_fill_processor.py` はSELLをBUYより先に処理する。
- `SELL_QUANTITY_INSUFFICIENT` を検知する。
- SELL fillでposition数量を減らす。
- 全売却ならpositionをcloseする。
- realized PnLを更新する。

不足:

- Phase12 Operations Fill MonitorはSELL sideをartifactへ残していない。
- SELL partially filled / filled後のposition減少を確認していない。
- full close / partial sell残数量を扱うschemaがない。
- Broker executions / positionsとのsemantic reconciliationがない。

監査判断:

```text
状態分類はSELLにも使えるが、SELL約定後のposition減少 / close / partial残数量をPhase12 Operationsではまだ扱えていない。
```

## 9. Reconciliation / Ledger / Report SELL Support

Reconciliation:

- `run_reconcile()` は対象としてBroker orders / executions / positions / ledger / fill / safety / reportを持つ。
- ただし現状は存在確認に近く、SELLの数量減少、position close、cash / buying_power増加、realized PnLまでは照合していない。

Ledger:

- Phase9 `virtual_fill_processor.py` はSELLでcash増加、position減少、position close、realized PnLを扱える。
- Phase12 Operations ledger連携は未完成。

Report:

- Phase9 reportingはSELL rows、realized PnL、sell reason表示の仕組みを持つ。
- Phase12 `run_daily_report()` はoperation status refs中心で、SELL理由 / `exit_source` / realized resultを出していない。

監査判断:

```text
Phase9にはSELL ledger/report能力がある。
Phase12 OperationsにはSELL semantic reconciliation / ledger update / report表示が未接続。
```

## 10. Minimal SELL Dry-run Test Result

実装変更なしで、一時rootにmock SELL planを渡してdry-run flowを確認した。

```text
operation_root=/private/tmp/phase12f_sell_audit_mock
Broker API call=false
Demo order wire execution=false
Production order=false
```

Flow:

```text
run_market_refresh()
run_daily_plan(plan_items=[SELL])
run_approval_prepare(approve=True)
run_demo_submit()
run_fill_monitor()
run_reconcile()
run_daily_report()
```

Result:

```text
submit_status=PASS
submitted SELL status=DRY_RUN_READY
fill_status=PASS
fill lifecycle=SUBMITTED
reconcile_status=REVIEW_REQUIRED
report_status=PASS
```

確認できたこと:

- SELL sideはOperations flowを通過できる。
- SELLはMAX_EXPOSUREでBLOCKされない。
- Demo wire / Broker order API / Production orderは呼ばれない。

確認できたgap:

- `exit_source` / `sell_reason` / `reason` はOrder Plan保存時に落ちる。
- position id / lot reference / broker position quantity checkがない。
- submitted / fill / reportへSELL固有情報が伝播しない。

## 11. Blocking Gaps

Demo運用開始前に修正すべきblocking gap:

1. Phase12 `run_daily_plan.py` がPosition Management AI / Exit Logicを呼んでSELL判断を生成していない。
2. `exit_source=fallback` がPhase11成果物に残っており、Production品質のExit統合は未完了。
3. Phase12 Order Plan schemaがSELL固有metadataを保持できない。
4. Approval artifactがSELL理由、allowed side、max quantity、position referenceを持たない。
5. `run_demo_submit.py` にBroker Source of TruthベースのSELL保有数量チェックがない。
6. submitted order / fill eventにSELLの `side`、`quantity`、`issue_code`、`exit_source`、`sell_reason` が十分に伝播しない。
7. Phase12 ReconciliationがSELL後のposition減少、full close、partial sell残、cash / buying_power変化、realized PnLを照合できない。
8. Phase12 Daily ReportがSELL理由 / `exit_source` / realized resultを表示できない。

## 12. Recommended Phase12 Next Tasks

優先順位付き:

1. Phase12 SELL schema拡張
   - `position_id`
   - `broker_position_quantity`
   - `lot_reference`
   - `exit_source`
   - `sell_reason`
   - `expected_notional`
   - `sell_intent=FULL_CLOSE | PARTIAL_SELL`
2. Position Management / Exit Logic adapter設計
   - Phase12 Operations用にJ-Quants由来featureだけを使う。
   - Broker Snapshot / Paper Ledger / Safety / Audit / cash / portfolio / PnLをAI学習へ混入させない。
3. `run_daily_plan.py` にSELL generation boundaryを追加
   - 実装前に設計レビュー。
   - fallback exitを使う場合は `exit_source=fallback` を明示し、Production revenue quality blockerとして扱う。
4. Approval SELL scope追加
   - side
   - quantity
   - max_quantity
   - position reference
   - sell reason
   - exit source
5. Submit SELL guard追加
   - Broker Source of Truth position quantity
   - over-sell block
   - position mismatch block
6. Fill Monitor SELL semantics追加
   - partial fill
   - full close
   - remaining quantity
7. Reconciliation SELL semantics追加
   - Broker orders / executions / positions / ledger / cash / buying_power / realized PnL
8. Daily Report SELL section追加
   - sell reason
   - exit_source
   - quantity
   - realized result
9. Mock SELL dry-run testを正式テスト化
   - Broker APIなし。
   - Demo wireなし。
   - raw responseなし。
   - secretなし。

## 13. Final Judgement

```text
PHASE12F_PRE_READONLY_SELL_EXIT_INTEGRATION_AUDIT_COMPLETE
SELL_SIDE_BASIC_FLOW_SUPPORTED_TRUE
SELL_EXIT_INTEGRATION_COMPLETE_FALSE
EXIT_SOURCE_FALLBACK_REMAINS_TRUE
DEMO_OPERATION_BEFORE_SELL_FIX_NOT_RECOMMENDED
DEMO_ORDER_WIRE_EXECUTION_FALSE
PRODUCTION_ORDER_EXECUTED_FALSE
LINE_SEND_EXECUTED_FALSE
```
