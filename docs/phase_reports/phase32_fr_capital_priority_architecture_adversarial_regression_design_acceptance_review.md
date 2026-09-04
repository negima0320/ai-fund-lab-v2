# Phase32-FR Capital Priority Architecture Adversarial Regression / Design Acceptance Review

## Scope

- Review type: Architecture / Design / READ-ONLY adversarial review.
- Target design: Phase32-FQ Capital Priority Architecture.
- Evidence base: Phase32-FO / FP / FQ, FC, FG/FH, FK, FL, FM/FN, Strategy / Runtime / PC / MCV / Cash / Opportunity Rank SoT, and current source.

No Production, SHADOW, source, config, schema, runtime state, Pending, or Ledger mutation was performed. No fresh-run, resume, recover, or replay was executed.

This review does not use future returns, later PnL, MFE/MAE, or final campaign outcome to choose Production features, thresholds, weights, ranks, or parameters.

## FQ Design Reconstruction

`FQ_DESIGN_RECONSTRUCTED`: YES.

The FQ design is:

```text
hard eligibility
-> comparable capital option materialization
-> MCV-extended next-capital-unit SHADOW comparator
-> PC final allocation remains unchanged in shadow
-> PS quantity authority remains unchanged
-> Runtime/Pending/Ledger unchanged
```

Common comparison surface:

| Option | Evidence used | Hard eligibility owner | Priority owner | Quantity owner |
|---|---|---|---|---|
| BUY_NEW | opportunity rank/score, BQ, Entry, market/risk, broker/CA, recent-exit guard | Candidate/BQ/Entry/PC safety gates | MCV under PC | PS |
| BUY_ADD | PM ADD intent, campaign id, no-loss-averaging, continuation, downside, expected edge, headroom, cap/liquidity | PM / Strategy Intelligence / PC | MCV under PC | PS / G129 |
| CASH | run/date-bound cash, risk posture, market quality, optionality, residual budget | Portfolio Policy / PC cash authority | PC cash competitor | not applicable |

Boundary reconstruction:

- MCV is EXTEND, not REPLACE.
- PC remains final capital allocation owner.
- PM remains current-position lifecycle owner and does not consume BUY_NEW.
- Sizing remains quantity/lot/cap owner and must not reinterpret priority.
- Runtime remains consumer of PC/PS/Pending authority and receives no SHADOW action/quantity authority.

Ambiguity retained: FQ does not define a numeric formula or Production threshold. This is intentional; the next step is SHADOW-only comparability, not Production scoring.

## Common Axis, Not Single Score

`COMMON_AXIS_WITH_ACTION_SPECIFIC_SEMANTICS_FEASIBLE`: YES.

`SINGLE_UNIVERSAL_SCORE_REQUIRED`: NO.

The safe design is a shared capital-value axis with action-specific evidence, not one universal score:

| Option | Preserved action-specific semantic |
|---|---|
| BUY_NEW | new opportunity, discovery, diversification, fresh current PIT entry evidence |
| BUY_ADD | incumbent continuation, no-loss averaging, same-campaign headroom, incremental capital justification |
| CASH | optionality, zero-market-exposure alternative, risk/regime/capital preservation |

A single score would create double-counting and semantic collapse risk. The comparator should instead emit ordered classes/reasons and explicit unresolved states.

## Adversarial Failure Modes

| Failure mode | Risk | Adversarial concern | Required guard |
|---|---|---|---|
| Strong BUY_NEW suppression | MEDIUM | Cash/ADD comparator could delay valid fast risk-on winners. | Strong BUY_NEW golden cases must remain deployable; no fixed cooldown/ramp/cash blanket. |
| ADD over-priority | HIGH | Existing winner label could become an implicit bonus. | ADD competes only after PM ADD, no-loss, continuation, headroom, cap, liquidity, and G129-compatible quantity. |
| Cash over-priority | MEDIUM-HIGH | Cash could become default winner and flatten growth engine. | Cash is first-class option, not automatic winner. Strong current evidence may still beat Cash. |
| Rank over-binding | HIGH | Rank refinement could become disguised top-N gate. | Rank is monotonic/supporting evidence, never fixed BUY/NO_BUY. |
| Evidence double counting | HIGH | BQ/Entry/rank/MCV may reuse common source features. | Comparator must preserve producer lineage and explain whether evidence is independent or derived. |
| Action semantic collapse | MEDIUM | BUY_NEW/ADD/Cash could be reduced to one formula. | Action-specific hard eligibility remains before shared priority. |
| Diversification loss | MEDIUM | Incumbent ADD may crowd out new winner discovery. | BUY_NEW discovery golden cases and new-opportunity class preserved. |
| Concentration increase | HIGH | More ADD may raise single-name exposure. | Current cap/headroom/liquidity/concentration gates remain hard. |

Required answers:

- `STRONG_BUY_NEW_SUPPRESSION_RISK`: `MEDIUM_MITIGATABLE`
- `ADD_OVER_PRIORITY_RISK`: `HIGH_MITIGATABLE_BY_ELIGIBILITY_AND_NO_LABEL_BONUS`
- `CASH_OVER_PRIORITY_RISK`: `MEDIUM_HIGH_MITIGATABLE_BY_NO_BLANKET_CASH_WINNER`
- `RANK_OVER_BINDING_RISK`: `HIGH_MITIGATABLE_BY_NO_FIXED_TOP_N`
- `DIVERSIFICATION_DEGRADE_RISK`: `MEDIUM_MITIGATABLE`
- `CONCENTRATION_DEGRADE_RISK`: `HIGH_MITIGATABLE_BY_EXISTING_CAP_HEADROOM_LIQUIDITY`

## Golden Case Adversarial Matrix

`GOLDEN_CASE_UNEXPLAINED_REGRESSION_COUNT`: 0.

| Case | Current | Proposed SHADOW | Must remain | Regression risk | Evidence / guard |
|---|---|---|---|---|---|
| 2023-03-22 `67750` Strong BUY_NEW | BUY_NEW deployable | Classified and compared, no Production action | BUY_NEW remains eligible | MEDIUM | Fast risk-on invariant; no Cash blanket/cooldown. |
| 2023-04-11 `27210` BUY_NEW | Comparable-high deployable | Comparable capital option | Remains deployable | MEDIUM | BQ/Entry hard gates unchanged. |
| 2023-04-11 `45980` BUY_NEW | Comparable-high deployable | Comparable capital option | Remains deployable | MEDIUM | PC output not consumed by SHADOW. |
| 2023-04-24 `69270` Strong BUY_NEW | Fast deployable | Strong option | Remains fast deployable | MEDIUM | No exposure ramp / no fixed waiting. |
| 2023-07-25 `67310` high-rank BUY_NEW | Eligible BUY_NEW | Problem/golden hybrid | Eligibility unchanged | MEDIUM | Later loss not used to suppress entry. |
| 2023-03-30 `43880` BUY_ADD | G129-safe ADD | ADD competitor after hard gates | BUY_ADD remains eligible | HIGH | PM ADD, campaign id, no-loss, PS increment preserved. |
| 2023-04-04 `83060` BUY_ADD | G129-safe ADD | ADD competitor | BUY_ADD remains eligible | HIGH | No old-history bonus; current ADD evidence only. |
| 2023-06-13 `21340` BUY_ADD | Positive ADD | ADD competitor | Quantity remains PS/G129 scoped | HIGH | No PM quantity authority. |
| 2023-06-13 `76470` cap-blocked ADD | No ADD if cap applies | Blocked option | Cap block remains | HIGH | Comparator cannot bypass five-ADD cap in this phase. |
| 2023-07-25 `94320` incumbent | Held, no accepted increment | Incumbent option, zero-increment explanation | Not converted to BUY_NEW | MEDIUM | campaign identity preserved. |
| Cash preferred defer | zero allocation | Cash option explanation | remains defer | MEDIUM | PC participation/deferral owner unchanged. |
| Recent-exit guard `83060` | bounded guard | hard eligibility block when applicable | remains guard | MEDIUM | no REENTRY semantic revival. |
| Hard risk / CA / broker block | review/block | blocked option | remains block | LOW-MEDIUM | hard eligibility before priority. |
| Lot/cap block | zero/review | blocked by feasibility | remains block | MEDIUM | PS/PC cap and lot unchanged. |

No golden case requires a Production behavior change to be explainable under FQ. All risky cases are only acceptable because the next step is SHADOW non-interference.

## Problem Case Review

`PROBLEM_CASE_COMPARABILITY_IMPROVES`: YES_FOR_SHADOW.

| Problem case | Current issue | FQ/FR shadow value |
|---|---|---|
| 2023-06-05 `31920` rank23 BUY_NEW | Higher-ranked incumbents and BUY_NEW rows above it, many zero-increment or PC/MCV zero. | Compare BUY_NEW vs incumbents vs Cash with rank, Entry, BQ, ADD/headroom evidence preserved. |
| 2023-07-25 `72770` rank39 BUY_NEW | LOW BQ but healthy Entry and MCV `ELIGIBLE_STRONG`; rank-depth compression visible. | Explain whether healthy Entry legitimately dominates rank/BQ weakness or is over-compressed. |
| 2023-07-25 `94320` / `76470` | Rank 1/2 incumbents with ADD-like evidence but zero accepted increment. | Expose ADD hard-gate vs priority gap without forcing ADD. |
| Cash available high-exposure days | Cash exists but often loses final binding. | Distinguish Cash optionality from leftover cash and identify participation-vs-deferral reason. |

FR does not decide what should have been bought. It only confirms the design can preserve current PIT differences for comparison.

## MCV EXTEND Safety

`MCV_EXTEND_REMAINS_MINIMUM_RISK`: YES.

Source/SoT reasons:

- Existing MCV already has `MARGINAL_CAPITAL_VALUE_AUTHORITY`, `UNIFIED_NEXT_CAPITAL_UNIT_SHADOW_AUTHORITY`, and `SECURITY_OPPORTUNITY_SHADOW_AUTHORITY` constants.
- Existing MCV preserves source fields such as rank, BQ, Entry, ADD evidence, current weight, accepted increments, lot feasibility, and concentration.
- Existing comparison classes intentionally map `COMPARABLE_MARGINAL` / `WEAK_VALID` into coarser legacy `ELIGIBLE_COMPARABLE`, which is precisely the compression surface to observe.
- Replacing MCV would risk PC/PS/Runtime authority disruption.

Required safety:

- Do not change existing MCV class semantics in SHADOW.
- Do not make shadow fields consumers for PC/PS/Runtime.
- Do not create dual Production authority.
- Do not rethreshold existing MCV.
- Do not publish quantity/action authority.

## Priority Information Preservation

All required evidence can reach the comparison surface as lineage or source evidence:

| Evidence | Preservation status | Risk |
|---|---|---|
| opportunity rank | available as `input_opportunity_rank` | rank over-binding |
| BQ | available as band/action/component evidence | double-counting |
| Entry | available as admission action/state/sufficiency | over-lifting deep rank |
| Expected Edge | available, often uncalibrated | false precision |
| continuation | available from SI/current position | ADD over-priority |
| downside | available as hard/soft evidence | risk bypass |
| ADD worthiness | available but hard-gated | cap bypass risk |
| headroom/concentration | available in PC/PS | concentration risk |
| Cash interaction | available in PC | cash over/under-priority |

The design is safe only if these are carried as typed evidence, not summed as independent points.

`EVIDENCE_DOUBLE_COUNTING_FOUND`: POTENTIAL_NOT_ACTUAL_IN_DESIGN. Risk is real because BQ, Entry, MCV, and selection quality share underlying rank/trend/quality lineage. It is mitigatable only by lineage-aware evidence grouping.

`AUTHORITY_DUPLICATION_FOUND`: POTENTIAL_NOT_ACTUAL_IN_SHADOW. The shadow layer must not re-decide Candidate/BQ/Entry/PM/PC/PS authority.

## Fast Risk-On / Discovery Preservation

`FAST_RISK_ON_DEGRADE_RISK`: MEDIUM_MITIGATABLE.

FH confirms fast deployment into strong current opportunity is part of the investment philosophy. Therefore the future comparator must reject:

- fixed cooldown after risk-off
- fixed exposure ramp
- historical hesitation penalty
- Cash always wins unless exceptional
- old ownership or campaign age penalty

`CURRENT_STRENGTHS_PRESERVABLE`: YES, but only with golden-case regression checks before Production promotion.

BUY_NEW discovery preservation:

- Fresh top-ranked / BQ HIGH / HEALTHY / strong current evidence must remain eligible.
- ADD cannot win merely because it is incumbent.
- Cash cannot win merely because market is not perfect.
- Rank cannot mechanically reject deep but strongly confirmed candidates.

## ADD / Cash / Rank Safety

`G129_PRESERVABLE`: YES.

BUY_ADD remains an eligible capital competitor, not a priority bonus:

- PM ADD intent required.
- campaign identity required.
- no-loss-averaging required.
- continuation/downside required.
- cap/headroom/liquidity required.
- PS remains quantity owner.
- Runtime consumes only PS-bound order increments.

`CASH_CAN_BE_SAFE_REAL_COMPETITOR`: YES. Cash can be an option, not leftover-only and not default winner.

Rank contract:

- rank should be monotonic/supporting evidence.
- rank alone must not decide BUY/NO_BUY.
- no fixed top-N.
- no mechanical exclusion of deep-rank candidates with strong current confirmation.

## History Bias / REENTRY / SELL Isolation

`LONG_LIVED_HISTORY_BIAS_AVOIDABLE`: YES.

The comparator must not use:

- prior BUY count as bonus/penalty
- prior ADD count as priority score
- prior REDUCE count as priority score
- campaign age as generic penalty
- old ownership history
- run age
- old EXIT reason

Known five-ADD cap remains an upstream hard/eligibility design issue and is not changed by FR.

`REENTRY_EW_EZ_PRESERVABLE`: YES.

- no `semantic_buy_type=REENTRY` revival
- flat symbol remains BUY_NEW
- bounded recent-exit guard only
- old EXIT history does not become current priority authority

`SELL_PM_PRESERVABLE`: YES.

Capital Priority does not touch HOLD, REDUCE, EXIT, `profit_retention_break`, SELL planning, submit, execution, or PM SELL authority.

`PS_RUNTIME_AUTHORITY_PRESERVABLE`: YES.

Shadow output has no order, quantity, action, Pending, Ledger, or Runtime authority.

## Shadow Non-Interference Contract

`SHADOW_NON_INTERFERENCE_PROVEN`: YES_BY_DESIGN_CONTRACT.

Shadow implementation must satisfy:

- Production PC result unchanged.
- PM unchanged.
- PS unchanged.
- Runtime unchanged.
- Pending unchanged.
- Ledger unchanged.
- order authority = NO.
- quantity authority = NO.
- action authority = NO.
- `authoritative_consumer_count = 0`.
- artifact is diagnostic only.

Minimum shadow output:

```text
option_type
symbol
campaign_id
hard_eligibility_status
current_evidence_groups
proposed_comparable_capital_priority
binding_constraint
production_result
shadow_comparison_result
divergence_reason
future_information_used=false
historical_outcome_used=false
authoritative_consumer_count=0
```

Shadow evaluation must use decision behavior:

- golden case preservation
- unexplained priority inversion
- strong BUY_NEW suppression
- ADD over-priority
- Cash over-priority
- rank over-binding
- information-loss reduction
- BUY_NEW/ADD/Cash comparability

It must not select formulas or thresholds from later PnL.

## Shadow Stop Conditions

`SHADOW_STOP_CONDITIONS_DEFINED`: YES.

Stop before Production consideration if any occur:

- unexplained Golden Case regression
- G129 semantic change
- REENTRY regression
- Fast Risk-on suppression
- hard risk / CA / broker / lot / cap bypass
- new long-lived history bias
- PS/Runtime authority leak
- unexplained strong BUY_NEW loss
- Cash blanket dominance
- ADD label bonus
- fixed top-N behavior
- double-counted evidence cannot be disentangled
- source/run/date authority stale or ambiguous

## Minimal Shadow Slice / Alternatives

Recommended minimal shadow slice:

```text
existing MCV evidence EXTEND
-> diagnostic next-capital-unit comparator
-> embedded or referenced from PC capital_competition evidence
-> no Production consumer
```

Alternative comparison:

| Alternative | Fit | Blast radius | Regression risk | Judgment |
|---|---|---:|---:|---|
| A. MCV EXTEND comparator | Strong | Low-Medium in SHADOW | Medium | Best minimum-risk path. |
| B. PC-only comparator | Good | Medium | Medium-High | Viable but risks PC becoming too large. |
| C. Rank refinement only | Weak | Low | High semantic risk | Too narrow; risks fixed top-N behavior. |
| D. Cash strengthening only | Partial | Medium | High | Can damage fast risk-on and discovery. |
| E. Full unified scorer | Poor for now | Critical | Critical | Too much semantic collapse/double-counting risk. |

## Independent Design Challenge

Reasons not to adopt FQ blindly:

| Challenge | Classification | Resolution |
|---|---|---|
| Existing evidence is heterogeneous and not calibrated into one economic unit. | MITIGATABLE | Use classes/reasons, not a single numeric score. |
| BQ/Entry/MCV may double-count rank/trend evidence. | MITIGATABLE | Group source lineage; forbid naive additive scoring. |
| ADD comparability can turn into incumbent favoritism. | MITIGATABLE | Require hard ADD eligibility and no label bonus. |
| Cash comparability can suppress the growth engine. | MITIGATABLE | No blanket Cash winner; preserve strong BUY_NEW. |
| Production PC/MCV change would have high blast radius. | VALID BLOCKER FOR DIRECT PRODUCTION | Shadow-first only. |
| Problem cases are partial-window and not full-year validated. | MITIGATABLE | Shadow actual-path inspection before promotion. |
| Five-ADD cap may dominate ADD availability regardless of comparator. | MITIGATABLE / SEPARATE THREAD | Isolate cap; do not bypass it in FQ/FR. |

`FQ_DESIGN_VALID_BLOCKERS`: DIRECT_PRODUCTION_ONLY.

`FQ_DESIGN_MITIGATABLE_RISKS`: double counting, ADD over-priority, Cash over-priority, rank over-binding, diversification loss, concentration increase, partial evidence calibration.

## Architecture Acceptance

- `DESIGN_SEMANTICALLY_SOUND`: YES
- `DESIGN_MINIMAL_ENOUGH`: YES_FOR_SHADOW
- `GOLDEN_CASES_PRESERVABLE`: YES
- `CURRENT_STRENGTHS_PRESERVABLE`: YES
- `SHADOW_NON_INTERFERENCE_PROVEN`: YES_BY_CONTRACT
- `SHADOW_IMPLEMENTATION_ACCEPTABLE`: YES
- `PRODUCTION_IMPLEMENTATION_READY`: NO

Rationale: the adversarial review found no unexplained golden-case regression and no unavoidable correctness/safety regression if the next step is strictly SHADOW-only. The same review rejects direct Production implementation because PC/MCV/Cash/ADD behavior has high blast radius.

## Required Answer Summary

- `FQ_DESIGN_RECONSTRUCTED`: `YES`
- `COMMON_AXIS_WITH_ACTION_SPECIFIC_SEMANTICS_FEASIBLE`: `YES`
- `SINGLE_UNIVERSAL_SCORE_REQUIRED`: `NO`
- `STRONG_BUY_NEW_SUPPRESSION_RISK`: `MEDIUM_MITIGATABLE`
- `ADD_OVER_PRIORITY_RISK`: `HIGH_MITIGATABLE_BY_ELIGIBILITY_AND_NO_LABEL_BONUS`
- `CASH_OVER_PRIORITY_RISK`: `MEDIUM_HIGH_MITIGATABLE_BY_NO_BLANKET_CASH_WINNER`
- `RANK_OVER_BINDING_RISK`: `HIGH_MITIGATABLE_BY_NO_FIXED_TOP_N`
- `DIVERSIFICATION_DEGRADE_RISK`: `MEDIUM_MITIGATABLE`
- `CONCENTRATION_DEGRADE_RISK`: `HIGH_MITIGATABLE_BY_EXISTING_CAP_HEADROOM_LIQUIDITY`
- `EVIDENCE_DOUBLE_COUNTING_FOUND`: `POTENTIAL_NOT_ACTUAL_IN_DESIGN`
- `AUTHORITY_DUPLICATION_FOUND`: `POTENTIAL_NOT_ACTUAL_IN_SHADOW`
- `FAST_RISK_ON_DEGRADE_RISK`: `MEDIUM_MITIGATABLE`
- `G129_PRESERVABLE`: `YES`
- `REENTRY_EW_EZ_PRESERVABLE`: `YES`
- `SELL_PM_PRESERVABLE`: `YES`
- `PS_RUNTIME_AUTHORITY_PRESERVABLE`: `YES`
- `LONG_LIVED_HISTORY_BIAS_AVOIDABLE`: `YES`
- `GOLDEN_CASE_UNEXPLAINED_REGRESSION_COUNT`: `0`
- `PROBLEM_CASE_COMPARABILITY_IMPROVES`: `YES_FOR_SHADOW`
- `MCV_EXTEND_REMAINS_MINIMUM_RISK`: `YES`
- `SHADOW_NON_INTERFERENCE_PROVEN`: `YES_BY_DESIGN_CONTRACT`
- `SHADOW_STOP_CONDITIONS_DEFINED`: `YES`
- `FQ_DESIGN_VALID_BLOCKERS`: `DIRECT_PRODUCTION_ONLY`
- `FQ_DESIGN_MITIGATABLE_RISKS`: `DOUBLE_COUNTING / ADD_OVER_PRIORITY / CASH_OVER_PRIORITY / RANK_OVER_BINDING / DIVERSIFICATION_LOSS / CONCENTRATION_INCREASE / PARTIAL_CALIBRATION`
- `DESIGN_SEMANTICALLY_SOUND`: `YES`
- `DESIGN_MINIMAL_ENOUGH`: `YES_FOR_SHADOW`
- `CURRENT_STRENGTHS_PRESERVABLE`: `YES`
- `SHADOW_IMPLEMENTATION_ACCEPTABLE`: `YES`
- `PRODUCTION_IMPLEMENTATION_READY`: `NO`

PRODUCTION_CHANGED: NO
SHADOW_CHANGED: NO
SOURCE_CHANGED: NO
CONFIG_CHANGED: NO
SCHEMA_CHANGED: NO
TARGET_RUN_MUTATED: NO
RUNTIME_STATE_MUTATED: NO
FRESH_RUN_EXECUTED: NO
RESUME_REPLAY_RECOVER_EXECUTED: NO
FUTURE_OUTCOME_USED_FOR_PRODUCTION_JUDGMENT: NO

Final Judgment: `PHASE32_FR_FQ_CAPITAL_PRIORITY_DESIGN_ADVERSARIALLY_ACCEPTED_FOR_SHADOW_ONLY_DIRECT_PRODUCTION_BLOCKED`
