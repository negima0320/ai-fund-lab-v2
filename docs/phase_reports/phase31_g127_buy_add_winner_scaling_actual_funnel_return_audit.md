# Phase31-G127 — BUY_ADD Winner Scaling Actual Funnel Return Audit

## Judgment

FINAL_DECISION =
`G127_BUY_ADD_WINNER_SCALING_DEFECT_CONFIRMED_READY_FOR_REPAIR`

PRIMARY_JUDGMENT:

BUY_ADD Winner Scaling is not design-conformant in the actual production-common path. PM does identify ADD candidates, and G115/PC can authorize one-increment ADDs without taking quantity ownership from PS. However, most authorized ADDs do not materialize as fills, and the few actual BUY_ADD fills are not materialized into canonical same-campaign BUY / ADD history in the latest campaign artifact.

The main confirmed boundaries are:

1. Runtime BUY_ADD / Submit: `74` PM-linked authorized ADDs reach Runtime BUY_ADD, but only `5` same-day BUY fills are observed. The dominant non-fill evidence is Submit `item_scoped_review_required`.
2. Execution fill / campaign lifecycle: all `5` true BUY_ADD fills preserve position quantity in effect but do not appear as same-campaign BUY events / ADD history in `positions/position_campaigns.json`.

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260825T135619843503Z`
- Completed daily evidence through: `2023-09-13`
- Latest campaign artifact used: `daily/2023-09-13/positions/position_campaigns.json`
- Primary artifacts:
  - `strategy/position_management.json`
  - `strategy/portfolio_construction.json`
  - `strategy/position_sizing.json`
  - `strategy/runtime_planning.json`
  - `submit/runtime_manifest.json`
  - `execution/fills.json`
  - `positions/position_campaigns.json`

READ_ONLY = YES  
CODE_CHANGED = NO  
RUN_MODIFIED = NO  
FRESH_RUN_EXECUTED = NO  
RESUME_EXECUTED = NO  
REPLAY_EXECUTED = NO  
LONG_HISTORICAL_EXECUTED = NO

## Philosophy Contract

BUY_ADD_PHILOSOPHY_CONTRACT_CONFIRMED = `YES`

Confirmed contract:

- Initial BUY may be small.
- PM may emit ADD for strong existing positions.
- ADD is not automatic.
- Each additional lot competes against other ADD, NEW_BUY, and Cash / residual optionality.
- G115 staged binding authorizes one executable increment, not the full requested block.
- PC remains capital allocation owner.
- PS remains discrete quantity owner.
- Runtime must not re-decide capital priority.
- Same-campaign BUY_ADD fills should preserve campaign identity and materialize BUY / ADD history under the G122 contract.

## PM ADD Population

PM_ADD_INTENT_COUNT = `220`

Top PM ADD symbols:

| Symbol | PM ADD intents |
| --- | ---: |
| 94320 | 126 |
| 76470 | 27 |
| 99840 | 18 |
| 43880 | 12 |
| 21340 | 9 |
| 94340 | 7 |
| 40520 | 7 |
| 54010 | 6 |
| 59550 | 5 |
| 72730 | 1 |
| 59350 | 1 |
| 30410 | 1 |

PM ADD evidence is concentrated in a small set of existing positions, which is consistent with selective Winner recognition rather than indiscriminate scaling.

## PM ADD To G115 Funnel

PM_ADD_TO_G115_FUNNEL:

| Outcome | Count |
| --- | ---: |
| `INSUFFICIENT_EVIDENCE_AND_NEW_BUY_SUPERIOR` | 119 |
| `AUTHORIZED_COMPARABLE_MARGINAL` | 65 |
| `INSUFFICIENT_EVIDENCE` | 20 |
| `AUTHORIZED_ADD_MARGINAL_PREFERRED` | 9 |
| `NEW_BUY_PREFERRED` | 5 |
| `PC_COMPETITOR_COMPETITOR_REJECTED_TERMINAL` | 2 |
| Total | 220 |

AUTHORIZED_ADD_PC_COUNT = `74`

The authorized rows split as:

| G115 authorization | Count |
| --- | ---: |
| `COMPARABLE_MARGINAL_RESIDUAL_SHOULDER_ONE_INCREMENT_AUTHORIZED` | 65 |
| `ADD_MARGINAL_PREFERRED_ONE_INCREMENT_AUTHORIZED` | 9 |

## Insufficient Evidence Root Cause

ADD_INSUFFICIENT_ROOT_CAUSE_COUNTS:

| Root cause | Count | Classification |
| --- | ---: | --- |
| incremental investment value UNKNOWN plus NEW_BUY superior opportunity cost | 52 | LEGITIMATE_INSUFFICIENCY |
| incremental investment value UNKNOWN | 79 | LEGITIMATE_INSUFFICIENCY |
| Cash/residual interaction blocked ADD frontier despite positive ADD evidence | 8 | ARCHITECTURE_DEFECT |

The first two buckets are not treated as defects: PC consumed canonical ADD evidence and failed closed when incremental value was unknown or NEW_BUY was superior. The third bucket is different: the G115 source shadow row had `incremental_investment_value = POSITIVE / PASS` and `opportunity_cost = PASS`, but the row still failed closed via `MARKET_CANDIDATE_CASH_INTERACTION_FAIL_CLOSED`.

ADD_EVIDENCE_PRESENT_BUT_NOT_CONSUMED_COUNT = `8`

Evidence-present boundary:

`canonical_add_marginal_capital_competition.source_shadow_increment`
-> `canonical_add_marginal_capital_competition_authority`

Affected examples:

| Date | Symbol |
| --- | --- |
| 2022-10-21 | 94320 |
| 2022-11-29 | 76470 |
| 2023-03-20 | 94320 |
| 2023-04-21 | 94320 |
| 2023-06-20 | 21340 |
| 2023-08-16 | 94320 |
| 2023-09-05 | 94320 |
| 2023-09-08 | 94320 |

## G115 One-Increment Contract

G115_ONE_INCREMENT_CONTRACT_CONFORMANCE = `PASS`

No violation was found where G115 authorized multiple increments for the same symbol/date or authorized a quantity greater than the executable lot increment. G115 correctly uses staged one-increment binding.

## PC To PS

AUTHORIZED_ADD_PC_COUNT = `74`

AUTHORIZED_ADD_PS_POSITIVE_COUNT = `74`

PC_TO_PS_ADD_QUANTITY_LEAK_COUNT = `0`

The G119-style PC/PS consistency issue did not recur for ADD. Authorized ADD rows retain positive PS quantity.

## PS To Runtime

PS_ADD_TO_RUNTIME_COUNT = `74`

PS_TO_RUNTIME_ADD_LEAK_COUNT = `0`

All PM-linked positive PS ADD quantities reached Runtime as `BUY_ADD`.

## Runtime To Fill

RUNTIME_BUY_ADD_COUNT = `75`

BUY_ADD_FILL_COUNT = `5`

RUNTIME_TO_FILL_ADD_LEAK_COUNT = `70`

Observed true BUY_ADD fills:

| Date | Symbol | Runtime qty | Fill qty |
| --- | --- | ---: | ---: |
| 2022-10-12 | 94320 | 100 | 100 |
| 2022-10-12 | 94340 | 100 | 100 |
| 2022-10-13 | 94340 | 100 | 100 |
| 2023-02-15 | 54010 | 100 | 100 |
| 2023-05-31 | 30410 | 100 | 100 |

Dominant non-fill evidence:

| Submit / visibility reason | Count |
| --- | ---: |
| `item_scoped_review_required` | 65 |
| No submit item found in searched manifest evidence | 3 |
| Candidate-only submit visibility | 2 |

The most important observed shape is:

`PM ADD`
-> `G115 authorized`
-> `PS positive quantity`
-> `Runtime BUY_ADD`
-> Submit item remains reviewed / not submitted
-> no fill

This is a confirmed actual-path Winner Scaling defect. It is not explained by PC selectivity or PS quantity ownership.

## Campaign Materialization

BUY_ADD_SAME_CAMPAIGN_IDENTITY_RATE = `0%`

BUY_ADD_QUANTITY_RECONCILIATION_FAILURE_COUNT = `5`

BUY_ADD_HISTORY_MATERIALIZATION_FAILURE_COUNT = `5`

For all 5 true BUY_ADD fills, the fill exists in `execution/fills.json`, but the latest canonical campaign artifact does not append the BUY_ADD fill as a same-campaign BUY event or ADD history.

Examples:

| Fill date | Symbol | Fill campaign id | Expected campaign relation |
| --- | --- | --- | --- |
| 2022-10-12 | 94320 | `pc-f9cfb6b5498e35e5-94320-0001` | should append to open 94320 campaign |
| 2022-10-12 | 94340 | `pc-f9cfb6b5498e35e5-94340-0001` | should append to open 94340 campaign |
| 2022-10-13 | 94340 | `pc-f9cfb6b5498e35e5-94340-0001` | should append to open 94340 campaign |
| 2023-02-15 | 54010 | `pc-f9cfb6b5498e35e5-54010-0001` | should append to open 54010 campaign |
| 2023-05-31 | 30410 | `pc-f9cfb6b5498e35e5-30410-0001` | should append to open 30410 campaign |

The latest `position_campaigns.json` still shows one BUY event / `buy_history_summary.count = 1` for these campaigns and no ADD history. This means G122's intended materialization contract is not active in this actual run path.

## Winner Alignment

PM_ADD_INTENT_COHORT_DISTRIBUTION:

| G125 cohort | PM ADD intents |
| --- | ---: |
| DURABLE_WINNER | 28 |
| ORDINARY | 7 |
| EARLY_FAILURE | 0 |
| SHORT_LIVED_WINNER | 0 |
| Outside G125 March-August cohort scope | 185 |

PM_ADD_WINNER_ALIGNMENT = `MODERATE`

Within the G125-audited March-August cohort, PM ADD aligns heavily toward Durable Winners and avoids Early Failures. However, only `3 / 37` Durable Winner campaigns receive any PM ADD intent, so coverage is sparse even though emitted intents are reasonably aligned.

## Durable Winner Scaling Conversion

DURABLE_WINNER_WITH_ADD_INTENT = `3`

DURABLE_WINNER_WITH_AUTHORIZED_ADD = `1`

DURABLE_WINNER_WITH_FILLED_ADD = `0`

DURABLE_WINNER_ADD_INTENT_TO_FILL_RATE = `0%`

Durable Winner campaigns with PM ADD intent:

| Campaign | Symbol | Fill outcome |
| --- | --- | --- |
| `pc-5fcb6d8b0237695e-40520-0001` | 40520 | no ADD fill |
| `pc-0b058d4a5bec4445-21340-0002` | 21340 | no ADD fill |
| `pc-42dc80fc64981776-43880-0001` | 43880 | no ADD fill |

## Missed Scaling Causes

WINNER_ADD_NONFILL_CAUSE_COUNTS:

| Cause | Count |
| --- | ---: |
| D. insufficient evidence | 26 |
| H. Runtime / Submit / Execution leak | 2 |
| A/B/C/F/G/I | 0 |

REJECTED_WINNER_ADD_CAPITAL_DESTINATION:

| Destination / effect | Count |
| --- | ---: |
| NEW_BUY | 22 |
| Cash | 3 |
| other / unspent / unresolved | 3 |

Interpretation:

Most rejected Winner ADD intents are not simple PC bugs: many fail closed because canonical incremental value is unknown or NEW_BUY is superior. But the authorized Winner ADDs still do not fill, which is an actual downstream defect.

## Monthly ADD Funnel

MONTHLY_ADD_FUNNEL:

| Month | PM ADD | Authorized ADD | Filled ADD | Insufficient | Winner ADD intent | Winner filled ADD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2022-10 | 18 | 6 | 3 | 12 | n/a | n/a |
| 2022-11 | 29 | 6 | 0 | 16 | n/a | n/a |
| 2022-12 | 15 | 8 | 0 | 7 | n/a | n/a |
| 2023-01 | 8 | 3 | 0 | 5 | n/a | n/a |
| 2023-02 | 5 | 1 | 1 | 4 | n/a | n/a |
| 2023-03 | 23 | 3 | 0 | 20 | 8 | 0 |
| 2023-04 | 14 | 3 | 0 | 11 | 4 | 0 |
| 2023-05 | 18 | 12 | 1 | 6 | 0 | 0 |
| 2023-06 | 41 | 16 | 0 | 25 | 16 | 0 |
| 2023-07 | 20 | 8 | 0 | 12 | 0 | 0 |
| 2023-08 | 20 | 6 | 0 | 14 | 0 | 0 |
| 2023-09 | 9 | 2 | 0 | 7 | n/a | n/a |

POST_APRIL_WINNER_SCALING_CONVERSION_SHIFT = `NO`

Winner scaling conversion is weak before and after April. The issue is not a clean post-April deterioration; it is a persistent ADD conversion/materialization limitation.

## Regime Funnel

BULL_ADD_FUNNEL:

| Regime | PM ADD | Authorized | Filled | Insufficient | Winner ADD intent |
| --- | ---: | ---: | ---: | ---: | ---: |
| BULL | 93 | 35 | 1 | 54 | 12 |

RANGE_ADD_FUNNEL:

| Regime | PM ADD | Authorized | Filled | Insufficient | Winner ADD intent |
| --- | ---: | ---: | ---: | ---: | ---: |
| RANGE | 47 | 15 | 1 | 32 | 5 |

Other regimes:

| Regime | PM ADD | Authorized | Filled | Insufficient | Winner ADD intent |
| --- | ---: | ---: | ---: | ---: | ---: |
| BEAR | 23 | 11 | 3 | 12 | 2 |
| RECOVERY | 44 | 9 | 0 | 32 | 8 |
| CORRECTION | 13 | 4 | 0 | 9 | 1 |

BUY_ADD_CONVERSION_REGIME_DEPENDENT = `NO`

The conversion problem is cross-regime. BULL has many PM ADDs and many authorizations, but still only one fill.

## Defect Gate

MANDATORY_BUY_ADD_REPAIR_FOUND = `YES`

Confirmed mandatory repair triggers:

- Required canonical ADD evidence exists but G115/PC does not consume it in 8 `MARKET_CANDIDATE_CASH_INTERACTION_FAIL_CLOSED` cases.
- Authorized ADD does not reliably materialize after Runtime BUY_ADD.
- True BUY_ADD fills fail campaign identity/history reconciliation.

BUY_ADD_RARITY_EXPLAINED_BY_DESIGN = `PARTIAL`

Rarity is partly explained by legitimate selectivity: many PM ADD intents have unknown incremental value or lose to superior NEW_BUY evidence. But rarity is not fully design-conformant because authorized ADDs mostly fail to fill and actual fills fail campaign history materialization.

WINNER_SCALING_PHILOSOPHY_CONFORMANCE = `FAIL`

The system can identify some Winners and ask to ADD. PC/G115 can authorize one increment and PS can size it. But marginal capital rarely reaches filled BUY_ADD, and successful BUY_ADD is not reflected in canonical campaign history. Therefore the small-entry -> confirmation -> ADD -> scaled winner loop is not operationally closed.

WINNER_SCALING_CAN_EXPLAIN_POST_APRIL_STAGNATION = `PARTIAL`

This does not prove Winner Scaling is the only post-April cause. But the actual funnel confirms a material structural limitation: Durable Winner ADD intent-to-fill conversion is `0%`, and same-campaign ADD history remains absent.

## Required Judgments

PM_ADD_INTENT_COUNT = `220`

ADD_EVIDENCE_PRESENT_BUT_NOT_CONSUMED_COUNT = `8`

G115_ONE_INCREMENT_CONTRACT_CONFORMANCE = `PASS`

PC_TO_PS_ADD_QUANTITY_LEAK_COUNT = `0`

PS_TO_RUNTIME_ADD_LEAK_COUNT = `0`

RUNTIME_TO_FILL_ADD_LEAK_COUNT = `70`

BUY_ADD_SAME_CAMPAIGN_IDENTITY_RATE = `0%`

BUY_ADD_QUANTITY_RECONCILIATION_FAILURE_COUNT = `5`

BUY_ADD_HISTORY_MATERIALIZATION_FAILURE_COUNT = `5`

PM_ADD_WINNER_ALIGNMENT = `MODERATE`

DURABLE_WINNER_WITH_ADD_INTENT = `3`

DURABLE_WINNER_WITH_AUTHORIZED_ADD = `1`

DURABLE_WINNER_WITH_FILLED_ADD = `0`

DURABLE_WINNER_ADD_INTENT_TO_FILL_RATE = `0%`

POST_APRIL_WINNER_SCALING_CONVERSION_SHIFT = `NO`

BUY_ADD_CONVERSION_REGIME_DEPENDENT = `NO`

MANDATORY_BUY_ADD_REPAIR_FOUND = `YES`

BUY_ADD_RARITY_EXPLAINED_BY_DESIGN = `PARTIAL`

WINNER_SCALING_PHILOSOPHY_CONFORMANCE = `FAIL`

WINNER_SCALING_CAN_EXPLAIN_POST_APRIL_STAGNATION = `PARTIAL`

FUTURE_INFORMATION_USED_FOR_PRODUCTION_DECISION = `NO`

PERFORMANCE_USED_TO_SELECT_PRODUCTION_PARAMETER = `NO`

## Next Task

Recommended exactly one next task:

`PHASE31_G128_BUY_ADD_SUBMIT_REVIEW_AND_CAMPAIGN_HISTORY_ACTUAL_PATH_REPAIR`

Repair scope should be narrow and evidence-bound:

1. First repair / audit boundary: authorized Runtime BUY_ADD -> Submit item-scoped review / fill materialization.
2. Then verify the G122 same-campaign BUY_ADD history materialization contract on the actual production-common path.

Do not change PM ADD thresholds, G115 competition semantics, Market Quality, Risk Pacing, Candidate ranking, PS quantity ownership, Runtime capital priority, or SELL semantics.
