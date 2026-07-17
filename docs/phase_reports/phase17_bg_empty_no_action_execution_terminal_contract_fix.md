# Phase17-BG EMPTY / NO_ACTION Execution Terminal Contract Fix

## 判定

`PHASE17_BG_EMPTY_NO_ACTION_EXECUTION_TERMINAL_CONTRACT_ACCEPTED`

本PhaseではFrozen Runの `run` / `resume` / `rollback` / `reset` / `backup` / `close` は実行していない。`.runtime` のPending / Ledger / Currentは手動変更していない。修正と検証はコード、および `tmp_path` の隔離runtime rootを使うpytestで実施した。

## Root Cause

Phase17-BFでSubmit Pipelineは正式なEMPTY/no-signal Pendingを `PASS / submit_action=NO_ACTION / submitted_count=0` として扱えるようになった。

しかしExecution PipelineはそのSubmit terminal authorityを読まず、Broker ReadOnly snapshotのOrderListを常に必須としていた。そのため、正式に注文0件のDay2であっても `orders=[]` を `orderlist evidence missing` と解釈し、Executionを `REVIEW_REQUIRED` にしていた。

## なぜDay1は通りDay2で露出したか

Day1は実注文あり経路だったため、HistoricalExecutionSnapshotProviderがOrderList/Position/Cash evidenceを生成し、Execution acceptanceが `orderlist_position_cash_evidence_accepted` でPASSした。

Day2はSELL Planningがno-signalとなり、Pendingは `EMPTY / active_pending=false / items=[]`、Submitは `NO_ACTION / submitted_count=0` で正常終了した。注文0件ではOrderListが生成されないため、Execution側の「OrderList常時必須」契約不一致が露出した。

## 変更ファイル

- `src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`
- `tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py`

## 共通Runtime Contract

Execution開始時に、次のauthorityを確認する。

- Pending readerが `valid=true`
- Pending classificationが `EMPTY`
- `active_pending=false`
- `items=[]`
- `target_session_date == business_date`
- `intended_submit_date == business_date`
- `no_action_reason` が正式に存在
- 同じbusiness_dateのSubmit runtime manifestが存在
- Submit manifestが `exit_code=0`
- Submit manifestが `pending_classification=EMPTY`
- Submit manifestが `submit_action=NO_ACTION`
- Submit manifestが `submitted_count=0`
- Submit manifestが `blocked_count=0`
- Submit manifestが `review_required=false`
- Submit manifestが `halt_required=false`
- broker write / production order executed がfalse

この条件が揃う場合、ExecutionはProduction / Demo / Historical共通の注文0件terminal状態として処理する。Historical専用分岐やRuntime Test専用業務ロジックは追加していない。

## NO_ACTION Execution結果

正式なNO_ACTION Executionでは次を返す。

```text
status = PASS
reason = no_submitted_orders
execution_action = NO_ACTION
orderlist_required = false
orderlist_status = NOT_REQUIRED
submitted_order_count = 0
execution_count = 0
fill_count = 0
ledger_orders_appended = 0
ledger_executions_appended = 0
ledger_positions_appended = 0
ledger_cash_appended = 0
ledger_events_appended = 0
current_apply_status = NOT_REQUIRED
runtime_owned_projection_status = NOT_REQUIRED
reconcile_status = NOT_REQUIRED
pending_terminalization_status = ALREADY_TERMINAL
pending_consumed = false
pending_mutated = false
```

NO_ACTION時はBroker ReadOnly snapshot providerを呼ばない。OrderList、Fill、Ledger append、Current applyはいずれも不要で、架空注文・架空約定は生成しない。

## orderlist required / not required

以下を明確に分離した。

- 注文あり、またはEMPTY/NO_ACTION authorityが成立しない場合:
  - `orderlist_required=true`
  - OrderList missingは従来通り `REVIEW_REQUIRED`

- 正式なSubmit NO_ACTION + EMPTY Pendingの場合:
  - `orderlist_required=false`
  - `orderlist_status=NOT_REQUIRED`
  - ExecutionはPASS

## Pending terminalization

EMPTY Pendingはすでに非ACTIVE terminal状態であるため、Executionはconsumeやterminal化を再実行しない。

```text
pending_terminalization_status = ALREADY_TERMINAL
pending_consumed = false
pending_mutated = false
```

## Ledger / Current非変更保証

NO_ACTION Executionでは以下を確認した。

- `orders.jsonl` 追記なし
- `executions.jsonl` 追記なし
- `positions.jsonl` 追記なし
- `cash.jsonl` 追記なし
- `events.jsonl` 追記なし
- `persistent_ledger/state.json` の資産SoTを変更しない
- `runtime_owned_projection_status=NOT_REQUIRED`
- `current_apply_status=NOT_REQUIRED`

Runtime manifestやRun Evidenceは運用証跡であり、資産SoTではない。

## Safety authority整合

今回の直接停止理由はOrderList authorityだった。Execution manifest上のHistorical Safetyは、Data Readinessの `data_readiness_safety_authority` が存在する場合 `_historical_safety_manifest_override()` によりeffective authorityへ上書きされる契約になっている。

Phase17-BGではSafety fail-closedは緩和していない。Production / DemoでSafety artifactが欠落する場合は、Data Readiness / effective safetyがREADYにならず、NO_ACTION Execution authorityだけでSafety欠落を許可する経路は追加していない。

## fail-closed維持

以下は引き続きPASSしない。

- EMPTY Pendingだが `target_session_date` 不一致
- EMPTY Pendingだが `items` が存在
- EMPTY PendingだがSubmit NO_ACTION authorityが存在しない
- Submit NO_ACTION manifestが不整合
- ACTIVE PendingなのにOrderList missing
- 実注文ありなのにOrderList missing
- 実注文あり経路のprojection / Current apply / reconciliation不整合

## Runtime Test Evidence

Phase17-BFで追加したRunner共通収集により、Executionが非ゼロ終了しても `daily/<date>/execution/cli_result.json`、`runtime_manifest.json`、`runtime_log.log` が収集される。Phase17-BGではExecution NO_ACTION用にrun-scoped evidence writerも拡張し、次がRun Evidenceに出る。

- `submitted_order_authority.orderlist_required=false`
- `submitted_order_authority.orderlist_status=NOT_REQUIRED`
- `submitted_order_authority.execution_action=NO_ACTION`
- `historical_fill_authority.fill_count=0`
- `pending_terminalization_evidence.status=ALREADY_TERMINAL`
- `pending_terminalization_evidence.pending_mutated=false`
- `current_apply_evidence.status=NOT_REQUIRED`

## 実行テスト

PASS:

```text
PYTHONPATH=src python3 -m pytest \
  tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py \
  tests/runtime_v2/test_phase17_bf_empty_pending_submit_contract.py \
  tests/runtime_v2/test_phase14e21_execution_readonly_pipeline.py \
  tests/runtime_v2/test_phase14e23_execution_acceptance_policy.py \
  tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py \
  tests/runtime_v2/test_phase14e17_submit_pipeline_connection.py \
  tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py \
  tests/runtime_v2/test_phase15as_data_readiness_semantic_consistency.py \
  -q
```

結果:

```text
45 passed in 2.33s
```

py_compile:

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase17_bg_pycache python3 -m py_compile \
  src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py \
  src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py \
  tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py \
  scripts/runtime_test.py
```

結果: PASS

`git diff --check`: PASS

## 禁止操作未実行

- `scripts/runtime_test.py run`: 未実行
- `scripts/runtime_test.py resume`: 未実行
- `scripts/runtime_test.py reset`: 未実行
- `scripts/runtime_test.py rollback`: 未実行
- `scripts/runtime_test.py backup`: 未実行
- `scripts/runtime_test.py close`: 未実行
- Frozen Run実行: 未実行
- `.runtime` Pending / Ledger / Currentの手動変更: 未実行
- broker write / Tachibana API write: 未実行
- 外部通知送信: 未実行
- J-Quants API fetch: 未実行

## 再テスト方針

対象Run `runtime-test-historical-smoke-20260715T111433056797Z` は、Day1完了、Day2 submitが `exit_code=0`、Day2 executionでHALTしている。Phase17-BF後のSubmit manifestには `submit_action=NO_ACTION` と `submitted_count=0` がRun Evidenceおよびruntime manifestに存在するため、今回の修正後は既存RunをresumeしてDay2 executionから再開可能と判断する。

Codexはresumeを実行していない。ユーザーが実行する場合のコマンド:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py resume \
  --profile historical-smoke \
  --run-id runtime-test-historical-smoke-20260715T111433056797Z \
  --confirm
```

ただし、チーム方針としてClean Smokeを最初から証明する場合は、別途clean baselineからPhase17-BD相当の新規Runを実施する。
