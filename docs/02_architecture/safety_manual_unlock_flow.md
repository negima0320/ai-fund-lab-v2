# AI Fund Lab vNext Safety Manual Unlock Flow

---

# 1. このドキュメントの目的

本ドキュメントは、Phase3-E Manual Unlock Design & Audit の設計を定義する。

目的は、HALT / TradingLock 発生後に、人間承認つきで解除を検討するための申請・承認・監査記録を作ることである。

Phase3-Eでは lock解除そのものは実行しない。

---

# 2. 基本原則

```text
unlockは自動復旧ではない
unlock前に最新Broker snapshotで再照合が必要
Reconciliation OKでなければ解除不可
SafetyReport確認が必要
requested_by が必須
reason が必須
approved_by が必須
approval_reason が必須
```

禁止:

```text
自動復旧
再照合なしのunlock
承認者なしのunlock
理由なしのunlock
実API接続
live mode
発注
訂正
取消
AI連携
Portfolio自動更新
```

---

# 3. unlock前提条件

unlock承認前に必須とすること:

```text
1. 最新Broker snapshotで再照合する
2. Reconciliation結果がOKである
3. SafetyReportを人間が確認する
4. unlock requestを作る
5. 人間承認情報を保存する
6. unlock auditを保存する
```

HALTまたはWARNINGのSafetyReportでは承認不可とする。

---

# 4. request者とapprove者

Phase3-Eでは、request者とapprove者が同一でも許可する。

理由:

```text
Phase3-Eは手動承認記録と監査基盤の段階
運用体制が未確定
将来、権限分離が必要になった時にpolicyで制限可能にする
```

将来の拡張:

```text
request者とapprove者の分離
承認者role
二人承認
承認期限
```

---

# 5. 保存先

unlock関連の保存先:

```text
.runtime/safety/unlock/requests/
.runtime/safety/unlock/approvals/
.runtime/safety/unlock/audit/
```

保存内容:

```text
UnlockRequest
UnlockApproval
UnlockAuditRecord
```

secret、URL、token、cookie、password、第二パスワードは保存しない。

---

# 6. Phase3-Eで実装すること

```text
UnlockRequest model
UnlockApproval model
UnlockAuditRecord model
unlock policy
unlock writer
manual unlock request作成
manual unlock approval記録
unlock audit記録
```

---

# 7. Phase3-Eで実装しないこと

```text
TradingLockの削除
TradingLockの無効化
lock解除適用処理
自動復旧
実API接続
live mode
発注
訂正
取消
Portfolio自動更新
AI連携
```

---

# 8. Phase3-Fへの引き継ぎ

Phase3-Fでは、手動承認済みunlockを実際のTradingLock状態に適用する設計を検討する。

Phase3-Fで検討すること:

```text
承認済みUnlockApprovalの読み込み
最新SafetyReportがOKであることの再確認
最新Broker snapshotでの再照合
TradingLock解除適用
解除前後のaudit
解除後に許可される操作の再評価
自動復旧禁止の維持
```

Phase3-Fでも、実API接続や発注機能とは分離する。
