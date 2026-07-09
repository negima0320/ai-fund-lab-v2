# Phase14-D13 Tachibana Position Response Mapping Fix

作成日: 2026-07-07

## Status

```text
PHASE14D13_POSITION_MAPPING_FIX_COMPLETE
```

Phase14-D13では、Position API mapping調査、normalizer修正、軽量テスト、7203既存保有のReadOnly再取得、D11相当のRuntime反映再評価を行った。追加Demo Submit、BUY再Submit、SELL Submit、Cancel API、訂正API、Production注文、本番Broker API Write、実資金運用、Notification実送信、launchd / plist変更、AI再学習、Backtest / Simulationは行っていない。

## 1. 背景

Phase14-D12では、7203 BUY 100がOrderList上で全部約定済みである一方、Position evidenceは全行 `issue_code="" quantity=0` となっていた。

D12時点の主因分類:

```text
position_response_mapping_gap
```

つまり、Broker Position APIは行を返しているが、Runtime normalizerが7203保有としてdecodeできていなかった。

## 2. Root Cause

D13のReadOnly診断で、`CLMGenbutuKabuList` の現物Position rowはsemantic keyではなく数値keyで返ることを確認した。

7203 cash position row:

```text
860 = 7203
864 = 100
861 = 100
855 = 102.0000
859 = 2941.0000
858 = 294100
856 = 283900
```

また、信用側 `CLMShinyouTategyokuList` には以下のsemantic keyが存在していたが、D12時点のPosition normalizer / safe diagnosis候補には含まれていなかった。

```text
sOrderIssueCode
sOrderOrderSuryou
sOrderBaibaiKubun
```

## 3. Mapping Fix

`src/ai_fund_lab_v2/broker/normalizer.py` を修正し、Position normalizerが以下を読めるようにした。

| Runtime field | Added keys |
| --- | --- |
| issue_code | `sOrderIssueCode`, `860` |
| quantity | `sOrderOrderSuryou`, `sOrderSuryou`, `864` |
| available_quantity | `sOrderCurrentSuryou`, `861` |
| average_price | `855` |
| market_price | `859` |
| market_value | `858` |
| unrealized_pnl | `856` |

`src/ai_fund_lab_v2/broker/tachibana_broker_snapshot.py` のsafe diagnosis候補にも同じmappingを追加した。

## 4. ReadOnly Recheck

D13修正後に、立花証券デモ環境でReadOnly再取得を行った。

Artifacts:

- `.runtime/phase14d13/tachibana_demo_snapshot.json`
- `reports/phase_reports/phase14_d13_position_mapping_fix_readonly_recheck.json`
- `reports/phase_reports/positions_safe_diagnosis.json`

結果:

| Item | Result |
| --- | --- |
| environment | `demo` |
| orders | `PASS`, count=2 |
| positions | `PASS`, count=8 |
| account | `PASS` |
| cash / buying power | `PASS` |
| executions detail | `FAIL`, count=0 |
| final readonly status | `FAILED_BROKER_READONLY_FETCH` |

全体statusは引き続き `CLMOrderListDetail` 失敗により `FAILED_BROKER_READONLY_FETCH` だが、D13の主対象であるPosition mappingはPASSした。

Position safe diagnosis:

```text
combined.issue_code = 8/8
combined.quantity = 8/8
combined.market_value = 4/8
combined.price = 4/8
```

7203 Runtime Position evidence:

```text
account_type = cash
issue_code = 7203
quantity = 100
available_quantity = 100
average_price = 102.0000
market_price = 2941.0000
market_value = 294100
unrealized_pnl = 283900
raw_clmid = CLMGenbutuKabuList
```

## 5. Runtime v2 Reflection Recheck

D13 snapshotを使い、D11相当のRuntime反映をBroker APIなしで再評価した。

Artifact:

- `.runtime/phase14d13/reflection_reevaluation/phase14_d13_d11_reflection_check.json`

結果:

```text
final_decision = PHASE14D11_D8_BUY_REFLECTION_PASS
fill_classification = ORDER_LIST_DERIVED_FULL_FILL
execution_equivalent = true
target_position_found = true
target_position_quantity = 100
asset_contains_target_position = true
reconcile_pass = true
audit_pass = true
report_detail_optional_missing_noted = true
```

これにより、Phase14-D10のOrderList + Position + Cash evidence policyへ戻せる状態になった。

## 6. SELL Guard Readiness

7203のPosition evidenceが `quantity=100` として取得できるため、次のSELL系テストでは以下が可能になった。

- SELL quantity guardでBroker PositionをSource of Truthとして使う。
- 保有数量超過SELLをBLOCKEDにできる。
- SELL約定後のPosition数量減少を検証できる。
- BrokerOrder単体ではなくPosition / Cash evidenceからAssetを作れる。

## 7. Tests

```text
PYTHONPATH=src:. PYTHONPYCACHEPREFIX=.runtime/pycache_phase14d13 python3 -m pytest tests/runtime_v2 -q
277 passed

PYTHONPATH=src:. PYTHONPYCACHEPREFIX=.runtime/pycache_phase14d13 python3 -m pytest tests/broker/test_broker_normalizer.py tests/broker/test_tachibana_phase10c_session_foundation.py -q
102 passed
```

## 8. Prohibited Actions

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

## 9. Acceptance Criteria

| Criteria | Result |
| --- | --- |
| Position API raw responseのkey mappingを特定している | PASS |
| issue_codeが空文字にならない | PASS |
| quantityが0固定にならない | PASS |
| 7203 PositionをRuntime v2 Position evidenceとして取得できる | PASS |
| quantity=100を確認できる | PASS |
| BrokerOrder単体からAssetを作っていない | PASS |
| OrderList + Position + Cash evidence policyに戻せる | PASS |
| D11のBUY reflectionを再実行可能な状態になる | PASS |
| SELL数量guardに使えるPosition evidenceが得られる | PASS |
| 追加Submit / SELL / Cancel APIを実行していない | PASS |
| Production endpointへ到達していない | PASS |

## 10. Final Decision

```text
PHASE14D13_POSITION_MAPPING_FIX_COMPLETE
```

