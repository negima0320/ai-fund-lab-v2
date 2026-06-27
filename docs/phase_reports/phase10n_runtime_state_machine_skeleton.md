# Phase10-N Runtime Foundation Skeleton

- status: IMPLEMENTED_REVISED
- created_at: 2026-06-27
- revised_at: 2026-06-28
- scope: runtime foundation only
- broker_api_connected: false
- demo_order_submitted: false
- production_order_submitted: false
- paper_ledger_updated: false
- broker_snapshot_updated: false

## 1. Summary

Phase10-N を Production Runtime の実行基盤として再整理した。

Phase10-N の責務:

```text
動かすための基盤
```

Phase11 の責務:

```text
安全に動かすための基盤
```

この改訂で Runtime と Safety の責務を分離し、Phase10-N から Safety Layer に属する placeholder を削除した。

## 2. Implemented Runtime Foundation

追加・更新した runtime package:

```text
src/ai_fund_lab_v2/runtime/
```

実装対象:

- Runtime State Machine
- Runtime Context
- Runtime Manifest
- Runtime Result
- Transition Validator
- Scheduler Interface
- Runtime Mode
  - Paper
  - Demo
  - Production
- Order Executor Interface
- Broker Runtime Interface
- Run Lock
- Business Day Guard
- Immutable Run Manifest

実装しないもの:

- Broker API 接続
- Demo 注文
- Production 注文
- Paper Ledger 更新
- Broker Snapshot 更新
- Scheduler 起動
- LaunchAgent
- AI 処理
- Order Manager 本体
- Fill Monitor 本体

## 3. Implemented Files

追加:

```text
src/ai_fund_lab_v2/runtime/runtime_mode.py
src/ai_fund_lab_v2/runtime/states.py
src/ai_fund_lab_v2/runtime/runtime_context.py
src/ai_fund_lab_v2/runtime/runtime_manifest.py
src/ai_fund_lab_v2/runtime/runtime_result.py
src/ai_fund_lab_v2/runtime/runtime_errors.py
src/ai_fund_lab_v2/runtime/transition_validator.py
src/ai_fund_lab_v2/runtime/state_machine.py
src/ai_fund_lab_v2/runtime/scheduler_interface.py
src/ai_fund_lab_v2/runtime/order_executor_interface.py
src/ai_fund_lab_v2/runtime/broker_runtime_interface.py
src/ai_fund_lab_v2/runtime/run_lock.py
src/ai_fund_lab_v2/runtime/business_day_guard.py
tests/runtime/test_runtime_state_machine.py
```

更新:

```text
src/ai_fund_lab_v2/runtime/__init__.py
```

`RuntimePaths` の既存 export は保持した。

削除:

```text
src/ai_fund_lab_v2/runtime/safety.py
```

## 4. State Enum

実装した state:

```text
PREOPEN
ORDER_PREPARED
ORDER_SUBMITTED
WAITING_FILL
PARTIALLY_FILLED
FILLED
MONITORING
CLOSE_VALUATION
NIGHTLY_INFERENCE
REPORT_READY
HALT
```

Phase10-N から除外した state:

```text
SAFETY_CHECKED
EMERGENCY_STOP
```

これらは Safety Layer の責務に属するため、Phase11 で必要に応じて独立した Safety State Machine として扱う。

## 5. Transition Rules

正常系:

```text
PREOPEN
ORDER_PREPARED
ORDER_SUBMITTED
WAITING_FILL
FILLED
MONITORING
CLOSE_VALUATION
NIGHTLY_INFERENCE
REPORT_READY
```

Partial fill:

```text
WAITING_FILL -> PARTIALLY_FILLED -> FILLED
WAITING_FILL -> PARTIALLY_FILLED -> MONITORING
```

Unknown:

```text
unknown state -> HALT
unknown target -> HALT
```

Invalid transition:

```text
status=BLOCKED
current state is kept
```

Phase10-N は Safety 判定を持たない。Safety による停止、緊急停止、復旧判断は Phase11 に分離する。

## 6. Runtime Context / Mode

`RuntimeContext` は以下を持つ。

```text
environment
runtime_mode
business_date
evaluation_cash
broker_actual_cash
broker_snapshot_path
paper_ledger_path
paper_test_id
runtime_id
created_at
```

Runtime Mode:

```text
paper
demo
production
```

Paper / Demo / Production は同じ `RuntimeStateMachine` を利用する。Order Executor は interface として分離し、Phase10-O 以降で差し替える。

## 7. Interfaces

Scheduler Interface:

```text
preopen()
order_prepare()
submit()
fill_check()
monitor()
close()
nightly()
report()
```

Order Executor Interface:

```text
prepare(context, order_plan)
submit(context, prepared_order)
status(context, order_ref)
```

Broker Runtime Interface:

```text
preopen_snapshot(context)
order_status(context)
fill_status(context)
position_snapshot(context)
close_snapshot(context)
```

これらは Protocol のみで、実処理は持たない。

## 8. Run Lock / Business Day Guard

Run Lock:

- runtime_id
- business_date
- locked
- owner
- reason

現時点では in-memory store のみを実装し、ファイル出力は行わない。

Business Day Guard:

- weekday は business day
- weekend は skip
- 明示 holiday set は skip

取引所カレンダー連携は後続フェーズで差し替える。

## 9. Manifest Schema

`RuntimeManifest` と `RuntimeTransitionManifest` を追加した。

現時点では schema のみで、ファイル出力は行わない。

Immutable run manifest flags:

```text
immutable=true
broker_api_called=false
demo_order_submitted=false
production_order_submitted=false
paper_ledger_updated=false
broker_snapshot_updated=false
ai_learning_updated=false
backtest_run=false
```

## 10. Phase11 Handoff

Phase11 に移動したもの:

- Safety Manager
- Safety State Machine
- Emergency Stop
- Hourly Position Monitor
- -7 percent Warning
- -10 percent Stop Loss Candidate
- -15 percent Emergency Candidate
- Duplicate Order Guard
- Broker Divergence Guard
- Quote Stale Guard
- Cash Buffer Guard
- Daily Loss Guard
- Recovery
- Safety Report

Phase10-N はこれらの placeholder を持たない。

## 11. Test Coverage

対象 pytest:

```text
PYTHONPATH=src python3 -m pytest tests/runtime/test_runtime_state_machine.py tests/broker/test_broker_runtime_paths.py -q
```

結果:

```text
13 passed
```

確認した項目:

- normal transition path
- partial fill path
- invalid transition blocked
- unknown state to HALT
- unknown target to HALT
- Paper / Demo / Production shared runtime
- manifest no-mutation flags
- Phase11 safety states are absent
- run lock conflict
- run lock release
- business day guard
- existing `RuntimePaths` export compatibility

## 12. Verification

```text
JSON validation: PASS
secret canary: PASS
forbidden CLMID audit: PASS
runtime/safety separation scan: PASS
no runtime mutation confirmation: PASS
```

## 13. Completion Criteria

Phase10-N revised completion criteria:

- Runtime Foundation が実装されている。
- Paper / Demo / Production が同じ Runtime State Machine を利用できる。
- Order Executor Interface を後続フェーズで差し込める。
- Broker Runtime Interface を後続フェーズで差し込める。
- Run Lock と Business Day Guard の基盤がある。
- Immutable Run Manifest schema がある。
- Safety Layer に属する placeholder が Phase10-N に存在しない。
- Broker API / order / ledger / snapshot / AI / backtest の副作用がない。

判定:

```text
IMPLEMENTED_REVISED
```

次に進める状態:

```text
Phase10-O demo order design / no production
```

