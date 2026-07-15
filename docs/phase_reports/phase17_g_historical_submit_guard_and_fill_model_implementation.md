# Phase17-G Historical Submit Guard And Fill Model Implementation

## Final Judgment

`PHASE17_G_HISTORICAL_SUBMIT_AND_FILL_MODEL_ACCEPTED`

Recommended next prefix: `Phase17-H`

Recommended next work name: `Historical Runtime 5BD Final Entry Gate and Execution Preparation`

## 1. 読み込んだ資料

- Phase17-G attachment
- Phase17-F conclusion: `PHASE17_F_LIMITED_RUNTIME_CORE_AMENDMENT_ACCEPTED`
- `docs/02_architecture/historical_runtime_test_contract.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/operational_lifecycle_state_reset_and_environment_transition_contract.md`
- Runtime Submit Guard / Pending / Approval / Policy / Safety / Execution Processor implementation

## 2. 実装範囲

Phase17-F で承認された限定 Runtime Core amendment を実装した。

- Submit Guard Environment Matrix
- `SubmitEnvironmentGuardContext`
- Historical broker capability
- `HistoricalSubmitAdapter`
- `HistoricalExecutionSnapshotProvider`
- Historical mode path validation
- Runtime CLI environment composition wiring
- Isolated unit / contract tests

作成していないもの:

- Historical-only Runtime
- Historical-only Feature Producer
- Historical-only Current
- Historical-only Ledger
- Historical-only Pending
- Historical-only State Machine

## 3. Runtime Mainline Preservation

Historical submit は `run_submit_pipeline -> run_submit_preflight -> HistoricalSubmitAdapter` の順に通る。Approval、Policy、Safety、Pending、Duplicate、Temporal、BUY cash、SELL quantity guard は通常 Submit Guard のまま維持した。

Execution は `HistoricalExecutionSnapshotProvider` が Runtime-compatible snapshot を出し、通常 Execution Processor に渡す。

## 4. Submit Guard Environment Matrix

| Environment | Pending | Broker | Adapter | Broker Write | 判定 |
|---|---|---|---|---:|---|
| Demo | `demo` | `tachibana_demo` | Demo adapter | true | 既存 Demo guard |
| Historical | `historical` | `historical_simulated` | `HistoricalSubmitAdapter` | false | common guard 後に許可 |
| Production | `production` | `tachibana_production` | Production adapter | explicit acceptance | acceptance なし fail closed |

Evidence: `reports/phase17_g_historical_submit_guard_and_fill_model_implementation/submit_guard_environment_matrix_contract.json`

## 5. Historical External Effect Blocking

Historical は `broker_write=false`、`external_delivery=false`、`broker_api_called=false`、`raw_request_saved=false`、`raw_response_saved=false`、`secret_saved=false` として実装した。

`broker_write=false` は外部 Broker write 禁止であり、Runtime mainline 停止ではない。

## 6. Historical Fill Price

5BD smoke 限定で以下を accepted とした。

- Market order のみ
- `target_session_date == business_date`
- fill time: `09:00:00+09:00`
- fill price: Canonical normalized OHLCV `Open`
- PIT manifest の `ohlcv_normalized` hash と source parquet hash を照合
- Listed Issues PIT universe membership を確認
- raw OHLCV `AdjFactor == 1.0` の場合のみ Corporate Action no-impact として通す
- duplicate evidence path が存在すれば block

Limit order、fees、tax、slippage、partial fill は 20BD 以降。

## 7. Lot / Trading Unit

判定: `ACCEPTED_EXISTING_RUNTIME_QUANTITY_AUTHORITY`

理由:

- Pending quantity と Approval order conditions が数量を固定する。
- Submit Guard が BUY cash / SELL owned quantity / available quantity を確認する。
- BrokerCapability が supported symbol / mode の authority を持つ。
- `listed_info.trading_unit` が存在する場合のみ adapter が倍数を確認する。
- `listed_info` に trading unit がない場合、無条件 100 株 rule は作らない。

## 8. Historical Submit Adapter

`HistoricalSubmitAdapter` は:

- environment が `historical` でない場合 fail closed
- business date / evaluation time 欠落で `HALT`
- market data / PIT / CA guard 不一致で `HALT`
- limit order は `REVIEW_REQUIRED`
- accepted submit は deterministic order / execution identity と evidence JSON を生成
- duplicate evidence は block

## 9. Historical Execution Snapshot Provider

Accepted historical submission evidence から Runtime-compatible snapshot を生成する。snapshot は orders、executions、positions、buying_power を含み、`simulation=true`、`historical_replay=true`、`broker_write=false` を明示する。

## 10. Runtime CLI

`run_daily_operation` に `--mode historical` と `--broker-environment` を追加し、Historical composition を manifest に出すようにした。

Historical mode は `--business-date`、`--evaluation-time`、`--notification-mode payload-only`、`broker_environment=historical_simulated` を要求する。

## 11. Path Resolver

`historical` を正式 mode/environment として validator に追加した。ただし Current object path は `.runtime/...` のままで、`.runtime/historical/...` は作らない。

## 12. Contract 更新

- `runtime_architecture_v2.md`: Submit Guard Environment Matrix と Phase17-G fill model を追補。
- `historical_runtime_test_contract.md`: 5BD smoke 限定 accepted fill model を追補。
- `operational_lifecycle_state_reset_and_environment_transition_contract.md`: Historical lifecycle isolation と fail-closed 条件を追補。

## 13. 実行した検証

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase17_g_pycache PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py tests/runtime_v2/test_phase17_b1i_a_historical_environment_composition.py tests/runtime_v2/test_phase14d3_pure_submit_path.py tests/runtime_v2/test_phase15bm_safety_blocked_submit_path.py tests/runtime_v2/test_phase14e17_submit_pipeline_connection.py tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py
```

Result:

```text
38 passed in 1.74s
```

## 14. Acceptance Gate

| Gate | Result |
|---|---|
| Runtime Mainline preserved | PASS |
| Submit Guard Environment Matrix | PASS |
| Historical external effect blocking | PASS |
| Historical fill price authority | PASS |
| Lot / trading unit authority | PASS |
| Duplicate submit guard | PASS |
| Safety block before adapter | PASS |
| Execution processor compatibility | PASS |
| Demo regression | PASS |
| Production boundary | PASS |
| Contract update | PASS |

## 15. 実行していない操作

- 5BD Historical Runtime execution
- Trading State Reset
- normal `.runtime` Current / Ledger / Pending / Runtime State mutation
- Feature generation
- Canonical update
- J-Quants fetch
- Tachibana API access
- Demo submit
- Production access

## 16. Blocking

なし。

## 17. Non-blocking

- fees / tax / slippage / partial fill は 20BD 以降。
- limit-order execution rule は別 acceptance。
- official long-term performance execution model は 1-Year / Full 前に別途必要。

## 18. 作成・更新ファイル

Code:

- `src/ai_fund_lab_v2/runtime_v2/submit/models.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/guards.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/historical_support/environment.py`
- `src/ai_fund_lab_v2/runtime_v2/broker_adapter/capability.py`
- `src/ai_fund_lab_v2/runtime_v2/storage/path_resolver.py`
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`

Tests:

- `tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py`
- `tests/runtime_v2/test_phase17_b1i_a_historical_environment_composition.py`

Reports:

- `reports/phase_reports/phase17_g_historical_submit_guard_and_fill_model_implementation.json`
- `reports/phase17_g_historical_submit_guard_and_fill_model_implementation/*.json`

## 19. Final

`PHASE17_G_HISTORICAL_SUBMIT_AND_FILL_MODEL_ACCEPTED`
