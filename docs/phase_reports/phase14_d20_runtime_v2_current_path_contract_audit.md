# Phase14-D20 Runtime v2 Current Path Contract Audit

作成日: 2026-07-07

## 最終判定

**PHASE14D20_CURRENT_PATH_CONTRACT_GAP_FOUND**

分類: **CURRENT_PATH_CONTRACT_GAP_FOUND**

Phase13設計で固めたRuntime v2 Current Path Contractは、Currentを固定Pathで扱い、phase番号配下にもruntime mode別配下にも置かないという原則である。

一方、現実装のRuntime v2 path resolver / current state reader / testsは `.runtime/<mode>/...` をCurrent pathとして扱っており、D20で再確認したcanonical contractとズレている。

Phase14-D15/D16のBUY/SELL E2Eは、Runtime v2 pure submit pathの手動Demo E2Eとしては有効である。ただし、Current Path Contract準拠E2Eとしては未達である。

## D20で再確定するCanonical Current Path

Currentは固定Pathであり、phase番号やruntime modeで分岐しない。

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

このcontractでは、以下を禁止する。

- `.runtime/phase14d15/...` をCurrentとして扱うこと
- `.runtime/phase14d*/...` をCurrentとして扱うこと
- `.runtime/demo/persistent_ledger/...` をCurrentとして扱うこと
- `.runtime/production/persistent_ledger/...` をCurrentとして扱うこと
- mode別Current pathを作ること
- Report / Audit / Notification PayloadをCurrent入力にすること

runtime modeやBroker環境の違いは、pathではなく以下で管理する。

- runtime request / runtime_mode
- broker adapter
- broker config / credential guard
- environment field
- submit guard
- audit metadata

## History / Evidence / Derived の分類

以下はHistory / Evidence / Derivedであり、Currentではない。

```text
.runtime/phase14d15/...
.runtime/phase14d*/...
reports/phase_reports/...
reports/public/...
report artifacts
notification payloads
audit artifacts
broker readonly snapshots
submit responses
approval artifacts
per-run asset_state projections
```

`.runtime/phase14d15/asset_state/asset_state.json` はD15 run内で作られたasset projectionである。Currentに近い内容を持つが、canonical Current SoTではない。

## Phase13設計との照合

Phase13のRuntime v2設計は、以下を明記している。

- Current / History / Derivedを分離する
- Runtime Currentを固定Path化する
- Submit対象を `pending_order_plan/pending_order_plan.json` に固定する
- Asset Current SoTは `persistent_ledger/state.json`
- Ledger Current / Historyは `persistent_ledger/*.jsonl`
- ReportはDerivedでありCurrentではない
- Reconcile / Report / AuditはCurrent Writerではない
- History artifactをCurrent決定元として自動選択しない
- Phase13用の一時保存場所をRuntime Currentとして使わない
- `YYYY-MM-DD` やphase別artifactをCurrentとして使わない

特に `docs/02_architecture/runtime_architecture_v2.md` は、Current fixed pathとして以下を挙げている。

```text
pending_order_plan/pending_order_plan.json
persistent_ledger/state.json
persistent_ledger/orders.jsonl
persistent_ledger/executions.jsonl
persistent_ledger/positions.jsonl
persistent_ledger/cash_history.jsonl
persistent_ledger/events.jsonl
runtime_state/current_state.json
```

D20のcanonical contractとの差分として、Phase13文書と現実装には `cash_history.jsonl` が残っている。一方、D20では `cash.jsonl` をcanonicalとする。これは追加のcontract gapであり、次フェーズで名称を統一する必要がある。

## 現実装とのgap

### 1. path resolverがmode別Current pathを返している

対象:

```text
src/ai_fund_lab_v2/runtime_v2/storage/path_resolver.py
```

現実装の `resolve_current_path("demo", "demo", "persistent_ledger_state")` は以下を返す。

```text
.runtime/demo/persistent_ledger/state.json
```

これはD20 canonical contractの以下と一致しない。

```text
.runtime/persistent_ledger/state.json
```

実装上のズレ:

- `_runtime_root(mode)` が `.runtime/<mode>` を返す
- Current pathがruntime mode別root配下になる
- testsも `.runtime/demo/...` を期待している

判定: **GAP**

### 2. current state readerがmode別Current pathを読む

対象:

```text
src/ai_fund_lab_v2/runtime_v2/current_state/reader.py
```

`read_current_state()` は `resolve_current_path()` を使うため、現実装では `.runtime/<mode>/...` を読む。

D20 contractでは、readerは以下を読むべきである。

```text
.runtime/persistent_ledger/state.json
.runtime/pending_order_plan/pending_order_plan.json
.runtime/runtime_state/current_state.json
.runtime/notification_delivery/delivery_ledger.jsonl
```

判定: **GAP**

### 3. testsがmode別Current pathを期待している

対象例:

```text
tests/runtime_v2/test_phase13_l_path_resolver.py
tests/runtime_v2/test_phase13_m_current_state_reader.py
tests/runtime_v2/test_phase13_n_orchestrator_skeleton.py
tests/runtime_v2/test_phase13_o_asset_state_writer.py
tests/runtime_v2/test_phase13_p_pending_reader_writer.py
```

これらは `.runtime/demo/...` をCurrent pathとして期待している。

判定: **GAP**

### 4. cash path名が統一されていない

D20 canonical:

```text
.runtime/persistent_ledger/cash.jsonl
```

Phase13文書 / 現実装:

```text
persistent_ledger/cash_history.jsonl
.runtime/<mode>/persistent_ledger/cash_history.jsonl
```

対象:

```text
src/ai_fund_lab_v2/runtime_v2/storage/path_resolver.py
src/ai_fund_lab_v2/runtime_v2/contracts/current_state_contracts.py
docs/02_architecture/runtime_architecture_v2.md
tests/runtime_v2/
```

判定: **GAP**

### 5. D15 per-run asset_stateがCurrent相当として生成されている

対象:

```text
src/ai_fund_lab_v2/broker/phase14d15_demo_sell_test.py
.runtime/phase14d15/asset_state/asset_state.json
```

D15では `build_current_asset_state()` で作ったasset stateを、Reconcile / Report / Auditに渡し、最後にphase専用artifactへ保存している。

```text
.runtime/phase14d15/asset_state/asset_state.json
```

これはD15 run内のprojectionとしては有効だが、Current代替として扱ってはいけない。

判定: **注意付きPASS**

D15 codeはcanonical Currentへwriteしていないため、phase配下Currentの恒久化違反は発生していない。ただし、per-run asset_stateがCurrent相当の入力として使われており、Current read-back acceptanceにはなっていない。

### 6. `.runtime/demo/persistent_ledger/` 案は採用しない

D19では、現実装のpath resolverに合わせて `.runtime/demo/persistent_ledger/state.json` をcanonical候補のように記載した箇所がある。

D20ではこの案を採用しない。

理由:

- Currentは固定Pathである
- Currentをruntime mode別pathに置かない
- demo/prodの違いはpathではなくruntime mode / broker adapter / configで扱う
- mode別Currentを許すと、Production readiness時にCurrent SoTが分裂する

判定: **D19のmode別path提案はD20でsupersede**

## Writer Contract監査

### Asset Runtime

対象:

```text
src/ai_fund_lab_v2/runtime_v2/asset/writer.py
```

`write_current_asset_state(path, state)` は存在し、明示pathへ `CurrentAssetState` をwriteできる。

ただし、このwriterはpathを引数で受けるため、canonical path enforcementはまだ弱い。D20 contractでは、Asset Runtime writerは `.runtime/persistent_ledger/state.json` を正規writer pathとして扱う必要がある。

現状:

- writer skeletonあり
- D15/D11等のPhase14-D系からは未接続
- `.runtime/persistent_ledger/state.json` へwriteしていない
- `.runtime/demo/persistent_ledger/state.json` を許すtestがある

判定: **GAP**

### Ledger Runtime

対象:

```text
src/ai_fund_lab_v2/runtime_v2/ledger/
src/ai_fund_lab_v2/runtime_v2/execution/ledger_projection.py
```

Ledgerはappend/dedup helperとprojection modelがあるが、canonical `.runtime/persistent_ledger/*.jsonl` writerとしては未接続である。

現状:

- `orders.jsonl`, `executions.jsonl`, `positions.jsonl`, `cash.jsonl`, `events.jsonl` へのcanonical writerが未完成
- 実装・docsには `cash_history.jsonl` が残っている
- Phase14-D系ではledger recordsがin-memoryまたはper-run artifactに閉じている

判定: **GAP**

### Reconcile / Report / Audit

対象:

```text
src/ai_fund_lab_v2/runtime_v2/reconcile/
src/ai_fund_lab_v2/runtime_v2/report/
src/ai_fund_lab_v2/runtime_v2/audit/
```

現行テストでは、Reconcile / Report / Auditが `write_current_asset_state` や `write_pending_order_plan` をimportしないことを確認している。

判定: **PASS**

Reconcile / Report / AuditはCurrentを書いていない。これはPhase13 Single Writer Ruleと整合する。

## Phase14-D系 scripts / harness監査

Phase14-D系は、以下のようにper-run rootへartifactを出力している。

```text
.runtime/phase14d5/...
.runtime/phase14d7/...
.runtime/phase14d8/...
.runtime/phase14d11/...
.runtime/phase14d15/...
```

これらはHistory / Evidence / per-run artifactとして許容される。

ただし、D15のようにper-run asset projectionをそのままReport / Reconcile / Auditへ渡す流れは、手動E2Eとしては有効でも、Current fixed path read/write contractの検証にはならない。

判定:

- per-run artifact出力: **PASS**
- per-run artifactをCurrent代替として恒久運用すること: **禁止**
- Current path read-back E2E: **未達**

## D15/D16の有効範囲の再分類

### D15

Phase14-D15は以下として有効。

```text
MANUAL_DEMO_BUY_SELL_E2E_WITH_PER_RUN_ARTIFACT_ONLY
```

有効な範囲:

- Runtime v2 pure submit path
- Demo SELL 1件
- Position 100 -> 0
- Cash / Buying Power更新
- OrderList + Position + Cash evidence
- BrokerOrder単体からAssetを作らない原則
- Reconcile PASS
- Report生成
- Notification Payload生成のみ
- Audit PASS
- Production注文なし
- 本番Broker API Writeなし
- launchd/plist変更なし

未達の範囲:

- `.runtime/persistent_ledger/state.json` へのAsset Current write
- `.runtime/persistent_ledger/*.jsonl` へのLedger write
- Current state readerによるcanonical fixed path read-back
- Current path contract準拠E2E

### D16

Phase14-D16のBUY/SELL E2E acceptance summaryは、Demo BUY/SELL操作面のまとめとして有効。

ただし、D20観点では以下に再分類する。

```text
BUY_SELL_DEMO_OPERATION_ACCEPTED_CURRENT_PATH_CONTRACT_PENDING
```

D16は「Runtime v2 pure submit path成立」を示すが、「Current Path Contract成立」は示していない。

## launchd運用前に必須修正か

必須修正である。

理由:

- Currentがmode別pathに分裂すると、日次運用でどれがSoTか曖昧になる
- phase配下artifactをCurrent代替にすると、最新状態探索が日付・phase依存になる
- Current reader / orchestrator / report source refsが実ファイルとズレる
- Submit guardのduplicate判定やPending consumptionが長期運用で不安定になる
- Production readiness時にdemo/prod path分岐が安全境界とSoT境界を混同する

launchd / plist再開、日次自動運用、multi-day rehearsalの前に、Current Path Contractを修正してからread/write/reconcile/report/auditの再試験が必要である。

## 次フェーズで必要な修正方針

Phase14-D21以降で、以下を行う。

1. path resolverをD20 canonical fixed pathへ修正する
   - `.runtime/<mode>/...` をCurrentでは使わない
   - `resolve_current_path()` は `.runtime/...` 直下を返す
   - mode / environmentはvalidation metadataとして扱う

2. current state readerをcanonical fixed pathへ合わせる
   - `.runtime/persistent_ledger/state.json`
   - `.runtime/pending_order_plan/pending_order_plan.json`
   - `.runtime/runtime_state/current_state.json`
   - `.runtime/notification_delivery/delivery_ledger.jsonl`

3. cash path名を統一する
   - D20 canonicalに従い `persistent_ledger/cash.jsonl` へ寄せる
   - `cash_history.jsonl` を残す場合は互換migration扱いにし、Current canonicalにはしない

4. Asset Runtime writerをcanonical fixed path専用にする
   - `.runtime/persistent_ledger/state.json`
   - Asset Runtime以外のwrite禁止を維持する

5. Ledger Runtime writerをcanonical fixed pathへ接続する
   - `.runtime/persistent_ledger/orders.jsonl`
   - `.runtime/persistent_ledger/executions.jsonl`
   - `.runtime/persistent_ledger/positions.jsonl`
   - `.runtime/persistent_ledger/cash.jsonl`
   - `.runtime/persistent_ledger/events.jsonl`

6. Phase14-D系 per-run artifactsはHistory / Evidenceへ明確に隔離する
   - `.runtime/phase14d*/...` はCurrentではない
   - Report / Auditにはsource refとして表示してよい
   - Planning / Approval / SubmitのCurrent入力にはしない

7. D15相当のE2EをCurrent Path Contract込みで再試験する
   - Broker evidence -> Ledger writer -> Asset writer -> Current reader read-back
   - Reconcile / Report / Auditがcanonical Currentを読めること
   - SubmitはPending fixed pathのみ
   - 追加Broker APIやSubmitは別フェーズで明示許可された場合のみ

## Acceptance Criteria 判定

| Criteria | 判定 |
| --- | --- |
| Current固定Pathの正を明記している | PASS |
| phase番号配下Current禁止を明記している | PASS |
| demo/prod mode別Current path禁止を明記している | PASS |
| `.runtime/phase14d15` 配下がHistory/Evidenceであることを明記している | PASS |
| `.runtime/demo/persistent_ledger` 案を採用しないことを明記している | PASS |
| 現実装とのgapを列挙している | PASS |
| launchd前に必須修正か判定している | PASS |
| D15/D16の有効範囲を再分類している | PASS |
| 次フェーズで必要な修正方針を明記している | PASS |
| コード変更していない | PASS |
| Broker API呼び出ししていない | PASS |
| Submitしていない | PASS |
| Currentへwriteしていない | PASS |

## 結論

D20の監査では、Phase13設計思想としてのCurrent固定Pathは確認できた。

しかし、現実装は `.runtime/<mode>/...` をCurrent pathとして扱っており、D20で再確定した「Currentをdemo/prodなどruntime mode別pathに置かない」というcontractに反している。

また、Phase14-D15/D16はDemo BUY/SELL手動E2Eとして有効だが、canonical Current Path Contract準拠E2Eではない。

したがって、最終判定は **PHASE14D20_CURRENT_PATH_CONTRACT_GAP_FOUND** とする。
