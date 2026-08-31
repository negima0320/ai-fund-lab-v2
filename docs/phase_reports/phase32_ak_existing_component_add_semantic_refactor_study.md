# Phase32-AK — Existing Component ADD Semantic Refactor Study

## Scope

- Primary trusted run: `runtime-test-historical-extended-smoke-20260830T081425790243Z`
- Trusted window: `2022-10-03` through `2023-10-10`
- Business days: `252`
- Mode: READ-ONLY / DESIGN-STUDY ONLY

No code, config, runtime state, component, Strategy parameter, threshold, weight, ADD history rule, Cash policy, BQ, Risk Pacing, PC, PS, fresh-run, resume, replay, recover, or long Historical action was changed or executed.

Historical outcomes were not used to select design parameters. This study uses Phase32-AF through AJ evidence and current source contracts only.

## Prior Findings Used

| Phase | Relevant Finding |
| --- | --- |
| AF | NEW/ADD/Cash are compared by PC, but do not share a common high-resolution marginal-yen value unit. `MARGINAL_CAPITAL_SEMANTIC_GAP_CONFIRMED`. |
| AG | ADD zero-winner was mixed: most ADD competitors were blocked/insufficient before final comparison; only one reached final deployable comparison and lost to NEW. |
| AH | PM ADD is mixed and mostly state strength; 19 missing `76470` ADDs were a repeated prior-ADD-history safeguard mechanism. |
| AI | PM ADD is stronger than HOLD at decision time, but `103/118` were `STATE_DOMINANT`, `0/118` were `CHANGE_DOMINANT`; incremental timing value was weak/not established. |
| AJ | Current architecture was only partially falsified; no new component was justified; first concern was the PM/SI action-authority boundary before PC ADD materialization. |

## Executive Summary

Existing components can support the needed ADD semantic distinction with a semantic refactor study. A new component is not justified by current evidence.

Recommended conceptual direction:

```text
Model 2 — PM Position Lifecycle + PC ADD Consideration
```

Meaning:

- PM remains owner of open-position lifecycle health: HOLD / REDUCE / EXIT and current exposure context.
- Candidate/Opportunity and BQ remain action-neutral security-opportunity evidence.
- SI remains non-action-authoritative but can produce canonical ADD consideration evidence from existing PIT inputs.
- PC remains owner of final next-lot capital deployment among NEW / ADD / Cash.
- ADD-specific evidence remains required so ADD does not collapse into NEW-with-held=true.

This is a semantic clarification plus authority-boundary change study. It is not yet an activated behavioral change.

## A — Current Authority Map

| Semantic | Current Owner | Evidence Producer | Consumer | Authoritative? | Duplication / Gap |
| --- | --- | --- | --- | --- | --- |
| security opportunity strength | Candidate/Opportunity, BQ | opportunity rows, BQ | PM, SI, PC, PS | YES for score/rank/quality fields | shared by held/unheld; not final action authority |
| current-position health | PM / Strategy PM | Runtime current position adapter, PM evidence | PC, PS, Runtime Planning | YES | overlaps with SI lifecycle evidence |
| continuation | PM and SI | PM score/triggers; SI continuation quality | Strategy PM, PC | PARTIAL | PM uses continuation for action; SI labels continuation but is non-action-authoritative |
| deterioration | PM / SI | PM risk/exit/reduce; SI risk/profit protection | PM, PC | YES for lifecycle control | reasonably owned by PM; SI evidence supports |
| refreshed strength | Candidate/BQ/SI artifacts | BQ trajectory, SI entry, opportunity rank/score | PM/PC indirectly | NO single owner | missing canonical semantic |
| ADD consideration | currently PM action plus SI/BQ evidence | PM action, SI add worthiness, ADD evidence | PC/PS | SPLIT | primary semantic overlap |
| incremental ADD eligibility | ADD investment evidence / Strategy PM | `add_investment_evidence.py`, SI lifecycle | PC | YES when `pm_action=ADD` reaches evidence | not produced for PM HOLD held rows |
| next-lot value | ADD investment evidence / PC | ADD evidence, opportunity cost, marginal capital evidence | PC | PARTIAL | AF found common marginal value unit absent |
| concentration/headroom | PM/PC/Risk | current position state, policy, safety cap | PC/PS | YES | must remain ADD-specific |
| Cash competition | PC | PC capital competition | PS/Runtime | YES | not same value scale as security opportunities |
| final capital allocation | PC | capital competition framework | PS/Runtime | YES | Runtime must consume, not recompute |

Semantic overlap:

```text
PM ADD
SI ADD_ALLOWED / ADD_REDUCED_ONLY
BQ FULL / REDUCED
ADD investment evidence PASS / FAIL_CLOSED
PC ADD competitor
```

all describe nearby but non-identical concepts. The missing ownership is not a new data source; it is a canonical semantic boundary between held-position strength, ADD consideration, and executable incremental capital deployment.

## B — Semantic States Without New Component

### HOLD_STRENGTH

Recommended owner:

```text
PM
```

Reason:

HOLD strength answers whether existing exposure remains justified. That is open-position lifecycle authority and naturally belongs to PM, supported by SI lifecycle, current return, risk, continuation, and profit-protection evidence.

### ADD_CONSIDERATION

Recommended owner:

```text
Existing SI/ADD-evidence semantics as non-final consideration, consumed by PC
```

Reason:

ADD consideration means the held security is strong enough to enter incremental-capital competition. It is not identical to PM HOLD/REDUCE/EXIT lifecycle authority, and it is not final capital allocation. SI already carries `ADD_ALLOWED`, `ADD_REDUCED_ONLY`, continuation quality, risk status, and lifecycle context; ADD investment evidence carries incremental eligibility/value/opportunity-cost evidence. PC is the natural consumer because final marginal deployment belongs there.

This does not require a new component. It requires clearer naming and propagation of existing evidence.

### FRESH_INCREMENTAL_OPPORTUNITY

Recommended owner:

```text
Existing Candidate/Opportunity + BQ + SI evidence, resolved as a canonical consideration state before PC allocation
```

Reason:

Freshness evidence is not purely PM lifecycle and not purely PC allocation. It is a PIT evidence condition composed from action-neutral opportunity strength, BQ trajectory, SI continuation/admission, and holding-specific context. Existing owners can represent the pieces without duplication if the final state is scoped as "consideration evidence", not "capital allocation."

## C — PM Action Contract Study

| Model | Description | Clarity | Duplication Risk | SI Effect | PC Effect | Backward Compatibility | Observability |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Model 1 — Preserve Current PM ADD | PM continues owning HOLD/ADD/REDUCE/EXIT; clarify reports only. | LOW-MEDIUM: PM ADD remains broad. | LOW | SI remains subordinate filter. | unchanged | HIGH | improves only with labels |
| Model 2 — PM Lifecycle + PC ADD Consideration | PM owns HOLD/REDUCE/EXIT lifecycle; ADD consideration is existing SI/BQ/ADD evidence consumed by PC. | HIGH | MEDIUM if poorly named, LOW if consideration is non-final | SI remains evidence owner, not order authority | PC receives explicit consideration candidate and still owns allocation | MEDIUM | HIGH, because state vs consideration becomes visible |
| Model 3 — Narrow Fresh-Event PM ADD | PM keeps ADD but redefines it as only fresh incremental opportunity. | MEDIUM | MEDIUM-HIGH, because PM must own freshness and lifecycle | SI must either feed or be subordinated to PM | PC flow remains similar when ADD emitted | LOW-MEDIUM | good if successful, but broad migration |

Study result:

Model 1 is too weak because it preserves the current semantic ambiguity.

Model 3 is attractive conceptually but risks moving freshness/opportunity authority into PM and may require broad migration of PM ADD historical meaning.

Model 2 best matches current evidence ownership: PM controls lifecycle, SI/BQ/Candidate describe opportunity/consideration, and PC controls capital deployment.

## D — Strategy Intelligence Role

Current SI already produces:

- `ADD_ALLOWED`
- `ADD_REDUCED_ONLY`
- `HEALTHY_CONTINUATION_ENTRY`
- `CONTINUATION_WITH_CAUTION`
- continuation quality
- downside risk status
- lifecycle / prior ADD / prior REDUCE context

Current SI also marks this as non-action-authoritative.

Recommended semantic role:

```text
SI should remain NON_ACTION_AUTHORITATIVE evidence, but its ADD consideration output can become canonical evidence consumed by PC.
```

This does not violate PM ownership if:

- PM still owns whether current exposure should be retained, reduced, or exited.
- SI does not issue order actions.
- PC uses SI's consideration evidence only for incremental-capital competition.
- PC retains final authority over NEW/ADD/Cash deployment.

Do not automatically promote SI to ADD action authority.

## E — Candidate / Opportunity Role

Held securities can already be evaluated by existing Candidate/Opportunity machinery. Current artifacts show held PC members can preserve opportunity rank/score and candidate reconciliation evidence such as:

- `candidate_duplicate_reconciled:<symbol>`
- `opportunity_buy_rank`
- `runtime_opportunity_score`
- `runtime_opportunity_score_authority`

One opportunity representation can serve both held and unheld securities if it remains action-neutral.

Answer:

```text
COMMON_OPPORTUNITY_SUBSTRATE_WITH_HOLDING_SPECIFIC_INCREMENTAL_AUTHORITY
```

Action-neutral common evidence:

- opportunity rank
- runtime opportunity score
- expected-edge evidence
- trend/momentum
- BQ
- Market Quality
- regime
- liquidity/execution feasibility

Portfolio state should determine whether the opportunity is interpreted as NEW candidate, HOLD strength, or ADD consideration later.

## F — ADD-Specific Evidence Classification

| Evidence | Classification | Notes |
| --- | --- | --- |
| current exposure | `RISK_ADJUSTMENT` / `HARD_GATE` | prevents over-concentration and duplicate exposure |
| average cost | `VALUE_INPUT` | needed for no-loss / incremental exposure context |
| current return | `VALUE_INPUT` / `ELIGIBILITY` | supports no-loss averaging |
| no-loss averaging | `HARD_GATE` | legitimate ADD-specific constraint |
| campaign health | `ELIGIBILITY` | confirms same-campaign continuation |
| prior ADD count | `HARD_GATE` / `RISK_ADJUSTMENT` | exposure/churn safeguard |
| prior REDUCE history | `HARD_GATE` / `OBSERVABILITY` | requires review before renewed ADD |
| MFE/giveback | `RISK_ADJUSTMENT` / `VALUE_INPUT` | position-specific profit retention context |
| concentration/headroom | `HARD_GATE` | capital safety and sizing boundary |
| safety cap | `HARD_GATE` | non-negotiable exposure control |
| incremental opportunity cost | `VALUE_INPUT` / `ELIGIBILITY` | compares next ADD lot against NEW/Cash alternatives |

This prevents ADD from becoming merely:

```text
NEW with current_position=true
```

## G — Three Existing-Component Architecture Models

| Criterion | Model 1 Preserve Current PM ADD | Model 2 PM Lifecycle + PC ADD Consideration | Model 3 Narrow Fresh-Event PM ADD |
| --- | --- | --- | --- |
| authority clarity | LOW-MEDIUM | HIGH | MEDIUM |
| duplication | LOW but ambiguous | LOW if contracts are precise | MEDIUM-HIGH |
| PIT safety | unchanged | strong if consideration evidence is serialized PIT | strong but PM must consume more evidence |
| fail-closed behavior | unchanged | preserve gates before PC/PS | preserve gates but migration sensitive |
| PC/PS compatibility | HIGH | HIGH with semantic adapter/contract | HIGH after PM migration |
| complexity | LOW | MEDIUM | MEDIUM-HIGH |
| migration blast radius | LOW | MEDIUM | HIGH |
| valid opportunity suppression risk | MEDIUM-HIGH | LOWER, because consideration can be observed before final PC gates | MEDIUM |
| overtrading risk | LOW | controllable through ADD-specific gates and PC allocation | controllable but PM freshness rule risk |
| NEW/ADD/Cash competition fit | WEAK-MEDIUM | HIGH | MEDIUM |

Architecturally strongest:

```text
Model 2 — PM Position Lifecycle + PC ADD Consideration
```

Rationale:

It separates lifecycle from incremental-capital consideration without creating a new component. It uses the existing action-neutral opportunity substrate, preserves ADD-specific gates, and leaves final allocation inside PC.

## H — Current Design Preservation Test

| Question | Model 1 | Model 2 | Model 3 |
| --- | --- | --- | --- |
| What behavior remains unchanged? | almost all | BUY_NEW/SELL/Risk/Cash/PS order semantics can remain unchanged initially | PC/PS order semantics mostly unchanged |
| What semantic must change? | labels only | ADD consideration becomes explicit non-final evidence | PM ADD meaning narrows |
| Artifact migration needed? | reports/observability | PM/SI/PC member contract, shadow fields first | PM decision schema and historical meaning |
| Does BUY_NEW change? | NO | NO | NO |
| Does SELL change? | NO | NO | NO |
| Does Risk Pacing change? | NO | NO | NO |
| Does Cash policy change? | NO | NO | NO |
| Does PS/Runtime need semantic changes? | NO | likely NO for activation if PC emits same final BUY_ADD authority; shadow observability first | likely NO after PM emits same ADD authority |
| Can migration be shadow-only first? | YES | YES | YES, but more invasive shadow comparison |

Smallest viable semantic change:

```text
Shadow-only explicit ADD consideration evidence in existing SI/ADD-evidence/PC member artifacts,
with PM lifecycle state preserved and PC still final allocation authority.
```

## I — 3 AJ Plausible Refresh Case Walkthroughs

### `2023-02-06 77760`

Evidence:

- PM action: `HOLD`
- SI: `ADD_REDUCED_ONLY / CONTINUATION_WITH_CAUTION`
- BQ: `FULL_ALLOCATION_ELIGIBLE / HIGH`
- opportunity rank: `5`
- current return: `+7.12%`
- prior change: BQ `BUY_WAIT -> FULL`; relative `MIXED -> SUPPORTIVE`; risk vote `3 -> 1`

| Model | Representation | ADD consideration? | Final capital decision | Legitimate gates remain |
| --- | --- | --- | --- | --- |
| Model 1 | HOLD with ADD-like evidence observable only indirectly | NO unless PM ADD | PC never sees ADD competitor | BQ/risk/cash unchanged |
| Model 2 | HOLD_STRENGTH plus ADD_CONSIDERATION evidence | YES as consideration, not order | PC | risk, BQ, opportunity cost, lot, Cash |
| Model 3 | PM would need to decide whether refresh is narrow ADD | possible | PC after PM ADD | same plus PM freshness gate |

### `2023-03-01 54010`

Evidence:

- PM action: `HOLD`
- SI: `ADD_ALLOWED / HEALTHY_CONTINUATION_ENTRY`
- BQ: `FULL_ALLOCATION_ELIGIBLE / HIGH`
- opportunity rank: `3`
- current return: `+15.28%`
- prior change: BQ `BUY_WAIT -> FULL`; SI `ADD_REDUCED_ONLY -> ADD_ALLOWED`

| Model | Representation | ADD consideration? | Final capital decision | Legitimate gates remain |
| --- | --- | --- | --- | --- |
| Model 1 | HOLD, strong evidence remains non-deployable | NO unless PM ADD | none for ADD | all current gates |
| Model 2 | strongest example of explicit consideration candidate | YES | PC | prior ADD, risk, BQ, opportunity cost, lot, Cash |
| Model 3 | PM might emit narrow ADD if freshness contract passes | possible | PC | same, but PM owns freshness action |

### `2023-06-16 40520`

Evidence:

- PM action: `HOLD`
- SI: `ADD_ALLOWED / HEALTHY_CONTINUATION_ENTRY`
- BQ: `FULL_ALLOCATION_ELIGIBLE / HIGH`
- opportunity rank: `5`
- current return: `+8.59%`
- prior evidence: limited immediate lookback

| Model | Representation | ADD consideration? | Final capital decision | Legitimate gates remain |
| --- | --- | --- | --- | --- |
| Model 1 | HOLD with indirect strong-state evidence | NO unless PM ADD | none for ADD | all current gates |
| Model 2 | possible consideration with freshness evidence caveat | YES/REVIEW depending evidence sufficiency | PC | prior evidence sufficiency, risk, BQ, opportunity cost |
| Model 3 | PM freshness rule likely needs REVIEW due limited lookback | possible but stricter | PC after PM ADD | PM freshness sufficiency plus downstream gates |

No walkthrough states that any row should have been bought.

## J — 118 PM ADD Preservation Test

Phase32-AI showed:

- PM ADD decisions: `118`
- `STATE_DOMINANT`: `103`
- `MIXED`: `15`
- `CHANGE_DOMINANT`: `0`
- actual BUY_ADD fills: `9`

| Model | State-strength observability | Avoid repeated state as fresh | Downstream filtering | ADD flood risk | Prior ADD safeguards |
| --- | --- | --- | --- | --- | --- |
| Model 1 | preserved | weak | preserved | low | preserved |
| Model 2 | preserved as HOLD_STRENGTH / consideration evidence | strong if consideration separates state vs refresh | preserved in PC/ADD evidence | controllable through ADD-specific gates and PC | preserved |
| Model 3 | preserved only if PM stores rejected/near-miss evidence | strong if PM freshness rule is good | preserved after PM | controllable but PM rule-sensitive | preserved but migration-sensitive |

Model 2 best preserves observability while preventing the 118 PM ADD state-strength signals from automatically becoming fresh opportunities.

## K — NEW / ADD Relationship

Conclusion:

```text
COMMON_OPPORTUNITY_SUBSTRATE_WITH_HOLDING_SPECIFIC_INCREMENTAL_AUTHORITY
```

NEW and ADD are not fully separate investment ideas at the security-opportunity layer. They share action-neutral evidence about the security and its opportunity strength.

They diverge at portfolio-state and incremental-capital authority:

- NEW asks whether to open exposure.
- ADD asks whether the next lot improves an existing campaign enough to increase exposure after position-specific gates.
- PC owns final capital allocation among NEW / ADD / Cash.

Action classification boundary:

```text
security opportunity evidence
-> portfolio state and lifecycle evidence
-> ADD-specific eligibility/value/risk gates
-> PC final capital allocation
```

## L — New Component Necessity Re-test

Classification:

```text
EXISTING_COMPONENTS_CAN_SUPPORT_WITH_SEMANTIC_REFACTOR
```

New component is not needed on current evidence.

Reasons:

- Candidate/Opportunity, BQ, SI, PM, ADD evidence, PC, and PS already hold the necessary data domains.
- The issue is not absence of data, but ambiguous ownership of ADD consideration vs PM action.
- Model 2 can preserve ownership boundaries without duplicating PM or PC.
- No genuine missed fresh incremental opportunity was proven in AJ.

## M — Preferred Architecture Study Result

Preferred conceptual model:

```text
Model 2 — PM Position Lifecycle + PC ADD Consideration
```

Selection criteria:

| Criterion | Judgment |
| --- | --- |
| investment philosophy alignment | strong: keeps lifecycle discipline separate from capital competition |
| authority clarity | strongest of the three |
| minimal duplication | good if SI remains evidence and PC remains allocator |
| PIT correctness | compatible with serialized PIT evidence |
| smallest blast radius | larger than Model 1, smaller and cleaner than Model 3 |
| safety controls | preserves prior ADD, risk, concentration, no-loss, BQ, Cash gates |
| shadow-testability | strong |
| avoids historical outcome optimization | yes |

Implementation is not performed in AK. Before implementation, the model should be shadow validated on actual artifacts.

## Required Final Answers

1. `WHO_SHOULD_OWN_HOLD_STRENGTH`

```text
PM
```

2. `WHO_SHOULD_OWN_ADD_CONSIDERATION`

```text
Existing SI / ADD evidence should produce non-final ADD consideration evidence; PC should consume it.
```

3. `WHO_SHOULD_OWN_FRESH_INCREMENTAL_OPPORTUNITY`

```text
Existing Candidate/Opportunity + BQ + SI evidence should represent the PIT freshness/strength evidence as consideration, without becoming final action authority.
```

4. `WHO_SHOULD_OWN_FINAL_NEXT_LOT_CAPITAL_DECISION`

```text
PC
```

5. `CAN_EXISTING_CANDIDATE_OPPORTUNITY_BE_SHARED_BY_NEW_AND_ADD`

```text
YES
```

It should remain action-neutral.

6. `WHAT_MUST_REMAIN_ADD_SPECIFIC`

```text
current exposure, average cost, current return/no-loss, campaign health, prior ADD count,
prior REDUCE history, MFE/giveback, concentration/headroom, safety cap,
incremental opportunity cost, and executable next-lot feasibility.
```

7. `IS_CURRENT_PM_ADD_ACTION_SEMANTIC_TOO_BROAD`

```text
YES
```

It often means persistent strong state rather than proven fresh incremental opportunity.

8. `SHOULD_PM_REMAIN_ADD_ACTION_AUTHORITY`

```text
NO_AS_CURRENT_BROAD_SEMANTIC; PM SHOULD_REMAIN_LIFECYCLE_AUTHORITY
```

PM should continue to own position health/lifecycle. ADD as incremental capital consideration should be separated conceptually before any behavioral change.

9. `CAN_PC_CONSUME_ADD_CONSIDERATION_WITHOUT_NEW_COMPONENT`

```text
YES
```

PC already owns final capital allocation and can process ADD when supplied the appropriate authority.

10. `WHICH_OF_MODEL_1_2_3_IS_ARCHITECTURALLY_STRONGEST`

```text
Model 2 — PM Position Lifecycle + PC ADD Consideration
```

11. `WHAT_IS_THE_MINIMUM_SEMANTIC_CHANGE_REQUIRED`

```text
Introduce shadow-observable ADD consideration semantics within existing SI/ADD-evidence/PC-member contracts,
while preserving PM lifecycle authority and PC final allocation authority.
```

No thresholds, weights, or Production action changes are implied by AK.

12. `IS_A_NEW_COMPONENT_NEEDED`

```text
NO
```

13. `CAN_THE_CHANGE_BE_SHADOW_VALIDATED_FIRST`

```text
YES
```

14. `IS_IMPLEMENTATION_JUSTIFIED_AFTER_AK`

```text
CONDITIONAL_YES_FOR_SHADOW_ONLY_SEMANTIC_INSTRUMENTATION; NO_FOR_PRODUCTION_BEHAVIOR_CHANGE
```

15. `WHAT_EXACTLY_SHOULD_BE_VALIDATED_BEFORE_IMPLEMENTATION`

```text
Validate that existing artifacts can deterministically classify HOLD_STRENGTH, ADD_CONSIDERATION,
and FRESH_INCREMENTAL_OPPORTUNITY candidates using only PIT evidence; validate that PC can consume
shadow ADD consideration without altering orders; validate no BUY_NEW, SELL, Risk Pacing, Cash,
BQ, prior ADD, G129, PS, or Runtime semantic regression; validate that repeated state is not
misclassified as fresh opportunity.
```

## Semantic Clarification / Authority Change / Behavioral Change / Unproven Assumptions

| Category | Judgment |
| --- | --- |
| semantic clarification | Required: separate HOLD strength, ADD consideration, and fresh incremental opportunity. |
| authority change | Conceptual change recommended: ADD consideration should not be identical to broad PM ADD action; PC remains final allocator. |
| behavioral change | Not approved in AK. Shadow-only validation first. |
| still-unproven assumptions | That explicit ADD consideration improves deployment; that a genuine fresh opportunity was missed; that prior ADD history blocks genuine renewals; that a new component is necessary. |

## Final Judgment

```text
PHASE32_AK_EXISTING_COMPONENT_ADD_SEMANTIC_REFACTOR_STUDY_COMPLETED_MODEL2_PREFERRED_SHADOW_VALIDATION_REQUIRED
```

The existing component architecture can support the ADD semantic refactor. The strongest current conceptual model is PM lifecycle authority plus PC-consumed ADD consideration evidence, with Candidate/Opportunity and BQ remaining action-neutral and ADD-specific evidence preserving exposure, campaign, risk, and next-lot constraints. No new component and no Production behavior change are justified by AK alone.
