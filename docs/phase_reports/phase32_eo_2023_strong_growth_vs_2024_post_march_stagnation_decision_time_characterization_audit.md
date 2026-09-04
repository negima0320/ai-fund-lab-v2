# Phase32-EO — 2023 Strong-Growth vs 2024 Post-March Stagnation Decision-Time Characterization Audit

## Scope

- Target run / SoT: `runtime-test-historical-extended-smoke-20260902T060955933565Z`
- Profile: `historical-extended-smoke`
- Run state at audit extraction: `RUNNING`
- Completed evidence coverage used: `2022-10-03` through `2024-12-18` (`545` completed business days)
- Current continuation point observed during read-only inspection: `2024-12-19:execution`
- Source baseline in run state: source commit `1f64f49ee9a8dd48280007e4df656e5f03e231ca`, accepted artifact hash `5451016e490214f81440f0d4fd154dc89cd76a86f84dd7daed5e8fb383e144a5`, registry hash `4c07b5647425b32653e3e0a0e1a1164130133cc0db2c22881dcef5b7c97a35ba`

This audit is read-only characterization. It does not judge candidates by future returns, MFE/MAE, later price movement, later SELL outcome, or final campaign PnL. Historical equity was used only to define and describe already-observed periods, not to tune or select Production parameters.

## Evidence Sources

Evidence was reconstructed from existing run artifacts only:

- `run_state.json`
- `daily/*/strategy/market_context.json`
- `daily/*/strategy/buy_quality_decisions.json`
- `daily/*/strategy/position_sizing.json`
- `daily/*/strategy/portfolio_construction.json`
- `daily/*/strategy/position_management.json`
- `daily/*/morning/planning_evidence.json`
- `daily/*/sell_planning/position_management_evidence.json`
- `daily/*/execution/fills.json`
- `daily/*/positions/position_campaigns.json`
- Prior Phase32 reports used as context only: EL, EM, EN

No source, config, runtime state, Pending, Ledger, Production artifact, or SHADOW artifact was modified.

## Compared Periods

The periods were selected from objective run evidence:

| Period | Dates | Reason |
| --- | --- | --- |
| A. 2023 strong growth | `2023-03-01` to `2023-06-30` | High-equity-growth interval in the current SoT run. |
| B. 2024 post-March early stagnation | `2024-03-18` to `2024-06-28` | After the March drawdown, including defensive rebuild and May/June capital redeployment. |
| C. 2024 Jul-Dec stagnation | `2024-07-01` to `2024-12-18` | Requested late-2024 comparison window. No new high-water mark was reached after `2024-03-05`. |

Monthly evidence showed the high-water mark reached `2,061,840` on `2024-03-05`; the longest no-HWM stretch in the observed run was `2024-03-06` through `2024-12-18`.

## Period Metrics

| Metric | A. 2023 Mar-Jun | B. 2024 Mar18-Jun | C. 2024 Jul-Dec |
| --- | ---: | ---: | ---: |
| Business days with PC evidence | 84 | 71 | 117 |
| Window equity change | +42.32% | +1.08% through May; June recovered but no HWM | -11.25% |
| Average exposure | 81.0% | 52.7% | 51.2% |
| Median exposure | 84.7% | 48.2% | 52.6% |
| Exposure min / max | 50.2% / 97.5% | 19.3% / 93.5% | 8.6% / 92.0% |
| Average cash | 286,465 | 907,944 | 856,382 |
| Average position count | 11.4 | 8.8 | 8.6 |
| Avg top1 / top3 / top5 concentration | 23.6% / 51.7% / 71.8% | 26.9% / 61.6% / 83.2% | 29.7% / 63.7% / 82.1% |
| Risk state: normal / cautious / gradual | 24 / 42 / 18 | 11 / 40 / 20 | 6 / 97 / 14 |

Interpretation:

- 2023 growth was not just higher exposure; it had materially more normal deployment and more diversified deployment.
- 2024 post-March and Jul-Dec were dominated by `CAUTIOUS_DEPLOYMENT`, much lower average exposure, lower position count, and higher top-name concentration.
- Late 2024 still periodically reached high exposure, so stagnation cannot be explained by cash alone. The character of deployed capital also changed.

## Candidate Quality Comparison

Decision-time BQ / candidate evidence:

| Metric | A. 2023 Mar-Jun | B. 2024 Mar18-Jun | C. 2024 Jul-Dec |
| --- | ---: | ---: | ---: |
| `FULL_ALLOCATION_ELIGIBLE` rows | 313 | 275 | 524 |
| `REDUCED_ALLOCATION_ONLY` rows | 2,168 | 1,884 | 3,027 |
| `BUY_WAIT` rows | 1,010 | 877 | 1,405 |
| `REJECT` rows | 696 | 482 | 801 |
| `REVIEW_REQUIRED` rows | 13 | 32 | 93 |
| Average quality score | 0.527 | 0.544 | 0.538 |
| Average top-5 quality score | 0.652 | 0.776 | 0.762 |
| Top-5 full slots / all top-5 slots | 46 / 420 | 26 / 355 | 52 / 585 |

Candidate-quality judgment:

- The evidence does not support pure `OPPORTUNITY_SCARCITY`.
- 2024 still had BQ-positive and top-ranked candidate evidence, and average top-5 quality was higher than the 2023 strong-growth window.
- The difference is that positive evidence more often remained reduced, waited, review-bound, risk-suppressed, or not converted into broad capital deployment.

## Selected / Bought Opportunity

Actual BUY fills by decision-time evidence:

| Metric | A. 2023 Mar-Jun | B. 2024 Mar18-Jun | C. 2024 Jul-Dec |
| --- | ---: | ---: | ---: |
| BUY fills | 135 | 97 | 156 |
| BUY notional | 11,411,500 | 9,824,560 | 14,905,040 |
| Average bought rank | 25.4 | 33.5 | 32.7 |
| Average bought quality | 0.625 | 0.567 | 0.570 |
| Bought `BUY_NEW` | 102 | 64 | 97 |
| Bought `REENTRY` | 31 | 33 | 59 |
| Bought `BUY_ADD` | 2 | 0 | 0 |
| Bought `FULL_ALLOCATION_ELIGIBLE` | 2 | 0 | 6 |
| Bought `REDUCED_ALLOCATION_ONLY` | 133 | 97 | 150 |
| Bought quality `<0.55` | 35 | 47 | 82 |
| Bought rank `>20` | 85 | 85 | 125 |

Selected-opportunity judgment:

- 2024 bought opportunities were weaker at decision time by the available rank and quality evidence.
- This is most visible in average bought rank moving from `25.4` to the low `33` range, average bought quality falling from `0.625` to about `0.57`, and low-quality bought counts increasing.
- ADD contribution effectively vanished after March. This is consistent with prior Phase32 ADD / marginal-capital audits, but EO did not find a new correctness defect from that fact alone.

## Candidate → BQ → Entry → PC → Runtime Funnel

Portfolio-construction and runtime funnel:

| Metric | A. 2023 Mar-Jun | B. 2024 Mar18-Jun | C. 2024 Jul-Dec |
| --- | ---: | ---: | ---: |
| PC positive NEW targets | 526 | 130 | 303 |
| PC positive ADD targets | 5 | 0 | 0 |
| PC zero-target rows | 2,810 | 2,607 | 4,421 |
| PC no-opportunity days/items | 0 | 17 | 20 |
| Average positive target weight | 7.02% | 5.79% | 5.71% |
| Median positive target weight | 5.82% | 4.76% | 5.39% |
| Runtime BUY plans | 275 | 110 | 181 |
| Runtime SELL plans | 129 | 98 | 145 |
| BUY fills / SELL fills | 135 / 164 | 97 / 122 | 156 / 159 |

Entry-state evidence observed in `position_sizing` rows:

| Entry evidence | A. 2023 Mar-Jun | B. 2024 Mar18-Jun | C. 2024 Jul-Dec |
| --- | ---: | ---: | ---: |
| `CONTINUATION_WITH_CAUTION` | 3,773 | 3,208 | 5,288 |
| `OVERHEATED_DECELERATING_ENTRY` | 469 | 344 | 500 |
| `HEALTHY_CONTINUATION_ENTRY` | 132 | 114 | 284 |
| `INSUFFICIENT_ENTRY_EVIDENCE` | 40 | 37 | 107 |
| `REVERSAL_RISK_ENTRY` | 23 | 4 | 6 |

Funnel judgment:

- 2024 had opportunity evidence, but the funnel produced far fewer positive PC targets per day and smaller target weights.
- The post-March funnel is not primarily an Execution loss problem: planned BUYs generally reached fills where approved, and no broad submit/fill authority defect was reproduced by EO.
- The dominant shift is upstream of execution: risk regime, Entry caution, reduced-only BQ, REENTRY/relationship constraints, and PC capital competition.

## Capital Deployment Character

Deployment changed materially:

- 2023 growth: high average exposure (`81.0%`), more normal deployment days, more positions, lower top-name concentration, and larger positive target weights.
- 2024 post-March: exposure averaged around half of equity, cash averaged around `900k`, position count dropped below 9, top-5 concentration rose above `80%`, and positive ADD disappeared.
- 2024 Jul-Dec: the system still bought, but under mostly `CAUTIOUS_DEPLOYMENT`; buys skewed to weaker ranks and lower quality, and exposure oscillated sharply rather than sustaining broad participation.

This supports `CAPITAL_ALLOCATION_SHIFT` and `REGIME/RISK_DEFENSIVENESS`, with some `ENTRY_QUALITY_SHIFT`. It does not prove a PC correctness defect because the target-zero analysis from Phase32-EN found zero clean unexplained BQ-positive target-zero cases.

## Long-Lived Holding Assessment

Representative open-position snapshots:

| Date | Open positions | Top concentration notes |
| --- | ---: | --- |
| `2024-03-29` | 9 | Top three: `23970` 22.3%, `70690` 19.3%, `94320` 17.5% of market value. |
| `2024-06-28` | 8 | Top three: `49210` 30.0%, `35580` 18.9%, `67040` 15.4%; `94320` remained 11.6%. |
| `2024-09-30` | 7 | `44850` alone was 41.7%; `94320` remained 11.9%. |
| `2024-12-18` | 10 | Top three: `63240` 23.8%, `73420` 17.3%, `44450` 12.0%; `94320` remained 9.6%. |

Long-lived example `94320`:

- Opened: `2023-01-23`
- Still open on `2024-12-18`
- PM events observed from `2024-03-18` through `2024-12-18`: `188` events, all `HOLD`
- Canonical sell state in those events: `HEALTHY_OR_RECOVERING`

Other examples:

- `76470` had `21` HOLD and `12` REDUCE events between `2024-03-18` and early May, showing weakening did reach PM as REDUCE evidence rather than being invisibly ignored.
- `44850` moved from HOLD to REDUCE/PERSISTENT_DETERIORATION and then EXIT in October, showing the lifecycle can release deteriorating capital.

Long-lived-holding judgment:

- There is some stale-capital / concentration character: `94320` occupies capital for nearly the entire comparison horizon, and late-2024 snapshots show higher concentration than 2023.
- However, the available decision-time evidence classifies the persistent `94320` state as `HEALTHY_OR_RECOVERING`; EO did not find a contract/provenance violation proving that this holding should have been forcibly released.
- The broader late-2024 concentration appears to be a portfolio character of fewer active positions and larger single-name weights, not a single confirmed stuck-capital correctness defect.

## Relationship to Phase32-EM / EN

EO is consistent with Phase32-EM and Phase32-EN:

- EM did not find candidate/execution correctness defects in the post-March funnel.
- EN found `0` clean unexplained BQ-positive target-zero rows for `2024-03-18` through May evidence.
- EN did find a structural relationship suppression pattern, but it was explained by PIT risk, Entry, REENTRY, expected-edge, downside, or incremental-justification evidence.

EO extends that view across late 2024:

- The stagnation window is not empty of opportunities.
- Capital deployment is more defensive, more concentrated, more reduced-only, and less ADD-driven.
- Bought opportunities appear weaker by decision-time rank/quality than in the 2023 strong-growth period.

## Root-Cause Classification

Final classification: `F. MIXED`

Components:

- `B. ENTRY_QUALITY_SHIFT`: Supported. Bought opportunities in 2024 have weaker decision-time rank/quality than in the 2023 growth window.
- `C. CAPITAL_ALLOCATION_SHIFT`: Supported. PC positive targets and target weights are lower, ADD is effectively absent, and buys are more reduced-only.
- `D. PORTFOLIO_CONCENTRATION_OR_STALE_CAPITAL`: Partially supported. Concentration is higher, and at least one long-lived holding (`94320`) occupies capital for the full stagnation window, but EO did not prove that its HOLD authority is invalid.
- `E. REGIME/RISK_DEFENSIVENESS`: Strongly supported. Late 2024 has `97` cautious deployment days versus only `6` normal deployment days.
- `A. OPPORTUNITY_SCARCITY`: Not primary. Strong/top BQ evidence still exists, especially in top-5 quality.
- `G. CORRECTNESS_DEFECT`: Not proven. No Architecture/SoT/PIT contract violation was identified.
- `H. INSUFFICIENT_EVIDENCE`: Not the overall classification; evidence is sufficient for characterization, though not for Production redesign.

## Production Repair Justified

`NO`

Reason:

- EO identified a performance-character shift, not a correctness defect.
- The observed 2024 behavior is explainable by decision-time risk posture, Entry caution, reduced-only BQ, relationship/REENTRY controls, and capital allocation semantics.
- Changing those semantics would be Strategy/PC design work, not a correctness repair justified by this audit.

## Next Single Thing To Investigate

Investigate one SHADOW-only question:

`Can action-neutral, next-capital-unit opportunity evidence separate late-2024 reduced-only/relationship-suppressed opportunities from genuinely weak opportunities without using future returns?`

This is the smallest useful next step because EO shows the gap is not candidate absence or execution loss; it is the decision-time translation from known opportunity evidence into capital deployment under relationship, Entry, and risk constraints.

## Explicit No-Mutation Confirmation

- `PRODUCTION_CHANGED: NO`
- `SHADOW_CHANGED: NO`
- `TARGET_RUN_MUTATED: NO`
- `RUNTIME_STATE_MUTATED: NO`
- `FUTURE_OUTCOME_USED_FOR_PRODUCTION_JUDGMENT: NO`

## Final Judgment

`PHASE32_EO_2023_VS_2024_DECISION_TIME_CHARACTERIZATION_MIXED_ENTRY_QUALITY_CAPITAL_ALLOCATION_RISK_DEFENSIVENESS_AND_CONCENTRATION_SHIFT_NO_CORRECTNESS_DEFECT_NO_PRODUCTION_REPAIR`
