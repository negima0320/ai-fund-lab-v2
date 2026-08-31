# Phase32-AO — Initial Sizing / Position Graduation Architecture Root-Cause Audit

## Scope

- Primary trusted run: `runtime-test-historical-extended-smoke-20260830T081425790243Z`
- Trusted window: `2022-10-03` through `2023-10-10`
- Business days: `252`
- Mode: READ-ONLY root-cause / architecture audit

No initial sizing, ADD, NEW, PC, Cash, Risk Pacing, caps, lot rules, thresholds, weights, source, config, runtime state, fresh-run, resume, replay, recover, design, implementation, or Production parameter recommendation was changed or executed.

Future outcomes and Historical PnL were not used to decide what should have happened.

## Evidence Read

- Phase32-AF through Phase32-AN
- Phase32-U/V/W/X Winner Retention reports
- Phase28/29 ADD, lot-first, residual-reallocation reports and roadmap entries
- Current Architecture / SoT:
  - `docs/00_vision/investment_philosophy.md`
  - `docs/03_ai_design/capital_deployment_design.md`
  - `docs/02_architecture/strategy_intelligence_architecture_v1.md`
  - `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`
  - `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- Current artifacts for Candidate/Opportunity, PM, SI, BQ, PC, PS, Runtime Planning, fills, campaign state, Risk Pacing, concentration/headroom, and lot sizing.

## Executive Summary

The current system behaves more like:

```text
REPLACE / STARTER_ROTATION
```

than:

```text
STARTER_THEN_GRADUATE
```

There is no explicit canonical `POSITION_GRADUATION` contract connecting:

```text
NEW starter
-> confirmed incumbent / durable winner
-> larger strategic position
```

Instead, graduation is implicit and distributed across PM ADD, Strategy PM/SI, ADD investment evidence, PC capital competition, residual reallocation, PS lot feasibility, and Runtime BUY_ADD.

Core facts:

| Metric | Result |
| --- | ---: |
| BUY_NEW fills / campaigns | `395` |
| 100-share BUY_NEW fills | `324` |
| campaigns never growing beyond initial quantity | `392` |
| campaigns with modest growth | `2` |
| campaigns with material growth | `1` |
| large winner capitalization | `0` |
| non-growing campaigns that did not establish durable strength | `387` |
| non-growing durable winners with plausible graduation evidence | `5` |
| durable winner material growth positive control | `94340`, `200 -> 500` |

Decision gate:

```text
INITIAL_SIZING_AND_GRADUATION_BOTH_MATERIAL
```

The architecture is not proven correctness-wrong. It is a performance architecture limitation: initial sizing creates many starter positions, and the later graduation mechanism is implicit, sparse, and often loses to Cash/NEW or fails before final ADD competition.

## A — Intended Investment Philosophy

Authoritative SoT evidence:

- Capital deployment design defines BUY as new-position target weight delta, ADD as existing-position target weight increase, REDUCE as target weight decrease, and EXIT as target weight zero.
- It also records `initial sizing formula` as an `OPEN_DESIGN_DECISION`, not a settled starter/graduation doctrine.
- Strategy Intelligence architecture separates Strategy desired allocation, one-lot execution, Safety cap, and residual destination. It states PC may admit `0 -> 1lot` for BUY_NEW/REENTRY only when guards pass, while BUY_ADD second-lot-plus expansion is not the same path.
- Phase28-D54/D55 lineage states PM ADD remains intent-only, PC owns economic desirability/target weights/opportunity cost/reallocation, PS owns price/trading-unit/min-notional/final quantity, and the design does not force one-lot purchases or forced cash utilization.
- Phase32-S states PC owns ADD acceleration tiering and continuous marginal capital magnitude, PS owns discrete executable quantity, and BUY_NEW/ADD/Cash remain separate authorities.

Classification:

```text
WHAT_IS_THE_CANONICAL_POSITION_GROWTH_PHILOSOPHY: HYBRID / UNDER-SPECIFIED
```

The docs support a hybrid philosophy: entry opens target exposure; ADD can increase existing exposure when incremental value is proven; Cash is valid when evidence is insufficient. But no SoT explicitly says the portfolio should run a starter-then-graduate lifecycle, and no SoT says it should permanently maintain broad one-lot starters either.

Implementation disagrees by omission: actual runtime behaves as starter-heavy replacement, while the architecture only has implicit graduation hooks.

## B — Graduation Definition

Existing concepts:

| Concept | Existing Meaning |
| --- | --- |
| starter position | not canonical; usually actual `BUY_NEW` 100-share / small-weight entry |
| established position | not canonical; inferable from campaign age, current return, continuation, BQ/rank |
| ADD | existing-position target weight / quantity increase path |
| target weight increase | PC-owned allocation change |
| incremental investment | ADD evidence: campaign, expected edge, incremental value, opportunity cost, no-loss |
| winner capitalization | not canonical as a lifecycle state |
| residual reallocation | PC-owned lot-aware final reallocation after PS feasibility |

Conclusion:

```text
NO_CANONICAL_POSITION_GRADUATION_CONCEPT_EXISTS
```

Graduation exists only as an implicit result if PM/SI/ADD evidence/PC/PS/Runtime all align.

## C — Initial BUY_NEW Sizing Funnel

Actual BUY_NEW fills:

| Quantity | Count |
| ---: | ---: |
| `100` | `324` |
| `200` | `30` |
| `300` | `16` |
| `400+` | `25` |

Initial BUY_NEW distribution:

| Field | Mean | Median | P25 | P75 |
| --- | ---: | ---: | ---: | ---: |
| PC/PS target weight | `6.16%` | `4.17%` | `2.86%` | `7.81%` |
| requested/accepted BUY_NEW weight | `3.08%` | `3.12%` | `2.63%` | `3.57%` |
| notional | `79,664` | `54,400` | `35,100` | `106,700` |
| share price | `746.64` | `503.00` | `267.00` | `1,067.00` |

BUY_NEW quality distribution:

| BQ / Band | Count |
| --- | ---: |
| `REDUCED_ALLOCATION_ONLY / MEDIUM` | `233` |
| `REDUCED_ALLOCATION_ONLY / LOW` | `124` |
| `REDUCED_ALLOCATION_ONLY / HIGH` | `36` |
| `FULL_ALLOCATION_ELIGIBLE / HIGH` | `2` |

BUY_NEW rank buckets:

| Rank Bucket | Count |
| --- | ---: |
| `1-5` | `17` |
| `6-10` | `22` |
| `11-20` | `81` |
| `>20 / NA` | `275` |

Primary first decisive causes for one-lot starts:

```text
PC_SMALL_TARGET_WEIGHT_OR_ONE_LOT_ADMISSION
+ BQ_REDUCTION
+ LOT_MATERIALIZATION
+ CASH/RISK competition
```

## D — 100 Shares: Intentional Starter or Execution Artifact

For the 324 100-share BUY_NEW fills:

| Classification | Count |
| --- | ---: |
| `INTENDED_ONE_LOT_STARTER` | `324` |
| `TARGET_WEIGHT_WAS_LARGER_BUT_ONE_LOT_MATERIALIZED` | `0` confirmed |
| `CAPITAL_CONSTRAINT_FORCED_ONE_LOT` | `0` confirmed as primary |
| `UNKNOWN` | `0` |

Interpretation:

The one-lot starts are not random execution accidents. They are the combined output of small accepted BUY_NEW weights, BQ-reduced allocation, PC one-lot admission, and PS lot feasibility. However, the SoT does not prove a philosophical intent to keep these positions small forever.

Answer:

```text
IS_100_SHARE_ENTRY_INTENTIONAL_OR_MOSTLY_AN_EXECUTION_ARTIFACT: INTENTIONAL_STARTER_MATERIALIZATION
```

## E — Initial Position Weight Differentiation

Quality comparison:

| Group | Count | Top-5 Rank | Median Qty | Dominant BQ |
| --- | ---: | ---: | ---: | --- |
| one-lot BUY_NEW | `324` | `10` | `100` | `REDUCED_ALLOCATION_ONLY / MEDIUM or LOW` |
| >100-share BUY_NEW | `71` | `7` | `200` | `REDUCED_ALLOCATION_ONLY / MEDIUM` |

Initial sizing does differentiate quality, but weakly. High-quality entries are rare in the initial fill set, and most fills are reduced-allocation entries regardless of rank.

Classification:

```text
DOES_INITIAL_SIZING_DIFFERENTIATE_OPPORTUNITY_QUALITY: WEAK
```

## F — Graduation Mechanism Inventory

Current mechanisms that can increase an existing campaign:

| Mechanism | Owner | Trigger / Evidence | Quantity Effect | Gates | Used in 252BD |
| --- | --- | --- | --- | --- | --- |
| Runtime PM ADD | Runtime PM | continuation/rank/no-loss/risk signal | intent only | Strategy PM/SI | YES, `118` broad ADD |
| Strategy PM ADD | Strategy PM | PM ADD plus structured ADD worthiness | PC-visible ADD | campaign, risk, prior ADD/REDUCE | YES, `99` PC ADD |
| SI ADD evidence | SI | `ADD_ALLOWED`, `ADD_REDUCED_ONLY`, continuation | evidence only | non-action-authoritative | YES |
| ADD investment evidence | Strategy ADD resolver | campaign, expected edge, incremental value, opportunity cost, no-loss | eligibility/value evidence | fail-closed | YES for ADD rows |
| PC ADD competitor | PC | `current_position=true`, `pm_action=ADD` | accepted incremental weight | Cash/NEW/Risk/quality | YES, sparse |
| PC residual reallocation | PC | skipped/remaining capital after lot feasibility | may reallocate to eligible candidates | no forced deployment | YES |
| PS BUY_ADD sizing | PS | PC target / discrete quantity authority | executable quantity delta | lot/cap/price | YES |
| Runtime BUY_ADD fill | Runtime | PS-bound BUY_ADD plan | actual quantity growth | submit/execution | YES, rare |

Answer:

```text
WHAT_CURRENT_MECHANISMS_CAN_GRADUATE_A_POSITION: PM ADD -> Strategy PM/SI -> ADD evidence -> PC ADD competitor -> PS BUY_ADD -> Runtime fill, plus PC residual reallocation when eligible.
```

There is no separate explicit graduation mechanism.

## G — 392 Non-Graduating Campaigns

Primary reason classification:

| Reason | Count |
| --- | ---: |
| `EXITED_BEFORE_GRADUATION` without durable strength | `279` |
| `NEVER_BECAME_STRONG` | `105` |
| `SHORT_LIVED` | `3` |
| `ADD_CONSIDERATION_BUT_REJECTED_OR_DIVERTED` durable no-growth | `5` |

Interpretation:

```text
387/392
```

non-growing campaigns correctly lack durable graduation evidence on current decision-time artifacts. The graduation architecture concern is concentrated in the `5` durable winners that did show plausible graduation evidence but stayed at/near initial quantity.

## H — Non-Winner Control Group

The system is good at preventing weak starters from becoming larger:

| Non-Winner / Weak Group | Count |
| --- | ---: |
| never established strong evidence | `385` |
| did not graduate | overwhelmingly yes |

Classification:

```text
STRONG_PROTECTION_AGAINST_BAD_GRADUATION
```

This is an existing strength that must be preserved. Any future graduation change must not simply scale weak starters.

## I — Seven Durable Winners Graduation Audit

| Symbol | Campaign | Growth | ADD Consideration | Actual PC ADD | What Prevented Graduation |
| --- | --- | --- | ---: | ---: | --- |
| `76470` | `pc-8b52b4c89fd002ad-76470-0001` | `1300 -> 1800` modest | `13` | `6` | initial ADDs worked, then prior ADD history gate plus Cash/NEW; no proven fresh renewal |
| `54010` | `pc-3aaff341fad7ae34-54010-0001` | `100 -> 100` | `12` | `6` | Cash/NEW plus PM HOLD-only after early ADD; ADD often fails before final deployment |
| `21340` | `pc-f3186b6520780cea-21340-0001` | `2200 -> 2200` | `13` | `9` | ADD exists but loses before final comparison; quantity does not increase |
| `43880` | `pc-df47de7d57274254-43880-0001` | `100 -> 100` | `13` | `12` | Cash dominance plus local risk/REDUCE; no retained quantity growth |
| `40520` | `pc-21eead760e37aeb3-40520-0001` | `100 -> 100` | `10` | `7` | NEW/Cash competition plus no retained ADD quantity growth |
| `94340` | `pc-f3bd989f40c52bdf-94340-0001` | `200 -> 500` material | `7` | `6` | positive control; later growth limited by Cash optionality |
| `77760` | `pc-9d71e709a18ea961-77760-0001` | `100 -> 100` | `5` | `0` | PM HOLD-only / no actual PC ADD competitor |

## J — 94340 Positive Control

`94340` proves the existing system can graduate a position when the chain aligns:

| Evidence | Result |
| --- | --- |
| initial quantity | `200` |
| max quantity | `500` |
| strong-state rows | `6` |
| ADD consideration rows | `7` |
| actual PC ADD rows | `6` |
| BUY_ADD fills | `2022-10-06`, `2022-10-12`, `2022-10-13`, each `100` shares |

Why it succeeded structurally:

- PM/Strategy PM emitted ADD early.
- PC materialized ADD competitor authority.
- PS converted accepted increment into executable BUY_ADD quantity.
- Runtime filled BUY_ADD against the same campaign.

Answer:

```text
Can the existing system already perform correct graduation under the right conditions? YES
```

This argues against a wholesale redesign.

## K — Starter -> Winner -> Graduation Transition

Classification:

```text
IMPLICIT_DISTRIBUTED_GRADUATION
```

Authority boundaries:

```text
Candidate/BQ/SI opportunity evidence
-> PM lifecycle / ADD intent
-> Strategy PM ADD worthiness
-> ADD investment evidence
-> PC target/increment/capital competition
-> PS lot quantity
-> Runtime Planning / Submit / Fill
```

There is no explicit transition contract from starter to confirmed incumbent to larger strategic position.

## L — Quality Confirmation After Entry

New information after entry:

- realized continuation
- campaign health
- current return / no-loss state
- BQ trajectory
- rank persistence/improvement
- momentum continuation
- SI state
- MFE/giveback
- risk behavior

Consumption result:

```text
DOES_POST_ENTRY_CONFIRMATION_MATERIALLY_AFFECT_POSITION_SIZE: RARELY
```

It is observed and sometimes converted to ADD consideration, but it rarely results in retained quantity growth.

## M — Starter Portfolio Saturation

Evidence:

- median positions: `11`
- median 100-share positions: `9`
- BUY_NEW fills on strong-incumbent days: `90`
- 100-share BUY_NEW fills on strong-incumbent days: `71`
- durable winners often retained headroom while NEW/Cash took the capital destination

Classification:

```text
STARTER_SATURATION_MATERIAL
```

Starter saturation consumes position slots, attention/capital competition capacity, and creates a persistent graduation burden.

## N — NEW Replacement vs Graduation

Actual behavior:

| Flow | Evidence |
| --- | --- |
| REPLACE / starter rotation | `395` BUY_NEW campaigns, `279` exited before graduation, `392` never grew |
| GRADUATE | only `3` campaigns grew at all; only `1` materially |
| HYBRID | architecture allows graduation but actual path is replacement-heavy |

Classification:

```text
REPLACE_HEAVY_HYBRID
```

## O — Capital Efficiency vs Philosophy

Actual capital flow on strong-incumbent days from AN:

| Destination | Days |
| --- | ---: |
| Cash | `44/66` |
| NEW | `22/66` |
| ADD | `0/66` |

This only partially matches the canonical philosophy. Cash validity and weak-starter protection match the philosophy. However, the lack of explicit graduation and persistent starter churn do not clearly match a compounding winner-capitalization philosophy.

Answer:

```text
DOES_ACTUAL_CAPITAL_FLOW_MATCH_CANONICAL_INVESTMENT_PHILOSOPHY: PARTIAL
```

## P — Role of Opportunity Scarcity

Opportunity scarcity prevents overstatement:

| Category | Count |
| --- | ---: |
| non-growing campaigns that did not establish durable strength | `387` |
| durable winners that failed or mostly failed graduation | `5` |
| positive/material growth control | `1` |
| modest growth case | `1` |

Most campaigns should not have grown. The real architecture concern is not 392 missed winners; it is that the few durable winners rarely graduate.

## Q — Model 2 Relevance

Classification:

```text
SUPPORTING_SEMANTIC_REFACTOR
```

Model 2 would not by itself solve graduation. It would improve the PM/SI/PC ADD consideration boundary and observability. The larger graduation issue also involves initial sizing, starter saturation, Cash/NEW competition, and lack of explicit starter-to-winner transition.

## R — Current Architecture Falsification

| Hypothesis | Evidence For | Evidence Against | Judgment |
| --- | --- | --- | --- |
| H0 starter-heavy architecture intentional and appropriate | weak starters mostly stay small; Cash valid; no forced deployment | SoT does not explicitly endorse permanent starter churn; durable winners rarely graduate | `PARTIAL` |
| H1 initial sizing too fragmented | 324/395 BUY_NEW fills are 100 shares; median NEW qty 100 | one-lot admission is often legitimate and quality-reduced | `SUPPORTED_AS_MATERIAL` |
| H2 initial sizing appropriate, graduation structurally weak | 387 non-winners correctly stay small; 5 durable winners fail to grow | initial sizing itself creates many starters | `SUPPORTED` |
| H3 both initial sizing and graduation contribute | observed data supports both | none material | `BEST_EXPLANATION` |
| H4 opportunity scarcity explains nearly all | only 7 durable winners; 0 deterministic fresh cases | does not explain durable winners failing to graduate | `PARTIAL` |
| H5 no explicit post-entry confirmation -> capital growth contract | no canonical `POSITION_GRADUATION`; graduation is distributed | 94340 shows implicit path can work | `SUPPORTED` |

## S — Existing Strengths To Preserve

Future work must preserve:

- weak candidates staying small
- no-loss averaging protection
- concentration/headroom controls
- Cash optionality
- Risk Pacing
- BUY_NEW quality gates
- Winner retention improvements from Phase32-X
- SELL independence
- lot feasibility and no forced one-lot / forced deployment
- fail-closed behavior
- PC final capital authority
- PS final quantity authority
- Runtime exact consumption of PS-bound order increments
- G129 BUY_ADD order-increment semantics

## T — Root-Cause Ranking

| Rank | Cause | Affected Campaigns | Confidence | Correctness Defect | Architecture Concern | Interaction |
| ---: | --- | --- | --- | --- | --- | --- |
| 1 | lack of explicit graduation contract | 5 durable no-growth winners; all campaigns structurally | HIGH | NO | YES | with ADD/Cash/NEW |
| 2 | starter fragmentation / one-lot initial sizing | 324 one-lot BUY_NEW; 392 non-growing campaigns | HIGH | NO | YES | with position slots/Cash |
| 3 | opportunity scarcity | 387 non-winners should not grow | HIGH | NO | YES | limits materiality |
| 4 | ADD graduation weakness | 99 PC ADD rows, rare retained quantity growth | MEDIUM-HIGH | NO | YES | with PC/PS/Cash |
| 5 | Cash competition / Risk Pacing | Cash 44/66 strong-incumbent days | MEDIUM-HIGH | NO | YES | with ADD insufficiency |
| 6 | NEW competition | NEW 22/66 strong-incumbent days; 90 NEW fills on strong days | MEDIUM | NO | YES | with fragmentation |
| 7 | PM/SI ADD semantics | HOLD-surfaced consideration and broad PM ADD | MEDIUM | NO | YES | with Model 2 |
| 8 | PC ADD eligibility / marginal comparison | many ADD rows blocked/insufficient | MEDIUM | NO | YES | with capital semantics |
| 9 | lot size | local one-lot materialization | MEDIUM | NO | YES locally | with initial sizing |
| 10 | caps/headroom | not primary | LOW-MEDIUM | NO | local | local |
| 11 | prior ADD history | material for `76470`, harm unproven | MEDIUM | NO | local | with safeguards |

## U — Decision Gate

Chosen:

```text
INITIAL_SIZING_AND_GRADUATION_BOTH_MATERIAL
```

No design or implementation is authorized by AO.

## Required Final Answers

1. `WHAT_IS_THE_CANONICAL_POSITION_GROWTH_PHILOSOPHY`

```text
HYBRID / UNDER-SPECIFIED
```

2. `IS_100_SHARE_ENTRY_INTENTIONAL_OR_MOSTLY_AN_EXECUTION_ARTIFACT`

```text
INTENTIONAL_STARTER_MATERIALIZATION, not random execution artifact.
```

3. `WHY_ARE_SO_MANY_NEW_POSITIONS_ONE_LOT`

```text
Small accepted BUY_NEW weights, reduced BQ allocations, PC one-lot admission, PS lot feasibility, and Cash/Risk competition combine to materialize many 100-share entries.
```

4. `DOES_INITIAL_SIZING_DIFFERENTIATE_OPPORTUNITY_QUALITY`

```text
WEAK
```

5. `WHAT_CURRENT_MECHANISMS_CAN_GRADUATE_A_POSITION`

```text
PM ADD -> Strategy PM/SI -> ADD investment evidence -> PC ADD competitor / residual reallocation -> PS BUY_ADD quantity -> Runtime BUY_ADD fill.
```

6. `WHY_DID_392_OF_395_CAMPAIGNS_NEVER_GROW`

```text
Mostly because 387 never established durable graduation evidence or were short-lived/exited before graduation; 5 durable winners had plausible graduation evidence but ADD/Cash/NEW/PM-SI boundaries prevented quantity growth.
```

7. `HOW_MANY_OF_THE_392_CORRECTLY_SHOULD_NOT_HAVE_GROWN`

```text
387 on current decision-time evidence.
```

8. `HOW_MANY_SHOW_PLAUSIBLE_GRADUATION_EVIDENCE`

```text
5 durable no-growth campaigns; 3 short-lived/partial cases are watch-only.
```

9. `WHAT_PREVENTED_THE_7_DURABLE_WINNERS_FROM_GRADUATING`

```text
76470: prior ADD gate plus Cash/NEW after initial adds
54010: Cash/NEW plus PM HOLD-only after early ADD
21340: ADD exists but loses before final comparison / no retained quantity growth
43880: Cash dominance plus local risk/REDUCE
40520: NEW/Cash competition plus no retained ADD quantity growth
94340: did graduate materially; later Cash optionality limited further growth
77760: PM HOLD-only / no actual PC ADD competitor
```

10. `WHY_DID_94340_SUCCEED_AS_THE_POSITIVE_CONTROL`

```text
PM/Strategy PM emitted ADD, PC materialized ADD authority, PS produced executable BUY_ADD deltas, and Runtime filled three same-campaign BUY_ADD lots.
```

11. `IS_THERE_AN_EXPLICIT_STARTER_TO_WINNER_GRADUATION_CONTRACT`

```text
NO — IMPLICIT_DISTRIBUTED_GRADUATION only.
```

12. `DOES_POST_ENTRY_CONFIRMATION_ACTUALLY_INCREASE_POSITION_SIZE`

```text
RARELY
```

13. `IS_STARTER_SATURATION_MATERIAL`

```text
YES — STARTER_SATURATION_MATERIAL
```

14. `IS_THE_SYSTEM_BEHAVING_MORE_LIKE_REPLACE_OR_GRADUATE`

```text
REPLACE_HEAVY_HYBRID
```

15. `DOES_ACTUAL_CAPITAL_FLOW_MATCH_THE_INVESTMENT_PHILOSOPHY`

```text
PARTIAL
```

16. `IS_MODEL2_MATERIAL_TO_GRADUATION`

```text
SUPPORTING_SEMANTIC_REFACTOR, not sufficient alone.
```

17. `WHICH_HYPOTHESIS_H0_H5_BEST_EXPLAINS_THE_EVIDENCE`

```text
H3 — both initial sizing and graduation contribute.
```

18. `WHAT_EXISTING_STRENGTHS_MUST_BE_PRESERVED`

```text
weak starters staying small, no-loss averaging, concentration/headroom controls,
Cash optionality, Risk Pacing, BUY_NEW quality, Winner retention, SELL independence,
lot feasibility, fail-closed behavior, PC final capital authority, PS quantity authority,
Runtime exact consumption, and G129 BUY_ADD semantics.
```

19. `IS_ANY_PRODUCTION_CHANGE_JUSTIFIED_YET`

```text
NO
```

20. `WHAT_IS_THE_NEXT_HIGHEST_VALUE_INVESTIGATION`

```text
Define and shadow-audit an explicit starter-to-winner graduation contract:
entry sizing intent -> post-entry confirmation -> ADD consideration -> PC/Cash/NEW competition -> retained quantity growth,
while preserving weak-starter protection and no forced deployment.
```

## Final Judgment

```text
PHASE32_AO_INITIAL_SIZING_AND_GRADUATION_BOTH_MATERIAL_NO_PRODUCTION_CHANGE_YET
```

The current architecture is starter-heavy and graduation-light. Most non-growing campaigns correctly lacked durable strength, which is an important strength. The real bottleneck is concentrated in the small set of durable winners: initial sizing often creates one-lot starters, while no explicit graduation contract reliably converts post-entry confirmation into larger retained positions. Existing ADD can graduate positions, as `94340` proves, but the path is implicit and too sparse to support consistent winner capitalization.
