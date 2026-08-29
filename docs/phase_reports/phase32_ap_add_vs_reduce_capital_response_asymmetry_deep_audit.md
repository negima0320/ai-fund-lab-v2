# Phase32-AP - ADD vs REDUCE Capital Response Asymmetry Deep Audit

## Executive Summary

Scope: READ-ONLY audit of:

```text
runtime-test-historical-extended-smoke-20260827T093649849074Z
```

Coverage frozen at latest completed valuation-ready date observed during AP:

```text
2022-10-03 through 2023-12-26
305 completed valuation-ready business days
```

Primary answer:

```text
The actual path shows material capital-response asymmetry.
Loss / weakness can release capital through REDUCE and especially EXIT far more often than strength / continuation adds capital through BUY_ADD.
This is not a REDUCE/EXIT defect and does not justify weakening defense.
It supports AO Design D: improve attack-side marginal capital value / target-gap architecture, not defense throttling.
```

Important nuance: REDUCE is also conservative in notional and weight magnitude. The largest defensive capital release is EXIT, not REDUCE. REDUCE does have multi-lot positive controls, but most REDUCE fills are still 100 shares. The strongest asymmetry is frequency and finality:

- PM ADD intent appears, but converts to BUY_ADD fill only rarely.
- PM REDUCE intent often produces partial sell fills when sell-planning quantity contract passes.
- PM EXIT almost directly liquidates the full position.
- Capital released by REDUCE/EXIT recycles mostly to NEW_BUY or remains Cash; it does not recycle effectively into ADD.

No production code, config, thresholds, model, schema, runtime state, fresh run, resume, replay, backtest, or run stop was changed or executed.

## Sources

Primary reports:

- `docs/phase_reports/phase32_ao_conviction_weighted_capital_allocation_multi_lot_add_design_research_audit.md`
- `docs/phase_reports/phase32_an_conviction_sizing_100_share_dominance_root_cause_audit.md`
- `docs/phase_reports/phase32_am_buy_new_early_failure_vs_winner_pit_divergence_deep_audit.md`
- `docs/00_vision/investment_philosophy.md`

Architecture / source:

- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`
- `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py`
- `src/ai_fund_lab_v2/strategy/reduce_intensity_authority.py`
- `src/ai_fund_lab_v2/strategy/position_sizing.py`
- `src/ai_fund_lab_v2/strategy/runtime_planning.py`

Run artifacts:

- `position_management/pm_decisions.json`
- `strategy/portfolio_construction.json`
- `strategy/position_sizing.json`
- `strategy/runtime_planning.json`
- `morning/pending_generation_evidence.json`
- `execution/fills.json`
- `current_valuation_refresh/valuation_projection.json`

## Event Counts

PM decision events are canonical day-symbol-campaign-action rows.

| PM decision type | Count | Unique symbols | Unique campaigns |
| --- | ---: | ---: | ---: |
| ADD | 337 | 15 | 17 |
| REDUCE | 636 | 317 | 323 |
| EXIT | 291 | 279 | 290 |
| HOLD | 1,907 | 250 | 256 |

Actual fills use strict execution provenance where `source_decision_type` is explicit or BUY fills can be joined to same-day PM ADD. There are also 212 SELL fills with `source_decision_type=MISSING`; AP does not force those into REDUCE/EXIT counts.

| Runtime/fill semantic | Count |
| --- | ---: |
| BUY_ADD fill | 11 |
| REDUCE fill | 52 |
| EXIT fill | 290 |
| Other BUY fill | 509 |
| SELL fill with missing source type | 212 |

Funnel-level counts:

| Funnel | Intent | Planned / selected executable | Fill |
| --- | ---: | ---: | ---: |
| ADD | 337 PM ADD | 12 BUY_ADD runtime plans / positive PC quantity | 11 |
| REDUCE | 636 PM REDUCE | 52 explicit REDUCE execution fills | 52 |
| EXIT | 291 PM EXIT | approximately 290 explicit EXIT fills | 290 |

Interpretation: ADD loses most volume before executable quantity; REDUCE loses most volume at the sell-planning quantity contract / lot / minimum remaining boundary; EXIT mostly passes through to full liquidation.

## Unique Campaign Counts

| Type | Fill events | Unique symbols | Unique campaigns | Median events/campaign | Max events/campaign |
| --- | ---: | ---: | ---: | ---: | ---: |
| ADD | 11 | 5 | 5 | 1 | 5 |
| REDUCE | 52 | 28 | 28 | 1 | 5 |
| EXIT | 290 | 279 | 290 | 1 | 1 |

ADD concentration:

| Campaign | ADD fills |
| --- | ---: |
| `pc-b946a79c4c1eb894-94320-0001` | 5 |
| `pc-b6597c7eeb47ff43-94340-0001` | 3 |
| `pc-56a2fb60eb4b0f4e-54010-0001` | 1 |
| `pc-403a6c3de383c9da-59550-0001` | 1 |
| `pc-9095d32b753e2b88-30410-0001` | 1 |

REDUCE has more campaign breadth and some repeated partial de-risking:

| Campaign | REDUCE fills |
| --- | ---: |
| `pc-5f2ebf1cc776493d-37820-0002` | 5 |
| `pc-18d61b37bb1716f7-65740-0001` | 4 |
| `pc-dc0b34ae1ea05484-23150-0001` | 4 |
| `pc-9b3ebf33e64f4633-87890-0001` | 3 |
| `pc-b946a79c4c1eb894-94320-0001` | 3 |
| `pc-264e6d1382dddc4a-33230-0001` | 3 |
| `pc-3114ae2c23579b3e-66590-0001` | 3 |
| `pc-b7419e4082d91248-32370-0001` | 3 |

## Quantity Distribution

| Type | 100 | 200 | 300 | 400-500 | 600-900 | 1000+ | Full liquidation |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ADD | 11 | 0 | 0 | 0 | 0 | 0 | n/a |
| REDUCE | 38 | 7 | 1 | 0 | 1 | 5 | n/a |
| EXIT | n/a | n/a | n/a | n/a | n/a | n/a | 290 |

| Type | Median qty | Mean qty | p75 | p90 | Max | 1-lot ratio | Multi-lot ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ADD | 100 | 100.0 | 100 | 100 | 100 | 100.0% | 0.0% |
| REDUCE | 100 | 251.9 | 200 | 300 | 1,700 | 73.1% | 26.9% |
| EXIT | 100 | 254.8 | 100 | 300 | 6,700 | 77.6% | 22.4% |

REDUCE is not structurally one-lot. It is fraction/weight-driven via reduce intensity, then rounded to 100-share tradable units.

## Notional Distribution

| Type | Median notional | Mean notional | p75 | p90 | Max |
| --- | ---: | ---: | ---: | ---: | ---: |
| ADD | JPY 16,020 | JPY 30,577 | JPY 16,260 | JPY 58,640 | JPY 138,500 |
| REDUCE | JPY 9,150 | JPY 11,922 | JPY 12,300 | JPY 17,100 | JPY 51,570 |
| EXIT | JPY 61,800 | JPY 86,668 | JPY 118,000 | JPY 184,800 | JPY 373,000 |

Notional / equity:

| Type | Median | Mean | p75 | p90 | Max |
| --- | ---: | ---: | ---: | ---: | ---: |
| ADD | 1.50% | 2.40% | 1.54% | 4.75% | 8.92% |
| REDUCE | 0.60% | 0.82% | 0.88% | 1.33% | 3.07% |
| EXIT | 4.11% | 5.97% | 7.56% | 13.44% | 25.23% |

ADD has larger median notional than REDUCE, but REDUCE occurs more often and EXIT dwarfs both as capital release.

## Weight-Change Distribution

Absolute weight change:

| Type | Median | Mean | p75 | p90 | Max |
| --- | ---: | ---: | ---: | ---: | ---: |
| ADD | 1.50% | 2.40% | 1.54% | 4.75% | 8.92% |
| REDUCE | 0.56% | 0.80% | 0.92% | 1.32% | 3.34% |
| EXIT | 4.08% | 5.96% | 7.60% | 13.55% | 25.44% |

This shows two different asymmetries:

- ADD vs REDUCE magnitude per event is not defense-heavy; ADD event size is larger in weight terms than REDUCE.
- ADD vs combined de-capitalization is heavily defense-heavy because EXIT is frequent and full-position.

## REDUCE Authority Path

Actual REDUCE quantity formation:

```text
PM REDUCE decision
-> PM delegates quantity to SELL_PLANNING_REDUCE_QUANTITY_CONTRACT
-> Portfolio Construction carries reduce_intensity / reduce_fraction
-> sell_pipeline.calculate_reduce_quantity_contract()
-> floor(raw_reduce_quantity / tradable_unit) * tradable_unit
-> reject if zero, full-liquidating, or leaves less than one tradable unit
-> pending item / historical simulated execution
-> execution/fills.json with source_decision_type=REDUCE
```

Source boundaries:

| Stage | Module / function | Authority field |
| --- | --- | --- |
| PM intent | `position_management/producer.py` artifact | `decision_type=REDUCE`, `decision_reason`, `dominant_cause` |
| Quantity delegation | PM decision row | `quantity_requested.quantity_authority=SELL_PLANNING_REDUCE_QUANTITY_CONTRACT` |
| Intensity | `reduce_intensity_authority.py` | LIGHT 25%, MEDIUM 33%, STRONG 50% |
| Sell quantity | `sell_pipeline.calculate_reduce_quantity_contract()` | `final_sell_quantity`, floor-to-tradable-unit |
| Execution | historical execution | `source_decision_type=REDUCE`, `quantity`, `gross_notional` |

REDUCE quantity classification:

```text
PHASE32_AP_REDUCE_QUANTITY_AUTHORITY = MIXED
```

More precisely: fraction/severity-intensity driven, lot-rounded, with full-exit prevented by contract.

## REDUCE Multi-Lot Positive Controls

Actual multi-lot REDUCE examples:

| Date | Symbol | Campaign | Cause | Intensity | Fraction | Pre qty | Post qty | Sold | Pre wt | Post wt | Released |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2023-11-24 | 82560 | `pc-33c18c76268524f9-82560-0002` | peak drawdown warning | STRONG | 0.50 | 3,400 | 1,700 | 1,700 | 4.80% | 2.68% | 45,900 |
| 2023-05-31 | 65740 | `pc-18d61b37bb1716f7-65740-0001` | weak hold score | LIGHT | 0.25 | 7,100 | 5,400 | 1,700 | 3.23% | 2.50% | 12,240 |
| 2023-06-01 | 65740 | `pc-18d61b37bb1716f7-65740-0001` | weak hold score | LIGHT | 0.25 | 5,400 | 4,100 | 1,300 | 2.43% | 1.90% | 9,100 |
| 2023-09-07 | 89180 | `pc-dd510c90667fb1bb-89180-0002` | weak hold score | LIGHT | 0.25 | 5,000 | 3,800 | 1,200 | 2.66% | 2.01% | 10,800 |
| 2023-06-07 | 65740 | `pc-18d61b37bb1716f7-65740-0001` | weak hold score | LIGHT | 0.25 | 4,100 | 3,100 | 1,000 | 1.79% | 1.33% | 6,800 |
| 2023-06-16 | 65740 | `pc-18d61b37bb1716f7-65740-0001` | weak hold score | LIGHT | 0.25 | 3,100 | 2,400 | 700 | 1.42% | 1.05% | 4,970 |
| 2023-03-07 | 37770 | `pc-9be29e3a70933239-37770-0001` | weak hold score | STRONG | 0.50 | 600 | 300 | 300 | 2.54% | 1.27% | 17,100 |
| 2022-12-05 | 94320 | `pc-b946a79c4c1eb894-94320-0001` | peak drawdown warning | MEDIUM | 0.33 | 700 | 500 | 200 | 9.16% | 6.63% | 29,980 |
| 2023-06-08 | 23150 | `pc-dc0b34ae1ea05484-23150-0001` | weak hold score | LIGHT | 0.25 | 800 | 600 | 200 | 3.17% | 2.42% | 12,600 |
| 2023-03-06 | 37770 | `pc-9be29e3a70933239-37770-0001` | weak hold score | LIGHT | 0.25 | 800 | 600 | 200 | 3.56% | 2.64% | 11,600 |
| 2023-08-10 | 66590 | `pc-3114ae2c23579b3e-66590-0001` | weak hold score | LIGHT | 0.25 | 900 | 700 | 200 | 3.30% | 2.50% | 11,000 |
| 2023-06-23 | 37820 | `pc-5f2ebf1cc776493d-37820-0002` | weak hold score | LIGHT | 0.25 | 900 | 700 | 200 | 2.68% | 2.12% | 9,800 |
| 2023-04-20 | 67400 | `pc-4809cc1138a06b6e-67400-0001` | weak hold score | LIGHT | 0.25 | 1,100 | 900 | 200 | 3.48% | 2.80% | 9,200 |
| 2022-10-11 | 33500 | `pc-546f6f48f84ef881-33500-0001` | weak hold score | LIGHT | 0.25 | 900 | 700 | 200 | 3.36% | 2.72% | 8,100 |

Only 14 actual multi-lot REDUCE cases were observed in strict-provenance fills, so the requested 20 cannot be supplied without using non-authoritative holdings deltas or `source_decision_type=MISSING` sells. AP intentionally does not do that.

## Severity-to-Release Relationship

PM REDUCE reasons:

| REDUCE PM reason | Count |
| --- | ---: |
| `risk_increased_but_trend_not_broken` | 532 |
| `peak_drawdown_warning` | 104 |

Actual strict REDUCE fill cause medians:

| Cause | Fill count | Median abs weight release |
| --- | ---: | ---: |
| `REDUCE_BY_WEAK_HOLD_SCORE` | 39 | 0.49% |
| `REDUCE_BY_PEAK_DRAWDOWN_WARNING` | 13 | 1.33% |

Actual strict REDUCE fill intensity medians:

| Intensity | Fill count | Median abs weight release |
| --- | ---: | ---: |
| LIGHT | 35 | 0.46% |
| MEDIUM | 5 | 1.31% |
| STRONG | 12 | 1.27% |

The quantity mechanism itself is severity/intensity-aware through LIGHT/MEDIUM/STRONG fractions, but realized released weight is also heavily affected by current quantity, share price, trading unit, and minimum remaining quantity. Therefore:

```text
PHASE32_AP_REDUCE_SEVERITY_CAPITAL_RELATIONSHIP = PARTIAL
```

## ADD Strength-to-Deployment Relationship

All PM ADD decisions share the same dominant cause:

```text
ADD_BY_STRONG_TREND_AND_RANK
```

But only 11 actual ADD fills materialized from 337 PM ADD decisions. All were one-lot fills. AO already found ADD accepted target gaps were mostly below one lot, with only four rows in the 1-2 lot cohort and none above two lots.

ADD has some strength-to-deployment relationship because the 11 fills are genuine PM ADD / strong trend and rank cases. However, the relationship is weak at the capital response level because stronger/continued ADD intent usually does not become larger or repeated scale-up.

```text
PHASE32_AP_ADD_STRENGTH_CAPITAL_RELATIONSHIP = WEAK
```

## Frequency Asymmetry

Per 100 completed business days:

| Event | Fills | Events / 100BD |
| --- | ---: | ---: |
| ADD | 11 | 3.61 |
| REDUCE | 52 | 17.05 |
| EXIT | 290 | 95.08 |

Defense-side action is dominant in frequency, especially when EXIT is included. This is partly justified by the investment philosophy: weakening positions should not be kept merely for symmetry. But the ADD path is sparse enough that attack-side winner scaling is underrepresented.

```text
PHASE32_AP_FREQUENCY_ASYMMETRY = DEFENSE_DOMINANT
```

## Magnitude Asymmetry

Per event, ADD median notional and weight delta are larger than REDUCE:

- median ADD notional: JPY 16,020
- median REDUCE notional: JPY 9,150
- median ADD weight delta: 1.50%
- median REDUCE weight delta: 0.56%

But EXIT is full liquidation and much larger:

- median EXIT notional: JPY 61,800
- median EXIT weight delta: 4.08%

Overall magnitude classification:

```text
PHASE32_AP_MAGNITUDE_ASYMMETRY = DEFENSE_FASTER_JUSTIFIED
```

Defense is dominant through EXIT, but REDUCE itself is measured and often small.

## Latency Asymmetry

Available artifact evidence supports a partial latency conclusion:

- REDUCE/EXIT source decisions and fills occur same-day when executable in historical simulation.
- REDUCE quantity is delegated immediately to sell-planning quantity contract.
- ADD intent can persist across many days and campaigns without scaling: e.g. PM ADD campaign `pc-091f6fd4e6c166be-94320-0002` had 225 PM ADD events but no comparable multi-lot scaling in the AP fill set.

AP does not infer first-observed strengthening/weakening timestamps from future outcomes. Within same-day artifacts:

```text
PHASE32_AP_LATENCY_ASYMMETRY = DEFENSE_FASTER
```

## ADD Funnel

Approximate actual-path ADD funnel:

| Stage | Count |
| --- | ---: |
| Held symbols evaluated by PM | reflected in 3,171 PM decisions |
| PM ADD intent | 337 |
| ADD Position Sizing rows | 337 |
| Positive PC / runtime BUY_ADD plan | 12 |
| Actual BUY_ADD fill | 11 |
| Multi-lot ADD fill | 0 |

First major ADD drop-off:

```text
PM ADD intent -> accepted target/incremental capital gap -> positive executable BUY_ADD quantity
```

AO quantified that accepted ADD gaps are already compressed before final execution; AP confirms that this sparse conversion remains true at the extended coverage point.

## REDUCE Funnel

Approximate actual-path REDUCE funnel:

| Stage | Count |
| --- | ---: |
| PM REDUCE intent | 636 |
| PC/strategy REDUCE rows | 422 visible strategy rows plus SELL planning path evidence |
| Explicit REDUCE fill | 52 |
| Multi-lot REDUCE fill | 14 |

First major REDUCE drop-off:

```text
PM REDUCE intent -> sell-planning reduce quantity contract / lot / minimum remaining boundary
```

Many PM REDUCE rows are intentionally no-order in the strategy planning view, especially when the partial reduction would not clear the minimum tradable / minimum notional / remaining-lot constraints. When SELL planning quantity contract passes, fills can be multi-lot.

## First Drop-Off Boundaries

| Side | First major drop-off | Diagnosis |
| --- | --- | --- |
| ADD | target-gap compression before PS and PC positive discrete quantity scarcity | attack-side capital-value / target mapping limitation |
| REDUCE | sell-planning reduce quantity contract and tradable-unit / minimum remaining constraints | conservative partial de-risking, not one-lot fixed |
| EXIT | little drop-off between PM EXIT and strict EXIT fill | full liquidation path is strong and direct |

## Capital Response Symmetry

Investment philosophy allows asymmetry: a swing momentum system should cut or reduce weakening positions without waiting for perfectly symmetric ADD behavior.

Still, AP confirms the user's observation in a qualified form:

```text
weakening -> capital release is frequent and direct, especially through EXIT
strengthening -> capital increase is rare and capped at one lot in actual ADD fills
```

This should not be repaired by slowing REDUCE or EXIT. It should be studied by improving attack-side capital scaling.

## Portfolio Consequence

AO and AN characterize the resulting posture:

- many one-lot positions;
- median open position count around 10;
- high-count days around 17-19 positions;
- top-3 share often not dominant enough to express a concentrated winner posture;
- ADD events cluster in very few campaigns and do not become broad scale-up.

This is consistent with the user's "spreads horizontally more than vertically" hypothesis.

## Capital Recycling

Across release days, capital released by strict REDUCE/EXIT was followed in the next 1-3 completed business days mostly by NEW/other BUY activity, not ADD:

| Metric | Value |
| --- | ---: |
| Release days | 249 |
| Strict REDUCE+EXIT released notional | JPY 44.1M |
| Next-3BD ADD deployed notional | JPY 0.78M |
| Next-3BD other BUY deployed notional | JPY 107.9M |
| ADD / other BUY next-3BD ratio | 0.72% |

Representative release/redeployment windows:

| Release date | Released | Next 1-3BD ADD | Next 1-3BD other BUY | Pattern |
| --- | ---: | ---: | ---: | --- |
| 2022-10-04 | 130,320 | 14,780 | 325,980 | small ADD, larger NEW |
| 2022-10-11 | 258,900 | 45,130 | 310,400 | ADD exists but NEW dominates |
| 2022-10-13 | 433,950 | 0 | 513,400 | NEW dominates |
| 2022-10-21 | 163,000 | 0 | 587,430 | NEW dominates |
| 2022-10-24 | 286,400 | 0 | 568,730 | NEW dominates |

Classification:

```text
PHASE32_AP_CAPITAL_RECYCLES_TO_ADD_EFFECTIVELY = NO
PHASE32_AP_CAPITAL_RECYCLES_TO_NEW_MORE_THAN_ADD = YES
```

## NEW vs ADD After Release

After REDUCE/EXIT release events, ADD opportunities sometimes existed, but released capital mostly funded NEW/other BUY or stayed within Cash/optionality. This matches AO's finding that ADD target gaps remain compressed and selected ADD quantity remains one-lot.

This is not proof that NEW was wrong. It is proof that the current architecture expresses replacement/exploration more readily than scaling existing winners.

## Safety / Risk Rationale

The asymmetry appears mixed:

- Permanent risk philosophy: YES for fast EXIT / partial REDUCE when weakness appears.
- Transitional migration artifact: YES for conservative one-lot ADD and compressed accepted ADD gaps.
- Emergent interaction: YES for Cash/PC/MCC/lot interactions recycling released capital toward NEW/Cash rather than ADD.

Therefore:

```text
PHASE32_AP_ASYMMETRY_ORIGIN = MIXED
```

## Architecture Implication

AP supports AO's preferred architecture, Design D:

```text
conviction-weighted target mapping
+ independently evaluated next-lot ADD marginal competition
```

Primary AP diagnosis:

```text
D - ADD scarcity + magnitude limitation
```

More broadly, this is a common marginal-capital asymmetry, but the immediate observable surface is ADD scarcity and one-lot ADD magnitude. No mandatory defect was found because the observed quantities follow the current contracts.

## Next Step

Do not weaken REDUCE or EXIT. Build a shadow-only common marginal capital response study that compares:

- NEW first lot;
- REENTRY first lot;
- ADD next lot;
- additional ADD next lot;
- Cash optionality;
- REDUCE/EXIT released-capital destination.

The study should report target-gap formation, PC competition, lot feasibility, and post-release destination without tuning thresholds from historical returns.

## Final Judgments

PHASE32_AP_RUN_ID = runtime-test-historical-extended-smoke-20260827T093649849074Z

PHASE32_AP_COVERAGE_END = 2023-12-26

PHASE32_AP_ADD_FILL_TOTAL = 11

PHASE32_AP_REDUCE_FILL_TOTAL = 52

PHASE32_AP_EXIT_FILL_TOTAL = 290

PHASE32_AP_ADD_UNIQUE_CAMPAIGNS = 5

PHASE32_AP_REDUCE_UNIQUE_CAMPAIGNS = 28

PHASE32_AP_ADD_1LOT_RATIO = 100.0%

PHASE32_AP_REDUCE_1LOT_RATIO = 73.1%

PHASE32_AP_REDUCE_MULTI_LOT_RATIO = 26.9%

PHASE32_AP_MEDIAN_ADD_NOTIONAL = JPY 16,020

PHASE32_AP_MEDIAN_REDUCE_NOTIONAL = JPY 9,150

PHASE32_AP_MEDIAN_ADD_WEIGHT_DELTA = 1.50%

PHASE32_AP_MEDIAN_REDUCE_WEIGHT_DELTA = 0.56%

PHASE32_AP_REDUCE_QUANTITY_AUTHORITY = MIXED

PHASE32_AP_REDUCE_SEVERITY_CAPITAL_RELATIONSHIP = PARTIAL

PHASE32_AP_ADD_STRENGTH_CAPITAL_RELATIONSHIP = WEAK

PHASE32_AP_ADD_EVENTS_PER_100BD = 3.61

PHASE32_AP_REDUCE_EVENTS_PER_100BD = 17.05

PHASE32_AP_EXIT_EVENTS_PER_100BD = 95.08

PHASE32_AP_FREQUENCY_ASYMMETRY = DEFENSE_DOMINANT

PHASE32_AP_MAGNITUDE_ASYMMETRY = DEFENSE_FASTER_JUSTIFIED

PHASE32_AP_LATENCY_ASYMMETRY = DEFENSE_FASTER

PHASE32_AP_ADD_FIRST_MAJOR_DROPOFF = PM_ADD_INTENT_TO_ACCEPTED_TARGET_INCREMENT_AND_POSITIVE_EXECUTABLE_BUY_ADD_QUANTITY

PHASE32_AP_REDUCE_FIRST_MAJOR_DROPOFF = PM_REDUCE_INTENT_TO_SELL_PLANNING_REDUCE_QUANTITY_CONTRACT_EXECUTABILITY

PHASE32_AP_CAPITAL_RECYCLES_TO_ADD_EFFECTIVELY = NO

PHASE32_AP_CAPITAL_RECYCLES_TO_NEW_MORE_THAN_ADD = YES

PHASE32_AP_WINNER_CAPITALIZATION_WEAKER_THAN_LOSS_DECAPITALIZATION = YES

PHASE32_AP_ASYMMETRY_ORIGIN = MIXED

PHASE32_AP_PRIMARY_DIAGNOSIS = D

PHASE32_AP_NEW_MANDATORY_DEFECT_FOUND = NO

PHASE32_AP_ARCHITECTURE_IMPROVEMENT_JUSTIFIED = YES

PHASE32_AP_AO_DESIGN_D_SUPPORTED = YES

PHASE32_AP_PRODUCTION_CHANGE_THIS_TASK = NO

PHASE32_AP_LONG_RUN_CONTINUE = YES

PHASE32_AP_NEXT_STEP = Shadow-only common marginal capital response study for NEW/REENTRY/ADD/Cash plus released-capital destination; preserve REDUCE/EXIT defense and avoid historical-return-tuned thresholds.
