# Phase12-Q Demo Buy/Sell Full Lifecycle Wire Execution

## Status

`PHASE12Q_BUY_REJECTED_BY_BROKER`

Phase12-Qでは、第二暗証番号設定後の立花証券Demo環境で、AI Fund Lab Operations RuntimeのDemo BUY wire executionを実行した。

BUY注文はDemo endpointで`CLMKabuNewOrder`まで到達したが、Broker側でredacted normalized rejectとなった。このため、指示どおり自動再注文・自動取消し・SELL送信は行わず、BUY後のread-only確認、Fill Monitor、Safety Monitor、Reconcile、Daily Report、Operation Auditまで実行した。

Production注文、Production Unlock、LINE実送信、AI再学習、Backtest再実行、raw request保存、raw response保存、secret保存は行っていない。

## Pre-Execution Gates

BUY wire execution前のguard確認結果:

| Gate | Result |
| --- | --- |
| `TACHIBANA_API_ENV=demo` | PASS |
| Demo base URL | PASS |
| production order allowed | `false` |
| line send enabled | `false` |
| Approval valid | PASS |
| demo order allowed | `true` |
| Safety | `ALLOW` |
| MAX_EXPOSURE | PASS |
| buying power | PASS |
| second password file present | PASS |
| second password loaded only at final boundary | PASS |
| order type | `CASH_EQUITY` |
| credit / margin | disabled |
| quantity | `100` |
| expected notional | `541000` |
| raw request saved | `false` |
| raw response saved | `false` |

第二暗証番号の値、hash、長さ、内容は表示・保存していない。presenceのみ確認した。

## BUY Wire Execution

使用したBUY item:

| Field | Value |
| --- | --- |
| side | `BUY` |
| code / issue_code | `92560` |
| quantity | `100` |
| order_type | `CASH_EQUITY` |
| price_type | `LIMIT` |
| limit_price | `5410` |
| expected_notional | `541000` |
| normalization_source | `jquants_latest_close` |

実行:

```bash
python3 scripts/run_demo_submit.py --trade-date 2026-06-29 --root .runtime/operations --execute-demo-order
```

結果:

| Field | Value |
| --- | --- |
| CLI status | `PASS` |
| broker_order_api_called | `true` |
| clm_kabu_new_order_called | `true` |
| demo_order_executed / accepted | `false` |
| normalized response status | `REJECTED_OR_UNKNOWN` |
| normalized rejected flag | `true` |
| p_errno | `6` |
| p_err | `引数（p_no:[1] <= 前要求.p_no:[1]）エラー。` |
| broker_order_ref_hash | empty |
| raw_request_saved | `false` |
| raw_response_saved | `false` |
| secret_saved | `false` |

Broker rejectのため、BUYは約定せず、Broker Orders / Executions / Positionsにも反映されなかった。

## BUY Post-Submit Read-Only Confirmation

Post-submit read-only refresh:

```bash
python3 scripts/run_preflight.py --trade-date 2026-06-29 --root .runtime/operations --refresh-broker-readonly
```

結果:

| Artifact | Count / Value |
| --- | ---: |
| Broker Orders | 0 |
| Broker Executions | 0 |
| Broker Positions | 0 |
| Buying Power | 20,000,000 JPY |
| Broker Snapshot Summary | PASS |
| Raw Response Saved | `false` |
| Secret Saved | `false` |

## Fill / Safety / Reconcile

Broker rejectを`UNKNOWN_STATUS`ではなく`REJECTED`として扱うため、Fill Monitorの分類だけを最小修正した。再注文は行っていない。

後続結果:

| Step | Result |
| --- | --- |
| Fill Monitor | `PASS`, lifecycle=`REJECTED` |
| Safety Monitor | `PASS`, safety_state=`ALLOW` |
| Reconcile | `PASS` |
| Daily Report | `PASS` |
| Operation Audit | `PASS` |

Fill Monitorは`auto_resubmit=false`、`auto_cancel=false`、`auto_sell=false`を維持している。

## SELL Wire Execution

SELLは未試行。

理由:

```text
BUY was rejected by broker
BUY was not filled
Broker positions count = 0
sell_zero_reason = no_valid_broker_positions
```

Phase12-Qの指示に従い、BUYが`FILLED`またはBroker positionsへ反映された場合のみSELLへ進むため、SELL Demo endpoint callは行っていない。

## Daily Report / Audit

Daily Report:

| Field | Value |
| --- | --- |
| current submit status | `PASS` |
| fill_monitor | `PASS` |
| safety_monitor | `PASS` |
| reconcile | `PASS` |
| blog draft generated | `true` |
| public report generated | `true` |
| line payload generated | `true` |
| line send executed | `false` |

Operation Audit:

| Field | Value |
| --- | --- |
| status | `PASS` |
| no production order audit | PASS |
| production unlock audit | PASS |
| leakage audit | PASS |
| secret audit | PASS |
| raw response audit | PASS |
| Phase9 isolation audit | PASS |

## Implementation Note

Phase12-Q中に、Broker normalized responseが`rejected=true`でもsubmit statusが`REJECTED_OR_UNKNOWN`の場合に、Fill Monitorが`UNKNOWN_STATUS`へ倒れる不整合を確認した。

必要最小修正として、`wire_execution_result.response.rejected=true`を`REJECTED`、`accepted=true`を`ACCEPTED`に分類するよう修正した。これは既存artifactの分類改善のみであり、注文仕様、Demo/Production分岐、Broker API仕様、wire executionの再試行動作は変更していない。

あわせて、second password設定済みの実環境でもguardテストが外部`.env`に影響されないよう、テスト内の`TACHIBANA_API_SECOND_PASSWORD_FILE`を空文字に固定した。

## Tests

実施した軽量確認:

```bash
python3 scripts/run_preflight.py --trade-date 2026-06-29 --root .runtime/operations
python3 scripts/run_demo_submit.py --trade-date 2026-06-29 --root .runtime/operations --execute-demo-order
python3 scripts/run_preflight.py --trade-date 2026-06-29 --root .runtime/operations --refresh-broker-readonly
python3 scripts/run_fill_monitor.py --trade-date 2026-06-29 --root .runtime/operations
python3 scripts/run_safety_monitor.py --trade-date 2026-06-29 --root .runtime/operations
python3 scripts/run_reconcile.py --trade-date 2026-06-29 --root .runtime/operations
python3 scripts/run_daily_report.py --trade-date 2026-06-29 --root .runtime/operations
python3 scripts/run_operation_audit.py --root .runtime/operations
python3 -m pytest tests/phase12/test_operations_fill_monitor_states.py tests/phase12/test_demo_order_wire_unlock_guards.py -q
PYTHONPYCACHEPREFIX=.runtime/operations/pycache_phase12q python3 -m py_compile src/ai_fund_lab_v2/operations/operations.py src/ai_fund_lab_v2/broker/demo_order.py scripts/run_demo_submit.py scripts/run_fill_monitor.py
```

結果:

- Targeted pytest: `8 passed`
- py_compile: PASS
- Daily Report: PASS
- Operation Audit: PASS

`run_daily_report.py`と`run_operation_audit.py`では、sandbox環境のArrow CPU情報警告が標準出力に出たが、artifact生成とstatusはPASSだった。

## Prohibited Actions Audit

- Production注文: not executed
- Production Unlock: not executed
- Demo SELL order: not executed
- LINE実送信: not executed
- AI再学習: not executed
- Backtest再実行: not executed
- raw request保存: false
- raw response保存: false
- secret保存: false
- Phase9 artifact / launchd / CLI破壊: not executed

## Remaining Gaps

1. Broker reject `p_errno=6` / `p_no` sequence errorの原因調査
2. Tachibana Demo order transportのrequest sequence / session state要件確認
3. 再試行前に、同一注文の二重送信を避けるため新しいApprovalとrun_idを切る
4. BUYがaccepted / filledされた後にのみSELL full lifecycleを再実行

## Next Phase

`PHASE12-R_DEMO_ORDER_SEQUENCE_FIX_AND_BUY_RETRY_REVIEW`

次は、Demo order request sequenceの原因を設計レビューし、必要最小修正後にBUY wire retryを行う。SELL full lifecycleはBUY fill / Broker position反映後に実施する。
