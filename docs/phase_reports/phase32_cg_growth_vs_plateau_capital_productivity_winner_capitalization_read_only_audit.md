# Phase32-CG — Growth Period vs Plateau Period Capital Productivity / Winner Capitalization READ-ONLY Audit

Target run:

`runtime-test-historical-extended-smoke-20260831T234344371102Z`

Evidence snapshot:

- run status at inspection: `RUNNING`
- source commit recorded in run commands: `cf0a00b0271d170094aa0ce2bfbedc203c364406`
- latest completed business date used: `2023-08-08`
- completed business days used through snapshot: `210`
- no mutating Runtime command was executed

This is a READ-ONLY characterization. No code, config, allocation rule, ADD rule, candidate ranking, max position, cap, exposure target, PM/SELL/HOLD/BQ behavior, Runtime state, Pending, Ledger, resume, recover, replay, or fresh-run action was changed or executed.

## Preserved Prior Conclusions

CG preserves Phase32-CE/CF and related Phase32 conclusions:

- SELL/HOLD/BQ broadening is not currently justified.
- Large-loss tail is partly concentration-driven.
- Organic Winner concentration can be strongly rewarded.
- High-notional starter risk is separate from organic Winner growth.
- ADD-driven concentration was not primary in CE.
- Initial high-notional binary admission is material but not a hard-cap correctness defect.
- CG does not redesign SELL, high-notional admission, ADD, caps, or ranking.

## Comparison Windows

Primary windows were the requested fixed windows:

- Growth Period: `2023-01-18` through `2023-04-10`
- Plateau Period: `2023-06-19` through `2023-08-08`

The Plateau window reaches beyond the requested minimum `2023-08-04`, so the comparison is sufficiently covered for CG's primary period audit.

## Method

Daily equity, market value, cash, holdings, exposure, position count, and concentration were read from:

`daily/<date>/current_valuation_refresh/current_valuation_manifest.json`

Daily symbol contribution was reconstructed as:

`current market value + same-day SELL proceeds - prior market value - same-day BUY notional`

Fills were read from `daily/<date>/execution/fills.json`. PM counts were read from `daily/<date>/position_management/pm_decisions.json`. Market regime and Buy Quality distributions were read from current run Strategy artifacts.

This is descriptive attribution only. Historical outcome was not used to create or tune a Production rule.

## Capital Productivity

| Metric | Growth | Plateau |
|---|---:|---:|
| Dates | 2023-01-18 -> 2023-04-10 | 2023-06-19 -> 2023-08-08 |
| Business days | 57 | 36 |
| Start equity | 1,135,830 | 1,777,340 |
| End equity | 1,766,350 | 1,737,730 |
| Period return | +55.51% | -2.23% |
| Net PnL | +630,520 | -39,610 |
| Gross positive PnL | +939,710 | +139,600 |
| Gross negative PnL | -309,190 | -179,210 |
| Gross gain / gross loss | 3.04 | 0.78 |
| Net retained fraction | 67.10% | -28.37% |
| Average daily return | +0.813% | -0.062% |
| Median daily return | +0.615% | -0.041% |
| Positive-day frequency | 67.86% | 42.86% |
| Negative-day frequency | 32.14% | 57.14% |
| Average exposure | 83.78% | 75.00% |
| Median exposure | 86.02% | 75.32% |
| Average invested capital | 1,094,343 | 1,313,607 |
| PnL / average invested capital | +57.62% | -3.02% |

`CAPITAL_PRODUCTIVITY_GROWTH = +57.62% net PnL / average invested capital`

`CAPITAL_PRODUCTIVITY_PLATEAU = -3.02% net PnL / average invested capital`

Plateau capital was still meaningfully deployed, but it generated materially less net return per unit of invested capital. The main difference is not zero exposure; it is lower productivity and cancellation.

## Position Count / Fragmentation

| Metric | Growth | Plateau |
|---|---:|---:|
| Median position count | 12 | 13 |
| P75 position count | 15 | 15 |
| P90 position count | 16 | 16 |
| Median 100-share positions | 9 | 10 |
| Median >100-share positions | 2 | 2 |
| Median equity share in 100-share positions | 70.11% | 67.05% |
| Median effective position count | 11.39 | 14.61 |
| Median HHI | 0.0878 | 0.0684 |
| Median top-1 share | 15.53% | 16.76% |
| Median top-3 share | 42.24% | 36.12% |
| Median top-5 share | 57.85% | 50.52% |

`PLATEAU_MORE_FRAGMENTED = YES_MODERATE`

Plateau had slightly more names and 100-share positions, lower HHI, and lower top-3/top-5 concentration. Top-1 was not lower, but top contribution concentration was much lower. This points to fragmentation of productive contribution rather than a simple count-only issue.

## Gross Gain / Gross Loss Cancellation

| Metric | Growth | Plateau |
|---|---:|---:|
| Symbol-day gross positive contribution | +1,448,550 | +403,800 |
| Symbol-day gross negative contribution | -818,030 | -443,410 |
| Net symbol-day contribution | +630,520 | -39,610 |
| Net retained / gross positive | 43.54% | -9.81% |

Plateau did have gross winners. They were cancelled by losses rather than absent.

`GROSS_GAIN_LOSS_CANCELLATION_MATERIAL = YES`

## Winner Contribution Concentration

Positive contribution concentration:

| Share of gross positive contribution | Growth | Plateau |
|---|---:|---:|
| Top 1 | 31.03% | 8.54% |
| Top 3 | 43.73% | 24.32% |
| Top 5 | 52.54% | 34.99% |
| Top 10 | 68.51% | 54.05% |

Growth was powered by a small number of economically dominant winners. Plateau still had winners, but no 59350/67310-style dominant gain engine.

Top Growth net contributors:

| Symbol | Net | Positive | Negative |
|---|---:|---:|---:|
| 59350 | +232,800 | +449,500 | -216,700 |
| 67310 | +100,000 | +100,000 | 0 |
| 44440 | +84,000 | +84,000 | 0 |
| 64240 | +41,300 | +41,400 | -100 |
| 68980 | +34,700 | +57,200 | -22,500 |

Top Plateau net contributors:

| Symbol | Net | Positive | Negative |
|---|---:|---:|---:|
| 31100 | +15,380 | +16,920 | -1,540 |
| 65260 | +12,400 | +16,400 | -4,000 |
| 66780 | +11,800 | +33,500 | -21,700 |
| 77090 | +10,100 | +15,200 | -5,100 |
| 95650 | +7,000 | +7,000 | 0 |

Plateau drags:

| Symbol | Net | Positive | Negative |
|---|---:|---:|---:|
| 40750 | -20,500 | +2,400 | -22,900 |
| 88900 | -19,400 | +25,700 | -45,100 |
| 40520 | -17,700 | +34,500 | -52,200 |
| 73690 | -14,830 | +5,830 | -20,660 |
| 45650 | -8,200 | +8,500 | -16,700 |

`WINNER_CONTRIBUTION_CONCENTRATION_DIFFERENCE = MATERIAL; Growth top-1/top-3 positive contribution share was far higher.`

## Winner Capitalization

`WINNER_CAPITALIZATION_GROWTH = STRONG`

Growth had dominant capitalized winners:

- `59350`: +232,800 net in the period, +449,500 gross positive, peak market value 549,000.
- `67310`: +100,000 period contribution on entry-day mark, though CE/CF preserve its later gap-risk classification.
- `44440`: +84,000 net with no offsetting loss in the period.
- `68980`: high-notional starter / winner control, +34,700 net.

Growth's major engine was not ADD-only. It was mostly organic appreciation plus successful high-notional / high-follow-through starters.

`WINNER_CAPITALIZATION_PLATEAU = WEAK`

Plateau had no comparable dominant winner:

- largest top net contribution was only +15,380
- largest positive contribution concentration top-1 was only 8.54%
- some large positions such as `88900` and `40520` contributed meaningful gross gains but gave them back or became drags

## Starter / New BUY Productivity

BUY_NEW campaigns initiated:

| Metric | Growth | Plateau |
|---|---:|---:|
| BUY_NEW entries | 78 | 68 |
| REENTRY entries | 0 | 0 |
| BUY_NEW initial notional | 6,205,660 | 7,338,070 |
| Capital recycled per business day | 108,871 | 203,835 |

Fixed horizon contribution for period starters:

| Horizon | Growth median | Growth mean | Growth positive rate | Growth material winner >=10k | Plateau median | Plateau mean | Plateau positive rate | Plateau material winner >=10k |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Same day | +750 | +4,245 | 65.4% | 14.1% | +425 | +902 | 66.2% | 1.5% |
| +1BD | +350 | +2,352 | 59.0% | 9.0% | +440 | +1,182 | 59.1% | 4.5% |
| +3BD | +550 | +4,995 | 59.0% | 10.3% | 0 | +191 | 49.2% | 3.2% |
| +5BD | +500 | +5,035 | 59.0% | 12.8% | 0 | -219 | 46.8% | 4.8% |
| +10BD | +620 | +7,842 | 59.0% | 12.8% | 0 | +304 | 47.1% | 7.8% |

`PLATEAU_STARTER_QUALITY_LOWER = YES_BY_FOLLOW_THROUGH`

Plateau starters did not immediately fail at same-day/+1BD, but they lacked Growth's +3/+5/+10BD follow-through and material-winner rate.

## BUY Turnover / Churn

| Metric | Growth | Plateau |
|---|---:|---:|
| BUY_NEW count | 78 | 68 |
| SELL_EXIT fills | 82 | 66 |
| REDUCE fills | 19 | 8 |
| PM ADD rows | 74 | 43 |
| PM REDUCE rows | 141 | 116 |
| PM EXIT rows | 44 | 28 |
| PM HOLD rows | 436 | 239 |
| Closed initiated campaigns | 78 | 56 |
| Median lifetime of closed initiated campaigns | 4BD | 4BD |
| Closed within 3BD | 34 | 24 |
| Closed within 5BD | 48 | 41 |

Plateau had fewer raw BUY_NEW entries but much higher initial BUY_NEW notional per business day and similar short campaign lifetimes. This is churn without productivity.

`PLATEAU_CHURN_MATERIAL = YES`

## ADD / Winner Scaling

| Metric | Growth | Plateau |
|---|---:|---:|
| PM ADD rows | 74 | 43 |
| actual BUY_ADD fills | 7 | 0 |
| BUY_ADD notional | 197,060 | 0 |
| campaigns receiving BUY_ADD | 2 | 0 |

Growth had actual ADD fills, but its primary growth engine still came from organic winners. Plateau had PM ADD signals but no actual BUY_ADD fills in the window.

`ADD_UNDERUTILIZATION_MATERIAL = YES`

This does not mean every PM ADD should have been filled. It means Plateau lacked executable Winner scaling, and additional capital mainly flowed to new starters / churn / cash rather than to scaled existing winners.

## Marginal Capital Competition

When additional capital was deployed in Plateau, the observed fill path was mostly:

```text
BUY_NEW starters
```

not:

```text
BUY_ADD into existing winners
```

Evidence:

- Plateau BUY_NEW initial notional: `7,338,070`
- Plateau BUY_ADD notional: `0`
- Plateau PM ADD rows still existed: `43`
- Plateau starter follow-through weakened after +3BD

`CAPITAL_COMPETITION_MISALLOCATION_SUPPORTED = PARTIAL`

The word "misallocation" is not used as a correctness defect here. The evidence supports an economic allocation weakness: marginal capital was more often materialized into new starters than into scaled winner positions, and those starters did not produce Growth-period follow-through.

## Productive Exposure

Descriptive exposure-state buckets:

- productive/mature: age at least 5 business days and positive unrealized PnL
- starter: age up to 5 business days
- weak: negative unrealized PnL

| Median exposure state | Growth | Plateau |
|---|---:|---:|
| Productive/mature exposure share | 50.02% | 37.83% |
| Starter exposure share | 33.04% | 39.24% |
| Weak exposure share | 6.52% | 13.24% |

`PRODUCTIVE_EXPOSURE_SHARE_GROWTH = 50.02%`

`PRODUCTIVE_EXPOSURE_SHARE_PLATEAU = 37.83%`

Plateau was not simply exposed less. It had less exposure in mature profitable states and more in starter / weak states.

## 100-Share Starter Saturation

`STARTER_SATURATION_MATERIAL = YES`

Evidence:

- median 100-share position count increased from 9 to 10
- median 100-share market value share remained very high: 70.11% in Growth and 67.05% in Plateau
- Plateau effective position count increased and HHI decreased
- Plateau starter exposure share rose to 39.24%
- Plateau new starter capital per business day almost doubled versus Growth

This is not "100 shares is bad". It is evidence that Plateau's deployed capital was more starter-heavy and less concentrated in productive winners.

## Opportunity Availability And Regime

Buy Quality raw opportunity evidence does not support a simple scarcity-only explanation:

| Metric | Growth | Plateau |
|---|---:|---:|
| BQ decision rows | 2,850 | 1,800 |
| FULL_ALLOCATION_ELIGIBLE | 223 | 178 |
| REDUCED_ALLOCATION_ONLY | 1,573 | 893 |
| HIGH band | 378 | 270 |
| MEDIUM band | 1,050 | 566 |

Per business day, Plateau did not obviously have fewer FULL/HIGH rows. But fixed-horizon follow-through was weaker, so opportunity quality after entry was lower than raw BQ availability alone suggests.

Regime composition:

| Regime | Growth days | Plateau days |
|---|---:|---:|
| BULL | 34 | 15 |
| RANGE | 11 | 9 |
| RECOVERY | 7 | 8 |
| CORRECTION | 2 | 4 |
| BEAR | 3 | 0 |

Regime-day PnL:

| Regime | Growth PnL | Plateau PnL |
|---|---:|---:|
| BULL | +127,340 | -14,530 |
| RANGE | +233,660 | -52,890 |
| RECOVERY | +147,460 | +20,500 |
| CORRECTION | +96,610 | +7,310 |
| BEAR | +25,450 | n/a |

`OPPORTUNITY_SCARCITY_SUPPORTED = PARTIAL_NOT_PRIMARY`

`REGIME_MIX_EXPLAINS_PLATEAU = PARTIAL_NOT_PRIMARY`

Plateau had less favorable BULL dominance and poor RANGE productivity, but raw candidate availability did not collapse. The stronger explanation is lower realized capital productivity and weaker winner capitalization under available opportunities.

## Rolling Window Robustness

20BD windows:

- best observed 20BD window through snapshot: `2023-03-10 -> 2023-04-10`, about `+40.07%`
- Plateau 20BD windows were mildly negative to flat; late Plateau examples:
  - `2023-07-06 -> 2023-08-04`: about `-1.65%`
  - `2023-07-07 -> 2023-08-07`: about `-1.49%`
  - `2023-07-10 -> 2023-08-08`: about `-1.30%`

40BD Plateau robustness is not fully available inside the fixed `2023-06-19 -> 2023-08-08` window because the Plateau window has 36 completed business days.

## Growth Engine Identification

`PRIMARY_GROWTH_ENGINE = CONCENTRATED_MAJOR_WINNERS_PLUS_ORGANIC_APPRECIATION_PLUS_SUCCESSFUL_STARTERS`

Supported mechanisms:

- dominant winners: especially `59350`, plus `67310`, `44440`, `64240`, `68980`
- high positive contribution concentration
- high gross gain / gross loss ratio
- productive/mature exposure share around 50%
- some actual BUY_ADD, but not the primary growth driver
- favorable but not sole regime tailwind

## Plateau Mechanism Identification

`PRIMARY_PLATEAU_MECHANISM = MIXED_GROSS_GAIN_LOSS_CANCELLATION_PLUS_WINNER_CAPITALIZATION_WEAK_PLUS_STARTER_SATURATION_PLUS_HIGH_CHURN_PLUS_ADD_UNDERUTILIZATION`

Best-supported primary/secondary mechanisms:

- `GROSS_GAIN_LOSS_CANCELLATION`: strong
- `WINNER_CAPITALIZATION_WEAK`: strong
- `STARTER_SATURATION`: material
- `HIGH_CHURN`: material
- `ADD_UNDERUTILIZATION`: material
- `CAPITAL_FRAGMENTATION`: moderate
- `LOWER_OPPORTUNITY_QUALITY`: partial by follow-through, not raw BQ scarcity
- `REGIME_MIX`: partial, not primary

`PLATEAU_IS_PRIMARILY = MIXED_CAPITAL_ALLOCATION_WEAKNESS_AND_WEAKER_OPPORTUNITY_FOLLOW_THROUGH`

This is not classified as a Runtime correctness defect. It is a capital productivity / performance architecture characterization.

## Required Final Answers

1. `LATEST_COMPLETED_DATE_USED = 2023-08-08`
2. `GROWTH_PERIOD = 2023-01-18 through 2023-04-10`
3. `PLATEAU_PERIOD = 2023-06-19 through 2023-08-08`
4. `GROWTH_PERIOD_RETURN = +55.51%`
5. `PLATEAU_PERIOD_RETURN = -2.23%`
6. `GROWTH_AVERAGE_EXPOSURE = 83.78%`
7. `PLATEAU_AVERAGE_EXPOSURE = 75.00%`
8. `CAPITAL_PRODUCTIVITY_GROWTH = +57.62% net PnL / average invested capital`
9. `CAPITAL_PRODUCTIVITY_PLATEAU = -3.02% net PnL / average invested capital`
10. `PLATEAU_CAPITAL_PRODUCTIVITY_LOWER = YES`
11. `GROWTH_MEDIAN_POSITION_COUNT = 12`
12. `PLATEAU_MEDIAN_POSITION_COUNT = 13`
13. `PLATEAU_MORE_FRAGMENTED = YES_MODERATE`
14. `GROWTH_TOP1_CONCENTRATION = 15.53% median EOD top-1 share`
15. `PLATEAU_TOP1_CONCENTRATION = 16.76% median EOD top-1 share; top-3/top-5 and contribution concentration were lower`
16. `WINNER_CAPITALIZATION_GROWTH = STRONG`
17. `WINNER_CAPITALIZATION_PLATEAU = WEAK`
18. `WINNER_CONTRIBUTION_CONCENTRATION_DIFFERENCE = MATERIAL`
19. `GROSS_GAIN_LOSS_CANCELLATION_MATERIAL = YES`
20. `GROWTH_STARTER_PRODUCTIVITY = POSITIVE_FOLLOW_THROUGH; +10BD median +620, mean +7,842, material-winner rate 12.8%`
21. `PLATEAU_STARTER_PRODUCTIVITY = WEAK_FOLLOW_THROUGH; +10BD median 0, mean +304, material-winner rate 7.8%`
22. `PLATEAU_STARTER_QUALITY_LOWER = YES_BY_FIXED_HORIZON_FOLLOW_THROUGH`
23. `PLATEAU_CHURN_MATERIAL = YES`
24. `GROWTH_BUY_ADD_COUNT = 7 fills, 197,060 notional, 2 campaigns`
25. `PLATEAU_BUY_ADD_COUNT = 0`
26. `ADD_UNDERUTILIZATION_MATERIAL = YES`
27. `STARTER_SATURATION_MATERIAL = YES`
28. `PRODUCTIVE_EXPOSURE_SHARE_GROWTH = 50.02% median mature/profitable exposure`
29. `PRODUCTIVE_EXPOSURE_SHARE_PLATEAU = 37.83% median mature/profitable exposure`
30. `CAPITAL_COMPETITION_MISALLOCATION_SUPPORTED = PARTIAL_ECONOMIC_ALLOCATION_WEAKNESS_NOT_CORRECTNESS_DEFECT`
31. `OPPORTUNITY_SCARCITY_SUPPORTED = PARTIAL_NOT_PRIMARY`
32. `REGIME_MIX_EXPLAINS_PLATEAU = PARTIAL_NOT_PRIMARY`
33. `PRIMARY_GROWTH_ENGINE = CONCENTRATED_MAJOR_WINNERS_PLUS_ORGANIC_APPRECIATION_PLUS_SUCCESSFUL_STARTERS`
34. `PRIMARY_PLATEAU_MECHANISM = MIXED_GROSS_GAIN_LOSS_CANCELLATION_PLUS_WINNER_CAPITALIZATION_WEAK_PLUS_STARTER_SATURATION_PLUS_HIGH_CHURN_PLUS_ADD_UNDERUTILIZATION`
35. `PLATEAU_IS_PRIMARILY = MIXED_CAPITAL_ALLOCATION_WEAKNESS_AND_WEAKER_OPPORTUNITY_FOLLOW_THROUGH`
36. `PRODUCTION_CHANGE_JUSTIFIED = NO`
37. `SHADOW_FOLLOWUP_JUSTIFIED = YES`
38. `NEXT_RECOMMENDED_STEP = READ-ONLY/SHADOW capital productivity study inside existing PC/PS/ADD architecture comparing marginal capital destinations: scaled winners vs new starters vs cash, with controls for Growth winners such as 59350 and high-notional starter controls from CF.`
39. `FINAL_JUDGMENT = PHASE32_CG_PLATEAU_CAPITAL_PRODUCTIVITY_LOWER_DESPITE_DEPLOYMENT_GROSS_GAIN_LOSS_CANCELLATION_AND_WEAK_WINNER_CAPITALIZATION_CHARACTERIZED_SHADOW_FOLLOWUP_JUSTIFIED_PRODUCTION_CHANGE_NOT_JUSTIFIED`

## No Change Confirmation

- code change: NO
- config/model/threshold/weight/cap change: NO
- Runtime/Pending/Ledger mutation: NO
- resume/recover/replay/fresh-run: NO
- Production behavior change: NO
- future outcome used for decision-time authority: NO

## Final Judgment

`PHASE32_CG_PLATEAU_CAPITAL_PRODUCTIVITY_LOWER_DESPITE_DEPLOYMENT_GROSS_GAIN_LOSS_CANCELLATION_AND_WEAK_WINNER_CAPITALIZATION_CHARACTERIZED_SHADOW_FOLLOWUP_JUSTIFIED_PRODUCTION_CHANGE_NOT_JUSTIFIED`
