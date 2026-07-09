# Phase14-D19 Runtime v2 Current SoT Reality Audit

作成日: 2026-07-07

## 最終判定

**PHASE14D19_CURRENT_SOT_GAP_FOUND**

Phase14-D15 の 7203 BUY -> SELL Demo E2E は、Runtime v2 pure submit path、Broker ReadOnly evidence、OrderList + Position + Cash / Buying Power reflection、Reconcile、Report、Audit の手動E2Eとしては有効である。

ただし、Phase13で定義した Runtime v2 Asset Current SoT である `persistent_ledger/state.json` への永続Current writeまでは成立していない。したがって D15 の有効範囲は次の分類とする。

**MANUAL_E2E_WITH_PER_RUN_ARTIFACT_ONLY**

## 監査範囲

今回の監査では、Submit、Broker API呼び出し、通知実送信、launchd/plist変更、コード変更は行っていない。確認した対象は以下である。

- `.runtime/`
- `.runtime/phase14d15/`
- `.runtime/phase14d15/report/runtime_report.json`
- `.runtime/phase14d15/notification/notification_payload.json`
- `reports/phase_reports/phase14_d15_demo_sell_single_order_guarded_test.json`
- `reports/phase_reports/phase14_d16_buy_sell_e2e_acceptance_summary.json`
- Runtime v2 ledger / asset writer実装
- Runtime v2 path resolver
- Runtime v2 current state reader
- Runtime v2 report generator
- `tests/runtime_v2/`

## Current SoT 実体確認

### `.runtime/persistent_ledger/state.json`

存在しない。

### `.runtime/persistent_ledger/`

存在しない。

### `.runtime/demo/persistent_ledger/state.json`

存在しない。

Runtime v2 の path resolver 上は、`persistent_ledger_state` のcanonical Current pathは以下に解決される。

```text
.runtime/demo/persistent_ledger/state.json
```

しかし現環境では `.runtime` 配下に `persistent_ledger` を含む実ファイル・実ディレクトリは確認できなかった。

## D15 BUY/SELL結果の保存場所

Phase14-D15 の成果物は、canonical Current SoTではなく phase専用のper-run artifactとして保存されている。

```text
.runtime/phase14d15/broker_readonly_before/tachibana_demo_snapshot.json
.runtime/phase14d15/broker_readonly_after/tachibana_demo_snapshot.json
.runtime/phase14d15/pending_order_plan/pending_order_plan.json
.runtime/phase14d15/approval_artifact/approval_phase14d15_demo_sell.json
.runtime/phase14d15/submit_response/runtime_v2_submit_result.json
.runtime/phase14d15/ledger_events/phase14d15_sell_events.json
.runtime/phase14d15/asset_state/asset_state.json
.runtime/phase14d15/report/runtime_report.json
.runtime/phase14d15/notification/notification_payload.json
.runtime/phase14d15/audit/audit_result.json
```

このうち、D15 SELL後のasset current相当は以下に保存されている。

```text
.runtime/phase14d15/asset_state/asset_state.json
```

このartifactには、以下の値が保存されている。

- environment: `demo`
- source: `phase14d15_orderlist_position_cash_reflection`
- cash: `19999648.0`
- buying_power: `19999648.0`
- total_equity: `23297648.0`
- market_value: `3298000.0`
- positions: 7 records
- 7203: D15 SELL後はpositionとして残っていない

## Cash / Buying Power / Position の保存場所

D15 SELL後の cash / buying_power / positions は、以下の複数artifactに保存されている。

### Broker ReadOnly evidence

```text
.runtime/phase14d15/broker_readonly_before/tachibana_demo_snapshot.json
.runtime/phase14d15/broker_readonly_after/tachibana_demo_snapshot.json
```

これらはBroker状態のevidenceであり、Runtime v2がBrokerをSource of Truthとして読む入力である。

### Runtime v2 asset projection

```text
.runtime/phase14d15/asset_state/asset_state.json
```

これはD15 run内で作られたCurrent Asset State相当のprojectionである。ただし、canonical Current SoTではなくper-run artifactである。

### Runtime v2 report

```text
.runtime/phase14d15/report/runtime_report.json
```

ReportはDerived artifactでありCurrentではない。Report内のasset sectionは `persistent_ledger/state.json` をsource refとして指しているが、現実の保存先は `.runtime/phase14d15/asset_state/asset_state.json` である。

### Phase report summary

```text
reports/phase_reports/phase14_d15_demo_sell_single_order_guarded_test.json
reports/phase_reports/phase14_d16_buy_sell_e2e_acceptance_summary.json
```

これらは監査・受入結果の要約であり、Current SoTではない。

## Runtime v2 writer実装の確認

Runtime v2には `write_current_asset_state(path, state)` が存在する。

```text
src/ai_fund_lab_v2/runtime_v2/asset/writer.py
```

このwriterは `CurrentAssetState` を `persistent_ledger/state.json` payloadへ変換し、明示されたpathへwriteできる。ただし、D15の実行経路ではこのwriterは呼ばれていない。

D15の実行経路は以下である。

1. Broker ReadOnly before snapshot取得
2. Pending SELL / Approval作成
3. Runtime v2 submit preflight
4. Tachibana Demo Submit AdapterでSELL submit
5. Broker ReadOnly after snapshot取得
6. `project_order_to_ledger_record`
7. `project_position_to_ledger_record`
8. `project_cash_to_ledger_record`
9. `build_current_asset_state`
10. `run_reconciliation`
11. `build_runtime_report`
12. `build_notification_payload`
13. `run_audit`
14. phase専用artifactへ `_write_json`

この流れでは、asset stateはin-memoryで生成され、Reconcile / Report / Auditに渡されたあと、以下へper-run保存される。

```text
.runtime/phase14d15/asset_state/asset_state.json
```

一方、以下には保存されていない。

```text
.runtime/demo/persistent_ledger/state.json
.runtime/demo/persistent_ledger/orders.jsonl
.runtime/demo/persistent_ledger/executions.jsonl
.runtime/demo/persistent_ledger/positions.jsonl
.runtime/demo/persistent_ledger/cash_history.jsonl
.runtime/demo/persistent_ledger/events.jsonl
```

## Ledger永続化の確認

Runtime v2 ledgerにはappend/dedup系の軽量helperは存在するが、D15ではcanonical `persistent_ledger/*.jsonl` への永続appendは行われていない。

D15で生成されたledger相当のデータは、以下にper-run artifactとして保存されている。

```text
.runtime/phase14d15/ledger_events/phase14d15_sell_events.json
```

また、ledger orders / positions / cash records はD15 run内でtupleとして生成され、Reconcile / Reportへ渡されているが、canonical ledger JSONLにはwriteされていない。

## Report生成元

D15の `runtime_report.json` は、canonical Current SoTから再読込して生成されたものではない。D15 run内で生成された以下のin-memory objectから生成されている。

- `asset_state`
- `pending_plan`
- `ledger_orders`
- `ledger_positions`
- `ledger_cash`
- `after_bundle.orders`
- `after_bundle.positions`
- `after_bundle.cash`
- `approval`
- `reconciliation`
- `ledger_events`

ReportはDerived artifactであり、Currentではない。Report内には以下のsource refsが含まれる。

```text
persistent_ledger/state.json
persistent_ledger/orders.jsonl
persistent_ledger/positions.jsonl
persistent_ledger/events.jsonl
```

しかし、現環境ではこれらの実ファイルは存在しない。これは設計意図上のsource refと、現実の保存先がずれている状態である。

## Reconcileが読んだsource

D15のReconcileは、canonical Current SoTからreadしたわけではない。D15 run内でBroker ReadOnly after snapshotからnormalize / projectした以下を直接受け取っている。

- `ledger_orders`
- `ledger_executions=()`
- `broker_orders`
- `broker_executions=()`
- `broker_positions`
- `broker_cash`
- `asset_state`

したがって、D15のReconcile PASSは「D15 run内のBroker evidenceとin-memory/per-run asset projectionの整合性」として有効である。

一方で、「canonical Current SoTに永続化されたasset stateを読み戻してReconcile PASSした」ことは確認できていない。

## Phase13 Current / History / Derived 分離とのズレ

Phase13の設計原則では、Asset Current SoTは `persistent_ledger/state.json` と定義されていた。

現実のD15成果物では、以下の分離は概念上は維持されている。

- Broker ReadOnly snapshot: Evidence / History相当
- Asset State JSON: Current相当のprojection
- Report / Notification / Audit: Derived

ただし、Current相当のprojectionがcanonical fixed pathにwriteされていないため、Current / History / Derived分離は運用可能な形では未完成である。

特に以下のズレがある。

- path resolverは `.runtime/demo/persistent_ledger/state.json` をCurrent pathとして定義している
- current state readerはこのfixed pathを読む前提である
- orchestrator preflightは `persistent_ledger_state` がmissing / unknown / invalidなら `REVIEW_REQUIRED` へ止める
- D15は `.runtime/phase14d15/asset_state/asset_state.json` へwriteしている
- D15 Reportは `persistent_ledger/state.json` をsource refとしているが、その実ファイルは存在しない

## 影響範囲

### D15手動E2Eへの影響

D15は、以下の範囲では有効である。

- Runtime v2 pure submit path
- Pending-only submit
- Approval必須
- duplicate guard
- demo-only guard
- SELL quantity guard
- Tachibana Demo Submit Adapter
- Broker ReadOnly order status sync
- Position 100 -> 0
- Cash / Buying Power更新
- OrderList + Position + Cash evidence policy
- BrokerOrder単体からAssetを作らない原則
- Reconcile PASS
- Report生成
- Notification Payload生成のみ
- Audit PASS
- Production注文なし
- 本番Broker API Writeなし
- launchd/plist変更なし

### Current SoT永続化E2Eへの影響

D15は、以下の範囲では未達である。

- `.runtime/demo/persistent_ledger/state.json` へのCurrent write
- `.runtime/demo/persistent_ledger/*.jsonl` へのLedger History write
- Current state readerによる永続Currentの再読込
- Report source refsと実ファイルの一致
- multi-day operationで前回Currentを引き継ぐこと
- launchd / 日次運用前提のCurrent SoT運用

## launchd / 日次運用前の必須性

Current SoT未接続は、launchd / 日次自動運用 / multi-day operation rehearsal の前に必須修正である。

理由は以下である。

- Runtime v2 orchestratorは `persistent_ledger_state` をCurrentとして読む前提である
- persistent Currentが無いと、次営業日のCurrent State ReadがREVIEW_REQUIREDへ止まる
- per-run artifactはphase名に依存しており、日次運用のCurrent固定Pathではない
- Report / AuditはDerivedであり、次回Planning / Submit / ReconcileのSoTにしてはいけない
- BrokerOrder単体またはReport artifactからAssetを復元すると、Phase13のSoT原則に反する

## 次に必要な修正案

Phase14-D20以降で、以下を実装・検証することを推奨する。

1. Runtime v2 persistent ledger writerを正規経路へ接続する
   - `write_current_asset_state(resolve_current_path("demo", "demo", "persistent_ledger_state"), asset_state)`
   - orders / positions / cash / events のappend-only writerを定義する

2. Single Writer Ruleを明確化する
   - Asset Current writerは1つに限定する
   - Report / Audit / NotificationはCurrentを書かない
   - BrokerOrderのみからAssetを書かない

3. D15相当のreflection後にcanonical Currentをwriteする
   - `.runtime/demo/persistent_ledger/state.json`
   - `.runtime/demo/persistent_ledger/orders.jsonl`
   - `.runtime/demo/persistent_ledger/positions.jsonl`
   - `.runtime/demo/persistent_ledger/cash_history.jsonl`
   - `.runtime/demo/persistent_ledger/events.jsonl`

4. Current state readerでread-back検証する
   - `persistent_ledger_state` が `CURRENT` または `CONFIRMED_EMPTY` として分類されること
   - environment mismatchが無いこと
   - `review_required=false` の場合のみPlanningへ進めること

5. Report source refsと実ファイルを一致させる
   - ReportはDerivedのまま
   - `source_current_paths` に列挙されたpathが存在することをAuditで検証する

6. D15 per-run artifactからのbackfillを行う場合は明示migrationにする
   - ReportやAuditをCurrent SoTとして扱わない
   - Broker ReadOnly after snapshot + ledger projection + asset builderから再生成する
   - migration audit artifactを残す

7. launchd / 日次運用のgateを追加する
   - `.runtime/demo/persistent_ledger/state.json` が存在しない場合はBLOCKEDまたはREVIEW_REQUIRED
   - Current SoTのvalidationが失敗した場合はSubmit禁止

## Acceptance Criteria 判定

| Criteria | 判定 |
| --- | --- |
| `persistent_ledger/state.json` の有無を確認している | PASS |
| D15 BUY/SELL結果の保存場所を特定している | PASS |
| cash / buying_power / positions の保存場所を特定している | PASS |
| Ledger / Assetが永続Currentを書いているか判定している | PASS |
| D15のE2E有効範囲を分類している | PASS |
| Current SoT未接続なら、次フェーズ修正案を明記している | PASS |
| コード変更していない | PASS |
| Broker API呼び出ししていない | PASS |
| Submitしていない | PASS |
| launchd/plist変更していない | PASS |

## 結論

Phase14-D15は、Runtime v2 pure submit pathによるDemo BUY/SELL手動E2Eとして受け入れ可能である。

しかし、Phase13で定義されたAsset Current SoTである `persistent_ledger/state.json` への永続化は現実には接続されていない。D15成果物は `.runtime/phase14d15/` 配下のper-run artifactに閉じており、Current SoT永続化まで含むFull E2Eではない。

したがって、D15分類は **MANUAL_E2E_WITH_PER_RUN_ARTIFACT_ONLY**、D19最終判定は **PHASE14D19_CURRENT_SOT_GAP_FOUND** とする。
