# Phase32-AN — Durable Winner Capital Competition Deep Root-Cause Audit

## Scope

- Primary trusted run: `runtime-test-historical-extended-smoke-20260830T081425790243Z`
- Trusted window: `2022-10-03` through `2023-10-10`
- Business days: `252`
- Mode: READ-ONLY deep root-cause audit

No Strategy, ADD/HOLD, NEW, Cash, Risk Pacing, PC, thresholds, weights, caps, source, config, runtime state, component, comparator, fresh-run, resume, replay, recover, design, implementation, or Production parameter recommendation was changed or executed.

No future outcome was used to select Production behavior.

## Evidence Read

- Phase32-AF through Phase32-AM reports
- Phase32-U/V/W/X winner-retention reports
- Target run artifacts:
  - `strategy/portfolio_construction.json`
  - `strategy/position_management.json`
  - `position_management/pm_decisions.json`
  - `strategy/buy_quality_decisions.json`
  - `strategy/strategy_intelligence.json`
  - `strategy/position_sizing.json`
  - `execution/fills.json`
  - `positions/position_campaigns.json`
- Current source contracts for PM, SI, BQ, ADD evidence, PC, PS, and Runtime planning

## Coverage Note

Phase32-AM reported:

```text
durable-winner days = 66
actual winner: Cash 44, NEW 22, ADD 0
```

AN reconstructed the same 66 strong-incumbent days. Within the strict 7 durable-winner campaign set from AM, 61 of those days belong to the 7 durable campaigns. The remaining 5 days are edge strong-incumbent days from campaigns with fewer than 5 strict strong rows:

| Edge Date | Strong Incumbent | Actual Winner | Cash State |
| --- | --- | --- | --- |
| `2022-11-21` | `99840` | `NEW_BUY 39660` | `OPTIONALITY_LOW` |
| `2022-11-25` | `99840` | `NEW_BUY 93180` | `OPTIONALITY_LOW` |
| `2023-05-31` | `59550` | `CASH_OPTIONALITY` | `OPTIONALITY_ELEVATED` |
| `2023-06-01` | `59550` | `CASH_OPTIONALITY` | `OPTIONALITY_ELEVATED` |
| `2023-07-05` | `37780` | `CASH_OPTIONALITY` | `OPTIONALITY_ELEVATED` |

Unless explicitly marked "strict 7-campaign subset", final day-level answers preserve AM's canonical 66-day denominator.

## Executive Summary

ADD won `0/66` durable/strong-incumbent days because ADD rarely reached the same final capital frontier as NEW or Cash, and when it did, it remained marginal or was outweighed by Cash/NEW semantics.

This is not evidence that ADD should have won. It is evidence that current capital competition is a mixed interaction:

```text
durable winner recognized
-> often not represented as final ADD competitor
-> if represented, often rejected/zero/insufficient before final comparison
-> Cash or NEW receives final capital destination
```

Main findings:

| Question | Finding |
| --- | --- |
| Cash wins on canonical durable-winner days | `44/66` |
| NEW wins on canonical durable-winner days | `22/66` |
| ADD wins | `0/66` |
| strict 7-campaign Cash wins | `41/61` |
| strict 7-campaign NEW wins | `20/61` |
| NEW wins with direct final ADD comparison | `2/20` strict subset |
| NEW wins because ADD never reached final competition | `18/20` strict subset |
| cash wins clearly/plausibly justified by no deployable/insufficient/gated ADD | `25/41` strict subset |
| cash wins with architecture concern | `16/41` strict subset |
| deterministic strong incremental capital candidates among 65 AM strong rows | `0` |
| plausible incremental candidates | small, not canonical; AL/AJ found `3` plausible fresh rows |

Decision gate:

```text
MIXED_INTERACTION_PRIMARY
```

The best H0-H6 explanation is H6: mixed interaction. Durable winner scarcity matters, but it does not alone explain the repeated diversion of capital to Cash/NEW while incumbents remain small.

## A — Canonical 66 Durable-Winner Day Inventory

All 66 AM strong-incumbent days were reconstructed. The 61 strict 7-campaign days are summarized below; the 5 edge days are listed in the coverage note.

Compact field legend:

```text
symbol:PM:rank:BQ/weight
```

| Date | Durable Winner Strong Row(s) | NEW Count | Actual ADD Count | Cash State | Actual Winner |
| --- | --- | ---: | ---: | --- | --- |
| `2022-10-05` | `94340:ADD:2:FULL/HIGH/2.8%` | `23` | `1` | `OPTIONALITY_ELEVATED` | `CASH_OPTIONALITY` |
| `2022-10-06` | `94340:ADD:2:FULL/HIGH/2.8%` | `21` | `1` | `OPTIONALITY_ELEVATED` | `CASH_OPTIONALITY` |
| `2022-10-07` | `94340:ADD:2:FULL/HIGH/4.1%` | `20` | `2` | `OPTIONALITY_ELEVATED` | `CASH_OPTIONALITY` |
| `2022-10-11` | `94340:ADD:2:FULL/HIGH/4.1%` | `19` | `1` | `OPTIONALITY_ELEVATED` | `CASH_OPTIONALITY` |
| `2022-10-12` | `94340:ADD:2:FULL/HIGH/4.2%` | `27` | `2` | `OPTIONALITY_ELEVATED` | `CASH_OPTIONALITY` |
| `2022-10-26` | `94340:HOLD:4:FULL/HIGH/6.9%` | `20` | `1` | `OPTIONALITY_NEUTRAL` | `CASH_OPTIONALITY` |
| `2022-11-28` | `76470:ADD:2:FULL/HIGH/3.1%` | `21` | `2` | `OPTIONALITY_NEUTRAL` | `NEW_BUY 93180` |
| `2022-11-29` | `76470:ADD:3:FULL/HIGH/3.1%` | `22` | `1` | `OPTIONALITY_LOW` | `NEW_BUY 76920` |
| `2022-11-30` | `76470:ADD:2:FULL/HIGH/3.4%` | `9` | `1` | `OPTIONALITY_ELEVATED` | `CASH_OPTIONALITY` |
| `2022-12-01` | `76470:ADD:2:FULL/HIGH/3.6%` | `14` | `1` | `OPTIONALITY_ELEVATED` | `CASH_OPTIONALITY` |
| `2022-12-02` | `76470:ADD:2:FULL/HIGH/3.9%` | `20` | `1` | `OPTIONALITY_NEUTRAL` | `NEW_BUY 64880` |
| `2022-12-06` | `76470:ADD:2:FULL/HIGH/4.1%` | `23` | `1` | `OPTIONALITY_NEUTRAL` | `CASH_OPTIONALITY` |
| `2022-12-07` | `76470:HOLD:2:FULL/HIGH/4.3%` | `23` | `0` | `OPTIONALITY_NEUTRAL` | `NEW_BUY 56100` |
| `2022-12-08` | `76470:HOLD:2:FULL/HIGH/4.4%` | `26` | `0` | `OPTIONALITY_NEUTRAL` | `NEW_BUY 61440` |
| `2022-12-09` | `76470:HOLD:2:FULL/HIGH/4.3%` | `29` | `0` | `OPTIONALITY_NEUTRAL` | `NEW_BUY 43510` |
| `2023-01-13` | `76470:HOLD:2:FULL/HIGH/4.4%` | `25` | `0` | `OPTIONALITY_ELEVATED` | `CASH_OPTIONALITY` |
| `2023-01-16` | `76470:HOLD:2:FULL/HIGH/4.3%` | `25` | `0` | `OPTIONALITY_ELEVATED` | `CASH_OPTIONALITY` |
| `2023-01-17` | `76470:HOLD:3:FULL/HIGH/4.4%` | `30` | `0` | `OPTIONALITY_ELEVATED` | `CASH_OPTIONALITY` |
| `2023-01-19` | `76470:HOLD:4:FULL/HIGH/4.3%` | `26` | `0` | `OPTIONALITY_ELEVATED` | `CASH_OPTIONALITY` |
| `2023-02-02` | `77760:HOLD:5:FULL/HIGH/3.0%` | `21` | `0` | `OPTIONALITY_NEUTRAL` | `NEW_BUY 48280` |
| `2023-02-06` | `77760:HOLD:5:FULL/HIGH/2.9%` | `22` | `0` | `OPTIONALITY_ELEVATED` | `CASH_OPTIONALITY` |
| `2023-02-07` | `77760:HOLD:5:FULL/HIGH/3.0%` | `26` | `0` | `OPTIONALITY_NEUTRAL` | `CASH_OPTIONALITY` |
| `2023-02-08` | `77760:HOLD:5:FULL/HIGH/3.1%` | `27` | `0` | `OPTIONALITY_NEUTRAL` | `CASH_OPTIONALITY` |
| `2023-02-09` | `77760:HOLD:5:FULL/HIGH/3.2%` | `17` | `0` | `OPTIONALITY_ELEVATED` | `CASH_OPTIONALITY` |
| `2023-02-15`-`2023-03-07` | `54010`, 13 strong rows, mixed ADD/HOLD | `11-24` | `0-1` | mostly `ELEVATED/NEUTRAL` | Cash or NEW |
| `2023-03-22`-`2023-04-04` | `43880`, 9 strong rows, mixed ADD/HOLD/REDUCE | `16-31` | `0-2` | mostly `ELEVATED` | Cash or NEW |
| `2023-06-06`-`2023-06-21` | `21340`, 12 strong rows, mixed ADD/HOLD | `15-30` | `0-2` | mixed | Cash or NEW |
| `2023-06-16`-`2023-07-04` | `40520`, 7 strong rows, mixed ADD/HOLD | `18-30` | `0-2` | mixed | Cash or NEW |

No ADD winner was observed on any of the 66 days.

## B — Recognition vs Deployment

Recognition and deployment are distinct:

| Layer | Result |
| --- | --- |
| strong security opportunity | recognized for all strong rows through rank/BQ/opportunity evidence |
| strong existing campaign | recognized through current return, campaign state, continuation evidence |
| ADD consideration | present for most durable rows, but sometimes only as shadow/HOLD-surfaced evidence |
| actual executable ADD candidate | much narrower; many rows remain zero, rejected, or not final-comparable |
| final deployment | Cash or NEW on all 66 days |

Critical finding:

```text
strong Winner != valid next-lot ADD
```

## C — Cash-Winner Days

Canonical AM denominator:

```text
Cash wins: 44/66
```

Strict 7-campaign deep classification:

| Cash First Decisive Reason | Count |
| --- | ---: |
| `ADD_INCREMENTAL_VALUE_INSUFFICIENT` | `19` |
| `ADD_PM_HOLD_ONLY` | `10` |
| `ADD_VALID_BUT_CASH_OPTIONALITY_HIGHER` | `6` |
| `ADD_PRIOR_HISTORY_BLOCK` | `4` |
| `NO_VALID_ADD_CANDIDATE` | `2` |

Interpretation:

| Cash Question | Count |
| --- | ---: |
| Cash won because there was genuinely no deployable / insufficient / gate-blocked incremental Winner opportunity | `25/41` strict subset |
| Cash won with architecture concern or semantically weak comparison | `16/41` strict subset |

The remaining 3 canonical Cash days are edge strong-incumbent days outside the strict 7-campaign subset.

## D — Cash Rationality Audit

Classification:

```text
IS_CASH_44_OF_66_MOSTLY_RATIONAL_OR_STRUCTURALLY_DOMINANT: MIXED
```

Cash was often rational or plausibly rational because ADD was not deployable, was insufficient, or was blocked by prior ADD/safety-style constraints. But Cash also looks structurally dominant in cases where a strong incumbent had plausible ADD consideration yet never reached final comparable competition or where Cash beat valid-but-marginal ADD through non-equivalent semantics.

Cash rationality counts:

| Cash Rationality | Count |
| --- | ---: |
| `CLEARLY/Plausibly justified` | `25/41` strict subset |
| `CASH_DOMINANCE_ARCHITECTURE_CONCERN` | `16/41` strict subset |

## E — NEW-Winner Days

Canonical AM denominator:

```text
NEW wins: 22/66
```

Strict 7-campaign deep classification:

| NEW-Winner Classification | Count |
| --- | ---: |
| `ADD_NEVER_REACHED_FINAL_COMPETITION` | `11` |
| `ADD_LOST_BEFORE_FINAL_COMPARISON` | `7` |
| `NEW_PLAUSIBLY_STRONGER` | `2` |

The remaining 2 canonical NEW days are edge strong-incumbent days outside the strict 7-campaign subset.

Representative actual NEW wins:

| Date | Incumbent | Incumbent State | Actual Winner | Interpretation |
| --- | --- | --- | --- | --- |
| `2022-11-29` | `76470` | ADD, BQ HIGH, rank 3 | `NEW_BUY 76920` | One of the few direct comparable cases; NEW plausibly stronger. |
| `2022-12-07` | `76470` | HOLD, BQ HIGH, rank 2, prior ADD count 5 | `NEW_BUY 56100` | Incumbent never reached final ADD competition. |
| `2023-02-20` | `54010` | ADD, BQ HIGH, rank 3 | `NEW_BUY 43810` | ADD existed but lost before final comparison. |
| `2023-06-16` | `21340` + `40520` | strong incumbents, ADD/HOLD mix | `NEW_BUY 92410` | incumbents did not reach final direct comparable ADD frontier. |

## F — Was NEW Actually Competing Against ADD?

Answer:

```text
NEW often did not literally beat Winner ADD at the same final stage.
```

Strict 7-campaign NEW-winner days:

| Relationship | Count |
| --- | ---: |
| NEW and durable ADD reached direct final competition | `2/20` |
| ADD existed but lost before final comparison | `7/20` |
| durable winner was only PM HOLD / shadow consideration or otherwise never reached ADD final competition | `11/20` |

Canonical 66-day extrapolation:

```text
HOW_MANY_NEW_WINS_ACTUALLY_COMPETED_DIRECTLY_WITH_ADD: 2 confirmed in strict subset
HOW_MANY_NEW_WINS_OCCURRED_BECAUSE_ADD_NEVER_REACHED_FINAL_COMPETITION: 18/20 strict subset, plus 2 edge NEW days not durable-campaign comparable
```

## G — Same-Scale Comparison Audit

Only a very small number of durable-winner days had direct NEW/ADD final comparison. For those, comparison is:

```text
PARTIALLY_COMPARABLE
```

Reason:

- PC places NEW, ADD, and Cash in one capital competition framework.
- Directionality and accepted weight are comparable enough for current runtime consumption.
- But AF already established that NEW/ADD/Cash do not share a common calibrated marginal-yen value unit.
- ADD next-lot value includes campaign/current-exposure constraints that NEW does not.
- Cash optionality is not the same economic unit as security opportunity.

Therefore:

```text
WHEN_NEW_AND_ADD_MET_WERE_THEY_ECONOMICALLY_COMPARABLE: PARTIALLY_COMPARABLE
```

## H — Durable Winner Capitalization Opportunity Quality

For AM's durable-winner strong rows:

| Incremental Quality | Count |
| --- | ---: |
| `STRONG_INCREMENTAL_CASE` | `0` |
| `PLAUSIBLE_INCREMENTAL_CASE` | `3` |
| `HOLD_STRENGTH_ONLY` | majority |
| `RISK_BLOCKED / PRIOR_ADD_BLOCKED` | material subset, especially `76470` |
| `INSUFFICIENT` | material among actual ADD competitors per AG/AF |

Answer:

```text
HOW_MANY_OF_THE_65_STRONG_ROWS_WERE_ACTUALLY_GOOD_INCREMENTAL_CAPITAL_CANDIDATES: 0 deterministic strong cases; 3 plausible cases
```

This is the most important guardrail: durable winner existence does not prove another lot was justified.

## I — Winner vs NEW Opportunity Substrate

Common action-neutral evidence is shared:

- opportunity rank
- runtime opportunity score
- BQ
- momentum/trend
- expected-edge support
- market/regime compatibility
- liquidity/execution feasibility

ADD-specific evidence then makes incumbent deployment harder:

- current exposure
- no-loss state
- campaign health
- prior ADD / prior REDUCE history
- headroom/concentration
- incremental opportunity cost
- executable next-lot feasibility

Conclusion:

```text
Incumbents are systematically disadvantaged only in the sense that ADD must satisfy legitimate extra evidence.
There is also an architecture concern because this extra evidence is not on a common calibrated capital-value scale with NEW/Cash.
```

## J — Fragmentation Mechanism

Across the trusted window:

| Metric | Count |
| --- | ---: |
| total BUY_NEW fills | `395` |
| BUY_NEW fills on the 66 strong-incumbent days | `90` |
| median BUY_NEW quantity on strong-incumbent days | `100` |
| 100-share BUY_NEW fills on strong-incumbent days | `71/90` |

AM also found:

- median daily position count: `11`
- median daily 100-share positions: `9`
- median daily positions above 100 shares: `1`

Fragmentation classification:

```text
CAPITAL_ALLOCATION_FRAGMENTATION / MIXED
```

Some diversification is intentional, but the repeated starter-position pattern while durable incumbents remain at 100 shares is an allocation-fragmentation concern.

## K — Initial Sizing vs ADD Graduation

Classification:

```text
BOTH
```

Initial sizing creates many 100-share starter positions, and ADD graduation rarely scales the winners afterward. The evidence does not support blaming only ADD; fragmentation begins at entry and persists because graduation is weak.

## L — Graduation Rate

Across `395` observed campaigns:

| Graduation | Count |
| --- | ---: |
| never grew beyond initial quantity | `392` |
| modest growth | `2` |
| material growth | `1` |
| large winner capitalization | `0` |

For durable winners:

| Graduation | Count |
| --- | ---: |
| material growth | `1` |
| modest growth | `1` |
| near/at initial size | `5` |

Answer:

```text
DO_STRONG_STARTER_POSITIONS_GRADUATE: RARELY
```

## M — Cash + NEW Combined Capital Diversion

On the canonical 66 strong-incumbent days:

| Capital Destination | Days |
| --- | ---: |
| Cash | `44` |
| NEW | `22` |
| ADD | `0` |

This is best described as:

```text
capital allocation destination is systematically away from incumbents
```

with the critical qualifier:

```text
incumbents often lacked deterministic valid incremental ADD evidence or never reached final comparison
```

## N — Risk Pacing Falsification

Risk Pacing/Cash optionality is not simply symmetric:

- Cash can win when deployment posture values optionality.
- NEW can still be allowed on other durable-winner days.
- ADD often faces extra gates before it can even become comparable.

Classification:

```text
ASYMMETRIC_ARCHITECTURE_CONCERN
```

This is not a correctness defect and not proof Risk Pacing is wrong. It is a capital-comparison architecture concern because NEW and ADD do not always face equivalent final-stage comparison.

## O — Position Cap / Concentration Falsification

Caps/headroom were not the main reason ADD won zero durable-winner days.

Evidence:

- many durable winners had max weights well below the single-name cap
- 100-share names such as `54010`, `40520`, and `77760` retained visible headroom
- only some higher-weight incumbents had local concentration relevance
- lot size can block individual increments but does not explain the broad 0/66 ADD-winner result

Classification:

```text
DO_CAPS_ACTUALLY_BLOCK_WINNER_GROWTH: NOT_PRIMARY
```

## P — Prior ADD Gate Falsification

Focus: `76470`.

Evidence:

- `76470` had 6 actual ADD consideration days before the gate.
- After prior ADD count reached 5, later strong HOLD rows remained observable but did not become ADD competitors.
- AJ/AL found no deterministic genuine fresh incremental opportunity among these rows.

Classification:

```text
SAFEGUARD_CONSERVATIVE_BUT_UNPROVEN_HARM
```

The gate is materially involved for `76470`, but current decision-time evidence does not prove it blocked a genuine refreshed opportunity.

## Q — Seven Durable Winner Case Studies

| Symbol | Why Durable | Growth | Headroom | ADD Consideration | Actual PC ADD | Main Competing Destination | Legitimate Risk Limit? | Model 2 Boundary Material? | Single Strongest Root Cause |
| --- | --- | --- | --- | ---: | ---: | --- | --- | --- | --- |
| `76470` | repeated top-2/4 rank, BQ HIGH, positive return | `1300 -> 1800`, modest | yes | `13` | `6` | NEW then Cash | prior ADD gate | YES | prior ADD gate plus Cash/NEW after initial adds |
| `54010` | top-3/5 rank, BQ HIGH, positive campaign return | `100 -> 100` | yes | `12` | `6` | Cash and NEW | not primary | YES | Cash/NEW plus PM HOLD-only after early ADD |
| `21340` | top-2/3 rank, BQ HIGH, strong positive return | `2200 -> 2200` | some, but larger initial qty | `13` | `9` | Cash/NEW | local sizing/headroom possible, not primary | YES | ADD exists but loses before final comparison |
| `43880` | top-3/4 rank, BQ HIGH, strong state | `100 -> 100` | moderate | `13` | `12` | Cash/NEW | concentration/risk local | PARTIAL | Cash dominance and local risk/REDUCE |
| `40520` | top-4/5 rank, BQ HIGH, positive return | `100 -> 100` | yes | `10` | `7` | NEW/Cash | not primary | YES | NEW competition plus no retained ADD quantity growth |
| `94340` | early strong rank/BQ continuation | `200 -> 500`, material | yes | `7` | `6` | Cash | not primary | PARTIAL | Cash optionality capped further growth |
| `77760` | top-5 rank, BQ HIGH, positive return | `100 -> 100` | yes | `5` | `0` | Cash/NEW | not primary | YES | PM HOLD-only / no actual ADD competitor |

## R — Plateau Period Segmentation

| Segment | Dates | Characterization |
| --- | --- | --- |
| early Oct-Nov 2022 | `2022-10` to `2022-11` | `94340`, `99840`, and `76470` show early winner/ADD activity, but Cash optionality is high. |
| Dec-Jan | `2022-12` to `2023-01` | `76470` transitions from ADD to prior-ADD-gated HOLD; NEW/Cash dominate. |
| Feb-Mar | `2023-02` to `2023-03` | `77760` and `54010` show strong/HOLD or mixed ADD evidence; many 100-share starters; Cash/NEW dominate. |
| late Mar-Apr | `2023-03` to `2023-04` | `43880` is strong but no quantity growth; Cash remains frequent; some REDUCE appears. |
| May | `2023-05` | few durable winners; opportunity scarcity and Cash are more prominent. |
| Jun-Jul | `2023-06` to `2023-07` | `21340`/`40520` durable strength appears but does not graduate; NEW wins and Cash both material. |
| Aug-Oct | `2023-08` to `2023-10-10` | fewer strict durable winner signals; high Cash/fragmentation/turnover remain relevant. |

Conclusion:

```text
The plateau has multiple sequential mechanisms, not one cause.
```

## S — Root Cause Materiality Matrix

| Cause | Affected Days / Campaigns | Confidence | Architecture Concern | Correctness Defect | Effect Type |
| --- | --- | --- | --- | --- | --- |
| opportunity scarcity | only 7 durable campaigns; 0 deterministic fresh cases | HIGH | YES | NO | independent |
| fragmentation | 395 BUY_NEW fills, 71/90 strong-day NEW fills at 100 shares | HIGH | YES | NO | independent + interaction |
| initial sizing | median NEW quantity 100; many starters | HIGH | YES | NO | independent |
| failure to graduate winners | 392/395 never grow; 5/7 durable near initial | HIGH | YES | NO | independent |
| PM/SI ADD boundary | 28 HOLD-surfaced ADD consideration rows; 77760 no ADD competitor | MEDIUM-HIGH | YES | NO | interaction |
| Cash optionality | Cash 44/66 canonical days | MEDIUM-HIGH | YES | NO | interaction |
| Risk Pacing | Cash/Risk optionality interacts with ADD weakness | MEDIUM | YES | NO | interaction |
| NEW competition | NEW 22/66, but direct final ADD comparison rare | MEDIUM | YES | NO | interaction |
| non-equivalent NEW/ADD/Cash semantics | AF confirmed no common calibrated marginal-yen unit | MEDIUM-HIGH | YES | NO | interaction |
| prior ADD gate | material for `76470`; harm unproven | MEDIUM | YES | NO | local |
| caps/headroom | local, not primary | LOW-MEDIUM | YES locally | NO | local |
| lot size | local, not primary | LOW-MEDIUM | YES locally | NO | local |
| REDUCE/EXIT | not primary after X in this window | LOW | WATCH | NO | residual |

## T — Current System Falsification

| Hypothesis | Evidence For | Evidence Against | Judgment |
| --- | --- | --- | --- |
| H0 current allocation broadly correct; scarcity explains most | only 7 durable winners; 0 deterministic fresh cases | durable winners still had 63 consideration rows and ADD never won | `PARTIAL` |
| H1 system identifies winners but fails to graduate starters | 392/395 campaigns never grew; 5/7 durable near initial | one material growth case exists | `STRONGLY_SUPPORTED` |
| H2 Cash/Risk Pacing is main diversion | Cash 44/66 | often ADD invalid/insufficient first | `SUPPORTED_AS_INTERACTION` |
| H3 NEW fragmentation main diversion | 90 BUY_NEW fills on strong days, 71 at 100 shares | many NEW may be legitimate opportunities | `SUPPORTED_AS_INTERACTION` |
| H4 ADD semantic/routing prevents valid incumbent competition | 18/20 strict NEW days did not have direct final ADD comparison; 28 HOLD-surfaced rows | no deterministic fresh ADD case proven | `SUPPORTED_AS_INTERACTION` |
| H5 non-equivalent semantics distort final allocation | AF confirmed no common marginal-yen scale | direct comparable cases are rare | `SUPPORTED_AS_ARCHITECTURE_CONCERN` |
| H6 mixed interaction required | all major mechanisms are present and interdependent | none | `BEST_EXPLANATION` |

## U — Decision Gate

Chosen:

```text
MIXED_INTERACTION_PRIMARY
```

No design or Production change is authorized by AN.

## Required Final Answers

1. `WHY_DID_ADD_WIN_ZERO_OF_66_DURABLE_WINNER_DAYS`

```text
Because durable winners usually did not reach a final deployable ADD comparison; when ADD existed, it was often insufficient, zero, cash-preferred, or lost before final comparison. Cash won 44 days, NEW won 22 days, ADD won 0.
```

2. `HOW_MANY_CASH_WINS_WERE_CLEARLY_OR_PLAUSIBLY_JUSTIFIED`

```text
25/41 in the strict 7-campaign subset; canonical 44-day denominator has 3 edge days not fully durable-campaign comparable.
```

3. `HOW_MANY_CASH_WINS_ARE_ARCHITECTURE_CONCERNS`

```text
16/41 in the strict 7-campaign subset.
```

4. `HOW_MANY_NEW_WINS_ACTUALLY_COMPETED_DIRECTLY_WITH_ADD`

```text
2/20 strict 7-campaign NEW-winner days.
```

5. `HOW_MANY_NEW_WINS_OCCURRED_BECAUSE_ADD_NEVER_REACHED_FINAL_COMPETITION`

```text
18/20 strict 7-campaign NEW-winner days.
```

6. `WHEN_NEW_AND_ADD_MET_WERE_THEY_ECONOMICALLY_COMPARABLE`

```text
PARTIALLY_COMPARABLE
```

7. `HOW_MANY_DURABLE_WINNER_ROWS_WERE_REAL_INCREMENTAL_CAPITAL_CANDIDATES`

```text
0 deterministic strong incremental cases; 3 plausible but non-canonical cases.
```

8. `IS_HIGH_FRAGMENTATION_INTENTIONAL_OR_AN_ALLOCATION_FAILURE`

```text
MIXED; intentional diversification exists, but evidence supports CAPITAL_ALLOCATION_FRAGMENTATION as a material architecture concern.
```

9. `DOES_INITIAL_SIZING_CREATE_TOO_MANY_STARTER_POSITIONS`

```text
YES_AS_CONTRIBUTING_CAUSE
```

10. `DO_STRONG_STARTER_POSITIONS_GRADUATE`

```text
RARELY
```

11. `IS_CAPITAL_SYSTEMATICALLY_DIVERTED_TO_NEW_AND_CASH`

```text
YES, as capital allocation destination; not necessarily as lost profit.
```

12. `IS_RISK_PACING_SYMMETRIC_BETWEEN_NEW_AND_ADD`

```text
ASYMMETRIC_ARCHITECTURE_CONCERN
```

13. `DO_CAPS_ACTUALLY_BLOCK_WINNER_GROWTH`

```text
NOT_AS_PRIMARY_CAUSE
```

14. `IS_PRIOR_ADD_HISTORY_MATERIALLY_HARMFUL`

```text
UNPROVEN; SAFEGUARD_CONSERVATIVE_BUT_UNPROVEN_HARM for 76470.
```

15. `WHAT_IS_THE_PRIMARY_ROOT_CAUSE_FOR_EACH_OF_THE_7_DURABLE_WINNERS`

```text
76470: prior ADD gate plus Cash/NEW after initial adds
54010: Cash/NEW plus PM HOLD-only after early ADD
21340: ADD exists but loses before final comparison
43880: Cash dominance plus local risk/REDUCE
40520: NEW competition plus no retained ADD quantity growth
94340: Cash optionality limits further growth after material early growth
77760: PM HOLD-only / no actual ADD competitor
```

16. `DOES_THE_PLATEAU_HAVE_ONE_CAUSE_OR_MULTIPLE_SEQUENTIAL_CAUSES`

```text
MULTIPLE_SEQUENTIAL_CAUSES
```

17. `WHICH_HYPOTHESIS_H0_H6_BEST_EXPLAINS_THE_EVIDENCE`

```text
H6 — Mixed interaction is required to explain the evidence.
```

## Final Judgment

```text
PHASE32_AN_DURABLE_WINNER_CAPITAL_COMPETITION_MIXED_INTERACTION_PRIMARY
```

ADD won zero durable-winner days mostly because durable incumbents rarely reached final, economically comparable ADD competition. Cash and NEW were often plausible contemporaneous capital destinations, but the evidence also shows meaningful architecture concerns: high starter-position fragmentation, weak graduation, PM/SI ADD consideration boundaries, Cash/Risk interaction, and non-equivalent NEW/ADD/Cash comparison semantics. No correctness defect or Production change is confirmed by AN.
