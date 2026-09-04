# Phase32-FJ Winner Capitalization / Peak Giveback / Profit Capture Root-Cause READ-ONLY Audit

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260903T213011268067Z`
- Audit snapshot used: stable completed artifacts from `2022-10-03` through `2023-06-27`.
- The run was still active while this READ-ONLY audit was being performed; later partially appearing `2023-06-28+` artifacts were not used for the core aggregate to avoid mixing moving evidence.
- Evidence sources: `run_state.json`, daily `positions/position_campaigns.json`, `execution/fills.json`, `current_valuation_refresh/current_valuation_manifest.json`, `position_management/pm_decisions.json`, and prior Phase32 reports.

No Production, SHADOW, config, schema, runtime state, Pending, or Ledger mutation was performed. No fresh-run, resume, recover, or replay was executed.

## Campaign Population

| Metric | Value |
|---|---:|
| `TOTAL_CAMPAIGNS` | 244 |
| `COMPLETED_CAMPAIGNS` | 227 |
| `WINNER_CAMPAIGNS` | 71 |
| `ADD_CAMPAIGNS` | 12 |
| ADD winner campaigns | 9 |

Characterization-only aggregate, using campaign peak/captured/giveback evidence and fills through the audit snapshot:

| Cohort | Count | Peak profit | Captured positive profit | Giveback estimate | Capture ratio | Median MFE | Median final return | Median giveback |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| All campaigns | 244 | 2,212,342 | 648,420 | 1,361,522 | 45.4% | 3.19% | 0.00% | 3.08% |
| Completed campaigns | 227 | 1,985,920 | 523,720 | 1,262,000 | 43.7% | 2.82% | -0.14% | 2.92% |
| Winners | 71 | 2,024,903 | 857,180 | 1,134,143 | 44.0% | 17.55% | 8.33% | 11.41% |
| ADD campaigns | 12 | 337,452 | 65,300 | 225,772 | 33.1% | 14.67% | 3.98% | 13.47% |
| ADD winners | 9 | 328,413 | 108,840 | 216,773 | 34.0% | 18.59% | 9.69% | 15.30% |

Interpretation: selection and capitalization do create winners, including ADD winners, but a large share of peak unrealized profit is not retained into final captured profit. This is characterization, not a Production threshold proposal.

## Large Winner / ADD Cohort

Top peak-profit campaigns:

| Symbol | Campaign | Open | Close/status | ADD fills | REDUCE count | Max shares | Max weight | MFE | Final return | Giveback | Peak profit | Final profit | Capture |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 59350 | `pc-066b1d25c0a578b4-59350-0001` | 2023-03-17 | 2023-04-20 | 0 | 0 | 100 | 34.8% | 243.6% | 136.6% | 113.9% | 395,200 | 213,200 | 53.9% |
| 67310 | `pc-3dc0e019081df712-67310-0001` | 2023-05-16 | 2023-05-22 | 0 | 2 | 100 | 18.1% | 50.0% | 0.0% | 50.0% | 200,000 | 100,000 | 50.0% |
| 67310 | `pc-0b33f0684e39d842-67310-0001` | 2023-06-05 | 2023-06-09 | 0 | 0 | 100 | 17.7% | 0.0% | -33.3% | 33.3% | 100,000 | 0 | 0.0% |
| 83060 | `pc-353ffefc940505e3-83060-0001` | 2022-10-14 | 2023-04-26 | 1 | 1 | 200 | 12.5% | 51.5% | 13.3% | 41.6% | 80,736 | 17,650 | 21.9% |
| 43880 | `pc-64642ec31e0f55ef-43880-0001` | 2023-03-22 | 2023-04-10 | 1 | 2 | 200 | 18.6% | 23.6% | 12.4% | 22.5% | 72,532 | 18,100 | 25.0% |
| 66560 | `pc-f62c17d79e12ebf4-66560-0001` | 2023-04-28 | 2023-06-02 | 0 | 2 | 100 | 12.8% | 34.9% | 20.4% | 14.5% | 58,800 | 35,200 | 59.9% |
| 92520 | `pc-b143256d72963fcb-92520-0001` | 2023-04-25 | 2023-04-27 | 0 | 0 | 100 | 19.0% | 8.9% | 8.9% | 0.0% | 51,720 | 51,720 | 100.0% |
| 21340 | `pc-0774f425fe6b09c1-21340-0001` | 2023-06-05 | OPEN | 1 | 0 | 2,500 | 5.2% | 119.4% | 79.0% | 40.4% | 51,700 | 34,200 | 66.2% |

Top ADD campaigns show the same pattern more sharply. `76470` and `94320` repeatedly receive ADD intent and actual ADD fills, but ADD-winner capture is materially below the overall winner cohort.

## 76470 Lifecycle

`76470` is not one campaign; it is a sequence of distinct campaigns. Key campaigns:

| Campaign | Open | Close/status | BUY/ADD path | REDUCE/EXIT path | Peak/giveback observation |
|---|---|---|---|---|---|
| `pc-c5e0986109845fbb-76470-0001` | 2022-10-12 | 2022-10-14 | BUY_NEW 600 shares | EXIT | Small positive, no material giveback. |
| `pc-d5155ddca7bde7ab-76470-0001` | 2022-10-20 | 2022-11-01 | BUY_NEW to 900 shares | 7 REDUCE events | Negative final, small MFE then giveback. |
| `pc-e27c96bb52f0a7bb-76470-0001` | 2022-11-07 | 2023-01-24 | BUY_NEW plus 5 ADD fills, max 2,100 shares | EXIT | Peak profit about 5,700, final about -600, capture 0%; ADD capitalization did not retain edge. |
| `pc-e91e1e7573c509df-76470-0001` | 2023-02-09 | 2023-02-14 | BUY_NEW | 2 REDUCE + EXIT | Flat/negative after reductions. |
| `pc-5b32844eb33bff6d-76470-0001` | 2023-02-20 | 2023-02-22 | BUY_NEW | EXIT | Flat. |
| `pc-0643cadfd0b26c2f-76470-0001` | 2023-02-28 | 2023-03-03 | BUY_NEW | 2 REDUCE + EXIT | Flat/negative. |
| `pc-da6119197c3334f9-76470-0001` | 2023-03-28 | 2023-03-30 | BUY_NEW | EXIT | Flat. |
| `pc-b28b3c7371371f96-76470-0001` | 2023-04-12 | 2023-04-17 | BUY_NEW | REDUCE + EXIT | Negative final. |
| `pc-86cc29266f5b880a-76470-0001` | 2023-04-21 | OPEN at snapshot | BUY_NEW plus 5 ADD fills; actual shares rose through 3,800, 3,900, 4,000, 4,100, 4,200, 4,300 | 1 REDUCE by 2023-06-02 | MFE 18.6%, current/final return 3.3%, giveback 15.3%, peak profit about 25,100, current captured about 7,900. |

`76470_CAMPAIGN_LIFECYCLE_EXPLAINED`: YES. Campaign identity continuity is intact; the apparent long 76470 story is a multi-campaign sequence with two material ADD campaigns. The leakage is not identity confusion, but repeated capitalization followed by low capture on later deterioration.

## 94320 Lifecycle

`94320` also has multiple campaigns:

- `pc-bd1879151437b21f-94320-0001`: opened 2022-10-05, closed 2022-12-07, 2 ADD fills, max 400 shares, final about -4,680, MFE 3.0%, giveback 10.9%.
- `pc-8ab721543669c35b-94320-0001`: opened 2022-12-13, still open at snapshot, 5 ADD fills, max 700 shares, max weight about 9.3%, MFE 11.4%, current return 10.6%, giveback 6.9%, peak profit about 18,540, current captured about 11,190, capture about 60%.

This is closer to intended winner retention than 76470. It still occupies capital for a long period, but the evidence does not show a correctness defect: PM continued to emit ADD/HOLD reasons such as `strong_trend_continuation`, `opportunity_rank_still_high`, `positive_expected_edge`, and `downside_risk_contained`.

## Large Daily PnL Attribution

Daily contribution below is calculated as:

`current market value - prior market value + same-day sell notional - same-day buy notional`.

This reconciles to total equity delta and separates mark-to-market from same-day trade cashflow.

### 2023-05-16

Total equity delta: `+121,300`.

Top contributors:

| Symbol | Contribution | Explanation |
|---|---:|---|
| 67310 | +100,000 | BUY_NEW 100 at 2,000; same-day valuation 3,000, market value 300,000. |
| 77930 | +7,900 | BUY_NEW at 1,066; same-day valuation 1,145. |
| 31330 | +5,000 | BUY_NEW at 435; same-day valuation 485. |
| 66560 | +3,300 | Existing position mark-to-market. |
| 71380 | +2,720 | BUY_NEW at 236; same-day valuation 249.6. |
| 83060 | +2,460 | Existing position mark-to-market. |
| 76010 | +2,400 | Existing position mark-to-market. |

`2023_05_16_TOP_PNL_CONTRIBUTORS`: dominated by 67310 same-day BUY_NEW valuation gain.

### 2023-05-19

Total equity delta: `-102,650`.

Top contributors:

| Symbol | Contribution | Explanation |
|---|---:|---|
| 67310 | -100,000 | Existing 100 shares repriced from 3,000 to 2,000. |
| 66560 | +5,800 | Existing position mark-to-market. |
| 31370 | +5,600 | SELL_EXIT above prior valuation. |
| 76010 | -3,800 | Existing position mark-to-market. |
| 49370 | -3,300 | Existing position mark-to-market. |
| 70660 | -2,950 | Existing position mark-to-market. |
| 31920 | -2,400 | Existing position mark-to-market. |

`2023_05_19_TOP_PNL_CONTRIBUTORS`: overwhelmingly 67310 single-position mark-to-market loss.

### 2023-05-22

Total equity delta: `+118,170`.

Top contributors:

| Symbol | Contribution | Explanation |
|---|---:|---|
| 67310 | +100,000 | SELL of 100 at 3,000 versus prior valuation 2,000. |
| 66560 | +12,700 | Existing position mark-to-market. |
| 44380 | +10,100 | BUY_NEW at 578; same-day valuation 679. |
| 49370 | +4,600 | Existing position mark-to-market. |
| 76470 | -4,300 | Existing ADD-capitalized position mark-to-market. |
| 31920 | -3,800 | Existing position mark-to-market. |
| 70660 | -3,500 | Existing position mark-to-market. |

`2023_05_22_TOP_PNL_CONTRIBUTORS`: again dominated by 67310, this time via sell/exit realization against prior-day valuation.

### 2023-06-08

Total equity delta: `-115,320`.

Top contributors:

| Symbol | Contribution | Explanation |
|---|---:|---|
| 67310 | -100,000 | Existing 100 shares repriced from 3,000 to 2,000. |
| 88900 | -4,100 | Existing position mark-to-market. |
| 76470 | -2,900 | Existing ADD-capitalized position mark-to-market. |
| 65570 | -2,500 | Existing position mark-to-market. |
| 99840 | -2,200 | Existing position mark-to-market. |
| 51310 | -1,900 | Existing position mark-to-market. |
| 94320 | -1,400 | Existing ADD-capitalized position mark-to-market. |

`2023_06_08_TOP_PNL_CONTRIBUTORS`: 67310 explains about 86.7% of the down day.

`LARGE_DAILY_SWINGS_PRIMARY_CAUSE`: concentrated single-name exposure to high-notional 100-share positions, especially 67310, plus same-day historical fill/valuation gaps in simulated execution artifacts. This is not explained by REENTRY, tick quantization, or accepted-generation mismatch.

## Deterioration, ADD, REDUCE, EXIT

Observed PM behavior:

- `59350`: several `profit_retention_break` HOLD decisions occurred before final `EXIT profit_retention_break` on 2023-04-20. This produced a very large winner with material giveback but still positive captured profit.
- `67310` May campaign: 2023-05-18 ADD intent existed at PM level, then 2023-05-19 and 2023-05-22 REDUCE decisions with `risk_increased_but_trend_not_broken`; actual lifecycle captured only about half the peak.
- `67310` June campaign: 2023-06-08 daily loss was dominated by same-day price movement; morning PM could not use that later same-day valuation as prior evidence. The campaign exited on 2023-06-09 with `hard_stop_current_return` / `profit_retention_break`.
- `43880`: 2023-03-23 `REDUCE peak_drawdown_warning` was followed by multiple ADD intents from 2023-03-24 onward under `strong_trend_continuation` / `opportunity_rank_still_high`, then later REDUCE/EXIT. This confirms ADD-after-deterioration can occur when current evidence recovers.
- `76470` April/June campaign: actual ADD capitalization occurred, then 2023-06-02 `REDUCE peak_drawdown_warning`; peak-to-current giveback remained material.

`DETERIORATION_RESPONSE_LAG_MATERIAL`: YES, as a design characteristic. The lag is not proven as a runtime correctness defect because decisions use strict-prior PIT evidence; same-day valuation drops cannot be used by that morning's PM decision. The material issue is that profit-retention warnings often remain HOLD/partial REDUCE before full capture.

`ADD_AFTER_DETERIORATION_FOUND`: YES. At least 43880 and other campaigns show ADD intent after prior deterioration/reduce signals when current PIT evidence again indicates strong continuation.

`ADD_REDUCE_RESPONSE_ASYMMETRY_FOUND`: YES. ADD intent can reappear frequently on recovered continuation evidence, while REDUCE/EXIT often progresses through partial or delayed capture. This is an architecture/design-refinement candidate, not a proven contract violation.

## Early vs Later Campaign Economics

Early strong campaigns show real edge creation:

- Large peak profits exist.
- ADD winners exist.
- High MFE campaigns are present.
- Candidate selection and BUY/ADD actual paths are functioning.

The economic leakage is downstream of winner creation:

- Large winners have material giveback.
- ADD-winner capture ratio is lower than overall winner capture ratio.
- A few concentrated 100-share high-notional positions dominate daily portfolio movement.
- Profit-retention evidence can coexist with HOLD for multiple days before EXIT.

`EARLY_LATE_CAMPAIGN_ECONOMICS_SHIFT`: MIXED. Through June 2023, the issue is not absence of opportunity; it is conversion of created opportunity into retained portfolio equity. Later 2024 stagnation remains covered by EO/EM/EN/EQ/ER/ES/ET and should not be folded into this FJ snapshot.

## Prior Issue Isolation

- `REENTRY_REGRESSION_FOUND`: NO. No FJ evidence points to REENTRY recent-exit guard regression as the cause of winner giveback.
- `QUANTIZATION_REGRESSION_FOUND`: NO. No one-yen tick / low-price quantization regression is needed to explain the large daily swings; 67310 is a high-notional 100-share position case.
- `CORRECTNESS_DEFECT_FOUND`: NO. The observed leakage is economically material but not proven to violate PIT, campaign identity, provenance, or runtime authority contracts.
- `DESIGN_REFINEMENT_JUSTIFIED`: YES. A profit-capture / winner-retention refinement study is justified, focused on peak giveback, partial REDUCE vs full EXIT, and concentration-aware profit protection.
- `PRODUCTION_REPAIR_JUSTIFIED`: NO at this phase. FJ is characterization; it does not prove a canonical correctness defect requiring immediate Production repair.
- `LONG_HORIZON_VALIDATION_SAFE_TO_CONTINUE`: YES, subject to normal runtime monitoring. No evidence here requires stopping the active long validation.

## Required Answers

- `TOTAL_CAMPAIGNS`: 244
- `COMPLETED_CAMPAIGNS`: 227
- `WINNER_CAMPAIGNS`: 71
- `ADD_CAMPAIGNS`: 12
- `WINNER_PEAK_PROFIT`: approximately 2,024,903
- `WINNER_CAPTURED_PROFIT`: approximately 857,180
- `WINNER_GIVEBACK`: approximately 1,134,143
- `WINNER_CAPTURE_RATIO`: approximately 44.0%
- `ADD_WINNER_GIVEBACK_MATERIAL`: YES
- `LARGE_DAILY_SWINGS_PRIMARY_CAUSE`: concentrated single-name high-notional exposure, especially 67310, with sell/buy valuation timing effects visible in historical simulated artifacts.
- `2023_05_16_TOP_PNL_CONTRIBUTORS`: 67310 +100,000; 77930 +7,900; 31330 +5,000; 66560 +3,300; 71380 +2,720.
- `2023_05_19_TOP_PNL_CONTRIBUTORS`: 67310 -100,000; 66560 +5,800; 31370 +5,600; 76010 -3,800; 49370 -3,300.
- `2023_05_22_TOP_PNL_CONTRIBUTORS`: 67310 +100,000; 66560 +12,700; 44380 +10,100; 49370 +4,600; 76470 -4,300.
- `2023_06_08_TOP_PNL_CONTRIBUTORS`: 67310 -100,000; 88900 -4,100; 76470 -2,900; 65570 -2,500; 99840 -2,200.
- `76470_CAMPAIGN_LIFECYCLE_EXPLAINED`: YES
- `DETERIORATION_RESPONSE_LAG_MATERIAL`: YES, as design behavior; not proven as correctness defect.
- `ADD_AFTER_DETERIORATION_FOUND`: YES
- `ADD_REDUCE_RESPONSE_ASYMMETRY_FOUND`: YES
- `EARLY_LATE_CAMPAIGN_ECONOMICS_SHIFT`: MIXED
- `PORTFOLIO_EDGE_LEAKAGE_PRIMARY_SOURCE`: winner peak-profit giveback plus concentrated single-name daily volatility, especially ADD-capitalized campaigns and 67310-style high-notional 100-share exposure.
- `REENTRY_REGRESSION_FOUND`: NO
- `QUANTIZATION_REGRESSION_FOUND`: NO
- `CORRECTNESS_DEFECT_FOUND`: NO
- `DESIGN_REFINEMENT_JUSTIFIED`: YES
- `PRODUCTION_REPAIR_JUSTIFIED`: NO
- `LONG_HORIZON_VALIDATION_SAFE_TO_CONTINUE`: YES

## No Mutation Confirmation

- `PRODUCTION_CHANGED`: NO
- `SHADOW_CHANGED`: NO
- `TARGET_RUN_MUTATED`: NO
- `RUNTIME_STATE_MUTATED`: NO
- `FUTURE_OUTCOME_USED_FOR_PRODUCTION_JUDGMENT`: NO

## Final Judgment

`PHASE32_FJ_WINNER_GIVEBACK_AND_CONCENTRATED_DAILY_SWINGS_MATERIAL_DESIGN_REFINEMENT_JUSTIFIED_NO_CORRECTNESS_DEFECT`
