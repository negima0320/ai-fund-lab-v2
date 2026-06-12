# AI Fund Lab vNext Safety Manual Unlock Apply Flow

---

# 1. このドキュメントの目的

本ドキュメントは、Phase3-F Manual Unlock Apply Flow の設計を定義する。

Phase3-Fは、Phase3-Eで保存した承認済み `UnlockApproval` を読み込み、手動unlockの適用結果を監査可能な形で保存する。

---

# 2. 基本方針

```text
Phase3-Fは手動承認済みunlockの適用だけ
自動復旧ではない
lockファイルは削除しない
解除済み状態を別JSONで保存する
latest SafetyReport OK が必須
UnlockApproval が必須
applied_by が必須
apply audit が必須
発注許可とはまだ接続しない
```

---

# 3. unlock apply条件

unlock applyには以下をすべて必要とする。

```text
承認済みUnlockApprovalが存在する
最新SafetyReportが存在する
最新SafetyReport.status が OK
approval.reconciliation_status が OK
approval.approved_by が存在する
approval.approval_reason が存在する
applied_by が存在する
unlock apply auditを保存する
```

最新SafetyReportが `WARNING` または `HALT` の場合、unlock applyは禁止する。

---

# 4. SafetyReport path差異の扱い

Phase3-Fでは、最新SafetyReport OKを優先する。

`approval.safety_report_path` と最新report pathが異なる場合でも、即拒否にはしない。

扱い:

```text
最新SafetyReportがOKならapply可能
path差異はaudit messageに残す
将来、運用要件が厳しくなった場合はpolicyで拒否可能にする
```

---

# 5. 保存先

解除済み状態:

```text
.runtime/safety/locks/
```

apply audit:

```text
.runtime/safety/unlock/apply_audit/
```

既存lockファイルは削除しない。

---

# 6. Phase3-Fで実装すること

```text
UnlockApproval reader
UnlockApplyResult model
unlock apply policy
unlock applied state writer
unlock apply audit writer
manual unlock apply flow
pytest
```

---

# 7. Phase3-Fで実装しないこと

```text
既存lockファイル削除
OperationGuard挙動変更
発注許可処理
実API接続
live mode
発注
訂正
取消
AI連携
Portfolio自動更新
Phase4以降のAI実装
```

---

# 8. Phase3-Gへの引き継ぎ

Phase3-Gでは、latest lock stateを読むOperationGuard拡張を検討する。

検討対象:

```text
latest unlock applied state reader
TradingLockとunlock applied stateの優先順位
OperationGuardがlatest lock stateを読む設計
解除済みでも再HALTなら即lock
unlock apply後の監査表示
```

Phase3-Gでも、発注機能や実API接続とは分離する。
