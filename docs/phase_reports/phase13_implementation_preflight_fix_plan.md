# Phase13-K Implementation Preflight Fix Plan

作成日: 2026-07-07

判定: DESIGN_ONLY

## 1. 目的

Phase13-J で残った軽微課題を、実装前に整理する。

対象:

- schema validator 配置
- mode / environment 必須の path resolver 方針
- legacy runtime entrypoint isolation list
- Ledger Runtime / Asset Runtime interface 整理

Phase13-K では実装しない。どこに置くか、どう実装するか、何を禁止するか、何をテストするかを整理する。

## 2. 前提

Phase13-K は実装前整理である。

守ること:

- 実装変更しない。
- 既存 Runtime を v2 正規フローとして継承しない。
- 既存 entrypoint を v2 から直接呼ばない。
- Current は固定 Path から読む。
- mode / environment を明示しない path 解決を禁止する。
- History / Derived から Current を推測しない。
- Submit は禁止。
- Broker 注文は禁止。
- `launchd` 再開は禁止。

## 3. Schema Validator 配置方針

### 推奨配置

```text
src/ai_fund_lab_v2/runtime_v2/contracts/
```

推奨理由:

- Current State Contract の実装場所として意味が明確。
- schema validation だけでなく read / write contract、result type、error classification を同居できる。
- 既存 runtime module と分離でき、legacy flow の継承を避けやすい。

### 予定 module 構成

```text
src/ai_fund_lab_v2/runtime_v2/contracts/
  __init__.py
  validation_result.py
  base_validator.py
  current_state_validator.py
  pending_order_plan_validator.py
  persistent_ledger_state_validator.py
  ledger_jsonl_validators.py
  notification_delivery_validator.py
```

### Validator 対象

- `runtime_state/current_state.json`
- `pending_order_plan/pending_order_plan.json`
- `persistent_ledger/state.json`
- `persistent_ledger/orders.jsonl`
- `persistent_ledger/executions.jsonl`
- `persistent_ledger/positions.jsonl`
- `persistent_ledger/cash_history.jsonl`
- `persistent_ledger/events.jsonl`
- `notification_delivery/delivery_ledger.jsonl`

### Validation result 形式

予定する結果 object:

```text
ValidationResult
  object_type
  path
  valid
  severity
  failure_code
  runtime_action
  review_required
  blocked
  halt
  messages
```

`runtime_action` 候補:

```text
PASS
BLOCKED
REVIEW_REQUIRED
HALT
```

### Validation 失敗分類

| Failure | Runtime action |
| --- | --- |
| schema_version missing / mismatch | BLOCKED |
| required field missing | BLOCKED |
| hash mismatch | REVIEW_REQUIRED |
| source unknown | REVIEW_REQUIRED |
| business_date mismatch | STALE -> REVIEW_REQUIRED or BLOCKED |
| raw request / raw response / secret detected | HALT |
| production_equivalent false in production current asset | REVIEW_REQUIRED |

### Architecture Test 対応

- Schema Validator Placement Test
- Schema Validation Test
- Required Field Test
- Raw Secret / Raw Response Prohibition Test
- Production Equivalent Validation Test

## 4. mode / environment 必須 Path Resolver 方針

### 推奨配置

```text
src/ai_fund_lab_v2/runtime_v2/storage/path_resolver.py
```

推奨理由:

- storage concern として contracts から分離できる。
- mode root 分離方針を集中管理できる。
- Current / History / Derived の path 解決を同一 policy で扱える。

### 必須方針

- `mode` は必須。
- `environment` は必須。
- 未指定時は例外。
- `default_mode=production` は禁止。
- environment 省略は禁止。
- Phase 番号による Current 解決は禁止。
- 日付別 directory による Current 解決は禁止。

### Runtime mode root

```text
.runtime/production/
.runtime/demo/
.runtime/simulation/
.runtime/backtest/
```

### 予定 API

```text
resolve_current_path(mode, environment, object_type)
resolve_history_path(mode, environment, object_type, business_date)
resolve_derived_path(mode, environment, object_type, business_date)
```

### 禁止 API / pattern

```text
resolve_latest_order_plan()
resolve_current_from_date_dir()
resolve_current_from_phase_dir()
default_mode=production
environment省略
```

### Current path 解決例

```text
resolve_current_path("demo", "demo", "pending_order_plan")
-> .runtime/demo/pending_order_plan/pending_order_plan.json

resolve_current_path("production", "production", "persistent_ledger_state")
-> .runtime/production/persistent_ledger/state.json
```

### Architecture Test 対応

- Mode Required Path Resolver Test
- Environment Required Path Resolver Test
- No Default Production Mode Test
- No Date Current Resolver Test
- No Phase Current Resolver Test
- Backtest Current Not Production Current Test

## 5. Legacy Runtime Entrypoint Isolation Plan

Phase13-K では削除しない。実装変更しない。entrypoint を無効化しない。調査・分類のみを行う。

### 分類カテゴリ

| Category | Meaning | v2 policy |
| --- | --- | --- |
| Legacy workflow entrypoint | 既存 runtime flow を一括実行する入口 | v2 から直接 import / call 禁止 |
| Legacy current resolver | 日付別 / latest から Current を推測する処理 | v2 では使用禁止 |
| Legacy submit path | 既存 Submit 実行経路 | v2 では使用禁止。Submit Runtime で再設計 |
| Legacy report path | 既存 Report current inference を含む処理 | v2 では直接使用禁止 |
| Reusable pure utility | 副作用なし、Current 推測なしの純粋関数 | wrapper 経由で再利用可 |
| Reusable broker readonly utility | Broker ReadOnly の低レベル client | Broker Runtime adapter 経由で再利用検討 |
| Reusable schema/data class candidate | data class / parser など | contract validation 後に再利用可 |
| Unknown / review required | 分類未確定 | v2 から使用禁止。調査後判断 |

### 調査対象候補

実装時に調査する候補:

- daily runtime runner
- submit operation runner
- approval prepare runner
- report generation runner
- reconcile runner
- fill monitor runner
- broker snapshot / readonly runner
- launchd linked scripts
- legacy path resolver / latest artifact resolver
- `demo_ledger` writer / reader paths

### Isolation 方針

- v2 implementation は legacy workflow entrypoint を直接呼ばない。
- 必要な既存処理は pure utility と workflow を分離してから wrapper 経由で使う。
- import 禁止リストまたは lint / architecture test で検知する。
- Unknown は使用禁止を default にする。

### Architecture Test 対応

- Legacy Entrypoint Isolation Test
- Legacy Current Resolver Prohibition Test
- Legacy Submit Path Prohibition Test
- Reusable Utility Wrapper Test

## 6. Ledger Runtime / Asset Runtime Interface 方針

### 整理する責務

Ledger Runtime:

- `persistent_ledger/orders.jsonl`
- `persistent_ledger/executions.jsonl`
- `persistent_ledger/positions.jsonl`
- `persistent_ledger/cash_history.jsonl`
- `persistent_ledger/events.jsonl`
- dedup
- append-only policy
- source / environment / review flags enforcement

Asset Runtime:

- ledger records から CurrentAssetState を再構築する。
- positions / cash / buying_power / market_value / total_equity を projection する。
- `persistent_ledger/state.json` snapshot を生成する。
- state_unknown / confirmed_empty / stale / review_required を判定する。

### 選択肢

| Option | Description | Pros | Cons |
| --- | --- | --- | --- |
| A | Ledger Runtime が `state.json` まで書く。Asset Runtime は計算補助のみ | writer が一箇所に集まる | Asset Runtime の責務が曖昧 |
| B | Ledger Runtime は append-only records まで。Asset Runtime が `state.json` snapshot を書く | record と snapshot の責務が明確 | transaction coordination が必要 |
| C | Ledger Runtime が Asset Runtime を呼び、`state.json` 更新は transaction 内で一体管理する | transaction boundary と責務分離を両立 | interface 設計が必要 |

### 推奨案

推奨: Option C

理由:

- append-only records は Ledger Runtime の責務として明確に保てる。
- CurrentAssetState の計算は Asset Runtime に閉じ込められる。
- Transaction E の atomic sequence の中で `LedgerExecution -> LedgerPosition -> LedgerCash -> CurrentAsset` を一体管理できる。
- `state.json` の実ファイル書き込みは Asset Runtime の single writer とし、Ledger Runtime は transaction coordinator として Asset Runtime を呼ぶ構成にできる。

### Single writer 方針

```text
persistent_ledger/state.json
  single writer: Asset Runtime
  transaction coordinator: Ledger Runtime
```

Planning / Approval / Submit / Report / Notification は `state.json` を書かない。

### Interface 案

```text
LedgerRuntime.append_order(record) -> AppendResult
LedgerRuntime.append_execution(record) -> AppendResult
LedgerRuntime.append_position(record) -> AppendResult
LedgerRuntime.append_cash(record) -> AppendResult
LedgerRuntime.append_event(record) -> AppendResult

AssetRuntime.rebuild_current_asset_state(ledger_root, mode, environment) -> CurrentAssetStateBuildResult
AssetRuntime.write_state_snapshot(state, mode, environment) -> WriteResult
```

### Review Required 条件

- execution / position / cash の dependency 不足
- source unknown
- production_equivalent false in production
- negative unexpected quantity
- cash / buying_power unknown
- broker divergence
- ledger divergence

### Architecture Test 対応

- Ledger Asset Interface Boundary Test
- State Json Single Writer Test
- Ledger Append Dedup Test
- CurrentAsset Rebuild Test
- No Planning State Write Test
- No Report State Write Test

## 7. Architecture Test 計画

Phase13-K ではテスト実装はしない。次フェーズで必要な Architecture Test を整理する。

| Test | Purpose |
| --- | --- |
| Schema Validator Placement Test | validator が runtime_v2 contracts 配下に配置される |
| Mode Required Path Resolver Test | mode 未指定で path resolve できない |
| Environment Required Path Resolver Test | environment 未指定で path resolve できない |
| No Default Production Mode Test | default production fallback が存在しない |
| No Date Current Resolver Test | 日付別 directory から Current を解決しない |
| No Phase Current Resolver Test | Phase 番号から Current を解決しない |
| Legacy Entrypoint Isolation Test | v2 が legacy workflow entrypoint を直接呼ばない |
| Ledger Asset Interface Boundary Test | Ledger append と Asset snapshot の責務境界が守られる |
| State Json Single Writer Test | `persistent_ledger/state.json` writer が Asset Runtime に限定される |
| Legacy Submit Path Prohibition Test | v2 Submit が legacy submit path を使わない |
| Backtest Current Not Production Current Test | mode root が混線しない |

## 8. Phase13-L 以降への引き継ぎ

推奨する次フェーズ:

```text
Phase13-L: Runtime v2 Skeleton / Path Resolver / Schema Validator implementation
Phase13-M: Current State Contract architecture tests
Phase13-N: Runtime State Machine skeleton
Phase13-O: Persistent Ledger / Asset Runtime implementation
```

Phase13-L で実装する候補:

- `runtime_v2` package skeleton
- mode / environment required path resolver
- schema validator placement
- validation result type
- legacy entrypoint isolation guard の最小設計反映

Phase13-K では実装しない。

## 9. 禁止事項

Phase13-K では以下を禁止する。

- 実装変更
- Submit
- Broker 注文
- Demo 注文
- Production 注文
- 通知送信
- `launchd` 再開
- 既存 plist 削除
- 新規 plist 作成
- artifact 削除
- AI 再学習
- フルバックテスト
- Backtest 実行
- Simulation 実行
- legacy entrypoint 削除
- 既存 Runtime 無効化

## 10. 完了条件

- schema validator 配置方針が整理されている。
- mode / environment 必須 path resolver 方針が整理されている。
- legacy runtime entrypoint isolation list が整理されている。
- Ledger Runtime / Asset Runtime interface 方針が整理されている。
- Architecture Test 計画が整理されている。
- Phase13-L 以降への引き継ぎが整理されている。
- JSON レポートが作成され、妥当性確認されている。
- 実装変更は一切行われていない。

