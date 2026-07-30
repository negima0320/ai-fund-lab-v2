# Phase23-BR 2022年10BD Post-Carry-forward Submit HALT Root Cause Audit

## Primary Judgment

`PHASE23_BR_2022_10BD_POST_CARRY_FORWARD_SUBMIT_HALT_ROOT_CAUSE_AUDIT_COMPLETE`

Read-only Evidence Reviewとして完了。Production code / test / fixture / Runtime rerun / Broker Write / J-Quants取得 / 既存Run artifact mutation は実施していない。

## 対象Run

- Run: `reports/runtime_tests/runs/runtime-test-historical-smoke-20260730T110025619692Z`
- Status: `HALT`
- aggregate exit code: `30`
- inner runtime exit code: `20`
- halt business date: `2022-07-12`
- halt stage: `submit`
- completed business days: `7`
- completed days: `2022-07-01`, `2022-07-04`, `2022-07-05`, `2022-07-06`, `2022-07-07`, `2022-07-08`, `2022-07-11`

## Direct Root Cause

`PM_ADD_PENDING_SUBMIT_POLICY_AUTHORITY_MISSING`

Lowest level reason:

`missing_submit_policy_evidence`

2022-07-12のSubmit直前Data Readinessは、`.runtime/pending_order_plan/pending_order_plan.json` に `pending-order-plan-pm-add-2022-07-12` を検出している。Pending itemは1件、`94320` の `BUY`、数量 `100`、`source_decision_type=ADD`。

しかし、そのPending payload / approval / item のSubmit Policy Authorityが空だった。

- `submit_policy_context = null`
- `submit_policy_version = ""`
- `submit_policy_source = ""`
- `submit_policy_hash = ""`
- `approval.submit_policy_version = ""`
- `approval.submit_policy_source = ""`
- `approval.submit_policy_hash = ""`
- `items[0].submit_policy_version/source/hash = ""`

Submit Guardは `runtime_v2.submit.pipeline._missing_policy_evidence_reason()` でこれを `missing_submit_policy_evidence` と判定し、fail-closedで `REVIEW_REQUIRED` / `submit_action=BLOCKED` にした。Guard動作は正しい。

## First Invalid Artifact

Run-scoped evidence上の最初の不正は以下。

`daily/2022-07-12/submit/runtime_manifest.json::runtime_data_readiness_gate.components.pending.payload`

Canonical runtime pathとして記録されているのは `.runtime/pending_order_plan/pending_order_plan.json`。source order planは `.runtime/runtime_state/sell_pipeline/2022-07-12/pm_add_order_plan.json`。

## BQ Runtime Verification

BQ修正は2022-07-12 Morningで成立している。

- `23880`: `CURRENT_PORTFOLIO_MEMBER`, `position_state_as_of=2022-07-11`, `valuation_as_of=2022-07-11`, `source_market_date=2022-07-11`, `business_date=2022-07-12`
- `94320`: `CURRENT_PORTFOLIO_MEMBER`, `position_state_as_of=2022-07-08`, `valuation_as_of=2022-07-11`, `source_market_date=2022-07-11`, `business_date=2022-07-12`
- `94340`: `CURRENT_PORTFOLIO_MEMBER`, `position_state_as_of=2022-07-11`, `valuation_as_of=2022-07-11`, `source_market_date=2022-07-11`, `business_date=2022-07-12`

`current_position_business_date_mismatch` は再発していない。

Judgment:

- `BQ_CURRENT_POSITION_RUNTIME_PASS = YES`
- `BQ_CARRY_FORWARD_RUNTIME_PASS = YES`
- `BQ_MORNING_STAGE_PASS = YES`

## BR-RQ Answers

BR-RQ1: 2022-07-12 Morning Strategy Planning自体は `NO_ORDER` / `NO_ACTION` のみで、Strategy Planning Authorityは `NO_ORDER_AUTHORIZED`、pending item countは `0`。その後の `sell_planning` stageでPM ADD経路が動き、`94320 BUY 100` の `BUY_ADD` 相当Pendingを生成した。

BR-RQ2: SELL注文pathは未到達。`sell_planning` stageは実行されたが、生成PendingはBUYのみ。`SELL_PATH_REACHED = NO`。

BR-RQ3: Morning artifact本体の不備ではなく、PM ADD Pending producerとSubmit Guard consumerのContract mismatch。PM ADD producerがSubmit Policy AuthorityをPending / Approval / Itemへ伝播していない。

BR-RQ4: BD/BB/BH/BO/BQ系のうち、Opportunity、Safety、Reference Price、Current Position Membership、QuantityはSubmit直前まで成立。BB Submit Policy AuthorityだけがPM ADD経路で未接続。

BR-RQ5: Production-common gap。Historical固有ではなく、Production / DemoでもPM ADD PendingがSubmit Guardへ渡る同じ境界で発生し得る。

## 2022-07-11 vs 2022-07-12

2022-07-11 submitは `23880 BUY 1400` と `94340 BUY 1100` の2件をSubmitし、`submit_policy_consistency=PASS`。

2022-07-12 submitは、Data Readinessでは `94320 BUY 100` のPM ADD Pendingを検出したが、Submit Pipeline上では `missing_submit_policy_evidence` により `REVIEW_REQUIRED`、`submitted_count=0`。

最初の重要差分は、2022-07-12のPM ADD Pendingにcanonical `submit_policy_*` が無いこと。

## Classification

- `SUBMIT_POLICY_AUTHORITY_FAILURE`
- `PRODUCER_CONSUMER_CONTRACT_MISMATCH`
- `PRODUCTION_CONTRACT_VIOLATION`

fail-closedは正しく働いた。

## Trading State Integrity

- no new fill after HALT: YES
- pending state consistent: YES
- cash unchanged after failed submit: YES
- positions unchanged after failed submit: YES
- ledger unchanged after failed submit: YES
- valuation unchanged: YES
- `TRADING_STATE_VALID = YES`
- `ROLLBACK_REQUIRED = NO`
- `STATE_DISCARD_REQUIRED = NO`
- `RESUME_SAFE = NO_UNTIL_REPAIR`
- `FRESH_RERUN_REQUIRED = YES_AFTER_REPAIR`

## Recommended Next Action

`Phase23-BS PM ADD Pending Submit Policy Authority Binding Repair`

最小修正範囲はProduction-commonに、PM ADD Pending writer / promoterでcanonical `submit_policy_context` を `promote_order_plan_to_pending()`、Approval request/artifact、PendingOrderItemへ渡すこと。Strategy Planning Authority経路と同じSubmit Policy Authority契約に揃える。

## Deliverables

- Human: `docs/phase_reports/phase23_br_2022_10bd_post_carry_forward_submit_halt_root_cause_audit.md`
- Machine: `reports/phase_reports/phase23_br_2022_10bd_post_carry_forward_submit_halt_root_cause_audit.json`
- Evidence: `reports/phase23_br_2022_10bd_post_carry_forward_submit_halt_root_cause_audit/`

## Final Gate

- `REPAIR_REQUIRED = YES`
- `READY_FOR_REPAIR = YES`
- `READY_FOR_2022_10BD_RERUN = NO`
