# Phase31-G53 — Capital Allocation Architecture Refinement Design

## Scope

Task type: DESIGN ONLY — SYSTEM-WIDE CAPITAL ALLOCATION ARCHITECTURE REFINEMENT.

G53 responds to G52's finding:

`PHASE31_G52_OVER_SUPPRESSION_AND_SINGLE_WINNER_SEMANTIC_DRIFT_CONFIRMED`

No implementation, config, threshold, parameter, fixture, fresh-run, resume,
replay, Historical rerun, or long Historical execution was performed. No
allocation percentage was selected from Historical returns.

Permanent architecture SoT was updated in:

- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`

## Primary Judgment

`PRIMARY_JUDGMENT = PHASE31_G53_MULTI_SECURITY_CONTINUOUS_CAPITAL_PACING_ARCHITECTURE_DEFINED`

G53 defines the replacement architecture: Market Quality and Risk Pacing pace
capital deployment intensity; they do not act as binary BUY admission gates.
Cash remains a true economic competitor, but Cash is no longer required to be a
winner-takes-all outcome. The general capital-allocation semantic becomes
multi-allocation: multiple securities plus Cash may receive authorized
incremental capital in the same business date.

## Project Objective Alignment

`PROJECT_OBJECTIVE_ALIGNMENT = PASS`

The design remains aligned with:

- capital growth as the top-level objective
- approximately +50% annual-return target as strategic aspiration
- momentum-oriented Japanese equity swing trading
- no forced investment
- no fixed number of BUYs
- no fixed exposure target
- no blanket market BUY ban
- BUY / SELL independence
- Position Sizing as discrete quantity owner
- no future information or Historical outcome input
- legitimate small losses accepted only when PIT evidence supports valid
  participation risk

## Permanent Principles

`PROFIT_ENGINE_PRESERVATION_PRINCIPLE_DEFINED = YES`

Defensive / market-aware improvements must preserve the system's ability to
capture valid symbol-level opportunities. Risk reduction is not independently
successful if it destroys the expected profit engine required by the strategy's
capital-growth objective.

`EXPLORATION_RISK_PRINCIPLE_DEFINED = YES`

G53 permanently distinguishes:

- `AVOIDABLE_LOW_QUALITY_RISK`
- `LEGITIMATE_EXPLORATION_OR_PARTICIPATION_RISK`

The system may accept legitimate small losses when PIT evidence supports
participation in potentially asymmetric opportunities. This does not weaken
fast loss control, Safety, missing-evidence fail-closed behavior, or SELL
authority.

## Market Quality And Risk Pacing

`MARKET_QUALITY_ROLE = CAPITAL_PACING_CONTEXT`

`MARKET_QUALITY_HARD_BUY_GATE = NO`

`RISK_PACING_ROLE = CAPITAL_DEPLOYMENT_INTENSITY_AUTHORITY`

`RISK_PACING_BINARY_SECURITY_ADMISSION_OWNER = NO`

Risk Pacing primarily changes deployment intensity, not security admission.
Candidate admission, Safety, corporate-action, special-risk, missing-evidence,
and explicit invalidity authorities remain the hard gates.

## Multi-Allocation Capital Problem

`GENERAL_CAPITAL_WINNER_CARDINALITY = MULTI_ALLOCATION`

`CAPITAL_ALLOCATION_PROBLEM_TYPE = HYBRID_MULTI_SECURITY_CAPITAL_BUDGET_ALLOCATION`

Canonical sequence:

1. Determine valid opportunity universe.
2. Determine Portfolio Policy incremental capital budget envelope.
3. Preserve candidate-local allocation evidence.
4. Portfolio Construction allocates budget across multiple security
   opportunities plus Cash.
5. Position Sizing converts authorized allocations to lots.
6. Portfolio Construction reconsideration handles residual / infeasible
   allocations.
7. Remaining capital returns to Cash.

`CANONICAL_MULTI_ALLOCATION_SEQUENCE_DEFINED = YES`

## Cash Semantics

`CASH_PARTIAL_ALLOCATION_SUPPORTED = YES`

`CASH_WINNER_TAKES_ALL_REQUIRED = NO`

Cash remains a true economic competitor. It may receive all capital when no
valid deployment is justified, or it may receive only part of available
marginal capital while several valid securities receive reduced allocations.
G53 intentionally does not define numeric allocation percentages.

`LEGITIMATE_100_PERCENT_CASH_SUPPORTED = YES`

100% Cash remains valid when no opportunities are valid, evidence is incomplete,
all opportunities are blocked, or market + candidate evidence jointly make
deployment unjustified.

## Authority Boundaries

`CAPITAL_BUDGET_ENVELOPE_OWNER = PORTFOLIO_POLICY`

Portfolio Policy owns `incremental_capital_budget_envelope`: a semantic
deployment-intensity / available marginal capital capacity authority. It may
consume Market Quality, Risk Pacing, portfolio state, existing exposure, Cash
state, and current holdings. It must not select symbols or quantities.

`CAPITAL_BUDGET_SEMANTICS_DEFINED = YES`

Initial semantic states:

- `FULL_DEPLOYMENT_CAPACITY`
- `ELEVATED_DEPLOYMENT_CAPACITY`
- `SELECTIVE_DEPLOYMENT_CAPACITY`
- `DEFENSIVE_DEPLOYMENT_CAPACITY`
- `PRESERVE_MOST_OPTIONALITY`

These are not Historical-return-derived percentages.

`MULTI_ASSET_CAPITAL_ALLOCATION_OWNER = PORTFOLIO_CONSTRUCTION`

Portfolio Construction owns allocation of the authorized marginal budget across
`NEW_BUY`, `ADD`, eligible re-entry-as-`NEW_BUY`, and Cash.

`POSITION_SIZING_REMAINS_QUANTITY_OWNER = YES`

`POSITION_SIZING_SELECTS_ECONOMIC_WINNERS = NO`

Position Sizing receives already-authorized allocations and converts them to
discrete lot-aware quantities. It does not choose winners, re-rank candidates,
or re-open Cash-defeated allocations.

## Opportunity Evidence Preservation

`OPPORTUNITY_INFORMATION_PRESERVATION_REFINED = YES`

`OPPORTUNITY_QUALITY_REMAINS_CANONICAL_SUMMARY = YES`

`WITHIN_CLASS_ALLOCATION_EVIDENCE_AVAILABLE = YES`

Opportunity Quality may remain a canonical summary, but Portfolio Construction
must preserve allocation-relevant within-class PIT evidence, including:

- rank / rank tier
- relative strength
- continuation quality
- early recovery or improving evidence
- stock-specific strength against weak market context
- evidence completeness
- fragility / overheat where authoritative
- Expected Edge evidence where authoritative

Rank alone is not authority. The purpose is to avoid collapsing meaningfully
different candidates into the same allocation result solely because they share
one coarse class.

## Market / Candidate Cases

`WEAK_MARKET_STRONG_STOCK_PARTICIPATION_SUPPORTED = YES`

A weak market / CAUTIOUS context plus strong stock-specific evidence may
produce reduced allocation rather than automatic zero allocation.

`CAUTIOUS_MARGINAL_AUTOMATIC_ZERO = NO`

A marginal valid opportunity under caution may receive reduced allocation, or
Cash may receive that capital, depending on comparative PIT evidence. The class
alone must not force every such opportunity to zero.

`NORMAL_MULTI_OPPORTUNITY_CAPTURE_SUPPORTED = YES`

NORMAL / healthy conditions preserve broad opportunity capture subject to
ordinary Portfolio Construction, lot, concentration, Safety, and evidence
constraints.

## Bootstrap And Reduced-Risk Entry

`BOOTSTRAP_AND_RESIDUAL_CASH_DISTINGUISHED = YES`

`BOOTSTRAP_PARTICIPATION_PATH_DEFINED = YES`

`REDUCED_RISK_INITIAL_ENTRY_DEFINED = YES`

G53 distinguishes:

- `EMPTY_OR_NEAR_EMPTY_PORTFOLIO_BOOTSTRAP`
- `RESIDUAL_OPTIONALITY_CASH`

Empty portfolio bootstrap must not become a permanent optionality trap when
valid PIT opportunities exist. Architecture may support reduced-risk initial
entry / exploration allocation without requiring investment, fixed BUY counts,
fixed holding periods, or fixed exposure.

## Fixed Target And Leakage Guards

`FIXED_MARKET_EXPOSURE_TARGET_CREATED = NO`

The design does not create BEAR=20%, RANGE=50%, BULL=90%, or equivalent fixed
market exposure buckets.

`HISTORICAL_RETURN_DERIVED_ALLOCATION_PERCENTAGE_COUNT = 0`

No allocation percentage, threshold, or matrix boundary was chosen from
Historical return, Paper Ledger, MFE/MAE, or later outcome evidence.

## Lot Reconsideration

`MULTI_ALLOCATION_LOT_RECONSIDERATION_DEFINED = YES`

Lot infeasibility is row-scoped before it is day-scoped. If one authorized
allocation cannot materialize into an executable lot, residual capital may be
reconsidered across remaining valid opportunities and Cash. The entire day's
allocation should collapse only when the residual/reconsideration contract
proves no valid executable allocation remains.

## ADD, Re-entry, Winners, SELL, Safety

`ADD_MULTI_ALLOCATION_SUPPORTED = YES`

`ADD_AUTOMATIC_PRIORITY = NO`

ADD competes in the same capital budget envelope as NEW_BUY and Cash. ADD label
alone is not priority.

`REENTRY_MULTI_ALLOCATION_SUPPORTED = YES`

`REENTRY_SPECIAL_PENALTY = NO`

Eligible re-entry behaves as a normal NEW_BUY capital competitor.

`WINNER_RETENTION_INDEPENDENCE_PRESERVED = YES`

Existing strong holdings are not penalized merely because incremental capital
pacing is cautious.

`BUY_SELL_INDEPENDENCE_PRESERVED = YES`

`SAFETY_AUTHORITY_CHANGED = NO`

SELL/REDUCE/EXIT and Safety authorities are unchanged.

## Evaluation And Acceptance Contracts

`EXPLORATION_VS_AVOIDABLE_LOSS_EVALUATION_CONTRACT_DEFINED = YES`

Future implementation must evaluate separately:

- avoidable low-quality loss prevented
- legitimate exploration / participation losses incurred
- winner opportunities captured
- winner opportunities missed

`PROFIT_ENGINE_PRESERVATION_ACCEPTANCE_DEFINED = YES`

Future acceptance must prove:

- valid multi-security opportunity capture still works
- weak-market reduced deployment works
- strong individual opportunities remain capturable
- Cash can retain part of capital
- Cash can retain all capital when genuinely justified

`MARKET_PACING_SELECTIVITY_REQUIREMENT_DEFINED = YES`

The future architecture must be able to represent different PIT structures
instead of suppressing pre-March and post-March valid opportunities almost
equally. This is a PIT-structure requirement, not a March return optimization.

## G38-G51 Migration Classification

`G43_BINDING_MATRIX_MIGRATION_CLASS = MIGRATE`

The G43 matrix may remain as semantic evidence for pacing and comparison, but
it must not remain the winner-takes-all capital gate.

`SINGLE_DEPLOYMENT_SET_MIGRATION_CLASS = MIGRATE`

The single deployment set migrates to a canonical multi-allocation deployment
set.

`G50_EXECUTABLE_BINDING_PRINCIPLE_PRESERVED = YES`

The valid G50 lesson is preserved: final PC authority must shape Position
Sizing executable input before Runtime Planning can emit BUY/ADD order intents.

`LINEAGE_BINDING_DISTINCTION_PRESERVED = YES`

Lineage persistence remains distinct from executable decision binding.

## Staged Migration Plan

`STAGED_MIGRATION_PLAN_DEFINED = YES`

Implementation must be staged:

A. permanent SoT update

B. capital budget envelope producer

C. multi-security allocation framework

D. Opportunity information preservation

E. bootstrap / reduced-risk entry semantics

F. Position Sizing consumption migration

G. lot / residual reconsideration

H. Runtime lineage migration

I. synthetic acceptance

J. existing-PIT activation / suppression characterization

K. fresh Historical

`BIG_BANG_IMPLEMENTATION_ALLOWED = NO`

## Required Design Decisions

1. Should Risk Pacing primarily change admission or deployment intensity?

Deployment intensity. It is not a binary security admission owner.

2. Can Cash and multiple securities receive capital simultaneously?

Yes. Cash can receive partial allocation while multiple valid securities also
receive authorized capital.

3. Who owns the capital budget envelope?

Portfolio Policy.

4. Who owns allocation across competitors?

Portfolio Construction.

5. Who owns discrete quantity?

Position Sizing.

6. How is empty-portfolio bootstrap different from residual Cash?

Bootstrap cash is undeployed starting capacity that may require cautious
participation to pursue the profit engine. Residual Cash is optionality
preserved after existing exposure / allocations already exist. They must be
separate semantic states.

7. How can the system participate cautiously without being forced to buy?

Portfolio Policy may authorize a defensive or selective budget envelope, and
Portfolio Construction may allocate reduced capital to PIT-valid opportunities
plus Cash. If evidence does not justify participation, Cash may still receive
all capital.

8. How is stock-specific strength preserved under weak Market Quality?

Opportunity Quality remains a summary, but PC must preserve within-class PIT
allocation evidence such as rank tier, relative strength, continuation quality,
early recovery evidence, completeness, and fragility.

9. How does ADD compete under the same framework?

ADD enters the same budget envelope as NEW_BUY and Cash. It has no automatic
priority and no automatic rejection.

10. How does lot reconsideration work with multiple allocations?

Lot infeasibility is row-scoped first. Infeasible or residual capital can be
reconsidered across remaining valid opportunities and Cash before a day-level
no-deployment result is reached.

11. How is G50 executable binding preserved?

The binding object changes from single deployment to multi-allocation
deployment set, but Position Sizing still consumes PC-authorized allocations
before Runtime Planning; downstream stages do not re-decide capital winners.

12. Which G38-G51 semantics are migrated/deprecated?

G43's binary winner-takes-all matrix is migrated into pacing evidence. G50's
single deployment set is migrated into a multi-allocation deployment set. G50's
executable binding and lineage-vs-binding lessons are preserved.

## Required Summary Output

`PRIMARY_JUDGMENT = PHASE31_G53_MULTI_SECURITY_CONTINUOUS_CAPITAL_PACING_ARCHITECTURE_DEFINED`

`PROJECT_OBJECTIVE_ALIGNMENT = PASS`

`PROFIT_ENGINE_PRESERVATION_PRINCIPLE_DEFINED = YES`

`EXPLORATION_RISK_PRINCIPLE_DEFINED = YES`

`MARKET_QUALITY_ROLE = CAPITAL_PACING_CONTEXT`

`MARKET_QUALITY_HARD_BUY_GATE = NO`

`RISK_PACING_ROLE = CAPITAL_DEPLOYMENT_INTENSITY_AUTHORITY`

`RISK_PACING_BINARY_SECURITY_ADMISSION_OWNER = NO`

`GENERAL_CAPITAL_WINNER_CARDINALITY = MULTI_ALLOCATION`

`CAPITAL_ALLOCATION_PROBLEM_TYPE = HYBRID_MULTI_SECURITY_CAPITAL_BUDGET_ALLOCATION`

`CASH_PARTIAL_ALLOCATION_SUPPORTED = YES`

`CASH_WINNER_TAKES_ALL_REQUIRED = NO`

`CAPITAL_BUDGET_ENVELOPE_OWNER = PORTFOLIO_POLICY`

`CAPITAL_BUDGET_SEMANTICS_DEFINED = YES`

`MULTI_ASSET_CAPITAL_ALLOCATION_OWNER = PORTFOLIO_CONSTRUCTION`

`POSITION_SIZING_REMAINS_QUANTITY_OWNER = YES`

`POSITION_SIZING_SELECTS_ECONOMIC_WINNERS = NO`

`OPPORTUNITY_INFORMATION_PRESERVATION_REFINED = YES`

`OPPORTUNITY_QUALITY_REMAINS_CANONICAL_SUMMARY = YES`

`WITHIN_CLASS_ALLOCATION_EVIDENCE_AVAILABLE = YES`

`WEAK_MARKET_STRONG_STOCK_PARTICIPATION_SUPPORTED = YES`

`CAUTIOUS_MARGINAL_AUTOMATIC_ZERO = NO`

`NORMAL_MULTI_OPPORTUNITY_CAPTURE_SUPPORTED = YES`

`BOOTSTRAP_AND_RESIDUAL_CASH_DISTINGUISHED = YES`

`BOOTSTRAP_PARTICIPATION_PATH_DEFINED = YES`

`REDUCED_RISK_INITIAL_ENTRY_DEFINED = YES`

`LEGITIMATE_100_PERCENT_CASH_SUPPORTED = YES`

`FIXED_MARKET_EXPOSURE_TARGET_CREATED = NO`

`HISTORICAL_RETURN_DERIVED_ALLOCATION_PERCENTAGE_COUNT = 0`

`CANONICAL_MULTI_ALLOCATION_SEQUENCE_DEFINED = YES`

`MULTI_ALLOCATION_LOT_RECONSIDERATION_DEFINED = YES`

`ADD_MULTI_ALLOCATION_SUPPORTED = YES`

`ADD_AUTOMATIC_PRIORITY = NO`

`REENTRY_MULTI_ALLOCATION_SUPPORTED = YES`

`REENTRY_SPECIAL_PENALTY = NO`

`WINNER_RETENTION_INDEPENDENCE_PRESERVED = YES`

`BUY_SELL_INDEPENDENCE_PRESERVED = YES`

`SAFETY_AUTHORITY_CHANGED = NO`

`EXPLORATION_VS_AVOIDABLE_LOSS_EVALUATION_CONTRACT_DEFINED = YES`

`PROFIT_ENGINE_PRESERVATION_ACCEPTANCE_DEFINED = YES`

`MARKET_PACING_SELECTIVITY_REQUIREMENT_DEFINED = YES`

`G43_BINDING_MATRIX_MIGRATION_CLASS = MIGRATE`

`SINGLE_DEPLOYMENT_SET_MIGRATION_CLASS = MIGRATE`

`G50_EXECUTABLE_BINDING_PRINCIPLE_PRESERVED = YES`

`LINEAGE_BINDING_DISTINCTION_PRESERVED = YES`

`STAGED_MIGRATION_PLAN_DEFINED = YES`

`BIG_BANG_IMPLEMENTATION_ALLOWED = NO`

`PERMANENT_SOT_UPDATED = YES`

`FUTURE_INPUT_COUNT = 0`

`HISTORICAL_OUTCOME_DESIGN_INPUT_COUNT = 0`

`PAPER_LEDGER_DESIGN_INPUT_COUNT = 0`

`MFE_MAE_DESIGN_INPUT_COUNT = 0`

`IMPLEMENTATION_CHANGE_EXECUTED = NO`

`CONFIG_CHANGE_EXECUTED = NO`

`THRESHOLD_CHANGE_EXECUTED = NO`

`PARAMETER_TUNING_EXECUTED = NO`

`FIXTURE_CHANGE_EXECUTED = NO`

`FRESH_RUN_EXECUTED = NO`

`RESUME_EXECUTED = NO`

`REPLAY_EXECUTED = NO`

`HISTORICAL_RERUN_EXECUTED = NO`

`LONG_HISTORICAL_EXECUTED = NO`

`GIT_DIFF_CHECK = PASS`

`NEXT_TASK_RECOMMENDATION = PHASE31_G54_CAPITAL_BUDGET_ENVELOPE_IMPLEMENTATION_PLANNING`
