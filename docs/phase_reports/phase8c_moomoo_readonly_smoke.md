# Phase8-C moomoo Read-only Smoke

## 1. 目的

Phase8-Cでは、moomoo OpenD / OpenAPI のread-only smoke test入口を実装した。

目的:

```text
Mac上でread-only接続できるか確認する
実口座情報を取得してもsecret / real account id / raw payloadをrepoへ保存しない
発注系APIを実装しない
```

## 2. 実装範囲

追加・更新:

```text
src/ai_fund_lab_v2/broker/moomoo/readonly_client.py
src/ai_fund_lab_v2/broker/moomoo/readonly_smoke.py
src/ai_fund_lab_v2/broker/moomoo/normalizer.py
src/ai_fund_lab_v2/broker/moomoo/__init__.py
scripts/smoke_moomoo_readonly_phase8c.py
scripts/audit_phase8c_moomoo_readonly_smoke.py
tests/broker/test_phase8c_moomoo_readonly_safety.py
```

## 3. 実行境界

通常実行では外部接続しない。

実API read-only smokeを実行するには、以下の両方が必要。

```text
--run-readonly-smoke
AI_FUND_LAB_MOOMOO_READONLY_SMOKE=1
```

OpenD起動とログイン状態は人間が事前に準備する。

## 4. 設定

設定は環境変数、または `.runtime/broker/moomoo_readonly.local.json` から読む。

```text
AI_FUND_LAB_MOOMOO_HOST
AI_FUND_LAB_MOOMOO_PORT
AI_FUND_LAB_MOOMOO_MARKET
AI_FUND_LAB_MOOMOO_ENV
AI_FUND_LAB_MOOMOO_SDK_MODULE
```

secretは扱わない。

## 5. Read-only対象

許可するmethod:

```text
get_acc_list
accinfo_query
position_list_query
order_list_query
history_order_list_query
```

## 6. 保存方針

保存するもの:

```text
normalized account snapshot
normalized balance snapshot
normalized position snapshot
normalized order snapshot
normalized execution snapshot
BrokerSyncResult
smoke summary report
```

保存しないもの:

```text
raw payload
secret
real account id
account number
card number
```

account identifierは `acct_hash_*` として保存する。

## 7. 監査

audit script:

```text
scripts/audit_phase8c_moomoo_readonly_smoke.py
```

確認:

```text
read-only method setが設計通り
Phase8-C対象sourceに禁止API tokenがない
smoke scriptが明示フラグを要求する
smoke scriptが環境変数gateを要求する
raw payload保存名がない
```

実行結果:

```text
python3 scripts/audit_phase8c_moomoo_readonly_smoke.py
status = PASS

python3 scripts/audit_phase8b_moomoo_order_manager_foundation.py
status = PASS
```

## 8. テスト結果

```text
python3 -m pytest tests/broker/test_phase8c_moomoo_readonly_safety.py tests/broker/test_moomoo_normalizer.py tests/broker/test_moomoo_snapshot_writer.py tests/broker/test_phase8b_moomoo_audit.py
11 passed

python3 -m pytest tests/broker
56 passed

python3 -m pytest
805 passed, 22 warnings
```

## 9. 実API smoke実行状況

このPhase8-C実装ターンでは、実API smokeは実行していない。

確認したこと:

```text
python3 scripts/smoke_moomoo_readonly_phase8c.py --runtime-dir /private/tmp/phase8c-runtime --reports-dir /private/tmp/phase8c-reports
status = SKIPPED
executed = false
```

理由:

```text
明示フラグと環境変数gateがない限り外部接続しない設計であるため
```

## 10. Phase8-Dへの引き継ぎ

Phase8-Dでは、実API接続を広げる前に以下を実装する。

```text
Broker snapshot loader
Paper ledger schema
Broker snapshotとpaper ledgerの分離突合
Human Review report writer
read-only smoke結果のSafety Reconciliation接続
locked時のreview-only診断
```

実発注、自動発注、発注系API、trade unlock、自動login/logout、OpenD自動起動は引き続き禁止する。
