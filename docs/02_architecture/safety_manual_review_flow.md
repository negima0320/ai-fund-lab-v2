# AI Fund Lab vNext Safety Manual Review Flow

---

# 1. このドキュメントの目的

本ドキュメントは、Safety Foundationで `HALT` が発生した場合の人間確認フローを定義する。

Phase3-Dでは、Safety dry-runから `SafetyReport`, `TradingLock`, `Audit` を出力し、人間が確認できる状態を作る。

Phase3-Dでは lock解除や復旧は実装しない。

---

# 2. 最重要原則

```text
分からない時は止まる
Broker状態を正とする
システム内部状態は参考
Broker Sync不一致はHALT
自動復旧は禁止
lock解除には人間承認が必要
```

---

# 3. HALT発生時の人間確認手順

1. `SafetyReport` を確認する。
2. `TradingLock` が有効であることを確認する。
3. `Audit` 履歴を確認する。
4. Broker snapshotを確認する。
5. PortfolioStateを確認する。
6. 不一致理由を特定する。
7. 必要な修正を人間が別作業として実施する。
8. 再度Broker SyncまたはSafety dry-runを実行する。
9. SafetyReportを再確認する。
10. 人間承認がある場合のみlock解除を検討する。

---

# 4. 確認対象

## SafetyReport

確認項目:

```text
status
issue_count
issues
trading_locked
broker_snapshot_id
checked_at
```

## Broker snapshot

確認項目:

```text
balance snapshot
position snapshot
order snapshot
snapshot_id
as_of
cash
buying_power
positions
open_orders
```

## PortfolioState

確認項目:

```text
cash
buying_power
positions
open_orders
as_of
```

PortfolioStateは参考状態であり、BrokerStateと矛盾した場合はBrokerStateを正とする。

---

# 5. 不一致理由の特定

代表例:

```text
cash_mismatch
buying_power_mismatch
position_quantity_mismatch
unknown_position
position_missing_in_broker
open_order_mismatch
duplicate_open_order_suspected
broker_snapshot_id_missing
```

不一致理由が特定できない場合は、HALTを維持する。

---

# 6. 修正方針

修正は人間が別作業として実施する。

Phase3-Dでは以下を実装しない。

```text
自動復旧
自動lock解除
PortfolioState自動更新
発注
訂正
取消
live mode
実API接続
AI連携
```

---

# 7. lock解除方針

lock解除には以下が必要である。

```text
異常解消
Broker snapshot確認
PortfolioState確認
SafetyReport確認
再照合結果の確認
人間承認
承認者
承認時刻
解除理由
監査ログ
```

Phase3-Dでは解除実装を行わない。

Phase3-Eで、手動承認つきunlock設計・監査を検討する。

---

# 8. Phase3-Dで提供するもの

Phase3-Dで提供するもの:

```text
broker snapshot loader
mock-only safety dry-run script
safety history reader
SafetyReport出力
TradingLock出力
Audit出力
```

Phase3-Dで提供しないもの:

```text
unlock実装
復旧実装
live接続
実API接続
発注機能
AI判断接続
```
