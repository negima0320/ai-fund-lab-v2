# Phase12.5 Monday Broker ReadOnly Diagnosis Runbook

作成日: 2026-07-04

## 目的

月曜のBroker ReadOnly自然実行後に `positions_safe_diagnosis.json` を確認し、以下を切り分ける。

1. Broker Positions APIが本当に空なのか
2. normalizer key mapping不足なのか
3. writer/filterで落ちているのか
4. Persistent Ledger Phase Bへ進めるのか
5. normalizer修正を先にすべきか

Persistent Ledger Writer / Reader Layer は実装済みだが、Runtime本線接続、Broker Orders fallback、Unified Ledger Phase B はまだ実装しない。

## 前提

月曜の自然実行後、対象日をセットして確認する。

```bash
TRADE_DATE=YYYY-MM-DD
ROOT=.runtime/operations
```

例: 2026-07-06 の自然実行後なら `TRADE_DATE=2026-07-06`。

## 確認対象

```text
$ROOT/broker_readonly_reports/$TRADE_DATE/positions_safe_diagnosis.json
$ROOT/broker_positions/$TRADE_DATE/positions.json
$ROOT/broker_snapshot/$TRADE_DATE/broker_snapshot.json
$ROOT/broker_readonly_reports/$TRADE_DATE/broker_readonly_snapshot_report.json
$ROOT/broker_orders/$TRADE_DATE/orders.json
$ROOT/broker_executions/$TRADE_DATE/executions.json
```

## 1. 実行後確認コマンド

### 1.1 positions_safe_diagnosis.json の存在確認

```bash
test -f "$ROOT/broker_readonly_reports/$TRADE_DATE/positions_safe_diagnosis.json" && echo "diagnosis=FOUND" || echo "diagnosis=MISSING"
```

### 1.2 broker_readonly_snapshot_report status確認

```bash
python3 -m json.tool "$ROOT/broker_readonly_reports/$TRADE_DATE/broker_readonly_snapshot_report.json"
```

重点確認:

- `status`
- `health.login.status`
- `health.positions.status`
- `health.positions.count`
- `health.positions.candidate_key_match_rate`
- `positions_safe_diagnosis_path`

### 1.3 candidate_key_match_rate確認

```bash
python3 - <<'PY'
import json, os
root = os.environ.get("ROOT", ".runtime/operations")
trade_date = os.environ["TRADE_DATE"]
path = f"{root}/broker_readonly_reports/{trade_date}/positions_safe_diagnosis.json"
data = json.load(open(path))
print(json.dumps({
    "cash": {
        "top_level_keys": data.get("cash", {}).get("top_level_keys", []),
        "list_key_hits": data.get("cash", {}).get("list_key_hits", []),
        "row_count": data.get("cash", {}).get("row_count", 0),
        "row_key_names": data.get("cash", {}).get("row_key_names", []),
        "candidate_key_match_rate": data.get("cash", {}).get("candidate_key_match_rate", {}),
    },
    "margin": {
        "top_level_keys": data.get("margin", {}).get("top_level_keys", []),
        "list_key_hits": data.get("margin", {}).get("list_key_hits", []),
        "row_count": data.get("margin", {}).get("row_count", 0),
        "row_key_names": data.get("margin", {}).get("row_key_names", []),
        "candidate_key_match_rate": data.get("margin", {}).get("candidate_key_match_rate", {}),
    },
    "combined": data.get("combined", {}).get("candidate_key_match_rate", {}),
    "raw_response_saved": data.get("raw_response_saved"),
    "raw_values_saved": data.get("raw_values_saved"),
    "secret_saved": data.get("secret_saved"),
}, ensure_ascii=True, indent=2, sort_keys=True))
PY
```

重点確認:

- `cash.top_level_keys`
- `margin.top_level_keys`
- `cash.list_key_hits`
- `margin.list_key_hits`
- `cash.row_count`
- `margin.row_count`
- `cash.row_key_names`
- `margin.row_key_names`
- `combined.candidate_key_match_rate.issue_code`
- `combined.candidate_key_match_rate.quantity`
- `combined.candidate_key_match_rate.market_value`
- `combined.candidate_key_match_rate.price`
- `raw_response_saved=false`
- `raw_values_saved=false`
- `secret_saved=false`

### 1.4 broker_positions件数確認

```bash
python3 - <<'PY'
import json, os
root = os.environ.get("ROOT", ".runtime/operations")
trade_date = os.environ["TRADE_DATE"]
path = f"{root}/broker_positions/{trade_date}/positions.json"
data = json.load(open(path))
positions = data.get("positions") or []
print(json.dumps({
    "broker_positions_count": len(positions),
    "raw_response_saved": data.get("raw_response_saved"),
    "secret_saved": data.get("secret_saved"),
}, ensure_ascii=True, indent=2, sort_keys=True))
PY
```

### 1.5 broker_orders全部約定確認

```bash
python3 - <<'PY'
import json, os
from decimal import Decimal
root = os.environ.get("ROOT", ".runtime/operations")
trade_date = os.environ["TRADE_DATE"]
path = f"{root}/broker_orders/{trade_date}/orders.json"
data = json.load(open(path))
orders = data.get("orders") or []
filled = []
for row in orders:
    executed = Decimal(str(row.get("executed_quantity") or "0").replace(",", ""))
    remaining = Decimal(str(row.get("remaining_quantity") or "0").replace(",", ""))
    status = str(row.get("status") or "")
    if executed > 0 and remaining == 0 and status in {"全部約定", "FILLED", "DONE", "約定済"}:
        filled.append(row)
print(json.dumps({
    "broker_orders_count": len(orders),
    "filled_order_status_count": len(filled),
    "all_orders_filled_by_order_status": bool(orders) and len(filled) == len(orders),
    "raw_response_saved": data.get("raw_response_saved"),
    "secret_saved": data.get("secret_saved"),
}, ensure_ascii=True, indent=2, sort_keys=True))
PY
```

### 1.6 broker_executions件数確認

```bash
python3 - <<'PY'
import json, os
root = os.environ.get("ROOT", ".runtime/operations")
trade_date = os.environ["TRADE_DATE"]
path = f"{root}/broker_executions/{trade_date}/executions.json"
data = json.load(open(path))
executions = data.get("executions") or []
print(json.dumps({
    "broker_executions_count": len(executions),
    "classification": data.get("classification") or data.get("executions_classification"),
    "raw_response_saved": data.get("raw_response_saved"),
    "secret_saved": data.get("secret_saved"),
}, ensure_ascii=True, indent=2, sort_keys=True))
PY
```

### 1.7 broker_snapshot整合確認

```bash
python3 - <<'PY'
import json, os
root = os.environ.get("ROOT", ".runtime/operations")
trade_date = os.environ["TRADE_DATE"]
path = f"{root}/broker_snapshot/{trade_date}/broker_snapshot.json"
data = json.load(open(path))
print(json.dumps({
    "counts": data.get("counts", {}),
    "source_counts": data.get("source_counts", {}),
    "health_positions": data.get("health", {}).get("positions", {}),
    "positions_api_safe_diagnosis_path": data.get("positions_api_safe_diagnosis_path", ""),
    "raw_response_saved": data.get("raw_response_saved"),
    "secret_saved": data.get("secret_saved"),
}, ensure_ascii=True, indent=2, sort_keys=True))
PY
```

## 2. 判定ロジック

### A. diagnosis未生成

条件:

```text
positions_safe_diagnosis.json が存在しない
```

判定: `BLOCK`

理由:

safe diagnosisがまだ取れていないため、API空 / normalizer key不足 / writer filter を切り分けられない。

次アクション:

- Broker ReadOnlyがsafe diagnosis実装後のコードで自然実行されたか確認する。
- launchd / plist / WorkingDirectory / ProgramArguments / git反映状態を確認する。
- 実装や再実行は別指示で行う。

### B. candidate_key_match_rate が issue_code / quantity とも0

条件例:

```text
combined.candidate_key_match_rate.issue_code = 0/N
combined.candidate_key_match_rate.quantity = 0/N
row_count > 0
row_key_names は存在する
```

判定: `REVIEW_REQUIRED` から `BLOCK`

理由:

Positions APIは何らかの行を返しているが、normalizer候補keyに一致していない可能性が高い。API仕様上の別key、codec mapping不足、またはnormalizer candidate key不足が疑われる。

次アクション:

- `row_key_names` を確認する。
- secret/raw値を保存せず、key名だけで normalizer candidate key 追加要否を判断する。
- normalizer修正を先に検討する。
- Persistent Ledger Phase Bへは進めない。

### C. match rateあり、broker_positions=0

条件例:

```text
combined.candidate_key_match_rate.issue_code != 0/N
combined.candidate_key_match_rate.quantity != 0/N
broker_positions_count = 0
```

判定: `REVIEW_REQUIRED`

理由:

key名は一致しているため、normalizer candidate key不足だけでは説明できない。値が空/ゼロなのか、normalizer後にゼロ化されているのか、writer/filterで落ちているのかを確認する必要がある。

次アクション:

- `broker_snapshot.source_counts.positions`
- `broker_snapshot.counts.positions`
- `broker_positions.positions`
- `positions_safe_diagnosis.row_count`
- `positions_safe_diagnosis.candidate_key_match_rate`

を比較する。

次に見るべき箇所:

- normalizerが値をDecimal化できているか
- writerが `issue_code` と `quantity > 0` filterで落としているか
- APIがkeyだけ返して値は空/ゼロなのか

Persistent Ledger Phase Bへはまだ進めない。

### D. broker_positions > 0

条件:

```text
broker_positions_count > 0
```

判定: `PASS` 寄り

理由:

Broker Positions API / normalizer / writer の最低限の経路が成立している。

次アクション:

- Broker PositionsをPersistent Ledgerへ流すPhase B設計へ進む。
- ProductionではBroker Positions / Broker ExecutionsをSoTにする方針を維持する。
- DemoでもBroker Positionsが取れるなら、Broker Orders fallback projectionを本線にしない。

注意:

`broker_positions > 0` でも `review_required=true` や `source=broker_orders_fallback` が混ざる場合は、完全PASSではなく `REVIEW_REQUIRED` とする。

### E. broker_positions=0 だが broker_orders全部約定が確認できる

条件:

```text
broker_positions_count = 0
broker_orders_count > 0
all_orders_filled_by_order_status = true
```

判定: `REVIEW_REQUIRED`

理由:

Broker Orders上は全部約定が確認できるが、Broker Positions / Broker Executionsが確定SoTとして取れていない。

次アクション:

- Demo限定で `broker_orders_fallback` projectionを検討する。
- ただしProductionではBroker Orders fallbackを確定保有SoTにしない。
- fallback projectionを使う場合も必ず以下を付ける。

```json
{
  "source": "broker_orders_fallback",
  "review_required": true,
  "production_equivalent": false
}
```

Persistent Ledger Phase Bへ進めるのは、Demo限定review付きprojectionとして設計承認された場合のみ。

## 3. Persistent Ledger Phase Bへ進む条件

Phase Bへ進める条件:

1. Positions APIがDemo仕様で空/placeholderと判断できた。
2. またはBroker Orders fallbackをDemo限定review付きprojectionとして使う設計が承認済み。
3. ProductionではBroker Positions / Broker ExecutionsをSoTにする方針が維持されている。
4. `positions_safe_diagnosis.json` が生成済みで、raw response / raw values / secret を保存していない。
5. `broker_positions`, `broker_orders`, `broker_executions`, `broker_snapshot`, `broker_readonly_snapshot_report` の件数関係が説明できる。

Phase Bへ進めない条件:

- `positions_safe_diagnosis.json` が未生成。
- `row_key_names` があるのに normalizer candidate keyが未対応。
- match rateがあるのに writer/filterで0件になる理由が未説明。
- ProductionでもBroker Orders fallbackをSoTにする設計になっている。

## 4. 禁止事項

月曜確認時も以下は禁止。

- 実装禁止
- Submit実行禁止
- Broker注文禁止
- Production接続禁止
- Production注文禁止
- artifact削除禁止
- notification送信禁止
- Unified Ledger Phase B実装禁止
- Broker Orders fallback実装禁止
- Daily Plan / Approval / Report / Notification参照先切替禁止

## 5. 記録テンプレート

確認後、以下を埋める。

```text
TRADE_DATE:
diagnosis_exists:
broker_readonly_status:
health.positions.status:
health.positions.count:
cash.row_count:
margin.row_count:
combined.issue_code_match_rate:
combined.quantity_match_rate:
combined.market_value_match_rate:
combined.price_match_rate:
broker_positions_count:
broker_orders_count:
filled_order_status_count:
broker_executions_count:
cause_classification:
judgement: PASS / REVIEW_REQUIRED / BLOCK
phase_b_allowed: yes / no
next_action:
```
