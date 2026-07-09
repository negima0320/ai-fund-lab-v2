# Phase14-D10 OrderList / Position / Cash Based Execution Evidence Policy

作成日: 2026-07-07

## Status

```text
PHASE14D10_EXECUTION_EVIDENCE_POLICY_COMPLETE
```

Phase14-D10では、設計見直し、Runtime v2の最小実装修正、軽量テスト、JSONレポート作成のみを行った。追加Demo Submit、BUY再Submit、SELL Submit、Cancel API、訂正API、Production注文、本番Broker API Write、実資金運用、Notification実送信、launchd / plist変更、AI再学習、Backtest / Simulationは行っていない。

## 1. 目的

Phase14-D8で Runtime v2 pure submit path による `7203 BUY 100` はDemo Submit成功となり、Broker order listでは以下を確認した。

```text
status=全部約定
executed_quantity=100
remaining_quantity=0
```

一方、Phase14-D9で確認したとおり、`CLMOrderListDetail` の正規入力は平文 `sOrderNumber` であり、保存済みの `order_id_hash` や `p_no` ではない。そのため、`CLMOrderListDetail` をRuntime v2の必須Evidenceにすると、order list上は全部約定であってもLedger / Assetへ進めない。

D10では、`CLMOrderListDetail` をoptional evidenceへ格下げし、Runtime v2の正規Evidenceを以下に再定義する。

- `CLMOrderList`
- `CLMGenbutuKabuList`
- `CLMZanKaiSummary`
- `CLMZanKaiKanougaku`

## 2. Evidence Policy

### 2.1 Optional Evidence

`CLMOrderListDetail` はoptional evidenceとする。取得できた場合はStrong Execution Evidenceとして扱えるが、取得失敗だけでは `REVIEW_REQUIRED` にしない。

ただし、約定明細がない場合は、Report / Auditに `detail_optional_missing` を残す。立花証券管理画面で約定明細を確認できることは運用メモとして扱い、Runtime v2のCurrent SoTにはしない。

### 2.2 OrderList Full Fill 条件

`CLMOrderList` 由来のfillは、以下を満たす場合に「全部約定候補」として扱う。

- order statusが `全部約定` またはfilled相当
- `executed_quantity > 0`
- `executed_quantity == ordered_quantity`
- `remaining_quantity == 0`
- Submit response / pending itemとorder ref hashで突合できる

OrderList単体ではAssetを作らない。BrokerOrderのみからAssetを作らない原則を維持する。

### 2.3 Execution-equivalent 条件

OrderList-derived fillは、以下のすべてが揃った場合のみExecution-equivalent evidenceとする。

- `CLMOrderList` が全部約定を示す
- `CLMGenbutuKabuList` で対象銘柄のPosition evidenceを確認できる
- `CLMZanKaiSummary` または `CLMZanKaiKanougaku` でCash / Buying Power evidenceを確認できる

この条件を満たす場合、Runtime v2は `ORDER_LIST_DERIVED_FULL_FILL` と分類し、Ledger / Assetへ進めてよい。`CLMOrderListDetail` が欠落している場合は、`detail_optional_missing=True` としてReportへ注記する。

### 2.4 BUY / SELLでの扱い

BUYでは、Position evidenceとして対象銘柄の保有数量が約定数量以上であることを確認する。Cash / Buying Power evidenceは、資金状態の正規ReadOnly evidenceとして扱う。

SELLでは、Broker Positionを正とし、保有数量超過SELLはBLOCKEDとする。SELL約定後のPosition減少、全数量SELLでのPosition消滅、Cash / Buying Power更新、取得または算出可能なrealized PnLをLedger / Reportへ反映する。SELLでもOrderList-derived fillはPosition / Cash evidenceとセットの場合のみExecution-equivalent evidenceとする。

## 3. Runtime v2 Implementation

D10で追加した最小実装:

- `FillClassificationType.ORDER_LIST_DERIVED_FULL_FILL`
- `OrderListPositionCashEvidencePolicyResult`
- `classify_orderlist_position_cash_fill()`
- Reportのreview summaryに `detail_optional_missing` などのevent labelを表示する処理

既存の `classify_fill()` は変更せず、従来どおりExecution detailがないfilled orderは保守的に `REVIEW_REQUIRED` とする。D10 policyは、新しい明示関数 `classify_orderlist_position_cash_fill()` を通る場合にのみ適用する。

## 4. Ledger / Asset Reflection Policy

Ledgerへ進める条件:

- Strong Execution Evidenceがある場合は通常Executionとして扱う。
- `CLMOrderListDetail` がなくても、OrderList / Position / Cash evidenceが整合する場合は `ORDER_LIST_DERIVED_FULL_FILL` としてLedger execution-equivalentに進めてよい。
- detailがない場合は `detail_optional_missing` をReport / Auditに残す。

Assetへ進める条件:

- BrokerOrder単体からAssetを作らない。
- Position evidenceとCash / Buying Power evidenceからAsset Currentを構成する。
- `persistent_ledger/state.json` をAsset Current SoTとする。
- BrokerOrderはAsset SoTではなく、OrderListはfill判定の一部Evidenceとしてのみ扱う。

## 5. Report / Audit Policy

`CLMOrderListDetail` が取得できないが、OrderList / Position / Cash evidenceで整合する場合:

- Runtimeは `REVIEW_REQUIRED` へ止めない。
- Reportに `detail_optional_missing` を注記する。
- Auditには、使用Evidence sourceとして `CLMOrderList`, `CLMGenbutuKabuList`, `CLMZanKaiSummary`, `CLMZanKaiKanougaku` を残す。
- 管理画面で詳細明細を確認可能であることを運用メモに残す。

## 6. Prohibited Actions Confirmation

| Action | Result |
| --- | --- |
| 追加Demo Submit | NOT_EXECUTED |
| BUY再Submit | NOT_EXECUTED |
| SELL Submit | NOT_EXECUTED |
| Cancel API | NOT_EXECUTED |
| 訂正API | NOT_EXECUTED |
| Production注文 | NOT_EXECUTED |
| 本番Broker API Write | NOT_EXECUTED |
| 実資金運用 | NOT_EXECUTED |
| Notification実送信 | NOT_EXECUTED |
| launchd / plist変更 | NOT_EXECUTED |
| AI再学習 | NOT_EXECUTED |
| Backtest / Simulation | NOT_EXECUTED |

## 7. Verification

実行した軽量テスト:

```text
PYTHONPATH=src:. PYTHONPYCACHEPREFIX=.runtime/pycache_phase14d10 python3 -m pytest tests/runtime_v2/test_phase14d10_orderlist_position_cash_execution_policy.py -q
3 passed

PYTHONPATH=src:. PYTHONPYCACHEPREFIX=.runtime/pycache_phase14d10 python3 -m pytest tests/runtime_v2 -q
271 passed
```

Broker APIへの追加呼び出しは行っていない。D10はD8/D9で取得済みの7203 evidenceと設計判断に基づくpolicy更新である。

## 8. Acceptance Criteria

| Criteria | Result |
| --- | --- |
| `CLMOrderListDetail`を必須Evidenceにしていない | PASS |
| `CLMOrderListDetail`取得失敗だけでは`REVIEW_REQUIRED`にしない | PASS |
| OrderList / Position / Cash / Buying Powerを正規Evidenceとして扱う | PASS |
| OrderList上の全部約定を認識できる | PASS |
| Position evidenceで保有増加を確認できる | PASS |
| Cash / Buying Power evidenceで資金変化を確認できる | PASS |
| BrokerOrder単体からAssetを作っていない | PASS |
| OrderList-derived fillはPosition / Cash evidenceとセットの場合のみExecution-equivalent evidenceになる | PASS |
| Ledger / Assetへ進める条件が明記されている | PASS |
| Reportに`detail_optional_missing`を注記できる | PASS |
| 追加Submit / SELL / Cancel APIを実行していない | PASS |
| Production endpointへ到達していない | PASS |

## 9. Phase14-D11以降への引き継ぎ

次に7203のReadOnly再同期を行う場合は、追加Submitではなく、OrderList / Position / Cash / Buying PowerのReadOnly evidenceだけで `ORDER_LIST_DERIVED_FULL_FILL` を確認する。Ledger / Asset反映は、BrokerOrder単体ではなくPosition / Cash evidenceから行う。

## 10. Final Decision

```text
PHASE14D10_EXECUTION_EVIDENCE_POLICY_COMPLETE
```

