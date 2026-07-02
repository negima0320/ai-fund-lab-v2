# Phase12-S RequestSequenceManager + Persistent Demo Ledger + BUY Retry

## Status

`PHASE12S_BUY_RETRY_REJECTED_BY_BROKER`

Phase12-Sでは、Phase12-Rで特定した`p_no` sequence issueに対して、session-scoped shared counterを追加し、Persistent Demo Ledgerを実装した。その後、guardを満たしたため、立花証券Demo環境でBUY wire retryを1回実行した。

BUY retryは`CLMKabuNewOrder`まで到達したが、Broker側でrejectされた。今回はPhase12-Qの`p_no` errorではなく、第二暗証番号フィールド/値に関するredacted classification:

```text
SECOND_PASSWORD_FIELD_OR_VALUE_ERROR
p_errno=-1
```

として保存した。Broker error text本文はredaction auditのため保存していない。

BUYはaccepted / filledされなかったため、SELL lifecycleには進んでいない。

## Changed Files

- `src/ai_fund_lab_v2/broker/request_sequence.py`
- `src/ai_fund_lab_v2/broker/request_builder.py`
- `src/ai_fund_lab_v2/broker/tachibana_order_request.py`
- `src/ai_fund_lab_v2/broker/demo_order.py`
- `src/ai_fund_lab_v2/operations/demo_ledger.py`
- `src/ai_fund_lab_v2/operations/operations.py`
- `tests/broker/test_tachibana_request_sequence_manager.py`
- `tests/phase12/test_persistent_demo_ledger.py`
- `docs/phase_reports/phase12s_request_sequence_demo_ledger_buy_retry.md`
- `reports/phase_reports/phase12s_request_sequence_demo_ledger_buy_retry.json`

## RequestSequenceManager

追加:

```text
RequestSequenceManager.current_no
RequestSequenceManager.next_no()
```

接続:

```text
TachibanaRequestBuilder
TachibanaCashStockOrderRequestBuilder
TachibanaDemoOrderAdapter
```

mock確認:

```text
login -> CLMKabuNewOrder -> logout
p_no  -> 1     -> 2              -> 3
```

また、read-only request後にorder builderが`p_no=1`へ戻らないことも確認した。

Phase12-Sの実Demo retryでは、Phase12-Qの`p_no:[1] <= 前要求.p_no:[1]` rejectは再発していない。したがって、sequence修正は有効と判断する。

## Persistent Demo Ledger

追加root:

```text
.runtime/operations/demo_ledger/
```

生成されたartifact:

```text
.runtime/operations/demo_ledger/orders.jsonl
.runtime/operations/demo_ledger/events.jsonl
.runtime/operations/demo_ledger/state.json
```

今回の状態:

| Field | Value |
| --- | ---: |
| order_history_count | 1 |
| accepted_order_count | 0 |
| rejected_order_count | 1 |
| execution_history_count | 0 |
| position_history_count | 0 |
| lifecycle_event_count | 1 |
| broker_reset_event_count | 0 |

方針:

```text
broker_snapshot_overwrites_demo_ledger=false
persistent_demo_ledger_used_for_multiday_history=true
raw_request_saved=false
raw_response_saved=false
secret_saved=false
plain_broker_ids_saved=false
```

## Demo Broker Reset Handling

実装:

```text
detect_demo_broker_daily_reset()
```

Demo Broker snapshotが翌日に空になっても、Persistent Demo Ledgerの過去order / execution / position履歴は削除しない。

reconcileには以下を追加した。

```text
demo_broker_reset_policy.broker_daily_reset_detected
demo_broker_reset_policy.classification
demo_broker_reset_policy.demo_ledger_continues=true
demo_broker_reset_policy.broker_snapshot_overwrites_demo_ledger=false
```

今回の同日retry後は、Broker側にaccepted order / execution / positionが無いため、daily resetは未検出。

```text
broker_daily_reset_detected=false
classification=PASS
```

## Retry Parent / New Approval / New Run

Phase12-Q rejected artifactをretry_parentとして記録した。

```text
retry_parent.phase=Phase12-Q
retry_parent.status=REJECTED_OR_UNKNOWN
retry_parent.accepted=false
retry_parent.rejected=true
retry_parent.broker_order_ref_hash=""
```

新Approval:

```text
approval_id=operation_approval_2026-06-29_0e3712f3c5d4
approval_status=APPROVED
demo_order_allowed=true
production_order_allowed=false
max_notional=600000
```

新Run:

```text
run_id=operation_2026-06-29_operation_approval_2026-06-29_0e3712f3c5d4_buy_2026-06-29_92560_001
```

## Pre-Retry Guard

BUY retry前にread-only refreshを実行。

| Gate | Result |
| --- | --- |
| environment | `demo` |
| Demo base URL | PASS |
| Broker Orders | 0 |
| Broker Executions | 0 |
| Broker Positions | 0 |
| Buying Power | 20,000,000 |
| Approval | APPROVED |
| Safety | ALLOW |
| MAX_EXPOSURE | PASS |
| second password file present | true |
| second password value printed/saved | false |
| Production allowed | false |
| raw request saved | false |
| raw response saved | false |

## BUY Retry

実行:

```bash
python3 scripts/run_demo_submit.py --trade-date 2026-06-29 --root .runtime/operations --execute-demo-order
```

BUY条件:

| Field | Value |
| --- | --- |
| code | `92560` |
| side | `BUY` |
| quantity | `100` |
| limit_price | `5410` |
| expected_notional | `541000` |
| order_type | `CASH_EQUITY` |
| price_type | `LIMIT` |

結果:

| Field | Value |
| --- | --- |
| broker_order_api_called | true |
| clm_kabu_new_order_called | true |
| demo_order_executed / accepted | false |
| normalized status | `REJECTED_OR_UNKNOWN` |
| p_errno | `-1` |
| p_err_classification | `SECOND_PASSWORD_FIELD_OR_VALUE_ERROR` |
| broker_order_ref_hash | empty |
| raw_request_saved | false |
| raw_response_saved | false |
| secret_saved | false |

`p_no` sequence errorは再発していない。

## Post-Submit Read-Only

BUY retry後、read-only refreshを実行した。

| Artifact | Count / Value |
| --- | ---: |
| Broker Orders | 0 |
| Broker Executions | 0 |
| Broker Positions | 0 |
| Buying Power | 20,000,000 |
| Raw Response Saved | false |
| Secret Saved | false |

## Fill / Reconcile / Report / Audit

| Step | Result |
| --- | --- |
| Fill Monitor | PASS, lifecycle=`REJECTED` |
| Safety Monitor | PASS |
| Reconcile | PASS |
| Daily Report | PASS |
| Operation Audit | PASS |

Daily Report / Operation Audit 実行時、sandbox環境のArrow CPU情報警告が標準出力に出たが、artifact生成とstatusはPASS。

## SELL Lifecycle

SELLは未試行。

理由:

```text
BUY retry was rejected by broker
BUY accepted=false
BUY filled=false
Broker positions=0
sell_zero_reason=no_valid_broker_positions
```

## Tests

実施:

```bash
python3 -m pytest tests/phase12 -q
python3 -m pytest tests/broker/test_tachibana_request_sequence_manager.py tests/broker/test_tachibana_client_mock.py tests/broker/test_tachibana_order_request_builder.py tests/broker/test_tachibana_demo_order_smoke_foundation.py -q
PYTHONPYCACHEPREFIX=.runtime/operations/pycache_phase12s python3 -m py_compile src/ai_fund_lab_v2/broker/request_sequence.py src/ai_fund_lab_v2/broker/request_builder.py src/ai_fund_lab_v2/broker/tachibana_order_request.py src/ai_fund_lab_v2/broker/demo_order.py src/ai_fund_lab_v2/operations/demo_ledger.py src/ai_fund_lab_v2/operations/operations.py
python3 -m json.tool reports/phase_reports/phase12s_request_sequence_demo_ledger_buy_retry.json
```

結果:

- Phase12 tests: `42 passed`
- Broker targeted tests: `27 passed`
- Additional targeted sequence / ledger tests: included above
- py_compile: PASS
- JSON validation: PASS

## Prohibited Actions Audit

- Production注文: not executed
- Production Unlock: not executed
- 信用取引: not executed
- LINE実送信: not executed
- AI再学習: not executed
- Backtest再実行: not executed
- raw request保存: false
- raw response保存: false
- secret保存: false
- Phase9 artifact / launchd / CLI変更: not executed
- Production側Broker Source of Truth弱体化: not changed

## Remaining Gaps

1. `sSecondPassword`がBroker側で`NULL`扱いになる原因調査
2. v4r9 compressed field id / request field name for second passwordの公式仕様再確認
3. `DemoOrderBrokerTransport._encode_order_payload()`のsecond password injection方式レビュー
4. 修正後も再retry前には新approval_id / 新run_id / retry_parent / Broker zero-state checkが必要
5. BUY accepted / filled後にのみSELL lifecycleへ進む

## Next Phase

`PHASE12-T_SECOND_PASSWORD_FIELD_MAPPING_FIX_REVIEW`

次はDemo order requestにおける第二暗証番号フィールドのエンコード/送信方式を設計レビューし、mockで確認してから再retryする。
