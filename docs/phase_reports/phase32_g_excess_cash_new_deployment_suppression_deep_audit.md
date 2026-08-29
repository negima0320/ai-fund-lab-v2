# Phase32-G - Excess Cash / NEW Deployment Suppression Deep Audit

## Executive Summary

Phase32-G audited why the plateau, especially late plateau BULL dates, often
kept high Cash despite visible NEW candidate supply.  This was read-only: no
production code, configuration, thresholds, Risk Pacing, Cash reserve, NEW
quality gates, PC/MCC, PM, PS, Runtime, High-Resolution Value, or Portfolio
Rotation behavior was changed.

Main finding: high-Cash BULL days were real and material, but they were not a
simple "no candidates" problem.  In the plateau window, `22` BULL days had
actual cash ratio >= `0.50`.  Those days still averaged `50` BUY-quality
decisions, `30.6` full/reduced candidates, and `22.5` NEW competitors.  The
drop occurred after candidate supply, inside the capital frontier: NEW demand
was usually marginal, Risk Pacing and Market Quality often made Cash
first-class optionality, PC/MCC frequently selected `CASH_OPTIONALITY`, and
Position Sizing / Runtime only consumed the bounded deployment set.

This supports a limitation classification, not a mandatory defect.  The
appropriate next step is a shadow `capital_frontier_cash_new_add_bridge.v1`
trace that joins NEW, ADD, Cash, Risk Pacing, MCC, PS quantity, Runtime, fills,
and final outcome without changing trading behavior.

## High-Cash BULL Day Inventory

Inventory predicate:

```text
regime = BULL
actual cash ratio = available cash / portfolio total equity >= 0.50
window = 2023-05-31 through 2024-02-26
```

`PHASE32_G_HIGH_CASH_BULL_DAYS = 22`

| Date | Cash ratio | Cash | Equity | Positions | Market Quality | Risk Pacing | Full/Reduced candidates | NEW competitors | PC NEW weight | Single capital winner | Authorized Cash weight | Security weight | BUY fills |
| --- | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| 2023-06-28 | 0.562 | 968,750 | 1,722,490 | 6 | SHORT_TERM_NARROWING_WITH_MEDIUM_STRENGTH | CAUTIOUS_DEPLOYMENT | 7/24 | 27 | 0.156250 | CASH_OPTIONALITY | 0.267664 | 0.306765 | 2 |
| 2023-09-27 | 0.593 | 1,102,970 | 1,861,160 | 8 | CONFLICTED_MARKET_STRUCTURE | CAUTIOUS_DEPLOYMENT | 8/29 | 28 | 0.060606 | CASH_OPTIONALITY | 0.538263 | 0.119012 | 2 |
| 2023-11-17 | 0.552 | 1,013,440 | 1,837,260 | 5 | CONFLICTED_MARKET_STRUCTURE | CAUTIOUS_DEPLOYMENT | 8/27 | 27 | 0.031250 | CASH_OPTIONALITY | 0.376498 | 0.175106 | 1 |
| 2024-01-10 | 0.764 | 1,393,100 | 1,824,590 | 4 | HEALTHY_EXPANSION | NORMAL_DEPLOYMENT | 6/23 | 20 | 0.086956 | NEW_BUY | 0.545757 | 0.238310 | 2 |
| 2024-01-11 | 0.685 | 1,248,800 | 1,821,740 | 5 | HEALTHY_EXPANSION | NORMAL_DEPLOYMENT | 6/23 | 25 | 0.000000 | CASH_OPTIONALITY | 0.593286 | 0.148148 | 0 |
| 2024-01-12 | 0.683 | 1,248,800 | 1,828,910 | 5 | HEALTHY_EXPANSION | NORMAL_DEPLOYMENT | 8/27 | 28 | 0.066666 | NEW_BUY | 0.489655 | 0.315934 | 2 |
| 2024-01-15 | 0.601 | 1,107,600 | 1,843,390 | 5 | HEALTHY_EXPANSION | NORMAL_DEPLOYMENT | 4/26 | 24 | 0.000000 | CASH_OPTIONALITY | 0.692474 | 0.000000 | 0 |
| 2024-01-16 | 0.684 | 1,277,600 | 1,867,900 | 4 | CONFLICTED_MARKET_STRUCTURE | CAUTIOUS_DEPLOYMENT | 6/24 | 23 | 0.071060 | CASH_OPTIONALITY | 0.655390 | 0.028588 | 2 |
| 2024-01-17 | 0.625 | 1,169,000 | 1,870,630 | 6 | SHORT_TERM_NARROWING_WITH_MEDIUM_STRENGTH | CAUTIOUS_DEPLOYMENT | 4/24 | 19 | 0.043478 | CASH_OPTIONALITY | 0.723068 | 0.084159 | 1 |
| 2024-01-18 | 0.732 | 1,365,500 | 1,865,800 | 6 | SHORT_TERM_BREADTH_BREAKDOWN | CAUTIOUS_DEPLOYMENT | 4/27 | 18 | 0.047619 | CASH_OPTIONALITY | 0.777977 | 0.035749 | 1 |
| 2024-01-19 | 0.756 | 1,420,900 | 1,880,730 | 5 | CONFLICTED_MARKET_STRUCTURE | CAUTIOUS_DEPLOYMENT | 5/26 | 17 | 0.047619 | CASH_OPTIONALITY | 0.796393 | 0.000000 | 1 |
| 2024-01-22 | 0.760 | 1,417,700 | 1,864,810 | 5 | CONFLICTED_MARKET_STRUCTURE | CAUTIOUS_DEPLOYMENT | 4/34 | 30 | 0.029412 | CASH_OPTIONALITY | 0.654010 | 0.146554 | 1 |
| 2024-01-23 | 0.715 | 1,331,700 | 1,863,070 | 5 | HEALTHY_EXPANSION | NORMAL_DEPLOYMENT | 5/25 | 21 | 0.000000 | CASH_OPTIONALITY | 0.622517 | 0.130434 | 0 |
| 2024-01-24 | 0.720 | 1,331,700 | 1,849,330 | 5 | HEALTHY_EXPANSION | NORMAL_DEPLOYMENT | 4/25 | 22 | 0.041667 | NEW_BUY | 0.804532 | 0.065351 | 2 |
| 2024-01-25 | 0.804 | 1,469,450 | 1,828,750 | 4 | HEALTHY_EXPANSION | NORMAL_DEPLOYMENT | 5/25 | 18 | 0.100000 | NEW_BUY | 0.493719 | 0.355167 | 3 |
| 2024-01-26 | 0.595 | 1,080,920 | 1,817,840 | 6 | HEALTHY_EXPANSION | NORMAL_DEPLOYMENT | 3/17 | 13 | 0.058824 | NEW_BUY | 0.566736 | 0.058824 | 1 |
| 2024-01-29 | 0.583 | 1,052,970 | 1,805,980 | 6 | CONFLICTED_MARKET_STRUCTURE | CAUTIOUS_DEPLOYMENT | 6/25 | 21 | 0.000000 | CASH_OPTIONALITY | 0.581474 | 0.040000 | 0 |
| 2024-01-30 | 0.609 | 1,103,140 | 1,811,380 | 5 | CONFLICTED_MARKET_STRUCTURE | CAUTIOUS_DEPLOYMENT | 7/25 | 22 | 0.000000 | CASH_OPTIONALITY | 0.610292 | 0.038462 | 0 |
| 2024-01-31 | 0.650 | 1,175,340 | 1,809,150 | 4 | HEALTHY_EXPANSION | NORMAL_DEPLOYMENT | 8/28 | 29 | 0.026696 | NEW_BUY | 0.469605 | 0.202108 | 1 |
| 2024-02-01 | 0.570 | 1,037,670 | 1,821,030 | 5 | SHORT_TERM_NARROWING_WITH_MEDIUM_STRENGTH | CAUTIOUS_DEPLOYMENT | 5/19 | 19 | 0.083334 | CASH_OPTIONALITY | 0.543522 | 0.026304 | 2 |
| 2024-02-02 | 0.506 | 921,370 | 1,821,120 | 7 | CONFLICTED_MARKET_STRUCTURE | CAUTIOUS_DEPLOYMENT | 6/23 | 23 | 0.103449 | CASH_OPTIONALITY | 0.349275 | 0.176430 | 3 |
| 2024-02-26 | 0.616 | 1,086,990 | 1,764,320 | 7 | CONFLICTED_MARKET_STRUCTURE | CAUTIOUS_DEPLOYMENT | 5/23 | 21 | 0.000000 | CASH_OPTIONALITY | 0.705032 | 0.041667 | 1 |

High-Cash BULL aggregate:

- Average actual cash ratio: `0.653`
- Average actual cash: `1,196,610`
- Average active positions: `5.4`
- Average full/reduced candidate count: `30.6`
- Average NEW competitor count: `22.5`
- Average PC accepted NEW weight: `0.0479`
- Single capital winner: `CASH_OPTIONALITY=16`, `NEW_BUY=6`
- Risk Pacing: `CAUTIOUS_DEPLOYMENT=13`, `NORMAL_DEPLOYMENT=9`
- Market Quality: `HEALTHY_EXPANSION=9`, `CONFLICTED_MARKET_STRUCTURE=9`,
  `SHORT_TERM_NARROWING_WITH_MEDIUM_STRENGTH=3`,
  `SHORT_TERM_BREADTH_BREAKDOWN=1`
- BUY fills on these dates: `28`, notional `3,325,960`

## Low-Cash BULL Positive Controls

Comparison predicate:

```text
regime = BULL
actual cash ratio < 0.30
```

There were `39` low-Cash BULL positive-control days.

Representative controls:

| Date | Cash ratio | Positions | Market Quality | Risk Pacing | Full/Reduced | NEW competitors | PC NEW weight | Single winner | BUY fills |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | ---: |
| 2023-06-14 | 0.176 | 13 | HEALTHY_EXPANSION | NORMAL_DEPLOYMENT | 4/20 | 17 | 0.192310 | NEW_BUY | 3 |
| 2023-06-15 | 0.235 | 14 | HEALTHY_EXPANSION | NORMAL_DEPLOYMENT | 7/21 | 19 | 0.192310 | NEW_BUY | 4 |
| 2023-06-16 | 0.162 | 15 | HEALTHY_EXPANSION | NORMAL_DEPLOYMENT | 7/30 | 25 | 0.112601 | NEW_BUY | 3 |
| 2023-06-19 | 0.192 | 15 | HEALTHY_EXPANSION | NORMAL_DEPLOYMENT | 8/30 | 27 | 0.117648 | NEW_BUY | 2 |
| 2023-09-01 | 0.160 | 14 | HEALTHY_EXPANSION | NORMAL_DEPLOYMENT | 3/31 | 25 | 0.184212 | NEW_BUY | 2 |
| 2023-09-05 | 0.084 | 17 | HEALTHY_EXPANSION | NORMAL_DEPLOYMENT | 4/29 | 20 | 0.128024 | NEW_BUY | 3 |
| 2023-09-07 | 0.073 | 17 | HEALTHY_EXPANSION | NORMAL_DEPLOYMENT | 6/21 | 17 | 0.137932 | NEW_BUY | 2 |
| 2024-02-07 | 0.193 | 10 | SHORT_TERM_NARROWING_WITH_MEDIUM_STRENGTH | CAUTIOUS_DEPLOYMENT | 4/26 | 22 | 0.033333 | CASH_OPTIONALITY | 1 |

What enables deployment in the controls is not merely BULL.  It is the
combination of lower existing cash, higher accepted NEW weight, more existing
position count / portfolio participation, and, on the strongest controls,
`HEALTHY_EXPANSION` with `NORMAL_DEPLOYMENT`.

## NEW Funnel

High-Cash BULL funnel:

| Stage | High-Cash BULL result |
| --- | --- |
| Candidate / BUY-quality rows | 50 rows per day, `1,100` total rows across 22 days |
| Full/reduced/high-quality candidate supply | Average `30.6` per day |
| Eligible NEW competitors in PC | Average `22.5` per day |
| BUY consideration / PC competitor set | Present every high-Cash BULL day |
| Positive NEW allocation in PC | Average accepted NEW weight `0.0479`; six days had NEW as single capital winner |
| Cash frontier / MCC | `CASH_OPTIONALITY` single winner on `16 / 22` days |
| Position Sizing quantity | Consumed PC deployment set; residual Cash preserved; no PS redecision authority observed |
| Runtime BUY | Runtime consumed PS/PC outputs; BUY fills occurred on `16 / 22` high-Cash BULL days |
| Fill | `28` BUY fills / `3,325,960` notional across high-Cash BULL days |

The funnel therefore does not fail at candidate discovery.  It narrows at
capital conversion: many candidates are valid enough to appear, but not strong
enough to defeat Cash under the current Market Quality / Risk Pacing / MCC
contract.

## Cash Decomposition

High-Cash BULL cash reason codes were dominated by:

| Reason surface | Count across high-Cash BULL days | Interpretation |
| --- | ---: | --- |
| `NO_VALID_COMPETITOR` | 36 | PC/MCC frequently exhausted deployable security priority before cash was exhausted. |
| `MARGINAL_OPPORTUNITY_SET` | 30 | NEW supply existed but was generally marginal, not compelling. |
| `CAUTIOUS_MARKET_OPTIONALITY_ELEVATED` | 26 | Cautious Risk Pacing / Market Quality made Cash a first-class competitor. |
| `CASH_PRE_FINAL_INTERACTION_WINNER` | 16 | Cash won the single capital interaction on most high-Cash BULL days. |
| `HEALTHY_MARKET_OPTIONALITY_LOW` | 12 | Even healthy BULL did not force full deployment. |
| `NORMAL_COMPARABLE_MARGINAL_DEPLOY` | 6 | Positive control: some marginal NEW was allowed. |
| `STRONG_OPPORTUNITY_PRESENT` | 8 | Strong supply could coexist with residual Cash. |

Cash cause mapping:

| Cash class | Evidence |
| --- | --- |
| `GENUINE_NO_COMPELLING_NEW` | Material: many dates show `MARGINAL_OPPORTUNITY_SET` and `NO_VALID_COMPETITOR`. |
| `NEW_FAILED_ENTRY_QUALITY` | Partial: candidates existed, but many were reduced/marginal rather than frontier winners. |
| `NEW_LOST_TO_CASH` | Material: `CASH_OPTIONALITY` won `16 / 22` single interactions. |
| `MCC_SUPPRESSION` | Material: represented by `market_candidate_cash_interaction` and cash-preferred deferrals. |
| `RISK_PACING_SUPPRESSION` | Partial/material: `CAUTIOUS_DEPLOYMENT` on `13 / 22`, but some high-Cash days were normal. |
| `MARKET_QUALITY_RESERVE` | Material on non-healthy Market Quality days. |
| `EXPOSURE_ALREADY_SUFFICIENT` | Partial: not high exposure, but policy did not require BULL full deployment. |
| `SAFETY_OR_CAP_LIMIT` | Not primary; no emergency or hard cap evidence dominated the sample. |
| `LOT_OR_EXECUTABILITY` | Partial/local: `LOT_RESIDUAL_OPTIONALITY` appears, but not as the main cause. |
| `SELL_GENERATED_TEMPORARY_CASH` | Partial: some high-Cash days include SELL fills, but high Cash persisted across sequences. |
| `UNALLOCATED_RESIDUAL` | Material as authorized Cash / residual optionality, not unexplained orphan cash. |

## Market Quality Analysis

The audit confirms the required separation:

```text
BULL != full investment required
```

On the 22 high-Cash BULL days:

- `9` were `HEALTHY_EXPANSION`
- `9` were `CONFLICTED_MARKET_STRUCTURE`
- `3` were `SHORT_TERM_NARROWING_WITH_MEDIUM_STRENGTH`
- `1` was `SHORT_TERM_BREADTH_BREAKDOWN`

Decision-time classification:

| Classification | Dates |
| --- | --- |
| `APPROPRIATE_CAUTION` | 2023-06-28, 2023-09-27, 2023-11-17, 2024-01-16, 2024-01-17, 2024-01-18, 2024-01-19, 2024-01-22, 2024-01-29, 2024-01-30, 2024-02-01, 2024-02-02, 2024-02-26 |
| `POSSIBLY_OVERCONSERVATIVE` | 2024-01-11, 2024-01-15, 2024-01-23, 2024-01-24, 2024-01-31 |
| `UNRESOLVED` | 2024-01-10, 2024-01-12, 2024-01-25, 2024-01-26 |

The unresolved / possibly overconservative cluster is mainly January 2024:
healthy BULL, normal Risk Pacing, high Cash, visible NEW candidates, and still
large authorized Cash.

## Risk Pacing Analysis

G140 remains intact:

```text
RISK_PACING_ARCHITECTURALLY_NECESSARY = YES
```

The question here is materiality, not existence.  Risk Pacing was material on
high-Cash BULL days because `13 / 22` were `CAUTIOUS_DEPLOYMENT`, and those
dates repeatedly carried `CAUTIOUS_MARKET_OPTIONALITY_ELEVATED`,
`CAUTIOUS_COMPARABLE_MARGINAL_CASH_PREFERRED`, and
`CAUTIOUS_MARGINAL_LOST_TO_CASH`.

But Risk Pacing alone does not explain the whole pattern.  `9 / 22` high-Cash
BULL dates were `NORMAL_DEPLOYMENT`, and `6` of those had NEW as the single
capital winner.  Even then, authorized Cash weight often remained large.  This
points to the broader capital frontier: normal deployment can still leave Cash
when NEW is marginal, residual, lot-limited, or not a decisive frontier
candidate.

## PC / MCC Analysis

MCC is represented inside `portfolio_construction.json` through
`market_candidate_cash_interaction`, `cash_competitor`,
`canonical_deployment_set`, and
`canonical_multi_allocation_deployment_set`.

Key PC/MCC findings:

- Cash won the single capital interaction on `16 / 22` high-Cash BULL days.
- NEW won the single interaction on only `6 / 22`.
- Average accepted PC NEW weight on high-Cash BULL days was `0.0479`, compared
  with `0.1043` for low-Cash BULL controls.
- Average authorized Cash weight in the high-Cash BULL multi-allocation set was
  `0.5844`; average authorized security weight was `0.1242`.
- Cash-preferred security deferrals totaled `21` rows across high-Cash BULL
  days.

This is material PC/MCC capital suppression in the semantic sense: security
allocation was bounded by Cash competition, not by a missing Runtime BUY path.
Runtime and execution consumed what PC/PS made executable.

## Spring Vs Plateau

| Window | Days | BULL days | Avg cash ratio | Avg positions | Avg full/reduced candidates | Avg NEW competitors | Avg PC NEW weight | BUY fills | BUY notional | Single NEW winner |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Spring `2023-02-27` to `2023-05-30` | 63 | 31 | 0.280 | 9.0 | 28.7 | 20.2 | 0.1577 | 95 | 10,185,080 | 17 |
| Plateau `2023-05-31` to `2024-02-26` | 182 | 76 | 0.375 | 10.0 | 30.5 | 22.3 | 0.0826 | 289 | 28,015,300 | 37 |
| High-Cash BULL subset | 22 | 22 | 0.653 | 5.4 | 30.6 | 22.5 | 0.0479 | 28 | 3,325,960 | 6 |
| Low-Cash BULL controls | 39 | 39 | 0.191 | 12.1 | 30.2 | 20.2 | 0.1043 | 70 | 5,779,410 | 13 |

Spring moved the portfolio through larger average accepted NEW weight and
sustained deployment into initial NEW lots.  Late plateau, especially January
2024, had ample candidate supply but lower position count, much higher Cash,
and a capital frontier that often converted candidate supply into optionality
rather than exposure.

## Interaction With Phase32-E Issues

Phase32-E remains a separate but interacting issue:

- Phase32-E: ADD often lost to NEW through ordinal-only ADD-vs-NEW comparison.
- Phase32-G: NEW often then lost to Cash, or only received bounded marginal
  allocation.

When both occur, the system can produce this frontier:

```text
ADD continuation evidence -> loses to NEW by ordinal score
NEW candidate supply -> judged marginal / cash-preferred by MCC
Cash -> absorbs residual or wins single capital interaction
```

That is not proof that Cash is wrong.  It is proof that ADD / NEW / Cash are
not yet observed together in one economic next-yen capital frontier.  Do not
promote High-Resolution Architecture to implementation from this finding alone.

## Root-Cause Ranking

| Rank | Cause | Classification | Evidence |
| ---: | --- | --- | --- |
| 1 | `CAPITAL_FRONTIER_LIMITATION` | Material | ADD, NEW, and Cash interact through ordinal/marginal classes, not calibrated next-yen value. |
| 2 | `PC_MCC_CAPITAL_SUPPRESSION` | Material | Cash wins `16 / 22`; average authorized Cash weight `0.5844`. |
| 3 | `RISK_PACING_CALIBRATION` | Partial/material | Cautious deployment appears on `13 / 22`; normal deployment also leaves high Cash. |
| 4 | `NEW_ENTRY_QUALITY` | Partial | Candidate count high, but opportunity often classed marginal/reconsiderable. |
| 5 | `MARKET_QUALITY_CAUTION` | Material on non-healthy days | `13 / 22` high-Cash BULL days were conflicted/narrowing/breadth breakdown. |
| 6 | `NORMAL_CASH_OPTIONALITY` | Mixed | BULL does not require full investment; some healthy days still look possibly conservative. |
| 7 | `EXECUTABILITY` | Local | Lot residual appears but is not the dominant aggregate cause. |

## Defect / Limitation / Normal Behavior Classification

Final classification: `MIXED`, with primary cause
`CAPITAL_FRONTIER_LIMITATION`.

No mandatory defect is established.  The observed behavior is partly normal
Cash optionality under G140 and weak/non-healthy Market Quality, partly PC/MCC
suppression of marginal NEW, and partly an observability limitation: current
artifacts do not present ADD, NEW, Cash, Risk Pacing, MCC, PS, Runtime, fills,
and final outcome as one capital-frontier row.

## Recommended Next Step

Create a shadow-only spec/reporting surface:

```text
capital_frontier_cash_new_add_bridge.v1
```

Required row fields:

- `business_date`, `regime`, `market_quality_state`, `risk_pacing_intent`
- actual equity, actual cash, actual cash ratio, current exposure, position
  count
- candidate count, full/reduced/high-quality count, top score/rank
- NEW eligible count, NEW competitor count, requested NEW, accepted NEW
- ADD competitor count, requested ADD, accepted ADD
- Cash competitor semantic, authorized Cash, residual Cash, reason codes
- MCC winner, defeated competitor summary, cash-preferred deferral count
- PS positive NEW quantity/notional, withheld / zero quantity reason codes
- Runtime BUY plan count, BUY fill count/notional
- final campaign outcome for offline labels only
- `future_information_used=false`, `shadow_only=true`,
  `not_action_authority=true`

## Final Judgments

```text
PHASE32_G_HIGH_CASH_BULL_DAYS = 22
PHASE32_G_NEW_CANDIDATE_SUPPLY_MATERIAL = YES
PHASE32_G_NEW_DEPLOYMENT_SUPPRESSION = PARTIAL
PHASE32_G_PRIMARY_CASH_CAUSE = CAPITAL_FRONTIER_LIMITATION / MIXED
PHASE32_G_RISK_PACING_SUPPRESSION_MATERIAL = PARTIAL
PHASE32_G_RISK_PACING_OVERCONSERVATIVE_EVIDENCE = PARTIAL
PHASE32_G_PC_MCC_SUPPRESSION_MATERIAL = YES
PHASE32_G_NEW_ENTRY_QUALITY_LIMITATION = PARTIAL
PHASE32_G_CASH_OPTIONALITY_APPROPRIATE = MIXED
PHASE32_G_CAPITAL_FRONTIER_LIMITATION = YES
PHASE32_G_PHASE32_E_INTERACTION_MATERIAL = YES
PHASE32_G_MANDATORY_DEFECT = NO
PHASE32_G_PRODUCTION_REPAIR_JUSTIFIED = NO
PHASE32_G_IMPLEMENTATION_READY = NO
PHASE32_G_NEXT_STEP = Phase32-H shadow capital_frontier_cash_new_add_bridge.v1 specification and extraction design
```

## Files / Commands Inspected

Files and artifact families inspected:

- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260825T235520054579Z/daily/*/strategy/portfolio_policy.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260825T235520054579Z/daily/*/strategy/portfolio_construction.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260825T235520054579Z/daily/*/strategy/position_sizing.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260825T235520054579Z/daily/*/strategy/runtime_planning.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260825T235520054579Z/daily/*/strategy/buy_quality_decisions.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260825T235520054579Z/daily/*/strategy/market_context.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260825T235520054579Z/daily/*/execution/fills.json`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md`
- `docs/phase_reports/phase32_e_add_vs_new_marginal_comparison_semantic_deep_audit.md`

Commands used:

- `sed -n ... pasted-text.txt`
- `find reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260825T235520054579Z/daily/...`
- `rg -n "MCC|marginal_capital|market_candidate_cash|capital_competition|cash_preferred" ...`
- ad hoc read-only Python extraction over daily JSON artifacts

