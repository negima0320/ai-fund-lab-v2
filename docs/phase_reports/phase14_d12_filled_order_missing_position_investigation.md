# Phase14-D12 Filled Order Missing Position Investigation

作成日: 2026-07-07

## Status

```text
PHASE14D12_MISSING_POSITION_ROOT_CAUSE_IDENTIFIED
```

Phase14-D12では、既存7203 BUY 100のReadOnly再取得とPosition evidence調査のみを行った。追加Demo Submit、BUY再Submit、SELL Submit、Cancel API、訂正API、Production注文、本番Broker API Write、実資金運用、Notification実送信、launchd / plist変更は行っていない。

## 1. 目的

Phase14-D11では、7203 BUY 100がOrderList上で全部約定である一方、Position evidenceに7203保有が確認できず、D10 policy上のExecution-equivalent反映を保留した。

D12では、この状態が以下のどれに近いかを切り分ける。

- デモ環境の反映遅延
- Position取得条件の問題
- 銘柄コード正規化の問題
- Runtime normalizerの問題
- 現物 / 信用 / 口座区分の取得先違い

## 2. ReadOnly Recheck

D12で立花証券デモ環境のReadOnly再取得を行った。

Artifacts:

- `.runtime/phase14d12/tachibana_demo_snapshot.json`
- `reports/phase_reports/phase14_d12_missing_position_readonly_recheck.json`
- `reports/phase_reports/positions_safe_diagnosis.json`

結果:

| Item | Result |
| --- | --- |
| environment | `demo` |
| production endpoint | not reached |
| orders | `PASS`, count=2 |
| positions | `PASS`, count=8 |
| account | `PASS` |
| cash / buying power | `PASS` |
| executions detail | `FAIL`, count=0 |
| final readonly status | `FAILED_BROKER_READONLY_FETCH` |

全体statusは約定詳細API失敗により `FAILED_BROKER_READONLY_FETCH` だが、D12の主対象であるOrderList / Position / Cashは取得できている。

## 3. OrderList Evidence

7203 BUY 100はOrderList上で以下の状態だった。

```text
issue_code=7203
side=buy
quantity=100
status=全部約定
executed_quantity=100
remaining_quantity=0
raw_clmid=CLMOrderList
```

9432 BUY 100は引き続き取消完了だった。

```text
issue_code=9432
status=取消完了
executed_quantity=0
remaining_quantity=0
```

## 4. Position Evidence

`CLMGenbutuKabuList` と `CLMShinyouTategyokuList` はどちらもレスポンス行を返している。

```text
cash positions row_count=4
margin positions row_count=4
combined row_count=8
```

しかし、safe diagnosisでは候補キー一致が全て0だった。

```text
combined.candidate_key_match_rate.issue_code = 0/8
combined.candidate_key_match_rate.quantity = 0/8
combined.candidate_key_match_rate.market_value = 0/8
combined.candidate_key_match_rate.price = 0/8
```

保存済みsnapshot上のPositionは、全行が以下のような形に正規化されている。

```text
account_type=cash or margin
issue_code=""
quantity=0
available_quantity=0
average_price=0
market_value=0
raw_clmid=CLMGenbutuKabuList or CLMShinyouTategyokuList
```

## 5. 銘柄コード表現の確認

調査対象の候補:

| Candidate | Result |
| --- | --- |
| `7203` | OrderListには存在、Positionには存在せず |
| `72030` | Position artifact内に存在せず |
| `7203.T` | Position artifact内に存在せず |
| 市場区分付き表現 | 保存済みPosition artifactには確認できず |

D12 snapshotでは、Position normalizerに渡された保存結果に7203相当の銘柄コードがない。したがって、現時点では銘柄コード表記ゆれだけでは説明できない。

## 6. 現物 / 信用 / 口座区分

取得先:

- 現物: `CLMGenbutuKabuList`, `account_type=cash`, row_count=4
- 信用: `CLMShinyouTategyokuList`, `account_type=margin`, row_count=4

7203 BUYは現物BUYとして扱っているため、通常は `CLMGenbutuKabuList` 側にPosition evidenceが出ることを期待する。ただしD12では現物側4行すべてが `issue_code="" quantity=0` で、7203を確認できない。

信用側にも7203は確認できない。

## 7. Normalizer / Mapping切り分け

`src/ai_fund_lab_v2/broker/normalizer.py` のPosition normalizerは、以下のsemantic keyを読む。

```text
issue_code: issue_code, sIssueCode, sMeigaraCode
quantity: quantity, sQuantity, sZanKabuSuu
market_value: market_value, sMarketValue, sHyokaGaku, sHyoukaGaku
price: price, average_price, market_price, sPrice, sAveragePrice, sBokaTanka, sHeikinTanka, sMarketPrice, sGenzaine, sGenzaichi
```

一方、D12のsafe diagnosisで確認できるPosition row keyは、現物では主に数値キーだった。

```text
579, 772, 847, 855, 856, 857, 858, 859, 860, 861, 862, 863, 864, 865, 920, 921
```

信用でも数値キーが中心で、一部 `sOrderBaibaiKubun`, `sOrderIssueCode`, `sOrderOrderSuryou` が存在するが、現物BUYの7203保有を示すsemantic keyは保存されていない。

このため、D12時点の最有力原因は以下である。

```text
CLMGenbutuKabuList / CLMShinyouTategyokuList のデモレスポンスは行を返しているが、
Position normalizerが期待するsemantic keyへdecode / mappingできていない。
その結果、Runtime v2のPosition evidenceでは7203を確認できない。
```

## 8. 反映遅延の可能性

反映遅延は完全には排除しない。ただし、D8直後、D9、D11、D12の複数回ReadOnlyで同じくPositionに7203が出ていないため、単純な短時間遅延だけを主因とする可能性は下がっている。

一方で、デモ環境ではOrderList上の `全部約定` が、保有一覧APIで即座に銘柄別Positionとして見えることを保証しない可能性がある。したがって、D10 policyは維持し、OrderList単体またはCash変化だけでAssetへ7203 positionを作らない。

## 9. Cash / Buying Powerとの整合

D12のCash / Buying Power evidence:

```text
CLMZanKaiSummary.cash_available=17960104
CLMZanKaiSummary.buying_power=19989824
CLMZanKaiKanougaku.cash_available=19989824
CLMZanKaiKanougaku.buying_power=19989824
```

Cash / Buying Powerは取得できており、D10 policyのCash evidence条件は満たす。ただし、Position evidenceが欠けているため、OrderList-derived fillをExecution-equivalentとしてAssetへ反映する条件は満たさない。

## 10. Policy Decision

D10 policyは維持する。

- `CLMOrderListDetail` はoptional evidence。
- `CLMOrderListDetail` 失敗だけではREVIEW_REQUIREDにしない。
- ただしOrderList-derived fillは、Position / Cash evidenceが揃った場合のみExecution-equivalent。
- BrokerOrder単体からAssetを作らない。
- Position evidenceに7203が確認できない間は、Asset反映を保留する。

現在の7203 BUY 100は以下のRuntime状態として扱う。

```text
MONITORING_FILL / REVIEW_REQUIRED
```

OrderList上は全部約定だが、Asset Current SoTへ入れるにはPosition evidenceが不足している。

## 11. 次にAsset反映へ進む条件

以下のいずれかを満たすまで、7203 positionのAsset反映を保留する。

1. `CLMGenbutuKabuList` のReadOnly再同期で、7203または正規化可能な7203相当コードと数量100以上が確認できる。
2. 数値キー `579`, `855` などのPosition API field mappingを一次資料または安全な診断で確認し、semantic keyへdecodeできるようにする。
3. 管理画面上の保有表示とReadOnly APIの差異を確認し、デモ環境固有のPosition非表示仕様として運用メモ化する。
4. 別のReadOnly sourceでPosition / Cash evidenceの整合を確認できる。

## 12. Acceptance Criteria

| Criteria | Result |
| --- | --- |
| Positionに7203が出ない原因候補を分類している | PASS |
| `CLMGenbutuKabuList` の取得結果を確認している | PASS |
| 銘柄コード正規化を確認している | PASS |
| 現物 / 信用 / 口座区分を確認している | PASS |
| 反映遅延の可能性を整理している | PASS |
| Asset反映を保留する判断を維持している | PASS |
| 次に再同期すべき条件を明記している | PASS |
| 追加Submitを行っていない | PASS |

## 13. Final Decision

```text
PHASE14D12_MISSING_POSITION_ROOT_CAUSE_IDENTIFIED
```

Root cause classification:

```text
primary: position_response_mapping_gap
secondary: demo_position_reflection_delay_possible
asset_reflection: hold
runtime_state: MONITORING_FILL / REVIEW_REQUIRED
```

