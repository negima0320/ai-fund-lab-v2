# Phase32-FZ — June Long-vs-Fresh Same-Day Portfolio State / Target Weight / Legacy Divergence READ-ONLY Audit

## Scope

- Long run: `runtime-test-historical-extended-smoke-20260903T213011268067Z`
- Fresh June 1M run: `runtime-test-historical-extended-smoke-20260904T112908488385Z`
- Same-day completed comparison window at audit time: `2023-06-01` through `2023-06-27`
- Same-day completed date count: `19`

The fresh run was active externally. At the start of this audit it had completed through `2023-06-26`; by the final read it had completed through `2023-06-27`. This report uses the final observed read-only snapshot, `19` same-day completed dates.

READ-ONLY confirmation:

- Production changed: NO
- SHADOW changed: NO
- Source/config/schema changed: NO
- Runtime/Pending/Ledger state mutated by this audit: NO
- fresh-run/resume/replay/recover executed by this audit: NO
- Historical outcome used only for actual economics characterization: YES
- Historical outcome used to select weights/thresholds/SELL parameters: NO

## Same-Day Candidate Equivalence

Candidate/opportunity evidence is effectively the same across the two runs for the shared calendar dates.

| Metric | Value |
|---|---:|
| Same-symbol PC rows compared | 959 |
| Rank equality | 100.0% |
| Full signal equality: rank + quality + BQ + Entry + MCV | 83.73% |
| PC target exact equality | 61.42% |
| Top50 overlap | 100.0% |
| Top20 overlap | 100.0% |
| Strong / Comparable High overlap | 86.84% |
| Actual BUY symbol overlap | 19.84% |

Required:

- `SAME_DAY_COMPLETED_DATE_COUNT = 19`
- `CANDIDATE_SIGNAL_EQUIVALENCE_RATE = 83.73% exact full signal; 100.0% rank`
- `TOP50_OVERLAP_RATE = 100.0%`
- `TOP20_OVERLAP_RATE = 100.0%`
- `SAME_SYMBOL_PC_TARGET_EQUIVALENCE_RATE = 61.42%`

Interpretation:

Candidate Selection is not the dominant explanation for long-vs-fresh divergence in this June window. The two runs see the same Top50/Top20 opportunity universe, but portfolio state causes different target/fill outcomes.

## Portfolio Drift Metrics

Diagnostic drift metric:

```text
L1 drift = sum(abs(actual_weight - current_target_weight))
```

Classification tolerance for diagnostic reporting: `0.5 percentage point`, used only to avoid classifying tiny lot/marking noise as material drift.

| Metric | Long | Fresh |
|---|---:|---:|
| Average L1 target/actual deviation | 0.04269 | 0.04335 |
| Overweight position rows | 30 | 32 |
| No-current-target held rows | 3 | 1 |
| Position rows | 327 | 287 |
| Average position count | 17.21 | 15.11 |
| Avg top1 concentration | 18.08% | 17.56% |
| Avg top3 concentration | 38.79% | 40.02% |
| Avg top5 concentration | 51.73% | 53.60% |

Required:

- `LONG_AVG_TARGET_ACTUAL_WEIGHT_DEVIATION = 0.04269`
- `FRESH_AVG_TARGET_ACTUAL_WEIGHT_DEVIATION = 0.04335`
- `LONG_OVERWEIGHT_POSITION_COUNT = 30`
- `FRESH_OVERWEIGHT_POSITION_COUNT = 32`
- `LONG_NO_CURRENT_TARGET_HELD_COUNT = 3`
- `FRESH_NO_CURRENT_TARGET_HELD_COUNT = 1`

Interpretation:

The core hypothesis that long is uniquely more target/actual-drifted than fresh is not supported in the same-day June completed window. Drift magnitude is similar, and fresh is slightly higher by this diagnostic L1 measure.

## Long Legacy Overweight Cohort

Long Top50-IN overweight:

- `TOP50_IN_LEGACY_OVERWEIGHT_COUNT = 29`
- `TOP50_IN_LEGACY_OVERWEIGHT_NOTIONAL = 3,068,000`

Largest long overweight examples:

| Date | Symbol | Actual weight | Target weight | Excess | Rank | Top50 | PM action | Age | Campaign |
|---|---:|---:|---:|---:|---:|---|---|---:|---|
| 2023-06-13 | 36670 | 4.81% | 2.40% | 2.40% | 22 | YES | REDUCE | 1 | `pc-cc719f671212bb81-36670-0001` |
| 2023-06-12 | 30410 | 8.91% | 7.30% | 1.61% | 2 | YES | HOLD | 3 | `pc-f464e928cc9847ea-30410-0001` |
| 2023-06-09 | 65570 | 2.95% | 1.46% | 1.49% | 33 | YES | REDUCE | 2 | `pc-b86690f53e487e90-65570-0001` |
| 2023-06-13 | 30410 | 8.00% | 6.68% | 1.33% | 26 | YES | REDUCE | 4 | `pc-f464e928cc9847ea-30410-0001` |
| 2023-06-16 | 40520 | 7.65% | 6.38% | 1.26% | 5 | YES | HOLD | 1 | `pc-7f0ecd77fbac260d-40520-0001` |
| 2023-06-08 | 88900 | 18.99% | 17.93% | 1.05% | none | NO | HOLD | 14 | `pc-7d37f48b2080f663-88900-0001` |
| 2023-06-01 | 88900 | 18.12% | 17.46% | 0.67% | 25 | YES | HOLD | 7 | `pc-7d37f48b2080f663-88900-0001` |

No-current-target held examples:

| Date | Symbol | Actual weight | Target | Rank | Top50 | PM action |
|---|---:|---:|---:|---:|---|---|
| 2023-06-07 | 65570 | 2.87% | 0.00% | 35 | YES | blank |
| 2023-06-20 | 33230 | 2.28% | 0.00% | 32 | YES | blank |
| 2023-06-15 | 38450 | 2.09% | 0.00% | 40 | YES | blank |

These cases exist, but they are not large enough or negative enough to explain the long-vs-fresh performance difference by themselves.

## Misalignment PnL Attribution

Same-day long June window, holding contribution grouped by target/actual alignment:

| Class | Gross profit | Gross loss | Net PnL |
|---|---:|---:|---:|
| ALIGNED | 359,270 | -255,010 | 104,260 |
| UNDERWEIGHT_VS_CURRENT_TARGET | 8,700 | -181,170 | -172,470 |
| OVERWEIGHT_VS_CURRENT_TARGET | 148,600 | -34,990 | 113,610 |
| NO_CURRENT_TARGET_BUT_HELD | 10,750 | 0 | 10,750 |

Required:

- `OVERWEIGHT_COHORT_GROSS_LOSS = -34,990`
- `OVERWEIGHT_COHORT_NET_PNL = 124,360` including no-current-target held rows, or `113,610` for overweight-only rows
- `OVERWEIGHT_COHORT_SHARE_OF_LATE_LOSS = not a drag in the same-day June window; overweight cohort was net positive`

Large-loss symbol overweight contribution:

- Focus symbols: `67310`, `21340`, `76470`, `99840`, `30410`, `59550`, `66560`, `88900`, `40520`, `31330`
- Total negative contribution among these symbols in the same-day June window: `-346,740`
- Portion classified as overweight / no-current-target: `-26,900`
- `LARGE_LOSS_SYMBOLS_LEGACY_OVERWEIGHT_SHARE = 7.76%`

Interpretation:

The loss-side evidence does not support legacy overweight as the dominant direct loss source. The same-day June common window loss was more strongly associated with underweight-vs-target and aligned large positions.

## 67310 Deep Trace

Long run 67310 current target vs actual:

| Date | Actual weight | Target weight | Deviation | Rank | Quantity | Class | PM action | Campaign age |
|---|---:|---:|---:|---:|---:|---|---|---:|
| 2023-06-05 | 17.54% | 17.77% | -0.23% | 5 | 100 | ALIGNED | blank | blank |
| 2023-06-06 | 17.68% | 17.54% | 0.14% | 4 | 100 | ALIGNED | HOLD | 1 |
| 2023-06-07 | 17.73% | 17.68% | 0.05% | 6 | 100 | ALIGNED | HOLD | 2 |
| 2023-06-08 | 12.68% | 17.73% | -5.05% | 5 | 100 | UNDERWEIGHT | HOLD | 3 |
| 2023-06-09 | 0.00% | 0.00% | 0.00% | 5 | 0 | ALIGNED | EXIT | 4 |
| 2023-06-27 | 17.12% | 16.93% | 0.19% | 2 | 100 | ALIGNED | blank | blank |

67310 long fills in the broader run:

- 2023-04-21 BUY_NEW 100, gross notional 200,000; 2023-04-24 EXIT 100, 300,000.
- 2023-05-01 BUY_NEW 100, 300,000; 2023-05-02 EXIT 100, 300,000.
- 2023-05-08 BUY_NEW 100, 300,000; 2023-05-09 EXIT 100, 300,000.
- 2023-05-16 BUY_NEW 100, 200,000; 2023-05-22 EXIT 100, 300,000.
- 2023-06-05 BUY_NEW 100, 300,000; 2023-06-09 SELL_EXIT 100, 300,000.
- 2023-06-27 BUY_NEW 100, 300,000; later 2023-06-30 EXIT 100, 200,000.

Required:

- `67310_CURRENT_TARGET_VS_ACTUAL = mostly aligned; on 2023-06-08 it was underweight, not legacy overweight`
- `67310_ADD_HISTORY_CONTRIBUTION = none observed in the traced 67310 fills; repeated BUY_NEW/EXIT campaigns, not ADD accumulation`
- `67310_PM_RESPONSE_TO_TARGET_SHRINK = HOLD through 2023-06-08 loss, EXIT on 2023-06-09`

67310 was not present in the fresh June same-day holdings through the compared dates. The 67310 divergence is therefore a portfolio/campaign-state presence difference, not same-symbol fresh alignment.

## Target Shrink Response

Long run current target shrink events within the same-day June comparison:

| Response | Count |
|---|---:|
| HOLD | 88 |
| REDUCE | 42 |
| EXIT | 36 |
| ADD | 8 |

Total shrink events: `174`

`HOLD_REBALANCING_GAP_FOUND = YES`

Target reduction frequently leaves the actual holding in HOLD rather than immediate rebalance. However, the observed same-day economics do not prove that this gap is the dominant June loss driver.

## ADD / Campaign / REENTRY Divergence

- `ADD_ACCUMULATION_DRIFT_FOUND = PARTIAL`

ADD history can create persistent actual holdings in general, but the key large-loss symbol 67310 was not an ADD accumulation case in the June trace.

- `CAMPAIGN_STATE_DIVERGENCE_FOUND = YES`

Long and fresh hold different symbols/campaigns despite seeing the same Top50/Top20 candidate universe. Actual BUY overlap is only `19.84%`, while Top50/Top20 overlap is `100%`.

- `REENTRY_HISTORY_DIVERGENCE_FOUND = PARTIAL`

The 67310 trace shows repeated prior ownership / exit / new campaign behavior in the long run. This contributes to portfolio path dependence, but FZ did not isolate REENTRY history as the dominant same-day target/actual drift source.

## Long vs Fresh Main Judgment

Selection difference:

- `SELECTION_DIFFERENCE_MATERIAL = NO`

The same-day Top50 and Top20 sets are identical. Candidate rank equality is 100%.

Portfolio state difference:

- `PORTFOLIO_STATE_DIFFERENCE_MATERIAL = YES`

Actual holdings, campaigns, and BUY fills differ materially despite same candidate universe.

Campaign history difference:

- `CAMPAIGN_HISTORY_DIFFERENCE_MATERIAL = YES`

Long carries existing campaigns and prior path state. Fresh starts from a new June portfolio, so the same current opportunity evidence maps into different holdings and executions.

But the specific hypothesis that long weakness is primarily because legacy actual weights are overweight versus current target is not supported:

- Long and fresh drift are similar.
- Long overweight cohort is net positive in the same-day June window.
- 67310 was aligned/underweight, not legacy overweight.
- Large-loss symbol overweight share is only `7.76%`.

## Root Cause Classification

`ROOT_CAUSE_CLASSIFICATION = CAMPAIGN_STATE_INTERACTION_DOMINANT`

Secondary:

- `PORTFOLIO_STATE_DIFFERENCE_MATERIAL = YES`
- `HOLD_REBALANCING_GAP_FOUND = YES`
- `LEGACY_ACTUAL_WEIGHT_DRIFT_DOMINANT = NO`
- `ADD_ACCUMULATION_DOMINANT = NO`

`FRESH_STRONG_LONG_WEAK_DIFFERENCE_PRIMARILY_EXPLAINED_BY = PORTFOLIO_STATE + CAMPAIGN_HISTORY`

More precise wording:

Same market / same candidates produce different outcomes because long and fresh enter June with different existing positions and campaign histories. The evidence does not support current-target-vs-actual overweight drift as the primary mechanism.

## Correctness vs Design

- `CORRECTNESS_DEFECT_FOUND = NO`
- `DESIGN_REFINEMENT_JUSTIFIED = YES`
- `PRODUCTION_REPAIR_JUSTIFIED = NO`

Design follow-up is still justified, but it should target campaign/portfolio path dependence and opportunity-cost-aware rotation rather than assuming actual overweight drift.

`NEXT_DESIGN_DIRECTION = campaign-state-aware current opportunity re-evaluation and rotation design; specifically test whether incumbent/absent campaign state, not target/actual overweight, explains June long-vs-fresh divergence`

## Required Final Answers

- `SAME_DAY_COMPLETED_DATE_COUNT = 19`
- `CANDIDATE_SIGNAL_EQUIVALENCE_RATE = 83.73% exact full signal; 100.0% rank`
- `TOP50_OVERLAP_RATE = 100.0%`
- `TOP20_OVERLAP_RATE = 100.0%`
- `SAME_SYMBOL_PC_TARGET_EQUIVALENCE_RATE = 61.42%`
- `LONG_AVG_TARGET_ACTUAL_WEIGHT_DEVIATION = 0.04269`
- `FRESH_AVG_TARGET_ACTUAL_WEIGHT_DEVIATION = 0.04335`
- `LONG_OVERWEIGHT_POSITION_COUNT = 30`
- `FRESH_OVERWEIGHT_POSITION_COUNT = 32`
- `LONG_NO_CURRENT_TARGET_HELD_COUNT = 3`
- `FRESH_NO_CURRENT_TARGET_HELD_COUNT = 1`
- `TOP50_IN_LEGACY_OVERWEIGHT_COUNT = 29`
- `TOP50_IN_LEGACY_OVERWEIGHT_NOTIONAL = 3,068,000`
- `LARGE_LOSS_SYMBOLS_LEGACY_OVERWEIGHT_SHARE = 7.76%`
- `67310_CURRENT_TARGET_VS_ACTUAL = aligned/underweight, not legacy overweight`
- `67310_ADD_HISTORY_CONTRIBUTION = none; repeated BUY_NEW/EXIT campaigns`
- `67310_PM_RESPONSE_TO_TARGET_SHRINK = HOLD through 2023-06-08 loss, EXIT 2023-06-09`
- `ADD_ACCUMULATION_DRIFT_FOUND = PARTIAL`
- `HOLD_REBALANCING_GAP_FOUND = YES`
- `CAMPAIGN_STATE_DIVERGENCE_FOUND = YES`
- `REENTRY_HISTORY_DIVERGENCE_FOUND = PARTIAL`
- `LONG_PORTFOLIO_STATE_DRIFT = average L1 0.04269`
- `FRESH_PORTFOLIO_STATE_DRIFT = average L1 0.04335`
- `OVERWEIGHT_COHORT_GROSS_LOSS = -34,990`
- `OVERWEIGHT_COHORT_NET_PNL = 124,360 including no-current-target; 113,610 overweight-only`
- `OVERWEIGHT_COHORT_SHARE_OF_LATE_LOSS = not a drag; net positive in same-day June comparison`
- `SELECTION_DIFFERENCE_MATERIAL = NO`
- `PORTFOLIO_STATE_DIFFERENCE_MATERIAL = YES`
- `CAMPAIGN_HISTORY_DIFFERENCE_MATERIAL = YES`
- `ROOT_CAUSE_CLASSIFICATION = CAMPAIGN_STATE_INTERACTION_DOMINANT`
- `FRESH_STRONG_LONG_WEAK_DIFFERENCE_PRIMARILY_EXPLAINED_BY = PORTFOLIO_STATE + CAMPAIGN_HISTORY`
- `CORRECTNESS_DEFECT_FOUND = NO`
- `DESIGN_REFINEMENT_JUSTIFIED = YES`
- `PRODUCTION_REPAIR_JUSTIFIED = NO`
- `NEXT_DESIGN_DIRECTION = campaign-state-aware current opportunity re-evaluation and rotation design`

Final Judgment: `PHASE32_FZ_JUNE_LONG_FRESH_DIVERGENCE_IS_PORTFOLIO_CAMPAIGN_STATE_DRIVEN_NOT_CANDIDATE_SELECTION_OR_LEGACY_OVERWEIGHT_DOMINANT`
