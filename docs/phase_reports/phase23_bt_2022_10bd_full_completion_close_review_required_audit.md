# Phase23-BT 2022年10BD Full Completion Close REVIEW_REQUIRED Audit

## Primary Judgment

`PHASE23_BT_2022_10BD_FULL_COMPLETION_CLOSE_REVIEW_REQUIRED_AUDIT_COMPLETE`

Read-only監査として完了。Production code / test / fixture / Runtime rerun / fresh-run / resume / Broker Write / Runtime Switch / J-Quants取得 / 既存Run artifact mutation は実施していない。

## 対象Run

- Run: `reports/runtime_tests/runs/runtime-test-historical-smoke-20260730T211110605880Z`
- fresh-run status: `REVIEW_REQUIRED`
- final_judgment: `REVIEW_REQUIRED`
- exit_code: `10`
- error: `close returned REVIEW_REQUIRED`
- run_state.status: `COMPLETED`
- requested business days: `10`
- completed business days: `10`
- early halt: `NO`

Completed days:

`2022-07-01`, `2022-07-04`, `2022-07-05`, `2022-07-06`, `2022-07-07`, `2022-07-08`, `2022-07-11`, `2022-07-12`, `2022-07-13`, `2022-07-14`

## Mandatory First Confirmation

- review_business_date: `2022-07-14`
- review_stage: `close`
- direct_review_reason: `strategy_shadow_judgment REVIEW_REQUIRED propagated through close_command strategy acceptance gate`
- lowest_level_reason: `runtime_planning existing_pending_conflict:23880 with SOURCE_RUNTIME_CONSUMER_NOT_ELIGIBLE / SOURCE_VALIDATION_REVIEW_REQUIRED`
- first_invalid_artifact: `daily/2022-07-14/strategy/runtime_planning.json`
- first_invalid_component: `strategy.runtime_planning`
- first_invalid_symbol: `23880`
- close_judgment: `REVIEW_REQUIRED`
- close_reason_codes: `existing_pending_conflict:23880` plus non-blocking planning taxonomy reason codes

Close実装上、`scripts/runtime_test.py::close_command()` は `update_run_strategy_shadow_indexes()` のaggregate `strategy_shadow_judgment` と `_strategy_acceptance_gate_status()` をFinal Summaryへ反映する。今回は日次Runtime自体ではなく、最終日のEOD Strategy Shadow `runtime_planning` が `REVIEW_REQUIRED` になり、それがCloseへ伝播した。

## Full 10BD Completion

`REQUESTED_BUSINESS_DAYS = 10`

`COMPLETED_BUSINESS_DAYS = 10`

`ALL_REQUESTED_DAYS_EXECUTED = YES`

`EARLY_HALT = NO`

Morning / Sell Planning / Submit / Historical Execution / Current Valuation は10営業日すべて実行完了。HALT summaryは `NOT_HALTED`。

## Trading Inventory

Fill inventory:

- `2022-07-08`: BUY `94320` 1100 @ 153.3
- `2022-07-11`: BUY `23880` 1400 @ 132.0
- `2022-07-11`: BUY `94340` 1100 @ 153.9
- `2022-07-12`: BUY `94320` 100 @ 158.0
- `2022-07-13`: BUY `66590` 1000 @ 145.0
- `2022-07-14`: SELL `23880` 1400 @ 113.0

SELL lifecycle:

`SELL_PATH_REACHED = YES`

`23880` の `SELL_EXIT` / full-position sell がSubmit Guard、Historical Fill、Cash update、Position updateまで到達している。

## BS Runtime Verification

2022-07-12 PM ADD:

- symbol: `94320`
- side: `BUY`
- source_decision_type: `ADD`
- expected quantity: `100`
- submitted_count: `1`
- fill: BUY `94320` 100 @ 158.0
- `submit_policy_consistency.policy_consistency_status = PASS`
- `missing_submit_policy_evidence = ABSENT`

Judgment:

- `BS_PM_ADD_RUNTIME_PASS = YES`
- `BS_SUBMIT_POLICY_RUNTIME_PASS = YES`
- `PM_ADD_SUBMITTED = YES`
- `PM_ADD_FILLED = YES`

Phase23-BS修正は実Runtimeで成立している。

## Close REVIEW_REQUIRED Trace

Final Summary:

- `strategy_shadow_judgment = REVIEW_REQUIRED`
- `strategy_review_required_dates = ["2022-07-14"]`
- `strategy_lineage_completeness = REVIEW_REQUIRED`
- `strategy_planning_authority_acceptance = REVIEW_REQUIRED`

2022-07-14 `strategy/runtime_planning.json`:

- `producer_result_status = REVIEW_REQUIRED`
- `validation_status = REVIEW_REQUIRED`
- `runtime_consumer_eligibility = NOT_ELIGIBLE`
- `human_review_status = REQUIRED`
- `consumer_eligibility_reason_codes = ["SOURCE_RUNTIME_CONSUMER_NOT_ELIGIBLE"]`
- `human_review_reason_codes = ["SOURCE_LIFECYCLE_DRAFT", "SOURCE_RUNTIME_CONSUMER_NOT_ELIGIBLE", "SOURCE_VALIDATION_REVIEW_REQUIRED"]`

該当plan:

- symbol: `23880`
- planning_intent: `BUY_NEW`
- planned_quantity: `1500`
- pending_eligibility: `REVIEW_REQUIRED`
- planning_reason: `existing_pending_conflict;position_sizing_quantity_candidate_resolved;positive_quantity_delta_maps_to_buy_new`

同じ日に実Runtimeでは、既存position `23880` が `SELL_EXIT` で全量売却済み。Final current pending snapshotにも `23880 SELL 1400` のCONSUMED Pendingが残っている。EOD Strategy Shadow runtime_planningは、そのCurrent pending artifactを参照し、`23880 BUY_NEW`候補に対して `existing_pending_conflict` と判定した。

## Trading State Reconciliation

- initial_cash: `1,000,000`
- total BUY debit: `683,520`
- total SELL credit: `158,200`
- net cash effect: `-525,320`
- expected ending cash: `474,680`
- actual ending cash: `474,680`
- realized PnL: `-26,600`
- unrealized PnL: `-19,300`
- market value: `478,950`
- total equity: `953,630`

Open positions:

- `94320`: 1200
- `94340`: 1100
- `66590`: 1000

Judgment:

- `TRADING_STATE_VALID = YES`
- `ACCOUNTING_STATE_VALID = YES`
- `AUDIT_STATE_VALID = NO_CLOSE_AUTHORITY_REVIEW_REQUIRED`
- `ROLLBACK_REQUIRED = NO`
- `STATE_DISCARD_REQUIRED = NO`
- `RERUN_REQUIRED = NO_FOR_TRADING_STATE__YES_AFTER_REPAIR_FOR_CLOSE_PASS_EVIDENCE`

## BT-RQ Answers

BT-RQ1: 最終日だけのClose問題。途中日のStrategy ShadowはPASSで、`strategy_review_required_dates` は `2022-07-14` のみ。

BT-RQ2: Execution / Fill / Cash / Position / Ledgerに不整合は確認されない。

BT-RQ3: 取引自体は完了している。問題はEOD Strategy Shadow runtime_planningのReviewをClose AuthorityがTrading State invalidityと区別せずFinal Judgmentへ伝播したこと。

BT-RQ4: Production-common Contract Gap。Historical固有ではなく、Close acceptance gateがnon-mutating strategy shadow reviewをどう扱うかの契約不足。

BT-RQ5: Trading Stateに対するrollback/discardは不要。Close Authority修正後、Close PASS evidenceを得る目的のrerun/close再評価は必要。

BT-RQ6: SELL lifecycleへ到達した。`2022-07-14` に `23880 SELL_EXIT 1400` がSubmit/Fillされた。

BT-RQ7: `2022-07-12` のPM ADDはSubmit・Fillされた。`94320 BUY 100 @ 158.0`。

## Classification

- `CLOSE_AUTHORITY_MISMATCH`
- `PLANNING_LINEAGE_FAILURE`
- `NON_BLOCKING_OBSERVABILITY_GAP`
- `PRODUCTION_CONTRACT_VIOLATION`

Closeのfail-closed / review-required自体は適切。ただし、取引状態不整合ではないEOD shadow reviewを最終Runtime validityと同列に扱う契約が未整理。

## Previous Blocker Recurrence

以下は直接blockerとして再発なし。

- `missing_submit_policy_evidence`
- `policy_mismatch`
- `current_position_business_date_mismatch`
- `strategy_plan_price_missing`
- `strategy_plan_quantity_unresolved`
- `opportunity_evidence_missing`
- `opportunity_no_buy_reason_present`
- `pending_safety_evidence_missing`
- `portfolio_membership_unresolved`
- `position_ownership_unresolved`
- `cash_authority_unresolved`
- `valuation_authority_unresolved`
- `historical_source_binding recurrence`

新規直接reason:

`existing_pending_conflict:23880` in EOD Strategy Shadow runtime_planning.

## Recommended Next Action

`Phase23-BU Close Authority Strategy Shadow Review Classification Repair`

最小修正範囲は、Close Acceptance Gateが以下を区別すること。

- Trading State / Accounting / Ledger invalidity
- Production consumerの実Runtime Planning failure
- non-mutating EOD Strategy Shadow review
- consumed pending artifactを参照したobservability-only conflict

テストをPASSにするためのClose判定緩和は禁止。

## Gate

- `REPAIR_REQUIRED = YES`
- `READY_FOR_REPAIR = YES`
- `READY_FOR_ALTERNATE_PERIOD_10BD = NO_UNTIL_CLOSE_AUTHORITY_REPAIR_REVIEW`
- `READY_FOR_20BD = NO`
- `READY_FOR_200BD = NO`

## Deliverables

- Human: `docs/phase_reports/phase23_bt_2022_10bd_full_completion_close_review_required_audit.md`
- Machine: `reports/phase_reports/phase23_bt_2022_10bd_full_completion_close_review_required_audit.json`
- Evidence: `reports/phase23_bt_2022_10bd_full_completion_close_review_required_audit/`
