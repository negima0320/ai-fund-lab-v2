# Phase12-R Demo Order Sequence Fix Investigation

## Status

`PHASE12R_DEMO_ORDER_SEQUENCE_FIX_INVESTIGATION_COMPLETE`

Phase12-Rでは、Phase12-QのDemo BUY wire executionで発生したBroker reject:

```text
p_errno=6
p_err=引数（p_no:[1] <= 前要求.p_no:[1]）エラー。
```

について、再注文せずに調査・設計レビューのみを行った。

`CLMKabuNewOrder`再呼び出し、Demo注文再試行、Production注文、Production Unlock、LINE実送信、AI再学習、Backtest再実行、raw request / raw response / secret保存は行っていない。

## Sources Reviewed

- `docs/phase_reports/phase12q_demo_buy_sell_full_lifecycle_wire_execution.md`
- `docs/phase_reports/phase12p_second_password_configured_demo_wire_retry.md`
- `docs/phase_reports/phase12o_minimal_demo_order_wire_execution.md`
- `docs/phase_reports/phase12n_demo_wire_unlock_preflight_review.md`
- `docs/phase_reports/phase10_final_summary_and_phase11_handoff.md`
- `docs/phase_reports/phase10l4_tachibana_account_protocol_error_reveal.md`
- `docs/phase_reports/phase10l5_tachibana_p_no_monotonic_sequence_fix.md`
- `docs/phase_reports/phase10s_demo_order_request_authorization_mock.md`
- `src/ai_fund_lab_v2/broker/request_builder.py`
- `src/ai_fund_lab_v2/broker/client.py`
- `src/ai_fund_lab_v2/broker/tachibana_order_request.py`
- `src/ai_fund_lab_v2/broker/demo_order.py`
- `src/ai_fund_lab_v2/broker/transport.py`
- Official Tachibana API reference:
  - `https://www.e-shiten.jp/e_api/mfds_json_api_refference.html`
  - `https://www.e-shiten.jp/e_api/mfds_json_api_ref_text.html`
  - `https://www.e-shiten.jp/e_api/e_api_request_if_v4r9.pdf`

公式HTMLでは、auth / request / master / price各I/Fの要求引数に`p_no`と`p_sd_date`が含まれること、`CLMKabuNewOrder`がREQUEST I/Fの株式新規注文であることを確認した。詳細な共通項目仕様は公式PDF参照だったが、ローカル環境にPDF text extractorが無かったため、Phase10-L4/L5で既に実証済みの`p_no <= previous p_no`挙動と既存実装を主根拠にした。

## p_no Understanding

Phase10-L4/L5の実証結果:

```text
p_errno=6
p_err=引数（p_no:[1] <= 前要求.p_no:[1]）エラー。
```

は、同一API flow / session内で現在要求の`p_no`が前要求の`p_no`より大きくない場合に発生するsequence precondition errorとして扱われている。

Phase10-L5では、read-only flowについて以下で解決済み:

```text
login -> account -> buying_power -> logout
p_no  -> 1     -> 2       -> 3            -> 4
```

実装上の理解:

- `p_no`は要求ごとの単調増加番号。
- `p_sd_date`は要求送信日時。
- login requestも`p_no`を消費する。
- read-only REQUEST I/Fも`p_no`を消費する。
- logout requestも`p_no`を消費する。
- 同一client / session flowでは、同じbuilder / counterを共有する必要がある。
- 別clientが独立counterを持つこと自体はmock上許容されているが、同一login session内で別counterを使うと`p_no=1`再利用になり得る。
- logout/loginでBroker側stateが完全にどうリセットされるかは公式本文から断定できない。ただしPhase10-L5では1回のlogin session内共有counterで問題が解消している。
- Demo / Production差分は確認できていないため、少なくともDemoでは同一session内単調増加が必要と判断する。

## Existing Implementation Findings

### Read-Only Client

`TachibanaReadOnlyClient`はPhase10-L5で修正済み。

```text
src/ai_fund_lab_v2/broker/client.py
```

- client初期化時に`TachibanaRequestBuilder`を保持する。
- `request_builder` propertyは同じbuilderを返す。
- login / read-only calls / logoutで同一counterを進める。
- transportがauth URLからREQUEST/PRICE URLへ切り替わる場合も、`builder=auth_client.request_builder`を渡せる。

`tachibana_broker_snapshot.py`でも:

```text
auth_client.login()
request_client = TachibanaReadOnlyClient(..., builder=auth_client.request_builder)
price_client = TachibanaReadOnlyClient(..., builder=auth_client.request_builder)
logout(auth_client, ...)
```

として、同一sessionの`p_no`を共有している。

### Demo Order Path

`TachibanaDemoOrderAdapter.submit_cash_stock_order()`の現在形:

```text
auth_client = TachibanaReadOnlyClient(...)
session = auth_client.login(...)
builder = TachibanaCashStockOrderRequestBuilder()
payload = builder.build_final_payload_with_second_password(...)
DemoOrderBrokerTransport(...).request(payload)
logout(auth_client, session, ...)
```

問題点:

- `auth_client.login()`が`p_no=1`を消費する。
- 注文payloadは新規`TachibanaCashStockOrderRequestBuilder()`が作る。
- order builderの`sequence_no`初期値は`0`。
- そのため注文payloadの`p_no`は`1`になる。
- 結果として、同一session内で`p_no=1`を再利用する形になり、Phase12-Qの`p_no:[1] <= 前要求.p_no:[1]`と一致する。

### p_no State Artifact

現在、runtime artifactとして`last_p_no`やsession-scoped counterは保存されていない。

ただし、raw request保存禁止のため、保存する場合も以下に限定すべき:

```text
sequence_state_saved=true
last_p_no=<integer only>
session_scope_hash=<safe runtime/session hash>
raw_request_saved=false
raw_response_saved=false
secret_saved=false
```

Phase12-Sの最小修正では、まず同一process / same adapter call内でbuilderを共有するだけで十分と判断する。永続artifact保存は、複数processで同一Broker sessionを再利用する設計が出るまで不要。

## Phase12-Q Failure Hypotheses

| Hypothesis | Judgement | Basis |
| --- | --- | --- |
| A. demo order requestが`p_no=1`固定で送られている | Highly likely | order builderが新規生成され、初回buildで`p_no=1` |
| B. read-only APIで既に`p_no=1`を使用済み | Likely in the broad sense | 同一adapter内のloginが`p_no=1`を使用済み。Phase12-Q直前のread-only refreshは別sessionの可能性が高く、直接原因ではない |
| C. login/session内の前要求p_noが1で、orderも1を使った | Most likely | error textが`p_no:[1] <= 前要求.p_no:[1]`。code pathも一致 |
| D. p_no stateを保存していない | Contributing but not root for one-shot call | 同一call内共有で解決可能。永続stateは将来課題 |
| E. order transportだけ別clientを作り直し、counter初期化している | Highly likely | read-only auth clientとorder builderが別counter |
| F. login/logout境界が想定と違う | Possible but secondary | Phase10-L5ではsame session shared builderで解決済み |

最有力原因:

```text
Demo order path does not share the login/session p_no counter.
login consumes p_no=1, then CLMKabuNewOrder is built by a fresh order builder with p_no=1.
Broker rejects because current p_no is not greater than previous p_no.
```

## Recommended Fix Plan

Phase12-Sでの最小修正案:

### 1. Shared Request Sequence

`TachibanaCashStockOrderRequestBuilder`が初期`sequence_no`を外部指定できる構造は既にあるため、以下のいずれかで同一counterを共有する。

推奨:

```text
TachibanaDemoOrderAdapter
  auth_client = TachibanaReadOnlyClient(...)
  session = auth_client.login(...)             # p_no=1
  order_builder = TachibanaCashStockOrderRequestBuilder(
      sequence_no=auth_client.request_builder.sequence_no
  )
  payload = order_builder.build_final_payload_with_second_password(...)  # p_no=2
  sync auth_client.request_builder.sequence_no = order_builder.sequence_no
  logout(auth_client, session, ...)            # p_no=3
```

ただし、`TachibanaRequestBuilder`と`TachibanaCashStockOrderRequestBuilder`は別classなので、より安全な設計は共通の`RequestSequenceManager`を作り、read-only builderとorder builderが同じ`next_no()`を使うこと。

Phase12-Sの最小実装では:

```text
RequestSequenceManager
  next_no()
  current_no
```

を追加し、両builderが任意で受け取れるようにする。

### 2. Keep Environment Branching Out of Business Logic

Demo / Production差分は既存方針どおり:

```text
Runtime Config
↓
Broker Factory / Adapter
↓
Transport
```

に閉じる。Operations層に`if demo` / `if production`を増やさない。

### 3. Do Not Persist Raw Payload

テストやdiagnostic artifactに保存してよいのは:

```text
sequence_shared=true
login_p_no=1
order_p_no=2
logout_p_no=3
raw_request_saved=false
raw_response_saved=false
secret_saved=false
```

保存禁止:

```text
request body
encoded request body
second password
auth id
session URL
raw response
plaintext order id
```

### 4. Tests Before Any Retry

Phase12-S実装時の最小テスト:

```text
login -> demo order -> logout uses p_no=1,2,3
read-only -> demo order in same session uses increasing p_no
fresh order builder alone remains monotonic
production environment fails closed
second password value is not saved
raw request / raw response are not saved
CLMKabuNewOrder is not called in tests
```

## Demo Broker Daily Reset / Persistent Demo Ledger Policy

Phase12-R追記として、立花証券Demo環境の日次リセットをOperations Runtime設計に明示的に織り込む。

前提:

```text
Broker Demo Snapshot
= 当日状態 / 日次リセットされる外部観測値

Persistent Demo Ledger
= AI Fund Lab側で保持するDemo運用履歴
```

Productionでは引き続き`Broker Source of Truth`を優先する。ただしDemo環境では、Broker側の注文・約定・保有情報が翌日に初期化され得るため、以下の二層モデルを採用する。

```text
Broker Source of Truth for same-day execution confirmation
+
Persistent Demo Ledger for multi-day operation history
```

### Required Behavior

Phase12-S以降で必ず守ること:

```text
Demo Broker snapshotでPersistent Demo Ledgerを全量上書きしない
Demo Broker positions=0でも、前日までのPersistent Demo Ledger positionを即削除しない
Demo Broker orders/executions=0でも、過去Demo order/execution履歴を即削除しない
Demo環境では broker_reset_detected を記録する
Broker reset後のreconcileは BLOCK / SYSTEM_EMERGENCY_STOP ではなく DEMO_BROKER_RESET_REVIEW として扱う
当日注文・当日約定はBroker read-onlyで確認する
翌日以降はPersistent Demo Ledgerを運用履歴として使う
```

### Persistent Demo Ledger Contents

最低限保持する履歴:

```text
demo_order_history
demo_execution_history
demo_position_history
demo_cash_history
demo_buying_power_history
demo_lifecycle_events
broker_reset_events
```

保存先案:

```text
.runtime/operations/demo_ledger/
.runtime/operations/demo_ledger/orders.jsonl
.runtime/operations/demo_ledger/executions.jsonl
.runtime/operations/demo_ledger/positions.jsonl
.runtime/operations/demo_ledger/cash.jsonl
.runtime/operations/demo_ledger/buying_power.jsonl
.runtime/operations/demo_ledger/events.jsonl
.runtime/operations/demo_ledger/broker_reset_events.jsonl
```

保存可能:

```text
redacted normalized order / execution / position lifecycle
hashed broker order id
hashed execution id
business_date
observed_at
broker_reset_detected
source_artifact_hash
raw_request_saved=false
raw_response_saved=false
secret_saved=false
```

保存禁止:

```text
raw request
raw response
second password
auth id
session token / virtual URL
plaintext broker order id
plaintext execution id
```

### Reconcile Policy

Demo環境で翌日にBroker read-only snapshotが空になった場合でも、Persistent Demo Ledgerの過去履歴を削除しない。

扱い:

```text
DEMO_BROKER_DAILY_RESET_DETECTED
DEMO_LEDGER_CONTINUES
REVIEW_REQUIRED
```

当日注文直後にBroker read-onlyで確認できない場合は、日次リセットではなく通常のsame-day execution confirmation failureとして扱う。

```text
same_day_order_not_confirmed -> REVIEW_REQUIRED or BLOCK
next_day_broker_empty_after_prior_demo_activity -> DEMO_BROKER_RESET_REVIEW
```

### Phase12-S Retry追加確認

BUY retry前には、Phase12-Rで定義した`p_no`修正に加え、以下を確認する。

```text
same_day_broker_orders=0
same_day_broker_executions=0
same_day_broker_positions=0
persistent_demo_ledger_previous_state確認
duplicate orderなし
retry_parent=Phase12-Q rejected artifact
new approval_id
new run_id
```

これにより、Demo Brokerの日次リセットによる空snapshotと、同日注文確認失敗を混同しない。

## Retry Policy

Phase12-SでBUY retryへ進む前の方針:

1. Phase12-Sはまず実装修正・mock/targeted testsのみ。
2. BUY retryは同じPhase12-S内で明示指示がある場合のみ、またはPhase12-Tとして分離。
3. retry前にBroker read-only refreshを実行し、以下を再確認する。

```text
orders_count=0
executions_count=0
positions_count=0
buying_power available
persistent_demo_ledger_previous_state checked
raw_response_saved=false
secret_saved=false
```

4. 前回Phase12-Qのrejected artifactは履歴として残す。
5. retryでは新しい`approval_id`を作成する。
6. retryでは新しいrun_id / runtime_idを作成する。
7. retry artifactには以下を持たせる。

```text
retry_parent_phase="Phase12-Q"
retry_parent_status="PHASE12Q_BUY_REJECTED_BY_BROKER"
retry_parent_item_id="buy_2026-06-29_92560_001"
previous_broker_order_ref_hash=""
previous_broker_accepted=false
previous_broker_orders_count=0
previous_broker_executions_count=0
previous_broker_positions_count=0
human_review_recorded=true
```

8. duplicate order防止:

```text
if broker_orders_count > 0: BLOCK
if broker_executions_count > 0: BLOCK
if same_day_broker_positions_count > 0 and side=BUY retry: HUMAN_REVIEW
if persistent_demo_ledger shows open duplicate position for same retry item: HUMAN_REVIEW
if previous accepted=true: BLOCK
if previous broker_order_ref_hash present: HUMAN_REVIEW
```

9. BUY accepted / filled / Broker position反映が確認できるまでSELLへ進まない。

## Phase12-S Required Minimum Tasks

1. `RequestSequenceManager`または同等のshared counterを設計・実装する。
2. `TachibanaRequestBuilder`と`TachibanaCashStockOrderRequestBuilder`が同一session counterを共有できるようにする。
3. `TachibanaDemoOrderAdapter`で`login -> order -> logout`が`p_no=1,2,3`になるようにする。
4. raw request / raw response / second passwordを保存しないdiagnostic summaryを追加する。
5. production環境では引き続きfail closedするテストを追加する。
6. `p_errno=6` / `p_no` errorは`SESSION_SEQUENCE_OR_AUTH_ERROR`相当に分類できるようにする。
7. retry前Broker read-only zero-state checkを明示する。
8. retry時は新Approval / 新run_id / retry_parent参照を必須にする。
9. Persistent Demo Ledgerを追加し、Demo Broker snapshotで過去履歴を全量上書きしない。
10. Demo Broker日次リセット検出時は`DEMO_BROKER_RESET_REVIEW`として扱い、即`SYSTEM_EMERGENCY_STOP`にしない。

## Prohibited Actions Audit

- Demo注文再試行: not executed
- `CLMKabuNewOrder`呼び出し: not executed
- Production注文: not executed
- Production Unlock: not executed
- LINE実送信: not executed
- AI再学習: not executed
- Backtest再実行: not executed
- raw request保存: false
- raw response保存: false
- secret保存: false
- Phase9 artifact / launchd / CLI変更: not executed

## Judgement

Phase12-Qのrejectは、注文内容や価格ではなく、`p_no` sequence管理の実装境界に起因する可能性が最も高い。

次は、Demo order adapterの同一session内でlogin/order/logoutの`p_no`を共有する最小修正を行い、mockで`p_no=1,2,3`を確認してから、新Approval / 新run_idでBUY retryを検討する。
