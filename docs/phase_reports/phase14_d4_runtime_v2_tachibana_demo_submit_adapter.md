# Phase14-D4 Runtime v2 Tachibana Demo Submit Adapter

作成日: 2026-07-07

## Status

```text
PHASE14D4_DEMO_SUBMIT_ADAPTER_READY
```

Phase14-D4 では、`RuntimeV2SubmitCommand` を旧 `OrderCommand` / `RuntimeMode` を経由せず、Tachibana Demo Submit adapter が直接受け取れるようにした。

今回は接続実装と dry-run / guard 確認までである。追加 Demo Submit、BUY 再 Submit、SELL Submit、注文取消、注文訂正、Production 注文、本番 Broker API Write、実資金運用、Notification 実送信、launchd / plist 変更、AI 再学習、Backtest / Simulation は行っていない。

## 1. 目的

目的:

```text
RuntimeV2SubmitCommand
↓
Runtime v2 Tachibana Demo Submit Adapter
↓
Tachibana request shape / response parser / transport boundary
```

この経路を作り、旧 Runtime `OrderCommand` を Submit authority として使わない。

## 2. 実装内容

追加:

- `src/ai_fund_lab_v2/broker/runtime_v2_demo_submit_adapter.py`
- `tests/runtime_v2/test_phase14d4_tachibana_demo_submit_adapter.py`

更新:

- `src/ai_fund_lab_v2/broker/tachibana_order_request.py`

主な変更:

- `RuntimeV2TachibanaDemoSubmitAdapter` を追加。
- `RuntimeV2SubmitCommand` を直接受け取る `submit(...)` / `preflight(...)` を追加。
- Phase14-D4 では dry-run 固定で、実 Broker API を呼ばない。
- `TachibanaCashStockOrderRequest.from_runtime_v2_submit_command(...)` を追加。
- Tachibana request builder は旧 Runtime enum だけに依存せず、Runtime v2 command から request shape を作れる。

## 3. Demo-only / Production Guard

Adapter guard:

- `command.environment == "demo"`
- `settings.environment == "demo"`
- `settings.base_url == DEMO_BASE_URL`
- `settings.base_url != PROD_BASE_URL`
- `command.source_current_path == "pending_order_plan/pending_order_plan.json"`
- `command.side == "BUY"` for Phase14-D4 dry-run
- `command.live_order_allowed == true`
- `command.quantity > 0`

Production endpoint / production credential path は `BLOCKED` とする。

## 4. Dry-run / Preflight Mode

Phase14-D4 の adapter は実 Submit 直前で止める。

Dry-run result:

```text
status=DRY_RUN_READY
submitted=false
accepted=false
broker_api_called=false
raw_request_saved=false
raw_response_saved=false
secret_saved=false
```

実 Submit は次フェーズまで行わない。

## 5. 9000番台銘柄除外

Phase14-D の 9432 は Demo order accepted になったが、after-submit execution detail fetch が失敗した。

Phase14-D4 では、次回の Demo 約定テスト候補から 9000 番台銘柄を除外する guard を追加した。

```text
command.symbol.startswith("9") -> BLOCKED
```

次回 BUY 再試験は、既存注文とは別シナリオとして、9000 番台以外の銘柄を選ぶ。

## 6. Existing Phase14-D Order Check Plan

次回 Demo Submit 前に必ず行うこと:

1. Phase14-D で accepted になった既存注文の ReadOnly order status を確認する。
2. open order / accepted order / unknown execution detail が残っている場合は新規 Submit しない。
3. 約定詳細取得 failure を診断する。
4. 次回 BUY は既存注文と同一 pending / same issue / same order scenario として扱わない。
5. duplicate guard は ledger order / pending consume と連動させる。

## 7. Runtime v2 Guard 維持

Phase14-D4 は Phase14-D3 の Runtime v2 Submit preflight を前提にする。

維持する guard:

- pending-only submit
- approval required
- duplicate submit guard
- environment guard
- demo-only guard
- production endpoint block
- max order amount guard
- POST_SEND_UNKNOWN auto-resubmit forbidden

## 8. Low-level Reuse / Legacy Boundary

OK:

- Tachibana request shape builder
- Tachibana codec
- Tachibana transport
- Tachibana response parser
- secret loader
- redaction / sanitizer

NG:

- legacy Runtime `OrderCommand` as submit authority
- legacy Runtime `RuntimeMode` as submit authority
- Legacy Runtime entrypoint
- Legacy Order Manager submit
- order_plan / approval_artifact direct submit

## 9. Verification

Phase14-D4 targeted test:

```text
PYTHONPATH=src:. PYTHONPYCACHEPREFIX=.runtime/pycache_phase14d4 python3 -m pytest tests/runtime_v2/test_phase14d4_tachibana_demo_submit_adapter.py -q
```

Result:

```text
6 passed
```

Related broker/runtime test:

```text
PYTHONPATH=src:. PYTHONPYCACHEPREFIX=.runtime/pycache_phase14d4 python3 -m pytest tests/broker/test_tachibana_order_request_builder.py tests/broker/test_tachibana_demo_order_smoke_foundation.py tests/runtime_v2/test_phase14d4_tachibana_demo_submit_adapter.py -q
```

Result:

```text
21 passed
```

Runtime v2 full test:

```text
PYTHONPATH=src:. PYTHONPYCACHEPREFIX=.runtime/pycache_phase14d4 python3 -m pytest tests/runtime_v2 -q
```

Result:

```text
262 passed
```

## 10. Acceptance Criteria

| Criteria | Result |
| --- | --- |
| RuntimeV2SubmitCommand を直接受け取る adapter がある | PASS |
| 旧 OrderCommand / RuntimeMode を Submit authority にしていない | PASS |
| Legacy Runtime entrypoint を呼ばない | PASS |
| dry-run / preflight で実 Submit 直前まで確認できる | PASS |
| demo-only guard がある | PASS |
| production endpoint が BLOCK される | PASS |
| pending-only submit が維持される | PASS |
| approval 必須が維持される | PASS |
| duplicate guard が維持される | PASS |
| 9000 番台銘柄をデモ約定テスト対象から除外している | PASS |
| 今回追加 Demo Submit を行っていない | PASS |

## 11. Final Decision

```text
PHASE14D4_DEMO_SUBMIT_ADAPTER_READY
```

理由:

- Runtime v2 command を直接受ける Tachibana Demo Submit Adapter を追加した。
- adapter は dry-run で実 Submit 直前まで確認でき、Broker API を呼ばない。
- production endpoint / non-demo environment / non-pending source / 9000 番台を BLOCK できる。
- 旧 Runtime `OrderCommand` / `RuntimeMode` を Submit authority にしない経路を用意した。
- 追加 Demo Submit、BUY 再 Submit、SELL Submit、注文取消、注文訂正は行っていない。
