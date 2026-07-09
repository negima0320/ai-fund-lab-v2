# Phase14-D22 Current SoT Write / Read-back E2E

作成日: 2026-07-07

## 最終判定

**PHASE14D22_CURRENT_SOT_WRITE_READBACK_PASS**

Phase14-D21で修正した固定Current Pathに対して、D15保存済みEvidenceを使い、Ledger / Asset / Pending / Runtime State のwrite/read-backを確認した。

Broker API呼び出し、Submit、Production注文、Notification実送信、launchd/plist変更、AI再学習、Backtest/Simulationは行っていない。

## 入力Evidence

Broker APIの再取得は行わず、既存D15成果物のみを入力にした。

```text
.runtime/phase14d15/asset_state/asset_state.json
.runtime/phase14d15/broker_readonly_after/tachibana_demo_snapshot.json
.runtime/phase14d15/pending_order_plan/pending_order_plan.json
.runtime/phase14d15/ledger_events/phase14d15_sell_events.json
```

`.runtime/phase14d15/...` はCurrentではなく、History / Evidence / per-run artifactとして扱った。

## 書き込み先

以下のcanonical Current Pathへwriteした。

```text
.runtime/persistent_ledger/state.json
.runtime/persistent_ledger/orders.jsonl
.runtime/persistent_ledger/executions.jsonl
.runtime/persistent_ledger/positions.jsonl
.runtime/persistent_ledger/cash.jsonl
.runtime/persistent_ledger/events.jsonl
.runtime/pending_order_plan/pending_order_plan.json
.runtime/runtime_state/current_state.json
```

`.runtime/demo/persistent_ledger/state.json` へのwriteはguardで拒否されることを確認し、実ファイルも作られていない。

## 実装内容

追加:

```text
src/ai_fund_lab_v2/runtime_v2/ledger/writer.py
src/ai_fund_lab_v2/runtime_v2/current_state/writer.py
src/ai_fund_lab_v2/runtime_v2/current_sot_write_readback.py
scripts/run_phase14d22_current_sot_write_readback_e2e.py
tests/runtime_v2/test_phase14d22_current_sot_write_readback_e2e.py
```

確認したこと:

- Asset Runtime writerで `state.json` をwriteできる
- Ledger Runtime writerで `orders/executions/positions/cash/events` JSONLをwriteできる
- Pending writerでfixed `pending_order_plan` をwriteできる
- Runtime State writerでfixed `runtime_state/current_state.json` をwriteできる
- mode-rooted Current pathはwriter guardで拒否される
- Current State Readerがfixed pathをread-backする
- Reconcile / Report / Auditがfixed Current由来のAsset / Ledger / Pendingを使える

## Read-back結果

```text
persistent_ledger/state.json: VALID
persistent_ledger/orders.jsonl: VALID
persistent_ledger/executions.jsonl: VALID
persistent_ledger/positions.jsonl: VALID
persistent_ledger/cash.jsonl: VALID
persistent_ledger/events.jsonl: VALID
pending_order_plan/pending_order_plan.json: VALID
runtime_state/current_state.json: VALID
```

D15相当のSELL後状態:

- 7203 position quantity: `0.0`
- cash: `19999648.0`
- buying_power: `19999648.0`
- Reconcile findings: `0`
- Audit findings: `0`

## テスト

```text
python3 -m pytest tests/runtime_v2/test_phase14d22_current_sot_write_readback_e2e.py
```

結果:

```text
4 passed
```

```text
python3 -m pytest tests/runtime_v2
```

結果:

```text
290 passed
```

## Acceptance Criteria

| Criteria | 判定 |
| --- | --- |
| fixed Current pathにstateを書ける | PASS |
| mode-rooted Current pathは拒否される | PASS |
| read-backが成功 | PASS |
| D15相当のAsset StateをCurrent SoTへ反映できる | PASS |
| Reconcile / Report / Auditがfixed Currentを使う | PASS |
| `tests/runtime_v2` PASS | PASS |

## 結論

D22により、D21で定義したfixed Current Pathに対して、D15相当のBUY/SELL結果をCurrent SoTとしてwriteし、Current State Readerでread-backできることを確認した。

これで次フェーズでは、Current SoTを前提にしたmanual operation rehearsal、Report/Blog生成接続、またはmulti-day rehearsalへ進める。
