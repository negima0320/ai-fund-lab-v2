# Phase32-GT — History-Neutral BUY Priority Rank-First vs Current-PIT Quality Authority Adversarial Design Review

Date: 2026-09-05 JST

Scope: READ-ONLY / DESIGN-ONLY. No source/config/schema/runtime state changes were made. The running 650BD run was not stopped, resumed, replayed, recovered, or otherwise changed. Historical return, realized PnL, future return, MFE/MAE, and final campaign outcome were not used as design evidence.

## Executive Judgment

History-neutral BUY priority does not require Current Opportunity rank to be absolute final authority. The correct investment authority is a history-neutral joint comparator inside existing MCV/NCU/PC responsibilities: same-day Current Opportunity rank remains a first-class input, but same-day Current-PIT quality, momentum, trend, continuation, Entry/BQ, MCV class, and NCU evidence should also participate before capital priority is finalized.

The GN repair correctly removed forbidden history/relationship/accepted-increment channels, but it overreached into Current-PIT quality by making rank the leading comparator key and demoting MCV quality class to post-rank tie/evidence. The right follow-up is design validation for Option C, not an immediate Production behavior change.

## Authority Semantic Map

| authority | meaning | priority role | forbidden use |
|---|---|---|---|
| Candidate AI | candidate validity / attractiveness before opportunity ranking | source evidence only | final BUY priority by candidate array order |
| Current Opportunity rank | same-day cross-sectional relative BUY opportunity order | important comparator input | absolute final capital authority by itself |
| BQ / Entry quality | PIT admission quality, allocation eligibility, reliability, and scaling evidence | current-quality comparator evidence | Submit/Safety/SELL authority |
| Momentum | PIT direction, persistence, acceleration, deterioration | current strength/weakness evidence | standalone action authority |
| Trend | PIT continuation or weakening evidence | current-quality comparator evidence | standalone HOLD/BUY/EXIT authority |
| Continuation | whether current strength remains coherent | current-quality comparator evidence | old winner/campaign favoritism |
| MCV | marginal capital value comparison among current eligible uses | proper home for investment priority semantics | history, cost basis, realized PnL, accepted-increment prerequisite |
| NCU | next capital unit comparison authority | single existing cross-candidate comparator | duplicated comparator in PC/PS/runtime |
| hard eligibility | broker, safety, guard, lot/cap/liquidity feasibility | gate / skip reason | investment attractiveness boost |
| current-position relationship | materializes BUY_NEW vs BUY_ADD after priority | post-priority relationship and sizing path | priority boost/penalty |
| campaign/history | audit lineage and bounded recent-exit guard only | no ordinary BUY priority role | old ownership, prior ADD/EXIT, average cost, realized PnL priority |

CURRENT_BUY_AUTHORITY_SEMANTIC_MAP_COMPLETE: `YES`

## Rank Meaning

CURRENT_OPPORTUNITY_RANK_MEANING: `same-day cross-sectional relative opportunity order from the Opportunity ranking artifact, copied into PC as input_opportunity_rank; it is not absolute quality, not expected return, not BUY-vs-cash authority, and not a complete marginal-capital decision by itself.`

SoT basis:

- `opportunity_buy_rank` is the canonical BUY opportunity rank.
- PC copies it as `input_opportunity_rank`.
- The architecture keeps rank separate from portfolio selection order and runtime planning order.
- Rank authority does not change BQ, Entry, PM, Re-entry, Submit Guard, max exposure, cash buffer, or future-PnL boundaries.

## Quality Meaning

CURRENT_PIT_QUALITY_MEANING: `same-day PIT evidence for admission quality, reliability, allocation strength, momentum/trend/continuation state, incremental investment suitability, and marginal capital value. It is not old ownership/history.`

Quality-side signals are PIT evidence:

- BQ evaluates relative opportunity quality, market context modifier, signal reliability, execution feasibility, and portfolio fit.
- Entry decides whether BUY_NEW is allowed, reduced, waiting, or rejected.
- Momentum/trend/continuation describe current market/security state.
- MCV/NCU decide relative next-capital-unit attractiveness among current alternatives.

These signals must exclude historical test result, paper ledger result, future price, future PnL, old campaign PnL, average cost, and realized PnL.

## Is Rank Alone Sufficient?

RANK_ALONE_SUFFICIENT_INVESTMENT_PRIORITY_AUTHORITY: `NO`

Reason:

- Rank expresses same-day relative order, but not full conviction, continuation state, quality sufficiency, incremental value, or risk-adjusted capital preference.
- The SoT explicitly states `BUY_NEW` requires candidate eligibility, sufficient opportunity, BUY Quality eligibility, incremental investment eligibility, portfolio fit, and capital/safety feasibility.
- The SoT also states relative rank alone is not sufficient: best remaining candidate does not automatically mean BUY_NEW.

Rank is necessary, but insufficient.

## Information Relationship

RANK_QUALITY_INFORMATION_RELATIONSHIP: `PARTIALLY_OVERLAPPING_WITH_INDEPENDENT_ADDITIONAL_INFORMATION`

Reason:

- Rank and quality both reference current opportunity attractiveness, so there is overlap.
- BQ/Entry/momentum/trend/continuation/MCV/NCU also encode information rank alone does not canonically own: admission quality, signal reliability, continuation, execution feasibility, portfolio fit, incremental value, and marginal capital sufficiency.
- GS observed 219 rank-quality conflict cases in post-GN early long-run artifacts, which proves the fields are not simply identical in materialized production evidence.

No correlation or PnL inference is needed for this conclusion.

## GN Over-Correction

GN_HISTORY_NEUTRAL_REPAIR_OVERREACHED_INTO_CURRENT_PIT_QUALITY: `YES`

What GN needed to remove:

- old ownership
- closed campaign state
- prior ADD count
- prior EXIT outside bounded recent-exit guard
- average cost
- realized PnL
- accepted-increment prerequisite
- held/flat relationship priority effects

What GN also weakened:

- same-day MCV quality class
- same-day BQ/Entry strength
- same-day momentum/trend/continuation evidence
- same-day NCU marginal quality evidence

Current code evidence: `marginal_capital_value.sort_key()` orders by Current Opportunity rank first, then MCV comparison class, then fallback sufficiency, then symbol. That makes MCV class unable to outrank rank except as a tie-break after equal/missing rank.

## Investment Philosophy

HISTORY_NEUTRALITY_SHOULD_STAY: `YES`

CURRENT_PIT_QUALITY_AUTHORITY_SHOULD_STAY: `YES`

AI Fund Lab’s philosophy is momentum-oriented swing / rotation:

- enter symbols with strong forward-looking PIT opportunity evidence
- hold winners while continuation remains valid
- add only when strength and incremental value exist
- rotate to materially stronger opportunities
- allow cash when evidence is insufficient
- prohibit old ownership penalties

This philosophy aligns better with rank plus Current-PIT quality than rank-only. Rank-only can preserve clean ordering, but it cannot express “strong opportunities first” when rank and same-day strength evidence conflict.

## NEW / ADD Parity And History Neutrality

NEW_ADD_PARITY_WITH_QUALITY_FEASIBLE: `YES`

Quality can return to the comparator without reviving held/flat asymmetry if the comparator evaluates a common current BUY opportunity row before relationship materialization:

```text
current PIT opportunity + BQ/Entry + momentum/trend/continuation + MCV/NCU
-> canonical BUY priority
-> relationship materialization as BUY_NEW or BUY_ADD
-> PC target / budget / safety / lot / sizing / runtime
```

HISTORY_NEUTRALITY_WITH_QUALITY_FEASIBLE: `YES`

History-neutrality remains intact if the comparator explicitly excludes old ownership, closed campaign state, prior ADD, prior EXIT outside bounded guard, average cost, realized PnL, campaign PnL, and accepted increment.

## Existing Architecture

EXISTING_ARCHITECTURE_ONLY_FEASIBLE: `YES`

- NEW_MODULE_REQUIRED: `NO`
- NEW_AUTHORITY_REQUIRED: `NO`
- NEW_COMPARATOR_REQUIRED: `NO`

Existing responsibility is enough:

- Candidate / Opportunity provide rank and current opportunity evidence.
- BQ / Entry provide current PIT admission and quality evidence.
- MCV owns marginal capital comparison semantics.
- NCU remains the single next-capital-unit comparator.
- PC consumes the resulting priority and handles target/budget/safety relationship.

ARBITRARY_NUMERIC_WEIGHTING_REQUIRED: `NO`

No `rank 70% + quality 30%`, fixed score blend, historical tuning, rank cutoff, or quality cutoff is required. The repair should use existing semantic classes and typed comparator ordering.

## Options

### Option A — Current Rank Absolute-First

OPTION_A_JUDGMENT: `REJECT_AS_FINAL_DESIGN / KEEP_AS_RUNNING_BASELINE`

Pros:

- cleanest history-neutrality
- easy auditability
- observed zero rank-priority inversions
- preserves NEW/ADD parity

Cons:

- rank becomes de facto final capital priority
- MCV/NCU quality class is reduced to tie/evidence after rank
- observed rank-quality conflicts cannot express stronger same-day quality if rank is lower
- conflicts with SoT language that rank alone is insufficient

Use: keep the current 650BD run unchanged as a rank-first baseline.

### Option B — Current-PIT Quality Class First, Rank Tie-Break

OPTION_B_JUDGMENT: `REJECT_AS_TOO_COARSE`

Pros:

- restores quality-class authority
- keeps history out if quality fields are constrained to PIT evidence

Cons:

- risks recreating the pre-GN problem in a cleaner costume: broad quality class can dominate rank too aggressively
- class-first may over-lift lower-ranked names whenever class buckets are coarse
- rank becomes too weak in the opposite direction

Use: not recommended as the primary repair.

### Option C — Quality-Aware Rank Inside Existing MCV/NCU Comparator

OPTION_C_JUDGMENT: `ACCEPT_AS_RECOMMENDED_DESIGN_DIRECTION`

Recommended semantic:

```text
hard current eligibility / bounded recent-exit guard
-> current PIT quality sufficiency class
-> current PIT rank within comparable quality relation
-> current PIT quality conflict resolver for materially stronger same-day evidence
-> deterministic symbol fallback
-> relationship materialization BUY_NEW / BUY_ADD
```

Option C does not discard rank or quality:

- rank remains the canonical same-day cross-sectional ordering input
- quality remains same-day investment-strength evidence
- NCU/MCV own the comparison
- relationship/history remain excluded
- accepted increment remains excluded from priority formation

No new threshold should be introduced. The comparator should rely on existing semantic classes such as MCV class, BQ action, Entry action, continuation state, momentum trajectory, sufficiency, hard eligibility, and NCU comparison state.

RECOMMENDED_OPTION: `Option C`

## MCV / NCU Responsibility

MCV_NCU_QUALITY_AUTHORITY_ROLE: `current-PIT marginal capital comparison authority; it should compare where the next unit of capital is best placed among current eligible alternatives using both Opportunity rank and Current-PIT quality evidence.`

If MCV/NCU does not use quality at all before priority, it becomes mostly an opportunity-rank ordering adapter rather than a marginal capital value authority.

CANDIDATE_RANK_FINAL_AUTHORITY_ROLE: `one important input, not final absolute authority and not mere tie-break only`

Candidate/Opportunity rank should be stronger than a display field, but weaker than a solo final authority. It belongs inside MCV/NCU as a primary input to a semantic comparator.

## Safety / SELL / Cash Isolation

Required changes:

- SELL_CHANGE_REQUIRED: `NO`
- SIZING_CHANGE_REQUIRED: `NO`
- CASH_CHANGE_REQUIRED: `NO`
- ADD_SAFETY_CHANGE_REQUIRED: `NO`
- REENTRY_CHANGE_REQUIRED: `NO`

Isolation rules:

- HOLD / REDUCE / EXIT / Winner Protection remain PM/Safety authority.
- ADD Safety, bounded Recent Exit Guard, lot, cap, liquidity, and G129 remain downstream gates.
- Cash remains residual / first-class optionality evidence; no forced deployment, minimum cash, fixed exposure target, or cash tuning is introduced.
- Runtime must continue consuming PS quantity; no runtime priority recomputation.

## Adversarial Cases

| case | Option C expected behavior |
|---|---|
| rank1 comparable vs rank3 strong | compare same-day strength semantically; rank1 does not automatically win if rank3 has materially stronger current PIT MCV/NCU class |
| rank3 strong vs rank5 strong | rank resolves within same strong quality relation |
| rank1 strong vs rank2 comparable | rank1 strong wins absent hard constraints |
| NEW vs ADD same evidence | same comparator result; relationship materializes after priority |
| old campaign symbol | old campaign is audit lineage only; no priority boost or penalty |
| recent EXIT symbol | bounded Recent Exit Guard may block/release as guard, not as permanent history penalty |
| ADD safety blocked | ADD Safety blocks downstream allocation; does not mutate investment priority |
| lot infeasible | PS/lot skip; no lower-priority implicit promotion without explicit residual handling |
| Cash exhaustion | buying power/cash can stop deployment; does not rewrite priority |
| Winner unaffected | PM Winner/HOLD/REDUCE/EXIT remains outside BUY priority |

## Information-Loss Test

CURRENT_GN_INFORMATION_LOSS_FOUND: `YES`

LOST_INFORMATION_TYPES:

- same-day MCV quality class override ability
- same-day BQ / Entry strength as priority input beyond eligibility
- same-day momentum/trend/continuation conflict resolution
- same-day NCU marginal-strength comparison beyond post-rank tie/evidence
- Current-PIT incremental investment strength as a semantic comparator input

If all of this had already been fully encoded into Current Opportunity rank, GS would not have observed rank-quality conflicts and current code would not need to carry the quality fields through MCV/PC. The artifacts show those fields remain distinct.

## Minimal Repair Feasibility

MINIMAL_REPAIR_FEASIBLE: `YES`

Minimal design target, not implementation:

- keep priority generation inside `marginal_capital_value.py`
- keep priority consumption inside `portfolio_construction.py`
- keep NCU as the single comparator authority
- keep priority before accepted-increment filtering
- keep relationship materialization after priority
- alter only comparator ordering semantics so current PIT quality can participate before final priority
- do not change PS, Runtime, PM, SELL, Winner, Cash, ADD Safety, G129, or REENTRY

## 650BD Interpretation

CONTINUE_650BD_UNCHANGED: `YES`

The running 650BD post-GN rank-first run should be preserved as the current GN baseline. It should not be changed mid-run. Its value increases if it remains a clean baseline for later Option C shadow/design comparison.

PRODUCTION_CHANGE_JUSTIFIED_NOW: `NO`

ADDITIONAL_SHADOW_VALIDATION_REQUIRED: `YES`

Reason: the design case for Option C is strong, but implementation should follow a new focused phase with shadow or differential validation that proves:

- history-neutrality remains intact
- NEW/ADD parity remains intact
- rank-quality conflicts are resolved by PIT evidence, not PnL
- no SELL/Winner/Sizing/Cash/ADD/G129/REENTRY/Runtime regression
- no new numeric weights, thresholds, or hidden fallback authority

## Required Answers

- CURRENT_BUY_AUTHORITY_SEMANTIC_MAP_COMPLETE: `YES`
- CURRENT_OPPORTUNITY_RANK_MEANING: `same-day cross-sectional relative Opportunity order; important input, not absolute quality or complete capital authority`
- CURRENT_PIT_QUALITY_MEANING: `same-day BQ/Entry/momentum/trend/continuation/MCV/NCU evidence; not old ownership/history`
- RANK_ALONE_SUFFICIENT_INVESTMENT_PRIORITY_AUTHORITY: `NO`
- RANK_QUALITY_INFORMATION_RELATIONSHIP: `PARTIALLY_OVERLAPPING_WITH_INDEPENDENT_ADDITIONAL_INFORMATION`
- GN_HISTORY_NEUTRAL_REPAIR_OVERREACHED_INTO_CURRENT_PIT_QUALITY: `YES`
- HISTORY_NEUTRALITY_SHOULD_STAY: `YES`
- CURRENT_PIT_QUALITY_AUTHORITY_SHOULD_STAY: `YES`
- NEW_ADD_PARITY_WITH_QUALITY_FEASIBLE: `YES`
- HISTORY_NEUTRALITY_WITH_QUALITY_FEASIBLE: `YES`
- EXISTING_ARCHITECTURE_ONLY_FEASIBLE: `YES`
- NEW_MODULE_REQUIRED: `NO`
- NEW_AUTHORITY_REQUIRED: `NO`
- NEW_COMPARATOR_REQUIRED: `NO`
- ARBITRARY_NUMERIC_WEIGHTING_REQUIRED: `NO`
- OPTION_A_JUDGMENT: `KEEP_AS_BASELINE / REJECT_AS_FINAL_DESIGN`
- OPTION_B_JUDGMENT: `REJECT_AS_TOO_COARSE`
- OPTION_C_JUDGMENT: `ACCEPT_AS_RECOMMENDED_DESIGN_DIRECTION`
- RECOMMENDED_OPTION: `Option C`
- CANDIDATE_RANK_FINAL_AUTHORITY_ROLE: `important input inside MCV/NCU semantic comparator, not absolute final authority`
- MCV_NCU_QUALITY_AUTHORITY_ROLE: `current-PIT marginal capital comparison authority using rank plus quality evidence`
- SELL_CHANGE_REQUIRED: `NO`
- SIZING_CHANGE_REQUIRED: `NO`
- CASH_CHANGE_REQUIRED: `NO`
- ADD_SAFETY_CHANGE_REQUIRED: `NO`
- REENTRY_CHANGE_REQUIRED: `NO`
- CURRENT_GN_INFORMATION_LOSS_FOUND: `YES`
- LOST_INFORMATION_TYPES: `MCV quality class override ability; BQ/Entry strength; momentum/trend/continuation conflict resolution; NCU marginal-strength comparison; current incremental investment strength`
- MINIMAL_REPAIR_FEASIBLE: `YES`
- CONTINUE_650BD_UNCHANGED: `YES`
- PRODUCTION_CHANGE_JUSTIFIED_NOW: `NO`
- ADDITIONAL_SHADOW_VALIDATION_REQUIRED: `YES`
- NEXT_STEP: `Open a focused design/validation phase for Option C: define a history-neutral quality-aware MCV/NCU comparator contract, add shadow/differential acceptance criteria for rank-quality conflict cases, and keep the current 650BD run unchanged as the rank-first baseline.`

Final Judgment: history-neutral BUY priority does not require absolute rank-first authority; same-day Current-PIT quality / momentum / trend / continuation / MCV / NCU should participate again inside the existing MCV/PC/NCU comparator, while the current 650BD rank-first run continues unchanged and no production change is justified until shadow validation passes.
