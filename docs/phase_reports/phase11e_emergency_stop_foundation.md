# Phase11-E Emergency Stop Foundation

- status: IMPLEMENTED
- created_at: 2026-06-28
- scope: Emergency Stop decision foundation and manual emergency flag for Phase11
- broker_api_connected: false
- login_logout_executed: false
- websocket_connected: false
- demo_order_submitted: false
- production_order_submitted: false
- clm_kabu_new_order_executed: false
- auto_sell_executed: false
- auto_recovery_executed: false
- runtime_behavior_changed: false
- broker_snapshot_updated: false
- paper_ledger_updated: false
- cron_or_launchagent_registered: false
- ai_learning_updated: false

## 1. Summary

Phase11-E では、重大異常を検知したときに Safety State を `EMERGENCY_STOP` に倒し、発注系 action を fail closed にする Emergency Stop Foundation を追加した。

Emergency Stop は損失を必ず限定する仕組みではない。ギャップダウン、ストップ安、約定不能では閾値を超える損失が起き得る。

Phase11-E の目的は、自動進行、新規買い、自動売却、自動復帰を止め、人間確認へ回すことである。

## 2. Implemented Files

追加:

```text
src/ai_fund_lab_v2/safety_phase11/emergency_stop.py
src/ai_fund_lab_v2/safety_phase11/emergency_flag.py
tests/safety_phase11/test_emergency_stop.py
tests/safety_phase11/test_emergency_flag.py
reports/phase_reports/phase11e_emergency_stop_foundation.json
```

最小更新:

```text
src/ai_fund_lab_v2/safety_phase11/event_writer.py
src/ai_fund_lab_v2/safety_phase11/report_schema.py
src/ai_fund_lab_v2/safety_phase11/__init__.py
```

## 3. Emergency Stop Conditions

扱う発動条件:

- manual emergency stop flag
- IndividualCrashGuard の -15% Emergency Candidate
- MarketCrashGuard の重大クラッシュ
- Broker Snapshot missing / stale が重大
- Runtime State unknown / invalid
- Duplicate active order risk
- Position quantity mismatch
- Unknown broker position
- Cash / Exposure 重大逸脱
- Order / Execution 重大乖離
- secret / raw response persistence violation 疑い
- unknown severe error

Emergency Stop 判定出力:

```text
emergency_required
reason_codes
triggered_guards
affected_issue_codes
recommended_human_actions
blocked_actions
allowed_actions
next_state
```

## 4. Manual Emergency Flag

保存先:

```text
.runtime/safety/phase11/state/manual_emergency_stop.json
```

機能:

- create manual emergency flag
- read manual emergency flag
- clear manual emergency flag candidate

flag項目:

- created_at
- created_by
- reason
- active
- raw_response_saved=false
- auto_trade_executed=false

clear は自動復旧ではない。clear 後も Recovery Guard / Human Review / `MANUAL_APPROVED` が必要である。

## 5. Emergency State

Emergency発動時:

```text
any state -> EMERGENCY_STOP
```

復帰は直接 `NORMAL` へ戻さない。

```text
EMERGENCY_STOP
↓
RECOVERY_CANDIDATE
↓
MANUAL_APPROVED
↓
NORMAL
```

## 6. Actions During Emergency

Blocked actions:

- new buy
- new sell auto execution
- correction
- cancel
- retry
- automatic recovery
- normal runtime progression
- broker order API
- demo order submit
- production order submit

Allowed actions:

- read-only broker sync
- quote polling
- report generation
- audit
- human review

## 7. Report / Review Queue Integration

Emergency Stop 発動時は既存の Safety Report / Human Review Queue に以下として反映される。

- emergency candidates
- blocked actions
- recommended human actions
- no-live-order confirmation
- auto_sell_executed=false
- auto_recovery_executed=false

Phase11-E では実Brokerや実Runtimeには接続していない。

## 8. Test Coverage

実行した軽量テスト:

```text
PYTHONPATH=src python3 -m pytest tests/safety_phase11 -q
```

結果:

```text
41 passed
```

確認したこと:

- manual emergency flag で `EMERGENCY_STOP` になる。
- -15% individual crash で emergency candidate になる。
- duplicate active buy order risk で emergency candidate になる。
- missing / stale critical broker snapshot で emergency candidate になる。
- any state から `EMERGENCY_STOP` へ遷移できる。
- `EMERGENCY_STOP` から直接 `NORMAL` へ戻れない。
- manual flag clear だけでは `NORMAL` へ戻れない。
- Emergency時に new buy / auto sell / retry / auto recovery が blocked actions に含まれる。
- allowed actions は read-only / report / audit / human review に限定される。
- flag / event / report に forbidden secret / raw values が保存されない。

## 9. Safety Confirmation

今回行っていないこと:

- Broker API接続
- Login / Logout
- WebSocket接続
- `CLMKabuNewOrder`
- Demo発注
- Production発注
- 自動売却
- 自動復帰
- Runtime本体への大規模変更
- Broker Snapshot更新
- Paper Ledger更新
- 長時間バックテスト
- フルテスト
- AI学習処理変更
- cron / LaunchAgent 登録

## 10. Result

判定:

```text
PHASE11E_EMERGENCY_STOP_FOUNDATION_COMPLETE
PHASE11F_READY_FOR_RECOVERY
LIVE_ORDER_EXECUTION_REMAINS_BLOCKED
```
