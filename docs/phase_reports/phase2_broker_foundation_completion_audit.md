# Phase2 Broker Foundation Completion Audit

---

# 1. Phase2の目的

Phase2 Broker Foundation の目的は、立花証券APIへ実接続する前に、Broker Sync の安全な土台を stub / mock で構築することである。

現時点では立花証券の契約が未完了のため、Phase2では実API接続を行わない。Phase2の成果物は、将来のlive接続前に、Portfolio State更新前inputとして使える broker snapshot と sync result を mock で再現できる状態にする。

---

# 2. Phase2で実装した範囲

実装済み:

```text
broker settings
secret sanitizer
read-only CLMID allowlist
mock transport
Tachibana request builder
read-only client skeleton
response envelope
normalized broker models
response normalizer
snapshot writer
mock broker sync runner
mock-only broker sync CLI
completion audit script
completion audit tests
```

主な実装ファイル:

```text
src/ai_fund_lab_v2/broker/settings.py
src/ai_fund_lab_v2/broker/sanitizer.py
src/ai_fund_lab_v2/broker/allowlist.py
src/ai_fund_lab_v2/broker/transport.py
src/ai_fund_lab_v2/broker/request_builder.py
src/ai_fund_lab_v2/broker/client.py
src/ai_fund_lab_v2/broker/response.py
src/ai_fund_lab_v2/broker/models.py
src/ai_fund_lab_v2/broker/normalizer.py
src/ai_fund_lab_v2/broker/snapshot_writer.py
src/ai_fund_lab_v2/broker/sync.py
src/ai_fund_lab_v2/broker/sync_result.py
src/ai_fund_lab_v2/cli/broker_sync.py
scripts/audit_phase2_broker_foundation.py
```

---

# 3. Phase2で明示的にやっていないこと

Phase2では以下を実装していない。

```text
実API呼び出し
実API login
実API logout
実API read smoke
live接続CLI
実HTTP transportの自動使用
新規注文
訂正注文
取消注文
売却注文
第二パスワード利用
実口座情報取得
AI接続
Portfolio State更新
Backtest連携
Paper Trading連携
```

---

# 4. Broker Foundation構成一覧

| 構成 | ファイル | 監査結果 |
| --- | --- | --- |
| settings | `broker/settings.py` | OK |
| sanitizer | `broker/sanitizer.py` | OK |
| allowlist | `broker/allowlist.py` | OK |
| mock transport | `broker/transport.py` | OK |
| request builder | `broker/request_builder.py` | OK |
| read-only client skeleton | `broker/client.py` | OK |
| response envelope | `broker/response.py` | OK |
| normalized models | `broker/models.py` | OK |
| normalizer | `broker/normalizer.py` | OK |
| snapshot writer | `broker/snapshot_writer.py` | OK |
| broker sync dry-run | `broker/sync.py` | OK |
| sync result | `broker/sync_result.py` | OK |
| CLI mock mode | `cli/broker_sync.py` | OK |

---

# 5. Read-only allowlist

Phase2で許可するCLMID:

```text
CLMAuthLoginRequest
CLMAuthLogoutRequest
CLMZanKaiSummary
CLMZanKaiKanougaku
CLMGenbutuKabuList
CLMShinyouTategyokuList
CLMOrderList
CLMOrderListDetail
```

`CLMAuthLoginRequest` と `CLMAuthLogoutRequest` は payload builder 用のstubであり、Phase2では実login/logoutを実行しない。

---

# 6. 禁止CLMID

Phase2で明示的に禁止するCLMID:

```text
CLMKabuNewOrder
CLMKabuCorrectOrder
CLMKabuCancelOrder
```

`ensure_read_only_clmid` と `MockBrokerTransport` は、禁止CLMIDおよびallowlist外CLMIDを例外にする。

---

# 7. 実API未接続確認

確認結果:

```text
live mode CLI: なし。broker_sync CLI は --mode mock のみ許可
実HTTP transportの自動使用: なし
login実行: なし。payload builderのみ
logout実行: なし。payload builderのみ
実API smoke: なし
発注系API呼び出し: なし
第二パスワード利用: なし
```

mock sync CLI:

```bash
PYTHONPATH=src python3 -m ai_fund_lab_v2.cli.broker_sync --mode mock --runtime-dir .runtime
```

---

# 8. 秘密情報保護確認

sanitizer対象:

```text
sAuthId
auth id
request URL
session URL
account id
password
second password
token
cookie
API応答内URL
```

確認結果:

```text
stdout: secret値を出さない
snapshot: secret値を保存しない
manifest: secret値を保存しない
repr: settings / response はsafe表示
account id: modelへ保存しない。必要な場合はhash化方針
raw response: normalized modelへ混入しない
```

---

# 9. Snapshot schema確認

## BrokerBalanceSnapshot

Portfolio State更新前inputとして必要な以下を保持する。

```text
snapshot_id
broker
source
as_of
currency
cash_available
buying_power
withdrawable_cash
total_assets
raw_clmid
raw_result_code
warnings
```

## BrokerPositionSnapshot

```text
snapshot_id
broker
source
as_of
account_type
issue_code
issue_name
quantity
available_quantity
average_price
market_price
market_value
unrealized_pnl
raw_clmid
raw_result_code
warnings
```

## BrokerOrderSnapshot

```text
snapshot_id
broker
source
as_of
order_id
issue_code
issue_name
side
order_type
quantity
executed_quantity
remaining_quantity
price
status
order_datetime
expire_date
raw_clmid
raw_result_code
warnings
```

## BrokerSyncResult

```text
sync_id
broker
source
started_at
finished_at
status
balance_snapshot_count
position_snapshot_count
order_snapshot_count
snapshot_paths
manifest_paths
warnings
errors
```

---

# 10. Broker Sync dry-run確認

Broker Sync dry-run は mock response のみで以下を実行する。

```text
1. balance summary取得
2. buying power取得
3. cash positions取得
4. margin positions取得
5. order list取得
6. normalizerで正規化
7. snapshot writerで保存
8. BrokerSyncResultを返す
```

保存先:

```text
.runtime/broker/snapshots/balance/
.runtime/broker/snapshots/positions/
.runtime/broker/snapshots/orders/
```

snapshot data JSON と manifest JSON が保存される。

---

# 11. pytest結果

B6監査時点の確認コマンド:

```bash
python3 -m pytest tests/broker/test_phase2_broker_completion_audit.py tests/cli/test_broker_sync_cli.py
```

結果:

```text
5 passed
```

全体pytestはB6完了時に再実行し、最終報告で結果を記録する。

全体pytest:

```bash
python3 -m pytest
```

結果:

```text
139 passed
```

補助監査script:

```bash
PYTHONPATH=src python3 scripts/audit_phase2_broker_foundation.py --runtime-dir .runtime
```

監査scriptは `status=complete` を返す。

---

# 12. Phase2完了判定

判定:

```text
Phase2 Complete
```

理由:

```text
実APIなしでBroker Sync dry-runが通る
balance / positions / orders snapshotが保存できる
sync resultが生成される
発注系APIが禁止されている
live接続CLIが存在しない
broker_sync CLIはmock modeのみ
秘密情報がsnapshot / manifest / stdoutへ保存・表示されない
Portfolio State更新前inputとして使える形式がある
completion audit testが通る
```

---

# 13. Phase3への引き継ぎ

Phase3で扱うべきこと:

```text
Portfolio State input schemaの確定
Broker snapshotからPortfolio Stateへ反映する前のvalidation
broker snapshotと内部portfolio stateの不一致検知
不一致時のHALT方針
Safety Guardとの接続
Phase2 snapshotを使ったPortfolio State更新dry-run
```

Phase3でも、実API接続や発注系APIに進む前に、mock snapshotを使った安全確認を優先する。

---

# 14. 立花証券契約後にやること

契約完了後に別Phaseとして実施すること:

```text
公式API仕様の再確認
認証方式の再確認
実HTTP transportの設計
live接続を明示的に有効化する設定
live read-only smoke CLI
login/logoutの最小read-only検証
実API応答とstub mappingの差分確認
第二パスワードを使わないread-only範囲の確認
rate limit / retry / timeout 方針
ログ・snapshot・manifestのsecret leak再監査
発注系APIは別Phaseで安全ガード完了後に検討
```
