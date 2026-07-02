# Phase12-N Demo Wire Unlock Preflight Review

## Status

`PHASE12N_DEMO_WIRE_UNLOCK_PREFLIGHT_REVIEW_COMPLETE`

Phase12-Mで復元したBUY itemについて、Demo Order Wire Executionを実装・解禁する前のPreflight Reviewを実施した。

今回は設計レビュー・監査のみ。Demo Order Wire Execution、`CLMKabuNewOrder`呼び出し、Demo注文、Production注文、Production Unlock、LINE実送信、AI再学習、Backtest再実行は行っていない。

## Reviewed Runtime State

対象business date:

`2026-06-29`

対象Order Plan:

`operation_plan_2026-06-29_6464fd8851d4`

Phase12-M後の状態:

| Item | Value |
| --- | ---: |
| feature rows | 4,303 |
| universe rows before hard gate | 4,303 |
| universe rows after hard gate | 3,681 |
| candidate count | 3,681 |
| opportunity count | 4,303 |
| BUY order plan count | 1 |

## BUY Item Review

現在のBUY item:

| Field | Value |
| --- | --- |
| item_id | `buy_2026-06-29_92560_001` |
| code / issue_code | `92560` |
| side | `BUY` |
| quantity | `100` |
| order_type | `CASH_EQUITY` |
| price_type | `LIMIT` |
| limit_price | `0` |
| expected_notional | `0` |
| estimated_value | `0` |
| approval_required | `true` |
| production_order_allowed | `false` |
| demo_order_allowed | `false` |
| environment | `demo` |

BUY signalは復元しているが、このitemはそのままwire-readyではない。`LIMIT`注文で`limit_price=0`、`expected_notional=0`のため、Phase12-Oでは最小Demo注文smoke用に有効な価格・notionalへ正規化する必要がある。

## Approval Review

本線 `.runtime/operations` の最新Approval artifactは、Phase12-Nで最新Order Planに対してdry-run生成し直した。

Current runtime approval:

| Field | Value |
| --- | --- |
| status | `PENDING` |
| approved_item_ids | `[]` |
| approved_sides | `[]` |
| demo_order_allowed | `false` |
| production_order_allowed | `false` |
| max_notional | `0` |
| safety_result_hash | present |
| broker_snapshot_hash | present |

一時rootでApproval作成を確認した。

```text
root=/private/tmp/phase12n_approval_review
status=APPROVED
approved_item_ids=["buy_2026-06-29_92560_001"]
approved_sides=["BUY"]
demo_order_allowed=true
production_order_allowed=false
max_notional=100000
```

Approvalなしではsubmit候補へ進まないことも一時rootで確認した。

```text
root=/private/tmp/phase12n_no_approval_root
run_demo_submit.py status=BLOCK
blocks=["approval_missing_or_not_demo_allowed"]
broker_order_api_called=false
```

## Safety / MAX_EXPOSURE Review

Safety result:

```text
status=ALLOW
system_guard=true
```

Broker basis:

| Field | Value |
| --- | ---: |
| broker_actual_equity | 20,000,000 |
| buying_power | 20,000,000 |
| current_exposure | 0 |
| max_total_exposure_ratio | 0.85 |
| max_allowed_exposure | 17,000,000 |

MAX_EXPOSUREはPaper Ledgerではなく、Broker actual equity / buying_power basisへ接続されている。

ただし現在のBUY itemは`estimated_value=0`なので、現状のprojected exposureは0として通る。Phase12-Oでは実際に使う最小notionalを設定した後、Safety / MAX_EXPOSUREを再評価する必要がある。

## Demo-only Guard Review

確認結果:

- Runtime environment: `demo`
- `production_order_allowed=false`
- Demo Order Wire Execution: `false`
- Production endpoint使用は禁止
- Production credential使用は禁止
- `run_demo_submit.py`は`validate_demo_environment`でdemo環境以外をfail closedにする
- `production_order_allowed=true`はsubmit guardでBLOCK

Operations層には環境guard呼び出しはあるが、Phase12-OでDemo / Production差分をさらにビジネスロジックへ散らさないこと。実際の切替はRuntime Config、Broker Factory、Broker Adapter、Transport境界に閉じる。

## CLMKabuNewOrder Review

現状、`CLMKabuNewOrder`は引き続き禁止されている。

禁止箇所:

- `src/ai_fund_lab_v2/broker/allowlist.py`
  - `FORBIDDEN_CLMIDS`に`CLMKabuNewOrder`
- `src/ai_fund_lab_v2/broker/request_builder.py`
  - `TachibanaRequestBuilder.build()`が`ensure_read_only_clmid()`を通す
- `src/ai_fund_lab_v2/broker/transport.py`
  - `HttpPostBrokerTransport.request()`が`ensure_read_only_clmid()`を通す
  - `MockBrokerTransport`もread-only allowlistを通す

Phase12-Oで開くべき場所:

read-only allowlistを弱めず、Broker Adapter / Transport層にdemo-order専用allow境界を追加する。

許可条件:

- `TACHIBANA_API_ENV=demo`
- demo base URL
- `demo_order_wire_execution=true`
- `production_order_allowed=false`
- explicit Approvalあり
- Safetyが`BLOCK` / `SYSTEM_EMERGENCY_STOP`ではない
- second passwordが最終request build境界でのみロードされる

Productionでは必ずfail closed。

## Second Password Boundary

既存設定:

`TACHIBANA_API_SECOND_PASSWORD_FILE`

既存ローダ:

`TachibanaSecretLoader.classify_second_password_file()`

現状はpresence分類のみ。

- `value_loaded=false`
- `value_saved=false`
- artifactへsecret値を保存しない

Phase12-Oで必要な境界:

```text
TACHIBANA_API_SECOND_PASSWORD_FILE
↓
demo-order-only secret loader
↓
final request assembly local variable
↓
sSecondPassword injection
↓
transport.request()
↓
discard
```

保存禁止:

- second password value
- raw request
- raw response
- account id
- session token
- plaintext broker order id
- plaintext execution id

## Request Schema Review

既存の`TachibanaCashStockOrderRequestBuilder`が持つDemo注文形状:

| Field | Meaning |
| --- | --- |
| `sCLMID` | `CLMKabuNewOrder` |
| `sZyoutoekiKazeiC` | account type, default `1` |
| `sIssueCode` | issue code |
| `sSizyouC` | market, default `00` |
| `sBaibaiKubun` | BUY=`3`, SELL=`1` |
| `sOrderPrice` | order price |
| `sOrderSuryou` | quantity |
| `sGenkinShinyouKubun` | cash equity, default `0` |
| `sOrderExpireDay` | validity / expire |
| `sSecondPassword` | Phase12-O final boundaryでのみ注入 |

現状のbuilderは`CLMKabuNewOrder` payload shapeを作れるが、`sSecondPassword`は意図的に省略している。Phase12-Oでは、safe summaryには出さず、最終payloadにだけ短命注入する。

未確定事項:

- 最小Demo smokeで使う有効期限値
- 受付確認のみを狙う遠い指値にするか、最小現実的指値にするか

## Response Redaction Plan

保存可:

- `submit_status`
- `broker_order_ref_hash`
- `submitted_at`
- `side`
- `code`
- `quantity`
- `order_type`
- `price_type`
- `redaction_status`
- `raw_response_saved=false`
- `secret_saved=false`

保存禁止:

- raw request
- raw response
- second password
- account id
- session token
- plaintext broker order id
- plaintext execution id

既存の`normalize_redacted_order_submit_result()`はbroker order idをhash化する前提。Phase12-Oではraw decoded responseをartifactへ渡さず、normalizerへ即時投入する。

## Phase12-O Minimal Demo Order Smoke Plan

Phase12-Oでの最小実行計画:

1. Broker read-only snapshotを更新する
2. Phase12-MのBUY item `buy_2026-06-29_92560_001` を使う
3. ただし`limit_price=0` / `expected_notional=0`を、最小Demo注文として有効な正のnotionalへ正規化する
4. 成行ではなく、可能なら指値で受付確認を優先する
5. Safety / MAX_EXPOSUREを実notionalで再評価する
6. explicit Demo Approvalを作成する
7. second passwordを最終request build境界でのみロードする
8. Demo-only Broker Adapterから`CLMKabuNewOrder`を呼ぶ
9. responseをredacted normalized artifactとして保存する
10. fill_monitor / broker orders / executions / positions / reconcile / daily_reportで追跡する

Phase12-Nでは上記を実行していない。

## Blocking Issues Before Wire

直ちにwire executionへ進む場合のblocker:

- 現在のBUY itemは`LIMIT price=0`、`expected_notional=0`でwire-readyではない
- `CLMKabuNewOrder`はread-only allowlist / transportでまだ禁止
- second password値ロード・注入境界が未実装
- Demo order wire transport / executorはstubのまま
- 本線Approval artifactは`PENDING`

## Required Phase12-O Tasks

Phase12-Oの最小実装タスク:

1. read-only allowlistを弱めず、demo-order-only `CLMKabuNewOrder` allow functionを追加する
2. Demo Broker Order Adapter / Transport pathを追加し、demo環境・demo base URL・`production_order_allowed=false`以外はfail closedにする
3. `TACHIBANA_API_SECOND_PASSWORD_FILE`からsecond passwordを最終request build境界でのみ短命ロードする
4. Phase12-M BUY itemを最小Demo注文用に有効なprice / notionalへ正規化する
5. BUY itemを含むexplicit Approvalを作り、`approved_sides=["BUY"]`、bounded `max_notional`を持たせる
6. 実notionalでSafety / MAX_EXPOSUREを再評価する
7. `sSecondPassword`をsafe summaryやartifactに出さず、final payloadにのみ注入する
8. Broker submit responseをhash化・redaction済みartifactへ正規化する
9. production環境、production base URL、approval missing、second password missing、raw response保存、adapter外`CLMKabuNewOrder`をすべてfail closedにするテストを追加する
10. 明示的なPhase12-O承認後にのみ最小Demo注文smokeを実行する

## Verification

実施した確認:

```bash
python3 scripts/run_approval_prepare.py --trade-date 2026-06-29 --root .runtime/operations
python3 scripts/run_demo_submit.py --trade-date 2026-06-29 --root /private/tmp/phase12n_no_approval_root
python3 scripts/run_approval_prepare.py --trade-date 2026-06-29 --root /private/tmp/phase12n_approval_review --approve --approver-label phase12n_review --max-notional 100000
```

結果:

- 本線Approval dry-run: PASS / PENDING
- Approvalなしsubmit check: BLOCK / `approval_missing_or_not_demo_allowed`
- 一時Approval review: APPROVED / BUY item included
- broker order API called: false
- Demo Order Wire Execution: false
- CLMKabuNewOrder called: false

Phase9 artifact / launchd / CLI / moduleは変更していない。
