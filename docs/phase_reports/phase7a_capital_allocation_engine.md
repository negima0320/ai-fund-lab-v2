# Phase7-A Capital Allocation Engine

## 1. Summary

Phase7-A Capital Allocation Engine の最小実装を完了した。

判定。

```text
PHASE7A_CAPITAL_ALLOCATION_ENGINE_READY
```

今回の実装は synthetic / fixture dry-run に限定した。

以下は行っていない。

```text
Broker API接続
Paper Trading
実発注
live order
立花証券API呼び出し
AIによる資金配分
Kelly基準
レバレッジ
信用取引
ナンピン
Phase6 EXIT単発での自動売却
固定利確
単純なTop3脱落Replacement
```

## 2. Implemented Scope

作成した実装。

```text
src/ai_fund_lab_v2/capital_allocation_ai/schema.py
src/ai_fund_lab_v2/capital_allocation_ai/policy.py
src/ai_fund_lab_v2/capital_allocation_ai/engine.py
src/ai_fund_lab_v2/capital_allocation_ai/audit.py
src/ai_fund_lab_v2/capital_allocation_ai/__init__.py
```

作成したスクリプト。

```text
scripts/run_phase7a_capital_allocation_dry_run.py
scripts/audit_phase7a_capital_allocation.py
```

作成したテスト。

```text
tests/capital_allocation_ai/test_phase7a_schema.py
tests/capital_allocation_ai/test_phase7a_policy.py
tests/capital_allocation_ai/test_phase7a_audit.py
```

## 3. Default Policy Parameters

Phase7-A default。

| parameter | value |
| --- | ---: |
| initial_total_assets | 1,000,000 |
| cash_buffer_ratio | 0.05 |
| max_position_weight | 0.20 |
| min_position_value | 50,000 |
| max_position_value | null |
| minimum_holding_days | 5 |
| replacement_rank_degradation_threshold | 20 |
| replacement_edge_margin | 0.02 |
| confirmation_days | 2 |
| emergency_exit_pct | -0.15 |

## 4. Decision Schema

Phase7-A decision record。

```text
target_date
code
action
current_position_value
target_position_value
current_weight
target_weight
buy_amount
sell_amount
cash_before_action
cash_after_action
expected_edge_score
buy_rank
opportunity_rank
downside_risk_score
risk_guard_status
position_signal
holding_days
unrealized_return
replacement_reason
defensive_reason
emergency_reason
validation_notes
```

action。

```text
BUY
HOLD
NO_ACTION
REPLACE_SELL
REPLACE_BUY
EMERGENCY_EXIT
DEFENSIVE_REVIEW
```

## 5. Dry-run Result

実行コマンド。

```text
python3 scripts/run_phase7a_capital_allocation_dry_run.py
```

結果。

| item | value |
| --- | ---: |
| status | OK |
| readiness_status | READY_FOR_PHASE7A_VALIDATION |
| decision_count | 13 |
| BUY | 2 |
| HOLD | 4 |
| NO_ACTION | 3 |
| REPLACE_SELL | 1 |
| REPLACE_BUY | 1 |
| EMERGENCY_EXIT | 1 |
| DEFENSIVE_REVIEW | 1 |
| max_buy_amount | 200,000 |
| sell_amount_exceeds_current_position_value | false |

主な確認ケース。

| case | result |
| --- | --- |
| Top3新規候補にBUYが出る | OK |
| minimum_holding_days未満の保有はHOLDになる | OK |
| emergency_exit_pct到達でEMERGENCY_EXITになる | OK |
| Phase6 EXIT単発はDEFENSIVE_REVIEWになる | OK |
| Top3から落ちただけではREPLACEしない | OK |
| replacement条件が揃った場合のみREPLACE候補になる | OK |
| buy_amountがmax_position_weight / cash_buffer / available_cashを超えない | OK |
| sell_amountがcurrent_position_valueを超えない | OK |

## 5.1. Replacement Execution Constraint

Phase7-Aのdry-runでは、比較検証用の decision record として `REPLACE_SELL` と `REPLACE_BUY` を同じ評価日に出力できる。

ただし、これは論理上の same-day replacement であり、実運用で売りと買いを同時実行する設計ではない。

実運用では、必ず以下の順序にする。

```text
1. REPLACE_SELL 候補を出す
2. 売り注文を出す
3. 売り約定を確認する
4. broker snapshot / buying power / cash を再取得する
5. REPLACE_BUY 候補を再評価する
6. 買付可能額・ロット・価格を確認してから買い注文を出す
```

Phase7-A / Phase7-Bのdry-run / validationでは論理上 same-day replacement として比較してよい。

将来の Broker / Paper Trading / live integration では、必ず以下の二段階実行にする。

```text
replacement_sequence:
SELL_FIRST_BUY_AFTER_FILL
```

この制約により、売却約定前の買付余力を仮定した実注文処理や、REPLACE_SELL / REPLACE_BUY の同時実行は行わない。

Artifact。

```text
reports/capital_allocation_ai/phase7a/capital_allocation_decisions.csv
reports/capital_allocation_ai/phase7a/capital_allocation_decisions.parquet
reports/capital_allocation_ai/phase7a/capital_allocation_summary.json
reports/capital_allocation_ai/phase7a/capital_allocation_audit.json
reports/capital_allocation_ai/phase7a/phase7a_completion_audit.json
```

## 6. Audit Result

実行コマンド。

```text
python3 scripts/audit_phase7a_capital_allocation.py
```

結果。

```text
completion_status:
PHASE7A_CAPITAL_ALLOCATION_ENGINE_READY

ready_for_phase7b:
true
```

監査フラグ。

| flag | value |
| --- | --- |
| broker_api_executed | false |
| paper_trading_executed | false |
| order_executed | false |
| live_order_executed | false |
| tachibana_api_called | false |
| fixed_take_profit_enabled | false |
| phase6_single_exit_auto_sell_enabled | false |
| simple_top3_drop_replacement_enabled | false |
| emergency_exit_enabled | true |
| replacement_requires_minimum_holding_days | true |
| replacement_requires_edge_margin | true |
| replacement_requires_confirmation_days | true |
| replacement_same_time_live_execution_enabled | false |
| replacement_requires_sell_fill_before_buy | true |
| cash_buffer_applied | true |
| max_position_weight_applied | true |

## 7. Test Result

実行コマンド。

```text
python3 -m pytest tests/capital_allocation_ai/test_phase7a_schema.py tests/capital_allocation_ai/test_phase7a_policy.py tests/capital_allocation_ai/test_phase7a_audit.py
```

結果。

```text
11 passed
```

## 8. Remaining Parameters

Phase7-B以降で検証する未決定パラメータ。

```text
minimum_holding_days:
5 / 10 / 20

replacement_rank_degradation_threshold:
Top10外 / Top20以下 / Candidate Top50外

replacement_edge_margin:
0.00 / 0.01 / 0.02 / 0.03

confirmation_days:
1 / 2 / 3

emergency_exit_pct:
-10% / -12% / -15% / -20% / -25%

cash_buffer_ratio:
0% / 5%

max_position_weight:
20% / 15% / 10%

min_position_value:
未決定

max_position_value:
未決定

lot_size:
未決定
```

## 9. Phase7-B Validation Topics

Phase7-Bで検証すべき内容。

```text
Top3 fixed 20bd hold vs Phase7-A conservative replacement

minimum_holding_days別のCAGR / max_drawdown / turnover比較

replacement_edge_margin別のreplacement_count / missed_winner_rate比較

confirmation_days別の過剰Replacement抑制効果

emergency_exit_pct別のworst_trade / max_drawdown / sold_then_up_rate比較

cash_buffer_ratio 0% / 5% のcapital_utilization比較

transaction_cost_sensitivity

2026 weak-regimeでのEmergency / Defensive signal有効性

full daily close path validation
```

## 10. Final Boundary Statement

Phase7-Aは、Capital Allocation Engine の policy / schema / engine / audit の最小実装である。

出力は売買ポリシー案であり、注文ではない。

```text
order_executed: false
broker_api_executed: false
paper_trading_executed: false
live_order_executed: false
tachibana_api_called: false
```
