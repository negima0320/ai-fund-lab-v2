# Phase17-BF EMPTY / No-Signal Pending Submit Contract Fix

## 判定

`PHASE17_BF_EMPTY_PENDING_SUBMIT_CONTRACT_ACCEPTED`

本PhaseではFrozen Runの `run` / `resume` / `rollback` / `reset` / `backup` / `close` は実行していない。`.runtime` のPending / Ledger / Currentを手動変更していない。修正と検証はコード、および `tmp_path` の隔離runtime rootを使うpytestで実施した。

## Root Cause

Phase17-BEで特定した通り、`read_pending_order_plan_path()` は正式なEMPTY Pendingを以下のように返していた。

```text
valid = true
classification = EMPTY
plan = null
errors = ()
```

一方、Submit Pipelineは `plan is None` を一律invalidとしてBLOCKEDにしていた。

```python
if not pending_read.valid or pending_read.plan is None:
```

そのため、Data ReadinessがREADYと判断した正式なno-signal Pendingが、Submit Pipelineで異常Pendingとして扱われ、CLI `EXIT_BLOCKED = 10` に到達していた。

## 修正内容

### Submit Pipeline

対象: `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`

`PendingOrderPlanReadResult.classification` をSubmit Pipelineが正式に解釈するようにした。

- `valid == false`: 従来どおりBLOCKED
- `classification == "EMPTY"`: EMPTY/no-signal contractを追加検証し、整合していれば注文0件の正常terminal状態としてPASS
- `classification != "EMPTY" and plan is None`: active Pending plan欠落としてBLOCKED
- active Pending: 従来のSubmit処理を継続

EMPTY/no-signalとして正常扱いする条件:

- `active_pending == false`
- `environment == mode`
- `state/status == EMPTY`
- `items == []`
- `approved_item_ids == []`
- `no_action_reason` が正式に記録されている
- `target_session_date == business_date`
- `intended_submit_date == business_date`
- `safety_context.safety_decision` が存在

EMPTY正常系のSubmit結果:

```text
status = PASS
reason = pending_empty_no_action
submit_action = NO_ACTION
submitted_count = 0
blocked_count = 0
review_required = false
halt_required = false
demo_submit_executed = false
```

### Manifest / Evidence

対象: `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`

Submit manifestのトップレベル、および `runtime_v2_submit_pipeline` stage detailsに以下を記録するようにした。

- `pending_read_valid`
- `pending_classification`
- `pending_active`
- `pending_plan_present`
- `pending_item_count`
- `no_action_reason`
- `submit_action`
- `submitted_count`
- `blocked_count`
- `review_required`
- `halt_required`
- `reason`

Submit結果が存在しない非Submit jobでは、既存Data Readiness等の同名フィールドを上書きしない。

### Runtime Test Evidence収集

対象: `scripts/runtime_test.py`

Phase17-BEで見えた `daily/<date>/submit` 欠落は、Submit CLIがmanifest/logを生成していなかったためではなく、Runner側にjob共通のmanifest/log収集処理がなかったことが原因だった。CLI stdoutにはmanifest pathが出ていたため、Runnerで以下を追加した。

- 各job subprocess終了直後、exit codeに関係なく `daily/<business_date>/<job>/cli_result.json` を作成
- CLI stdoutのmanifest pathを読み取り、存在すれば `runtime_manifest.json` としてコピー
- manifestの `run_id` からruntime logを解決し、存在すれば `runtime_log.log` としてコピー
- 非ゼロ終了時も、HALT例外を投げる前に収集

これにより、将来のBLOCKED / REVIEW_REQUIRED / HALTでも、Run Evidence配下から停止jobのmanifest/logを確認できる。

## Production / Demo / Historical共通性

EMPTY/no-signal Pendingの解釈はSubmit Pipelineの共通コードに実装した。Historical専用if、Runtime Test専用業務ロジック、Smoke専用例外は追加していない。

環境差は既存どおりBroker adapter / broker write可否 / historical adapter確認に限定される。EMPTY/no-signalの場合はProduction/Demo/Historicalいずれでも注文送信を行わないterminal状態として扱う。ただし現行RuntimeではProduction submit自体に既存のPhase14-E17制約が残るため、本PhaseではProduction broker write許可条件は拡張していない。

## Fail-Closed維持

以下は引き続きBLOCKEDまたはREVIEW_REQUIREDとなる。

- `valid == false`
- malformed schema
- `classification != EMPTY` かつ `plan is None`
- EMPTYなのに `active_pending == true`
- EMPTYなのにitemsが存在
- no-action/no-signal理由欠落
- target/intended submit date mismatch
- safety authority欠落
- policy missing
- approval/policy/safety guard mismatch
- broker write scope mismatch
- unresolved order condition

## Broker Writeなしの証拠

EMPTY正常系テストでは以下を確認した。

- `demo_submit_executed == false`
- `submitted_count == 0`
- `persistent_ledger/orders.jsonl == []`
- Pending JSONは実行前後で不変
- CLI manifest `prohibited_actions.demo_submit_executed == false`

## Runtime Test Evidence収集の調査結果

現行Runnerは成功時のみ収集していたのではなく、そもそもjob共通のCLI manifest/log収集がなかった。`run_daily_operation.py` にはmorning/sell_planning/execution/current_valuation_refresh向けの個別Evidence writerがあるが、submit向けは存在しなかった。

今回、Runnerに共通収集を追加したため、個別writerがないjobでも `cli_result.json`、`runtime_manifest.json`、`runtime_log.log` がRun Evidence配下に残る。

## 実行テスト

PASS:

```text
PYTHONPATH=src python3 -m pytest \
  tests/runtime_v2/test_phase17_bf_empty_pending_submit_contract.py \
  tests/runtime_v2/test_phase14e17_submit_pipeline_connection.py \
  tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py \
  tests/runtime_v2/test_phase15bn_isolated_normal_submit_scenario.py \
  tests/runtime_v2/test_phase15as_data_readiness_semantic_consistency.py \
  tests/runtime_v2/test_phase17_ag_day2_sell_planning_integration.py \
  tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py \
  tests/runtime_v2/test_phase15m_sell_broker_available_quantity_evidence.py \
  tests/runtime_v2/test_phase15bm_safety_blocked_submit_path.py::test_phase15bm_safety_blocked_submit_path_never_calls_broker_or_consumes_pending \
  tests/runtime_v2/test_phase15bm_safety_blocked_submit_path.py::test_phase15bm_safety_blocked_retry_is_idempotent \
  tests/runtime_v2/test_phase15bm_safety_blocked_submit_path.py::test_phase15bm_fail_closed_for_missing_stale_expired_and_action_scope_missing \
  tests/runtime_v2/test_phase15bm_safety_blocked_submit_path.py::test_phase15bm_broker_write_scope_missing_fails_closed \
  tests/runtime_v2/test_phase15bm_safety_blocked_submit_path.py::test_phase15bm_order_condition_unresolved_blocks_submit_before_broker \
  -q
```

結果:

```text
57 passed in 2.68s
```

py_compile:

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase17_bf_pycache python3 -m py_compile \
  src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py \
  src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py \
  scripts/runtime_test.py \
  tests/runtime_v2/test_phase17_bf_empty_pending_submit_contract.py
```

結果: PASS

補足: `python3 -m py_compile ...` を通常実行するとmacOSのユーザーCache配下への `.pyc` 書き込みでPermissionErrorになったため、`PYTHONPYCACHEPREFIX=/private/tmp/phase17_bf_pycache` を指定して再実行した。

## 既知の非対象テスト

広めの確認で `tests/runtime_v2/test_phase15n_safety_operation_guard_runtime_connection.py` の2件が `exit_code=20` となった。manifest確認の結果、原因は現行Data Readiness契約で必要なCurrent/Market/Pending fixture不足であり、本PhaseのSubmit EMPTY修正経路ではない。

また `tests/runtime_v2/test_phase15bm_safety_blocked_submit_path.py::test_phase15bm_isolated_fixture_does_not_modify_existing_runtime_root` は、実 `.runtime` 内の特定apply candidate存在を前提にしており、Frozen Run不変方針と相性が悪いため本Phaseの隔離fixture検証から除外した。

## Frozen Run未変更

禁止操作は実施していない。

- `runtime_test.py run`: 未実行
- `runtime_test.py resume`: 未実行
- `runtime_test.py rollback`: 未実行
- `runtime_test.py reset`: 未実行
- `runtime_test.py backup`: 未実行
- `runtime_test.py close`: 未実行
- broker write / Tachibana API write / 外部通知: 未実行

検証はpytestの `tmp_path` 隔離runtime rootで実施した。
