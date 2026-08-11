# Phase29-K Post-J2 100BD Final Effect Attribution and Long-Horizon Validation Gate Audit

## Primary Judgment

PHASE29_K_POST_J2_100BD_MATERIAL_PERFORMANCE_IMPROVEMENT_CONFIRMED_LONG_HORIZON_READY.

Phase29 local 100BD tuning should stop. The next step is long-horizon validation, not another local 100BD parameter repair.

## Scope

READ_ONLY audit. No Production code, config, schema, threshold, Runtime artifact, fresh-run, resume, 100BD, or long Historical execution was changed by Codex.

Target run:

```text
runtime-test-historical-smoke-20260810T031643559982Z
2023-04-03 through 2023-08-25
100 business days
initial cash 1,000,000 JPY
runtime status COMPLETED
final judgment REVIEW_REQUIRED
```

Primary comparison baseline:

```text
runtime-test-historical-smoke-20260809T211454176476Z
```

## Performance Result

Return improved from +15.747% to +24.736%, a +8.989 percentage point gain and +89,890 JPY final-equity delta versus the Phase29-H primary baseline.

Max drawdown improved from -13.7517% to -12.9364%. Return / abs(max drawdown) improved to 1.9122.

Average exposure improved from 60.8911% to 70.7702%, and average cash fell from 39.1089% to 29.2298%. Final exposure was 83.4859%, with final cash 16.5141%.

Execution notional expanded from 4,393,870 JPY to 7,031,010 JPY. BUY notional was 3,912,510 JPY and SELL notional was 3,118,500 JPY.

## ADD Non-Regression

ADD did not weaken in the post-J2 run:

```text
PM ADD intent: 173 -> 186
BUY_ADD fills: 4 -> 4
BUY_ADD notional: 273,300 -> 304,440 JPY
```

BUY_NEW expanded materially:

```text
BUY_NEW fills: 18 -> 28
BUY_NEW notional: 2,234,680 -> 3,608,070 JPY
```

The large performance improvement is therefore primarily capital deployment and BUY_NEW expansion, with ADD intent/notional preserved rather than regressed.

## Risk and Integrity

Cash/leverage integrity passed:

```text
negative cash occurrences: 0
exposure > 100% occurrences: 0
minimum cash: 20,030 JPY
maximum exposure: 98.2962%
pending cash integrity: PASS
```

Compound capital revalidation passed. There is no evidence of an active hidden fixed 1,000,000 JPY sizing base.

Concentration is acceptable for long-horizon validation, with monitoring. Average largest position weight was 19.9961%, max largest position weight was 31.0460%, and no active BUY/ADD above-cap positive-quantity bypass was observed.

## Winner Dependency

Top symbol contribution:

```text
65730: +187,110 JPY, 75.6428% of total return
```

Top 3 contribution:

```text
65730 + 21340 + 76470 = +342,610 JPY, 138.5066% of total return
```

This is high winner dependency, but not a local 100BD blocker. It should be validated over long horizons.

## Close REVIEW_REQUIRED Classification

Close REVIEW_REQUIRED is classified as non-mutating Strategy Shadow review:

```text
NON_MUTATING_STRATEGY_SHADOW_REVIEW_NON_BLOCKING
```

Runtime execution, trading state, accounting state, and production planning passed. No blocking execution defect was found.

## Gate

Performance gate:

```text
PASS
PHASE29_PERFORMANCE_OBJECTIVE_MET_LOCAL_TUNING_STOP_LONG_HORIZON_VALIDATION_READY
```

Stop local 100BD tuning:

```text
YES
```

Long-horizon ready:

```text
YES
```

Recommended next task:

```text
Phase29-L Multi-Year Historical Validation Handoff
```

## Mandatory Answers

```text
1 Primary Judgment: K-A MATERIAL_PERFORMANCE_IMPROVEMENT_CONFIRMED_LONG_HORIZON_READY
2 Before Return: +15.747%
3 After Return: +24.736%
4 Return delta: +8.989 percentage points, +89,890 JPY
5 Before Max DD: -13.7517%
6 After Max DD: -12.9364%
7 Before Average Exposure: 60.8911%
8 After Average Exposure: 70.7702%
9 Before Average Cash: 39.1089%
10 After Average Cash: 29.2298%
11 Exposure >=80 days Before/After: 0 / 31
12 Exposure >=90 days Before/After: 0 / 14
13 Before unused deployable capital: 64 days, 117,875.62 JPY average
14 After unused deployable capital: 37 days, 50,729.91 JPY average
15 Average / max positions: 4.86 / 7
16 ADD funnel delta: PM_ADD 173->186, Fill 4->4, notional 273,300->304,440 JPY
17 BUY_NEW funnel delta: Fill 18->28, notional 2,234,680->3,608,070 JPY
18 Turnover Before/After: 4.39387x / 7.03101x
19 Top winner contribution: 65730 +187,110 JPY, 75.6428%
20 Top3 winner contribution: +342,610 JPY, 138.5066%
21 Winner Retention judgment: PASS with high winner-dependency monitoring
22 SELL / EXIT Quality judgment: PASS with re-entry review caveat
23 Compound Capital PASS/FAIL: PASS
24 Negative Cash occurrences: 0
25 >100% Exposure occurrences: 0
26 Pending cash integrity PASS/FAIL: PASS
27 J1 material effect: MATERIAL_SUPPORTING_EFFECT
28 J2 material effect: MATERIAL_EFFECT
29 Close REVIEW_REQUIRED classification: NON_MUTATING_STRATEGY_SHADOW_REVIEW_NON_BLOCKING
30 Performance Gate: PASS
31 Stop Local 100BD Tuning YES/NO: YES
32 Long-Horizon Ready YES/NO: YES
33 Recommended next task: Phase29-L Multi-Year Historical Validation Handoff
34 Production code changed: NO
35 Runtime mutated: NO
36 Historical executed: NO
```

## Evidence

Evidence directory:

```text
reports/phase29_k_post_j2_100bd_final_effect_attribution_long_horizon_gate_audit/
```

Key generated evidence includes:

```text
performance_before_after.json
daily_equity_curve.csv
drawdown_analysis.json
cash_exposure_distribution.json
strategy_target_vs_actual_exposure.csv
unused_capital_analysis.json
position_count_analysis.json
concentration_analysis.json
add_funnel.json
buy_new_funnel.json
performance_attribution.json
winner_dependency.json
winner_retention.json
sell_exit_quality.json
sell_plan_submit_gap.json
compound_capital_revalidation.json
cash_leverage_integrity.json
j1_effect.json
j2_effect.json
close_review_classification.json
performance_gate.json
overfit_stop_tuning_gate.json
long_horizon_readiness.json
```
