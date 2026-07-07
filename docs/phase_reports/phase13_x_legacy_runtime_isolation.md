# Phase13-X Legacy Runtime Isolation / Writer Contract Fix

## Status

IMPLEMENTED

Phase13-Wで残ったCurrent Writer Contractの差異を解消し、Runtime v2からLegacy Runtimeへの依存がないことをArchitecture Guardで固定した。

本フェーズではSubmit、Broker注文、Broker API呼び出し、Demo/Production注文、通知送信、Notification send実装、launchd/plist操作、Backtest/Simulation実行、既存Runtime entrypoint呼び出しは行っていない。

## Writer Contract Fix

`persistent_ledger/state.json` のwriter contractから`Reconciliation Runtime`を外し、`Asset Runtime`をsingle writerとして固定した。

Current Writerは以下に整理した。

| Current | Single Writer |
| --- | --- |
| `runtime_state/current_state.json` | Runtime State Runtime |
| `pending_order_plan/pending_order_plan.json` | Pending Runtime |
| `persistent_ledger/orders.jsonl` | Ledger Runtime |
| `persistent_ledger/executions.jsonl` | Ledger Runtime |
| `persistent_ledger/positions.jsonl` | Ledger Runtime |
| `persistent_ledger/cash_history.jsonl` | Ledger Runtime |
| `persistent_ledger/events.jsonl` | Ledger Runtime |
| `persistent_ledger/state.json` | Asset Runtime |
| `notification_delivery/delivery_ledger.jsonl` | Notification Runtime |

Reconcile RuntimeはCurrent Writerではない。責務はRead、Compare、Finding、ReviewRequired、Evidenceに限定する。

## Single Writer Rule

追加したArchitecture Guardにより、以下を確認している。

- 各Current contractはwriterを1つだけ持つ。
- Current path object typeは重複しない。
- owner componentはsingle writerと一致する。
- Reconciliation Runtime、Report Runtime、Report Builder、Audit RuntimeはCurrent writerではない。
- Asset Runtimeだけが`persistent_ledger/state.json` writerである。
- Ledger Runtimeはappend-only ledgerのwriterである。

## Atomic Writer Contract

Current更新順序は以下に固定する。

```text
Ledger append
↓
Asset rebuild
↓
persistent_ledger/state.json
↓
Report
↓
Notification Payload
```

禁止確認:

- ReportからCurrent更新しない。
- ReconcileからCurrent更新しない。
- AuditからCurrent更新しない。
- ReconcileはAsset writerもPending writerも呼ばない。

## Legacy Runtime Isolation

runtime_v2 packageから以下への直接依存がないことをASTベースのテストで確認した。

- legacy workflow
- legacy entrypoint
- legacy resolver
- legacy submit
- legacy report
- legacy current
- `demo_ledger`
- `ai_fund_lab_v2.runtime`
- `ai_fund_lab_v2.operations`
- `ai_fund_lab_v2.broker`

## Tests Added

- `tests/runtime_v2/test_phase13_x_writer_contract.py`
- `tests/runtime_v2/test_phase13_x_legacy_runtime_isolation.py`
- `tests/runtime_v2/test_phase13_x_no_current_writer_conflict.py`
- `tests/runtime_v2/test_phase13_x_atomic_writer_contract.py`

## Validation

```text
python3 -m pytest tests/runtime_v2/test_phase13_x_writer_contract.py
4 passed in 0.04s

python3 -m pytest tests/runtime_v2/test_phase13_x_legacy_runtime_isolation.py
3 passed in 0.07s

python3 -m pytest tests/runtime_v2/test_phase13_x_no_current_writer_conflict.py
4 passed in 0.03s

python3 -m pytest tests/runtime_v2/test_phase13_x_atomic_writer_contract.py
4 passed in 0.04s

python3 -m pytest -q tests/runtime_v2/
247 passed in 0.66s
```

## Safety Confirmation

- Submitは実行していない。
- Broker注文は実行していない。
- Broker APIは呼び出していない。
- Demo注文は実行していない。
- Production注文は実行していない。
- 通知送信は実行していない。
- Notification send実装は追加していない。
- launchd再開は行っていない。
- 既存plist削除は行っていない。
- 新規plist作成は行っていない。
- Backtestは実行していない。
- Simulationは実行していない。
- 既存Runtime workflowは継承していない。
- 既存Runtime entrypointは呼び出していない。

## Completion Criteria

- Writer Contractは一意になっている。
- Current Writer競合はない。
- Reconcile RuntimeはCurrent Writerではない。
- Asset Runtimeだけが`persistent_ledger/state.json` writerである。
- Ledger Runtimeはappend-onlyである。
- Legacy Runtime依存はruntime_v2から隔離されている。
- Writer Contract TestsはPASSしている。
- runtime_v2全体テストはPASSしている。
- JSONレポートは作成され、`json.tool`で妥当性確認する。

