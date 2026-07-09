# Phase14-D16 BUY/SELL Demo E2E Acceptance Summary

作成日: 2026-07-07

最終判定: **PHASE14D16_BUY_SELL_E2E_ACCEPTED**

## 1. 目的

Phase14-D16は、Phase14-D〜D15で実施したRuntime v2 pure submit pathのDemo BUY / SELL検証を整理し、Demo環境におけるE2E Acceptanceの到達点、残課題、次フェーズ条件を明確化する。

Phase14-D系では、初回Demo BUY smokeから始まり、旧Runtime混入の監査、Runtime v2 pure submit pathの再設計、7203 BUY、Execution Evidence Policyの見直し、Position mapping修正、BUY reflection再評価、7203 SELLまでを段階的に検証した。

Production注文、本番Broker API Write、実資金運用、Notification実送信、launchd / plist変更は行っていない。

## 2. 時系列 Summary

| Phase | 判定 | 要点 |
| --- | --- | --- |
| Phase14-D | `PHASE14D_REVIEW_REQUIRED` | Demo BUY accepted smokeとしては成立。ただし後続監査で旧Runtime submit authority混入が疑われ、Runtime v2 pure acceptanceとしては無効化対象となった。 |
| Phase14-D2 | `PHASE14D2_LEGACY_PATH_FOUND_REDESIGN_REQUIRED` | `scripts/run_phase14d_demo_buy_guarded.py` / `broker/demo_order.py` が旧 `OrderCommand` / `RuntimeMode` を参照。Submit sourceはPendingのみだったが、pure Runtime v2 submit pathではなかった。 |
| Phase14-D3 | `PHASE14D3_PURE_SUBMIT_PATH_READY` | `RuntimeV2SubmitCommand`、Runtime v2 submit guards、adapter boundaryを設計・実装。旧Runtimeをsubmit authorityにしない方針を確立。 |
| Phase14-D4 | `PHASE14D4_DEMO_SUBMIT_ADAPTER_READY` | `RuntimeV2SubmitCommand`を直接受け取るTachibana Demo Submit Adapterを追加。dry-run / preflight、demo-only、production endpoint block、9000番台除外を確認。 |
| Phase14-D5 | `PHASE14D5_REVIEW_REQUIRED` | 9432が9000番台でデモ約定対象外となり、未約定状態が残った。次のBUY再試験前に整理が必要になった。 |
| Phase14-D6 | `PHASE14D6_ORDER_RESOLUTION_PLAN_COMPLETE` | 9432 BUY 100の未解決状態を整理。Pendingはidempotency上CONSUMED可、Broker lifecycleは別管理、Cancelは人手またはguard設計後とした。 |
| Phase14-D7 | `PHASE14D7_BROKER_STATE_SYNC_PASS` | 立花証券デモ画面で人手取消された9432をBroker ReadOnly同期。PendingはCONSUMED、Asset変化なし、Reconcile PASS。 |
| Phase14-D8 | `PHASE14D8_REVIEW_REQUIRED` | Runtime v2 pure submit pathで7203 BUY 100をDemo SubmitしACCEPTED。OrderListでは全部約定だが、CLMOrderListDetail取得失敗により当時はREVIEW_REQUIRED。 |
| Phase14-D9 | `PHASE14D9_EXECUTION_EVIDENCE_POLICY_READY` | CLMOrderListDetailの入力・取得条件を調査。Detail APIをRuntime v2必須Evidenceにしない方向を整理。 |
| Phase14-D10 | `PHASE14D10_EXECUTION_EVIDENCE_POLICY_COMPLETE` | CLMOrderListDetailをoptional evidence化。正規EvidenceをCLMOrderList / CLMGenbutuKabuList / CLMZanKaiSummary / CLMZanKaiKanougakuに再定義。 |
| Phase14-D11 | `PHASE14D11_REVIEW_REQUIRED` | D10 policyで7203 BUY reflectionを再評価したが、Positionに7203が出ず、Position evidence不足でREVIEW_REQUIRED。 |
| Phase14-D12 | `PHASE14D12_MISSING_POSITION_ROOT_CAUSE_IDENTIFIED` | Position APIは行を返しているがRuntime normalizerがdecodeできていないことを確認。主因はposition_response_mapping_gap。 |
| Phase14-D13 | `PHASE14D13_POSITION_MAPPING_FIX_COMPLETE` | Position response mappingを修正。7203 `quantity=100` / `available_quantity=100` をRuntime v2 Position evidenceとして取得。D11相当BUY reflectionがPASS。 |
| Phase14-D14 | `PHASE14D14_SELL_PREFLIGHT_COMPLETE` | 7203 SELL 100のpreflightを実施。SELL quantity guard、available_quantity guard、Approval、Duplicate、Pending-onlyを確認。SELL Submitは未実行。 |
| Phase14-D15 | `PHASE14D15_DEMO_SELL_SINGLE_ORDER_PASS` | Runtime v2 pure submit pathで7203 SELL 100をDemo Submit。OrderList + Position + Cash evidenceでSELL reflection、Reconcile / Audit PASS。 |

## 3. 旧Runtime混入問題と解消

Phase14-D2監査で、Phase14-D初回BUY smokeはDemo注文としてはacceptedだったが、以下の旧Runtime由来参照が確認された。

- `ai_fund_lab_v2.runtime.order_command.OrderCommand`
- `RuntimeMode`
- `TachibanaDemoOrderAdapter.submit_cash_stock_order(OrderCommand)`

このためPhase14-Dは「Demo BUY accepted smoke」として部分有効、「Runtime v2 pure submit acceptance」としては無効または再評価対象とした。

Phase14-D3/D4で以下を追加・整理し、旧Runtime submit authorityを排除した。

- Runtime v2-native `RuntimeV2SubmitCommand`
- Runtime v2 submit guards
- `pending_order_plan/pending_order_plan.json` only source
- Approval guard
- Duplicate submit guard
- demo-only / production endpoint block
- `RuntimeV2TachibanaDemoSubmitAdapter`
- `TachibanaCashStockOrderRequest.from_runtime_v2_submit_command`

D8以降のBUY再試験とD15 SELLは、旧 `OrderCommand` / `RuntimeMode` をsubmit authorityとして使っていない。

## 4. 9432 9000番台銘柄ミスと外部取消同期

Phase14-D/D5で使われた9432は9000番台銘柄で、デモ約定対象外として未約定 `remaining_quantity=100` が残った。

Phase14-D6ではこの注文をRuntimeの未解決Broker orderとして整理し、Pendingは再Submit防止のためCONSUMED扱い可能、Asset反映はPosition / Cash evidenceが必要とした。

Phase14-D7では、立花証券デモ画面で人手取消された9432をBroker ReadOnly同期し、以下を確認した。

- Broker側取消済みをSource of Truthとして検知。
- RuntimeはBroker状態を書き換えない。
- PendingはCONSUMED。
- Assetは変化なし。
- Reconcile PASS。
- Audit findings 0。
- Cancel APIは使っていない。

これにより、7203でのBUY再試験へ進める状態になった。

## 5. 7203 BUY Acceptance

Phase14-D8で、Runtime v2 pure submit pathにより7203 BUY 100をDemo Submitした。

確認結果:

- `environment=demo`
- `base_url_is_demo=True`
- `base_url_is_production=False`
- `RuntimeV2SubmitCommand`を直接使用
- 旧 `OrderCommand` / `RuntimeMode` submit authority未使用
- Submit sourceは`pending_order_plan/pending_order_plan.json`
- Approval guard PASS
- Duplicate guard PASS
- Demo Broker response: `ACCEPTED`
- BrokerOrder Status: 7203 BUY 100 `全部約定`
- `executed_quantity=100`
- `remaining_quantity=0`

D8時点ではCLMOrderListDetail取得失敗のためREVIEW_REQUIREDだったが、後続のD10/D13によりEvidence policyとPosition mappingが修正され、D11相当BUY reflectionはPASSへ昇格した。

## 6. Execution Evidence Policy

Phase14-D9/D10で、CLMOrderListDetailをRuntime v2必須Evidenceから外した。

設計判断:

- CLMOrderListDetailはoptional evidence。
- CLMOrderListDetail取得失敗だけではREVIEW_REQUIREDにしない。
- Runtime v2の正規Evidenceは以下:
  - CLMOrderList
  - CLMGenbutuKabuList
  - CLMZanKaiSummary
  - CLMZanKaiKanougaku
- BrokerOrder単体からAssetを作らない。
- OrderList-derived fillはPosition / Cash evidenceとセットの場合のみExecution-equivalent evidenceとして扱う。
- Detailがない場合はReportに`detail_optional_missing`を注記できる。

この設計により、立花証券デモ環境のDetail API制約にRuntime v2が過剰依存しない形になった。

## 7. Position Mapping GapとD13修正

Phase14-D12で、7203 BUY 100はOrderList上で全部約定していたが、Position evidenceに7203が出ていなかった。

原因:

- Broker Position APIは行を返していた。
- Runtime normalizerがTachibana Position response keyをdecodeできず、`issue_code="" quantity=0` に落としていた。
- 主因は `position_response_mapping_gap`。

Phase14-D13で以下を修正した。

| Runtime field | 追加/確認したkey |
| --- | --- |
| issue_code | `sOrderIssueCode`, `860` |
| quantity | `sOrderOrderSuryou`, `sOrderSuryou`, `864` |
| available_quantity | `sOrderCurrentSuryou`, `861` |
| average_price | `855` |
| market_price | `859` |
| market_value | `858` |
| unrealized_pnl | `856` |

D13 recheck結果:

- 7203 Position evidence found。
- `quantity=100`
- `available_quantity=100`
- D11相当BUY reflection PASS。
- `ORDER_LIST_DERIVED_FULL_FILL`
- execution_equivalent true。
- Asset contains target position。
- Reconcile PASS。
- Audit PASS。

## 8. 7203 SELL Acceptance

Phase14-D14でSELL preflightを実施し、Phase14-D15で7203 SELL 100をRuntime v2 pure submit pathからDemo Submitした。

D15結果:

| Item | Value |
| --- | --- |
| final_decision | `PHASE14D15_DEMO_SELL_SINGLE_ORDER_PASS` |
| issue_code | `7203` |
| side | `SELL` |
| quantity | `100` |
| account_type | `cash` |
| before_position_quantity | `100` |
| before_available_quantity | `100` |
| submit_status | `ACCEPTED` |
| target_order_status | `filled` |
| target_order_filled_quantity | `100` |
| target_order_remaining_quantity | `0` |
| after_position_quantity | `0` |
| cash_before | `19989824` |
| cash_after | `19999648` |
| buying_power_before | `19989824` |
| buying_power_after | `19999648` |
| reconcile_pass | `true` |
| audit_pass | `true` |

SELL reflectionは、BrokerOrder単体ではなく、OrderList + Position + Cash / Buying Power evidenceにより成立した。

## 9. Acceptance到達点

Phase14-D系で以下が成立した。

- Runtime v2 pure submit pathからDemo BUYを送信できる。
- Runtime v2 pure submit pathからDemo SELLを送信できる。
- Pending-only Submitを維持している。
- Approval必須を維持している。
- Duplicate guardを維持している。
- Demo-only guardを維持している。
- Production endpoint blockを維持している。
- 旧Runtime Submit authorityを使わない。
- 9000番台銘柄はデモ約定テスト対象から除外する。
- BrokerOrder単体からAssetを作らない。
- OrderList + Position + Cash evidenceでLedger / Assetへ進める。
- BUY後の7203 Position 100をRuntime v2で認識できる。
- SELL後に7203 Position 100→0をRuntime v2で認識できる。
- SELL後にCash / Buying Power更新をRuntime v2で認識できる。
- Reconcile PASS。
- Audit PASS。
- NotificationはPayload生成のみ。
- launchd / plist未変更。
- Production注文なし。
- 本番Broker API Writeなし。

## 10. 残課題

Phase14-D系はDemo BUY/SELL E2EとしてAcceptanceできるが、次の課題は残る。

- CLMOrderListDetailはoptional化済みだが、Detail APIの正規取得条件とUI照合運用は継続整理が必要。
- D15のReadOnly全体ステータスは`FAILED_BROKER_READONLY_FETCH`で、orders / positions / account healthはPASS。Detail系失敗を含む全体ステータスの表現改善余地がある。
- SELLのrealized PnLは、取得または算出できる場合にLedger / Reportへ反映する設計の追加が必要。
- Persistent duplicate guardを、長期運用のCurrent / History成果物とさらに統合する余地がある。
- Multi-day manual operation rehearsalでは、翌営業日以降のOrderList / Position / Cash反映差分を継続確認する必要がある。
- Production readiness前に、Production endpoint / credential / write pathが物理的にBLOCKされることを再監査する必要がある。

## 11. 次フェーズ条件

次フェーズへ進む条件:

- D15 SELL後のDemo口座状態をfresh ReadOnlyで再確認する。
- 7203 Positionが0または消滅していることを確認する。
- Cash / Buying PowerがD15 SELL後状態で安定していることを確認する。
- PendingはCONSUMEDまたは適切な終端状態であることを確認する。
- No open duplicate ordersを確認する。
- Notification実送信はまだ禁止のまま維持する。
- launchd / plist再開はまだ禁止のまま維持する。
- Production注文、本番Broker API Write、実資金運用は禁止のまま維持する。
- 次に実行する場合は、Single-order guarded test単位でApproval / Pending / Duplicate guardを再確認する。

## 12. Final Decision

Phase14-D〜D15のRuntime v2 pure submit pathによるDemo BUY / SELL E2Eは、Demo環境に限定したAcceptanceとして成立した。

```text
PHASE14D16_BUY_SELL_E2E_ACCEPTED
```
