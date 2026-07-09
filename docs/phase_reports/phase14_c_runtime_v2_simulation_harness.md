# Phase14-C Runtime v2 Simulation Harness

作成日: 2026-07-07

## Status

```text
PHASE14C_SIMULATION_HARNESS_COMPLETE
```

Phase14-C では、立花証券 API に依存せず Runtime v2 を複数営業日にわたり検証するため、Simulation Broker Adapter と軽量 Simulation Harness を追加した。

本フェーズでは Production 注文、本番 Broker API Write、実資金運用、実 Broker Submit、Demo Submit、Broker API 呼び出し、Notification 実送信、launchd / plist 変更、AI 再学習、最適化目的の Full Backtest、Simulation 結果の AI 学習利用、Legacy Runtime の正規フロー復活は行っていない。

## 1. Phase14-C の目的

Phase14-C の目的は、Broker 部分だけを Simulation Broker へ差し替え、Runtime v2 の既存 component が BUY / SELL / BUY-SELL mixed / multi-business-day replay を破綻なく処理できることを確認することである。

対象 flow:

```text
Market data replay
Feature replay
Current State Read
Planning
Approval
Pending
Simulated Submit
Simulated Fill
Execution Reflection
Ledger Update
Asset Update
Reconcile
Report
Notification Payload
Audit
```

Phase14-C は実 Broker 接続の代替ではない。Demo Broker へ進む前に、Runtime v2 本体の状態遷移、Ledger / Asset / Reconcile 境界、SELL 安全性を軽量に確認するための harness である。

## 2. Phase14-A/B との関係

Phase14-A では Integrated Operation Acceptance Test 全体を定義した。

Phase14-B では Demo Broker 接続前提、BUY / SELL シナリオ、Demo Submit 前 guard を整理した。

Phase14-C では、そのうち実 Broker に依存しない Runtime v2 の検証を進める。

```text
Phase14-A:
  Integrated Operation Acceptance Test design

Phase14-B:
  Demo Broker / BUY / SELL preflight

Phase14-C:
  Runtime v2 Simulation Harness
```

## 3. Demo Broker と Simulation Broker の差し替え境界

差し替え境界は Broker Adapter である。

```text
Runtime v2
  ↓
Broker Adapter Boundary
  ├─ Demo Broker
  └─ Simulation Broker
```

Runtime v2 本体は Demo / Simulation を極力意識しない。Simulation Broker は Runtime v2 の `BrokerReadOnlyBundle` と同じ境界に合わせて、orders / executions / positions / cash を返す。

## 4. Simulation Broker の責務

Simulation Broker の責務:

- 外部 Broker API を呼ばない。
- In-memory の cash / buying_power / positions を管理する。
- Approved Pending item に対して simulated submit を受け付ける。
- BUY fill により cash / buying_power を減らし、position を増やす。
- SELL fill により position を減らし、cash / buying_power を増やす。
- 全数量 SELL では position を消滅させる。
- SELL realized PnL を算出可能な場合に返す。
- 保有数量超過 SELL を `BLOCKED` にする。
- duplicate pending item submit を `BLOCKED` にする。
- POST_SEND_UNKNOWN の自動再送を `REVIEW_REQUIRED` にする。
- Runtime v2 用の Broker ReadOnly snapshot を返す。

Simulation Broker がやらないこと:

- AI 判断を行わない。
- Runtime v2 の Planning / Approval / Pending / Ledger / Asset / Reconcile を再実装しない。
- Production / Demo Broker API を呼ばない。
- Notification を送信しない。
- Backtest optimizer として結果を評価しない。

## 5. Simulation Broker が返す model

Simulation Broker は既存 Runtime v2 の `BrokerReadOnlyBundle` を返す。

構成:

- `BrokerOrderSnapshot`
- `BrokerExecutionSnapshot`
- `BrokerPositionSnapshot`
- `BrokerCashSnapshot`

これにより、下流は既存の Runtime v2 component をそのまま使う。

使用する既存 component:

- `classify_fill`
- `project_order_to_ledger_record`
- `project_execution_to_ledger_record`
- `project_position_to_ledger_record`
- `project_cash_to_ledger_record`
- `build_current_asset_state`
- `run_reconciliation`
- `build_runtime_report`
- `build_notification_payload`
- `run_audit`

## 6. Runtime v2 本体を二重実装しない方針

Phase14-C では Simulation 専用 Runtime を新規作成していない。

追加したのは以下である。

- Simulation Broker Adapter
- Simulation Harness
- Simulation 用 dataclass
- Phase14-C tests

Runtime v2 の Planning / Approval / Pending / Execution Reflection / Ledger / Asset / Reconcile / Report / Notification Payload / Audit は既存 component を呼び出している。

## 7. BUY シナリオ

BUY シナリオ:

```text
1. Simulation Broker snapshot
2. Current Asset State build
3. Planning
4. Pending promotion
5. Approval
6. Pending approval linkage
7. Simulated Submit
8. Simulated Fill
9. Broker ReadOnly snapshot
10. Fill Classification
11. Ledger projection
12. Asset build
13. Reconcile
14. Report
15. Notification Payload
16. Audit
```

確認:

- Approval 必須
- Pending-only Submit 相当
- buying_power 減少
- position 増加
- order / execution / position / cash evidence 生成
- BrokerOrder のみから Asset を作らない

## 8. SELL シナリオ

SELL シナリオは Phase14 の必須対象である。

確認:

- Broker Position を正とする。
- 保有数量超過 SELL は `BLOCKED`。
- SELL 約定後に position quantity が減少する。
- 全数量 SELL では position が消滅する。
- SELL 約定後に cash が更新される。
- realized PnL を算出できる場合は harness result に含める。
- SELL でも二重 Submit 禁止。
- SELL でも POST_SEND_UNKNOWN は自動再送禁止。
- Execution / Position / Cash evidence から Asset を作る。

## 9. BUY / SELL 混在シナリオ

BUY / SELL mixed path では、同一 business date に BUY と SELL を含められる。

確認:

- item ごとに Approval が必要。
- BUY と SELL の ledger record は分離される。
- BUY position increase と SELL position reduction が同じ asset state に反映される。
- Report は BUY / SELL を orders / executions / positions / asset として分離表示できる。

同一銘柄の同時 opposite side については Phase14-D 以降の Demo rehearsal 前に REVIEW_REQUIRED policy をさらに強化する。

## 10. 複数営業日 Replay 方針

multi-business-day replay では、Day N の fill 結果を Day N+1 の broker state として引き継ぐ。

最小確認:

- Day1 BUY
- Day2 partial SELL
- Day3 full SELL

確認:

- cash carry-over
- position carry-over
- consumed pending no-resubmit
- ledger order / execution dedup
- full SELL 後 position 消滅

## 11. Current SoT 検証

Simulation Harness は Asset Current を `build_current_asset_state` で構築する。

Current SoT 原則:

- BrokerOrder は Asset SoT ではない。
- Execution / Position / Cash evidence を経由して Asset を作る。
- `persistent_ledger/state.json` 相当の Asset Current は Asset Runtime の責務である。
- Report / Audit は Current ではない。

## 12. Ledger 整合性検証

Ledger projection では以下を分離する。

- Order record
- Execution record
- Position record
- Cash record

`append_record` により dedup key ベースの重複 append を防ぐ。

## 13. Asset 整合性検証

Asset は latest Broker Position / Cash evidence から作る。

SELL 後の期待:

- partial SELL: position quantity が減る。
- full SELL: position が消える。
- cash / buying_power が増える。
- market_value / total_equity が再計算される。

## 14. Reconcile / Report / Audit 検証

Reconcile:

- Pending / Ledger Order / Broker Order
- Broker Execution / Ledger Execution
- Broker Position / Asset Position
- Broker Cash / Asset Cash

Report:

- Derived artifact
- Current と Evidence を分離
- orders / executions / positions / asset / reconciliation sections を生成

Audit:

- Report / Notification Payload が Current ではないことを確認
- Reconciliation review を evidence として扱う
- Submit source ではない

## 15. 禁止事項

Phase14-C では以下を禁止し、実行していない。

- Production 注文
- 本番 Broker API Write
- 実資金運用
- 実 Broker Submit
- Demo Submit
- Broker API 呼び出し
- Notification 実送信
- launchd / plist 変更
- AI 再学習
- 最適化目的の Full Backtest
- 未来情報利用
- Backtest / Simulation 結果を AI 学習へ利用
- Legacy Runtime を正規フローとして復活させること

## 16. 実装内容

追加:

- `src/ai_fund_lab_v2/runtime_v2/simulation/__init__.py`
- `src/ai_fund_lab_v2/runtime_v2/simulation/models.py`
- `src/ai_fund_lab_v2/runtime_v2/simulation/broker.py`
- `src/ai_fund_lab_v2/runtime_v2/simulation/harness.py`
- `tests/runtime_v2/test_phase14c_simulation_harness.py`
- `reports/phase_reports/phase14_c_runtime_v2_simulation_harness.json`

Simulation 専用 Runtime は作っていない。

## 17. Acceptance Criteria

| Criteria | Result |
| --- | --- |
| Simulation Broker は Broker Adapter 境界で差し替えられる | PASS |
| Runtime v2 本体を二重実装していない | PASS |
| BUY シナリオが PASS する | PASS |
| SELL シナリオが PASS する | PASS |
| BUY / SELL 混在シナリオが PASS する | PASS |
| 複数営業日 Replay の最小ケースが PASS する | PASS |
| 保有数量超過 SELL が BLOCKED になる | PASS |
| SELL 約定後に position / cash / ledger / asset が更新される | PASS |
| BrokerOrder のみから Asset を作らない | PASS |
| Execution / Position / Cash evidence から Asset を作る | PASS |
| Current / History / Derived 分離を維持する | PASS |
| Pending-only Submit 相当を維持する | PASS |
| Approval 必須を維持する | PASS |
| 二重 Submit 禁止を維持する | PASS |
| POST_SEND_UNKNOWN 自動再送禁止を維持する | PASS |
| Reconcile / Report / Audit が生成される | PASS |
| Production 注文、本番 Broker API Write、実 Broker API 呼び出しは行っていない | PASS |

## 18. Verification

Phase14-C targeted test:

```text
PYTHONPATH=src:. python3 -m pytest tests/runtime_v2/test_phase14c_simulation_harness.py -q
```

Result:

```text
4 passed
```

Runtime v2 full test:

```text
PYTHONPATH=src:. python3 -m pytest tests/runtime_v2 -q
```

Result:

```text
251 passed
```

## 19. Phase14-D への引き継ぎ条件

Phase14-D へ進む条件:

- Simulation Harness の BUY / SELL / mixed / multi-day replay が PASS している。
- 保有数量超過 SELL が BLOCKED になる。
- Runtime v2 の Pending-only Submit、Approval 必須、duplicate guard、POST_SEND_UNKNOWN 自動再送禁止が維持されている。
- BrokerOrder のみから Asset を作らないことが確認済み。
- Execution / Position / Cash evidence から Asset を作ることが確認済み。
- Demo Submit に進む前に、Phase14-B の Demo-only guard を再確認する。

Phase14-D では Demo Broker を使った guarded test へ進む。ただし Production 注文、本番 Broker API Write、実資金運用は引き続き禁止する。

## 20. Final Decision

```text
PHASE14C_SIMULATION_HARNESS_COMPLETE
```

理由:

- Broker Adapter 境界に Simulation Broker を追加した。
- Runtime v2 本体を二重実装せず、既存 component を使う harness を追加した。
- BUY / SELL / BUY-SELL mixed / multi-business-day replay の軽量テストが PASS した。
- SELL の保有数量超過 BLOCKED、position reduction、full exit、cash update、realized PnL を確認した。
- Reconcile / Report / Notification Payload / Audit が生成されることを確認した。
- Production 注文、本番 Broker API Write、実 Broker API 呼び出し、Demo Submit、通知送信、launchd / plist 変更は行っていない。
