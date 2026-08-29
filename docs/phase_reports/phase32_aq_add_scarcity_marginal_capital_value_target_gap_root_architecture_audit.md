# Phase32-AQ - ADD Scarcity / Marginal Capital Value / Target-Gap Root Architecture Audit

## Executive Summary

Scope: READ-ONLY root architecture audit for:

```text
runtime-test-historical-extended-smoke-20260827T093649849074Z
```

Coverage frozen at the latest completed valuation-ready boundary observed during AQ aggregation:

```text
2022-10-03 through 2023-12-27
306 completed valuation-ready business days
```

Primary finding:

```text
ADD scarcity is real, but it is not caused by a Position Sizing lot-rounding bug or by PM failing to express ADD intent.
The first major loss is the transformation from PM ADD intent into positive accepted incremental target weight / target gap.
```

Observed funnel:

| Stage | Count | Rate vs PM ADD |
| --- | ---: | ---: |
| PM ADD intent present in Position Sizing rows | 340 | 100.00% |
| ADD rows with incremental-value proxy / accepted increment field available | 340 | 100.00% |
| ADD rows entering current capital competition as ADD | 340 | 100.00% |
| ADD rows with accepted incremental weight > 0 | 12 | 3.53% |
| ADD rows with PC ADD eligible flag | 20 | 5.88% |
| ADD rows with target gap >= one executable lot | 4 | 1.18% |
| ADD rows with PC discrete quantity > 0 | 12 | 3.53% |
| ADD rows with PS positive quantity delta | 12 | 3.53% |
| Runtime BUY_ADD plans | 12 | 3.53% |
| Actual BUY_ADD fills | 11 | 3.24% |

The observed conversion rate is:

```text
11 fills / 340 PM ADD intents = 3.24%
```

The important architectural distinction is:

```text
PM ADD intent is directional continuation / permissible add evidence.
It is not common cardinal marginal capital value.
It is not quantity authority.
It does not prove the next ADD lot beats NEW, REENTRY, another ADD, or Cash.
```

The current system has enough PIT-safe evidence to design a shadow high-resolution marginal capital value layer. It does not yet have a production-authoritative common value object that can compare:

```text
NEW first lot
REENTRY first lot
ADD next lot
another ADD next lot
Cash / optionality
```

Therefore the minimal architecture boundary is Portfolio Construction-owned capital value / target-gap authority, not PM, Position Sizing, runtime, Safety, Cash, PC/MCC threshold changes, or REDUCE/EXIT weakening.

No production code, config, threshold, schema, model, runtime state, fresh run, resume, replay, backtest, or run stop was changed or executed.

## Run Identity

| Field | Value |
| --- | --- |
| Run id | `runtime-test-historical-extended-smoke-20260827T093649849074Z` |
| Evidence path | `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260827T093649849074Z` |
| Audit boundary | latest completed valuation-ready artifacts observed during AQ |
| Coverage start | `2022-10-03` |
| Coverage end | `2023-12-27` |
| Completed valuation-ready business days | 306 |
| Mutation policy | READ-ONLY |

## Inherited AO / AP Facts

Phase32-AO established:

| Finding | Judgment |
| --- | --- |
| One-lot ADD origin | `CONSERVATIVE_TRANSITIONAL_DESIGN` |
| Multi-lot ADD architecturally valid | `YES` |
| Existing target gap supports immediate multi-lot production switch | `PARTIAL` |
| Conviction compression primary boundary | PC accepted incremental weight / capital value before PS |
| ADD / NEW common value scale | partially comparable, not common cardinal |
| Preferred design direction | Design D: common marginal capital value / next-lot comparison |
| Production repair readiness | `PARTIAL` |

Phase32-AP established:

| Finding | Value |
| --- | ---: |
| Coverage then observed | `2023-12-26` |
| PM ADD intents | 337 |
| BUY_ADD fills | 11 |
| PM REDUCE intents | 636 |
| REDUCE fills | 52 |
| PM EXIT intents | 291 |
| EXIT fills | 290 |
| ADD 100-share ratio | 100.0% |
| REDUCE multi-lot ratio | 26.9% |
| Primary diagnosis | attack-side capitalization weakness, not defense defect |

AQ extended the same run one more completed valuation-ready day. PM ADD intent increased from 337 to 340, while ADD fills remained 11. This preserves AP's core finding: ADD intent persists, but almost never becomes executable incremental capital.

## Sources

Primary artifacts and documents:

- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260827T093649849074Z`
- `docs/phase_reports/phase32_ao_conviction_weighted_capital_allocation_multi_lot_add_design_research_audit.md`
- `docs/phase_reports/phase32_ap_add_vs_reduce_capital_response_asymmetry_deep_audit.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`
- `src/ai_fund_lab_v2/strategy/position_sizing.py`
- `configs/strategy/position_sizing.json`

Artifact families inspected:

- `position_management/pm_decisions.json`
- `strategy/portfolio_construction.json`
- `strategy/position_sizing.json`
- `strategy/runtime_planning.json`
- `execution/fills.json`
- `current_valuation_refresh/valuation_projection.json`

## Exact ADD Funnel

Canonical ADD row basis: day-symbol-campaign rows where Position Management emitted ADD intent and the row appeared in Position Sizing / downstream allocation artifacts.

| Funnel boundary | Count | Drop from prior | Interpretation |
| --- | ---: | ---: | --- |
| PM ADD intent | 340 | n/a | PM produces frequent ADD intent. |
| ADD present in Position Sizing | 340 | 0 | PM-to-PS row materialization exists. |
| Runtime opportunity score populated | 340 | 0 | Opportunity evidence is not absent. |
| Buy quality score populated | 340 | 0 | Quality evidence is not absent. |
| Target weight populated | 340 | 0 | Target architecture is present. |
| Target minus current > 0 | 10-12 observable positive rows depending on final target/accepted-increment field | approximately 328 | First material loss. Target gap usually remains zero. |
| Accepted incremental weight > 0 | 12 | 328 | Capital increment authority rarely materializes. |
| PC ADD eligible | 20 | not monotonic with accepted increment | Eligibility and positive increment are separate. |
| Lot-equivalent target gap >= one lot | 4 | 8 from accepted increment | Some positive increments are below one full lot by target-gap measurement. |
| PC discrete quantity > 0 | 12 | 0 from accepted increment | When PC discrete authority exists, it resolves to one lot. |
| PS positive quantity delta | 12 | 0 | PS consumes authority; PS is not the primary loss point. |
| Runtime BUY_ADD plan | 12 | 0 | Runtime planning preserves PS positive ADDs. |
| Actual BUY_ADD fill | 11 | 1 | One planned ADD did not become a fill; this is not the architectural bottleneck. |

Top Position Sizing ADD evidence reasons:

| Reason signature | Count |
| --- | ---: |
| `ADD_TARGET_WEIGHT_UNCHANGED; existing_position_baseline_quantity_authoritative; membership_intent:RETAIN; pm_action:ADD` | 327 |
| `ADD_POSITIVE_QUANTITY_DELTA; PC_DISCRETE_EXECUTABLE_QUANTITY_AUTHORITY_CONSUMED; existing_position_baseline_quantity_authoritative; membership_intent:RETAIN; pm_action:ADD` | 12 |
| `ADD_TARGET_WEIGHT_UNCHANGED; EXISTING_BASELINE_CAP_DRIFT_ACCEPTED_NO_INCREMENT; existing_position_baseline_quantity_authoritative; membership_intent:RETAIN; pm_action:ADD` | 1 |

First major dropoff:

```text
PM_ADD_INTENT -> POSITIVE_ACCEPTED_INCREMENTAL_TARGET_WEIGHT / TARGET_GAP
```

This is earlier than final Position Sizing lot conversion. The failure mode is not “PS had a strong target and rounded it away”; the common pattern is “target remained equal to current position, so no incremental lot existed to size.”

## ADD Persistence

PM ADD intent is not a one-day artifact. Several campaigns repeatedly emit ADD while remaining unable to convert into incremental capital.

| Campaign | Symbol | PM ADD rows | ADD days | Positive ADD rows | Runtime ADD plans | ADD fills | Max current weight | Max target weight | Max accepted increment | Max lot-equivalent gap |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `pc-091f6fd4e6c166be-94320-0002` | 94320 | 227 | 159 | 0 | 0 | 0 | 2.61% | 2.61% | 0.00% | 0.00 |
| `pc-491b476ad402b5d3-76470-0002` | 76470 | 27 | 12 | 0 | 0 | 0 | 0.78% | 0.78% | 0.00% | 0.00 |
| `pc-3a1cb47435afe84e-99840-0001` | 99840 | 18 | 18 | 0 | 0 | 0 | 16.03% | 16.03% | 0.00% | 0.00 |
| `pc-b946a79c4c1eb894-94320-0001` | 94320 | 15 | 12 | 5 | 5 | 5 | 9.08% | 8.86% | 1.56% | 1.02 |
| `pc-3153c50490542a3d-43880-0001` | 43880 | 12 | 8 | 0 | 0 | 0 | 9.50% | 9.50% | 0.00% | 0.00 |
| `pc-b6597c7eeb47ff43-94340-0001` | 94340 | 6 | 6 | 4 | 4 | 3 | 7.10% | 5.69% | 1.41% | 1.00 |
| `pc-56a2fb60eb4b0f4e-54010-0001` | 54010 | 6 | 5 | 1 | 1 | 1 | 9.75% | 9.75% | 4.87% | 1.02 |
| `pc-9095d32b753e2b88-30410-0001` | 30410 | 1 | 1 | 1 | 1 | 1 | 17.14% | 8.71% | 8.43% | 1.00 |

Interpretation:

```text
ADD persistence is high.
ADD capital persistence is low.
```

The extreme case is `94320` campaign `pc-091f6fd4e6c166be-94320-0002`: 227 ADD rows across 159 ADD days, but target weight remained equal to current weight and no accepted increment appeared. This is the clearest example of PM semantic persistence being preserved while capital increment authority stays zero.

## PM ADD Semantics

Observed and documented semantics:

| Question | Answer |
| --- | --- |
| Does PM ADD mean the position is still held and continuation is favorable? | Yes. |
| Does PM ADD mean adding is permissible from PM's existing-position perspective? | Yes. |
| Does PM ADD mean “this is a good campaign”? | Usually yes in PM-local semantics. |
| Does PM ADD mean more capital has positive global marginal value? | No. |
| Does PM ADD mean the ADD lot beats all NEW, REENTRY, other ADD, and Cash alternatives? | No. |
| Does PM ADD define executable quantity? | No. |
| Does PM ADD own final target weight? | No. |

Architecture source-of-truth states that PM `ADD` is directional intent and that:

```text
ADD_DOES_NOT_IMPLY_BEST_GLOBAL_ALTERNATIVE = YES
```

Therefore PM is not defective merely because most ADD intents remain unfilled. The architecture gap is downstream: the system needs a Portfolio Construction-owned marginal capital value object that can decide whether the next ADD lot deserves scarce capital.

## Incremental Value Semantics

Existing artifacts preserve meaningful evidence:

| Evidence family | Present | Notes |
| --- | --- | --- |
| PM ADD intent | Yes | Frequent and persistent. |
| Campaign identity / continuation | Yes | Strong enough for repeated PM ADD. |
| Runtime opportunity score | Yes | 340/340 populated; continuous unique values. |
| Buy quality score | Yes | 340/340 populated; continuous values. |
| Current weight | Yes | 340/340 populated. |
| Target weight | Yes | 340/340 populated. |
| Accepted incremental weight | Yes | Field exists, but zero in 328/340 rows. |
| PC discrete executable quantity | Yes | Positive in 12/340 rows. |
| Cash / competition outcome | Partially | Capital competition exists, but not as common high-resolution cardinal value. |

Metric distribution for ADD rows:

| Metric | Min | p25 | Median | p75 | p90 | Max | Zero rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `runtime_opportunity_score` | 0.0577 | 0.2160 | 0.3627 | 0.4255 | 0.4864 | 0.6350 | 0.00% |
| `quality_score` | 0.6659 | 0.7661 | 0.7898 | 0.8013 | 0.8117 | 0.8281 | 0.00% |
| `current_weight` | 0.6993% | 2.0342% | 2.1134% | 2.5731% | 9.3670% | 20.0714% | 0.00% |
| `target_weight` | 0.6993% | 2.0342% | 2.1134% | 2.5731% | 9.5487% | 20.0714% | 0.00% |
| `target_minus_current` | 0.0000% | 0.0000% | 0.0000% | 0.0000% | 0.0000% | 8.4326% | 97.06% |
| `accepted_incremental_weight` | 0.0000% | 0.0000% | 0.0000% | 0.0000% | 0.0000% | 8.4326% | 96.47% |
| `lot_equiv_gap` | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 1.0166 | 96.47% |
| `pc_discrete_qty` | 0 | 0 | 0 | 0 | 0 | 100 | 96.47% |

Interpretation:

```text
The system has continuous quality / opportunity information,
but that resolution collapses before or at accepted incremental target weight.
```

The existing numeric target-weight fields are cardinal portfolio ratios, but they are not a common cardinal marginal value representation across semantic types. Current incremental value is best classified as:

```text
MIXED
```

It is numeric after capital allocation, but the semantic value inputs remain type-specific and partly ordinal/status-like.

## Resolution-Loss Analysis

Resolution is preserved at the evidence layer:

- 340 unique `runtime_opportunity_score` observations.
- 340 populated `quality_score` observations.
- persistent PM ADD campaigns.
- distinct current weights, ranks, quality, and campaign histories.

Resolution is lost at the capital-increment boundary:

- `target_minus_current` is zero in 97.06% of PM ADD rows.
- `accepted_incremental_weight` is zero in 96.47% of PM ADD rows.
- `pc_discrete_qty` is zero in 96.47% of PM ADD rows.
- maximum lot-equivalent ADD gap is only 1.0166 lots.
- observed ADD fills are all 100 shares.

The observed pattern is:

```text
many differentiated ADD intents
-> mostly unchanged target weights
-> mostly zero accepted increments
-> almost no executable ADD lots
```

This supports AO/AP: conviction-to-capital resolution is compressed. It does not support a narrow PS-only repair.

## Target-Gap < One-Lot Causes

Classified causes among PM ADD rows:

| Cause | Count | Interpretation |
| --- | ---: | --- |
| `zero_or_no_accepted_increment` | 328 | Primary cause. No incremental target gap exists to size. |
| `accepted_increment_below_one_lot_after_target_mapping` | 7 | Secondary cause. Some positive target increments are still below one lot. |
| `current_weight_at_or_above_target` | 1 | Existing position already meets/exceeds target. |

Primary target-gap diagnosis:

```text
Target gap < one lot is mainly caused by absent / zero accepted incremental weight, not by final lot rounding.
```

This is why multi-lot ADD cannot be safely created by simply changing lot conversion. The architecture first needs stronger target-gap authority, grounded in marginal capital value.

## Target-Weight Architecture

Current source-of-truth:

| Responsibility | Owner |
| --- | --- |
| Candidate opportunity validity / attractiveness | Candidate AI / BUY Quality |
| Existing-position action intent | Position Management |
| Capital budget / deployment posture | Portfolio Policy / Risk Pacing |
| Capital allocation and Cash frontier | Portfolio Construction |
| Target portfolio ratio / target weight | Portfolio Construction |
| Discrete target quantity / quantity delta | Position Sizing |
| Safety hard constraints | Safety authorities |
| Execution consumption | Runtime |

`target_weight` is a Portfolio Construction-owned target portfolio ratio. Position Sizing converts target weight into notional and discrete quantity using portfolio equity, investable capital, price, trading unit, current holdings, cap, and minimum-notional policy.

Position Sizing must not reinterpret opportunity scores as capital authority. That boundary is important. The current evidence shows Position Sizing generally consumes the target/increment it receives; it does not own the missing ADD value signal.

## NEW / REENTRY / ADD / Cash Semantic Matrix

| Alternative | Current semantic basis | Current comparability | Missing for high-resolution common comparison |
| --- | --- | --- | --- |
| NEW first lot | opportunity score/rank, BUY quality, entry quality, market context, risk pacing, lot feasibility | comparable enough for current PC selection | common next-lot marginal value against ADD and Cash |
| REENTRY first lot | prior-exit context, recovery/cooldown, opportunity, trend/momentum recovery, buy quality, PC competition | improved after prior Phase32 repairs; still type-specific | common marginal value vs NEW/ADD/Cash after re-entry recovery passes |
| ADD next lot | PM ADD intent, campaign continuation, existing position state, incremental investment/opportunity-cost evidence, cap/headroom, lot feasibility | partly comparable, but weaker common cardinal semantics | explicit next-lot object and diminishing marginal value |
| Cash / optionality | first-class capital alternative, deployment deferral, optionality | present as a frontier result, but often not explainable as common value | explicit Cash marginal utility / opportunity-cost comparator |

Current classification:

```text
NEW_ADD_VALUE_SEMANTICS = TYPE_SPECIFIC_SEMANTICS
FOUR_WAY_COMMON_VALUE_READY = PARTIAL
```

The evidence base is sufficient to design and shadow-test a common value layer. It is not yet production-authoritative as a common cardinal marginal value object.

## Released-Capital Root Cause

AP established that REDUCE/EXIT releases capital more often than ADD absorbs capital:

| Action | Intent/fill behavior |
| --- | --- |
| ADD | 340 PM ADD intents; 11 fills through AQ coverage |
| REDUCE | frequent partial de-risking; 52 fills through AP coverage |
| EXIT | near-direct full liquidation; 290 fills through AP coverage |

The released capital does not automatically flow to existing winners because ADD usually has no positive accepted increment. When released capital is available, NEW has clearer first-lot opportunity semantics and frequently receives executable plans on the same days that ADD rows remain target-unchanged.

Primary cause:

```text
Released capital is not suppressed by REDUCE/EXIT.
It is not reliably captured by ADD because ADD lacks a high-resolution next-lot marginal value / target-gap authority comparable to NEW and Cash.
```

## Same-Day Competition Cases

AQ observed 267 days with same-day ADD rows and NEW planning activity.

Representative patterns:

| Date | ADD status | NEW status | Interpretation |
| --- | --- | --- | --- |
| `2022-10-05` | 1 ADD row, 0 positive ADD | 6 NEW plans, including 94320 / 76920 / 99840 | NEW first-lot semantics can win while ADD target remains unchanged. |
| `2022-10-06` | 1 positive ADD, one-lot quantity | 3 NEW plans | ADD can win one lot, but not multi-lot. |
| `2022-10-07` | 2 ADD rows, 0 positive ADD | 4 NEW plans | ADD intent does not imply scarce-capital priority. |
| `2022-10-11` | 1 positive ADD | 1 NEW plan | ADD and NEW coexist; ADD remains one-lot. |
| `2022-10-12` | 2 positive ADD | 1 NEW plan | Positive ADD is possible but still low-resolution. |
| `2022-10-13` | 1 positive ADD | 5 NEW plans | NEW breadth remains easier to capitalize. |

These cases support a root architecture issue rather than a missing artifact lineage issue. ADD is present, competes, and sometimes wins, but the target-gap object rarely expresses more than zero or one lot.

## Winner vs Marginal NEW Cases

The artifact pattern does not prove that all NEW allocations are wrong. It proves a weaker but important point:

```text
Existing winners do not currently receive a common next-lot value challenge against marginal NEW opportunities.
```

For strong winners with repeated PM ADD, the system often preserves HOLD/ADD semantics while keeping target equal to current weight. Meanwhile, marginal NEW candidates can receive first-lot allocations because their semantic object is already naturally “new deployable capital.”

This creates architectural disadvantage for ADD:

- ADD must overcome current-position baseline semantics.
- ADD must produce an incremental target gap.
- ADD must remain below cap/headroom.
- ADD must beat competing allocations.
- ADD must survive lot feasibility.
- But ADD lacks an explicit high-resolution next-lot value representation.

The disadvantage is architectural, but not absolute. Positive ADD rows and fills exist. The correct judgment is:

```text
ADD_DISADVANTAGED_VS_NEW_BY_ARCHITECTURE = PARTIAL
```

## Next-Lot Semantics

Source-of-truth already defines the right future object:

```text
ADD must be evaluated as executable marginal increments.
Repeated ADD increments must be independently evaluable.
```

Conceptually, each of these should be a separate capital object:

```text
current quantity -> current quantity + 100
current quantity + 100 -> current quantity + 200
current quantity + 200 -> current quantity + 300
```

The object should preserve:

- semantic type: `BUY_ADD`;
- symbol and campaign identity;
- current quantity / current weight;
- executable increment size;
- current concentration / cap headroom;
- PM continuation and ADD intent evidence;
- opportunity / quality evidence;
- incremental investment / opportunity-cost evidence;
- Cash optionality comparison;
- strongest competing NEW / REENTRY / ADD alternative;
- marginal desirability separate from feasibility;
- final PC disposition and quantity authority.

Feasibility judgment:

```text
NEXT_LOT_OBJECT_FEASIBLE = YES
```

This is feasible as a shadow artifact because the required evidence families largely exist. It is not yet production-authoritative.

## Diminishing Marginal Value

The current architecture has partial ingredients for diminishing marginal value:

- current position weight;
- target weight;
- maximum position weight;
- current quantity and notional;
- lot feasibility;
- concentration/cap constraints;
- Cash optionality;
- PM continuation state.

What is missing is explicit authority for the value of the next additional lot after the first additional lot. Today, a strong ADD campaign can persist while all incremental value collapses to:

```text
0 lots
or
1 lot
```

There is no observed high-resolution sequence such as:

```text
next lot 1: high value
next lot 2: medium value
next lot 3: below Cash
```

Therefore:

```text
DIMINISHING_MARGINAL_VALUE_AUTHORITY_PRESENT = PARTIAL
```

Ingredients are present; the authoritative object is not.

## Concentration Guardrails

Any ADD improvement must preserve concentration and Safety guardrails.

Guardrails to keep:

- single-name maximum position weight;
- cap/headroom checks;
- risk pacing / deployment posture;
- MCC / PC capital competition;
- lot feasibility;
- hard Safety constraints;
- Cash optionality;
- no loss averaging;
- PM campaign and continuation evidence.

The audit does not justify bypassing caps or allowing ADD to win automatically. The target architecture should let strong winners scale only when the next lot remains superior after those guardrails.

## Starter / Confirmation / Scale Contract

AQ reaffirms AO's contract:

| Layer | Meaning |
| --- | --- |
| Starter | NEW / REENTRY can start small when opportunity evidence is valid. |
| Confirmation | PM and market evidence confirm the campaign remains strong. |
| Scale | ADD receives additional lots only when each next lot has superior marginal value versus alternatives. |

This is compatible with the user's stated principle:

```text
position count should be an output, not a fixed rule
```

It also avoids the opposite failure: forcing all winners to scale regardless of Cash, concentration, risk, or opportunity cost.

## Position-Count Principle

The evidence does not support a fixed number of holdings as a primary rule.

Position count should emerge from:

- available capital;
- valid opportunities;
- quality and expected edge;
- campaign strength;
- Cash optionality;
- current concentration;
- lot feasibility;
- Safety;
- marginal value comparison.

Therefore:

```text
POSITION_COUNT_AS_OUTPUT_PRINCIPLE = ACCEPT
```

The architecture should improve marginal capital value, not hard-code a target number of positions.

## REDUCE / EXIT Keep

AQ does not find a mandatory reason to weaken REDUCE or EXIT.

AP established that defensive response is stronger and faster, but also that:

- REDUCE has legitimate severity/fraction quantity authority;
- EXIT should remain able to release capital when PM evidence breaks;
- the strongest de-capitalization comes from EXIT finality, which is intended for broken positions;
- ADD weakness is attack-side capitalization, not proof that defense is wrong.

Therefore:

```text
REDUCE_KEEP = YES
EXIT_KEEP = YES
```

## Root Diagnosis

Candidate root causes:

| Candidate | Judgment | Evidence |
| --- | --- | --- |
| A. ADD eligibility too strict | Partial | PC ADD eligible appears in 20 rows, but major loss is accepted increment/target gap. |
| B. Value generation weak | Yes | ADD lacks common next-lot marginal capital value semantics. |
| C. Value normalization cross-type weak | Yes | NEW/ADD/REENTRY/Cash remain type-specific. |
| D. Conviction-to-target mapping weak | Yes | Continuous quality/opportunity collapses to zero target gap. |
| E. PC competition semantics favor NEW by default | Partial | NEW has clearer deployable first-lot semantics; ADD lacks next-lot value object. |
| F. Discrete lot rounding | Secondary | Some positive increments are below one lot, but 328 rows have zero/no increment. |
| G. Multi-stage combination | Primary | ADD scarcity emerges across semantics, target gap, competition, and lot feasibility. |

Primary diagnosis:

```text
G_MULTI_STAGE_COMBINATION
```

Secondary diagnosis:

```text
CROSS_TYPE_VALUE_SEMANTIC_GAP
CONVICTION_TO_TARGET_COMPRESSION
NEXT_LOT_COMPETITION_MISSING
ADD_VALUE_RESOLUTION_LOSS
```

## Minimal Architecture Boundary

The minimal future repair boundary should be:

```text
Portfolio Construction-owned Capital Value Authority
Portfolio Construction-owned target-gap authority for ADD next-lot objects
Shadow-only common marginal value artifact before production activation
```

Keep out of scope:

- PM ADD/REDUCE/EXIT action semantics;
- existing REENTRY logic;
- cooldown;
- MA5 or other new threshold tuning;
- Cash weakening;
- PC/MCC threshold changes;
- Risk Pacing changes;
- Position Sizing reinterpretation of scores;
- runtime recomputation;
- Safety weakening;
- REDUCE/EXIT throttling.

Position Sizing should continue to consume authoritative target/increment/quantity fields. It should not become the place where conviction is translated into capital priority.

## Shadow Readiness

AQ supports a shadow-only design / artifact step.

Recommended shadow artifact:

```text
add_next_lot_marginal_capital_value
```

Recommended common frontier:

```text
NEW first lot
REENTRY first lot
ADD next lot
Cash / optionality
```

Required properties:

- PIT-safe only;
- no historical outcome fitting;
- no threshold tuning from returns;
- separates desirability from feasibility;
- preserves raw evidence lineage;
- explains strongest rejected alternative;
- supports zero, one, or multiple ADD next-lot candidates;
- preserves Cash as a first-class winner;
- preserves concentration and Safety guardrails.

Readiness judgment:

```text
SHADOW_READINESS = READY_FOR_SHADOW_SPEC
```

## Defect Judgment

AQ finds no new mandatory production defect requiring immediate behavior change.

The current behavior is conservative and under-resolves ADD scaling, but it is consistent with the documented current/future architecture split:

- current PC can allocate among NEW / ADD / Cash;
- current high-resolution marginal capital value is explicitly deferred;
- PM ADD does not prove global capital priority;
- PS consumes capital authority rather than creating it.

The right next step is a shadow architecture spec, not direct production changes.

## Recommendation

Current long run should continue.

Rationale:

- no runtime halt;
- no state integrity issue identified;
- no mandatory strategy defect requiring immediate stop;
- AQ is an architecture audit, not an acceptance blocker;
- longer coverage remains valuable for observing ADD/NEW/Cash behavior across regimes.

Recommended next step:

```text
Draft a shadow-only Portfolio Construction capital value design for ADD next-lot marginal value and common NEW/REENTRY/ADD/Cash comparison.
Do not activate production allocation behavior until shadow evidence proves semantic clarity and guardrail preservation.
```

## Final Judgments

```text
PHASE32_AQ_RUN_ID = runtime-test-historical-extended-smoke-20260827T093649849074Z
PHASE32_AQ_COVERAGE_END = 2023-12-27

PHASE32_AQ_PM_ADD_INTENT_TOTAL = 340
PHASE32_AQ_ADD_FILL_TOTAL = 11
PHASE32_AQ_ADD_INTENT_TO_FILL_RATE = 3.24%
PHASE32_AQ_ADD_FIRST_MAJOR_DROPOFF = PM_ADD_INTENT_TO_POSITIVE_ACCEPTED_INCREMENTAL_TARGET_WEIGHT_AND_TARGET_GAP

PHASE32_AQ_PM_ADD_SEMANTICS = STRONG_CONTINUATION_AND_ADD_PERMISSIBLE_DIRECTIONAL_INTENT_ONLY_NOT_QUANTITY_OR_GLOBAL_CAPITAL_PRIORITY
PHASE32_AQ_INCREMENTAL_VALUE_CARDINALITY = MIXED
PHASE32_AQ_CONVICTION_RESOLUTION_LOSS_BOUNDARY = PORTFOLIO_CONSTRUCTION_ACCEPTED_INCREMENTAL_WEIGHT_AND_TARGET_GAP_MATERIALIZATION
PHASE32_AQ_TARGET_GAP_LT_ONE_LOT_PRIMARY_CAUSE = ZERO_OR_NO_ACCEPTED_INCREMENTAL_WEIGHT

PHASE32_AQ_NEW_ADD_VALUE_SEMANTICS = TYPE_SPECIFIC_SEMANTICS
PHASE32_AQ_FOUR_WAY_COMMON_VALUE_READY = PARTIAL
PHASE32_AQ_RELEASED_CAPITAL_ADD_SUPPRESSION_PRIMARY_CAUSE = ADD_TARGET_GAP_MATERIALIZATION_AND_CROSS_TYPE_VALUE_SEMANTIC_GAP_WITH_NEW_REPLACEMENT_DEFAULT
PHASE32_AQ_ADD_DISADVANTAGED_VS_NEW_BY_ARCHITECTURE = PARTIAL
PHASE32_AQ_NEXT_LOT_OBJECT_FEASIBLE = YES

PHASE32_AQ_DIMINISHING_MARGINAL_VALUE_AUTHORITY_PRESENT = PARTIAL
PHASE32_AQ_STARTER_CONFIRMATION_SCALE_CONTRACT = ACCEPT
PHASE32_AQ_POSITION_COUNT_AS_OUTPUT_PRINCIPLE = ACCEPT
PHASE32_AQ_REDUCE_KEEP = YES
PHASE32_AQ_EXIT_KEEP = YES

PHASE32_AQ_ROOT_DIAGNOSIS_PRIMARY = G_MULTI_STAGE_COMBINATION
PHASE32_AQ_ROOT_DIAGNOSIS_SECONDARY = CROSS_TYPE_VALUE_SEMANTIC_GAP;CONVICTION_TO_TARGET_COMPRESSION;NEXT_LOT_COMPETITION_MISSING;ADD_VALUE_RESOLUTION_LOSS
PHASE32_AQ_MINIMAL_ARCHITECTURE_BOUNDARY = PORTFOLIO_CONSTRUCTION_OWNED_CAPITAL_VALUE_AUTHORITY_AND_TARGET_GAP_AUTHORITY;PM_PS_RUNTIME_SAFETY_REDUCE_EXIT_KEEP
PHASE32_AQ_SHADOW_READINESS = READY_FOR_SHADOW_SPEC

PHASE32_AQ_NEW_MANDATORY_DEFECT_FOUND = NO
PHASE32_AQ_PRODUCTION_CHANGE_THIS_TASK = NO
PHASE32_AQ_LONG_RUN_CONTINUE = YES
PHASE32_AQ_NEXT_STEP = SHADOW_ONLY_ADD_NEXT_LOT_MARGINAL_CAPITAL_VALUE_AND_COMMON_NEW_REENTRY_ADD_CASH_FRONTIER_DESIGN
```
