# Phase14-E19 Runtime v2 Submit Issue Code Normalization Fix

作成日: 2026-07-08

## 最終判定

**PHASE14E19_SUBMIT_ISSUE_CODE_NORMALIZATION_FIXED**

## 目的

Phase14-E18で特定したReject root causeを修正した。

Root cause:

```text
Runtime v2 Submit pathで既存Broker issue code normalizerが未接続
↓
Tachibana CLMKabuNewOrder sIssueCodeへJ-Quants/internal 5桁コードをそのまま送信
```

E19では、新しいnormalizerを作らず、既存の以下をRuntime v2 Submit adapter境界へ接続した。

```text
src/ai_fund_lab_v2/broker/issue_code_normalizer.py
```

## 実装方針

OrderPlan / Pending / RuntimeV2SubmitCommandでは内部コードを保持する。

Broker request境界でのみ、既存normalizerを使ってBroker向けコードへ変換する。

```text
OrderPlan/Pending/SubmitCommand symbol = 65220
Broker request sIssueCode = 6522
```

Runtime v2本体から `ai_fund_lab_v2.broker.*` を静的importしない契約も維持した。

## 実装内容

### 1. Pendingへlisted_infoを保持

更新:

- `src/ai_fund_lab_v2/runtime_v2/pending/models.py`
- `src/ai_fund_lab_v2/runtime_v2/pending/reader.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py`

Morning PipelineのFeature inputには以下が存在している。

- `product_category`
- `market_name`
- `is_current_listed`

これをsanitized `listed_info` としてPending itemへ保持する。

### 2. RuntimeV2SubmitCommandへlisted_infoを引き継ぎ

更新:

- `src/ai_fund_lab_v2/runtime_v2/submit/models.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/guards.py`

SubmitCommandの `symbol` は内部コードのまま維持し、`listed_info` だけ追加した。

### 3. Broker request境界で既存normalizerを適用

更新:

- `src/ai_fund_lab_v2/broker/tachibana_order_request.py`

`TachibanaCashStockOrderRequest.from_runtime_v2_submit_command(...)` で以下を実行する。

```text
normalize_broker_issue_code(command.symbol, listed_info=command.listed_info)
```

その結果だけをBroker request `sIssueCode` に使う。

### 4. Demo AdapterでFail Closed

更新:

- `src/ai_fund_lab_v2/broker/runtime_v2_demo_submit_adapter.py`

listed info不足や正規化失敗時は、Broker APIを呼ぶ前に `BLOCKED` を返す。

### 5. Manifest / Ledger metadata

更新:

- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/ledger/models.py`

Submit result / manifest / Ledger orderへ以下をsanitized metadataとして残す。

- `original_symbol`
- `broker_issue_code`
- `broker_market_code`
- `normalization_rule`
- `normalization_status`
- `market`
- `product_category`
- `security_type`

Response normalizerの二次Gapにも対応し、以下をredacted classificationとして残す経路を追加した。

- `p_errno`
- `sResultCode`
- `p_err_classification`
- `business_classification`
- `order_number_present`
- `result_code_present`
- `result_code_zero`
- `warning_code_present`
- `warning_code_value`
- `warning_code_zero`

raw request / raw response / secretは保存しない。

## Broker Request Safe Summary Evidence

Broker APIは呼ばず、request builderのsafe summaryで確認した。

| Internal Symbol | Broker sIssueCode | Rule |
| --- | --- | --- |
| 65220 | 6522 | JQUANTS_5CHAR_TRAILING_ZERO_TO_BROKER_4CHAR |
| 78780 | 7878 | JQUANTS_5CHAR_TRAILING_ZERO_TO_BROKER_4CHAR |
| 68970 | 6897 | JQUANTS_5CHAR_TRAILING_ZERO_TO_BROKER_4CHAR |
| 63270 | 6327 | JQUANTS_5CHAR_TRAILING_ZERO_TO_BROKER_4CHAR |
| 45910 | 4591 | JQUANTS_5CHAR_TRAILING_ZERO_TO_BROKER_4CHAR |
| 7203 | 7203 | BROKER_4CHAR_ALREADY_NORMALIZED |

これにより、E17でRejectされた5件について、Brokerへ渡る `sIssueCode` は4桁になることを確認した。

## E17 Pending Reuse

E17のPendingは以下のまま維持している。

```text
state=CONSUMED
consumed=true
submitted_order_ids=5
```

E19ではこのCONSUMED Pendingを再Submitしていない。

## Demo Submit再実行

E19ではDemo Submit再実行は行っていない。

理由:

- E17 PendingはCONSUMED済みで再利用禁止。
- 追加Submitする場合は、新しいMorning / Approval / Pendingを通常経路で作る必要がある。
- 今回はBroker request safe summaryで、修正後の `sIssueCode` が4桁になる証拠を残せた。

## Tests

追加:

- `tests/runtime_v2/test_phase14e19_submit_issue_code_normalization.py`

確認:

- `65220 -> 6522`
- `78780 -> 7878`
- `68970 -> 6897`
- `63270 -> 6327`
- `45910 -> 4591`
- 4桁 `7203` は維持
- listed info不足時はBroker API前にBLOCK
- Demo 9000番台BLOCK維持
- Production capabilityでは9000番台をBLOCKしない
- Submit pipeline resultにnormalization metadataが残る
- Ledger orderにnormalization metadataが残る
- response classification detailがredactedで残る

Focused:

```text
python3 -m pytest tests/runtime_v2/test_phase14e19_submit_issue_code_normalization.py tests/runtime_v2/test_phase14d4_tachibana_demo_submit_adapter.py tests/runtime_v2/test_phase14d14_demo_sell_guarded_preflight.py tests/runtime_v2/test_phase14e17_submit_pipeline_connection.py
20 passed
```

Full:

```text
python3 -m pytest tests/runtime_v2
323 passed
```

## Prohibited Actions

- Production注文: なし
- Production Broker API Write: なし
- Notification実送信: なし
- launchd load/unload/bootstrap: なし
- Phase9 Runtime呼び出し: なし
- Phase9 writer呼び出し: なし
- `.runtime/demo` Current path復活: なし
- phase artifact Current扱い: なし
- raw request保存: なし
- raw response保存: なし
- secret保存: なし
- 新規normalizer作成: なし
- E17 CONSUMED Pending再利用: なし

## Acceptance

| Criteria | Result |
| --- | --- |
| 既存 issue_code_normalizer を使っている | PASS |
| 新しいnormalizerを作っていない | PASS |
| Runtime v2 Submit pathでnormalizerが接続されている | PASS |
| Broker request sIssueCodeが4桁になる | PASS |
| 5桁内部コードはOrderPlan/Pending/SubmitCommand側では保持可能 | PASS |
| manifest / ledger / auditにsanitized normalization metadataが残る | PASS |
| response classification detailがredactedで残る | PASS |
| 9000番台Demo BLOCK維持 | PASS |
| Production 9000番台許可維持 | PASS |
| E17のCONSUMED Pendingを再利用しない | PASS |
| tests/runtime_v2 PASS | PASS |
| Production注文なし | PASS |
| Notification実送信なし | PASS |
| Phase9未使用 | PASS |

## Next

次にDemo Submit再試験を行う場合は、必ず新しいMorning / Approval / Pendingを通常経路で生成し、Submit前manifestまたはadapter preflightで `broker_issue_code` が4桁であることを確認してから実行する。
