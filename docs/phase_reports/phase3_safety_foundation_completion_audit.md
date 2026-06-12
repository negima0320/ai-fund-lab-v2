# AI Fund Lab vNext Phase3 Safety Foundation Completion Audit

## Phase3の目的

Phase3 Safety Foundation は、Broker状態とPortfolio状態の照合、HALT判定、TradingLock、SafetyReport、手動レビュー、手動unlock監査、OperationGuardの許可判定を整備し、事故防止の土台を作る段階である。

## 実装済みコンポーネント一覧

- Safety model: PortfolioState / BrokerState / ReconciliationResult / TradingLock / SafetyReport
- Reconciliation: cash / buying power / positions / open orders の照合
- HALT / TradingLock: HALT issueがあればlockを有効化
- SafetyReport writer: `.runtime/safety/reports/`
- TradingLock writer: `.runtime/safety/locks/`
- Audit writer: `.runtime/safety/audit/`
- Broker snapshot adapter: Phase2 snapshotからBrokerStateを構築
- Safety dry-run: mock PortfolioStateと照合しreport/lock/auditを保存
- Manual review flow: HALT時の人間確認手順
- Manual unlock request / approval / audit
- Manual unlock apply: approvalと最新OK report必須
- OperationGuard: 最新lock stateを読んだ許可判定

## Reconciliation / HALT / TradingLock / SafetyReport概要

Broker状態を正とし、Portfolio状態との不一致を検出する。cash、buying power、position数量、未知position、open order不一致や重複疑いはHALTとして扱い、TradingLockを有効化する。SafetyReportは照合結果とlock状態を監査可能なJSONとして保存する。

## Broker snapshot連携概要

Phase2のbalance / positions / orders snapshotをBrokerStateへ変換するadapterを用意している。Phase3では実API接続は行わず、snapshot入力をdry-runの材料に限定する。

## Dry-run概要

`scripts/safety/run_safety_dry_run.py` はmock専用で、live modeや実API引数を持たない。実行結果としてstatus、issue_count、trading_locked、report/lock/audit pathを出力する。

## Manual Review概要

HALT時はSafetyReport、TradingLock、Audit、Broker snapshot、PortfolioStateを人間が確認する。不明な場合はHALTを維持し、修正は別作業として人間が実施する。

## Manual Unlock概要

unlock request / approval / auditを保存する。承認にはSafetyReport OK、承認者、理由、再照合結果が必要で、Phase3では自動復旧として扱わない。

## Unlock Apply概要

承認済みUnlockApprovalと最新OK SafetyReportがある場合だけ、解除適用状態を新しいJSONとして保存する。既存lockファイルは削除しない。

## OperationGuard概要

`.runtime/safety/locks/` の最新状態を正とする。最新TradingLockがlockedなら危険操作は禁止し、最新UnlockApplyResultがappliedならunlocked扱いにする。破損状態はfail-closedでlocked扱いにする。

## 禁止事項遵守

実API、live mode、発注、訂正、取消、AI連携、Portfolio自動更新、自動復旧はPhase3-H監査時点で追加していない。

## Audit Checks

- `broker_snapshot_integration`: OK
- `dry_run`: OK
- `fail_closed`: OK
- `manual_review`: OK
- `manual_unlock`: OK
- `manual_unlock_apply`: OK
- `no_ai_integration`: OK
- `no_auto_recovery`: OK
- `no_live_mode`: OK
- `no_ordering`: OK
- `no_real_api`: OK
- `operation_guard_lock_state`: OK
- `reconciliation`: OK
- `runtime_safety_paths`: OK
- `safety_models`: OK
- `safety_report`: OK
- `tests_present`: OK
- `trading_lock`: OK

## pytest結果欄

確認コマンド: `python3 -m pytest tests/safety -q && python3 -m pytest -q`

## Phase3完了判定

`Phase3 Complete`

## Phase4へ進む前の注意

Phase4以降でAIや注文系に進む場合も、Phase3のOperationGuardとTradingLockを必ず前段に置く。実API接続や発注機能を作る場合は、別途live接続監査、秘密情報監査、発注禁止テストから始める。
