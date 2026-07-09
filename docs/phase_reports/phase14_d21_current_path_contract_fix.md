# Phase14-D21 Runtime v2 Current Path Contract Fix

作成日: 2026-07-07

## 最終判定

**PHASE14D21_CURRENT_PATH_CONTRACT_FIX_COMPLETE**

Phase14-D20で確認した `.runtime/<mode>/...` Current path依存を廃止し、Runtime v2 Current pathを `.runtime/` 直下の固定Pathへ統一した。

Broker API呼び出し、Submit、Production注文、Notification実送信、launchd/plist変更、AI再学習、Backtest/Simulationは行っていない。

## Canonical Current Path

D21後のRuntime v2 Current pathは以下に統一する。

```text
.runtime/persistent_ledger/state.json
.runtime/persistent_ledger/orders.jsonl
.runtime/persistent_ledger/executions.jsonl
.runtime/persistent_ledger/positions.jsonl
.runtime/persistent_ledger/cash.jsonl
.runtime/persistent_ledger/events.jsonl
.runtime/pending_order_plan/pending_order_plan.json
.runtime/runtime_state/current_state.json
.runtime/notification_delivery/delivery_ledger.jsonl
```

Current pathでは以下を使わない。

```text
.runtime/demo/...
.runtime/production/...
.runtime/simulation/...
.runtime/backtest/...
.runtime/phase14d*/...
```

runtime modeやdemo/productionの違いはpathではなく、runtime request、broker adapter、config、credential guard、environment field、submit guard、audit metadataで扱う。

## 実装修正

### 1. path resolver

対象:

```text
src/ai_fund_lab_v2/runtime_v2/storage/path_resolver.py
```

変更:

- `resolve_current_path()` が `.runtime/<mode>/...` を返す挙動を廃止
- Current pathは常に `.runtime/...` 直下を返す
- `mode` / `environment` は引き続きvalidationするが、Current storage rootには使わない
- `persistent_ledger_cash_history` を `persistent_ledger_cash` に整理
- `persistent_ledger/cash_history.jsonl` を `persistent_ledger/cash.jsonl` に整理

### 2. current state reader

対象:

```text
src/ai_fund_lab_v2/runtime_v2/current_state/reader.py
```

`read_current_state()` は `resolve_current_path()` を経由するため、D21後は固定Current pathを読む。

例:

```text
read_current_state(mode="demo", environment="demo", object_type="persistent_ledger_state")
-> .runtime/persistent_ledger/state.json
```

### 3. Current State Contract

対象:

```text
src/ai_fund_lab_v2/runtime_v2/contracts/current_state_contracts.py
```

変更:

- `persistent_ledger_cash_history` を `persistent_ledger_cash` に変更
- Ledger Runtime writer contractは維持
- Reconcile / Report / AuditがCurrent writerではないことは維持

### 4. Asset / Pending writer guard

対象:

```text
src/ai_fund_lab_v2/runtime_v2/asset/writer.py
src/ai_fund_lab_v2/runtime_v2/pending/writer.py
```

変更:

- `.runtime/demo/...`
- `.runtime/production/...`
- `.runtime/simulation/...`
- `.runtime/backtest/...`

のようなmode-rooted Current pathを拒否するguardを追加した。

これにより、明示pathでwriterを呼ぶ場合でも、mode別Current pathへ誤ってwriteしない。

phase配下artifactはHistory / Evidence / per-run artifactとして扱うため、このguardでは `.runtime/phase14d*/...` をmode-rooted Current pathとしては扱わない。

### 5. architecture document

対象:

```text
docs/02_architecture/runtime_architecture_v2.md
```

変更:

- `persistent_ledger/cash_history.jsonl` を `persistent_ledger/cash.jsonl` へ整理
- D21 canonical Current Pathに合わせた

Phase13の過去phase reportは履歴資料として残し、D20/D21でsupersedeされたものとして扱う。

### 6. tests

対象:

```text
tests/runtime_v2/
```

変更:

- `.runtime/demo/...` をCurrent pathとして期待していたテストを固定Pathへ修正
- path resolver testにmode-rootが含まれないことを追加
- `persistent_ledger_cash` / `cash.jsonl` の期待値へ修正
- writerがmode-rooted Current pathを拒否することを確認

## Phase配下artifactの扱い

以下はCurrentではない。

```text
.runtime/phase14d15/asset_state/asset_state.json
.runtime/phase14d15/report/runtime_report.json
.runtime/phase14d15/notification/notification_payload.json
.runtime/phase14d*/...
```

これらはHistory / Evidence / Derived / per-run artifactとして扱う。

D15/D16は引き続き以下の分類とする。

- D15: `MANUAL_DEMO_BUY_SELL_E2E_WITH_PER_RUN_ARTIFACT_ONLY`
- D16: `BUY_SELL_DEMO_OPERATION_ACCEPTED_CURRENT_PATH_CONTRACT_PENDING`

D21により、次フェーズでCurrent SoT write/read-back E2Eへ進む前提が整った。

## Reconcile / Report / Audit

D21後も以下を維持している。

- ReconcileはCurrentを書かない
- ReportはCurrentを書かない
- AuditはCurrentを書かない
- Notification PayloadはCurrentを書かない
- Report / Audit / NotificationはDerived / EvidenceでありCurrent SoTではない

## テスト結果

対象テスト:

```text
python3 -m pytest tests/runtime_v2
```

結果:

```text
286 passed
```

補助確認として、Current path contract関連の対象テストも個別に実行し、62件PASSを確認した。

## 禁止事項の確認

| 禁止事項 | 結果 |
| --- | --- |
| Broker API呼び出し | 未実行 |
| Submit | 未実行 |
| Production注文 | 未実行 |
| Notification実送信 | 未実行 |
| launchd/plist変更 | 未実行 |
| AI再学習 | 未実行 |
| Backtest/Simulation | 未実行 |
| Currentへの実write | 未実行 |

## Acceptance Criteria

| Criteria | 判定 |
| --- | --- |
| `.runtime/<mode>/...` をCurrent pathとして使わない | PASS |
| `.runtime/demo/persistent_ledger` を使わない | PASS |
| fixed Current pathのみを使う | PASS |
| `tests/runtime_v2` PASS | PASS |
| D15/D16は再分類済み | PASS |
| 次にCurrent SoT write/read-back E2Eへ進める | PASS |

## 次フェーズへの引き継ぎ

Phase14-D22以降では、Broker evidence / Runtime v2 projectionを以下へ正規writeし、read-backまで検証する。

```text
.runtime/persistent_ledger/state.json
.runtime/persistent_ledger/orders.jsonl
.runtime/persistent_ledger/executions.jsonl
.runtime/persistent_ledger/positions.jsonl
.runtime/persistent_ledger/cash.jsonl
.runtime/persistent_ledger/events.jsonl
```

次の検証では、per-run artifactではなくcanonical Current fixed pathをCurrent State Readerで読み戻し、Reconcile / Report / Auditへ渡す必要がある。

## 結論

Runtime v2 Current Path Contractは、D21で `.runtime/` 直下の固定Pathへ修正された。

`.runtime/<mode>/...` Current path依存は廃止され、`.runtime/demo/persistent_ledger` はCurrent pathとして採用しない。Runtime mode差分はpathではなくruntime_mode / broker adapter / configで扱う。

最終判定は **PHASE14D21_CURRENT_PATH_CONTRACT_FIX_COMPLETE** とする。
