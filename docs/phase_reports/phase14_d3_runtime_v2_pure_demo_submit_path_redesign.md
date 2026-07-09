# Phase14-D3 Runtime v2 Pure Demo Submit Path Redesign

作成日: 2026-07-07

## Status

```text
PHASE14D3_PURE_SUBMIT_PATH_READY
```

Phase14-D3 では、Phase14-D2 の監査結果を受け、Runtime v2 正規フローだけで Demo Submit へ到達するための pure submit path を再設計し、最小実装と dry-run test を追加した。

本フェーズでは追加 Demo Submit、BUY 再 Submit、SELL Submit、注文取消、注文訂正、Production 注文、本番 Broker API Write、実資金運用、Notification 実送信、launchd / plist 変更、AI 再学習、Backtest / Simulation は行っていない。

## 1. Phase14-D2 からの前提

Phase14-D2 の結論:

```text
PHASE14D2_LEGACY_PATH_FOUND_REDESIGN_REQUIRED
```

理由:

- `runtime_v2/demo_buy/guarded_test.py` 自体は Runtime v2 component のみを使っていた。
- しかし `scripts/run_phase14d_demo_buy_guarded.py` と `broker/demo_order.py` が旧 `ai_fund_lab_v2.runtime.order_command.OrderCommand` / `RuntimeMode` を参照していた。
- Phase14-D は Demo BUY accepted smoke としては部分有効だが、Runtime v2 pure Submit acceptance としては再評価が必要である。

## 2. 旧依存箇所の整理

旧依存:

```text
scripts/run_phase14d_demo_buy_guarded.py
  ai_fund_lab_v2.runtime.order_command
  ai_fund_lab_v2.runtime.runtime_mode

src/ai_fund_lab_v2/broker/demo_order.py
  ai_fund_lab_v2.runtime.order_command

src/ai_fund_lab_v2/broker/tachibana_order_request.py
  ai_fund_lab_v2.runtime.order_command
```

分類:

| Dependency | Current Use | D3 Classification |
| --- | --- | --- |
| `runtime.order_command.OrderCommand` | Broker submit request input | NG: legacy runtime order command reuse |
| `runtime.runtime_mode.RuntimeMode` | Demo / Production authority | NG: legacy runtime mode as submit authority |
| Tachibana low-level client / transport | Broker API execution | OK: low-level client reuse |
| Tachibana request builder / response parser | Request / response codec | OK: schema / response parser reuse |
| order_plan history | Evidence only | NG as direct submit source |
| approval_artifact history | Evidence only | NG as direct submit source |

## 3. Runtime v2 Pure Submit Path

Pure path:

```text
pending_order_plan/pending_order_plan.json
↓
Runtime v2 Pending Runtime
↓
Runtime v2 Approval Link
↓
Runtime v2 Submit Preflight
↓
RuntimeV2SubmitCommand
↓
RuntimeV2DemoSubmitAdapter
↓
Broker adapter implementation
↓
Low-level Tachibana client / transport / parser
```

Runtime v2 Submit authority is:

```text
RuntimeV2SubmitCommand
```

Not authority:

```text
legacy OrderCommand
legacy RuntimeMode
order_plan/YYYY-MM-DD
approval_artifact/YYYY-MM-DD
Report
Audit
```

## 4. Added Runtime v2 Models

追加:

- `src/ai_fund_lab_v2/runtime_v2/submit/models.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/guards.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/__init__.py`

主な model:

```text
RuntimeV2SubmitCommand
RuntimeV2SubmitPreflightResult
RuntimeV2SubmitResult
```

`RuntimeV2SubmitCommand` は以下を含む。

- environment
- pending_plan_id
- pending_item_id
- approval_hash
- symbol
- side
- quantity
- order_type
- price_type
- limit_price
- estimated_amount
- target_session_date
- source_current_path

`source_current_path` は `pending_order_plan/pending_order_plan.json` を正とする。

## 5. Added Broker Adapter Boundary

追加:

- `src/ai_fund_lab_v2/runtime_v2/broker_adapter/models.py`
- `src/ai_fund_lab_v2/runtime_v2/broker_adapter/fake_demo_submit.py`
- `src/ai_fund_lab_v2/runtime_v2/broker_adapter/__init__.py`

Broker adapter protocol:

```text
RuntimeV2DemoSubmitAdapter.submit(RuntimeV2SubmitCommand) -> RuntimeV2SubmitResult
```

この boundary の方針:

- Runtime v2 は legacy `OrderCommand` を渡さない。
- Broker adapter implementation は low-level Tachibana client / transport / parser を再利用してよい。
- Broker adapter implementation は Submit authority として legacy Runtime model を要求してはならない。

## 6. Runtime v2 内 Guard

`run_submit_preflight(...)` で以下を確認する。

- environment is demo
- base URL classification is demo
- base URL classification is not production
- live order allowed
- Submit source is `pending_order_plan/pending_order_plan.json`
- Pending state is `APPROVED`
- Approval artifact is `APPROVED`
- Approval pending_plan_id matches Pending
- Pending approval link exists
- Pending approval hash matches Approval artifact hash
- approved item exists in Pending
- duplicate submit guard passes
- item side is BUY or SELL
- quantity is positive
- estimated amount does not exceed max order amount

## 7. Submit Source 固定

Submit source:

```text
pending_order_plan/pending_order_plan.json
```

禁止:

```text
order_plan/YYYY-MM-DD
approval_artifact/YYYY-MM-DD
Report
Audit
History
Derived artifact
```

## 8. Existing Broker Client Reuse Policy

OK:

- Tachibana low-level HTTP transport
- Tachibana codec
- Tachibana response parser
- secret loader
- demo-only allowlist / transport guard
- redaction / sanitizer

NG:

- legacy Runtime `OrderCommand` as submit authority
- legacy Runtime `RuntimeMode` as submit authority
- Legacy Runtime entrypoint
- Legacy Order Manager submit
- `demo_ledger` as Current SoT
- direct submit from order_plan / approval_artifact history

## 9. Tests

追加:

```text
tests/runtime_v2/test_phase14d3_pure_submit_path.py
```

Coverage:

- Runtime v2 Pending / Approval から `RuntimeV2SubmitCommand` を作れる。
- fake demo adapter が Runtime v2 command を受け取れる。
- Approval link missing blocks.
- duplicate pending submit blocks.
- production endpoint classification blocks.
- non-pending submit source blocks.
- fake adapter does not call broker API.
- Runtime v2 legacy isolation guard remains passing.

## 10. Verification

Phase14-D3 targeted test:

```text
PYTHONPATH=src:. PYTHONPYCACHEPREFIX=.runtime/pycache_phase14d3 python3 -m pytest tests/runtime_v2/test_phase14d3_pure_submit_path.py -q
```

Result:

```text
4 passed
```

Runtime v2 full test:

```text
PYTHONPATH=src:. PYTHONPYCACHEPREFIX=.runtime/pycache_phase14d3 python3 -m pytest tests/runtime_v2 -q
```

Result:

```text
256 passed
```

## 11. Phase14-D 再試験条件

Phase14-D retry / D4 へ進む条件:

1. Actual Tachibana Demo Submit adapter が `RuntimeV2SubmitCommand` を直接受け取る。
2. `scripts/run_phase14d_demo_buy_guarded.py` から `ai_fund_lab_v2.runtime.*` import を除去する。
3. `broker/demo_order.py` または新 adapter が legacy `OrderCommand` なしで submit payload を構築する。
4. Runtime v2 Submit preflight を必ず通す。
5. Pending source は `pending_order_plan/pending_order_plan.json` のみ。
6. Approval hash / pending link / approved item を確認する。
7. Persistent duplicate guard を ledger order / pending consume と連動させる。
8. Phase14-D で accepted になった既存 Demo BUY order の Broker 状態を ReadOnly で確認する。
9. 再 Submit が重複注文にならない別シナリオであることを明示する。
10. Production 注文、本番 Broker API Write、実資金運用は禁止継続。

## 12. Acceptance Criteria

| Criteria | Result |
| --- | --- |
| Runtime v2 pure Submit path が設計されている | PASS |
| 旧 `ai_fund_lab_v2.runtime.order_command` / `RuntimeMode` を Submit authority として使わない | PASS in new Runtime v2 path |
| Legacy Runtime entrypoint を呼ばない | PASS |
| Legacy Order Manager を使わない | PASS |
| Submit source は `pending_order_plan/pending_order_plan.json` のみ | PASS |
| Approval guard が Runtime v2 内で必須 | PASS |
| Duplicate submit guard が Runtime v2 内で必須 | PASS |
| Environment guard が demo-only を保証する | PASS |
| Production endpoint へ到達しない | PASS in D3 dry-run |
| Broker adapter 境界が明確 | PASS |
| Low-level API client 再利用と Legacy Runtime 依存の境界が分類されている | PASS |
| 追加 Demo Submit を行っていない | PASS |
| Phase14-D 再試験条件が明記されている | PASS |

## 13. Final Decision

```text
PHASE14D3_PURE_SUBMIT_PATH_READY
```

理由:

- Runtime v2-native Submit command / preflight / result model を追加した。
- Runtime v2 broker adapter protocol を追加した。
- fake demo adapter dry-run により Runtime v2 command の受け渡しを確認した。
- Submit source を `pending_order_plan/pending_order_plan.json` に固定した。
- Approval / duplicate / environment / demo-only guard を Runtime v2 内に定義した。
- Runtime v2 full test が PASS し、legacy isolation guard に抵触していない。
- 追加 Demo Submit、BUY 再 Submit、SELL Submit、注文取消、注文訂正は行っていない。
