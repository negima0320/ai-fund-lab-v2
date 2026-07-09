# Phase14-D9 Execution Evidence Source Review for Demo Filled BUY

作成日: 2026-07-07

## Status

```text
PHASE14D9_EXECUTION_EVIDENCE_POLICY_READY
```

Phase14-D9では、ReadOnly再取得と既存証跡調査のみを行った。追加Demo Submit、BUY再Submit、SELL Submit、Cancel API、訂正API、Production注文、本番Broker API Write、実資金運用、Notification実送信、launchd / plist変更、AI再学習、Backtest / Simulationは行っていない。

## 1. 目的

Phase14-D8で `7203 BUY 100` は Runtime v2 pure submit path から Demo Submit され、Broker response は `ACCEPTED` だった。

Broker order list では以下を確認した。

```text
issue_code=7203
side=buy
quantity=100
status=全部約定
executed_quantity=100
remaining_quantity=0
```

一方、`CLMOrderListDetail` による約定詳細取得は `FAILED_BROKER_READONLY_FETCH` となり、Execution detail evidence を取得できなかった。

本資料では、Runtime v2で Ledger / Asset へ進むための Execution evidence policy を定義する。

## 2. ReadOnly Recheck Result

D9でReadOnly再取得を実行した。

Artifacts:

- `reports/phase_reports/phase14_d9_readonly_recheck.json`
- `.runtime/phase14d9/tachibana_demo_snapshot.json`

結果:

| Item | Result |
| --- | --- |
| environment | `demo` |
| production endpoint | not reached |
| orders | `PASS`, count=2 |
| account | `PASS` |
| positions | `PASS`, count=8 |
| cash / buying power | `PASS` |
| quotes | `PASS_WITH_EMPTY_RESULT` |
| executions detail | `FAIL`, count=0 |
| detail attempted | `2` |
| detail failed | `2` |
| final readonly status | `FAILED_BROKER_READONLY_FETCH` |

7203 order evidence:

```text
status=全部約定
executed_quantity=100
remaining_quantity=0
order_id_hash=order_5eda06d71a80aeed
```

9432 order evidence:

```text
status=取消完了
executed_quantity=0
remaining_quantity=0
order_id_hash=order_347b4cfc8e59e728
```

## 3. CLMOrderListDetail Failure Classification

失敗原因候補:

| Candidate | Classification | Evidence |
| --- | --- | --- |
| `sOrderNumber`に平文注文番号ではなくhash相当を渡している | likely | snapshot保存値は `order_id_hash` のみで、平文 `sOrderNumber` は保存されていない |
| Demo環境の `CLMOrderListDetail` が一部注文で使えない | possible | 9432取消注文、7203全部約定注文の両方でdetail failure |
| request payload key不備 | less likely | `TachibanaRequestBuilder.order_list_detail()` は `CLMOrderListDetail` + `sOrderNumber` を生成し、codecにも `sOrderNumber=643` がある |
| p_no sequence不整合 | possible but less likely | shared builder sequenceは使っているが、失敗は order_detail_response で result_code非0 |
| order list normalizerが平文order numberを取り出せていない | likely | order list artifactは redaction policyにより `order_id_hash` のみ保存 |

## 4. sOrderNumber / order id / p_no Mapping

整理:

- `p_no` はAPI request sequenceであり、注文番号ではない。
- `CLMOrderListDetail` のrequest keyは `sOrderNumber`。
- `sOrderNumber` はBrokerが返す平文注文番号である。
- Runtime保存証跡では、平文注文番号を保存せず `order_id_hash` にしている。
- `order_id_hash` は監査・突合用であり、`CLMOrderListDetail(sOrderNumber=...)` の入力には使えない。
- Submit responseでは `broker_order_id_hash=sha256:5eda...` が保存され、order listでは `order_id_hash=order_5eda...` が保存されているため、redacted correlationはできる。
- ただし、hashから平文 `sOrderNumber` は復元できない。

結論:

```text
CLMOrderListDetailの正規入力は平文sOrderNumber。
Runtime evidence保存はhash化で正しいが、detail retry用には短期メモリ内または暗号化一時領域のorder number handling設計が必要。
```

## 5. Execution Evidence Policy

Runtime v2では Execution evidence を3段階に分類する。

### Strong Execution Evidence

Ledger execution を通常作成してよい条件:

- `CLMOrderListDetail` などの約定明細APIから以下を取得できる。
  - execution id or execution key
  - order number reference
  - issue code
  - side
  - executed quantity
  - execution price
  - executed at
- response result code が成功。
- order list の executed_quantity と execution detail の合計数量が一致。
- raw response / secret / plaintext customer identifier は保存しない。

### Derived Execution Evidence From Order List

Order listだけで「約定扱いに近い分類」をしてよい条件:

- order status が `全部約定` または filled相当。
- executed_quantity が注文数量と一致。
- remaining_quantity が0。
- same order hash が Submit response hash と突合できる。
- positions / cash が同時刻付近で取得できる。
- `CLMOrderListDetail` が失敗していることを明示する。

ただしこの場合:

- `LedgerExecutionRecord` は通常の execution として作らない。
- `DERIVED_EXECUTION_FROM_ORDER_STATUS` として別イベントまたは review event にする。
- `review_required=True` を維持する。
- Asset更新は Position / Cash evidence を経由する。

### Insufficient Evidence

以下の場合は Execution を作らない。

- order listに executed_quantity がない。
- remaining_quantity が不明。
- order statusが未約定、受付、取消、失効、拒否、unknown。
- Submit response hashとorder list hashを突合できない。
- positions / cashが取得できない。

## 6. Positions / Cash Evidence

positions / cash は Execution detail の代替ではないが、Asset更新の正規入力である。

方針:

- Asset Current SoT は `persistent_ledger/state.json`。
- BrokerOrderのみからAssetを作らない。
- Assetは Position evidence と Cash evidence から再構築する。
- 7203のポジション数量がBroker positionsで確認できる場合、Asset positionへ反映してよい。
- cash / buying power の変化はCash evidenceとしてAssetへ反映してよい。
- ただしExecution price / execution idがない限り、Ledger executionは `REVIEW_REQUIRED` または derived event扱いにする。

今回のD9ではpositions normalizerのkey match rateが低く、7203 positionの明示抽出は未確認である。そのため、Asset反映の解除条件には positions normalizer修正または Broker position evidenceの明確化を含める。

## 7. Ledger / Asset Update Conditions

Ledger order:

- Broker order list evidenceから作成可。
- 7203は `status=全部約定`、9432は `status=取消完了` として記録可。

Ledger execution:

- Strong Execution Evidence がある場合のみ通常作成。
- Order list derived evidenceだけの場合は、通常の `LedgerExecutionRecord` ではなく `derived_fill_review_event` 相当にする。
- Review解除までは `review_required=True`。

Asset:

- BrokerOrderのみから作らない。
- Position / Cash evidenceから再構築する。
- 7203 positionが明確に取得できるまでは、BUY約定のAsset反映は `REVIEW_REQUIRED`。

## 8. REVIEW_REQUIRED解除条件

以下のいずれかが必要:

1. `CLMOrderListDetail` から7203の約定明細が取得できる。
2. 正規の別ReadOnly sourceから execution id / price / quantity / executed_at が取得できる。
3. order list derived execution を採用する設計変更を行い、manual approval付きで `DERIVED_EXECUTION_FROM_ORDER_STATUS` としてLedgerへ入れる。
4. positions / cash normalizerで7203 position / cash changeを明確に取得し、AssetはPosition/Cash evidenceから反映、Executionはderived review eventとして残す。

## 9. Required Fix / Next Steps

推奨修正:

1. `CLMOrderList` の平文 `sOrderNumber` を保存せず、process-local memory内で `CLMOrderListDetail` に渡す設計を確認する。
2. detail request payload summaryを保存する。保存するのは `sCLMID`, `p_no`, `sOrderNumber_present`, `sOrderNumber_hash` のみ。
3. detail failure reportに result_code classification を追加する。
4. order list derived execution policyをRuntime v2へ追加する。
5. positions normalizerの7203銘柄/数量/平均単価抽出を検証する。
6. D10でReadOnly-only再同期を行い、detail取得またはderived policyでLedger/Asset反映を再試験する。

## 10. Acceptance Criteria

| Criteria | Result |
| --- | --- |
| 追加Submitしていない | PASS |
| Production endpointへ到達していない | PASS |
| 7203 BUY 100のorder status evidenceを整理している | PASS |
| 約定詳細API失敗原因候補を分類している | PASS |
| sOrderNumber / order id / p_no mappingを確認している | PASS |
| positions / cash evidenceで補強できるか整理している | PASS |
| order listだけでExecution扱いしてよい条件を明記している | PASS |
| BrokerOrderのみからAssetを作らない原則を維持している | PASS |
| Ledger / Assetへ進めるためのevidence policyを明記している | PASS |
| 次に必要な修正または再同期条件を明記している | PASS |

## 11. Final Decision

```text
PHASE14D9_EXECUTION_EVIDENCE_POLICY_READY
```

D9では、7203 BUY 100のorder list上の全部約定は確認できたが、Execution detail evidenceは未取得のままである。Runtime v2は、order list derived fillを強いexecution evidenceとは区別し、Ledger execution / Asset反映は detail evidence または Position/Cash evidence policyに従って進める。
