# Phase12-P Second Password Configured Demo Wire Retry

## Status

`PHASE12P_SECOND_PASSWORD_CONFIGURED_DEMO_WIRE_RETRY_BLOCKED_BY_GUARD`

Phase12-Pでは、Phase12-Oで実装したDemo order wire pathを同じguard付きで再試行した。

結論として、現在のruntime環境では`TACHIBANA_API_SECOND_PASSWORD_FILE`が未設定のため、再びFail Closedした。これは正しい挙動であり、`CLMKabuNewOrder`は呼んでいない。

## Secret Handling

第二暗証番号の値は表示していない。読み上げ、`cat`、`echo`、ログ出力、JSON保存、Markdown保存、hash化、長さ保存は行っていない。

確認したのはpresence分類のみ。

```text
second_password_file_configured=false
second_password_file_exists=false
second_password_file_readable=false
second_password_file_nonempty=false
second_password_present=false
value_loaded=false
value_saved=false
failure_classification=SECOND_PASSWORD_FILE_NOT_CONFIGURED
```

`.secrets/`がgit管理されないよう、`.gitignore`に`.secrets/`を追加した。secret値やsecretファイルは作成していない。

## Preflight

```text
status=REVIEW_REQUIRED
reason=required_env_missing
missing=TACHIBANA_API_SECOND_PASSWORD_FILE
environment=demo
demo base url=true
production_order_allowed=false
raw_response_saved=false
secret_saved=false
```

Broker read-only artifact bundleは既存artifact上でPASS。

## BUY Item

Phase12-Oで正規化済みのBUY itemを確認した。

| Field | Value |
| --- | --- |
| item_id | `buy_2026-06-29_92560_001` |
| code / issue_code | `92560` |
| side | `BUY` |
| quantity | `100` |
| order_type | `CASH_EQUITY` |
| price_type | `LIMIT` |
| limit_price | `5410` |
| expected_notional | `541000` |
| normalization_source | `jquants_latest_close` |
| production_order_allowed | `false` |

## Approval / Safety / MAX_EXPOSURE

Approval:

```text
status=APPROVED
approval_id=operation_approval_2026-06-29_bb40f1681a3c
approved_item_ids includes target=true
approved_sides includes BUY=true
demo_order_allowed=true
production_order_allowed=false
max_notional=600000
actual_expected_notional=541000
approval_max_notional_pass=true
```

Safety:

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

## Wire Retry Result

実行:

```bash
python3 scripts/run_demo_submit.py --trade-date 2026-06-29 --root .runtime/operations --execute-demo-order
```

結果:

```text
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

`TACHIBANA_API_SECOND_PASSWORD_FILE`が未設定であるため、final request build boundaryに到達せず、Broker order API呼び出し前に停止した。

## Post-submit / Monitoring

実注文は送信されていないため、post-submit read-only refreshは実施していない。既存Broker read-only artifact上では以下。

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

Daily Reportの`BLOCK`はstale artifactではない。現在runのsubmit guard blockを反映している。

## Local Setup Required

Codexは第二暗証番号の値を知らないため、ユーザーがMac上で直接作成する必要がある。以下はプレースホルダであり、値をCodexやチャットへ貼らないこと。

```bash
mkdir -p .secrets
printf '%s' '<USER_INPUT_SECOND_PASSWORD_ON_LOCAL_MAC>' > .secrets/tachibana_demo_second_password.txt
chmod 600 .secrets/tachibana_demo_second_password.txt
```

local `.env`またはRuntime Configに以下を設定する。

```text
TACHIBANA_API_SECOND_PASSWORD_FILE=.secrets/tachibana_demo_second_password.txt
```

その後、以下を再実行する。

```bash
python3 scripts/run_preflight.py --trade-date 2026-06-29 --root .runtime/operations
python3 scripts/run_demo_submit.py --trade-date 2026-06-29 --root .runtime/operations --execute-demo-order
```

## Prohibited Actions Audit

- Production注文: not executed
- Production Unlock: not executed
- `CLMKabuNewOrder`: not called
- Demo注文: not submitted
- LINE実送信: not executed
- AI再学習: not executed
- Backtest: not rerun
- raw request保存: false
- raw response保存: false
- secret保存: false
- Phase9 artifact / launchd / CLI: not changed

## Remaining Gaps

1. `TACHIBANA_API_SECOND_PASSWORD_FILE`をユーザーのMac上で安全に設定する
2. preflightでsecond password presenceをPASSさせる
3. 同じguard付きwire pathで`CLMKabuNewOrder`を再試行する
4. 実Demo注文がacceptedされた場合、Broker read-only orders / executions / positions / buying_powerを再取得する
5. Fill Monitor / Reconcile / Daily Report / Auditを再実行する

## Next Phase

`PHASE12-Q_SECOND_PASSWORD_PRESENT_DEMO_ORDER_WIRE_EXECUTION`

第二暗証番号ファイル設定後、同じ最小Demo注文を再試行する。
