# Phase31-G112 — Repeated ADD Marginal Capital Competition Contract Audit

## Judgment

PRIMARY_JUDGMENT = G112_ADD_MARGINAL_COMPETITION_DEFECT_CONFIRMED_READY_FOR_REPAIR

The G111 suspected root cause is confirmed as an architecture-level ADD marginal competition defect, not a G97/G99/G102/G104 connectivity defect.

Confirmed classes:

- D: Cash semantic too weak for ADD marginal value.
- E: total campaign / same-row ADD quality is reused as incremental ADD value rather than true next-increment marginal value.
- F: block ADD quantity is authorized without lot-level marginal re-evaluation.

Additional partial findings:

- B: ADD-vs-ADD frontier is incomplete in the canonical `add_investment_evidence.v1` opportunity-cost contract.
- C: ADD-vs-NEW_BUY comparison exists, but it is not a full final-frontier comparison against the actual PC security/Cash allocation set.

ROOT_CAUSE_CLASS = H

## Scope

POST_REPAIR_RUN = runtime-test-historical-extended-smoke-20260825T072702567342Z

BASELINE_RUN = runtime-test-historical-extended-smoke-20260824T055234719725Z

Primary campaign:

- symbol = 76470
- campaign = pc-03ca91a459c078c1-76470-0002

Primary ADD dates:

- 2022-12-06
- 2022-12-21
- 2023-01-04

READ_ONLY = YES

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

RUN_MUTATED = NO

CODE_CHANGED = NO

FUTURE_PNL_OR_OUTCOME_USED_AS_DECISION_AUTHORITY = NO

## Canonical Contract Findings

CANONICAL_INCREMENTAL_CAPITAL_COMPETITION_DEFINED = PARTIAL

The current contract defines PM ADD eligibility, PC ADD competitor construction, PC capital allocation, PS quantity ownership, and Runtime quantity consumption. It does not define a complete repeated-ADD marginal frontier where each additional ADD lot must beat other ADDs, NEW_BUY, Cash, and residual optionality after current position size is updated.

### Owner Matrix

| Responsibility | Current owner | Evidence / code | Finding |
| --- | --- | --- | --- |
| PM ADD intent | POSITION_MANAGEMENT | PM decision fields consumed by PC | Defined |
| ADD campaign continuation | ADD investment evidence / PC bridge | `add_investment_evidence.campaign_continuation` | Defined |
| ADD expected edge | ADD investment evidence | `expected_edge` | Defined |
| ADD incremental investment value | ADD investment evidence | `incremental_value` | Partial: PASS derives from expected-edge cascade and opportunity-cost PASS |
| ADD opportunity cost | ADD investment evidence | `_resolve_opportunity_cost()` | Partial: compares against best NEW_BUY score only |
| ADD capital allocation | PORTFOLIO_CONSTRUCTION | canonical ADD competitor / multi allocation | Defined, but block-level |
| Cash optionality competition | PORTFOLIO_CONSTRUCTION | `CASH_PREFERRED_PARTICIPATION_VALID` | Partial: participation-valid is not a marginal ADD-beats-Cash proof |
| Discrete quantity | POSITION_SIZING | PC discrete authority consumed by PS | Defined |
| Runtime order planning | Runtime Planning | PS quantity binds Runtime | Defined |
| Lot-level marginal ADD re-evaluation | No canonical owner found | No evidence in current contract | Missing |

## Code Evidence

`src/ai_fund_lab_v2/strategy/add_investment_evidence.py` resolves ADD opportunity cost by comparing the ADD row score against same-day non-current-position members with `membership_intent == "ADD_CANDIDATE"`:

- candidate score = `runtime_opportunity_score`
- comparison set = NEW_BUY-like rows only
- output = `best_new_buy_score`, `candidate_score`, `comparison_result`

It does not compare:

- ADD vs other ADD candidates
- ADD vs Cash
- ADD vs residual optionality
- first ADD lot vs later ADD lot
- marginal value after current quantity / target weight changes

`src/ai_fund_lab_v2/strategy/portfolio_construction.py` preserves the ADD evidence in `canonical_add_competitor`, but its ADD eligibility only requires current position + PM ADD + incremental value PASS + opportunity cost PASS. The Cash-preferred resolver can allow reduced participation via `CASH_PREFERRED_PARTICIPATION_VALID`, but that proof is a participation/deferral decision, not a proof that the next ADD increment has higher marginal capital value than Cash.

## Primary 76470 Reconstruction

### 2022-12-06 / 76470

PM_ADD = YES

ADD_INVESTMENT_EVIDENCE = PASS

INCREMENTAL_VALUE = POSITIVE / PASS

OPPORTUNITY_COST = PASS

OPPORTUNITY_COST_AUTHORITY = portfolio_construction_same_day_score_competition

CANDIDATE_SCORE = 0.42251035

BEST_NEW_BUY_SCORE = 0.27563508

ADD_VS_NEW_BUY = PASS

ADD_VS_ADD = NOT_EVALUATED

ADD_VS_CASH = NOT_EVALUATED_AS_MARGINAL_VALUE

PC_AUTHORIZED_INCREMENTAL_WEIGHT = 0.032258

MULTI_ALLOC_INTERACTION = CASH_PREFERRED

CASH_PREFERRED_RESOLUTION = CASH_PREFERRED_PARTICIPATION_VALID

CASH_SEMANTIC = OPTIONALITY_NEUTRAL

LOT_STATE = LOT_EXECUTABLE_COMPATIBLE

FILL = BUY_ADD 1300 @ 27

MARGINAL_WINNER_PROVEN = NO

### 2022-12-21 / 76470

PM_ADD = YES

ADD_INVESTMENT_EVIDENCE = PASS

INCREMENTAL_VALUE = POSITIVE / PASS

OPPORTUNITY_COST = PASS

CANDIDATE_SCORE = 0.49393618

BEST_NEW_BUY_SCORE = -0.14106898

ADD_VS_NEW_BUY = PASS

ADD_VS_ADD = NOT_EVALUATED

ADD_VS_CASH = NOT_EVALUATED_AS_MARGINAL_VALUE

PC_AUTHORIZED_INCREMENTAL_WEIGHT = 0.028462

MULTI_ALLOC_INTERACTION = CASH_PREFERRED

CASH_PREFERRED_RESOLUTION = CASH_PREFERRED_PARTICIPATION_VALID

CASH_SEMANTIC = OPTIONALITY_ELEVATED

LOT_STATE = LOT_EXECUTABLE_COMPATIBLE

FILL = BUY_ADD 1000 @ 27

MARGINAL_WINNER_PROVEN = NO

### 2023-01-04 / 76470

PM_ADD = YES

ADD_INVESTMENT_EVIDENCE = PASS

INCREMENTAL_VALUE = POSITIVE / PASS

OPPORTUNITY_COST = PASS

CANDIDATE_SCORE = 0.39654501

BEST_NEW_BUY_SCORE = -0.14045628

ADD_VS_NEW_BUY = PASS

ADD_VS_ADD = NOT_EVALUATED

ADD_VS_CASH = NOT_EVALUATED_AS_MARGINAL_VALUE

PC_AUTHORIZED_INCREMENTAL_WEIGHT = 0.007407

REQUESTED_INCREMENTAL_WEIGHT = 0.025517

MULTI_ALLOC_INTERACTION = CASH_PREFERRED

CASH_PREFERRED_RESOLUTION = CASH_PREFERRED_PARTICIPATION_VALID

CASH_SEMANTIC = OPTIONALITY_ELEVATED

LOT_STATE = LOT_EXECUTABLE_COMPATIBLE

FILL = BUY_ADD 900 @ 28

MARGINAL_WINNER_PROVEN = NO

## Competition Contract Answers

ADD_VS_NEW_BUY_FULL_FRONTIER = PARTIAL

The ADD evidence compares candidate score to best NEW_BUY score. It does not prove superiority over the final PC allocation frontier, Cash, residual optionality, or lot-level marginal increments.

ADD_VS_ADD_CANONICAL_COMPETITION = PARTIAL

PC can hold multiple ADD competitors in the capital competition artifact, but `add_investment_evidence.v1` opportunity cost does not compare one ADD against other ADDs. In the post-repair run, 23 completed dates had multiple ADD competitors, so this is not only a theoretical gap.

ADD_ALLOCATION_ORDER_DEPENDENT = NOT_CONFIRMED

No symbol-order or first-listed processing defect was confirmed. The defect is not simple iteration order; it is missing marginal frontier semantics.

ADD_FIRST_COME_CAPITAL_ADVANTAGE = PARTIAL

Prior ADDs create a larger incumbent position and keep the campaign eligible for later ADD evaluation. That is a valid campaign-continuation mechanism, but the contract does not prove that later increments still have positive marginal capital value after prior increments.

CASH_PREFERRED_PARTICIPATION_SEMANTIC = REDUCED_SECURITY_PARTICIPATION_ALLOWED

`CASH_PREFERRED_PARTICIPATION_VALID` means a Cash-preferred row may still receive reduced security participation when its evidence is complete and it remains within the participation shoulder. It does not mean the ADD increment explicitly beats Cash.

ADD_MARGINAL_VALUE_EXPLICITLY_BEATS_CASH = NO

PRIOR_ADD_CREATES_FUTURE_ADD_ADVANTAGE = PARTIAL

UNINTENDED_INCUMBENCY_ADVANTAGE = PARTIAL

The audit does not prove an unintended direct privilege flag, but it confirms an architectural condition where campaign continuity plus non-marginal opportunity-cost PASS can permit repeated block ADDs without re-proving marginal superiority.

ADD_VALUE_IS_TRUE_INCREMENTAL_MARGINAL_VALUE = PARTIAL

The value is ADD-specific and PIT-safe, but it is not true next-lot marginal value. It primarily reflects expected-edge/campaign/no-loss/opportunity-cost gates.

MARGINAL_VALUE_POSITION_SIZE_AWARE = PARTIAL

Current weight and caps are present in PC/PS constraints, but the ADD opportunity-cost value itself is not position-size-decayed or lot-marginal.

ADD_COMPETITION_GRANULARITY = BLOCK_INCREMENT

MARGINAL_LOT_REEVALUATION_PRESENT = NO

## Generality Check

Existing post-repair artifacts through the audited completed dates show:

- ADD evidence records = 38
- ADD evidence dates = 34
- ADD symbols = 5
- opportunity-cost authority = `portfolio_construction_same_day_score_competition` for 38 / 38
- opportunity-cost PASS = 38 / 38
- `CASH_PREFERRED_PARTICIPATION_VALID` = 22 / 38
- LOT_EXECUTABLE_COMPATIBLE = 20 / 38
- dates with multiple ADD competitors = 23

Other ADD campaign examples:

| Symbol | Dates observed | Same contract finding |
| --- | ---: | --- |
| 94320 | 10 | ADD opportunity cost compares to best NEW_BUY; no ADD-vs-ADD/Cash marginal proof |
| 99840 | 7 | Same |
| 94340 | 4 | Same |
| 45940 | 3 | Same |
| 76470 | 14 | Same |

Representative multiple-ADD competitor dates include:

- 2022-10-12: 94320, 94340
- 2022-11-01: 94320, 99840
- 2022-11-24: 45940, 76470, 99840
- 2023-03-08: 59350, 94320
- 2023-03-22: 43880, 94320

This confirms the missing marginal frontier is a general contract gap, not a 76470-only artifact.

## G111 Hypothesis Resolution

C_REPEATED_ADD_CAPITAL_COMPETITION_INCOMPLETE = CONFIRMED_PARTIAL

Repeated ADD is admitted by ADD evidence and PC block allocation, but the contract does not prove each repeated increment against the complete frontier.

E_OPPORTUNITY_COST_CONTRACT_INCOMPLETE = CONFIRMED

Opportunity cost is only ADD-vs-best-NEW_BUY score in the canonical producer.

D_REPEATED_ADD_MARGINAL_VALUE_REEVALUATION_INCOMPLETE = CONFIRMED

There is no canonical per-lot / post-prior-ADD marginal value re-evaluation.

## Repair Boundary

REPAIR_REQUIRED = YES

SAFE_NARROW_REPAIR_POSSIBLE = YES

REPAIR_BOUNDARY = PORTFOLIO_CONSTRUCTION / CANONICAL_ADD_MARGINAL_CAPITAL_COMPETITION_CONTRACT

The repair should not change PM ADD thresholds, Market Quality, Risk Pacing, Candidate ranking, Safety, PS quantity ownership, or Runtime priority. The narrow missing boundary is the PC-owned ADD marginal competition contract:

- define ADD incremental capital comparison against the full same-date frontier: NEW_BUY, other ADDs, Cash, and residual optionality;
- make Cash preference explicit as either reduced participation allowed or marginal Cash superiority;
- re-evaluate repeated ADD at lot/increment granularity using current position size, cap/headroom, executable lot context, and remaining budget;
- preserve PS as discrete quantity owner and Runtime as consumer.

## Required Outputs

CANONICAL_INCREMENTAL_CAPITAL_COMPETITION_DEFINED = PARTIAL

ADD_VS_NEW_BUY_FULL_FRONTIER = PARTIAL

ADD_VS_ADD_CANONICAL_COMPETITION = PARTIAL

ADD_ALLOCATION_ORDER_DEPENDENT = NOT_CONFIRMED

ADD_FIRST_COME_CAPITAL_ADVANTAGE = PARTIAL

CASH_PREFERRED_PARTICIPATION_SEMANTIC = REDUCED_SECURITY_PARTICIPATION_ALLOWED

ADD_MARGINAL_VALUE_EXPLICITLY_BEATS_CASH = NO

PRIOR_ADD_CREATES_FUTURE_ADD_ADVANTAGE = PARTIAL

UNINTENDED_INCUMBENCY_ADVANTAGE = PARTIAL

ADD_VALUE_IS_TRUE_INCREMENTAL_MARGINAL_VALUE = PARTIAL

MARGINAL_VALUE_POSITION_SIZE_AWARE = PARTIAL

ADD_COMPETITION_GRANULARITY = BLOCK_INCREMENT

MARGINAL_LOT_REEVALUATION_PRESENT = NO

20221206_76470_MARGINAL_WINNER_PROVEN = NO

20221221_76470_MARGINAL_WINNER_PROVEN = NO

20230104_76470_MARGINAL_WINNER_PROVEN = NO

ROOT_CAUSE_CLASS = H

REPAIR_REQUIRED = YES

SAFE_NARROW_REPAIR_POSSIBLE = YES

CODE_CHANGED = NO

RUN_MODIFIED = NO

FUTURE_INPUT_COUNT = 0

HISTORICAL_OUTCOME_DECISION_INPUT_COUNT = 0

FINAL_DECISION = G112_ADD_MARGINAL_COMPETITION_DEFECT_CONFIRMED_READY_FOR_REPAIR

