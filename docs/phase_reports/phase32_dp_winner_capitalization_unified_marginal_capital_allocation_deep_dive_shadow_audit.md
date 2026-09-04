# Phase32-DP — Winner Capitalization / Unified Marginal Capital Allocation Deep-Dive READ-ONLY + SHADOW Design Audit

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260902T060955933565Z`
- Primary evidence window: `2022-10-03` through latest completed date observed during this audit, `2023-11-06`
- Completed business days observed: 270
- Run state during read-only inspection: `RUNNING`, continuation observed at `2023-11-07:submit`
- Current source identity: `a56f2bc26105eb14fd67322b7cd53c0d6ef1b1bd`
- Production change executed: NO
- Target run mutated: NO
- Historical PnL use: diagnostic/materiality only. No thresholds, weights, formula, rank rule, action bonus, exposure target, or max-position value was selected from Historical PnL.

Mandatory references read: Phase32-DO, Phase32-CY, Phase32-CZ, Phase32-CW, Phase32-CX, Phase32-DG, `high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`, Runtime Architecture v2 capital competition notes, Strategy Intelligence migration contract, and Strategy decision quality / continuation quality contract.

## Executive Finding

The remaining winner-capitalization bottleneck is confirmed, but it is not a broken BUY_ADD execution path and not evidence that ADD should receive fixed preference. PM ADD intent is frequent and PC can produce valid BUY_ADD fills. The loss occurs because the current marginal-capital machinery is still a partial/compatibility authority: it ranks eligible incremental buy rows by coarse quality class, rank, construction priority, and feasibility artifacts, but it does not yet estimate the value of the next deployable yen or next executable lot on one high-resolution action-neutral basis across BUY_NEW, semantic REENTRY, BUY_ADD, and CASH.

The correct next step is SHADOW implementation/design of a unified marginal capital contract inside Portfolio Construction's Capital Value Authority. Production promotion is conditional on future shadow evidence, not justified directly by low ADD counts.

## ADD Funnel

PM ADD-origin funnel, latest observed window:

| Boundary | Count |
|---|---:|
| PM ADD decisions | 307 |
| Same-symbol/same-campaign PC considered | 307 |
| PC ADD candidate rows | 152 |
| BQ/Entry not hard-blocked | 186 |
| Positive accepted incremental weight | 22 |
| Lot-aware positive ADD | 15 |
| BUY_ADD fills | 11 |

The gap from PM ADD to PC ADD candidate means PM ADD context is visible to PC, but only part of the PM ADD universe becomes an ADD capital competitor. The later drop from 22 positive accepted incremental weights to 15 lot-aware positives and 11 fills is normal executable-discrete narrowing plus a small same-day non-fill gap; the material bottleneck is earlier, where continuing winners fail to win or retain positive incremental authority.

`ADD_FUNNEL_RECONSTRUCTED = YES`

## First Decisive Blockers

First decisive blocker profile for PM ADD rows that did not become BUY_ADD fills:

| First blocker | Count | Materiality proxy |
|---|---:|---:|
| Concentration / cap / headroom | 164 | 17,144,320 |
| BQ or continuation caution | 81 | 8,540,840 |
| Entry caution / `NO_ADD` | 39 | 4,271,410 |
| Weight positive but no lot-aware executable ADD | 7 | 300,153 |
| Lot-positive but no same-day BUY_ADD fill | 4 | 368,327 |
| No positive incremental authority | 1 | 110,740 |

Materiality proxy uses available one-lot notional, continuous target notional, requested incremental weight times equity, or PM market value where the more specific field was absent. It is diagnostic only.

`ADD_FIRST_DECISIVE_BLOCKER_PROFILE = CONCENTRATION_CAP_DOMINANT_THEN_BQ_ENTRY_CAUTION; LOT_AND_POST_PS_SECONDARY`

## Eligibility vs Funding

| Decomposition | Count |
|---|---:|
| A. Not eligible at all | 284 |
| B. Eligible but not funded / no positive authority | 1 |
| C. Funded partially or weight-positive but no executable/fill | 11 |
| D. Funded/executed BUY_ADD | 11 |

This distinction matters. Most ADD loss is not "eligible ADD loses to NEW by clean marginal comparison." Most ADD intent never reaches a strong, executable, positive ADD capital claim because continuation/BQ/Entry/cap/headroom constraints compress or remove the ADD increment before final funding.

`ADD_ELIGIBILITY_VS_FUNDING_DECOMPOSITION = A_NOT_ELIGIBLE_284, B_ELIGIBLE_NOT_FUNDED_1, C_PARTIAL_OR_NO_EXECUTABLE_11, D_EXECUTED_11`

## Current Unified Marginal Capital Authority

Architecture says current PC already owns scarce-capital competition among `NEW_BUY`, `BUY_ADD`, and Cash/optionality. Runtime consumes the result and must not re-rank or re-size. Current source confirms:

- `marginal_capital_value.py` publishes `MARGINAL_CAPITAL_VALUE_AUTHORITY`.
- Current ordering uses `marginal_capital_value_class`, opportunity quality class, rank, stable order, and source evidence.
- The authority explicitly records `buy_add_unconditional_priority = False` and `buy_new_unconditional_priority = False`.
- PC's `build_capital_competition_framework` emits competitors, cash competitor evidence, canonical deployment set, multi-allocation shadow, and canonical ADD marginal competition artifacts.
- PC authority records `cash_economic_binding_active = False`, `multi_allocation_shadow_authoritative_consumer_count = 0`, and an ADD staged authority binding.

Action-type comparison status:

| Action | Inputs consumed | Current representation | Gap |
|---|---|---|---|
| BUY_NEW | rank/score, BQ, Entry, selection quality, market/risk context | quality class + rank + weight/lot feasibility | Not calibrated to marginal JPY value or opportunity cost against existing winners |
| REENTRY | prior campaign context, recovery, cooldown/churn, renewed current evidence, BQ/Entry | semantic REENTRY eligibility, then largely BUY_NEW-like funding path | Semantic lifecycle survives, but fill label remains BUY_NEW and value is not separate marginal-JPY REENTRY value |
| BUY_ADD | PM ADD, continuation, SI ADD worthiness, no-loss averaging, cap/headroom, BQ/Entry | ADD competitor + staged authority + accepted incremental weight | Strong HOLD / strong ADD / next-lot opportunity value still coarse and often collapses into caution/cap buckets |
| CASH | reserve, no valid competitor, lot residual, concentration, risk pacing | cash competitor evidence and final cash optionality | Cash is valid, but not expressed as the same expected marginal value unit as securities |

`CURRENT_UNIFIED_MARGINAL_CAPITAL_AUTHORITY_STATUS = PARTIAL`

## Marginal-JPY Comparability

The current system does not consistently answer: "What is the value of the next deployable yen across NEW / REENTRY / ADD / CASH?"

It does answer a narrower question: among rows that have survived eligibility and sizing, which coarse class/rank/feasibility result should receive scarce incremental allocation? That is useful and canonical, but it is not a high-resolution marginal value unit.

Incomparable semantics:

- BUY_NEW rank/score is not calibrated to expected incremental yen value.
- REENTRY has lifecycle recovery semantics, but its accepted buy path is still represented as BUY_NEW-like capital rather than a fully separate marginal REENTRY unit.
- ADD consumes campaign continuation and PM intent, but next-lot desirability is not preserved separately from cap/headroom/BQ/Entry compression.
- Cash optionality is valid but not normalized to the same opportunity-value unit.
- Lot feasibility can collapse high-value-but-infeasible into no allocation, rather than preserving `HIGH_VALUE + INFEASIBLE`.

`MARGINAL_JPY_COMPARABILITY = PARTIAL`

## Direct Competition Cases

Representative NEW vs ADD cases:

| Date | ADD candidate | ADD evidence | ADD accepted / lot | Competing funded NEW/REENTRY | Competing weight | Decision-time reading |
|---|---|---|---:|---|---:|---|
| 2022-10-05 | 94340 | BQ full, Entry `ADD_REDUCED_ONLY` | 0 / 0 | 99840 BUY_NEW | 0.127617 | ADD had continuation evidence but no positive ADD authority; residual cash/lot remained |
| 2022-10-06 | 94340 | BQ full, Entry `ADD_REDUCED_ONLY` | 0.035714 / 0.013786 | 45750 BUY_NEW | 0.064391 | ADD and NEW both funded; ADD was allowed but smaller |
| 2022-10-11 | 94340 | BQ full, Entry `ADD_REDUCED_ONLY` | 0.029600 / 0.013644 | 76470 BUY_NEW | 0.029600 | ADD had authority; final residual reported `NO_VALID_COMPETITOR` after allocation |
| 2022-10-13 | 94340 | BQ reduced, Entry `ADD_REDUCED_ONLY` | 0.026429 / 0.014015 | 78780 BUY_NEW | 0.205687 | NEW received much larger starter allocation under coarse class/lot framework |
| 2022-10-25 | 94320 | BQ reduced, Entry `ADD_REDUCED_ONLY` | 0 / 0 | 69730 BUY_NEW | 0.144203 | ADD did not retain positive increment; NEW received deployable capital |

Representative REENTRY vs ADD cases:

| Date | ADD candidate | ADD accepted / lot | REENTRY candidate | REENTRY state | REENTRY lot weight | Decision-time reading |
|---|---|---:|---|---|---:|---|
| 2022-10-11 | 94340 | 0.029600 / 0.013644 | 41650 | `REENTRY_ELIGIBLE` | 0 | ADD was executable; REENTRY eligible but not funded |
| 2022-10-19 | 94320 | 0 / 0 | 41650 | `REENTRY_ELIGIBLE` | 0.068175 | REENTRY had a mature BUY_NEW-like funding path; ADD lost all positive increment |
| 2022-10-24 | 94320 | 0 / 0 | 41650 | `REENTRY_ELIGIBLE` | 0.074878 | Same pattern: REENTRY can win through entry path while ADD remains zero |
| 2022-11-01 | 94320 | 0.032258 / 0.015233 | 66330 | `REENTRY_ELIGIBLE` | 0.030934 | Both lifecycle types received capital |
| 2022-11-21 | 99840 | 0.032258 / 0 | 83060 | `REENTRY_ELIGIBLE` | 0 | ADD had weight but no executable lot |

Representative Cash vs ADD cases:

| Date | ADD candidate | ADD accepted / lot | Cash reason | Available incremental budget | Reading |
|---|---|---:|---|---:|---|
| 2022-10-05 | 94340 | 0 / 0 | `UNAVOIDABLE_LOT_RESIDUAL` | 0.321590 | Cash remained because ADD did not become deployable despite full BQ |
| 2022-10-06 | 94340 | 0.035714 / 0.013786 | `UNAVOIDABLE_LOT_RESIDUAL` | 0.208353 | ADD funded but residual cash remained due lot/discrete allocation |
| 2022-10-11 | 94340 | 0.029600 / 0.013644 | `NO_VALID_COMPETITOR` | 0.072287 | After allocations, no remaining deployable competitor |
| 2022-10-24 | 94320 | 0 / 0 | `UNAVOIDABLE_LOT_RESIDUAL` | 0.458534 | ADD continuation evidence existed, but no positive executable ADD |
| 2022-10-26 | 94320 | 0 / 0 | `UNAVOIDABLE_LOT_RESIDUAL` | 0.237182 | Cash/lot residual remained while ADD was not capitalized |

`NEW_VS_ADD_DIRECT_COMPETITION_CASES = PRESENT; NEW_AND_REENTRY_OFTEN_USE_MATURE_ENTRY_PATH_WHILE_ADD_INCREMENT_IS_COMPRESSED_OR_ZEROED`

`REENTRY_VS_ADD_DIRECT_COMPETITION_CASES = PRESENT; REENTRY_BENEFITS_FROM_BUY_NEW_LIKE_FUNDING_ONCE_REQUALIFIED`

`CASH_VS_ADD_COMPETITION_CASES = PRESENT; CASH_WINS_OR_REMAINS_PRIMARILY_AS_LOT_RESIDUAL_RESERVE_NO_VALID_COMPETITOR_AFTER_ADD_COMPRESSION`

## Starter Proliferation

Semantic funded buy view through `2023-11-06`:

| Semantic type | Fills | Notional |
|---|---:|---:|
| BUY_NEW | 384 | 30,458,620 |
| REENTRY | 82 | 6,049,210 |
| BUY_ADD | 11 | 211,930 |

Campaign graduation at latest observed date:

- Campaigns with a buy event: 355
- Closed campaigns with no ADD: 341
- Campaigns reaching 2x starter quantity: 3
- Campaigns reaching 3x starter quantity: 1
- Campaigns reaching 5x starter quantity: 0
- Days with ADD candidate evidence: 113
- On ADD-candidate days, average open positions: 11.5
- On ADD-candidate days, average starter-like open positions: 10.2; max starter-like open positions: 15

Open campaigns at `2023-11-06` include one clear graduation case:

- `94320 / pc-7c5bd9294d48b016-94320-0001`: starter 200 shares, max/current 700 shares, 5 ADD fills, 3.5x starter quantity.

Most other open positions remained at starter quantity or near starter quantity.

`STARTER_PROLIFERATION_STATUS = MIXED`

This is not pure over-fragmentation. Broad starter discovery coexists with controlled drawdowns and post-April growth. The weakness is that few discovered campaigns graduate into larger allocations.

## Campaign Graduation Authority

Existing implicit path:

```text
PM ADD intent
-> Strategy Intelligence continuation / ADD worthiness
-> BQ / Entry
-> PC ADD competitor
-> accepted incremental weight
-> Position Sizing lot-aware quantity
-> Runtime BUY_ADD
```

The path exists and can succeed, but the graduation authority is not a first-class lifecycle state with an action-neutral marginal value object. It is implicit across PM ADD, SI evidence, BQ/Entry, PC competition, and lot-aware sizing.

`CAMPAIGN_GRADUATION_AUTHORITY_STATUS = IMPLICIT`

## 94320 Positive Control

Successful graduation case: `94320 / pc-7c5bd9294d48b016-94320-0001`

BUY_ADD fills:

| Date | BQ | Entry | Accepted / lot weight | Pre-ADD qty | Campaign age evidence | Notional |
|---|---|---|---:|---:|---:|---:|
| 2023-01-31 | reduced | `ADD_REDUCED_ONLY` | 0.018547 / 0.012646 | 200 | 8 | 15,680 |
| 2023-02-13 | reduced | `ADD_REDUCED_ONLY` | 0.033333 / 0.012279 | 300 | 21 | 15,370 |
| 2023-02-22 | full | `ADD_REDUCED_ONLY` | 0.040000 / 0.013141 | 400 | 30 | 15,860 |
| 2023-02-24 | reduced | `ADD_REDUCED_ONLY` | 0.033333 / 0.013302 | 500 | 32 | 15,760 |
| 2023-03-15 | reduced | `ADD_REDUCED_ONLY` | 0.029412 / 0.012981 | 600 | 51 | 15,840 |

Success factors visible at decision time:

- PM reason repeatedly `strong_trend_continuation`, `opportunity_rank_still_high`, `no_loss_averaging`.
- Entry allowed reduced ADD instead of hard `NO_ADD`.
- BQ was at least reduced and sometimes full.
- Lot size was small enough that the accepted incremental weight translated to an executable 100-share increment.
- Campaign headroom existed often enough before cap/concentration stopped further growth.

The same campaign also had 30 PM ADD days without ADD fills, split between BQ/Entry caution and cap/concentration. This proves the path is functional but narrow, not unconditional.

`94320_GRADUATION_SUCCESS_FACTORS = PM_STRONG_TREND_AND_RANK + REDUCED_OR_FULL_BQ + ADD_REDUCED_ONLY_ENTRY + SMALL_EXECUTABLE_LOT + AVAILABLE_HEADROOM`

## Failed Graduation Controls

Representative controls with repeated PM ADD but no repeated ADD fill:

| Symbol / campaign | PM ADD no-fill days | Main blockers | Last observed PM ADD no-fill state |
|---|---:|---|---|
| 94320 / `pc-7c5bd9294d48b016-94320-0001` | 30 | BQ/Entry caution 13, cap/concentration 17 | 600 shares, 7.83% weight, `BUY_WAIT`, `ADD_REDUCED_ONLY` |
| 94340 / `pc-8d0b3d71adb1e835-94340-0001` | 14 | cap/concentration 9, BQ/Entry caution 5 | 300 shares, 2.78% weight, BQ full, `ADD_REDUCED_ONLY` |
| 83060 / `pc-090162015342d58a-83060-0001` | 12 | BQ/Entry caution 5, cap/concentration 7 | 100 shares, 7.53% weight, BQ reduced, `ADD_REDUCED_ONLY` |
| 43880 / `pc-77b04ae8a6085bfd-43880-0001` | 12 | cap/concentration 11, BQ/Entry caution 1 | 100 shares, 8.41% weight, BQ reduced, `ADD_REDUCED_ONLY` |
| 99840 / `pc-7c3e2f7c66f69bc8-99840-0001` | 8 | BQ/Entry caution 3, cap/concentration 5 | 100 shares, 9.44% weight, BQ full, `ADD_REDUCED_ONLY` |
| 40520 / `pc-3551cfa510023cea-40520-0001` | 7 | cap/concentration 4, BQ/Entry caution 3 | 100 shares, 8.05% weight, `BUY_WAIT`, `ADD_REDUCED_ONLY` |

These are not symbol-specific Production rules. They show the repeated shape: PM wants ADD, continuation evidence often remains supportive enough to hold, but ADD's next executable lot does not become a durable first-class capital claim.

`FAILED_GRADUATION_CASES = MULTI_SYMBOL_CONTROLS_SHOW_ADD_INTENT_SURVIVES_BUT_NEXT_LOT_AUTHORITY_IS_COMPRESSED_BY_BQ_ENTRY_AND_CAP_HEADROOM`

## BULL / RECOVERY Deployment Pressure

June through September:

| Semantic type | Funded count | Notional | Avg rank | Avg BQ score | Avg confidence |
|---|---:|---:|---:|---:|---:|
| BUY_NEW | 125 | 10,777,080 | 27.8 | 0.604 | 0.464 |
| REENTRY | 32 | 2,846,420 | 22.7 | 0.647 | 0.566 |
| BUY_ADD | 0 | 0 | n/a | n/a | n/a |

Funded BUY_NEW monthly quality:

| Month | BUY_NEW fills | Avg rank | Median rank | Avg BQ score | Avg position count | Avg exposure |
|---|---:|---:|---:|---:|---:|---:|
| 2023-06 | 30 | 27.4 | 27.5 | 0.619 | 14.2 | 87.2% |
| 2023-07 | 30 | 28.4 | 30.5 | 0.587 | 15.9 | 85.8% |
| 2023-08 | 30 | 27.5 | 27.5 | 0.595 | 14.0 | 76.6% |
| 2023-09 | 35 | 27.9 | 30.0 | 0.612 | 16.1 | 80.0% |

`BULL_CAPITAL_DEPLOYMENT_PRESSURE_CONFIRMED = PARTIAL`

There is real broad deployment in BULL/RECOVERY months, but it is not merely cash-forcing: funded BUY_NEW quality does not collapse month by month, and semantic REENTRY participates with better average rank/quality than BUY_NEW. The concerning link is narrower: high position counts and high exposure coexist with zero BUY_ADD fills across June-September.

`MARGINAL_BUY_NEW_QUALITY_DILUTION = PARTIAL`

October/November show clearer softening in funded BUY_NEW average rank/quality, but June-September do not prove severe marginal NEW dilution. Evidence supports a partial dilution/fragmentation concern, not a Production rule to penalize NEW.

`EXCESSIVE_BREADTH_SUPPRESSES_WINNER_CAPITALIZATION = PARTIAL`

The capital-competition link is present through cap/concentration and cash/opportunity artifacts, but not strong enough to say breadth alone causes ADD starvation. The more precise bottleneck is missing high-resolution marginal capital comparison plus action-specific lifecycle compression.

## SHADOW Contract Design

`UNIFIED_MARGINAL_CAPITAL_SHADOW_CONTRACT`

Owner:

```text
Portfolio Construction / Capital Value Authority
```

Question answered:

```text
For the next executable capital increment, what is the best marginal use of scarce portfolio capital?
```

Competitor rows:

- `BUY_NEW_NEXT_LOT`
- `REENTRY_NEXT_LOT`
- `BUY_ADD_NEXT_LOT`
- `CASH_OPTIONALITY`

Required row identity:

- run id
- business date
- symbol if security competitor
- action type
- campaign id for ADD/REENTRY where applicable
- source PM decision id for ADD
- source candidate/opportunity id for NEW/REENTRY
- feature-date / PIT proof
- current position/cash/exposure snapshot hash

Decision-time evidence families:

- opportunity/rank/score evidence
- BQ action and quality score
- Entry action/state
- continuation quality and lifecycle state
- PM ADD intent and reason lineage for ADD
- prior EXIT/recovery/churn evidence for REENTRY
- downside/risk and market context
- confidence/evidence completeness
- current weight, headroom, concentration
- liquidity, unit size, minimum tick, lot granularity
- incremental exposure and cash reserve impact
- cash optionality/risk reserve evidence

Required separation:

- marginal desirability
- evidence completeness
- execution feasibility
- portfolio/risk cost
- cash optionality comparison
- final arbitration

The design should preserve states like:

```text
HIGH_VALUE + INFEASIBLE_DUE_TO_LOT
HIGH_VALUE + BLOCKED_BY_CONCENTRATION
MEDIUM_VALUE + FEASIBLE
CASH_WINS_DUE_TO_RISK_OPTIONALITY
```

It must not collapse every infeasible ADD to low value, because that hides whether the system is missing capital scale/lot/cap headroom versus correctly preferring another opportunity.

Non-requirements:

- no scalar score required
- no fixed ADD bonus
- no BUY_NEW penalty
- no fixed campaign-age bonus
- no forced exposure target
- no PnL-fitted threshold

Validation path:

1. Produce SHADOW rows for all four competitor types without changing Production allocation.
2. Compare shadow ordering with existing Production winners.
3. Explain divergences using PIT evidence only.
4. Track whether shadow high-value ADD rows repeatedly lose because of true feasibility/cap limits or because Production lacks comparable marginal units.
5. Promote only after no-hindsight acceptance and focused regression of G129, REENTRY, BQ, Entry, cash, and lot authority.

`ACTION_TYPE_FIXED_PREFERENCE_INTRODUCED = NO`

`INVESTMENT_PHILOSOPHY_ALIGNMENT = PASS`

The contract allows NEW, REENTRY, ADD, or CASH to win if it has the strongest decision-time marginal value. It explicitly rejects action-label favoritism.

## Ownership and Model 2

`CANONICAL_MARGINAL_CAPITAL_OWNER = PORTFOLIO_CONSTRUCTION_CAPITAL_VALUE_AUTHORITY`

Candidate, BQ, Entry, PM, Strategy Intelligence, Market Quality, Risk Pacing, Safety, and Position Sizing remain evidence or constraint owners. Runtime must not re-decide the capital ranking.

`MODEL2_RELATIONSHIP = INDEPENDENT_BUT_OVERLAPPING_RESEARCH; KEEP_SEPARATE_AND_ON_HOLD`

Unified marginal allocation can reuse evidence families Model 2 may later consume, but it does not require enabling Model 2 and should not import Model 2 behavior.

## Production Necessity and Phase32 Implication

`PRODUCTION_REPAIR_REQUIRED = CONDITIONAL`

There is no correctness defect requiring immediate Production repair: BUY_ADD authority is functional, fail-closed behavior is preserved, and no action label receives automatic priority. However, the performance bottleneck is material enough to justify the next phase as SHADOW implementation, not more READ-ONLY characterization alone.

`PHASE32_CLOSURE_IMPLICATION = CARRY_FORWARD_PERFORMANCE_IMPROVEMENT; NOT_A_CORRECTNESS_BLOCKER; DO_NOT_CLOSE_PHASE32_AUTOMATICALLY`

## Required Final Answers

1. `ADD_FUNNEL_RECONSTRUCTED = YES`
2. `ADD_FIRST_DECISIVE_BLOCKER_PROFILE = CONCENTRATION_CAP_DOMINANT_THEN_BQ_ENTRY_CAUTION; LOT_AND_POST_PS_SECONDARY`
3. `ADD_ELIGIBILITY_VS_FUNDING_DECOMPOSITION = A_NOT_ELIGIBLE_284, B_ELIGIBLE_NOT_FUNDED_1, C_PARTIAL_OR_NO_EXECUTABLE_11, D_EXECUTED_11`
4. `CURRENT_UNIFIED_MARGINAL_CAPITAL_AUTHORITY_STATUS = PARTIAL`
5. `MARGINAL_JPY_COMPARABILITY = PARTIAL`
6. `NEW_VS_ADD_DIRECT_COMPETITION_CASES = PRESENT_WITH_ADD_OFTEN_COMPRESSED_TO_ZERO_OR_SMALL_INCREMENT_BEFORE_FINAL_FUNDING`
7. `REENTRY_VS_ADD_DIRECT_COMPETITION_CASES = PRESENT_WITH_REENTRY_USING_MATURE_BUY_NEW_LIKE_FUNDING_AFTER_REQUALIFICATION`
8. `CASH_VS_ADD_COMPETITION_CASES = PRESENT_WITH_CASH_RESIDUAL_RESERVE_NO_VALID_COMPETITOR_AFTER_ADD_COMPRESSION`
9. `STARTER_PROLIFERATION_STATUS = MIXED`
10. `CAMPAIGN_GRADUATION_AUTHORITY_STATUS = IMPLICIT`
11. `94320_GRADUATION_SUCCESS_FACTORS = PM_STRONG_TREND_AND_RANK + REDUCED_OR_FULL_BQ + ADD_REDUCED_ONLY_ENTRY + SMALL_EXECUTABLE_LOT + AVAILABLE_HEADROOM`
12. `FAILED_GRADUATION_CASES = 94320,94340,83060,43880,99840,40520_CONTROLS_SHOW_ADD_INTENT_SURVIVES_BUT_NEXT_LOT_AUTHORITY_COMPRESSES`
13. `BULL_CAPITAL_DEPLOYMENT_PRESSURE_CONFIRMED = PARTIAL`
14. `MARGINAL_BUY_NEW_QUALITY_DILUTION = PARTIAL`
15. `EXCESSIVE_BREADTH_SUPPRESSES_WINNER_CAPITALIZATION = PARTIAL`
16. `UNIFIED_MARGINAL_CAPITAL_SHADOW_CONTRACT = PORTFOLIO_CONSTRUCTION_OWNED_ACTION_NEUTRAL_NEXT_EXECUTABLE_INCREMENT_COMPARISON`
17. `ACTION_TYPE_FIXED_PREFERENCE_INTRODUCED = NO`
18. `INVESTMENT_PHILOSOPHY_ALIGNMENT = PASS`
19. `CANONICAL_MARGINAL_CAPITAL_OWNER = PORTFOLIO_CONSTRUCTION_CAPITAL_VALUE_AUTHORITY`
20. `MODEL2_RELATIONSHIP = INDEPENDENT_BUT_OVERLAPPING_RESEARCH_KEEP_SEPARATE`
21. `PRODUCTION_REPAIR_REQUIRED = CONDITIONAL`
22. `HISTORICAL_PNL_USED_FOR_PARAMETER_SELECTION = NO`
23. `PHASE32_CLOSURE_IMPLICATION = CARRY_FORWARD_PERFORMANCE_IMPROVEMENT_NOT_CORRECTNESS_BLOCKER`
24. `PRODUCTION_CHANGE_EXECUTED = NO`
25. `TARGET_RUN_MUTATED = NO`
26. `NEXT_RECOMMENDED_STEP = Implement SHADOW-only unified marginal capital authority rows inside Portfolio Construction, then audit divergences before any Production promotion.`
27. `FINAL_JUDGMENT = PHASE32_DP_WINNER_CAPITALIZATION_BOTTLENECK_CONFIRMED_UNIFIED_MARGINAL_CAPITAL_SHADOW_DESIGN_REQUIRED_NO_PRODUCTION_CHANGE`

## Final Judgment

`PHASE32_DP_WINNER_CAPITALIZATION_BOTTLENECK_CONFIRMED_UNIFIED_MARGINAL_CAPITAL_SHADOW_DESIGN_REQUIRED_NO_PRODUCTION_CHANGE`
