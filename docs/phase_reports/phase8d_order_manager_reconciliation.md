# Phase8-D Order Manager Reconciliation

## 1. 目的

Phase8-Dでは、実API smokeを実行せず、mock / normalized snapshotを入力にしたOrder Manager基盤を実装した。

実装対象:

```text
Broker snapshot loader
Paper ledger schema
Broker snapshotとPaper ledgerの分離突合
Human Review report writer
Safety Reconciliation接続
locked時のreview-only診断出力
```

## 2. 実装境界

Phase8-Dでは以下を実行しない。

```text
moomoo SDK接続
OpenD接続
実API smoke
OpenD自動起動
自動login/logout
trade unlock
実発注
自動発注
raw moomoo response保存
```

## 3. Reconciliation仕様

Broker snapshotを正とし、Paper ledgerは参考状態として比較する。

比較対象:

```text
cash / buying power
positions
open orders
executions
```

差分がある場合:

```text
warning = true
halt_candidate = true または warning
mismatch detailを保存
```

不明、欠損、破損、timestamp不整合はfail-closedとして扱う。

## 4. locked時挙動

Safety lock stateがlockedの場合:

```text
通常plan生成は禁止
review-only diagnostic planのみ生成
plan_status = REVIEW_ONLY_LOCKED
executable = false
live_order_allowed = false
requires_human_review = true
```

## 5. 保存先

Broker snapshot:

```text
.runtime/broker/snapshots/
.runtime/broker/sync_results/
```

Paper ledger:

```text
.runtime/order_manager/paper/ledgers/
```

Human Review report:

```text
.runtime/order_manager/review/
docs/phase_reports/
```

## 6. Audit

audit script:

```text
scripts/audit_phase8d_order_manager_reconciliation.py
```

確認対象:

```text
発注系API token不在
OrderPlan安全境界
locked時REVIEW_ONLY_LOCKED
paper ledgerとBroker snapshot保存先分離
raw payload / secret / real account identifier平文保存なし
```

実行結果:

```text
python3 scripts/audit_phase8b_moomoo_order_manager_foundation.py
status = PASS

python3 scripts/audit_phase8c_moomoo_readonly_smoke.py
status = PASS

python3 scripts/audit_phase8d_order_manager_reconciliation.py
status = PASS
```

## 7. テスト結果

```text
python3 -m pytest tests/order_manager tests/broker/test_moomoo_normalizer.py tests/broker/test_moomoo_snapshot_writer.py
17 passed

python3 -m pytest tests/order_manager
13 passed

python3 -m pytest tests/broker
56 passed

python3 -m pytest
815 passed, 22 warnings
```

## 8. Smoke script確認

Phase8-Dでは実API smokeを実行していない。

確認:

```text
python3 scripts/smoke_moomoo_readonly_phase8c.py --runtime-dir /private/tmp/phase8d-runtime --reports-dir /private/tmp/phase8d-reports
status = SKIPPED
executed = false
```

## 9. Phase8-Eへの引き継ぎ

Phase8-Eでは、実API接続を広げる前に以下を実装する。

```text
Order Plan Generator
Capital Allocation decision loader
Human Review approval record
Paper ledger update flow
SELL_FIRST_BUY_AFTER_FILL dependency validation
read-only smoke resultからSafety dry-runへの接続強化
```

実発注、自動発注、trade unlock、発注系API、OpenD自動起動は引き続き禁止する。
