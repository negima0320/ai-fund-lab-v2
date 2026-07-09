# Phase14-E8 Runtime v2 Demo Broker Capability / Evaluation Capital SoT Fix

作成日: 2026-07-07

## 最終判定

**PHASE14E8_DEMO_CAPABILITY_FIX_COMPLETE**

Phase14-E8では、立花証券Demo Brokerの制約をRuntime v2本線から切り離し、BrokerCapabilityで吸収する実装を追加した。あわせて、Demo Operation TestのRuntime評価資金を100万円に固定し、D15/D22由来のDemo Broker 2,000万円/保有銘柄Current汚染をbackup付きで除去した。

今回、Demo Submit、Broker API Write、Production注文、Notification実送信、launchd load/unload、Phase9 runtime / writer呼び出しは行っていない。

## 背景

立花証券デモ環境には以下の制約がある。

- 毎日、保有銘柄がリセットされる。
- 毎日、所持金額が約2,000万円へリセットされる。
- 9000番台銘柄は約定しない。

一方、Runtime v2 Demo Operation Testでは以下を守る必要がある。

- Runtime評価資金は100万円スタート。
- Runtime側では日々の保有銘柄・Cash・Ledgerを継続管理する。
- Broker Demoの2,000万円CashをAI / Planning / Capital Allocationの資金基準にしない。
- Broker Demoの日次リセットでRuntime Current SoTを勝手にリセットしない。
- 本番切替時にRuntimeロジックを入れ替えない。
- 環境差はBroker Adapter / BrokerCapabilityで吸収する。

## 実装内容

追加・更新:

- `src/ai_fund_lab_v2/runtime_v2/broker_adapter/capability.py`
- `src/ai_fund_lab_v2/runtime_v2/broker_adapter/__init__.py`
- `src/ai_fund_lab_v2/runtime_v2/asset/capability_policy.py`
- `src/ai_fund_lab_v2/runtime_v2/asset/initializer.py`
- `src/ai_fund_lab_v2/runtime_v2/asset/__init__.py`
- `src/ai_fund_lab_v2/runtime_v2/current_state/classifier.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/guards.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/order_plan_builder.py`
- `scripts/run_phase14e8_demo_operation_current_init.py`
- `tests/runtime_v2/test_phase14e8_demo_broker_capability_evaluation_capital_fix.py`
- `tests/runtime_v2/test_phase14d3_pure_submit_path.py`

## BrokerCapability

Capabilityはruntime modeから自動決定する。yaml/json/toml等の外部設定ファイルやユーザー定義ファイルは作成していない。

### mode=demo

```text
supports_daily_reset = true
cash_as_truth = false
buying_power_as_truth = false
positions_as_truth = false
executions_as_truth = true
order_status_as_truth = true
supports_9000_series_orders = false
default_evaluation_capital = 1000000
broker_cash_is_evidence_only = true
broker_positions_are_evidence_only_after_reset = true
```

### mode=production

```text
supports_daily_reset = false
cash_as_truth = true
buying_power_as_truth = true
positions_as_truth = true
executions_as_truth = true
order_status_as_truth = true
supports_9000_series_orders = true
default_evaluation_capital = null
broker_cash_is_evidence_only = false
broker_positions_are_evidence_only_after_reset = false
```

Unknown modeはfail closedで`ValueError`を返す。

## Demo Asset Reflection Policy

Demo capabilityではBroker cash / buying power / positionsはCurrent Asset TruthではなくEvidenceとして扱う。

実装:

- Broker cash 20,000,000が来てもRuntime Asset cashは1,000,000のまま。
- Broker buying power 20,000,000が来てもRuntime buying powerは1,000,000のまま。
- Broker daily resetでpositionsが空になってもRuntime Current positionsを自動消去しない。
- reset-like evidenceはReview Event / Reconcile finding相当として扱う。
- Production capabilityではcash / buying power / positionsをtruthとして扱える。

## 9000番台Guard

Demo capabilityでは9000番台銘柄をPlanning / Submit対象から除外する。

実装:

- `is_symbol_allowed_by_capability`
- Planning helperのCapability filter
- Submit preflight guard

既存D3 pure submit正常系fixtureは、約定不能な9432から7203へ更新した。9000番台BLOCKはE8専用テストで明示的に固定した。

## Current SoT初期化

実行:

```text
python3 scripts/run_phase14e8_demo_operation_current_init.py
```

初期化前backup:

```text
.runtime/backups/phase14e8/2026-07-07/
```

このbackupにはD15/D22由来の以下が保存されている。

- cash = 19,999,648
- buying_power = 19,999,648
- total_equity = 23,297,648
- positions = 6501 / 6502 / 9984 / 9001 等
- source = `phase14d15_orderlist_position_cash_reflection`

最終初期化manifest:

```text
.runtime/backups/phase14e8/2026-07-07_2/initialization_manifest.json
```

初期化後Current:

```text
.runtime/persistent_ledger/state.json
.runtime/persistent_ledger/orders.jsonl
.runtime/persistent_ledger/executions.jsonl
.runtime/persistent_ledger/positions.jsonl
.runtime/persistent_ledger/cash.jsonl
.runtime/persistent_ledger/events.jsonl
```

初期化後state:

| Field | Value |
| --- | --- |
| cash | 1,000,000 |
| buying_power | 1,000,000 |
| market_value | 0 |
| total_equity | 1,000,000 |
| positions | [] |
| environment | demo |
| source | `phase14e8_demo_operation_initial_state` |
| review_required | false |
| production_equivalent | false |
| current_state_confirmed_empty | true |

Read-back:

```text
classification = CONFIRMED_EMPTY
valid = true
review_required = false
```

## Public Report

Runtime v2 Public Reportを再生成した。

```text
reports/public/runtime_v2/latest.md
reports/public/runtime_v2/2026-07-07/public_report.md
```

表示内容:

- Cash: JPY 1,000,000
- Buying power: JPY 1,000,000
- Market value: JPY 0
- Total equity: JPY 1,000,000
- Holdings: No active positions
- BUY orders: 0
- SELL orders: 0
- Reconcile: PASS
- Audit: PASS

Public Reportには9000番台position、`phase14d15` source、secret、raw response、Broker internal idは出ていない。

## Verification

Commands:

```text
python3 -m pytest tests/runtime_v2/test_phase14e8_demo_broker_capability_evaluation_capital_fix.py
python3 scripts/run_phase14e8_demo_operation_current_init.py
python3 -m pytest tests/runtime_v2
```

Results:

- Phase14-E8 focused tests: 9 passed
- Runtime v2 tests: 306 passed
- Current read-back: `CONFIRMED_EMPTY`
- Public Report: 100万円・保有0

## 禁止事項確認

| Item | Result |
| --- | --- |
| capability外部定義ファイル作成 | Not created |
| user-config capability定義 | Not used |
| Demo Submit | Not executed |
| Broker API Write | Not executed |
| Production注文 | Not executed |
| Notification実送信 | Not executed |
| launchd load/unload | Not executed |
| Phase9 runtime | Not called |
| Phase9 writer | Not called |
| `.runtime/demo/...` Current復活 | Not used |
| phase artifact Current扱い | Not used |

## Acceptance Criteria

| Criteria | Result |
| --- | --- |
| Demo Broker制約をBrokerCapabilityで表現している | PASS |
| capabilityはmodeから自動決定される | PASS |
| capability外部定義ファイルを作っていない | PASS |
| Runtime本体にdemo専用の資産上書きロジックを散らしていない | PASS |
| Broker Demo cashをRuntime cash SoTにしていない | PASS |
| Broker Demo resetでRuntime positionsを自動消去しない | PASS |
| 9000番台がDemoでBLOCKされる | PASS |
| Runtime評価資金100万円で初期化済み | PASS |
| D15/D22由来Current汚染が除去済み | PASS |
| Public Reportが100万円・保有0を示す | PASS |
| Submitなし | PASS |
| Broker API Writeなし | PASS |
| Production注文なし | PASS |
| Notification実送信なし | PASS |
| launchd load/unloadなし | PASS |
| tests/runtime_v2 PASS | PASS |

## Final Decision

PHASE14E8_DEMO_CAPABILITY_FIX_COMPLETE
