# Phase29-H Post-E/G 100BD Final Effect Attribution and Performance Gate Audit

## Status

COMPLETE

READ_ONLY audit only. No Production code, Strategy, Runtime, config, schema, threshold, fixture, Accepted Generation, fresh-run, resume, 100BD, or long Historical execution was changed or performed.

Primary Judgment:

```text
PHASE29_H_POST_EG_100BD_FINAL_EFFECT_ATTRIBUTION_PARTIAL_IMPROVEMENT_NEXT_BOTTLENECK_CONFIRMED
```

Performance completion decision:

```text
PHASE29_PERFORMANCE_IMPROVEMENT_CONTINUE_ONE_MORE_FOCUSED_BOTTLENECK
```

## Target Run

```text
runtime-test-historical-smoke-20260809T211454176476Z
profile = historical-smoke
start = 2023-04-03
business_days = 100
initial_cash = 1,000,000 JPY
status = COMPLETED
final_judgment = REVIEW_REQUIRED
```

Close REVIEW_REQUIRED is separated from performance: runtime execution and trading/accounting state passed; close review is non-mutating Strategy Shadow / lineage review.

## Final Performance

| Metric | Before | After | Delta |
|---|---:|---:|---:|
| Final equity | 1,139,700 | 1,157,470 | +17,770 |
| Total return | +139,700 | +157,470 | +17,770 |
| Return rate | +13.970% | +15.747% | +1.777 pt |
| Max drawdown | -12.25% | -13.7517% | -1.5017 pt |
| Return / \|Max DD\| | n/a | 1.1451 | n/a |
| Worst 5BD return | n/a | -8.6775% | n/a |
| Worst 10BD return | n/a | -11.6532% | n/a |

After execution notional:

```text
BUY notional = 2,507,980
SELL notional = 1,885,890
total execution notional = 4,393,870
turnover = 4.39387x initial capital
realized_pnl = 41,100
unrealized_pnl = 153,000
```

Drawdown:

```text
peak = 1,134,260 on 2023-05-16
trough = 978,280 on 2023-06-01
largest peak-to-trough loss = -155,980 JPY
recovery = 2023-06-19, 12 business days after trough
```

## Capital Deployment

| Metric | Before | After |
|---|---:|---:|
| Average cash ratio | 44.71% | 39.1089% |
| Median cash ratio | n/a | 34.3992% |
| Final actual cash ratio | 50.81% | 32.6497% |
| Average actual exposure | 55.29% | 60.8911% |
| Median actual exposure | n/a | 65.6008% |
| Final actual exposure | 49.19% | 67.3503% |
| Exposure >= 60% days | n/a | 66 |
| Exposure >= 70% days | n/a | 39 |
| Exposure >= 80% days | n/a | 0 |
| Exposure >= 90% days | n/a | 0 |

The final Strategy target gross exposure was 72%, while final valuation-derived actual exposure was 67.3503%. The audit uses actual daily valuation exposure as the performance gate metric.

## Position Count

```text
average = 4.17
median = 5
min = 2
max = 6
final = 5
days with 1-2 positions = 9
days with 3-5 positions = 88
days with >=6 positions = 3
legacy max_positions re-authority = NO
```

Position count increase appears to be genuine opportunity allocation, not forced count or legacy max_positions bypass.

## ADD Funnel

| Stage | Before | After |
|---|---:|---:|
| PM ADD | 190 | 173 |
| D55-A PASS | 68 | 70 |
| PC positive accept | 60 | 60 |
| Lot-first executable | n/a | 5 |
| PS positive BUY_ADD | 4 | 5 |
| Runtime BUY_ADD | 4 | 5 |
| Fill | 4 | 4 |
| BUY_ADD notional | 345,500 | 273,300 |

ADD count conversion improved slightly through PS/Runtime formation, but filled count stayed flat and BUY_ADD notional decreased. ADD is therefore PARTIAL, not material.

## BUY_NEW Funnel

| Stage | Before | After |
|---|---:|---:|
| Positive request | 155 | 176 |
| PC positive accept | 102 | 92 |
| Lot-first executable | 29 | 29 |
| PS positive | n/a | 25 |
| Runtime BUY_NEW | 24 | 25 |
| Fill | 21 | 18 |
| BUY_NEW notional | n/a | 2,234,680 |

BUY_NEW runtime formation improved by one, but fills dropped from 21 to 18. Main dropouts remain concentration and lot/minimum-notional constraints.

## Capital Recycling

| Metric | Before | After |
|---|---:|---:|
| Lot skip days | 78 | 75 |
| Skipped allocation count | n/a | 189 |
| Recycled allocation count | n/a | 223 |
| Unused deployable capital days | 96 | 64 |
| Average unused deployable capital | 178,537.41 | 117,875.62 |
| Median unused deployable capital | n/a | 96,155.98 |
| Final residual deployable capital | n/a | 95,893.17 |

After unused deployable capital is derived as:

```text
incremental_budget_reconciliation.trimmed_incremental_weight * position_sizing.portfolio_value
```

Phase29-E materially improved capital recycling versus the immediate bottleneck, but residual unused capital remains meaningful.

## Concentration and Safety

```text
average largest position weight = 18.9988%
max largest position weight = 27.3290%
average top2 = 35.8100%
max top2 = 44.0632%
average top3 = 49.0677%
max top3 = 60.3967%
```

Phase29-G behavior was observed:

```text
passive drift >25% retained cases = 6
all observed cases = 21340
active BUY/ADD above cap with positive quantity = 0
```

21340 passive winner drift was retained on 2023-06-16, 2023-06-20, 2023-06-21, 2023-06-22, 2023-06-26, and 2023-06-27. This confirms Phase29-G had a real run-level effect: the prior 2023-06-16 Safety-cap HALT no longer stops the 100BD run.

## Winner Retention

Known focus cases:

```text
21340 campaign 1 realized = -25,200
21340 campaign 2 realized = +71,200
21340 net realized = +46,000
65730 final open unrealized = +106,920
```

Judgment:

```text
PARTIAL
```

Winner retention works in the sense that 21340 passive drift was retained and 65730 remains a large open winner. It is not a clean PASS because total performance is still concentrated and SELL / EXIT quality remains insufficiently explained.

## SELL / Re-Entry Decision Quality

Observed SELL then re-BUY:

```text
within 1BD = 0
within 3BD = 0
within 5BD = 0
within 10BD = 1
```

Judgment:

```text
PARTIAL
```

This is not a churn explosion. However, Close REVIEW_REQUIRED still reports SELL lineage / lifecycle review issues, and case-level original SELL source vs signal-change evidence is not complete enough to declare SELL quality PASS.

## Compound Capital Authority

Judgment:

```text
PASS
```

CCI results:

```text
CCI-1 PC target notional uses current authoritative equity = YES
CCI-2 Realized SELL proceeds return to available cash/buying power = YES
CCI-3 Realized profit can be redeployed = YES
CCI-4 Unrealized gains affect portfolio weight/equity correctly = YES
CCI-5 Unrealized gains are not double-counted as free cash = YES
CCI-6 Equity growth can increase future executable position size = YES
CCI-7 Losses reduce future sizing naturally = YES
CCI-8 Hidden fixed 1,000,000 sizing authority active = NO
```

Legacy `evaluation_capital` / `initial_cash` values remain in evidence and manifests, but audit classification is metadata/observability, not active sizing authority.

## Close REVIEW_REQUIRED

Classification:

```text
MULTI_CAUSAL_OBSERVABILITY_AND_SUMMARIZATION_GAP
```

Evidence:

```text
runtime_execution_judgment = PASS
trading_state_judgment = PASS
accounting_state_judgment = PASS
production_planning_judgment = PASS
strategy_shadow_close_classification = NON_MUTATING_STRATEGY_SHADOW_REVIEW_NON_BLOCKING
reported reasons include:
- SELL_PLAN_SOURCE_DECISION_NOT_TRACEABLE
- LIFECYCLE_CONSISTENCY_REVIEW_REQUIRED
- SELL_PLAN_TO_SUBMIT = False
SELL plans = 36
SELL submitted/executed = 20
```

No actual execution defect is proven in Phase29-H. Do not repair in this phase.

## Performance Gate

```text
P1 Return = PARTIAL
P2 Capital Deployment = PARTIAL
P3 Drawdown = PASS, with mild DD deterioration
P4 Compound Capital = PASS
P5 Safety / Concentration = PASS
P6 Winner Retention = PARTIAL
Overall = PARTIAL
```

Phase29-E material effect:

```text
PARTIAL
```

It improved average exposure and unused deployable capital materially, but ADD/BUY_NEW fills did not materially expand.

Phase29-G material effect:

```text
YES
```

It removed the 2023-06-16 passive concentration drift halt and allowed 21340 winner drift retention without weakening active ADD risk controls.

Primary remaining bottleneck:

```text
SELL / EXIT quality
```

Reason: capital deployment is improved enough to stop treating lot conversion as the sole blocker, compound capital passes, Safety regression is not observed, but return remains below the user's ~20% 100BD expectation and SELL lineage / lifecycle review prevents a clean quality judgment.

Long-horizon validation readiness:

```text
YES_WITH_REVIEW_REQUIRED_OBSERVABILITY_CAVEAT
```

The next long-horizon run is reasonable if the operator accepts that Close REVIEW_REQUIRED is non-mutating observability debt, not a proven execution defect. A cleaner path is one focused SELL / EXIT quality and lineage audit first.

## Deliverables

```text
reports/phase29_h_post_eg_100bd_final_effect_attribution_and_performance_gate_audit/performance_comparison.json
reports/phase29_h_post_eg_100bd_final_effect_attribution_and_performance_gate_audit/daily_equity_curve.csv
reports/phase29_h_post_eg_100bd_final_effect_attribution_and_performance_gate_audit/drawdown_analysis.json
reports/phase29_h_post_eg_100bd_final_effect_attribution_and_performance_gate_audit/cash_exposure_distribution.json
reports/phase29_h_post_eg_100bd_final_effect_attribution_and_performance_gate_audit/position_count_distribution.json
reports/phase29_h_post_eg_100bd_final_effect_attribution_and_performance_gate_audit/add_conversion_funnel.json
reports/phase29_h_post_eg_100bd_final_effect_attribution_and_performance_gate_audit/buy_new_conversion_funnel.json
reports/phase29_h_post_eg_100bd_final_effect_attribution_and_performance_gate_audit/capital_recycling_effect.json
reports/phase29_h_post_eg_100bd_final_effect_attribution_and_performance_gate_audit/residual_cash_reason_distribution.json
reports/phase29_h_post_eg_100bd_final_effect_attribution_and_performance_gate_audit/concentration_analysis.json
reports/phase29_h_post_eg_100bd_final_effect_attribution_and_performance_gate_audit/winner_retention_analysis.json
reports/phase29_h_post_eg_100bd_final_effect_attribution_and_performance_gate_audit/sell_reentry_decision_quality.json
reports/phase29_h_post_eg_100bd_final_effect_attribution_and_performance_gate_audit/compound_capital_authority.json
reports/phase29_h_post_eg_100bd_final_effect_attribution_and_performance_gate_audit/close_review_required_classification.json
reports/phase29_h_post_eg_100bd_final_effect_attribution_and_performance_gate_audit/performance_gate.json
```
