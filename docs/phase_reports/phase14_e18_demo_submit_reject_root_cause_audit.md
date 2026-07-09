# Phase14-E18 Demo Submit Reject Root Cause Audit

作成日: 2026-07-08

## 最終判定

**PHASE14E18_REJECT_ROOT_CAUSE_IDENTIFIED**

## 結論

E17の5件Reject主因は、**Runtime v2 SubmitCommand / Demo Adapter境界でBroker向け銘柄コード正規化が未接続だったこと**である。

分類:

- A. Runtimeデグレ: **YES**
  - Morning Pipeline / Pending / SubmitCommandがJ-Quants内部コード5桁をそのままSubmitCommand symbolとして保持した。
- B. Submit parameter誤り: **YES**
  - Broker request `sIssueCode` に `65220`, `78780`, `68970`, `63270`, `45910` がそのまま渡った。
- C. Broker Adapter誤り: **YES**
  - `TachibanaCashStockOrderRequest.from_runtime_v2_submit_command(...)` が `command.symbol` をそのまま `issue_code` / `sIssueCode` に使っている。
- D. Tachibana Demo仕様: **NO, primary evidenceなし**
  - 「DemoだからReject」とする証拠はない。
- E. Broker Response Normalizer: **SECONDARY GAP**
  - `REJECTED_OR_UNKNOWN` への分類自体は安全側だが、adapterが `p_errno` / `sResultCode` / `p_err_classification` 等のredacted detailをRuntimeV2SubmitResultへ保持していないため、Reject理由の後追い証跡が弱い。

Primary root cause:

```text
J-Quants/internal code 5桁末尾0
↓
RuntimeV2SubmitCommand.symbol にそのまま入る
↓
TachibanaCashStockOrderRequest.issue_code にそのまま入る
↓
CLMKabuNewOrder sIssueCode に5桁で送信
↓
Broker reject
```

Expected:

```text
65220 -> 6522
78780 -> 7878
68970 -> 6897
63270 -> 6327
45910 -> 4591
```

## 調査制約

今回は調査のみ。

- コード変更: なし
- 追加Submit: なし
- Broker API Write: なし
- Notification送信: なし
- launchd変更: なし

参照したのは保存済みartifactと既存コードのみである。

## Evidence 1: E17 Submit Result

E17 manifest:

```text
.runtime/runtime_state/run_manifest/2026-07-08/runtime-v2-submit-2026-07-08-20260708T053642.093652+0000.json
```

結果:

| Field | Value |
| --- | --- |
| exit_code | 20 |
| final_state | REVIEW_REQUIRED |
| demo_submit_executed | true |
| submitted_count | 5 |
| accepted_count | 0 |
| rejected_count | 5 |
| unknown_count | 0 |
| blocked_count | 0 |
| pending_consumed | true |

5件すべて:

```text
submit_status=REJECTED_OR_UNKNOWN
reason=normalized_redacted_order_submit_result
preflight_status=PASS
submitted=true
blocked=false
unknown=false
```

つまり、Runtime guardで止まったのではなく、Broker submit後のresponseがaccept条件を満たさなかった。

## Evidence 2: OrderPlan / Pending / SubmitCommand の値

Morning Pipelineが生成したOrderPlan:

```text
.runtime/runtime_state/morning_pipeline/2026-07-08/order_plan.json
```

Pending Current:

```text
.runtime/pending_order_plan/pending_order_plan.json
```

OrderPlanからPendingまで、以下の値は一貫している。

| Symbol | Side | Quantity | Order Type | Estimated Price | Estimated Amount |
| --- | --- | ---: | --- | ---: | ---: |
| 65220 | BUY | 100 | MARKET | 1000 | 100000 |
| 78780 | BUY | 100 | MARKET | 1000 | 100000 |
| 68970 | BUY | 100 | MARKET | 1000 | 100000 |
| 63270 | BUY | 100 | MARKET | 1000 | 100000 |
| 45910 | BUY | 100 | MARKET | 1000 | 100000 |

PendingはE17後に `CONSUMED` となり、再Submitは禁止されている。

```text
consume_reason=runtime_v2 submit attempted with partial failure; automatic resubmit forbidden
raw_request_saved=false
raw_response_saved=false
secret_saved=false
```

## Evidence 3: SubmitCommand -> Demo Adapter -> Broker Request で値が変化していない

既存の変換コード:

```text
src/ai_fund_lab_v2/broker/tachibana_order_request.py
```

`TachibanaCashStockOrderRequest.from_runtime_v2_submit_command(...)` は以下の通り、`command.symbol` をそのまま `issue_code` へ入れている。

```text
issue_code=command.symbol
```

`TachibanaCashStockOrderRequestBuilder.build(...)` は `issue_code` をそのまま `sIssueCode` へ入れる。

```text
sIssueCode = request.issue_code
```

E17のBroker request safe summary:

| Pending Symbol | Runtime Command Symbol | Broker sIssueCode | Side | Quantity | Price Type | Price | Market | Account | Cash/Margin |
| --- | --- | --- | --- | ---: | --- | ---: | --- | --- | --- |
| 65220 | 65220 | 65220 | BUY | 100 | MARKET | 0 | 00 | 1 | 0 |
| 78780 | 78780 | 78780 | BUY | 100 | MARKET | 0 | 00 | 1 | 0 |
| 68970 | 68970 | 68970 | BUY | 100 | MARKET | 0 | 00 | 1 | 0 |
| 63270 | 63270 | 63270 | BUY | 100 | MARKET | 0 | 00 | 1 | 0 |
| 45910 | 45910 | 45910 | BUY | 100 | MARKET | 0 | 00 | 1 | 0 |

価格、数量、売買区分、現物/特定、market codeはD15成功時と同系統であり、差分として目立つのは `sIssueCode` の5桁形式である。

## Evidence 4: D15成功時との差分

D15成功レポート:

```text
reports/phase_reports/phase14_d15_demo_sell_single_order_guarded_test.json
```

D15:

| Field | Value |
| --- | --- |
| symbol | 7203 |
| side | SELL |
| quantity | 100 |
| order_type | MARKET |
| adapter_preflight_status | DRY_RUN_READY |
| submit_preflight_status | PASS |
| submit_status | ACCEPTED |
| demo_order_accepted | true |
| broker_api_called | true |

D15 Broker request safe summary:

| sIssueCode | Side | Quantity | Price Type | Price | Market |
| --- | --- | ---: | --- | ---: | --- |
| 7203 | SELL | 100 | MARKET | 0 | 00 |

D15は4桁 `7203` でaccepted。

E17は同じRuntime v2-native adapterを使い、MARKET / quantity=100 / market=00 / account=1 / cash=0 は同系統だが、`sIssueCode` が5桁だった。

## Evidence 5: 既存Issue Code Normalizerは正しい4桁変換を持っている

既存コード:

```text
src/ai_fund_lab_v2/broker/issue_code_normalizer.py
```

既存設計:

```text
len(code) == 5 and code.endswith("0")
↓
broker_code = code[:-1]
normalization_rule = JQUANTS_5CHAR_TRAILING_ZERO_TO_BROKER_4CHAR
```

E17対象5件に既存normalizerを適用した結果:

| Internal / J-Quants Code | Expected Broker sIssueCode | Rule |
| --- | --- | --- |
| 65220 | 6522 | JQUANTS_5CHAR_TRAILING_ZERO_TO_BROKER_4CHAR |
| 78780 | 7878 | JQUANTS_5CHAR_TRAILING_ZERO_TO_BROKER_4CHAR |
| 68970 | 6897 | JQUANTS_5CHAR_TRAILING_ZERO_TO_BROKER_4CHAR |
| 63270 | 6327 | JQUANTS_5CHAR_TRAILING_ZERO_TO_BROKER_4CHAR |
| 45910 | 4591 | JQUANTS_5CHAR_TRAILING_ZERO_TO_BROKER_4CHAR |

従って、normalizer自体は存在するが、Runtime v2 Submit pathでは未接続だった。

## Evidence 6: Phase12の既知Rejectと同型

Phase12X資料:

```text
docs/phase_reports/phase12x_broker_issue_code_normalization_review.md
```

当時の既知Reject:

```text
Order Plan issue_code=92560
Broker request sIssueCode=92560
sResultCode=11104
銘柄がありません / 銘柄マスタレコードなし
```

結論:

```text
Tachibana CLMKabuNewOrder should receive broker issue code 9256 for this security, not internal code 92560.
```

E17はこれと同型である。

```text
OrderPlan symbol=65220
Broker request sIssueCode=65220
Expected broker sIssueCode=6522
```

## Response Normalizer Review

Normalizer:

```text
normalize_redacted_order_submit_result(raw)
```

Accepted条件:

```text
not protocol_error
and sResultCode == "0"
and order_id present
```

E17では `accepted=false` となり、`REJECTED_OR_UNKNOWN` へ分類された。

この分類は安全側として妥当だが、RuntimeV2SubmitResultに以下が保持されていない。

- p_errno
- sResultCode
- sWarningCode
- p_err_classification
- business_classification
- result_code_present
- order_number_present

そのため、E17 artifactだけではBrokerの具体Reject理由を再現できない。

ただし、これは主因ではなく二次的な監査ギャップである。主因はBroker request境界の `sIssueCode` 正規化未接続である。

## Root Cause Classification

| Candidate | 判定 | 根拠 |
| --- | --- | --- |
| A. Runtimeデグレ | ROOT_CAUSE_PART | Runtime v2 Morning/Submit pathが5桁内部コードをBroker boundaryへそのまま渡した |
| B. Submit parameter誤り | ROOT_CAUSE | `sIssueCode` がBroker向け4桁でなく5桁だった |
| C. Broker Adapter誤り | ROOT_CAUSE_PART | `from_runtime_v2_submit_command` がissue_code normalizerを呼ばない |
| D. Tachibana Demo仕様 | NOT_SUPPORTED | D15ではDemo SELL 7203 accepted。Demo一般Rejectとは言えない |
| E. Response Normalizer | SECONDARY_GAP | Reject詳細をRuntime resultへ保持していないが、5桁issue code問題の説明力が高い |

## 必要な次修正

次フェーズで実装すべき修正:

1. Runtime v2 Submit pathで、Broker Adapter境界直前に `normalize_broker_issue_code(...)` を必須化する。
2. OrderPlan / Pending / SubmitCommandの `symbol` は内部コードとして保持してよい。
3. Broker request onlyで `broker_issue_code` を使う。
4. listed info / market / product_category / security_type がない場合はSubmit前BLOCKする。
5. 正規化metadataをmanifest / Ledger order record / auditにredacted保存する。
6. `RuntimeV2SubmitResult` またはmanifestに、redacted response classificationを保持する。
7. 追加Submitは、PendingがCONSUMEDのため新しいMorning/Approval/Pendingで行う。

## Acceptance

| Criteria | Result |
| --- | --- |
| 実際に送信したRuntime SubmitCommandを整理 | PASS |
| SubmitCommandからAdapterで値が変化していないか確認 | PASS |
| Broker Request欠落/誤りを確認 | PASS |
| D15成功時と比較 | PASS |
| Broker Response Reject理由取得可否を確認 | PASS |
| Response Normalizer誤分類可能性を確認 | PASS |
| コード形式差分を確認 | PASS |
| Broker API仕様との差分を確認 | PASS |
| 各段階比較表を作成 | PASS |
| 追加Submitなし | PASS |
| Broker API Writeなし | PASS |
| Notification送信なし | PASS |
| launchd変更なし | PASS |

## Final

E17 Rejectは「DemoだからReject」ではない。

根本原因は、Runtime v2 Submit pathで既存のBroker issue code normalizationが接続されておらず、Tachibana `CLMKabuNewOrder` の `sIssueCode` にJ-Quants/internal 5桁コードをそのまま送ったことである。
