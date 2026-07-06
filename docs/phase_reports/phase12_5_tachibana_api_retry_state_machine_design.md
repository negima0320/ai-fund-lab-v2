# Phase12.5 Tachibana API Retry / Order Safety State Machine Design

作成日: 2026-07-03

## 現状の問題

Phase12.5 Day1では、Submitは成功し立花Web画面でも約定を確認できたが、Broker ReadOnly snapshotが一時的な `login/session` 失敗で取得できず、Runtime側の約定確認が `REVIEW_REQUIRED` になった。

ReadOnly側には短期retryとsafe diagnosisを追加済みだが、立花API全体ではまだretry方針が統一されていない。特に注文APIは、timeoutやsocket切断などで「Brokerに届いたか不明」になった場合、安易に再送すると二重発注になる。

したがって、retry可能な処理とretry禁止の処理をAPI種別ごとに明確化し、注文APIはFailure State Machineで扱う。

## Retry対象分類

| 対象 | Retry | 方針 |
|---|---:|---|
| login/session取得 | 可 | 副作用なし。短いbackoffで最大3回程度 |
| account summary | 可 | read-only。fetch失敗は短期retry |
| buying power | 可 | read-only。fetch失敗は短期retry |
| positions | 可 | read-only。fetch失敗は短期retry |
| orders | 可 | read-only。POST_SEND_UNKNOWN確認にも使う |
| executions | 可 | read-only。約定確認のSource of Truth |
| quotes | 可 | read-only。失敗時はReadOnly fetch分類 |
| logout | 可 | best-effort retry。失敗しても主処理を巻き戻さない |
| buy order | 単純retry禁止 | 送信後結果不明時の再送は禁止 |
| sell order | 単純retry禁止 | 送信後結果不明時の再送は禁止 |

## 注文API Failure State Machine

注文APIはbuy/sell共通で以下の状態に正規化する。

```text
PRE_SEND_FAILURE
POST_SEND_UNKNOWN
BROKER_REJECTED
ACCEPTED
REVIEW_REQUIRED
```

### PRE_SEND_FAILURE

Brokerへ注文送信していないことが明確な失敗。

例:

- request生成前のvalidation失敗
- auth/session取得前の失敗
- second password missing
- demo/prod guardでBLOCK
- code normalization failure
- approval / safety / budget guardでBLOCK

扱い:

- Broker注文未送信
- 条件付きretry可
- `production_order_submitted=false`
- `broker_order_api_called=false`

### POST_SEND_UNKNOWN

Brokerへ届いたか不明な失敗。

例:

- HTTP timeout
- socket disconnect
- request送信後の例外
- response decode不能
- result codeを確認できない

扱い:

- 自動再送禁止
- Broker read-onlyで注文存在確認を試みる
- 確認できれば `ACCEPTED`
- 確認できなければ `REVIEW_REQUIRED`

### BROKER_REJECTED

Broker応答で明確に拒否された状態。

扱い:

- 自動再送禁止
- safeな拒否分類だけ保存
- raw responseは保存しない
- 人間レビュー対象

### ACCEPTED

Broker応答、またはPOST_SEND_UNKNOWN後のBroker read-only照会で注文受付を確認できた状態。

扱い:

- 正常
- raw broker order idは保存しない
- broker order idはhashのみ保存
- `classification_source` を保存する

例:

```text
broker_order_api_response
broker_readonly_order_confirmation
```

### REVIEW_REQUIRED

自動判断できない状態。

例:

- POST_SEND_UNKNOWN後、Broker read-only確認でも注文存在を確認できない
- Broker read-only自体が失敗
- 注文候補の照合が曖昧

扱い:

- 自動再送禁止
- 人間確認
- Fill / Reconcile / Daily Reportで隠さない

## 共通Retry Helper設計

`src/ai_fund_lab_v2/broker/retry_policy.py` を追加する方針。

概念:

```text
BrokerRetryPolicy
BrokerAttemptRecord
classify_failure_stage()
run_retryable_call()
```

`BrokerAttemptRecord` の例:

```json
{
  "attempt": 1,
  "failure_stage": "login_session",
  "safe_error_class": "TimeoutError",
  "retryable": true,
  "classification": "FAILED_LOGIN_SESSION"
}
```

保存禁止:

- secret
- raw request
- raw response
- 認証ID
- 復号URL
- raw broker order id

## ReadOnly Retry設計

既に追加した `run_tachibana_broker_snapshot()` のlogin/session retryは、共通helperへ移行する。

ReadOnly fetch対象:

- account summary
- buying power
- positions
- orders
- executions
- quotes

分類:

```text
FAILED_CONFIGURATION
FAILED_LOGIN_SESSION
FAILED_BROKER_READONLY_FETCH
FAILED_BROKER_READONLY_PARSE
```

方針:

- login/sessionは短いbackoffでretry
- read-only fetchも短いbackoffでretry
- parse/normalize失敗はretryより分類保存を優先
- retry attemptsは `broker_readonly_snapshot_report.json` に保存
- snapshotが書けない場合もsafe diagnosisは保存

## Logout Best-Effort Retry

logoutはbest-effortでretryする。

例:

```json
{
  "logout": {
    "attempted": true,
    "status": "BEST_EFFORT_FAILED",
    "retry_attempts": 3,
    "attempts": []
  }
}
```

logout失敗は主処理の成功を取り消さない。ただし、連続失敗はAudit/Reportで見える化する。

## Order Retry禁止設計

buy/sell共通で、送信境界を明示するwrapperを設計する。

候補関数:

```text
prepare_order_request()
mark_send_started()
submit_order()
classify_submit_result()
confirm_unknown_order_via_readonly()
```

重要ルール:

- `mark_send_started()` より前の失敗は `PRE_SEND_FAILURE`
- `mark_send_started()` 以降のtimeout/socket disconnect/decode errorは `POST_SEND_UNKNOWN`
- `POST_SEND_UNKNOWN` は同一注文の自動再送禁止
- `POST_SEND_UNKNOWN` 後はBroker read-only確認へ進む

## POST_SEND_UNKNOWN確認フロー

注文送信後に結果不明になった場合:

1. 同一注文の再送はしない
2. Broker read-only snapshotを取得またはrefreshする
3. `broker_orders` を照合する
4. 必要に応じて `broker_executions` も参照する
5. 確認できれば `ACCEPTED`
6. 確認できなければ `REVIEW_REQUIRED`

照合キー候補:

```text
issue_code
side
quantity
order time window
price / limit price
account type
```

確認成功時:

```json
{
  "submit_classification": "ACCEPTED",
  "classification_source": "broker_readonly_order_confirmation",
  "post_send_unknown": true,
  "broker_readonly_confirmation_attempted": true,
  "broker_readonly_confirmation_status": "CONFIRMED"
}
```

確認不能時:

```json
{
  "submit_classification": "REVIEW_REQUIRED",
  "post_send_unknown": true,
  "broker_readonly_confirmation_attempted": true,
  "broker_readonly_confirmation_status": "NOT_CONFIRMED",
  "review_reason": "order_submit_result_unknown_and_broker_confirmation_missing"
}
```

## submitted_orders Artifact設計

各itemに以下を追加する。

```json
{
  "retry_attempts": 1,
  "attempts": [],
  "submit_classification": "ACCEPTED",
  "classification_source": "broker_order_api_response",
  "post_send_unknown": false,
  "broker_readonly_confirmation_attempted": false,
  "broker_readonly_confirmation_status": "NOT_REQUIRED",
  "broker_order_id_hash": "",
  "raw_broker_order_id_saved": false,
  "raw_request_saved": false,
  "raw_response_saved": false,
  "secret_saved": false
}
```

## Circuit Breaker案

login/session失敗を短時間に連打しないため、軽量Circuit Breakerを検討する。

例:

```text
FAILED_LOGIN_SESSION が連続3回
↓
circuit open
↓
一定時間 retry停止
↓
REVIEW_REQUIRED
```

保存候補:

```text
.runtime/operations/broker_api_circuit_state/tachibana.json
```

記録:

```json
{
  "status": "OPEN",
  "failure_classification": "FAILED_LOGIN_SESSION",
  "consecutive_failure_count": 3,
  "opened_at": "...",
  "cooldown_seconds": 300
}
```

目的:

- Broker側への過剰アクセス防止
- 連続ログイン失敗によるロック/制限リスク低減
- launchd連続実行時の無意味な再試行抑止

## Retry Metrics案

Daily Audit / Daily Report / Blog Reportには詳細すぎる生データではなく、集約値を出す。

候補:

```text
retry_count
retry_success_count
retry_failure_count
FAILED_LOGIN_SESSION
FAILED_BROKER_READONLY_FETCH
FAILED_BROKER_READONLY_PARSE
POST_SEND_UNKNOWN
BROKER_REJECTED
REVIEW_REQUIRED
```

表示方針:

- public reportでは「Broker確認要」など簡潔に表示
- internal auditではattempt count / failure_stage / safe_error_classを表示
- secret/raw payloadは出さない

## 最小実装順序

1. `broker/retry_policy.py` を追加
2. retry record / classificationのschemaを定義
3. `run_tachibana_broker_snapshot()` のlogin/session retryを共通helperへ移行
4. read-only fetchに共通retryを適用
5. logoutにbest-effort retryを適用
6. 注文API wrapperで送信境界を明示
7. `POST_SEND_UNKNOWN` 分類を導入し、自動再送禁止を実装
8. `POST_SEND_UNKNOWN` 後のBroker read-only注文存在確認を実装
9. `submitted_orders` artifactへattempt/state machine項目を追加
10. Fill / Reconcile / Daily Report / Notificationで `REVIEW_REQUIRED` を隠さないように反映
11. Circuit Breakerを必要最小限で追加
12. Retry MetricsをAudit/Reportへ追加

## 影響範囲

- `src/ai_fund_lab_v2/broker/`
- `src/ai_fund_lab_v2/operations/operations.py`
- `src/ai_fund_lab_v2/operations/broker_readonly.py`
- `src/ai_fund_lab_v2/operations/notifications.py`
- `scripts/run_submit_operation.py`
- `scripts/run_fill_monitor.py`
- `reports/phase_reports/`
- `.runtime/operations/submitted_orders/`
- `.runtime/operations/broker_readonly_reports/`
- `.runtime/operations/broker_api_circuit_state/`

## テスト方針

最低限追加するテスト:

- login/session failure retry success
- login/session retry exhaustion -> `FAILED_LOGIN_SESSION`
- read-only fetch retry success
- read-only fetch retry exhaustion -> `FAILED_BROKER_READONLY_FETCH`
- logout retry best-effort failure does not overwrite main success
- order PRE_SEND_FAILURE is retryable and broker_order_api_called=false
- order POST_SEND_UNKNOWN does not retry submit
- order POST_SEND_UNKNOWN invokes Broker read-only confirmation
- confirmation success -> `ACCEPTED`
- confirmation missing -> `REVIEW_REQUIRED`
- Broker rejected -> `BROKER_REJECTED`
- submitted_orders does not save raw order id / raw request / raw response / secret
- Production order remains disabled in Phase12.5

## 今回は実装していないこと

今回は設計と最小実装計画のみ。

- 実装変更なし
- Submit実行なし
- Broker注文なし
- Production接続なし
- Production注文なし
- 既存artifact削除なし
- notification送信なし
- secret出力なし
- raw request/response保存なし
- AI再学習なし
- フルバックテストなし
