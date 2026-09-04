# Phase32-FO Late-Run Performance Decay / Capital Efficiency Root-Cause Exhaustive READ-ONLY Audit

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260903T213011268067Z`
- Evidence root: `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260903T213011268067Z`
- Audit freeze: `2023-08-03`, 207 completed business days.
- Current run moved during audit; later `2023-08-04+` state was not used for performance conclusions.
- Periods:
  - EARLY: `2022-10-03` through `2023-02-28` / 100BD
  - MIDDLE: `2023-03-01` through `2023-05-31` / 62BD
  - LATE: `2023-06-01` through `2023-08-03` / 45BD
- Evidence sources: `run_state.json`, daily `current_valuation_refresh/valuation_projection.json`, `positions/position_campaigns.json`, `execution/fills.json`, `strategy/buy_quality_decisions.json`, `strategy/portfolio_construction.json`, `strategy/position_sizing.json`, `strategy/market_context.json`, `strategy/portfolio_policy.json`, `position_management/pm_decisions.json`, and Phase32 FJ/FK/FL/FM/FN reports.

This audit is READ-ONLY with respect to Production/SHADOW/config/schema/runtime state/Pending/Ledger. No fresh-run, resume, recover, or replay was executed. The only created artifact is this report.

Historical PnL was used only for performance characterization and case discovery. It was not used to choose or tune Production features, thresholds, weights, ranks, or parameters.

## Source / Generation Context

- Current workspace source commit during audit: `04ded4ca66a9a6308be2bc395c0e26ba1a98b8bf`
- Run source baseline: `1f64f49ee9a8dd48280007e4df656e5f03e231ca`, `source_dirty=true`
- Daily source-commit evidence through the audit freeze:
  - `2022-10-03` through `2023-05-25`: only `1f64f49ee9a8dd48280007e4df656e5f03e231ca`
  - `2023-05-26` through `2023-08-03`: mixed evidence including `1f64f49...` and `04ded4...`

Judgment: source-generation transition is part of the evidence context for LATE, but no authority mismatch, schema incompatibility, or concrete correctness failure was found in this audit. The transition is therefore not proven as the causal explanation for the observed capital efficiency decay.

## Performance Shape

| Period | Start equity | End equity | Return | Return % | Peak equity | Max DD | Avg daily PnL | Positive-day rate | Avg positive day | Avg negative day | Volatility |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| EARLY | 1,012,350 | 1,267,270 | +254,920 | +25.18% | 1,311,900 | -4.11% | +2,575 | 65.7% | +8,454 | -8,926 | 11,055 |
| MIDDLE | 1,286,490 | 1,695,780 | +409,290 | +31.81% | 1,720,890 | -10.21% | +6,911 | 54.8% | +32,981 | -24,744 | 40,211 |
| LATE | 1,660,800 | 1,578,510 | -82,290 | -4.95% | 1,821,630 | -13.35% | -2,606 | 51.1% | +19,813 | -26,044 | 36,520 |

`PERFORMANCE_DECAY_BOUNDARY`: after the MIDDLE growth phase, materially visible from `2023-06-01`, with LATE peak on `2023-06-19` followed by a drawdown into `2023-08-03`.

## Capital Deployment

| Period | Avg exposure | Median exposure | Days >80% | Days >90% | Avg cash | Avg positions | BUY notional | SELL notional | Gross turnover |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| EARLY | 77.03% | 80.14% | 50.0% | 21.0% | 264,506 | 12.25 | 10,538,650 | 9,855,570 | 17.505 |
| MIDDLE | 81.41% | 83.24% | 56.5% | 22.6% | 274,798 | 10.61 | 9,825,960 | 9,853,830 | 13.418 |
| LATE | 85.01% | 85.83% | 80.0% | 20.0% | 254,888 | 14.49 | 5,982,130 | 5,954,560 | 7.021 |

`UNDER_INVESTMENT_EXPLAINS_DECAY`: NO. LATE had the highest average exposure and the highest share of days above 80% exposure. The decay is not explained by idle cash alone.

## Capital Efficiency

| Period | Return / avg exposure | PnL / BUY notional | PnL / turnover capital |
|---|---:|---:|---:|
| EARLY | +32.69% | +2.42% | +1.25% |
| MIDDLE | +39.08% | +4.17% | +2.08% |
| LATE | -5.83% | -1.38% | -0.69% |

`CAPITAL_EFFICIENCY_DECLINES`: YES. The late period deployed high exposure, but each unit of deployed capital produced weaker realized equity growth.

## BUY Quality / Marginal Capital

| Period | BUY fills | BUY_NEW | BUY_ADD | Median candidate rank | HIGH band | LOW band | MCV STRONG | MCV COMPARABLE | High/full/strong capital proxy | Cash-pref fill share |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| EARLY | 210 | 191 | 19 | 14 | 73 | 31 | 45 | 165 | 54.8% | 0.0% |
| MIDDLE | 119 | 111 | 8 | 15 | 36 | 3 | 11 | 108 | 41.2% | 0.0% |
| LATE | 79 | 77 | 2 | 21 | 23 | 11 | 18 | 61 | 64.3% | 0.0% |

`BUY_QUALITY_DISTRIBUTION_SHIFTS`: MIXED. Late selected capital is not visibly dominated by explicit MARGINAL or cash-preferred fills. However, median selected rank worsened from 14/15 to 21, LOW-band share rebounded, and ADD participation collapsed to 2 fills.

`STRONG_HIGH_CAPITAL_SHARE_EARLY_MIDDLE_LATE`: 54.8% / 41.2% / 64.3% using the conservative actual-fill proxy of HIGH band, FULL allocation, or MCV STRONG evidence.

`MARGINAL_CAPITAL_SHARE_EARLY_MIDDLE_LATE`: 0.0% / 0.0% / 0.0% for explicit marginal labels in filled rows. If `ELIGIBLE_COMPARABLE` is treated as non-strong rather than marginal, comparable shares are 70.9% / 89.5% / 73.4%.

`CASH_PREFERRED_FILL_SHARE_EARLY_MIDDLE_LATE`: 0.0% / 0.0% / 0.0%.

## Opportunity Supply vs Forced Deployment

| Period | BQ rows | HIGH/day | FULL/day | REDUCED/day | WAIT/day | REJECT/day |
|---|---:|---:|---:|---:|---:|---:|
| EARLY | 5,000 | 5.92 | 3.09 | 29.04 | 9.36 | 8.28 |
| MIDDLE | 3,100 | 4.76 | 2.79 | 26.06 | 12.27 | 8.68 |
| LATE | 2,250 | 6.13 | 3.76 | 26.42 | 10.73 | 8.76 |

`OPPORTUNITY_SUPPLY_DECLINES`: NO for raw BQ HIGH/FULL supply through the current audit freeze. LATE did not lack BQ-positive candidates by count. The weaker realized growth is therefore better characterized as capitalization/efficiency deterioration than simple opportunity scarcity.

`PC_MCV_DEPLOYS_DEEPER_INTO_MARGINAL`: NOT PROVEN. Explicit marginal capital was not observed in fills. The weaker median rank and higher position breadth suggest broader deployment, but not a canonical marginal-label overdeployment defect.

## Breadth / Winners / Losers / Churn

| Period | Opened campaigns | Winner rate | Loser rate | Loser loss | Median loser | Large losses >50k | Winner peak | Winner final | Winner capture | ADD campaigns |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| EARLY | 142 | 47.9% | 47.2% | -135,600 | -1,300 | 0 | 673,896 | 341,290 | 50.6% | 7 |
| MIDDLE | 72 | 43.1% | 51.4% | -182,500 | -2,300 | 0 | 882,782 | 539,040 | 61.1% | 3 |
| LATE | 56 | 58.9% | 33.9% | -181,100 | -3,600 | 1 | 325,570 | 195,770 | 60.1% | 2 |

`BUY_NEW_BREADTH_INCREASES`: YES, modestly. Unique BUY_NEW rate was about 1.19/day EARLY, 1.13/day MIDDLE, and 1.29/day LATE, while ADD nearly disappeared.

`WINNER_FORMATION_RATE_DECLINES`: NO in current evidence. LATE winner rate is higher, though some LATE campaigns are still young and this is not a final-outcome claim.

`LOSER_LOSS_INCREASES`: YES. LATE loser loss is almost equal to MIDDLE despite fewer days and fewer losing campaigns, median loser loss worsened, and one >50k loss appeared.

`WINNER_CAPTURE_DECLINES`: NO versus MIDDLE. Capture is about 60.1% LATE vs 61.1% MIDDLE. The issue is not primarily lower winner capture in this freeze; it is lower absolute winner peak/final contribution plus thicker loser impact.

`CHURN_INCREASES`: NO by gross turnover. Turnover declined from 17.505 to 13.418 to 7.021. The more relevant change is breadth/relationship composition: LATE capital is dominated by BUY_NEW and position count rises.

## Concentration / Regime-Adjusted Behavior

| Period | Avg top1 weight | Avg top3 weight | Top1 abs contribution share | Top3 abs contribution share |
|---|---:|---:|---:|---:|
| EARLY | 15.1% | 37.0% | 36.8% | 70.7% |
| MIDDLE | 18.2% | 40.5% | 38.1% | 71.9% |
| LATE | 19.6% | 39.7% | 37.2% | 72.1% |

`CONCENTRATION_INCREASES`: YES, modestly at top1 weight. Top3 contribution concentration remains persistently high across periods.

Regime-adjusted daily PnL:

| Regime | EARLY avg PnL / exposure | MIDDLE avg PnL / exposure | LATE avg PnL / exposure |
|---|---:|---:|---:|
| BULL | +2,712 / 87.2% | +5,571 / 83.3% | -2,359 / 85.7% |
| RANGE | +4,616 / 76.5% | +4,249 / 82.5% | -2,413 / 88.7% |
| RECOVERY | +1,339 / 80.5% | +13,382 / 79.0% | -282 / 84.5% |
| CORRECTION | +2,435 / 81.9% | -5,450 / 69.8% | -12,315 / 77.0% |

`SAME_REGIME_LATE_PERFORMANCE_WEAKER`: YES. LATE BULL/RANGE/RECOVERY labels produced weaker or negative PnL despite comparable or higher exposure.

`RISK_ON_WHIPSAW_INCREASES`: MIXED. LATE maintained high exposure across nominal BULL/RANGE/RECOVERY contexts and suffered negative average PnL, but the audit did not find a PIT correctness violation in regime/risk authority. This supports design review of risk-on persistence/whipsaw handling, not a correctness repair.

## ADD / Profit Retention / Known Phase32 Threads

`ADD_MATERIAL_TO_DECAY`: NO as a primary cause. LATE contains only 2 BUY_ADD fills; Phase32-FL measured ADD-attributable loss share at 6.24% and found giveback not ADD-specific.

`PROFIT_RETENTION_MATERIAL_TO_DECAY`: YES as a secondary design thread. Phase32-FM/FN showed `profit_retention_break` is meaningful but sometimes remains HOLD, with mixed economics. In this FO freeze, winner capture itself did not decline versus MIDDLE, so profit retention is not the sole primary explanation for LATE decay.

`RUN_AGE_BIAS_BEYOND_KNOWN_ADD_CAP_FOUND`: NO. Phase32-FK found no REENTRY-style cross-campaign re-ADD bias, but did find the campaign-local five-ADD cap. FO found no new long-lived history decision bias beyond that known campaign-local ADD cap.

## Root-Cause Classification

Primary observed change:

```text
high exposure maintained
-> capital efficiency turns negative
-> selected rank worsens and BUY_NEW breadth rises
-> ADD contribution nearly vanishes
-> loser losses become thicker
-> same nominal regimes produce weaker outcomes
```

`PRIMARY_DECAY_CAUSE`: MIXED capital-efficiency decay, led by weaker late-period realized edge per exposure and heavier loser impact while high exposure is maintained.

`SECONDARY_DECAY_CAUSES`:

- modest concentration increase and persistent top-contributor sensitivity
- BUY_NEW breadth increase with worse median selected rank
- near-zero ADD materialization, reducing incumbent winner capitalization contribution
- profit-retention/profit-protection design tension already characterized by FM/FN
- possible risk-on whipsaw/design issue because LATE BULL/RANGE/RECOVERY days underperformed despite high exposure
- source-generation transition is present as context after `2023-05-26`, but not proven causal

`CORRECTNESS_DEFECT_FOUND`: NO. No PIT, provenance, authority, stale-state, schema, Pending/Ledger, source-registry, or fail-closed correctness defect was proven.

`DESIGN_REFINEMENT_JUSTIFIED`: YES. The evidence supports a multi-factor design review around marginal capital quality, loser containment, concentration/profit protection, and risk-on re-exposure persistence.

`PRODUCTION_REPAIR_JUSTIFIED`: NO. There is no proven correctness defect that requires immediate Production repair.

`NEXT_ACTION`: Continue the long-horizon validation and separately open a design study that compares current capital deployment against action-neutral next-capital-unit evidence, profit-protection state, and regime/risk-on whipsaw behavior. Do not tune from this partial LATE outcome.

`LONG_HORIZON_VALIDATION_SAFE_TO_CONTINUE`: YES. This audit found no reason to stop the active validation run.

## Required Answer Summary

- `PERFORMANCE_DECAY_BOUNDARY`: `2023-06-01` / after MIDDLE growth, with LATE peak on `2023-06-19`
- `EARLY_RETURN`: `+254,920` / `+25.18%`
- `MIDDLE_RETURN`: `+409,290` / `+31.81%`
- `LATE_RETURN`: `-82,290` / `-4.95%`
- `EARLY_AVG_EXPOSURE`: `77.03%`
- `MIDDLE_AVG_EXPOSURE`: `81.41%`
- `LATE_AVG_EXPOSURE`: `85.01%`
- `UNDER_INVESTMENT_EXPLAINS_DECAY`: `NO`
- `CAPITAL_EFFICIENCY_DECLINES`: `YES`
- `BUY_QUALITY_DISTRIBUTION_SHIFTS`: `MIXED`
- `STRONG_HIGH_CAPITAL_SHARE_EARLY_MIDDLE_LATE`: `54.8% / 41.2% / 64.3%`
- `MARGINAL_CAPITAL_SHARE_EARLY_MIDDLE_LATE`: `0.0% / 0.0% / 0.0%` explicit marginal fills
- `CASH_PREFERRED_FILL_SHARE_EARLY_MIDDLE_LATE`: `0.0% / 0.0% / 0.0%`
- `OPPORTUNITY_SUPPLY_DECLINES`: `NO`
- `PC_MCV_DEPLOYS_DEEPER_INTO_MARGINAL`: `NOT_PROVEN`
- `BUY_NEW_BREADTH_INCREASES`: `YES`
- `WINNER_FORMATION_RATE_DECLINES`: `NO`
- `LOSER_LOSS_INCREASES`: `YES`
- `WINNER_CAPTURE_DECLINES`: `NO`
- `CHURN_INCREASES`: `NO`
- `CONCENTRATION_INCREASES`: `YES`
- `SAME_REGIME_LATE_PERFORMANCE_WEAKER`: `YES`
- `RISK_ON_WHIPSAW_INCREASES`: `MIXED`
- `ADD_MATERIAL_TO_DECAY`: `NO`
- `PROFIT_RETENTION_MATERIAL_TO_DECAY`: `YES_SECONDARY`
- `RUN_AGE_BIAS_BEYOND_KNOWN_ADD_CAP_FOUND`: `NO`
- `SOURCE_GENERATION_TRANSITION_INVOLVED`: `YES_AS_CONTEXT_NOT_PROVEN_CAUSAL`
- `PRIMARY_DECAY_CAUSE`: `MIXED_CAPITAL_EFFICIENCY_DECAY`
- `SECONDARY_DECAY_CAUSES`: `BUY_NEW_BREADTH / LOSER_LOSS / CONCENTRATION / PROFIT_RETENTION_DESIGN_TENSION / RISK_ON_WHIPSAW / LOW_ADD_MATERIALIZATION`
- `CORRECTNESS_DEFECT_FOUND`: `NO`
- `DESIGN_REFINEMENT_JUSTIFIED`: `YES`
- `PRODUCTION_REPAIR_JUSTIFIED`: `NO`
- `NEXT_ACTION`: `CONTINUE_LONG_VALIDATION_PLUS_MULTI_FACTOR_DESIGN_STUDY`
- `LONG_HORIZON_VALIDATION_SAFE_TO_CONTINUE`: `YES`

PRODUCTION_CHANGED: NO
SHADOW_CHANGED: NO
TARGET_RUN_MUTATED: NO
RUNTIME_STATE_MUTATED: NO
FUTURE_OUTCOME_USED_FOR_PRODUCTION_JUDGMENT: NO

Final Judgment: `PHASE32_FO_LATE_RUN_PERFORMANCE_DECAY_IS_MIXED_CAPITAL_EFFICIENCY_DECAY_NO_CORRECTNESS_DEFECT_DESIGN_REFINEMENT_JUSTIFIED`
