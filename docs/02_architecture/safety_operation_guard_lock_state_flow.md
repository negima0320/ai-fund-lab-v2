# AI Fund Lab vNext Safety OperationGuard Lock State Flow

---

# 1. このドキュメントの目的

本ドキュメントは、Phase3-G OperationGuard Lock State Integration の設計を定義する。

Phase3-Gでは、`.runtime/safety/locks/` に保存された最新lock stateを読み、OperationGuardの許可判定に接続する。

OperationGuardは発注機能ではない。操作を許可してよいかを判定するだけであり、実API、live mode、発注、訂正、取消には接続しない。

---

# 2. 最新状態を正とする

lock stateは `.runtime/safety/locks/` 配下の最新JSONを正とする。

対象:

```text
TradingLock JSON
UnlockApplyResult JSON
```

ルール:

```text
最新状態が TradingLock かつ is_locked=true なら locked
最新状態が UnlockApplyResult かつ applied=true なら unlocked
何もなければ unlocked / source=none
破損状態がある場合は fail-closed で locked
```

---

# 3. unlock後の再HALT方針

unlock applied後でも、新しい `TradingLock` が保存されたら再lockする。

理由:

```text
Safety Guardでは最新状態を正とする
unlock appliedは過去の解除適用記録であり、将来のHALTを上書きしない
新しいHALTは常に優先する
```

---

# 4. fail-closed原則

以下の場合はlocked扱いにする。

```text
最新lock state JSONが破損
最新lock state JSONが想定外schema
判定不能
```

分からない時は止まる。

---

# 5. locked時の操作判定

locked時に許可:

```text
broker_sync
read_state
audit
report
```

locked時に禁止:

```text
buy
sell
new_order
correct_order
cancel_order
portfolio_update
ai_trade_decision
```

unlocked時は原則許可する。

ただし、これは発注機能の存在や実行を意味しない。Phase3-Gは許可判定のみである。

---

# 6. Phase3-Gで実装すること

```text
latest lock state reader
current lock state resolver
OperationGuard current state判定
pytest
```

---

# 7. Phase3-Gで実装しないこと

```text
実API接続
live mode
発注機能
訂正
取消
AI連携
Portfolio自動更新
自動復旧
Phase4以降のAI実装
```

---

# 8. Phase3-Hへの引き継ぎ

Phase3-Hでは、Safety Foundation全体の完了監査を行う。

確認対象:

```text
Reconciliation
TradingLock
SafetyReport
Safety dry-run
Manual review
Manual unlock request / approval / apply
OperationGuard lock state判定
禁止事項監査
```
