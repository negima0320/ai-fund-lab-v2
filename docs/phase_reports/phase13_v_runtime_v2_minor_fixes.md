# Phase13-V Runtime v2 Minor Fixes / Architecture Guard

## Status

IMPLEMENTED_MINOR_FIXES

Phase13-U Runtime v2 System Reviewで残った軽微なfollow-upを解消し、Runtime v2 skeletonのArchitecture Guardを強化した。

本フェーズではSubmit、Broker注文、Broker API呼び出し、Demo/Production注文、通知送信、Notification send実装、launchd/plist操作、Backtest/Simulation実行、既存Runtime entrypoint呼び出しは行っていない。

## Implemented Scope

### 1. Reconcile fallback policy integration

`run_reconciliation`にfallback source contextを追加し、`source="broker_orders_fallback"`の場合に`check_demo_fallback_policy`が統合reconcile flowで必ず評価されるようにした。

追加入力:

```python
source: str | None = None
production_equivalent: bool | None = None
review_required: bool | None = None
```

確認した挙動:

- production modeで`broker_orders_fallback`を使うと`HALT` findingになる。
- production environmentで`broker_orders_fallback`を使うと`HALT` findingになる。
- `broker_orders_fallback`かつ`review_required=false`は`REVIEW_REQUIRED` findingになる。
- `broker_orders_fallback`かつ`production_equivalent=true`は`REVIEW_REQUIRED` findingになる。
- demo + `review_required=true` + `production_equivalent=false`はfallback policy findingを出さない。

この接続はfinding生成に限定され、Current Asset確定やAsset writer呼び出しは行わない。

### 2. Import graph / cycle guard

ASTベースのArchitecture Guard testを追加した。

確認対象:

- runtime_v2内部の明示的な循環importがないこと。
- `report`がCurrent writer、pending writer、broker submit/APIへ依存しないこと。
- `audit`がsubmit runtimeやbroker APIへ依存しないこと。
- `reconcile`がasset writerやpending writerへ依存しないこと。
- `planning` / `approval`がbroker APIやsubmit runtimeへ依存しないこと。
- `notification.payload`がnotification senderへ依存しないこと。
- runtime_v2がlegacy runtime workflow / entrypointへ依存しないこと。

pure modelやutility importは許容し、責務境界を壊すimport patternだけを禁止対象にしている。

### 3. Derived not Current schema guard

Report / Notification / Audit / ReconciliationがRuntime Current入力やSubmit sourceにならないことをschema/model levelで確認するテストを追加した。

確認対象:

- `ReportArtifact`: `derived=true`, `not_current_state=true`
- `NotificationPayload`: `derived=true`, `not_current_state=true`
- `AuditResult`: `evidence_only=true`, `not_submit_source=true`
- `ReconciliationResult`: `evidence_only=true`, `not_submit_source=true`, `not_current_state=true`, `current_writer=false`

`ReconciliationResult`にはEvidence扱いとCurrent writerではないことを明示する最小属性を追加した。

## Tests Added

- `tests/runtime_v2/test_phase13_v_reconcile_fallback_policy_integration.py`
- `tests/runtime_v2/test_phase13_v_import_graph_cycle_guard.py`
- `tests/runtime_v2/test_phase13_v_derived_not_current_schema_guard.py`

## Validation

```text
python3 -m pytest tests/runtime_v2/test_phase13_v_reconcile_fallback_policy_integration.py
5 passed in 0.06s

python3 -m pytest tests/runtime_v2/test_phase13_v_import_graph_cycle_guard.py
5 passed in 0.19s

python3 -m pytest tests/runtime_v2/test_phase13_v_derived_not_current_schema_guard.py
5 passed in 0.08s

python3 -m pytest -q tests/runtime_v2/
232 passed in 0.58s
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
- ReconcileはCurrentを書き換えていない。
- ReconcileはAsset writerを呼び出していない。

## Completion Criteria

- `broker_orders_fallback` policyは`run_reconciliation`に接続されている。
- Production fallback禁止は統合flowでテストされている。
- import graph / cycle guardは強化されている。
- Derived artifactがCurrent入力にならないschema-level testは追加されている。
- `tests/runtime_v2/`はPASSしている。
- JSONレポートは作成され、`json.tool`で妥当性確認する。

