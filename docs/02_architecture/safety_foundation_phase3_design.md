# AI Fund Lab vNext Phase3-A Safety Foundation Design

---

# 1. このドキュメントの目的

本ドキュメントは、vNext Phase3: Safety Foundation のうち、Phase3-Aとして実装前に必要な設計を定義する。

Phase3の目的は以下である。

```text
事故防止
異常検知
停止
監査
```

Phase3-Aは設計のみである。実装対象はまだ作らない。

---

# 2. 前提と現在地

`phase_roadmap.md` では、Phase3は Safety Foundation である。

Phase1ではData Foundationを作った。

Phase2では、実API未接続の Broker Foundation として以下を作った。

```text
mock broker sync
broker snapshot
BrokerSyncResult
balance / positions / orders normalized snapshot
```

Phase3では、Phase2のbroker snapshotと将来のPortfolio Stateを使い、異常検知と停止判断の土台を作る。

---

# 3. Safety Guardの最重要原則

Safety Guardの最重要原則は以下である。

```text
分からない時は止まる
```

追加原則:

```text
Broker状態を正とする
システム内部状態は参考
Broker Sync不一致はHALT
HALT時は新規買い禁止
自動復旧は禁止
復旧には人間承認が必要
```

禁止する考え方:

```text
多分大丈夫
きっと大丈夫
推測で継続
不一致を無視
同期失敗を無視
```

---

# 4. Phase3-Aのスコープ

Phase3-Aでやること:

```text
Portfolio State設計
Broker State設計
Reconciliation設計
Safety Status設計
HALT設計
Trading Lock設計
Safety Report設計
復旧フロー設計
Phase3-B以降のテスト方針定義
```

Phase3-Aでやらないこと:

```text
実装
発注機能
注文訂正
注文取消
live mode
実API接続
AI連携
Portfolio更新処理の実行
backtest
paper trading
Phase4以降のAI設計・実装
```

---

# 5. 状態モデル

## 5.1 PortfolioState

PortfolioStateは、システム内部が保持する参考状態である。

更新元は原則としてBroker Sync Managerのみとする。

Broker状態と矛盾した場合、Broker状態を正とし、PortfolioStateを正とは扱わない。

候補フィールド:

```text
portfolio_state_id
source
as_of
cash
buying_power
positions
open_orders
last_broker_sync_id
last_reconciliation_id
state_version
status
warnings
```

positionsの候補フィールド:

```text
issue_code
issue_name
account_type
quantity
available_quantity
average_price
market_price
market_value
unrealized_pnl
```

open_ordersの候補フィールド:

```text
order_id
issue_code
side
quantity
executed_quantity
remaining_quantity
status
order_datetime
expire_date
```

注意:

```text
PortfolioStateは学習入力にしない
backtest result / trade result / future情報と混ぜない
Brokerと不一致ならHALT
```

## 5.2 BrokerState

BrokerStateは、Broker Syncから得た証券会社側の状態である。

Phase2で作成した以下を入力にする。

```text
BrokerBalanceSnapshot
BrokerPositionSnapshot
BrokerOrderSnapshot
BrokerSyncResult
```

候補フィールド:

```text
broker_state_id
broker
source
as_of
sync_id
balance_snapshot_path
position_snapshot_path
order_snapshot_path
cash
buying_power
positions
open_orders
sync_status
warnings
errors
```

BrokerStateはReconciliationにおける正とする。

## 5.3 ReconciliationResult

ReconciliationResultは、PortfolioStateとBrokerStateの比較結果である。

候補フィールド:

```text
reconciliation_id
as_of
portfolio_state_id
broker_state_id
status
safety_status
trading_lock_required
matched
mismatches
warnings
errors
recommended_action
requires_human_approval
```

mismatchesの候補:

```text
cash_mismatch
buying_power_mismatch
position_quantity_mismatch
position_missing_in_broker
unknown_broker_position
margin_position_mismatch
open_order_mismatch
order_status_mismatch
duplicate_order_suspected
broker_sync_failed
portfolio_corrupted
```

## 5.4 SafetyStatus

SafetyStatusは3段階とする。

```text
OK
WARNING
HALT
```

OK:

```text
BrokerStateとPortfolioStateが一致している
重大なAPI/データ/注文異常がない
TradingLockは無効
```

WARNING:

```text
運用継続は可能
ログと通知が必要
新規買いを即停止するほどではない
```

HALT:

```text
新規買い禁止
新規発注禁止
人間確認待ち
自動復旧禁止
```

## 5.5 TradingLock

TradingLockは、SafetyStatusに基づいて売買操作を制限する状態である。

候補フィールド:

```text
lock_id
enabled
reason_code
reason_detail
safety_status
created_at
created_by
requires_human_approval
approved_by
approved_at
released_at
release_reason
```

HALT時は `enabled=true` とする。

TradingLockが有効な場合に禁止すること:

```text
新規買い
新規発注
自動復旧
推測による継続
```

TradingLockが有効でも許可すること:

```text
Broker Sync
状態取得
監査
Safety Report生成
```

## 5.6 SafetyReport

SafetyReportは、Safety Guardの判断結果を人間が確認できる形で保存する監査成果物である。

候補フィールド:

```text
report_id
created_at
safety_status
trading_lock_enabled
portfolio_state_id
broker_state_id
reconciliation_id
summary
detected_issues
halt_reasons
warning_reasons
allowed_actions
blocked_actions
required_human_actions
snapshot_refs
audit_refs
```

---

# 6. Reconciliation設計

## 6.1 比較対象

Reconciliationでは以下を比較する。

```text
cash
buying power
cash positions
margin positions
open orders
order status
```

BrokerStateを正とし、PortfolioStateは参考として比較する。

## 6.2 基本ルール

完全一致:

```text
SafetyStatus = OK
TradingLock = disabled
```

重大不一致:

```text
SafetyStatus = HALT
TradingLock = enabled
```

一時的な取得問題:

```text
SafetyStatus = WARNING
TradingLock = 原則disabled
```

ただし、取得問題により状態が分からない場合はHALTへ倒す。

## 6.3 不一致例

例:

```text
Broker: 7203 90株
System: 7203 100株
```

結果:

```text
mismatch_type = position_quantity_mismatch
SafetyStatus = HALT
TradingLock = enabled
recommended_action = BrokerStateを確認し、人間承認まで新規買い禁止
```

---

# 7. HALT条件

最低限、以下はHALTとする。

```text
Broker Sync不一致
残高不一致
保有株不一致
想定外ポジション
二重注文疑い
Portfolio破損
データ破損
API認証失敗
人間による停止指示
```

HALT時の禁止:

```text
新規買い
新規発注
自動復旧
推測による継続
```

HALT時の許可:

```text
Broker Sync
状態取得
監査
レポート生成
```

---

# 8. WARNING条件

最低限、以下はWARNINGとする。

```text
API遅延
一時的取得失敗
日次損失閾値超過
AI候補数異常
```

注意:

```text
Phase3-AではAI実装はしない
AI候補数異常は将来のSafety Guard入力として設計だけ定義する
WARNINGでも継続可否は状況によりHALTへ昇格できる
```

---

# 9. Trading Lock設計

TradingLockは、SafetyStatusがHALTになった時に有効化する。

Phase3では、少なくとも以下の判定を定義する。

```text
SafetyStatus=OK -> TradingLock disabled
SafetyStatus=WARNING -> TradingLock disabled。ただし手動設定でenabled可能
SafetyStatus=HALT -> TradingLock enabled
```

TradingLockは人間承認なしに解除しない。

解除に必要な情報:

```text
異常解消の確認
Broker Sync成功
Reconciliation再実行
Safety Report確認
人間承認
解除理由
承認者
承認時刻
```

---

# 10. 復旧フロー設計

復旧条件:

```text
異常解消
Broker Sync成功
Reconciliation結果がOKまたは許容可能なWARNING
Safety Report確認
人間承認
```

復旧フロー:

```text
1. HALT発生
2. TradingLock enabled
3. 新規買い・新規発注を停止
4. Broker Syncを再実行
5. BrokerStateを再作成
6. PortfolioStateとReconciliation
7. SafetyReportを生成
8. 人間が確認
9. 人間承認がある場合のみTradingLock解除
```

自動復旧は禁止。

---

# 11. 保存先案

Phase3の生成物は `.runtime` 配下へ集約する。

保存先案:

```text
.runtime/safety/reports/
.runtime/safety/locks/
.runtime/safety/audit/
```

保存対象:

```text
SafetyReport
TradingLock
ReconciliationResult
SafetyStatus履歴
HALT理由
WARNING理由
人間承認記録
```

注意:

```text
APIキー、token、cookie、password、第二パスワードを保存しない
実口座番号は保存しない。必要ならhashのみ
Broker raw responseそのものをSafetyReportへ混入しない
```

---

# 12. Safety Report設計

Safety Reportは、HALT/WARNING/OK判定の理由を監査可能にする。

最小構成:

```text
report_id
created_at
safety_status
trading_lock_enabled
summary
reconciliation_result
detected_issues
allowed_actions
blocked_actions
required_human_actions
input_snapshot_paths
```

HALT時は以下を必ず含める。

```text
halt_reason_code
halt_reason_detail
trading_lock_id
human_approval_required=true
auto_recovery_allowed=false
```

---

# 13. テスト方針

Phase3-B以降で実装するテスト方針を定義する。

必須ケース:

```text
完全一致ならOK
cash不一致ならHALT
buying power不一致ならHALTまたはWARNINGからHALT昇格
position数量不一致ならHALT
unknown positionならHALT
margin position不一致ならHALT
open order重複疑いならHALT
order status不一致ならHALTまたはWARNING
API一時失敗ならWARNING
API認証失敗ならHALT
Portfolio破損ならHALT
データ破損ならHALT
人間停止指示ならHALT
HALT時はTradingLock有効
HALT時は新規買い禁止
HALT後の自動復旧は禁止
復旧には人間承認が必要
SafetyReportが.runtime/safety/reports/に保存される
TradingLockが.runtime/safety/locks/に保存される
secretがreport/lock/auditに出ない
```

CLIやscriptを作る場合のテスト:

```text
mock inputのみで動く
実APIを呼ばない
live modeを持たない
発注系APIを呼ばない
PortfolioStateを勝手に更新しない
```

---

# 14. Phase3-Bで実装すべき内容

Phase3-Bでは、Phase3-Aの設計をもとに最小実装を行う。

候補:

```text
safety model dataclass
PortfolioState model
BrokerState model
ReconciliationResult model
SafetyStatus enum
TradingLock model
SafetyReport model
Reconciliation checker
SafetyReport writer
TradingLock writer
mock snapshot fixture
pytest
```

Phase3-Bでも禁止すること:

```text
実API接続
live mode
発注
注文訂正
注文取消
AI連携
PortfolioStateの自動更新
```

---

# 15. Phase3-A完了条件

Phase3-Aの完了条件:

```text
Phase3-A設計ドキュメントが作成されている
既存ロードマップと矛盾していない
Safety Guard設計と矛盾していない
Broker Integration設計と矛盾していない
Phase4以降のAI実装に進んでいない
実API、live mode、発注機能を追加していない
次のPhase3-B実装タスクが明確になっている
```

判定:

```text
Phase3-A Complete
```
