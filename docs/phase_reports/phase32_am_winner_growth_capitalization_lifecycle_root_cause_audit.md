# Phase32-AM — Winner Growth / Capitalization Lifecycle Root-Cause Audit

## Scope

- Primary trusted run: `runtime-test-historical-extended-smoke-20260830T081425790243Z`
- Trusted window: `2022-10-03` through `2023-10-10`
- Business days: `252`
- Mode: READ-ONLY root-cause characterization

No Strategy, ADD, HOLD, REDUCE/EXIT, NEW, Cash, Risk Pacing, caps, thresholds, weights, source, config, runtime state, fresh-run, resume, replay, recover, design, implementation, or Production parameter recommendation was changed or executed.

Future outcomes were not used to decide what the system should have done. Any forward outcome references from earlier phases remain `POST_HOC_DIAGNOSTIC_ONLY`.

## Evidence Read

- Phase32-AF through Phase32-AL reports
- Winner retention reports Phase32-U/V/W/X
- Current artifacts from the target run:
  - `strategy/portfolio_construction.json`
  - `strategy/position_management.json`
  - `position_management/pm_decisions.json`
  - `strategy/buy_quality_decisions.json`
  - `strategy/strategy_intelligence.json`
  - `strategy/position_sizing.json`
  - `execution/fills.json`
  - `positions/position_campaigns.json`
- Current source contracts for PM, SI, BQ, ADD evidence, PC, PS, and Runtime planning

## Executive Summary

Weak winner capitalization is real in the trusted 252BD evidence, but no single mechanism explains it.

Campaign-level result:

| Metric | Count |
| --- | ---: |
| campaigns observed | `395` |
| `DURABLE_WINNER_STATE` campaigns | `7` |
| `SHORT_LIVED_STRENGTH` campaigns | `3` |
| `NEVER_ESTABLISHED_WINNER` campaigns | `385` |
| durable winners with material quantity growth | `1` |
| durable winners with modest growth | `1` |
| durable winners near/at initial quantity | `5` |

Portfolio-level result:

| Daily Fragmentation Metric | Average | Median | Max |
| --- | ---: | ---: | ---: |
| positions | `10.90` | `11` | `19` |
| positions at 100 shares | `9.39` | `9` | `17` |
| positions >100 shares | `1.51` | `1` | `4` |
| positions >2x initial quantity | `0.15` | `0` | `1` |
| positions >5x initial quantity | `0.00` | `0` | `0` |
| top-1 weight | `17.07%` | `16.65%` | `32.84%` |
| top-3 weight | `41.91%` | `41.77%` | `65.78%` |
| median position weight | `5.65%` | `5.51%` | `15.10%` |

Fragmentation classification:

```text
HIGH_FRAGMENTATION
```

Winner capitalization funnel for durable-winner strong-state rows:

| First Decisive Boundary | Count |
| --- | ---: |
| `CASH_PREFERRED` | `26` |
| `PM_HOLD_ONLY` | `20` |
| `LOST_TO_NEW` | `10` |
| `PRIOR_ADD_GATE` | `7` |
| `NO_ADD_CONSIDERATION` | `2` |

Change necessity gate:

```text
MIXED_CAUSES
```

Weak winner capitalization is a material plateau contributor, but it is not reducible to "ADD is broken." The evidence points to a combined architecture/performance pattern:

```text
few durable winners
+ high 100-share fragmentation
+ slow/rare quantity growth
+ Cash preference on many durable-winner days
+ NEW winning over incumbents
+ PM/SI ADD consideration boundary
+ prior ADD safeguard in one repeated campaign
```

## A — Winner Growth Lifecycle Framework

Decision-time-compatible lifecycle states:

| State | Existing Evidence Basis |
| --- | --- |
| `ENTRY` | BUY_NEW/REENTRY fill, campaign id, initial quantity/weight |
| `EARLY_CONFIRMATION` | positive current return, BQ PASS, continuation quality improving |
| `ESTABLISHED_WINNER` | repeated top-rank/BQ HIGH/positive-return/continuation PASS state |
| `CAPITALIZATION_OPPORTUNITY` | ADD consideration evidence: PM ADD or held HOLD with SI/BQ/opportunity ADD-like evidence |
| `POSITION_GROWTH` | quantity or position weight materially increases |
| `DEACCELERATION` | PM REDUCE, SI caution, deterioration/profit-protection/risk evidence |
| `REDUCE` | PM/PS/Runtime sell-side partial reduction authority |
| `EXIT` | PM/Runtime full close authority |

No new Production thresholds are proposed. For audit only, `DURABLE_WINNER_STATE` is identified by repeated contemporaneous strong-state evidence: BQ `FULL_ALLOCATION_ELIGIBLE/HIGH`, top-5 rank, positive current campaign return, continuation PASS, and no hard downside block.

## B — Campaign Inventory Summary

Growth over all observed campaigns:

| Growth Class | Count |
| --- | ---: |
| `NEVER_GREW_BEYOND_INITIAL` | `392` |
| `MODEST_GROWTH` | `2` |
| `MATERIAL_GROWTH` | `1` |
| `LARGE_WINNER_CAPITALIZATION` | `0` |

Winner-state classification:

| Winner State | Count |
| --- | ---: |
| `DURABLE_WINNER_STATE` | `7` |
| `SHORT_LIVED_STRENGTH` | `3` |
| `NEVER_ESTABLISHED_WINNER` | `385` |
| `AMBIGUOUS` | `0` |

Durable winner inventory:

| Symbol | Campaign | Entry | Exit Evidence Date | Days Held | Initial Qty | Max Qty | Initial Wt | Max Wt | ADD Rows | REDUCE Rows | EXIT Rows | Strong Days | ADD Consideration Rows | Growth |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `76470` | `pc-8b52b4c89fd002ad-76470-0001` | `2022-11-28` | `2023-01-24` | `39` | `1300` | `1800` | `3.11%` | `4.71%` | `6` | `0` | `1` | `13` | `13` | `MODEST_GROWTH` |
| `54010` | `pc-3aaff341fad7ae34-54010-0001` | `2023-01-23` | `2023-04-05` | `51` | `100` | `100` | `4.67%` | `5.44%` | `6` | `0` | `1` | `13` | `12` | `NEVER_GREW_BEYOND_INITIAL` |
| `21340` | `pc-f3186b6520780cea-21340-0001` | `2023-06-06` | `2023-07-07` | `24` | `2200` | `2200` | `3.33%` | `5.06%` | `9` | `0` | `1` | `12` | `13` | `NEVER_GREW_BEYOND_INITIAL` |
| `43880` | `pc-df47de7d57274254-43880-0001` | `2023-03-17` | `2023-04-10` | `16` | `100` | `100` | `10.35%` | `10.35%` | `12` | `2` | `1` | `9` | `13` | `NEVER_GREW_BEYOND_INITIAL` |
| `40520` | `pc-21eead760e37aeb3-40520-0001` | `2023-06-16` | `2023-07-14` | `21` | `100` | `100` | `6.88%` | `9.41%` | `7` | `2` | `1` | `7` | `10` | `NEVER_GREW_BEYOND_INITIAL` |
| `94340` | `pc-f3bd989f40c52bdf-94340-0001` | `2022-10-04` | `2022-12-07` | `44` | `200` | `500` | `2.85%` | `7.06%` | `6` | `0` | `1` | `6` | `7` | `MATERIAL_GROWTH` |
| `77760` | `pc-9d71e709a18ea961-77760-0001` | `2023-02-01` | `2023-02-16` | `12` | `100` | `100` | `3.18%` | `3.18%` | `0` | `1` | `1` | `5` | `5` | `NEVER_GREW_BEYOND_INITIAL` |

## C — How Many Winners Existed

```text
WERE_THERE_ENOUGH_DURABLE_WINNERS_TO_CAPITALIZE: PARTIAL / LIMITED_SUPPLY
```

There were enough durable winners to make weak capitalization material, but not enough to explain the whole plateau as a simple "many winners ignored" problem. Only `7` campaigns reached durable winner state in 252BD, and only `65` campaign-days met the strict strong-state standard.

## D — Winner Size Growth

Durable winner summary:

| Result | Count |
| --- | ---: |
| grew materially in quantity | `1` |
| grew modestly | `1` |
| remained near/at initial size | `5` |

Answer:

```text
Strong campaigns generally did not grow materially in quantity allocation.
```

Some weights rose through price appreciation, but quantity rarely increased after entry.

## E — 100-Share Fragmentation

The portfolio was structurally dominated by small positions:

- median daily position count: `11`
- median daily 100-share positions: `9`
- median daily positions above 100 shares: `1`
- max daily positions above 2x initial quantity: `1`
- no positions exceeded 5x initial quantity

Classification:

```text
HIGH_FRAGMENTATION
```

This supports a fragmentation/capitalization concern: the portfolio often opens and holds many small positions, while very few campaigns compound into larger quantities.

## F — Winner Capitalization Funnel

For durable-winner strong-state rows:

```text
strong position identified: 65
-> ADD consideration evidence: 63
-> actual PC ADD authority: 40
-> HOLD-surfaced consideration only: 28
-> decisive first losses:
   CASH_PREFERRED: 26
   PM_HOLD_ONLY: 20
   LOST_TO_NEW: 10
   PRIOR_ADD_GATE: 7
   NO_ADD_CONSIDERATION: 2
-> material quantity growth: 1 campaign
```

Representative boundaries:

| Boundary | Representative Evidence |
| --- | --- |
| `CASH_PREFERRED` | `54010` ADD rows on `2023-02-15` to `2023-02-17`; winner Cash despite strong BQ/rank/current return. |
| `PM_HOLD_ONLY` | `77760` rows `2023-02-02` to `2023-02-09`; SI/BQ/rank strong but Strategy/PC PM action HOLD. |
| `LOST_TO_NEW` | `54010` `2023-02-20`, `21340` `2023-06-16/20`; PC winner NEW. |
| `PRIOR_ADD_GATE` | `76470` `2022-12-07` onward; prior ADD history count `5` blocks increment while strong evidence remains observable. |
| `NO_ADD_CONSIDERATION` | rare rows such as `54010` `2023-02-24` with SI `NO_ADD`. |

## G — NEW vs Winner Capital Allocation

On all `66` days with at least one durable-winner strong-state row, NEW competitors were present.

Actual winner distribution on durable-winner days:

| Actual Winner | Days |
| --- | ---: |
| `CASH_OPTIONALITY` | `44` |
| `NEW_BUY` | `22` |
| `ADD` | `0` |

Classification:

```text
NEW_FRAGMENTATION_BIAS_CONFIRMED_AS_CONTRIBUTING_CAUSE
```

This does not mean NEW choices were irrational. It means actual allocation repeatedly opened or favored NEW/Cash while durable incumbents rarely received quantity growth.

## H — Cash vs Winner Capitalization

Cash state on durable-winner days:

| Cash State | Days |
| --- | ---: |
| `OPTIONALITY_ELEVATED` | `35` |
| `OPTIONALITY_NEUTRAL` | `25` |
| `OPTIONALITY_LOW` | `6` |

Classification:

```text
CASH_CONTRIBUTES_TO_UNDERCAPITALIZATION
```

with caveat:

```text
MIXED
```

Cash often won when ADD candidates were already marginal, blocked, or not represented as actual ADD competitors. Therefore Cash is part of the observed bottleneck, but the root is not simply "Cash too high"; it is Cash interacting with ADD scarcity/representation and NEW competition.

## I — REDUCE During Winner State

Strong-state REDUCE evidence was limited:

| Symbol | Campaign | REDUCE While Strong | Total REDUCE | Strong Days |
| --- | --- | ---: | ---: | ---: |
| `43880` | `pc-df47de7d57274254-43880-0001` | `1` | `2` | `9` |

Classification:

```text
IS_WINNER_GROWTH_BEING_ERODED_BY_REDUCE: MINOR / NOT_PRIMARY
```

REDUCE is not the primary winner-growth bottleneck in this 252BD evidence.

## J — EXIT During Winner State

No EXIT row met the strict strong-state condition in the durable-winner audit.

Classification:

```text
ARE_WINNERS_EXITED_BEFORE_CAPITALIZATION_COMPLETES: NOT_PRIMARY_IN_CURRENT_252BD_EVIDENCE
```

This does not reopen Phase32-V/W concerns. Phase32-X improved soft deterioration semantics, and the current 252BD evidence does not show EXIT as the main capitalization limiter.

## K — Position Growth vs Deacceleration Asymmetry

Observed asymmetry:

- durable winners can show many strong days and ADD consideration rows
- actual quantity growth is rare
- REDUCE/EXIT eventually occurs for all seven durable winners in the observed campaign windows
- very few campaigns reach 2x initial quantity; none reach 5x

Classification:

```text
ASYMMETRY_CONFIRMED
```

The asymmetry is now more about slow/weak acceleration and capital competition than about a dominant premature EXIT defect.

## L — Winner Retention After Phase32-X

Phase32-X introduced episode-scoped recoverable deterioration and non-emergency EXIT confirmation. In this target run through `2023-10-10`, REDUCE/EXIT do not appear to be the primary blocker of durable winner capitalization.

Answer:

```text
Winner retention is improved enough that capitalization is now a material next bottleneck,
but retention should remain monitored.
```

## M — Position Cap / Headroom

Caps and lot size do not explain most weak growth:

- durable winners often had max weights below the 18% single-name cap
- only `43880` and high-weight incumbents approached meaningful concentration levels, but still did not show broad cap-driven evidence
- 100-share discreteness is material for small increments, but the portfolio-level pattern is broader than lot-size infeasibility
- no daily position exceeded 5x initial quantity; only one position at a time exceeded 2x initial quantity

Classification:

```text
ARE_CAPS_ACTUALLY_PREVENTING_WINNER_GROWTH: NO_AS_PRIMARY_CAUSE
```

Caps/lot size are local constraints, not the dominant root cause.

## N — Risk Pacing / Market Quality

Risk Pacing/Cash optionality is material:

- Cash won on `44/66` durable-winner days.
- Cash optionality was elevated on `35/66` durable-winner days.
- AF/AG showed Cash often beat already-marginal or non-deployable ADD candidates.

Classification:

```text
RISK_PACING_MARKET_QUALITY: MIXED
```

It is not proven inappropriate, but it contributes to undercapitalization when winner ADD evidence is weakly represented or non-deployable.

## O — Opportunity Scarcity

Opportunity scarcity is material:

| Metric | Result |
| --- | ---: |
| durable winner campaigns | `7` |
| short-lived strength campaigns | `3` |
| never-established campaigns | `385` |
| deterministic fresh incremental opportunities from AL | `0` |
| AL plausible-but-ambiguous freshness cases | `3` |

Classification:

```text
IS_OPPORTUNITY_SCARCITY_THE_MAIN_EXPLANATION: MATERIAL_BUT_NOT_SOLE
```

Scarcity prevents blaming only ADD routing. But scarcity alone does not explain why several durable winners had repeated ADD consideration and still rarely grew.

## P — Representative Winner Case Studies

| Case | Evidence | Interpretation |
| --- | --- | --- |
| successful material growth: `94340` | initial `200`, max `500`, 6 ADD rows, 6 strong days | The system can capitalize a winner sometimes, but not to large-winner scale. |
| modest growth then gate: `76470` | initial `1300`, max `1800`, 6 ADD rows, later prior ADD history count `5`, 13 strong days | Prior ADD gate preserved; opportunity observation can persist while increment is blocked. |
| strong but no quantity growth: `54010` | initial/max `100`, 13 strong days, 12 ADD consideration rows | Cash/NEW and PM/SI boundaries limit capitalization. |
| strong but no quantity growth: `21340` | initial/max `2200`, 12 strong days, 13 ADD consideration rows | Repeated ADD consideration without quantity growth; NEW/Cash competition material. |
| short durable burst: `77760` | initial/max `100`, 5 strong days, 5 HOLD-surfaced considerations | PM HOLD-only boundary; no actual PC ADD authority. |
| high weight no growth: `43880` | initial/max `100`, max weight `10.35%`, 12 ADD rows, 2 REDUCE rows | local risk/concentration and REDUCE interact, but not broad cap proof. |
| fragmented/no ADD scale: `40520` | initial/max `100`, max weight `9.41%`, 7 ADD rows | repeated ADD rows do not translate into quantity growth. |

## Q — Plateau Link

Plateau context from AF:

- average Apr-Oct 2023 cash fraction approximately `23.2%`
- max cash fraction approximately `66.6%`
- no material unresolved/stuck-capital mechanism reproduced

AM adds:

- high fragmentation
- only 7 durable winners
- only 1 material quantity-growth durable winner
- Cash/NEW dominate durable-winner days
- ADD consideration exists but rarely converts to retained quantity growth

Classification:

```text
IS_WEAK_WINNER_CAPITALIZATION_A_MATERIAL_CAUSE_OF_THE_PLATEAU: MATERIAL_CONTRIBUTING_CAUSE
```

Not primary by itself, because durable winner supply is limited and Cash/Risk/NEW competition also matter.

## R — Root-Cause Ranking

| Rank | Cause | Affected Evidence | Confidence | Correctness Defect | Performance Architecture Concern | Mitigated by Phase32-X |
| ---: | --- | --- | --- | --- | --- | --- |
| 1 | opportunity scarcity / few durable winners | only `7` durable winners; `0` deterministic fresh incremental opportunities | HIGH | NO | YES | NO |
| 2 | high portfolio fragmentation | median `9` positions at 100 shares; only `1` material growth campaign | HIGH | NO | YES | NO |
| 3 | Cash/Risk Pacing interaction | Cash winner on `44/66` durable-winner days | MEDIUM-HIGH | NO | YES | NO |
| 4 | PM/SI ADD consideration boundary | `28` HOLD-surfaced ADD consideration rows; `20` durable strong rows first lost at PM HOLD-only | MEDIUM-HIGH | NO | YES | NO |
| 5 | NEW competition | NEW winner on `22/66` durable-winner days; durable winners always had NEW competitors present | MEDIUM | NO | YES | NO |
| 6 | prior ADD history | `76470` repeated gate, `7` durable strong rows | MEDIUM | NO | YES / safeguard tradeoff | NO |
| 7 | PC ADD competition / ADD evidence fail-closed | AG/AF ADD funnel shows many ADD rows blocked/insufficient | MEDIUM | NO | YES | NO |
| 8 | caps / lot size | local constraints present, not primary in durable winners | LOW-MEDIUM | NO | YES locally | NO |
| 9 | premature REDUCE | only one strict strong-state REDUCE row | LOW | NO | WATCH | YES partly |
| 10 | premature EXIT | no strict strong-state EXIT rows in durable-winner audit | LOW | NO | WATCH | YES partly |

## S — Change Necessity Gate

Chosen classification:

```text
MIXED_CAUSES
```

Production change is not justified yet. The next work should continue characterization and shadow-contract validation rather than changing parameters or behavior.

## Required Final Answers

1. `HOW_MANY_DURABLE_WINNERS_EXISTED`

```text
7
```

2. `HOW_MANY_GREW_MATERIALLY_IN_QUANTITY_OR_WEIGHT`

```text
1 material quantity-growth campaign; 2 if modest growth is included.
```

3. `HOW_MANY_STRONG_WINNERS_REMAINED_AT_OR_NEAR_INITIAL_SIZE`

```text
5
```

4. `IS_THE_PORTFOLIO_STRUCTURALLY_FRAGMENTED`

```text
YES — HIGH_FRAGMENTATION
```

5. `WHAT_IS_THE_WINNER_CAPITALIZATION_FUNNEL`

```text
65 durable-winner strong rows
-> 63 ADD consideration rows
-> 40 actual PC ADD authority rows plus 28 HOLD-surfaced consideration rows
-> first losses: CASH_PREFERRED 26, PM_HOLD_ONLY 20, LOST_TO_NEW 10, PRIOR_ADD_GATE 7, NO_ADD_CONSIDERATION 2
-> 1 material quantity-growth durable campaign
```

6. `DOES_NEW_COMPETITION_PREVENT_WINNER_GROWTH`

```text
YES_AS_CONTRIBUTING_CAUSE
```

7. `DOES_CASH_PREVENT_WINNER_GROWTH`

```text
YES_AS_CONTRIBUTING_CAUSE / MIXED
```

8. `DOES_RISK_PACING_PREVENT_WINNER_GROWTH`

```text
MIXED; material interaction with Cash optionality, not proven inappropriate.
```

9. `DO_CAPS_OR_LOT_SIZE_PREVENT_WINNER_GROWTH`

```text
NOT_AS_PRIMARY_CAUSE
```

10. `ARE_REDuce_ACTIONS_ERODING_WINNERS`

```text
MINOR / NOT_PRIMARY
```

11. `ARE_EXIT_ACTIONS_ERODING_WINNERS`

```text
NOT_PRIMARY_IN_CURRENT_252BD_EVIDENCE
```

12. `IS_SLOW_ACCELERATION_FAST_DEACCELERATION_STILL_PRESENT`

```text
YES — ASYMMETRY_CONFIRMED
```

The current asymmetry is mainly slow/weak capitalization rather than a dominant premature EXIT failure.

13. `IS_OPPORTUNITY_SCARCITY_THE_MAIN_EXPLANATION`

```text
MATERIAL_BUT_NOT_SOLE
```

14. `IS_WEAK_WINNER_CAPITALIZATION_A_MATERIAL_CAUSE_OF_THE_PLATEAU`

```text
YES — MATERIAL_CONTRIBUTING_CAUSE
```

15. `WHAT_ARE_THE_TOP_ROOT_CAUSES_IN_ORDER`

```text
1. limited durable winner supply / opportunity scarcity
2. high 100-share portfolio fragmentation
3. Cash/Risk Pacing interaction
4. PM/SI ADD consideration boundary
5. NEW competition against incumbents
6. prior ADD history safeguard in specific campaigns
7. PC ADD evidence fail-closed / marginal-capital semantic gap
8. caps/lot size as local constraints
9. premature REDUCE/EXIT as residual watch items
```

16. `IS_MODEL2_ADD_SEMANTIC_REFACTOR_STILL_MATERIAL_AFTER_THIS_WIDER_AUDIT`

```text
YES_AS_MATERIAL_CONTRIBUTING_TRACK
```

It is not the only bottleneck, but the PM/SI/PC ADD consideration boundary remains materially relevant.

17. `IS_ANY_PRODUCTION_CHANGE_JUSTIFIED_YET`

```text
NO
```

18. `WHAT_SHOULD_BE_INVESTIGATED_NEXT`

```text
Validate a deterministic freshness/capitalization shadow contract at campaign level:
durable winner recognition -> ADD consideration -> PC/Cash/NEW competition -> retained quantity growth,
with explicit separation of opportunity scarcity, Cash/Risk Pacing, NEW fragmentation, and ADD semantic routing.
```

## Final Judgment

```text
PHASE32_AM_WINNER_CAPITALIZATION_MIXED_CAUSES_ROOT_CAUSE_CHARACTERIZED
```

Weak winner capitalization is a material contributor to the plateau, but the root cause is mixed. The dominant evidence is limited durable winner supply plus high fragmentation and Cash/NEW competition, with Model 2 ADD semantic refactor still material as a contributing track. REDUCE/EXIT are not the primary current bottleneck after Phase32-X evidence, and no Production behavior change is justified yet.
