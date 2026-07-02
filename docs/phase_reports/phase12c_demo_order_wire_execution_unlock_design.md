# Phase12-C Demo Order Wire Execution Unlock Design Review

作成日: 2026-06-29

## Status

```text
PHASE12C_DEMO_ORDER_WIRE_EXECUTION_UNLOCK_DESIGN_COMPLETE
DESIGN_REVIEW_ONLY
IMPLEMENTATION_CHANGED_FALSE
DEMO_ORDER_EXECUTED_FALSE
PRODUCTION_ORDER_EXECUTED_FALSE
LINE_SEND_EXECUTED_FALSE
AI_RETRAINING_EXECUTED_FALSE
BACKTEST_RERUN_FALSE
```

## 1. Purpose

Phase12-C は `Demo Order Wire Execution Unlock Design Review` である。

目的は、Production向け運用CLI骨格のうち `scripts/run_demo_submit.py` から、立花証券デモ環境へ実Demo注文を送信するために、どの安全境界を開く必要があるかを明確にすること。

今回は設計レビューのみであり、実装変更、Demo注文、Production注文、Production unlock、LINE実送信、AI再学習、Backtest再実行、Broker API接続は行わない。

## 2. Read Materials / Code

確認した資料:

- `docs/phase_reports/phase12a_demo_full_operation_design.md`
- `docs/phase_reports/phase12b_demo_full_operation_minimal_implementation.md`
- `docs/phase_reports/phase12b_cleanup_production_runtime_cli_naming.md`
- `docs/phase_reports/phase11_final_summary_and_phase12_handoff.md`
- `docs/02_architecture/safety_layer_phase11_refined_design.md`
- `docs/phase_reports/phase10_final_summary_and_phase11_handoff.md`
- `docs/02_architecture/tachibana_demo_order_api_design.md`
- `docs/phase_reports/phase10t_demo_order_live_smoke_readiness_audit.md`

確認したコード:

- `src/ai_fund_lab_v2/operations/`
- `scripts/run_demo_submit.py`
- `tests/phase12/`
- `src/ai_fund_lab_v2/broker/allowlist.py`
- `src/ai_fund_lab_v2/broker/request_builder.py`
- `src/ai_fund_lab_v2/broker/client.py`
- `src/ai_fund_lab_v2/broker/transport.py`
- `src/ai_fund_lab_v2/broker/settings.py`
- `src/ai_fund_lab_v2/broker/secrets.py`
- `src/ai_fund_lab_v2/broker/tachibana_order_request.py`
- `src/ai_fund_lab_v2/runtime/order_authorization.py`
- `src/ai_fund_lab_v2/safety_phase11/`
- related broker/runtime/phase12 tests

## 3. Current State

現在の状態:

```text
Production向け運用CLI骨格: 完了
Runtime package: src/ai_fund_lab_v2/operations/
Runtime artifact root: .runtime/operations/
CLI: scripts/run_preflight.py / run_daily_plan.py / run_demo_submit.py 等
環境判定: .env / TACHIBANA_API_ENV
Demo submit CLI: scripts/run_demo_submit.py
Demo注文wire execution: stub
Production注文: 禁止
```

`run_demo_submit.py` は `ai_fund_lab_v2.operations.operations.run_demo_submit()` を呼ぶ薄いCLIである。現状では approval / safety / exposure guard を通した後も `DemoOrderExecutor().submit(..., dry_run=True)` に留まり、実Broker wire executionには入らない。

## 4. CLMKabuNewOrder Allowlist Review

### 4.1 Current Prohibition

`CLMKabuNewOrder` は現在実行禁止である。

禁止箇所:

- `src/ai_fund_lab_v2/broker/allowlist.py`
  - `FORBIDDEN_CLMIDS` に `CLMKabuNewOrder` が含まれる。
  - `CLMKabuCorrectOrder`
  - `CLMKabuCancelOrder`
  - `CLMKabuCancelOrderAll`
  - `CLMAuthCheckSecondPassword`
  - `CLMAuthStkLoginRequest`
  も禁止されている。
- `TachibanaRequestBuilder.build()` は全CLMIDに `ensure_read_only_clmid()` を通す。
- `HttpPostBrokerTransport.request()` も `ensure_read_only_clmid()` を通す。
- `MockBrokerTransport.register_response()` / `request()` も同様に read-only allowlist を通す。

既存テスト:

- `tests/broker/test_broker_allowlist.py`
  - forbidden CLMID は reject。
- `tests/broker/test_mock_transport.py`
  - `CLMKabuNewOrder` は reject。
- `tests/broker/test_tachibana_request_builder.py`
  - `TachibanaRequestBuilder.build("CLMKabuNewOrder")` は reject。

結論:

```text
clm_kabu_new_order_currently_allowed = false
```

### 4.2 Demo-only Unlock Design

Phase12-Dで開くべき allow path は、既存 read-only allowlist を壊さず、別境界として作る。

設計:

- `ensure_read_only_clmid()` は変更しない、または read-only transportでは引き続き `CLMKabuNewOrder` を禁止する。
- 新たに demo order 専用の allow function を追加する。
  - 例: `ensure_demo_order_clmid(clmid, settings)`
- 許可するCLMIDは `CLMKabuNewOrder` のみ。
- 条件はすべて満たす必要がある。
  - `TACHIBANA_API_ENV=demo`
  - `settings.environment == "demo"`
  - `settings.base_url == DEMO_BASE_URL`
  - `production_order_allowed=false`
  - `RuntimeMode.DEMO`
  - explicit approval exists
  - latest Safety is not `BLOCK` / `SYSTEM_EMERGENCY_STOP`
- production環境では、第二暗証番号が設定されていても必ず fail closed。

禁止維持:

- `CLMKabuCorrectOrder`
- `CLMKabuCancelOrder`
- `CLMKabuCancelOrderAll`
- `CLMAuthCheckSecondPassword`
- `CLMAuthStkLoginRequest`
- all production order CLMIDs

## 5. Second Password / Order Password Boundary

### 5.1 Current State

現在存在するもの:

- `BrokerSettings.second_password_file`
- `.env` variable: `TACHIBANA_API_SECOND_PASSWORD_FILE`
- `TachibanaSecretLoader.classify_second_password_file()`
  - ファイル設定、存在、読取可能、非空を判定する。
  - 値は読み込まない。
  - `value_loaded=false`
  - `value_saved=false`
- `OrderApprovalGate.authorize(..., second_password_present=...)`
  - presence がなければ `BLOCKED_SECOND_PASSWORD_MISSING`。
- `TachibanaCashStockOrderRequest.second_password_present`
  - boolean only。
- `TachibanaCashStockOrderRequestBuilder.build()`
  - `sSecondPassword` は意図的にpayloadへ入れない。

### 5.2 Required Boundary For Phase12-D

実Demo注文では、第二暗証番号の値注入は「最後のrequest assembly直前」に限定する。

設計:

```text
TACHIBANA_API_SECOND_PASSWORD_FILE
↓
Demo-only Secret Loader
↓
ephemeral secret value
↓
live request assembler only
↓
transport.request()
↓
immediate discard
```

ルール:

- `.env` にsecret値を置かない。pathのみ。
- secret値をstdout / log / report / artifactへ出さない。
- secret値を dataclass の `to_dict()` 対象へ入れない。
- `safe_summary` には `second_password_present=true/false` のみ保存。
- request builder以外にsecret値を渡さない。
- testではdummy secret fileのみ使う。
- production environment では secret file が存在しても load しない。
- `CLMAuthCheckSecondPassword` / unlock相当APIは使わない。

追加すべき実装:

- `load_second_password_value_for_demo_order_only()` 相当。
- 返却値は通常のreportable objectではなく、短命なローカル変数として扱う。
- `finally` で参照破棄。
- unit testで dummy secret が artifact / stdout / result JSON に出ないことを確認。

## 6. Transport Execution Boundary

### 6.1 Current State

現在の実Broker API送信層:

- `HttpPostBrokerTransport.request(payload)`
  - read-only allowlistを通す。
  - codec encode/decodeを行う。
  - raw HTTP response textはローカル変数でのみ扱い、戻り値はdecoded dict。
- `TachibanaReadOnlyClient`
  - login / logout / balance / positions / orders / quote など read-only APIを提供。
  - class名も read-only 前提。

### 6.2 Required Boundary

`run_demo_submit.py` から直接HTTP実行してはいけない。

Phase12-Dでは、Broker層に demo order 専用 executor/client を追加する。

推奨責務分離:

```text
operations.run_demo_submit()
  ↓
approval / safety / max exposure / buying power / duplicate / position guards
  ↓
broker.demo_order_executor.submit_cash_stock_order()
  ↓
demo order request builder
  ↓
ephemeral second password injection
  ↓
demo-only transport execution
  ↓
redacted response normalizer
  ↓
operations artifact writer
```

Transport側設計:

- read-only transportはそのまま維持。
- demo order transport pathだけ `ensure_demo_order_clmid()` を使う。
- production URLなら即例外。
- request bodyのsafe summaryは保存可能だが、raw requestは保存禁止。
- raw responseは保存禁止。
- decoded raw response dictもそのままartifactへ渡さず、即 normalizer へ渡す。

### 6.3 Demo / Production Branching Boundary

Phase12-D以降では、Demo / Production の違いを Operations 層へ散らさない。

基本方針:

```text
Operations
  ↓
Order Manager
  ↓
Broker Adapter
  ↓
Demo Broker または Production Broker
```

切り替えは、設定ファイルを読んで Broker Adapter を生成する境界だけで行う。

禁止する設計:

```python
if demo:
    ...

if production:
    ...
```

上記のような環境分岐を `operations.run_demo_submit()`、Order Manager、Safety、Approval、MAX_EXPOSURE、Reconciliation の通常ロジックへ増やさない。

Operations 層の理想フロー:

```text
Approval
↓
Safety
↓
MAX_EXPOSURE
↓
Request Build
↓
broker.submit_order()
↓
Response Normalize
```

Operations 層は `broker.submit_order()` を呼ぶだけにし、DemoかProductionかを意識しない。

Broker Adapter設計:

```text
BrokerInterface
  submit_order()
  cancel_order()
  get_orders()
  get_positions()
  get_buying_power()
```

実装候補:

- `DemoBrokerAdapter`
- `ProductionBrokerAdapter`

Phase12-DではProduction注文は引き続き禁止のため、`ProductionBrokerAdapter.submit_order()` は fail closed のままにする。一方で、Operations層の呼び出し形はProduction Runtimeへ進んでも変えない。

既存構成の尊重:

- 既に `demo_client()` / `production_client()` / `demo_request()` / `production_request()` 相当の関数が存在する場合は、無理に全面置換しない。
- ただし、それらは Broker Factory / Adapter / Transport 層へ閉じ込める。
- ビジネスロジック層からは、環境別関数を直接呼ばない。

設計レビュー観点:

- demo専用関数が Broker / Transport / settings 境界に閉じているか。
- production専用関数が Broker / Transport / settings 境界に閉じているか。
- Operations / Order Manager / Safety / Approval に環境分岐が漏れていないか。
- artifact出力パスやredaction方針が環境別分岐に依存しすぎていないか。
- Broker Factoryが未設定、不正値、判定不能を fail closed にできるか。

## 7. Request Schema Findings

既存設計と `TachibanaCashStockOrderRequestBuilder` から整理する。

| Field | Meaning | Current / Planned handling |
|---|---|---|
| `sCLMID` | 機能ID | `CLMKabuNewOrder` only |
| `sZyoutoekiKazeiC` | 譲渡益課税区分 | `1` 特定口座候補。口座設定との照合は未確認 |
| `sIssueCode` | 銘柄コード | `OrderCommand.issue_code` |
| `sSizyouC` | 市場 | 初期は `00` 東証 |
| `sBaibaiKubun` | 売買区分 | BUY=`3`, SELL=`1` |
| `sCondition` | 執行条件 | 初期は `0` |
| `sOrderPrice` | 注文値段 | MARKET=`0`, LIMIT=`limit_price` |
| `sOrderSuryou` | 注文数量 | `OrderCommand.quantity`。最小単元/100株前提は要確認 |
| `sGenkinShinyouKubun` | 現金信用区分 | 現物=`0` only |
| `sOrderExpireDay` | 注文期日 | 初期は当日=`0` |
| `sGyakusasiOrderType` | 逆指値注文種別 | 通常=`0` |
| `sGyakusasiZyouken` | 逆指値条件 | 通常=`0` |
| `sGyakusasiPrice` | 逆指値値段 | 通常=`*` |
| `sTatebiType` | 建日種類 | 現物=`*` |
| `sTategyokuZyoutoekiKazeiC` | 建玉譲渡益課税区分 | 現物=`*` |
| `sSecondPassword` | 第二暗証番号 | Phase12-Dで ephemeral injection。保存禁止 |

Endpoint:

- Demo: `https://demo-kabuka.e-shiten.jp/e_api_v4r9`
- Production: `https://kabuka.e-shiten.jp/e_api_v4r9`

Production endpointでは `CLMKabuNewOrder` を送らない。

不明点 / Phase12-Dで確認すべき点:

- `sZyoutoekiKazeiC=1` が対象デモ口座で常に妥当か。
- `sOrderSuryou` の最小単元。通常100株想定だが、1株注文可否は銘柄/市場/口座仕様を確認する。
- `sCondition=0` の意味と寄付き前指値での受付挙動。
- `sOrderExpireDay=0` が当日扱いで正しいか。
- 指値が制限値幅外の場合の reject code。
- 約定しない価格の指値を出した場合のキャンセル要否。Cancel APIは未解禁のため、初回smokeでは当日失効を前提にできるか確認が必要。
- `CLMKabuNewOrder` response の order number field名。既存 normalizer は `sOrderNumber` / `sOrderOrderNumber` / `order_number` 候補を見るが、実responseで要確認。

## 8. Response Normalizer / Redaction Plan

保存可能な normalized response:

```json
{
  "order_submit_status": "ACCEPTED | REJECTED_OR_UNKNOWN",
  "broker_order_ref_hash": "sha256:...",
  "submitted_at": "ISO-8601",
  "environment": "demo",
  "side": "BUY",
  "issue_code": "7203",
  "quantity": "100",
  "order_type": "CASH_EQUITY",
  "price_type": "LIMIT",
  "limit_price": "1234",
  "result_code": "redacted_or_safe_code",
  "result_classification": "ACCEPTED | REJECTED | UNKNOWN",
  "warning_code": "safe_code_or_empty",
  "redaction_status": "PASS",
  "raw_request_saved": false,
  "raw_response_saved": false,
  "second_password_value_saved": false,
  "plaintext_order_id_saved": false,
  "plaintext_execution_id_saved": false
}
```

保存禁止:

- raw request
- raw response
- request body containing `sSecondPassword`
- second password
- auth id
- account/customer id
- session token / virtual URL
- plaintext broker order id
- plaintext execution id
- private key

Current reusable code:

- `normalize_redacted_order_submit_result(raw)`
  - order id候補をhash化。
  - `raw_order_id_saved=false`
  - `raw_response_saved=false`

Phase12-Dで必要な拡張:

- 実response field名に合わせた normalizer coverage。
- result code / warning code の safe field whitelist。
- raw response dictをartifact writerへ渡さない型境界。
- testで raw order id / dummy secret が JSON に出ないことを確認。

## 9. Approval / Safety / Guard Checklist

実Demo注文送信前に必ず通す条件:

- `.env` / Broker settings が `demo`。
- `settings.base_url == DEMO_BASE_URL`。
- production endpointではない。
- `production_order_allowed=false`。
- `demo_order_allowed=true`。
- approval artifact exists。
- approval not expired。
- approval item scope matches:
  - approval id
  - issue code
  - side
  - quantity
  - max_notional
- latest Safety check exists and is fresh。
- Safety result is not `BLOCK`。
- Safety result is not `SYSTEM_EMERGENCY_STOP` / `EMERGENCY_STOP`。
- MAX_EXPOSURE PASS。
- buying_power PASS。
- duplicate active orderなし。
- position mismatchなし。
- cash equity only。
- margin / credit order禁止。
- price_type allowlisted。
- market code allowlisted。
- run lock acquired。
- raw/secret persistence audit PASS。

`NON_BLOCKING_REVIEW` の扱い:

- 単独ではSystem emergencyではない。
- ただし実Demo注文では、Human Approval artifactに明示的に含まれていることを必須にする。

失敗時:

- fail closed。
- no retry。
- no cancel。
- no resubmit。
- no auto sell。
- Human Review / report only。

## 10. Demo Order Smoke Plan

Phase12-D以降で実行する最小 smoke plan。

目的:

- 約定益を狙わず、Demo order wire path / broker acceptance / redaction / fill monitor / reconciliation を検証する。

推奨手順:

1. Preflight
   - demo環境確認。
   - latest broker snapshot。
   - buying_power確認。
   - orders_count確認。
   - duplicate active orderなし。
2. Order Plan
   - 1 itemのみ。
   - 現物。
   - limit order。
   - max notionalを小さくする。
3. Approval
   - item単位の explicit approval。
   - approval expiry短め。
4. Submit
   - `CLMKabuNewOrder` one-shot。
   - retryなし。
   - cancelなし。
   - raw保存なし。
5. Post-submit
   - `CLMOrderList`
   - `CLMOrderListDetail`
   - `CLMGenbutuKabuList`
   - FillMonitor
   - Reconciliation

注文内容候補:

- 原則は低価格・流動性あり・最小単元。
- ただし「1株」は立花API / 市場 / 口座で可能か不明。現時点では100株を最小単元として扱う設計が既存。
- 成行は使わない。
- 可能なら約定しにくい指値で受付確認のみを狙う。

重要な未決事項:

- 約定しない指値を出した場合、Cancel APIを解禁しないまま当日失効を待つ運用で安全か。
- 取消が必須なら、Phase12-Dでは `CLMKabuCancelOrder` を開かず、Phase12-Eとして別設計レビューに分ける。
- 売りsmokeは買いが約定し、Broker positionで確認できた後にだけ検討する。

## 11. Phase12-D Required Implementation Tasks

優先順位付き最小タスク:

1. Demo order CLMID allow boundary
   - `ensure_demo_order_clmid()` 相当。
   - `CLMKabuNewOrder` only。
   - demo URL / demo env / production prohibited。
2. Demo order broker executor/client
   - read-only clientとは別境界。
   - `run_demo_submit.py` から直接HTTPしない。
3. Ephemeral second password loader
   - `TACHIBANA_API_SECOND_PASSWORD_FILE` を使う。
   - demo order pathだけ値を読む。
   - valueはartifact/log/stdoutへ出さない。
4. Live request assembler
   - `TachibanaCashStockOrderRequestBuilder` のpayloadに `sSecondPassword` を最後に注入。
   - raw request保存禁止。
5. Demo-only transport execution
   - `CLMKabuNewOrder` one-shot。
   - no retry / no cancel / no correction。
6. Redacted response normalizer
   - order ref hashのみ保存。
   - safe result code whitelist。
7. operations integration
   - `run_demo_submit()` の dry-run/stub を demo wire executor へ差し替える。
   - explicit flagは維持。
8. Post-submit read-only reconciliation
   - order list / detail / positions / fill monitor。
9. Tests
   - production env blocks。
   - production URL blocks。
   - missing second password blocks。
   - dummy second password not persisted。
   - `CLMKabuNewOrder` demo-only allowed。
   - cancel/correct/second-password-check remain forbidden。
   - raw response not persisted。
   - plaintext order id not persisted。
   - approval expired blocks。
   - Safety BLOCK / SYSTEM_EMERGENCY_STOP blocks。
10. Smoke runbook
   - exact target issue / price / quantity / approval expiration / observation checklist。

## 12. Final Judgement

```text
PHASE12C_DEMO_ORDER_WIRE_EXECUTION_UNLOCK_DESIGN_COMPLETE
CLM_KABU_NEW_ORDER_CURRENTLY_ALLOWED_FALSE
DEMO_ONLY_UNLOCK_REQUIRES_PHASE12D_IMPLEMENTATION
PRODUCTION_ORDER_REMAINS_FORBIDDEN
```

## Forbidden Actions Confirmation

- implementation_changed: false
- demo_order_executed: false
- production_order_executed: false
- production_unlock_executed: false
- line_send_executed: false
- ai_retraining_executed: false
- backtest_rerun: false
- broker_api_connected: false
- raw_response_saved: false
- plaintext_secret_saved: false
