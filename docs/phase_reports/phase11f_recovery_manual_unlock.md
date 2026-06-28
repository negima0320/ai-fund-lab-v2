# Phase11-F Recovery / Manual Unlock Foundation

- status: IMPLEMENTED
- created_at: 2026-06-28
- scope: Recovery candidate and manual unlock foundation for Phase11
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

Phase11-F では、`BUY_STOP` / `EMERGENCY_STOP` から通常運用へ戻すための Recovery / Manual Unlock 基盤を追加した。

Recovery Guard は底を当てるAIではない。解除候補を検出し、`RECOVERY_CANDIDATE` へ候補化し、Human Review と Manual Approval を経て `MANUAL_APPROVED` へ進めるための基盤である。

自動で `NORMAL` へ戻す処理は実装していない。`MANUAL_APPROVED -> NORMAL` は最新 Safety Check が `ALLOW` の時のみ許可する設計にした。

## 2. Implemented Files

追加:

```text
src/ai_fund_lab_v2/safety_phase11/recovery.py
src/ai_fund_lab_v2/safety_phase11/manual_unlock.py
tests/safety_phase11/test_recovery.py
tests/safety_phase11/test_manual_unlock.py
reports/phase_reports/phase11f_recovery_manual_unlock.json
```

最小更新:

```text
src/ai_fund_lab_v2/safety_phase11/report_schema.py
src/ai_fund_lab_v2/safety_phase11/__init__.py
```

## 3. Recovery Candidate Conditions

Recovery Candidate 判定条件:

- manual emergency flag が inactive
- severe market crash が解消候補
- index / market summary が数営業日安定
- candidate universe drawdown が改善
- 急落銘柄比率が低下
- stop-limit / extreme down candidate 比率が低下
- quote stale がない
- broker snapshot stale がない
- broker divergence がない
- duplicate active order risk がない
- daily loss / drawdown が許容範囲
- runtime state が valid
- no secret / raw persistence violation
- latest Safety Report が存在する

Recovery 出力:

```text
recovery_candidate
required_evidence
satisfied_evidence
missing_evidence
blocking_reasons
next_recommended_state
requires_human_review=true
auto_recovery_executed=false
```

条件が揃っても `NORMAL` へ自動復帰しない。

## 4. Manual Unlock

Manual Unlock approval 保存先:

```text
.runtime/safety/phase11/state/manual_unlock_approval.json
```

approval項目:

- approval_id
- approved_at
- approved_by
- reason
- target_state
- source_state
- safety_report_path
- recovery_evidence
- expires_at
- active
- auto_trade_executed=false
- auto_recovery_executed=false
- raw_response_saved=false

制約:

- stale approval は無効
- missing safety report path は無効
- missing recovery evidence は無効
- source_state が `BUY_STOP` または `EMERGENCY_STOP` 以外なら無効
- target_state は `MANUAL_APPROVED` のみ
- approval なしで `NORMAL` へ戻さない
- `MANUAL_APPROVED` 後も `NORMAL` へ進める前に最新 Safety Check `ALLOW` が必要

## 5. State Transition

厳守する復帰経路:

```text
BUY_STOP -> RECOVERY_CANDIDATE
EMERGENCY_STOP -> RECOVERY_CANDIDATE
RECOVERY_CANDIDATE -> MANUAL_APPROVED
MANUAL_APPROVED -> NORMAL
```

禁止:

```text
BUY_STOP -> NORMAL
EMERGENCY_STOP -> NORMAL
RECOVERY_CANDIDATE -> NORMAL
approvalなしのNORMAL復帰
expired approvalによる復帰
```

## 6. Report / Review Queue Integration

Safety Report schema に以下の欄を追加した。

- recovery_candidate_summary
- manual_unlock_summary

Recovery / Manual Unlock は運用監査・人間確認のための成果物であり、AI学習データではない。

## 7. Test Coverage

実行した軽量テスト:

```text
PYTHONPATH=src python3 -m pytest tests/safety_phase11 -q
```

結果:

```text
52 passed
```

確認したこと:

- `BUY_STOP` から Recovery Candidate になる。
- `EMERGENCY_STOP` から Recovery Candidate になる。
- 条件不足時は Recovery Candidate にならない。
- Recovery Candidate は自動 `NORMAL` 復帰しない。
- Manual Unlock 承認で `MANUAL_APPROVED` になる。
- approval なしで `NORMAL` にならない。
- expired approval は無効。
- missing safety report path は無効。
- missing recovery evidence は無効。
- `BUY_STOP -> NORMAL` は禁止。
- `EMERGENCY_STOP -> NORMAL` は禁止。
- `RECOVERY_CANDIDATE -> NORMAL` は禁止。
- `MANUAL_APPROVED -> NORMAL` は最新 Safety Check `ALLOW` の時のみ許可する設計。
- report / approval に forbidden secret / raw values が保存されない。

## 8. Safety Confirmation

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

## 9. Result

判定:

```text
PHASE11F_RECOVERY_MANUAL_UNLOCK_COMPLETE
PHASE11G_OR_PHASE11Z_READY
LIVE_ORDER_EXECUTION_REMAINS_BLOCKED
```
