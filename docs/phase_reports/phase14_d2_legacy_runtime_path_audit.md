# Phase14-D2 Legacy Runtime Path Audit for Demo BUY Test

作成日: 2026-07-07

## Status

```text
PHASE14D2_LEGACY_PATH_FOUND_REDESIGN_REQUIRED
```

Phase14-D2 では、Phase14-D Demo BUY Single-Order Guarded Test の実行経路が Runtime v2 のみだったか、Legacy Runtime / Legacy Order Manager / 旧 Submit 経路を使っていないかを監査した。

本監査では追加 Demo Submit、BUY 再 Submit、SELL Submit、注文取消、注文訂正、Production 注文、本番 Broker API Write、実資金運用、Notification 実送信、launchd / plist 変更、AI 再学習、Backtest / Simulation は行っていない。

## 1. 監査対象

対象:

- `scripts/run_phase14d_demo_buy_guarded.py`
- `src/ai_fund_lab_v2/runtime_v2/demo_buy/guarded_test.py`
- `src/ai_fund_lab_v2/broker/demo_order.py`
- Phase14-D 生成物
  - `.runtime/phase14d/pending_order_plan/pending_order_plan.json`
  - `.runtime/phase14d/approval_artifact/approval_phase14d_demo_buy.json`
  - `reports/phase_reports/phase14_d_demo_buy_single_order_guarded_test.json`
  - `docs/phase_reports/phase14_d_demo_buy_single_order_guarded_test.md`

## 2. Phase14-D 実行結果の確認

Phase14-D JSON summary:

```text
final_decision=PHASE14D_REVIEW_REQUIRED
environment=demo
base_url_is_demo=true
base_url_is_production=false
demo_submit_executed=true
demo_order_accepted=true
submit_classification=ACCEPTED
readonly_after_status=FAILED_BROKER_READONLY_FETCH
post_send_unknown=false
production_order_executed=false
production_broker_api_write_executed=false
pending_plan_path=.runtime/phase14d/pending_order_plan/pending_order_plan.json
approval_artifact_path=.runtime/phase14d/approval_artifact/approval_phase14d_demo_buy.json
```

Demo BUY order は accepted になったが、after-submit ReadOnly の execution detail fetch が失敗したため、Phase14-D は `PHASE14D_REVIEW_REQUIRED` として停止している。

## 3. Import / Call Graph

### 3.1 Runtime v2 harness

`src/ai_fund_lab_v2/runtime_v2/demo_buy/guarded_test.py` imports:

```text
ai_fund_lab_v2.runtime_v2.approval.linkage
ai_fund_lab_v2.runtime_v2.approval.models
ai_fund_lab_v2.runtime_v2.asset.builder
ai_fund_lab_v2.runtime_v2.audit.auditor
ai_fund_lab_v2.runtime_v2.broker_readonly.normalizer
ai_fund_lab_v2.runtime_v2.execution.ledger_projection
ai_fund_lab_v2.runtime_v2.ledger.append
ai_fund_lab_v2.runtime_v2.notification.payload
ai_fund_lab_v2.runtime_v2.pending.consume
ai_fund_lab_v2.runtime_v2.pending.models
ai_fund_lab_v2.runtime_v2.pending.promotion
ai_fund_lab_v2.runtime_v2.reconcile.reconciler
ai_fund_lab_v2.runtime_v2.report.builder
ai_fund_lab_v2.runtime_v2.report.models
```

Current finding:

```text
Runtime v2 harness itself has no direct ai_fund_lab_v2.runtime import.
Runtime v2 harness itself has no direct ai_fund_lab_v2.broker import.
Runtime v2 harness itself has no direct order_manager import.
Runtime v2 harness itself has no demo_ledger reference.
```

### 3.2 Phase14-D script boundary

`scripts/run_phase14d_demo_buy_guarded.py` imports:

```text
ai_fund_lab_v2.broker.demo_order
ai_fund_lab_v2.broker.settings
ai_fund_lab_v2.broker.tachibana_broker_snapshot
ai_fund_lab_v2.runtime.order_command
ai_fund_lab_v2.runtime.runtime_mode
ai_fund_lab_v2.runtime_v2.demo_buy
ai_fund_lab_v2.runtime_v2.demo_buy.guarded_test
```

Call path to submit:

```text
scripts/run_phase14d_demo_buy_guarded.py
↓
run_demo_buy_single_order_guarded_test(...)
↓
submit_func=_submit_demo_buy
↓
TachibanaDemoOrderAdapter().submit_cash_stock_order(OrderCommand(...))
↓
TachibanaCashStockOrderRequest.from_order_command(...)
↓
DemoOrderBrokerTransport.request(...)
↓
CLMKabuNewOrder to Tachibana demo endpoint
```

### 3.3 Broker adapter boundary

`src/ai_fund_lab_v2/broker/demo_order.py` imports:

```text
ai_fund_lab_v2.broker.client
ai_fund_lab_v2.broker.crypto
ai_fund_lab_v2.broker.retry_policy
ai_fund_lab_v2.broker.secrets
ai_fund_lab_v2.broker.settings
ai_fund_lab_v2.broker.tachibana_broker_snapshot
ai_fund_lab_v2.broker.tachibana_codec
ai_fund_lab_v2.broker.tachibana_order_request
ai_fund_lab_v2.broker.transport
ai_fund_lab_v2.runtime.order_command
```

Finding:

```text
Broker demo order adapter still consumes legacy ai_fund_lab_v2.runtime.order_command.OrderCommand.
```

## 4. Legacy Runtime / Legacy Order Manager 判定

| Item | Finding | Classification |
| --- | --- | --- |
| Legacy Runtime entrypoint | 呼んでいない | PASS |
| Legacy Order Manager | 呼んでいない | PASS |
| Phase9 daily runtime | 呼んでいない | PASS |
| operations submit runner | 呼んでいない | PASS |
| demo_ledger Current SoT | 使っていない | PASS |
| Runtime v2 harness direct legacy import | 現在は無い | PASS |
| Script-level `ai_fund_lab_v2.runtime.order_command` | 使用あり | schema/model_reuse_only |
| Broker adapter `ai_fund_lab_v2.runtime.order_command` | 使用あり | schema/model_reuse_only |
| Submit path fully Runtime v2-native | いいえ | REDESIGN_REQUIRED |

Phase14-D は legacy Runtime workflow や legacy Order Manager を Submit 実行に使ってはいない。しかし、実 Broker Submit adapter の入力 schema として旧 `ai_fund_lab_v2.runtime.order_command.OrderCommand` を使っている。

これは `forbidden_submit_path` ではないが、`Runtime v2のみで完結` とは言えない。Phase13 の Legacy Runtime Isolation 原則から見ると、Phase14-D の Submit adapter boundary は Runtime v2-native に再設計するべきである。

## 5. Submit Source Audit

確認結果:

- Submit source は Runtime v2 harness が生成した `pending_order_plan/pending_order_plan.json` 相当である。
- Pending は `promote_order_plan_to_pending(...)` で生成されている。
- Approval は `ApprovalArtifact` と `link_approval_to_pending(...)` で紐付けられている。
- Submit 前に `can_submit_pending_plan(...)` を通している。
- `order_plan/YYYY-MM-DD` から直接 Submit していない。
- `approval_artifact/YYYY-MM-DD` から直接 Submit 対象を推測していない。
- Report / Audit / History / Derived artifact を Submit source にしていない。

判定:

```text
pending_only_submit_source: PASS
```

## 6. Approval / Duplicate Guard Audit

確認結果:

- Pending state は `APPROVED` に遷移している。
- Approval hash は pending plan payload hash として作成され、Pending approval link に保存されている。
- approved item は 1 件のみ。
- Submit 前に `can_submit_pending_plan(pending_plan, set())` を確認している。
- Demo BUY は 1 件のみ。
- POST_SEND_UNKNOWN は発生していない。
- 自動再送は行っていない。

判定:

```text
approval_guard: PASS
duplicate_submit_guard: PASS_FOR_SINGLE_RUN
post_send_unknown_auto_resubmit: NOT_TRIGGERED / PASS
```

補足:

Phase14-D の duplicate guard は single-run scope で確認されている。永続的な duplicate guard は `persistent_ledger/orders.jsonl` などの Runtime v2 Current / Ledger と連動させる必要があり、Phase14-D3 以降で強化する。

## 7. Ledger / Asset / Report / Audit Path Audit

確認結果:

- Broker ReadOnly snapshot を Runtime v2 `BrokerReadOnlyBundle` に正規化している。
- Broker order は `project_order_to_ledger_record(...)` で Ledger order に変換している。
- Broker execution は存在しなかったため Ledger execution は 0 件。
- Broker positions / cash は `project_position_to_ledger_record(...)` / `project_cash_to_ledger_record(...)` を経由している。
- Asset は `build_current_asset_state(...)` で Position / Cash evidence から作っている。
- BrokerOrder のみから Asset を作っていない。
- Reconcile / Report / Notification Payload / Audit は Runtime v2 component で生成している。

判定:

```text
broker_order_only_asset_sot_violation: false
execution_position_cash_evidence_path: PASS
report_audit_current_boundary: PASS
```

## 8. Single Writer Rule Audit

Phase14-D harness は `.runtime/phase14d/` 配下に Phase14-D 専用 artifact を書いている。

書き込み:

```text
.runtime/phase14d/pending_order_plan/pending_order_plan.json
.runtime/phase14d/approval_artifact/approval_phase14d_demo_buy.json
.runtime/phase14d/broker_readonly_before/tachibana_demo_snapshot.json
.runtime/phase14d/broker_readonly_after/tachibana_demo_snapshot.json
reports/phase_reports/phase14_d_demo_buy_single_order_guarded_test.json
docs/phase_reports/phase14_d_demo_buy_single_order_guarded_test.md
```

Finding:

- Production Current path は更新していない。
- `persistent_ledger/state.json` 本線 Current は更新していない。
- `demo_ledger` は使っていない。
- Phase14-D 専用 root への artifact write であり、Single Writer Rule の本線 Current 競合は確認されない。

判定:

```text
single_writer_current_conflict: NOT_FOUND
```

## 9. Phase13-X Legacy Runtime Isolation Guard

Phase14-D2 時点の Runtime v2 harness は legacy import guard に抵触しない。

確認:

```text
src/ai_fund_lab_v2/runtime_v2/demo_buy/guarded_test.py
  no ai_fund_lab_v2.runtime import
  no ai_fund_lab_v2.broker import
  no order_manager import
  no demo_ledger reference
```

Runtime v2 full test:

```text
PYTHONPATH=src:. PYTHONPYCACHEPREFIX=.runtime/pycache_phase14d python3 -m pytest tests/runtime_v2 -q
252 passed
```

ただし、Phase14-D script と Broker adapter boundary には legacy model reuse が残っている。

## 10. Phase14-D 結果の有効性分類

Phase14-D result classification:

```text
PARTIALLY_VALID_REQUIRES_REDESIGN
```

有効扱いできる部分:

- Demo environment guard
- Production endpoint deny
- BUY 1 件のみ
- Runtime v2 Pending generation
- Runtime v2 Approval linkage
- Pending-only Submit source
- Runtime v2 guard before submit
- Demo Broker accepted response
- Broker order list confirmation
- Runtime v2 Ledger / Asset / Report / Audit generation
- Production 注文なし
- 本番 Broker API Write なし

有効扱いできない / 再設計が必要な部分:

- `Runtime v2のみで完結した Demo Submit` という主張
- Broker Submit adapter の Runtime v2-native interface
- legacy `ai_fund_lab_v2.runtime.order_command.OrderCommand` への依存
- after-submit ReadOnly execution detail fetch failure の解消

Phase14-D は「Demo BUY accepted smoke」としては部分有効だが、「Runtime v2 pure Submit acceptance」としては無効化または再実施が必要である。

## 11. 必要な修正方針

Phase14-D3 または Phase14-E 前に以下を行う。

1. Runtime v2-native Submit Command を定義する。
2. Broker adapter が legacy `OrderCommand` ではなく Runtime v2-native command を受け取れるようにする。
3. `scripts/run_phase14d_demo_buy_guarded.py` から `ai_fund_lab_v2.runtime.*` import を除去する。
4. `src/ai_fund_lab_v2/broker/demo_order.py` の legacy `OrderCommand` dependency を adapter boundary で切り離す。
5. Runtime v2 Submit adapter contract test を追加する。
6. after-submit ReadOnly の execution detail fetch failure を診断する。
7. 永続 duplicate guard を ledger order / pending consume と連動させる。
8. 修正後に Demo BUY を再 Submit する場合は、既存 accepted order の状態を Broker ReadOnly で確認し、重複注文にならない別シナリオとして明示承認する。

## 12. Acceptance Criteria Review

| Criteria | Result |
| --- | --- |
| Phase14-D 実行経路の import / call graph を整理している | PASS |
| Runtime v2 のみで完結しているか判定している | PASS: not fully Runtime v2-native |
| Legacy Runtime 参照がある場合、用途を分類している | PASS |
| Submit source が pending_order_plan のみだったか確認している | PASS |
| Approval guard が通っていたか確認している | PASS |
| duplicate submit guard が通っていたか確認している | PASS_FOR_SINGLE_RUN |
| Phase14-D の結果を有効 / 無効 / 部分有効に分類している | PASS: PARTIALLY_VALID_REQUIRES_REDESIGN |
| 必要な修正方針を明記している | PASS |
| 追加注文を行っていない | PASS |

## 13. Final Decision

```text
PHASE14D2_LEGACY_PATH_FOUND_REDESIGN_REQUIRED
```

理由:

- Runtime v2 harness 自体は Runtime v2 component のみで構成され、Legacy Runtime entrypoint、Legacy Order Manager、Phase9 daily runtime、demo_ledger は使っていない。
- Submit source は `pending_order_plan/pending_order_plan.json` 相当であり、order_plan / approval_artifact / Report / Audit から直接 Submit していない。
- しかし、Phase14-D script と Broker demo order adapter は `ai_fund_lab_v2.runtime.order_command.OrderCommand` / `RuntimeMode` を使用しており、Demo Submit adapter boundary が Runtime v2-native ではない。
- そのため、Phase14-D の accepted Demo BUY は部分有効だが、Runtime v2 pure Submit acceptance としては再設計後に再評価が必要である。
