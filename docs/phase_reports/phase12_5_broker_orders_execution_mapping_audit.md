# Phase12.5 Broker Orders -> Executions / Positions Mapping Audit

作成日: 2026-07-03

## 調査範囲

対象artifact:

- `.runtime/operations/broker_readonly_reports/2026-07-03/broker_readonly_snapshot_report.json`
- `.runtime/operations/broker_readonly_source/2026-07-03/tachibana_demo_snapshot.json`
- `.runtime/operations/broker_snapshot/2026-07-03/broker_snapshot.json`
- `.runtime/operations/broker_snapshot_summary/2026-07-03/broker_snapshot_summary.json`
- `.runtime/operations/broker_orders/2026-07-03/orders.json`
- `.runtime/operations/broker_executions/2026-07-03/executions.json`
- `.runtime/operations/broker_positions/2026-07-03/positions.json`
- `.runtime/operations/fill_events/2026-07-03/fill_events.json`
- `.runtime/operations/ledger/2026-07-03/ledger_state.json`
- `.runtime/operations/reconciliation_result/2026-07-03/reconciliation_result.json`

対象コード:

- `src/ai_fund_lab_v2/broker/client.py`
- `src/ai_fund_lab_v2/broker/request_builder.py`
- `src/ai_fund_lab_v2/broker/normalizer.py`
- `src/ai_fund_lab_v2/broker/tachibana_broker_snapshot.py`
- `src/ai_fund_lab_v2/operations/broker_readonly.py`
- `src/ai_fund_lab_v2/operations/ledger.py`
- `src/ai_fund_lab_v2/operations/operations.py`

今回は調査のみ。修正、Submit、Broker注文、Production接続、artifact削除、notification送信、raw request/response保存は実施していない。

## Broker APIレスポンス確認

raw responseは保存禁止設計のため、現存artifactから生レスポンスそのものは確認できない。

ただし、保存済みのsanitized snapshotでは以下を確認した。

- `broker_readonly_source/.../tachibana_demo_snapshot.json`
  - `orders`: 5件
  - `executions`: 0件
  - `positions`: 12件
  - `health.orders.status`: `PASS`
  - `health.executions.status`: `FAIL`
  - `health.positions.status`: `PASS`

ordersのsanitized snapshotには、少なくとも以下が存在する。

```json
{
  "issue_code": "6897",
  "order_id_hash": "order_...",
  "side": "3",
  "executed_quantity": "100",
  "remaining_quantity": "0",
  "status": "全部約定"
}
```

従って、銘柄コードと注文番号由来のhashはRuntime保存前に完全消失していない。raw注文番号は保存禁止のためhash化されている。

一方、市場コードは現在のnormalized order artifactには保存されていない。

## code=null原因

結論: Broker Orders artifactの正規フィールドは `issue_code` であり、`code` フィールドは出力されていない。`code=null` は、APIレスポンス欠落というより、下流/表示側が `code` を参照しているschema mismatchの可能性が高い。

確認結果:

- `.runtime/operations/broker_orders/2026-07-03/orders.json` には `issue_code` が存在する。
- 同artifactには `code` フィールドがない。
- `src/ai_fund_lab_v2/operations/broker_readonly.py` の `_normalize_order()` は `issue_code` を出力するが、`code` aliasを出力していない。
- `fill_events` ではsubmit由来の `issue_code` はあるが、`code` はない。

分類:

- APIレスポンスにcodeがない: 未確定。raw responseは保存されていないため直接確認不能。
- Parserで落としている: `normalizer.py` では `sIssueCode` / `sOrderIssueCode` / `sMeigaraCode` を `issue_code` へ変換している。
- Normalizerでnullにしている: `issue_code` は保持されているため、少なくともordersでは該当しない。
- Redactionで消している: 銘柄コードはredaction対象ではなく、`issue_code` として残っている。
- 保存時に欠落している: `code` aliasは保存していない。ここが表示上の `code=null` 原因候補。

## side=3の意味

`docs/02_architecture/tachibana_demo_order_api_design.md` では、立花の売買区分は以下。

- `sBaibaiKubun=3`: BUY
- `sBaibaiKubun=1`: SELL

従って、Broker Ordersの `side=3` はBUYを意味する。

注意点として、`src/ai_fund_lab_v2/broker/normalizer.py` の `_normalize_side()` は `{"1": "buy", "2": "sell"}` というmappingを持つが、実artifactでは `3` がそのまま残っている。現状のBUY判定はoperations側の `_has_active_same_side_broker_order()` などで `3` をBUYとして扱っている。将来SELL側ではmapping不整合が顕在化する可能性がある。

## Orders -> Executions -> Positions -> Ledger -> Reconcile

現在の流れ:

```text
CLMOrderList
  -> normalize_order_list()
  -> snapshot.orders
  -> operations/broker_orders/orders.json

CLMOrderListDetail(first order only)
  -> normalize_order_detail_executions()
  -> snapshot.executions
  -> operations/broker_executions/executions.json

CLMGenbutuKabuList / CLMShinyouTategyokuList
  -> normalize_cash_positions() / normalize_margin_positions()
  -> snapshot.positions
  -> operations/broker_positions/positions.json

operations broker artifacts
  -> operations ledger
  -> reconcile
```

止まっている箇所:

- Executions: `tachibana_broker_snapshot.py` はordersがある場合、先頭1件の `get_executions_history(orders[0].order_id)` だけを呼ぶ。今回 `health.executions.status=FAIL` で、`executions=[]` になっている。
- Positions: ReadOnly source snapshotにはpositions 12件があるが、全件 `issue_code=""` / `quantity=0` / `market_value=0` の空行。operations writerが `issue_code`あり、かつ `quantity > 0` のみ残すため、broker_positionsは0件になる。
- Ledger: `operations/ledger.py` はbroker_positionsとbroker_executionsをそのまま集計するため、positions_count=0、executions_count=0になる。
- Reconcile: broker_ordersは5件あるが、broker_executions=0、broker_positions=0のため `REVIEW_REQUIRED`。

## Executions生成

Broker Ordersには以下がある。

- `status="全部約定"`
- `executed_quantity="100"`
- `remaining_quantity="0"`

しかし現在のRuntimeでは、Broker OrdersからBroker Executions artifactを合成していない。

現在のexecutions生成は `CLMOrderListDetail` のresponseに依存している。さらに、現実装は5注文すべてではなく先頭1注文のdetailのみを呼んでいる。

今回のsource snapshotでは:

- `orders_count=5`
- `executions_count=0`
- `health.executions.status=FAIL`

したがって、Orders上は全部約定を示しているが、Executions API/detail側が失敗し、executions artifactに反映されていない。

## Positions生成

Broker ReadOnly source snapshotではpositions API自体は `PASS` で、source_countは12件。

ただし中身は以下のような空/ゼロ行だった。

```json
{
  "issue_code": "",
  "quantity": "0",
  "market_value": "0",
  "account_type": "cash"
}
```

operations writerでは以下条件でフィルタしている。

```text
issue_code exists AND quantity > 0
```

そのため、broker_positionsは0件になる。

これは「writerが有効な空ポジションを落としている」点だけ見れば正常仕様。ただし、Web画面で5件全部約定後に保有があるはずなら、positions APIの反映遅延、Demo固有の反映仕様、またはpositions normalizerのkey mapping不足を疑う必要がある。現存artifactだけではraw response keysが保存されていないため、APIが本当に空を返したのか、normalizerが未知keyを拾えずゼロ化したのかは確定できない。

## Reconcileへの影響

`.runtime/operations/reconciliation_result/2026-07-03/reconciliation_result.json` では:

- `broker_order_count=5`
- `broker_orders_cover_accepted=true`
- `broker_orders_used_as_execution_fallback=true`
- `broker_executions_count=0`
- `broker_positions_count=0`
- `classification=REVIEW_REQUIRED`

さらにDaily Report側のReview logicでは、accepted fill eventがあるのにbroker_executions_count=0の場合:

```text
fill_events_accepted_without_broker_executions
```

をReview理由にする設計。

つまり、Broker Ordersだけではaccepted/filledらしさを補助的に示せるが、RuntimeのSource of Truthとしてはexecutions/positionsの欠落を隠さずReviewにしている。

## Runtime設計上、OrdersだけでExecutions/Positions生成は可能か

技術的には一部可能。

Broker Ordersの `status="全部約定"`、`executed_quantity=100`、`remaining_quantity=0`、`price`、`order_datetime` から、synthetic execution相当のイベントを作ることはできる。

ただし、現在設計では:

- broker_executionsはBroker Executions / Order Detail API優先
- broker_positionsはBroker Positions API優先
- broker_orders fallbackはReconcile上でReview理由付き

という扱い。Ordersだけでpositionsを確定するには、買い/売り、約定単価、約定日時、同一注文照合、既存保有との合算、売却時のlot処理などが必要で、Broker Positions APIの代替として無条件採用するのは危険。

Phase12.5のProduction Equivalent方針では、Orders fallbackは「Review付き補完」に留めるのが妥当。

## Root Cause

Root Causeは複合。

### API仕様 / API挙動

- `CLMOrderList` は全部約定・約定数量を返している。
- `CLMOrderListDetail` は今回 `FAIL` になり、executionsを返せていない。
- positions APIは `PASS` だが、normalized結果は空/ゼロ行のみ。

### Runtime parser / normalizer

- Orders normalizerは `issue_code` を保持しているが、`code` aliasを出さない。
- Executions normalizerはOrder Detail responseに依存している。
- Positions normalizerは保存済みsnapshot上では空/ゼロ行を生成しており、raw keys不明のためkey mapping不足の可能性が残る。
- `_normalize_side()` の `1/2` mappingは立花設計書の `1=SELL, 3=BUY` とズレがある。

### Mapping

- `code` vs `issue_code` のschema不一致が、`code=null` 表示の主因候補。
- internal codeは5桁、broker issue codeは4桁であり、Submit / Broker Orders / Reportの照合では `broker_issue_code` / `issue_code` のどちらを見るかを統一する必要がある。

### Reconcile設計

- ReconcileはBroker Orders fallbackを認識するが、Executions/Positionsが0件ならReviewにする。
- これは現状、実態を隠さない安全側の挙動。

## 修正案（未実装）

1. `broker_orders` artifactに `code` aliasを追加するか、Report/Reconcile側を `issue_code` 正規に統一する。
2. `CLMOrderListDetail` を全注文に対して呼ぶ。現状の先頭1注文のみdetail取得を修正する。
3. Order Detail失敗時に、`order_id_hash` / `issue_code` / `status` / `executed_quantity` / `remaining_quantity` を用いた `ORDER_STATUS_FILLED_FALLBACK_REVIEW` を明示分類する。
4. Broker Ordersからsynthetic executionsを作る場合は、`source=broker_orders_fallback`、`review_required=true`、`broker_executions_api_failed=true` を必須にする。
5. Positions APIのsafe key diagnosisを追加し、raw responseを保存せずに「どの候補keyが存在したか」だけを記録する。
6. `_normalize_side()` を立花仕様に合わせ、`1=SELL`, `3=BUY` に修正する。
7. Positionsが0件でもOrders全部約定がある場合、Daily Report / Reconcileで「Broker Orders上は全部約定、Broker Positions未反映」と明示する。

## 今回修正していないこと

- 実装変更なし
- Submit実行なし
- Broker注文なし
- Production接続なし
- Production注文なし
- artifact削除なし
- notification送信なし
- secret出力なし
- raw request保存なし
- raw response保存なし
