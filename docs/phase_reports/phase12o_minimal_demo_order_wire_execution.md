# Phase12-O Minimal Demo Order Wire Execution

## Status

`PHASE12O_MINIMAL_DEMO_ORDER_WIRE_EXECUTION_BLOCKED_BY_GUARD`

Phase12-Oでは、Demo注文wire execution実装を追加し、Phase12-M/Phase12-Nで確認したBUY itemを最小Demo注文用に正規化した。

ただし、実行許可条件の1つである`TACHIBANA_API_SECOND_PASSWORD_FILE`がruntime環境で未設定だったため、Demo注文はfail closedで停止した。

`CLMKabuNewOrder`は呼んでいない。Demo注文、Production注文、Production Unlock、LINE実送信、AI再学習、Backtest再実行も行っていない。

## Changed Files

- `src/ai_fund_lab_v2/broker/allowlist.py`
- `src/ai_fund_lab_v2/broker/transport.py`
- `src/ai_fund_lab_v2/broker/secrets.py`
- `src/ai_fund_lab_v2/broker/tachibana_order_request.py`
- `src/ai_fund_lab_v2/broker/demo_order.py`
- `src/ai_fund_lab_v2/operations/operations.py`
- `tests/phase12/test_demo_order_wire_unlock_guards.py`
- `docs/phase_reports/phase12o_minimal_demo_order_wire_execution.md`
- `reports/phase_reports/phase12o_minimal_demo_order_wire_execution.json`

## BUY Item Normalization

Before:

| Field | Value |
| --- | --- |
| item_id | `buy_2026-06-29_92560_001` |
| code | `92560` |
| side | `BUY` |
| quantity | `100` |
| order_type | `CASH_EQUITY` |
| price_type | `LIMIT` |
| limit_price | `0` |
| expected_notional | `0` |

After:

| Field | Value |
| --- | --- |
| limit_price | `5410` |
| expected_notional | `541000` |
| estimated_value | `541000` |
| source | `jquants_latest_close` |

正規化価格は、J-Quants normalized daily quotesの`2026-06-26`最新Closeから取得した。Broker SnapshotやLedgerはAI学習・価格正規化入力に使っていない。

## Approval

Phase12-O用に本線Approval artifactを明示作成した。

```text
status=APPROVED
approval_id=operation_approval_2026-06-29_bb40f1681a3c
approved_item_ids includes buy_2026-06-29_92560_001
approved_sides includes BUY
demo_order_allowed=true
production_order_allowed=false
max_notional=600000
actual_expected_notional=541000
approval_max_notional_pass=true
```

## Safety / MAX_EXPOSURE / Buying Power

Safety result:

```text
status=ALLOW
system_guard=true
```

MAX_EXPOSURE:

```text
base_equity=20000000
basis=broker_actual_equity_or_buying_power
current_exposure=0
projected_exposure=541000
max_allowed_exposure=17000000
max_total_exposure_ratio=0.85
decision=ALLOW
```

Buying power:

```text
buying_power=20000000
actual_expected_notional=541000
buying_power_pass=true
```

## Demo-only Wire Boundary

追加した境界:

- read-only allowlistは維持
- `CLMKabuNewOrder`はread-only transportでは引き続き禁止
- demo-order-only `ensure_demo_order_clmid(...)`を追加
- `DemoOrderBrokerTransport`は以下が揃わないとfail closed
  - environment=`demo`
  - demo base URL
  - `demo_order_wire_execution=true`
  - `production_order_allowed=false`
  - CLMID=`CLMKabuNewOrder`

Production環境では必ずfail closed。

## Second Password Boundary

既存の`TachibanaSecretLoader.classify_second_password_file()`はpresence分類のみを継続する。

追加した値ロード境界:

```text
TachibanaSecretLoader.load_second_password_value_for_demo_order_only()
```

これはDemo注文adapter内のfinal request assembly直前でのみ使う。値はartifact、stdout、logに保存しない。

今回の実行ではpreflightで以下を検出した。

```text
status=REVIEW_REQUIRED
reason=required_env_missing
missing=TACHIBANA_API_SECOND_PASSWORD_FILE
```

このため、`run_demo_submit.py --execute-demo-order`は`BLOCKED_SECOND_PASSWORD_MISSING`で停止した。

## Wire Execution Result

```text
execute_demo_order_requested=true
submit_status=BLOCK
item_status=BLOCKED_SECOND_PASSWORD_MISSING
broker_order_api_called=false
clm_kabu_new_order_called=false
demo_order_submitted=false
production_order_submitted=false
raw_request_saved=false
raw_response_saved=false
secret_saved=false
```

## Post-submit Runtime Results

注文は送信されていないため、post-submit read-only refreshは実施していない。既存Broker read-only artifact上では以下。

```text
orders_count=0
executions_count=0
positions_count=0
buying_power=20000000
```

後続CLI:

| Step | Result |
| --- | --- |
| Fill Monitor | `PASS`, lifecycle=`REJECTED` |
| Safety Monitor | `PASS` |
| Reconcile | `PASS` |
| Daily Report | `BLOCK`, current submit guard block |
| Operation Audit | `PASS` |

Daily Reportの`BLOCK`はstale artifactではなく、今回の現在runのsubmit guard blockを正しく反映している。

## Tests

```bash
python3 -m pytest tests/phase12/test_demo_order_wire_unlock_guards.py -q
python3 -m pytest tests/phase12/test_demo_order_wire_unlock_guards.py tests/broker/test_broker_allowlist.py tests/broker/test_mock_transport.py tests/broker/test_tachibana_order_request_builder.py -q
PYTHONPYCACHEPREFIX=.runtime/operations/pycache_phase12o python3 -m py_compile ...
python3 -m json.tool reports/phase_reports/phase12o_minimal_demo_order_wire_execution.json
```

Results:

- Demo order guard tests: `7 passed`
- Targeted broker guard tests: `20 passed`
- py_compile: PASS
- JSON validation: PASS

## Blocking Issues

- `TACHIBANA_API_SECOND_PASSWORD_FILE`がruntime環境で未設定
- second password final boundaryが成立しないため、Demo order wire executionは実行不可
- `CLMKabuNewOrder`は呼ばれていない

## Remaining Gaps

1. `TACHIBANA_API_SECOND_PASSWORD_FILE`を安全に設定する
2. `run_preflight.py`でrequired env PASSを確認する
3. `run_demo_submit.py --execute-demo-order`を再実行する
4. 実送信後にBroker read-only orders / executions / positions / buying_powerを再取得する
5. Fill Monitor / Safety Monitor / Reconcile / Daily Report / Auditを再実行する

## Next Phase

`PHASE12-P_SECOND_PASSWORD_CONFIGURED_DEMO_WIRE_RETRY`

次はsecond password file設定後、同じguard付きwire pathで最小Demo注文を再試行する。
