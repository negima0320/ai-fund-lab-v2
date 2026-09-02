# Phase32-CX — REENTRY Suppression Accumulation vs Long-Horizon Growth Decay READ-ONLY Audit

## Scope

This is a READ-ONLY audit.

No Production source, config, runtime state, Pending, Ledger, run artifact, resume, recover, replay, fresh-run, or long Historical command was modified or executed.

Primary diagnostic run:

- `runtime-test-historical-extended-smoke-20260831T234344371102Z`
- run status at inspection: `HALT`
- completed business dates used for direct artifact scan: `2022-10-03` through `2024-06-07`
- completed business days used: `413`
- halt after completed window: `2024-06-10:market_refresh`, operator interrupt

Post-CW reference run:

- `runtime-test-historical-extended-smoke-20260901T223409325599Z`
- run status at inspection: `RUNNING`
- completed dates observed: `2022-10-03` through `2022-10-14`
- used only for early structural comparison

The pre-CW run is interpreted through the Phase32-CN strict-prior reconstruction principle. Generic scalar `EXIT` collapse is not treated as legitimate Strategy rejection when strict-prior PM/campaign semantic evidence exists upstream.

Outcome data, future price, future return, future regime, MFE/MAE, final campaign outcome, and Historical profitability were not used to classify REENTRY opportunities or to select CW-eligible cases.

## References Read

- `docs/phase_reports/phase32_cm_reentry_zero_fill_requalification_suppression_root_cause_read_only_audit.md`
- `docs/phase_reports/phase32_cn_prior_exit_semantic_provenance_recovery_reentry_requalification_shadow_audit.md`
- `docs/phase_reports/phase32_cp_reentry_temporal_lifecycle_prior_campaign_relevance_read_only_audit.md`
- `docs/phase_reports/phase32_ch_post_april_plateau_root_cause_winner_capitalization_funnel_read_only_audit.md`
- `docs/phase_reports/phase32_ci_new_reentry_add_action_type_bias_post_april_opportunity_capture_root_cause_audit.md`
- `docs/phase_reports/phase32_ct_reentry_dedicated_penalty_necessity_legacy_safety_mechanism_read_only_audit.md`
- `docs/phase_reports/phase32_cu_minimal_residual_reentry_protection_production_contract_read_only_audit.md`
- `docs/phase_reports/phase32_cv_missing_generic_prior_exit_context_lifecycle_read_only_audit.md`
- `docs/phase_reports/phase32_cw_minimal_residual_reentry_unknown_context_production_repair.md`

## Method

Direct artifacts read:

- `run_state.json`
- `daily/<date>/strategy/portfolio_construction.json`
- `daily/<date>/strategy/runtime_planning.json`
- `daily/<date>/strategy/position_sizing.json`
- `daily/<date>/execution/fills.json`
- `daily/<date>/current_valuation_refresh/valuation_projection.json`
- `daily/<date>/current_valuation_refresh/current_valuation_manifest.json`
- `daily/<date>/positions/position_campaigns.json`

REENTRY candidate rows were identified from PC members where `reentry_recovery_status != NOT_APPLICABLE`. This is the canonical actual-path REENTRY surface in this run. The final `portfolio_members` artifact contains the PC materialized member surface; prior reports such as CM/CI used broader reconstructed episode/raw row populations where noted.

Classification used:

- legitimate residual protection: active cooldown / elapsed `<3BD`, repeated unresolved churn, prior-cause trend or momentum recovery failure, HARD_STOP enhanced recovery failure, corporate-action blocking;
- legacy / repaired suppression: generic prior EXIT provenance collapse, `insufficient_prior_exit_context`, REENTRY-only `reentry_opportunity_not_requalified`, REENTRY-specific BQ/quality block, long-lived prior-ownership suppression after the cooldown floor;
- canonical REENTRY fill: a BUY fill whose source authority is actually REENTRY. Same-symbol BUY_NEW bypass cases were not counted as canonical REENTRY fills.

## First REENTRY Candidate

`FIRST_REENTRY_CANDIDATE_DATE = 2022-10-05`

`FIRST_REENTRY_CANDIDATE_SYMBOL = 83060`

Evidence:

| Date | Symbol | Prior EXIT | Elapsed BD | Rank | BQ | Status | Reason |
| --- | --- | --- | ---: | ---: | --- | --- | --- |
| 2022-10-05 | 83060 | 2022-10-04 | 0 | 10 | `REDUCED_ALLOCATION_ONLY` | `FAIL_CLOSED` | `reentry_trend_recovery_not_satisfied` |

This is an immediate post-EXIT candidate. It belongs to the short-churn / prior-cause recovery surface, not the long-lived legacy penalty surface.

## First REENTRY Suppression

`FIRST_ANY_REENTRY_BLOCK_DATE = 2022-10-05`

The first block is `83060` on `2022-10-05`, elapsed `0BD`, trend and momentum not recovered. This is legitimate residual protection.

`FIRST_LEGITIMATE_RESIDUAL_REENTRY_BLOCK_DATE = 2022-10-05`

`FIRST_LEGACY_REENTRY_SUPPRESSION_DATE = 2022-10-11`

`FIRST_LEGACY_REENTRY_SUPPRESSION_SYMBOL = 89180`

`FIRST_LEGACY_REENTRY_SUPPRESSION_REASON = reentry_opportunity_not_requalified`

Evidence:

| Date | Symbol | Prior EXIT | Elapsed BD | Rank | Score | BQ | Prior Class | Status | Reason |
| --- | --- | --- | ---: | ---: | ---: | --- | --- | --- | --- |
| 2022-10-11 | 89180 | 2022-10-04 | 4 | 15 | -0.318816 | `REDUCED_ALLOCATION_ONLY` | `HARD_STOP` | `FAIL_CLOSED` | `reentry_opportunity_not_requalified` |

This is the first post-cooldown REENTRY-specific opportunity/requalification stop in the inspected final PC surface. It is classified as legacy/repaired suppression because CW removed broad REENTRY-only rank/requalification as an independent prior-ownership penalty, while preserving HARD_STOP enhanced recovery when it is the actual failed boundary.

## Earliest Material Capital Impact

`FIRST_MATERIAL_CAPITAL_IMPACT_DATE = 2022-10-12`

Causal chain:

```text
2022-10-04 89180 exited
-> 2022-10-12 89180 appears again as currently-flat prior-owned candidate
-> PC classifies it as REENTRY and fails it before target membership
-> no REENTRY PC target, no REENTRY PS/runtime executable quantity
-> same-day capital is deployed elsewhere: 94340 BUY_ADD and 76470 BUY_NEW
```

Evidence:

| Date | Suppressed REENTRY | Block | Same-day funded actions |
| --- | --- | --- | --- |
| 2022-10-12 | 89180 | `reentry_opportunity_not_requalified` | 94340 `BUY_ADD` 14,640 JPY; 76470 `BUY_NEW` 21,600 JPY |

This is material in the authority sense: the REENTRY row had no positive PC/PS/runtime materialization, while other symbols received executable capital. It is not a claim that 89180 would have been profitable.

## Daily Cumulative Prior-Owned Series

The full 413BD daily series was recomputed from fills plus PC artifacts. Key daily columns:

```text
date,ever_bought,fully_exited,prior_owned_currently_flat,active_positions,candidates,reentry_candidates,legacy_blocks,legitimate_blocks,reentry_pc_participants,reentry_plans,canonical_reentry_fills
```

Opening sample:

```text
2022-10-03,7,0,0,7,50,0,0,0,0,0,0
2022-10-04,10,3,3,7,50,0,0,0,0,0,0
2022-10-05,12,5,5,7,50,2,1,3,0,0,0
2022-10-06,15,5,5,10,50,4,3,5,0,0,0
2022-10-07,16,7,7,9,50,4,3,5,0,0,0
2022-10-11,16,8,8,8,50,6,4,4,0,0,0
2022-10-12,17,9,9,8,50,7,6,4,0,0,0
2022-10-13,18,12,12,6,50,7,6,2,0,0,0
2022-10-14,21,13,13,8,50,8,7,3,0,0,0
2022-10-17,24,14,14,10,50,8,7,3,0,0,0
2022-10-18,25,17,17,8,50,9,8,4,0,0,0
2022-10-19,28,18,18,10,50,11,10,6,0,0,0
2022-10-20,30,18,18,12,50,10,9,5,0,0,0
2022-10-21,30,20,20,10,50,9,7,5,0,0,0
2022-10-24,34,21,21,13,50,10,8,5,0,0,0
2022-10-25,36,23,23,13,50,10,10,3,0,0,0
2022-10-26,37,27,27,10,50,12,11,6,0,0,0
2022-10-27,40,28,28,12,50,13,12,6,0,0,0
2022-10-28,41,31,31,10,50,13,11,6,0,0,0
2022-10-31,42,32,32,10,50,14,13,5,0,0,0
```

Post-April structural-break sample:

```text
2023-04-03,188,181,180,8,50,30,29,6,0,0,0
2023-04-04,188,182,181,7,50,29,27,4,0,0,0
2023-04-05,188,183,182,6,50,32,30,3,0,0,0
2023-04-06,188,185,184,4,50,31,28,4,0,0,0
2023-04-07,190,185,184,6,50,31,28,5,0,0,0
2023-04-10,193,187,186,7,50,30,27,5,0,0,0
2023-04-11,194,188,187,7,50,27,24,4,0,0,0
2023-04-12,196,190,189,7,50,25,23,3,0,0,0
2023-04-13,198,191,190,8,50,26,23,6,0,0,0
2023-04-14,202,192,191,11,50,26,24,6,0,0,0
2023-04-17,203,195,194,9,50,28,24,8,0,0,0
2023-04-18,204,196,195,9,50,31,28,8,0,0,0
2023-04-19,204,197,195,9,50,30,27,8,0,0,0
2023-04-20,206,199,197,9,50,29,26,8,0,0,0
2023-04-21,208,201,199,9,50,27,24,6,0,0,0
2023-04-24,209,203,201,8,50,29,27,7,0,0,0
2023-04-25,211,205,204,7,50,31,29,8,0,0,0
2023-04-26,213,205,204,9,50,33,31,9,0,0,0
2023-04-27,216,207,206,10,50,31,30,6,0,0,0
2023-04-28,217,209,208,9,50,33,31,6,0,0,0
```

Late-run sample:

```text
2024-05-13,564,561,558,6,50,41,38,7,1,0,0
2024-05-14,565,561,558,7,50,41,38,6,0,0,0
2024-05-15,567,561,558,9,50,38,34,6,0,0,0
2024-05-16,568,562,559,9,50,41,37,6,0,0,0
2024-05-17,569,563,560,9,50,41,37,5,0,0,0
2024-05-20,569,565,562,7,50,40,35,6,0,0,0
2024-05-21,569,565,562,7,50,41,35,8,0,0,0
2024-05-22,569,567,563,6,50,42,37,6,1,0,0
2024-05-23,571,567,563,8,50,39,34,7,0,0,0
2024-05-24,573,567,563,10,50,38,35,4,0,0,0
2024-05-27,573,569,565,8,50,36,33,4,0,0,0
2024-05-28,574,570,566,8,50,37,34,5,0,0,0
2024-05-29,574,570,566,8,50,40,36,7,0,0,0
2024-05-30,575,572,568,7,50,38,34,7,0,0,0
2024-05-31,577,572,568,9,50,37,32,6,0,0,0
2024-06-03,577,575,570,7,50,37,32,4,1,0,0
2024-06-04,578,575,570,8,50,38,33,7,0,0,0
2024-06-05,578,576,571,7,50,38,32,8,0,0,0
2024-06-06,579,576,574,5,50,37,32,8,0,0,0
2024-06-07,579,577,575,4,50,41,33,11,0,0,0
```

`DAILY_CUMULATIVE_PRIOR_OWNED_SERIES = AVAILABLE_FROM_DIRECT_ARTIFACT_RECALCULATION`

The series is monotonic in unique ever-bought symbols and nearly monotonic in prior-owned flat symbols, except when re-opened positions temporarily reduce the flat count. The burden still rises from `0` to `575` prior-owned flat symbols by `2024-06-07`.

## Daily REENTRY Funnel Series

The daily REENTRY funnel was recalculated using PC final member rows:

```text
REENTRY candidate -> residual/legacy block -> PC participant -> runtime plan -> canonical REENTRY fill
```

Canonical REENTRY fills are zero in the pre-CW/cutoff window. Some later same-symbol BUY fills exist, but their `source_decision_type` is `BUY_NEW`; those are not counted as canonical REENTRY fills and overlap with the previously repaired BUY_NEW bypass class.

`DAILY_REENTRY_FUNNEL_SERIES = RECOMPUTED_FROM_PC_RUNTIME_FILL_ARTIFACTS`

## Monthly REENTRY Suppression Series

| Month | Candidates | REENTRY | REENTRY Share | Legacy Blocks | Legit Residual Blocks | REENTRY PC Participants | Canonical REENTRY Fills |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2022-10 | 1000 | 157 | 15.7% | 83 | 74 | 0 | 0 |
| 2022-11 | 1000 | 263 | 26.3% | 212 | 51 | 0 | 0 |
| 2022-12 | 1100 | 324 | 29.5% | 249 | 75 | 0 | 0 |
| 2023-01 | 950 | 363 | 38.2% | 282 | 81 | 0 | 0 |
| 2023-02 | 950 | 347 | 36.5% | 254 | 93 | 0 | 0 |
| 2023-03 | 1100 | 484 | 44.0% | 388 | 96 | 0 | 0 |
| 2023-04 | 1000 | 589 | 58.9% | 476 | 113 | 0 | 0 |
| 2023-05 | 1000 | 630 | 63.0% | 536 | 94 | 0 | 0 |
| 2023-06 | 1100 | 667 | 60.6% | 514 | 153 | 0 | 0 |
| 2023-07 | 1000 | 549 | 54.9% | 439 | 110 | 0 | 0 |
| 2023-08 | 1100 | 596 | 54.2% | 471 | 125 | 0 | 0 |
| 2023-09 | 1000 | 583 | 58.3% | 439 | 144 | 0 | 0 |
| 2023-10 | 1050 | 758 | 72.2% | 591 | 167 | 0 | 0 |
| 2023-11 | 1000 | 780 | 78.0% | 688 | 87 | 7 | 0 |
| 2023-12 | 1050 | 774 | 73.7% | 623 | 144 | 5 | 0 |
| 2024-01 | 950 | 728 | 76.6% | 630 | 96 | 2 | 0 |
| 2024-02 | 950 | 593 | 62.4% | 499 | 84 | 5 | 0 |
| 2024-03 | 1000 | 570 | 57.0% | 493 | 71 | 2 | 0 |
| 2024-04 | 1050 | 743 | 70.8% | 648 | 87 | 3 | 0 |
| 2024-05 | 1050 | 835 | 79.5% | 714 | 117 | 3 | 0 |
| 2024-06 | 250 | 191 | 76.4% | 155 | 34 | 1 | 0 |

`MONTHLY_REENTRY_SUPPRESSION_SERIES = ABOVE`

## REENTRY Opportunity Share By Period

| Period | Candidates | REENTRY | REENTRY Share | Legacy Blocks | Legit Residual Blocks |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2022Q4 | 3100 | 744 | 24.0% | 544 | 200 |
| 2023Q1 | 3000 | 1194 | 39.8% | 924 | 270 |
| 2023Q2 | 3100 | 1886 | 60.8% | 1526 | 360 |
| 2023Q3 | 3100 | 1728 | 55.7% | 1349 | 379 |
| 2023Q4 | 3100 | 2312 | 74.6% | 1902 | 398 |
| 2024Q1 | 2900 | 1891 | 65.2% | 1622 | 251 |
| 2024Q2 partial | 2350 | 1769 | 75.3% | 1517 | 238 |

This confirms the prior observation: REENTRY becomes an increasingly large fraction of observable PC opportunity population as the run accumulates ownership history.

`REENTRY_OPPORTUNITY_SHARE_BY_PERIOD = CONFIRMED_RISING_FROM_24.0_PERCENT_IN_2022Q4_TO_60.8_PERCENT_IN_2023Q2_AND_75.3_PERCENT_IN_2024Q2_PARTIAL`

## Suppression Acceleration Window

The REENTRY burden accelerates before inspecting equity:

- October 2022: REENTRY share `15.7%`, prior-owned flat max `32`.
- January-March 2023: REENTRY share rises into `36-44%`.
- April-June 2023: REENTRY share jumps to `58.9-63.0%`, prior-owned flat universe reaches `208` by `2023-04-28` and `271` by `2023-06-30`.
- 2023Q4 onward: REENTRY routinely exceeds `70%`.

`REENTRY_SUPPRESSION_ACCELERATION_WINDOW = 2023-04-03 through 2023-06-30`

This window is selected from REENTRY/cumulative ownership artifacts, not from the equity curve.

## Equity Growth Regime Windows

Independently, using equity high-water / slope from valuation artifacts:

| Window | Description |
| --- | --- |
| 2022-10-03 to 2022-12-30 | early mild growth / volatility; equity from about 1.01M to 1.11M |
| 2023-01-04 to 2023-04-10 | strongest acceleration; January-March monthly gains culminate near 1.77M by 2023-04-10 |
| 2023-04-11 to 2023-04-28 | drawdown / break; equity falls from about 1.62M to 1.57M in the direct valuation series and CH recorded the structural break from 2023-04-10 through 2023-04-28 |
| 2023-05-01 to 2023-08-31 | plateau / low-slope recovery; equity oscillates around 1.58M-1.81M with much weaker slope than Jan-Mar |
| 2023-09-01 to 2024-06-07 | extended low-slope / choppy period; some recovery attempts, but repeated drawdowns and high cash periods persist |

Monthly equity first/last snapshots:

| Month | First Equity | Last Equity | Delta |
| --- | ---: | ---: | ---: |
| 2023-01 | 1,107,270 | 1,196,240 | +88,970 |
| 2023-02 | 1,203,580 | 1,233,950 | +30,370 |
| 2023-03 | 1,262,100 | 1,605,220 | +343,120 |
| 2023-04 | 1,688,100 | 1,573,440 | -114,660 |
| 2023-05 | 1,580,490 | 1,638,130 | +57,640 |
| 2023-06 | 1,619,370 | 1,750,820 | +131,450 |
| 2023-07 | 1,757,240 | 1,747,910 | -9,330 |
| 2023-08 | 1,745,400 | 1,814,450 | +69,050 |

`EQUITY_GROWTH_REGIME_WINDOWS = ABOVE`

## Temporal Alignment

The REENTRY suppression acceleration window starts around `2023-04-03` and is fully visible through `2023-04-28`. The independent equity deceleration / structural break is `2023-04-10 through 2023-04-28`.

`REENTRY_SUPPRESSION_VS_GROWTH_DECELERATION_ALIGNMENT = COINCIDES_WITH_EARLY_PRECEDENCE`

Interpretation:

- REENTRY burden was already rising through Q1.
- It crosses into a materially large share of opportunity population just before and during the April break.
- The timing supports material contribution, not single-cause proof.

## Post-April REENTRY State

`POST_APRIL_REENTRY_STATE` for `2023-04-10 through 2023-04-28`:

| Metric | Value |
| --- | ---: |
| prior-owned flat symbols at 2023-04-10 | 186 |
| prior-owned flat symbols at 2023-04-28 | 208 |
| REENTRY rows in sampled window | 439 |
| legacy blocks in sampled window | 407 |
| legitimate residual blocks in sampled window | 105 |
| REENTRY PC participants | 0 |
| canonical REENTRY fills | 0 |
| active positions range | 7-11 |
| same-window BUY_NEW / BUY_ADD deployment | BUY_NEW continued; BUY_ADD notional 0 in CH post-April windows |

This is the point where the effective prior-owned REENTRY universe is already large enough to dominate the observable candidate surface, while capital still flows mainly into NEW starters.

## CW Contract Would-Release Count

Accepted CN comparable population through `2023-09-22`:

- REENTRY episodes: `267`
- original non-generic prior EXITs reconstructed: `229`
- original generic under current taxonomy: `38`
- restored semantic SHADOW recovery PASS: `25`
- long-delay `>60BD` SHADOW recovery PASS: `6`

`CW_CONTRACT_WOULD_RELEASE_COUNT_PRE_CW_RUN = 25_RECOVERY_PASS_EPISODES_UNDER_CN_STRICT_PRIOR_RESTORATION`

Breakdown available from CN:

| Prior EXIT class | Episodes | CW/CN restored recovery PASS |
| --- | ---: | ---: |
| `TREND_MOMENTUM` | 200 | 25 |
| `HARD_STOP` | 29 | 0 |
| `GENERIC` | 38 | 0 |

Month-level exact release counts for those 25 episodes were not materialized as a standalone artifact in the repository. Reconstructing them precisely would require rerunning the CN shadow episode classifier, which CX did not do as a mutating or fresh-run action. The direct PC row suppression burden by month is still visible in the monthly table above.

## Opportunity Quality Comparison

`NEW_VS_CW_ELIGIBLE_SUPPRESSED_REENTRY_PIT_COMPARISON`:

Decision-time PIT comparison supports a mixed but real substitution problem:

- CI found post-April REENTRY rows with positive `runtime_opportunity_score`, high ranks, and BQ reduced/full states while NEW received capital.
- CN found only `25/267` restored-context REENTRY recovery PASS episodes, so not every suppressed REENTRY was viable under CW.
- Representative substitution rows had suppressed REENTRY rank often better than funded NEW rank:
  - `2022-10-20` 76470 REENTRY rank 9 vs funded NEW ranks 17 and 42.
  - `2022-10-24` 76470 REENTRY rank 6 vs funded NEW ranks 23, 35, 24, 32.
  - `2022-10-25` 76470 REENTRY rank 6 vs funded NEW ranks 34 and 40.
  - `2022-10-26` 76470 REENTRY rank 5 vs funded NEW rank 26.
  - `2022-10-27` 76470 REENTRY rank 4 vs funded NEW ranks 24, 18, 19.

These are PIT comparisons only. They do not imply later profitability.

## Capital Substitution Cases

Direct scan found `300` dates where at least one post-cooldown legacy-suppressed REENTRY row with rank `<=10` coexisted with funded BUY activity elsewhere. This is a broad actual-path substitution population, not a claim that every case would pass CW.

`LEGACY_REENTRY_TO_WEAKER_NEW_SUBSTITUTION_CASE_COUNT = 300_DIRECT_PIT_SUBSTITUTION_SURFACES; 25_CN_CW_RELEASE_EPISODES_HIGH_CONFIDENCE`

Representative actual-path cases:

| Date | Suppressed REENTRY | Rank | Block | Funded symbols |
| --- | --- | ---: | --- | --- |
| 2022-10-20 | 76470 | 9 | `insufficient_prior_exit_context` | 17570 rank 17; 69930 rank 42 |
| 2022-10-24 | 76470 | 6 | `insufficient_prior_exit_context` | 66630 rank 23; 79220 rank 35; 66330 rank 24; 62270 rank 32 |
| 2022-10-25 | 76470 | 6 | `insufficient_prior_exit_context` | 69730 rank 34; 21950 rank 40 |
| 2022-10-26 | 76470 | 5 | `insufficient_prior_exit_context` | 58200 rank 26 |
| 2022-10-27 | 76470 | 4 | `insufficient_prior_exit_context` | 60480 rank 24; 27210 rank 18; 65790 rank 19 |

## Mechanical Accumulation Test

`TIME_ACCUMULATING_REENTRY_UNIVERSE_EROSION_CONFIRMED = YES`

Evidence:

```text
more completed trading history
-> ever-bought symbols rise from 7 to 579
-> prior-owned currently-flat symbols rise from 0 to 575
-> REENTRY share rises from 15.7% in Oct 2022 to >60% in Q2 2023 and >70% in later windows
-> canonical REENTRY fills remain zero in the pre-CW comparable window
-> effective ordinary BUY_NEW/ADD opportunity competition becomes increasingly shaped by prior-ownership lineage
```

The effect is mechanical: every full exit expands the future population that can be routed into the stricter REENTRY branch.

## Structural Materiality

`REENTRY_SUPPRESSION_PLATEAU_MATERIALITY = MAJOR_CONTRIBUTOR`

Basis:

- timing: REENTRY acceleration begins before and during the April growth break;
- scale: REENTRY share rises to `58.9-63.0%` in April-June 2023;
- conversion: no canonical REENTRY PC/fill conversion in the pre-CW comparable window;
- substitution: many PIT-visible suppressed REENTRY rows coexist with funded NEW/ADD elsewhere;
- CN/CW high-confidence release population: `25` restored-context recovery PASS episodes, proving the zero-fill outcome was not semantically necessary.

It is not classified as `PRIMARY` because CH/CI identified other material causes: weaker market follow-through, starter replacement churn, winner engine decay, ADD suppression, and marginal-capital semantic gaps.

## Plateau Cause Decomposition Updated

`PLATEAU_CAUSE_DECOMPOSITION_UPDATED`:

| Cause | Prior status | CX update |
| --- | --- | --- |
| weaker market follow-through | material | preserved |
| starter replacement churn | primary/major in CH | preserved |
| winner engine decay | primary/major in CH | preserved |
| ADD suppression | material | preserved |
| marginal-capital semantic gap | material | preserved |
| portfolio-growth universe expansion | material | preserved |
| REENTRY suppression accumulation | material from CP/CT | upgraded to `MAJOR_CONTRIBUTOR` for long-horizon opportunity-universe erosion |

REENTRY suppression changes the ranking by becoming a major structural contributor, but it does not replace the winner-capitalization and starter-churn explanation.

## Early vs Late Structural Comparison

Early period: `2022-10-03` through `2023-03-31`.

Later period: `2023-04-03` through `2024-06-07`.

| Metric | Early | Later |
| --- | ---: | ---: |
| candidates | 6100 | 16950 |
| REENTRY rows | 1938 | 9338 |
| REENTRY share | 31.8% | 55.1% overall; many later months >70% |
| prior-owned flat by period end | 180 | 575 |
| canonical REENTRY fills | 0 | 0 by source decision type |
| dominant capital behavior | strong Jan-Mar winner acceleration plus NEW/limited ADD | NEW recycling, weak ADD, REENTRY mostly suppressed |
| equity slope | strong by Jan-Mar, especially March | choppy/low-slope after April |

`EARLY_VS_LATE_STRUCTURAL_COMPARISON = REENTRY_BURDEN_AND_PRIOR_OWNED_FLAT_UNIVERSE_MUCH_HIGHER_LATER_WHILE_EQUITY_SLOPE_WEAKENS`

## Post-CW Early Structural Difference

Post-CW reference run coverage is early only: through `2022-10-14`.

`POST_CW_EARLY_STRUCTURAL_DIFFERENCE = LIMITED_EARLY_EVIDENCE_AVAILABLE`

Observed difference:

- Pre-CW same dates show REENTRY rows but no `PASS` REENTRY in the early final PC surface.
- Post-CW through `2022-10-14` shows early REENTRY `PASS` rows with zero target on some dates, e.g. 33700 / 41650 / 93600, proving the recovered/reworked residual contract is active in actual early artifacts.
- No plateau-period comparison is possible yet.

`INSUFFICIENT_POST_CW_HORIZON = YES_FOR_PLATEAU_PERIOD`

## Long-Run CW Validation Metrics

`POST_CW_LONG_RUN_VALIDATION_METRICS`:

- cumulative prior-owned universe;
- prior-owned currently-flat universe;
- REENTRY opportunity share;
- residual REENTRY block rate split by cooldown, repeated churn, prior-cause recovery, HARD_STOP, unknown context, ordinary current BUY authority;
- REENTRY PC participation count and target weight;
- REENTRY plan / fill count by source authority;
- NEW / REENTRY / ADD mix in PC, PS, runtime planning, Pending, and fills;
- Cash / exposure / productive exposure;
- starter churn;
- ADD conversion and winner capitalization;
- high-water-mark recovery;
- rolling equity slope;
- capital substitution cases where CW-released REENTRY competes with weaker NEW/ADD;
- CK invariant: blocked REENTRY cannot silently relabel to BUY_NEW.

## Required Final Answers

1. `LATEST_PRE_CW_COMPLETED_DATE_USED`: `2024-06-07` for direct artifact scan; `2023-09-22` preserved for CN comparable strict-prior release count.
2. `LATEST_POST_CW_COMPLETED_DATE_USED`: `2022-10-14`.
3. `FIRST_REENTRY_CANDIDATE_DATE`: `2022-10-05`.
4. `FIRST_REENTRY_CANDIDATE_SYMBOL`: `83060`.
5. `FIRST_ANY_REENTRY_BLOCK_DATE`: `2022-10-05`.
6. `FIRST_LEGITIMATE_RESIDUAL_REENTRY_BLOCK_DATE`: `2022-10-05`.
7. `FIRST_LEGACY_REENTRY_SUPPRESSION_DATE`: `2022-10-11`.
8. `FIRST_LEGACY_REENTRY_SUPPRESSION_SYMBOL`: `89180`.
9. `FIRST_LEGACY_REENTRY_SUPPRESSION_REASON`: `reentry_opportunity_not_requalified`.
10. `FIRST_MATERIAL_CAPITAL_IMPACT_DATE`: `2022-10-12`.
11. `DAILY_CUMULATIVE_PRIOR_OWNED_SERIES`: recalculated; representative CSV segments included above.
12. `DAILY_REENTRY_FUNNEL_SERIES`: recalculated from PC/runtime/fill artifacts; monthly and representative daily segments included.
13. `MONTHLY_REENTRY_SUPPRESSION_SERIES`: included above.
14. `REENTRY_OPPORTUNITY_SHARE_BY_PERIOD`: Q4 2022 `24.0%`, Q1 2023 `39.8%`, Q2 2023 `60.8%`, Q3 2023 `55.7%`, Q4 2023 `74.6%`, Q1 2024 `65.2%`, Q2 2024 partial `75.3%`.
15. `REENTRY_SUPPRESSION_ACCELERATION_WINDOW`: `2023-04-03 through 2023-06-30`.
16. `EQUITY_GROWTH_REGIME_WINDOWS`: early mild growth, Jan-Mar strongest acceleration, Apr 10-28 break, May-Aug low-slope plateau, Sep 2023-Jun 2024 choppy low-slope.
17. `REENTRY_SUPPRESSION_VS_GROWTH_DECELERATION_ALIGNMENT`: `COINCIDES_WITH_EARLY_PRECEDENCE`.
18. `POST_APRIL_REENTRY_STATE`: prior-owned flat `186 -> 208`, REENTRY rows `439`, legacy blocks `407`, canonical REENTRY fills `0` in `2023-04-10` through `2023-04-28`.
19. `CW_CONTRACT_WOULD_RELEASE_COUNT_PRE_CW_RUN`: `25` CN restored-context recovery PASS episodes through `2023-09-22`.
20. `NEW_VS_CW_ELIGIBLE_SUPPRESSED_REENTRY_PIT_COMPARISON`: suppressed REENTRY often had better decision-time rank/score than funded NEW in representative substitution cases; exact high-confidence CW release set remains CN's `25` episodes.
21. `LEGACY_REENTRY_TO_WEAKER_NEW_SUBSTITUTION_CASE_COUNT`: `300` direct PIT substitution surfaces; `25` high-confidence CN/CW release episodes.
22. `TIME_ACCUMULATING_REENTRY_UNIVERSE_EROSION_CONFIRMED`: `YES`.
23. `REENTRY_SUPPRESSION_PLATEAU_MATERIALITY`: `MAJOR_CONTRIBUTOR`.
24. `PLATEAU_CAUSE_DECOMPOSITION_UPDATED`: REENTRY suppression upgraded to major contributor; other CH/CI causes preserved.
25. `EARLY_VS_LATE_STRUCTURAL_COMPARISON`: prior-owned flat and REENTRY share materially higher later; equity slope weaker later.
26. `POST_CW_EARLY_STRUCTURAL_DIFFERENCE`: early structural difference visible, plateau horizon insufficient.
27. `POST_CW_LONG_RUN_VALIDATION_METRICS`: listed above.
28. `OUTCOME_DATA_USED_TO_CLASSIFY_REENTRY_OPPORTUNITIES`: `NO`.
29. `PRODUCTION_CHANGE_JUSTIFIED`: `NO_FROM_CX_DIAGNOSTIC_ONLY`.
30. `PRODUCTION_CHANGE_EXECUTED`: `NO`.
31. `TARGET_RUN_MUTATED`: `NO`.
32. `NEXT_RECOMMENDED_STEP`: continue the user-operated post-CW Historical run until at least the `2023-04-10` through `2023-06-30` acceleration/plateau window, then run a READ-ONLY post-CW validation comparing the metrics defined above.
33. `FINAL_JUDGMENT`: `PHASE32_CX_REENTRY_SUPPRESSION_ACCUMULATION_CONFIRMED_MAJOR_CONTRIBUTOR_TO_LONG_HORIZON_GROWTH_DECAY_POST_CW_LONG_RUN_VALIDATION_REQUIRED`

## Final Judgment

`PHASE32_CX_REENTRY_SUPPRESSION_ACCUMULATION_CONFIRMED_MAJOR_CONTRIBUTOR_TO_LONG_HORIZON_GROWTH_DECAY_POST_CW_LONG_RUN_VALIDATION_REQUIRED`
