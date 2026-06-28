# Phase11-B Safety Runtime Foundation

- status: IMPLEMENTED
- created_at: 2026-06-28
- scope: independent Safety Layer runtime foundation
- broker_api_connected: false
- login_logout_executed: false
- websocket_connected: false
- demo_order_submitted: false
- production_order_submitted: false
- clm_kabu_new_order_executed: false
- runtime_behavior_changed: false
- broker_snapshot_updated: false
- paper_ledger_updated: false
- ai_learning_updated: false

## 1. Summary

Phase11-B では、Phase11-A の設計に基づき、Runtime / Broker Runtime から分離した独立 subsystem として `safety_phase11` を追加した。

今回の実装は pure function / mock input ベースであり、外部 API、Broker session、Demo / Production 発注、Runtime 本体の大きな変更は行っていない。

Safety Layer は AI 学習データを作るものではない。Runtime の安全判定だけを行う。

AI学習に使わないもの:

```text
Backtest outcome
Paper Ledger
Broker Snapshot
PnL
Portfolio state
Cash
selected / bought / affordable data
Order result
Execution result
Safety result
Audit result
PM multiplier imitation
```

## 2. Implemented Files

追加:

```text
src/ai_fund_lab_v2/safety_phase11/__init__.py
src/ai_fund_lab_v2/safety_phase11/models.py
src/ai_fund_lab_v2/safety_phase11/state_machine.py
src/ai_fund_lab_v2/safety_phase11/guards.py
src/ai_fund_lab_v2/safety_phase11/safety_manager.py
src/ai_fund_lab_v2/safety_phase11/event_writer.py
src/ai_fund_lab_v2/safety_phase11/report_writer.py
tests/safety_phase11/test_state_machine.py
tests/safety_phase11/test_guards_and_manager.py
tests/safety_phase11/test_writers.py
reports/phase_reports/phase11b_safety_runtime_foundation.json
```

## 3. Safety Models

`models.py` で定義した主要 model:

- `SafetyState`
- `SafetyDecision`
- `SafetySeverity`
- `SafetyGuardName`
- `SafetyEvent`
- `SafetyCheckInput`
- `SafetyCheckResult`
- `HumanReviewItem`

Safety states:

```text
NORMAL
WARNING
BUY_STOP
EMERGENCY_STOP
RECOVERY_CANDIDATE
MANUAL_APPROVED
```

Safety decisions:

```text
ALLOW
BLOCK
REVIEW_REQUIRED
EMERGENCY_STOP
```

## 4. Safety State Machine

実装した方針:

- valid transition のみ許可。
- unknown state は `EMERGENCY_STOP`。
- invalid transition は `REVIEW_REQUIRED`。
- any state -> `EMERGENCY_STOP` は許可。
- `RECOVERY_CANDIDATE -> MANUAL_APPROVED -> NORMAL` のみ復帰可。
- `BUY_STOP -> NORMAL` は禁止。
- `EMERGENCY_STOP -> NORMAL` は禁止。

## 5. Implemented Guards

`guards.py` は外部 API を呼ばず、`SafetyCheckInput` のデータだけで判定する。

実装した guard:

- `DuplicateOrderGuard`
- `CashBufferGuard`
- `MaxExposureGuard`
- `QuoteStaleGuard`
- `MarketCrashGuard`
- `BrokerDivergenceGuard`
- `DailyLossGuard`
- `EmergencyStopGuard`
- `IndividualCrashGuard`
- `MarketRecoveryGuard`

主な挙動:

- Market crash は `BUY_STOP` / `BLOCK`。
- Severe market crash は `EMERGENCY_STOP`。
- Individual crash は -7% / -10% / -15% を分類。
- Recovery は `RECOVERY_CANDIDATE` までで、自動 `NORMAL` 復帰はしない。
- Duplicate active order は `BLOCK`。
- Broker duplicate order risk は `EMERGENCY_STOP`。
- Stale quote / missing quote は `BLOCK`。

## 6. Safety Manager

`SafetyManager` は複数 guard をまとめて評価する。

集約ルール:

```text
1つでも EMERGENCY_STOP -> 全体 EMERGENCY_STOP
BLOCK があれば BLOCK
REVIEW_REQUIRED があれば REVIEW_REQUIRED
すべて ALLOW なら ALLOW
```

出力:

- current safety state
- overall decision
- state candidate
- transition allowed / reason
- guard results
- SafetyEvent
- HumanReviewItem

## 7. Event / Report Writers

Safety Event 保存先:

```text
.runtime/safety/phase11/events/
```

Safety Report 保存先:

```text
reports/safety/phase11/
```

保存前に Phase11 用 sanitizer を通す。

保存禁止:

```text
raw response
raw request
plaintext account id
plaintext order id
plaintext execution id
auth id
private key
virtual URL
second password
```

Safety Report には no-live-order confirmation を含める。

## 8. Test Coverage

実行した軽量テスト:

```text
PYTHONPATH=src python3 -m pytest tests/safety_phase11 -q
```

結果:

```text
14 passed
```

確認したこと:

- state machine 正常遷移。
- `BUY_STOP -> NORMAL` 禁止。
- `EMERGENCY_STOP -> NORMAL` 禁止。
- any state -> `EMERGENCY_STOP` 許可。
- unknown state は `EMERGENCY_STOP`。
- MarketCrashGuard は buy stop / block を返す。
- RecoveryGuard は自動 NORMAL 復帰しない。
- IndividualCrashGuard は -7 / -10 / -15 を分類する。
- DuplicateOrderGuard は重複注文を block する。
- QuoteStaleGuard は stale quote を block する。
- event / report に forbidden secret/raw values が保存されない。

## 9. Safety Confirmation

今回行っていないこと:

- Broker API接続
- Login / Logout
- WebSocket接続
- `CLMKabuNewOrder`
- Demo発注
- Production発注
- Runtime本体への大規模変更
- Broker Snapshot更新
- Paper Ledger更新
- 長時間バックテスト
- フルテスト
- AI学習処理変更

## 10. Result

判定:

```text
PHASE11B_SAFETY_RUNTIME_FOUNDATION_COMPLETE
PHASE11C_READY_FOR_HOURLY_POSITION_MONITOR
LIVE_ORDER_EXECUTION_REMAINS_BLOCKED
```
