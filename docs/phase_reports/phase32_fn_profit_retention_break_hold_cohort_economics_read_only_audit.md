# Phase32-FN Profit-Retention-Break HOLD Cohort Economics READ-ONLY Audit

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260903T213011268067Z`
- Audit snapshot: `2022-10-03` through `2023-07-14`, matching Phase32-FM.
- Starting point: Phase32-FM found `profit_retention_break` winner rows = 36, HOLD 18 / REDUCE 0 / EXIT 18, with all HOLD rows architecture-valid under the current contract.
- Evidence sources: Phase32-FM / FL / FJ, daily `position_management/pm_decisions.json`, `strategy/position_management.json`, `positions/position_campaigns.json`, `execution/fills.json`, and PM / Position Lifecycle / SELL Architecture SoT.

This was READ-ONLY. No Production, SHADOW, config, schema, runtime state, Pending, Ledger, fresh-run, resume, recover, or replay mutation was executed.

Historical outcome is used only for cohort economics and mechanical attribution. It is not used to select Production features, thresholds, weights, ranks, parameters, or SELL rules.

## Method

FM's 18 HOLD rows were deduplicated to unique campaigns. The economic anchor is the first `profit_retention_break -> HOLD` row per campaign.

For each campaign:

```text
first-break HOLD profit
-> maximum later profit through the snapshot
-> final/current captured profit through the snapshot
```

For same-day full exits, execution fills were used as the final captured profit source. This avoids double-counting pre-action position market value plus same-day sell proceeds.

`IMMEDIATE_EXIT_REFERENCE_ONLY`: first-break profit is shown only as a mechanical reference for understanding capital-at-risk. It is not a Production counterfactual or rule recommendation.

## HOLD Cohort Deduplication

| Metric | Value |
|---|---:|
| `HOLD_ROW_COUNT` | 18 |
| `UNIQUE_HOLD_CAMPAIGN_COUNT` | 5 |

| Symbol | Campaign | First HOLD | Last HOLD | HOLD rows | Subsequent REDUCE | Subsequent EXIT | Final status |
|---|---|---|---|---:|---|---|---|
| 59350 | `pc-066b1d25c0a578b4-59350-0001` | 2023-03-20 | 2023-04-17 | 9 | None | 2023-04-20 `profit_retention_break` | CLOSED |
| 43880 | `pc-64642ec31e0f55ef-43880-0001` | 2023-03-27 | 2023-03-27 | 1 | 2023-04-07 `peak_drawdown_warning` | 2023-04-10 `trend_and_opportunity_broken` | CLOSED |
| 21340 | `pc-0774f425fe6b09c1-21340-0001` | 2023-06-12 | 2023-06-23 | 5 | None | 2023-07-07 `trend_and_opportunity_broken` | CLOSED |
| 30410 | `pc-f464e928cc9847ea-30410-0001` | 2023-06-12 | 2023-06-12 | 1 | 2023-06-13 `risk_increased_but_trend_not_broken` | 2023-06-15 `trend_and_opportunity_broken` | CLOSED |
| 40520 | `pc-7f0ecd77fbac260d-40520-0001` | 2023-06-16 | 2023-06-19 | 2 | 2023-07-05 `peak_drawdown_warning` | 2023-07-14 `trend_and_opportunity_broken` | CLOSED |

## First-Break Anchors

All five first-break rows were current-contract-valid HOLD rows: continuation PASS, downside PASS, recovery present, and `profit_retention_break` paired with positive current evidence.

| Symbol | First shares | First market value | Approx position share of gross MV | First return | First MFE | First giveback | Continuation | Downside | Recovery | Regime |
|---|---:|---:|---:|---:|---:|---:|---|---|---|---|
| 59350 | 100 | 214,400 | 24.9% | 34.2% | 34.2% | 0.0% | PASS | PASS | RECOVERY_PRESENT | CORRECTION |
| 43880 | 100 | 147,300 | 14.0% | 23.6% | 23.6% | 0.4% | PASS | PASS | RECOVERY_PRESENT | RECOVERY |
| 21340 | 2,400 | 60,000 | 5.1% | 47.1% | 47.1% | 0.0% | PASS | PASS | RECOVERY_PRESENT | BULL |
| 30410 | 100 | 154,300 | 13.2% | 31.5% | 31.5% | 0.0% | PASS | PASS | RECOVERY_PRESENT | BULL |
| 40520 | 100 | 136,800 | 9.6% | 34.0% | 34.0% | 0.0% | PASS | PASS | RECOVERY_PRESENT | BULL |

## Campaign Economics

| Symbol | First-break profit | Post-HOLD peak date | Post-HOLD peak profit | Final captured profit | Incremental upside | Post-HOLD giveback | Final vs first-break | Classification |
|---|---:|---|---:|---:|---:|---:|---:|---|
| 59350 | 54,600 | 2023-04-06 | 389,200 | 213,200 | 334,600 | 176,000 | +158,600 | `HOLD_CLEARLY_ADDED_AND_RETAINED_VALUE` |
| 43880 | 28,100 | 2023-04-07 | 30,100 | 18,100 | 2,000 | 12,000 | -10,000 | `HOLD_ADDED_UPSIDE_BUT_GAVE_BACK_BELOW_FIRST_BREAK` |
| 21340 | 19,200 | 2023-06-19 | 51,700 | 26,700 | 32,500 | 25,000 | +7,500 | `HOLD_CLEARLY_ADDED_AND_RETAINED_VALUE` |
| 30410 | 37,000 | 2023-06-12 | 37,000 | 14,700 | 0 | 22,300 | -22,300 | `HOLD_NO_MEANINGFUL_ADDITIONAL_UPSIDE` |
| 40520 | 34,700 | 2023-06-19 | 47,300 | 29,600 | 12,600 | 17,700 | -5,100 | `HOLD_ADDED_UPSIDE_BUT_GAVE_BACK_BELOW_FIRST_BREAK` |

## Aggregate HOLD Cohort Economics

| Metric | Value |
|---|---:|
| `HOLD_COHORT_FIRST_BREAK_PROFIT` | 173,600 |
| `HOLD_COHORT_POST_HOLD_PEAK_PROFIT` | 555,300 |
| `HOLD_COHORT_FINAL_CAPTURED_PROFIT` | 302,300 |
| `HOLD_COHORT_INCREMENTAL_UPSIDE` | 381,700 |
| `HOLD_COHORT_POST_HOLD_GIVEBACK` | 253,000 |
| `HOLD_COHORT_NET_VS_FIRST_BREAK` | +128,700 |

Aggregate interpretation:

- HOLD did capture a large amount of additional upside after first break.
- The cohort still retained more final profit than the first-break reference.
- But post-HOLD giveback was also material: 253,000, or about 66.3% of the incremental upside.
- The aggregate positive result is concentrated in 59350; without 59350, the other four campaigns net to -29,900 vs first break.

## Recovery Counts

| Metric | Value |
|---|---:|
| `HOLD_CAMPAIGNS_WITH_POST_HOLD_UPSIDE` | 4 |
| `HOLD_CAMPAIGNS_FINAL_ABOVE_FIRST_BREAK` | 2 |
| `HOLD_CAMPAIGNS_FINAL_BELOW_FIRST_BREAK` | 3 |
| `HOLD_CLEARLY_ADDED_AND_RETAINED_VALUE_COUNT` | 2 |
| `HOLD_ADDED_UPSIDE_BUT_GAVE_BACK_BELOW_FIRST_BREAK_COUNT` | 2 |
| `HOLD_NO_MEANINGFUL_ADDITIONAL_UPSIDE_COUNT` | 1 |
| `OPEN_UNRESOLVED_COUNT` | 0 |

The count-level evidence is mixed. Four of five had some post-HOLD upside, but only two finished above the first-break reference.

## 59350 Deep Dive

Timeline:

```text
2023-03-20 first profit_retention_break HOLD
2023-03-20 to 2023-04-17 repeated profit_retention_break HOLD rows
2023-04-06 post-HOLD peak profit
2023-04-20 EXIT with profit_retention_break
```

Required economics:

- `59350_FIRST_BREAK_PROFIT`: 54,600
- First-break return: 34.2%
- `59350_POST_HOLD_PEAK_PROFIT`: 389,200
- Later peak return: approximately 243.6% campaign MFE in campaign evidence; daily profit peak used for cohort economics was 389,200.
- `59350_FINAL_CAPTURED_PROFIT`: 213,200
- `59350_HOLD_INCREMENTAL_UPSIDE`: 334,600
- `59350_POST_HOLD_GIVEBACK`: 176,000
- `59350_FINAL_VS_FIRST_BREAK`: +158,600

Answer to central question: 59350 both captured substantial additional upside and retained enough of it that final profit remained materially above the first-break reference. It also produced the largest post-HOLD giveback, so it is simultaneously the strongest evidence for winner-retention value and the strongest evidence for concentration-aware profit-protection design review.

## 21340 Deep Dive

`21340_HOLD_ECONOMICS`:

- Campaign: `pc-0774f425fe6b09c1-21340-0001`
- First profit-retention HOLD: 2023-06-12
- Last profit-retention HOLD: 2023-06-23
- HOLD row count: 5
- First-break profit: 19,200
- Post-HOLD peak profit: 51,700 on 2023-06-19
- Final captured profit: 26,700
- Incremental upside: 32,500
- Post-HOLD giveback: 25,000
- Final vs first-break: +7,500
- Later action: 2023-07-07 EXIT with `trend_and_opportunity_broken`
- Classification: `HOLD_CLEARLY_ADDED_AND_RETAINED_VALUE`

21340 confirms the same pattern at smaller absolute scale: HOLD captured real upside, then gave back most of the incremental peak, but still finished above first-break profit.

## Other HOLD Campaigns

### 43880

- First-break profit: 28,100
- Post-HOLD peak: 30,100
- Final captured: 18,100
- Net vs first-break: -10,000
- Later path: REDUCE `peak_drawdown_warning`, then EXIT `trend_and_opportunity_broken`

HOLD added only small upside and then gave back below the first-break reference.

### 30410

- First-break profit: 37,000
- Post-HOLD peak: 37,000
- Final captured: 14,700
- Net vs first-break: -22,300
- Later path: next-day REDUCE `risk_increased_but_trend_not_broken`, then EXIT `trend_and_opportunity_broken`

This is the clearest case where first-break HOLD did not produce meaningful additional upside.

### 40520

- First-break profit: 34,700
- Post-HOLD peak: 47,300
- Final captured: 29,600
- Net vs first-break: -5,100
- Later path: REDUCE `peak_drawdown_warning`, then same-snapshot EXIT `trend_and_opportunity_broken`

HOLD captured incremental peak value but did not retain it above the first-break reference.

## HOLD vs Immediate EXIT Reference

`IMMEDIATE_EXIT_REFERENCE_ONLY`: first-break profit is a descriptive anchor. It is not a proposed rule.

The anchor shows what was left at risk by continuing to HOLD:

- First-break total profit at risk: 173,600
- Later peak profit reached: 555,300
- Final captured: 302,300

Thus, the HOLD cohort did not simply "give back profit." It first expanded profit substantially, then retained only part of that expansion.

## HOLD vs Profit-Protect REDUCE Envelope

First-break exposure was meaningful:

- 59350: 214,400 market value, about 24.9% of gross position market value on that day.
- 43880: 147,300, about 14.0%.
- 30410: 154,300, about 13.2%.
- 40520: 136,800, about 9.6%.
- 21340: 60,000, about 5.1%.

No percentage REDUCE rule is proposed. The evidence only shows that first-break HOLD leaves substantial winner profit-at-risk in several cases, especially high-notional 100-share positions.

## Concentration Split

`HOLD_COST_CONCENTRATED_IN_LARGE_WINNERS`: YES.

- 59350 alone accounts for 176,000 of 253,000 post-HOLD giveback, about 69.6%.
- 59350 plus 21340 account for 201,000 of 253,000, about 79.4%.
- 59350 also accounts for 334,600 of 381,700 incremental upside, about 87.7%.

The economics are concentration-driven. 59350 dominates both the benefit and cost of continuing after `profit_retention_break`.

## Repeated HOLD Effect

`REPEATED_WARNING_WITHOUT_ACTION_MATERIAL`: YES.

Repeated cases:

- 59350: 9 `profit_retention_break -> HOLD` rows from 2023-03-20 through 2023-04-17 before 2023-04-20 EXIT.
- 21340: 5 rows from 2023-06-12 through 2023-06-23 before 2023-07-07 EXIT.
- 40520: 2 rows from 2023-06-16 through 2023-06-19 before 2023-07-05 REDUCE and 2023-07-14 EXIT.

The persistent-warning pattern is real. Current contract permits it because each row still has recovery / continuation evidence. Economically, it creates a repeated window where large winner profit remains exposed until a separate REDUCE or EXIT trigger appears.

## Later Action Triggers

| Symbol | Later action trigger |
|---|---|
| 59350 | EXIT with `profit_retention_break` after recovery/no-recovery boundary changed. |
| 43880 | REDUCE with `peak_drawdown_warning`, then EXIT with `trend_and_opportunity_broken`. |
| 21340 | EXIT with `trend_and_opportunity_broken`. |
| 30410 | REDUCE with `risk_increased_but_trend_not_broken`, then EXIT with `trend_and_opportunity_broken`. |
| 40520 | REDUCE with `peak_drawdown_warning`, then EXIT with `trend_and_opportunity_broken`. |

Current PM generally waits for either no-recovery / EXIT-candidate severity or a separate REDUCE/EXIT reason family. `profit_retention_break` with recovery remains HOLD.

## Economics vs Current Contract

Contract correctness:

- FM showed all 18 HOLD rows are valid under current accepted semantics.
- FN found no PIT, provenance, campaign identity, Runtime, or authority defect.

Economic characterization:

- HOLD created material upside.
- HOLD also created material post-peak giveback.
- The final aggregate was positive vs first-break, but the campaign count was mixed and the economics were dominated by one large winner.

Therefore economic leakage does not retroactively make the HOLD rows correctness defects.

## Design Necessity Signal

| Signal | Judgment |
|---|---|
| `HOLD_CREATES_MATERIAL_ADDITIONAL_UPSIDE` | YES |
| `HOLD_RETAINS_MATERIAL_ADDITIONAL_UPSIDE` | YES_AGGREGATE / MIXED_BY_CAMPAIGN |
| `HOLD_GIVEBACK_MATERIAL` | YES |
| `HOLD_NET_ECONOMICS_POSITIVE_VS_FIRST_BREAK` | YES_AGGREGATE |
| `HOLD_COST_CONCENTRATED_IN_LARGE_WINNERS` | YES |
| `REPEATED_WARNING_WITHOUT_ACTION_MATERIAL` | YES |

The design signal is not "exit immediately." The better-supported design question is whether a concentration-aware profit-protective REDUCE or escalation state should exist between HOLD continuation and full EXIT.

## Required Answers

- `HOLD_ROW_COUNT`: 18
- `UNIQUE_HOLD_CAMPAIGN_COUNT`: 5
- `HOLD_COHORT_FIRST_BREAK_PROFIT`: 173,600
- `HOLD_COHORT_POST_HOLD_PEAK_PROFIT`: 555,300
- `HOLD_COHORT_FINAL_CAPTURED_PROFIT`: 302,300
- `HOLD_COHORT_INCREMENTAL_UPSIDE`: 381,700
- `HOLD_COHORT_POST_HOLD_GIVEBACK`: 253,000
- `HOLD_COHORT_NET_VS_FIRST_BREAK`: +128,700
- `HOLD_CAMPAIGNS_WITH_POST_HOLD_UPSIDE`: 4
- `HOLD_CAMPAIGNS_FINAL_ABOVE_FIRST_BREAK`: 2
- `HOLD_CAMPAIGNS_FINAL_BELOW_FIRST_BREAK`: 3
- `HOLD_CLEARLY_ADDED_AND_RETAINED_VALUE_COUNT`: 2
- `HOLD_ADDED_UPSIDE_BUT_GAVE_BACK_BELOW_FIRST_BREAK_COUNT`: 2
- `HOLD_NO_MEANINGFUL_ADDITIONAL_UPSIDE_COUNT`: 1
- `OPEN_UNRESOLVED_COUNT`: 0
- `59350_FIRST_BREAK_PROFIT`: 54,600
- `59350_POST_HOLD_PEAK_PROFIT`: 389,200
- `59350_FINAL_CAPTURED_PROFIT`: 213,200
- `59350_HOLD_INCREMENTAL_UPSIDE`: 334,600
- `59350_POST_HOLD_GIVEBACK`: 176,000
- `59350_FINAL_VS_FIRST_BREAK`: +158,600
- `21340_HOLD_ECONOMICS`: first 19,200; peak 51,700; final 26,700; incremental upside 32,500; giveback 25,000; final vs first +7,500.
- `REPEATED_WARNING_WITHOUT_ACTION_MATERIAL`: YES
- `HOLD_CREATES_MATERIAL_ADDITIONAL_UPSIDE`: YES
- `HOLD_RETAINS_MATERIAL_ADDITIONAL_UPSIDE`: YES_AGGREGATE / MIXED_BY_CAMPAIGN
- `HOLD_GIVEBACK_MATERIAL`: YES
- `HOLD_NET_ECONOMICS_POSITIVE_VS_FIRST_BREAK`: YES_AGGREGATE
- `HOLD_COST_CONCENTRATED_IN_LARGE_WINNERS`: YES
- `CORRECTNESS_DEFECT_FOUND`: NO
- `DESIGN_REFINEMENT_JUSTIFIED`: YES
- `PRODUCTION_REPAIR_JUSTIFIED`: NO
- `LONG_HORIZON_VALIDATION_SAFE_TO_CONTINUE`: YES

## Judgment

Selected classification:

`D. HOLD_ECONOMICS_MIXED_CONCENTRATION_DRIVEN`

Reason:

- Aggregate economics support current winner-retention behavior because final captured profit exceeded first-break reference by 128,700.
- Campaign-level economics are mixed: only 2 of 5 finished above first-break, and 3 finished below.
- The dominant case, 59350, proves that HOLD can preserve substantial additional winner upside.
- The same case also proves that post-HOLD giveback can be large and concentrated.

## Next Recommended Step

Continue with design-only work on a profit-protection escalation concept that does not turn `profit_retention_break` into immediate EXIT. The strongest next question is whether current PIT evidence can support a middle `PROFIT_PROTECT_REDUCE` state for high-notional / high-MFE / repeated-warning winners while preserving the upside-capture benefit shown by 59350 and 21340.

## Final Judgment

`PHASE32_FN_HOLD_ECONOMICS_MIXED_CONCENTRATION_DRIVEN_UPSIDE_CAPTURED_BUT_RETENTION_GAP_MATERIAL`
