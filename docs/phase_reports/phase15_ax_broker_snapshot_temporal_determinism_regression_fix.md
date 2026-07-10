# Phase15-AX Broker Snapshot Temporal Determinism Regression Fix

作成日: 2026-07-11

## 目的

Phase15-AWの保持確認で判明したBroker Snapshot freshnessの時間依存Regressionを修正した。

目的はBroker freshness契約を緩めることではない。同じfixtureが、実行した時刻に関係なく、同じ結果になるようにすることである。

## Root Cause

対象事象:

```text
tests/runtime_v2/test_phase15ad_runtime_safety_evaluation_regular_path.py
```

保持確認時、CLI経由のSafety Evaluationで以下が発生した。

```text
BROKER_SNAPSHOT_STALE
```

確認結果:

| Item | Evidence |
|---|---|
| fixture snapshot_at | `2026-07-10T09:00:00+00:00` |
| fixture generated_at | `2026-07-10T09:00:00+00:00` |
| Runtime used now | CLI default system clock |
| max snapshot age | `900` seconds |
| expected status | PASS |
| actual status | REVIEW_REQUIRED / `BROKER_SNAPSHOT_STALE` |

Root Cause分類:

```text
STATIC_OLD_TIMESTAMP_FIXTURE
UNINJECTABLE_SYSTEM_CLOCK
```

Safety evaluation関数自体は `now` injectionを持っていた。一方でCLI通常経路には評価時刻を渡す入口がなく、CLI testでは実行日の現在時刻が使われていた。そのため、同じfixtureでも実行日が進むとBroker snapshot ageが閾値を超えた。

## Clock Injection Contract

CLIへ以下を追加した。

```text
--evaluation-time
```

契約:

- Production defaultは実時刻。
- Tests / Acceptanceではtimezone-aware evaluation timeを明示できる。
- timezoneなし `--evaluation-time` はconfig error。
- Broker snapshot freshness thresholdは変更しない。
- stale snapshotは引き続きREVIEW_REQUIRED。

実装:

- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`
  - `--evaluation-time` を追加。
  - `safety_evaluation` に `now=evaluation_time` を渡す。
  - `safety_refresh` に `now=evaluation_time` を渡す。

## Temporal Foundation利用

Broker snapshot freshness比較をPhase15-AV Temporal Foundationへ追加した。

```text
evaluate_broker_snapshot_freshness()
```

利用箇所:

- `src/ai_fund_lab_v2/runtime_v2/safety/evaluation.py`

保持した契約:

```text
fresh Broker snapshot -> PASS / READY
stale Broker snapshot -> REVIEW_REQUIRED
missing Broker snapshot -> REVIEW_REQUIRED
invalid timestamp -> REVIEW_REQUIRED
timezoneなしtimestamp -> REVIEW_REQUIRED
```

timezoneなしtimestampをUTC扱いする挙動は停止側へ修正した。

## 修正したFixture / Tests

更新:

- `tests/runtime_v2/test_phase15ad_runtime_safety_evaluation_regular_path.py`

追加・修正したRegression:

| Case | Result |
|---|---|
| fixed evaluation time + fresh snapshot | PASS |
| fixed evaluation time + stale snapshot | REVIEW_REQUIRED |
| UTC snapshot / JST evaluation | PASS |
| timezoneなしtimestamp | REVIEW_REQUIRED |
| same fixture + same evaluation time repeated | same result |
| Phase15-AD CLI safety_evaluation -> safety_refresh regular path | PASS |
| Production default clock remains runtime now | PASS |

## Runtime Behavior保持

Broker freshness契約は緩和していない。

禁止された以下は行っていない。

- Broker snapshot age check無効化
- stale threshold拡大
- Production Runtimeの現在時刻固定
- stale snapshotのREADY扱い

## Regression

Target:

```text
python3 -m pytest tests/runtime_v2/test_phase15ad_runtime_safety_evaluation_regular_path.py
```

Result:

```text
16 passed
```

AD / AW:

```text
python3 -m pytest tests/runtime_v2/test_phase15ad_runtime_safety_evaluation_regular_path.py tests/runtime_v2/test_phase15aw_market_quote_evidence_producer.py
```

Result:

```text
26 passed
```

Required retention:

```text
python3 -m pytest tests/runtime_v2/test_phase15ad_runtime_safety_evaluation_regular_path.py tests/runtime_v2/test_phase15aw_market_quote_evidence_producer.py tests/runtime_v2/test_phase15av_runtime_temporal_contract_foundation.py tests/runtime_v2/test_phase15as_data_readiness_semantic_consistency.py tests/runtime_v2/test_phase15aq_runtime_data_readiness_gate.py tests/runtime_v2/test_phase15n_safety_operation_guard_runtime_connection.py tests/runtime_v2/test_phase15r_report_notification_reason_propagation.py
```

Result:

```text
61 passed
```

Compile:

```text
PYTHONPYCACHEPREFIX=/private/tmp/pycache_phase15ax python3 -m compileall src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py src/ai_fund_lab_v2/runtime_v2/safety/evaluation.py src/ai_fund_lab_v2/runtime_v2/temporal tests/runtime_v2/test_phase15ad_runtime_safety_evaluation_regular_path.py
```

Result:

```text
passed
```

## 非実施事項

このPhaseでは以下を行っていない。

- Broker freshness契約の緩和
- stale snapshotの許可
- Market Refresh実運用
- Broker API接続
- Safety実運用
- Current migration
- Current valuation refresh
- Morning
- SELL Planning
- Submit
- Execution
- Broker Write
- 注文
- Notification real send
- launchd変更
- Current直接編集

## 最終判定

```text
PHASE15AX_BROKER_SNAPSHOT_TEMPORAL_DETERMINISM_REGRESSION_FIX_COMPLETE
```
