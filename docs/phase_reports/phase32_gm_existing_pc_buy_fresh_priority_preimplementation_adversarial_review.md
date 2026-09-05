# Phase32-GM — Existing-PC BUY Fresh Priority Pre-Implementation Adversarial Review

Status: READ-ONLY / PRE-IMPLEMENTATION

Production implementation performed: NO

Source/config/schema changes performed: NO

New module/component/artifact/schema implemented: NO

## Executive Judgment

The Phase32-GL Option A' path can be frozen into a minimal Production implementation spec.

The intended change is narrow: make BUY Investment Priority history-neutral and Current PIT Opportunity based before current-position relationship materializes into `BUY_NEW` or `BUY_ADD`. All target weights, sizing, cash, ADD safety, G129, SELL, Winner, PM, and Runtime responsibilities remain unchanged.

This is not a direct Production promotion. It is an implementation-ready boundary specification plus adversarial acceptance contract.

## Exact Production Change Boundary

EXACT_FUNCTION_CHANGE_SET:

- `src/ai_fund_lab_v2/strategy/portfolio_construction.py::_reconcile_members`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py::_resolve_target_weight_contract`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py::_reconcile_incremental_budget`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py::build_capital_competition_framework`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py::apply_lot_aware_final_reallocation`
- `src/ai_fund_lab_v2/strategy/marginal_capital_value.py::apply_marginal_capital_priority`
- `src/ai_fund_lab_v2/strategy/marginal_capital_value.py::candidate_intent`
- `src/ai_fund_lab_v2/strategy/marginal_capital_value.py::accepted_increment`

Allowed private helper surface:

- Existing-module-only private helper in `portfolio_construction.py` or `marginal_capital_value.py`.
- No new module.
- No new component.
- No new authoritative artifact.
- No new schema family.
- No second comparator.

Regression-only / no production logic change:

- `position_sizing.py::build_position_sizing_payload`
- `position_sizing.py::_apply_canonical_deployment_set_to_sizing_rows`
- `position_sizing.py::_raw_position`
- `runtime_planning.py::build_runtime_planning_payload`
- PM / SELL / Winner code paths

## Current vs Proposed BUY Flow

Current semantic flow:

```text
Current Opportunity
↓
position/campaign relationship participation
↓
BUY path / priority over deployment-shaped accepted increments
↓
target/sizing
```

Proposed Option A' semantic flow:

```text
Current PIT Opportunity
↓
history-neutral BUY Investment Priority
↓
current position relationship
↓
BUY_NEW / BUY_ADD
↓
existing target sizing
↓
existing safety
↓
existing PS / Runtime
```

FIRST_SEMANTIC_CHANGE_POINT:

`marginal_capital_value.apply_marginal_capital_priority()` must stop making positive accepted increment the prerequisite for canonical BUY Investment Priority. Priority must be computed from the current PIT BUY opportunity universe before PC relationship, target-weight, and incremental-budget state narrows the executable set.

## Priority Authority Contract

BUY_PRIORITY_CURRENT_PIT_ONLY_CONTRACT_DEFINED: YES

Allowed priority inputs:

- canonical Current Opportunity rank
- current BQ / Entry evidence
- existing MCV / NCU current PIT evidence
- current hard eligibility facts
- deterministic stable fallback, such as symbol, only after canonical comparison evidence

Forbidden priority inputs:

- old ownership
- closed campaign history
- prior EXIT outside the bounded recent EXIT guard
- prior ADD count as attractiveness
- average cost
- realized PnL
- old campaign PnL
- old campaign age
- current-position relationship label
- `BUY_NEW` / `BUY_ADD` action-label bonus or penalty
- Fresh Target SHADOW target weight
- Fresh Target SHADOW cash/release/exit semantics

CURRENT_POSITION_PRIORITY_INPUT_REMOVED: YES_BY_SPEC

OLD_HISTORY_PRIORITY_INPUTS_REMOVED: YES_BY_SPEC

## Current Position Timing

Current-position state may be read only after canonical BUY priority is assigned.

Permitted post-priority use:

```text
flat -> BUY_NEW
held -> BUY_ADD
```

Invariant:

`current_position_relationship_used_for_priority = false`

## NEW / ADD Parity

BUY_NEW_ADD_RELATIONSHIP_POST_PRIORITY: YES

NEW_ADD_PARITY_SPEC_COMPLETE: YES

Parity rule:

- Same Current PIT Opportunity evidence yields the same BUY Investment Priority for flat and held candidates.
- Relationship materialization happens after priority.
- Held relationship may route the candidate to ADD safety and lot-aware ADD sizing.
- Flat relationship may route the candidate to BUY_NEW sizing.
- ADD safety may block a higher-ranked ADD, allowing a lower-ranked NEW to proceed.
- The block reason must be typed as safety or feasibility, not investment attractiveness.

## Existing Sizing Freeze

SIZING_CODE_CHANGE_REQUIRED: NO

Frozen sizing surfaces:

- BUY_NEW sizing formula
- BUY_ADD sizing formula
- target weight formula
- lot-aware sizing
- concentration constraints
- liquidity constraints
- buying-power handling
- cap/headroom handling
- G129 order increment scope

Position Sizing must remain a consumer of PC-selected deployment rows. It must not recompute BUY Investment Priority.

## Cash Freeze

CASH_SEMANTIC_CHANGE_REQUIRED: NO

Fresh BUY priority decides only the order in which available incremental capital is considered.

Forbidden changes:

- minimum cash
- reserve cash percentage
- forced deployment
- cash target weight
- exposure target
- all-candidate equal allocation
- Fresh Target SHADOW cash allocation authority

## SELL / PM / Winner Isolation

SELL_CODE_PATH_CHANGE_COUNT: 0

PM_AUTHORITY_CHANGE_REQUIRED: NO

WINNER_PROTECTION_CHANGE_REQUIRED: NO

Excluded from future implementation changes:

- HOLD
- REDUCE
- EXIT
- Winner Protection
- Profit Retention
- PM sell evidence
- sell planning
- Fresh Target `EXIT_CANDIDATE`
- Fresh Target sell/release delta

BUY priority must not feed backward into PM outcomes. PM remains the lifecycle action authority, and Fresh Target SHADOW keeps `authoritative_consumer_count = 0`.

## ADD Safety / G129 Freeze

ADD_SAFETY_CHANGE_REQUIRED: NO

G129_CHANGE_REQUIRED: NO

Frozen safety surfaces:

- no-loss averaging
- current campaign deterioration
- concentration
- headroom
- liquidity
- lot feasibility
- G129 order increment scope

Fresh priority may select consideration order; it must not revive a safety-blocked ADD.

## Recent EXIT

RECENT_EXIT_GUARD_CHANGE_REQUIRED: NO

Recent EXIT remains the only bounded history exception.

Contract:

1. Current Opportunity priority is recorded fresh.
2. Recent EXIT guard is applied as downstream hard eligibility or bounded churn control.
3. After the guard window no old EXIT history remains in BUY priority.
4. Permanent EXIT penalty is forbidden.

## NCU Single Authority

NCU_COMPARATOR_INSTANCE_COUNT: 1

HIDDEN_RERANKING_ALLOWED: NO

Forbidden:

- second score
- Fresh BUY score
- NEW bonus
- ADD bonus
- Cash bonus
- hidden re-ranking
- post-PS priority recomputation
- Runtime priority recomputation

Canonical ordering contract:

1. hard current eligibility gate
2. existing NCU / MCV comparison class
3. canonical Current Opportunity rank and current PIT quality evidence
4. deterministic tie-break only
5. relationship materialization into BUY_NEW / BUY_ADD
6. existing target, budget, safety, lot, and sizing filters

## Priority Skip Reasons

PRIORITY_SKIP_REASON_CONTRACT_DEFINED: YES

Allowed typed skip reasons:

- HARD_ELIGIBILITY
- RECENT_EXIT_GUARD
- ADD_SAFETY
- LOT_INFEASIBLE
- CAP_HEADROOM
- LIQUIDITY
- BUYING_POWER_EXHAUSTED

Forbidden skip reasons:

- old ownership
- old campaign
- old ADD count
- average cost
- realized PnL
- prior campaign age

## Capital Exhaustion Contract

CAPITAL_EXHAUSTION_CONTRACT_DEFINED: YES

Available capital is considered in canonical BUY priority order until existing budget, headroom, lot, liquidity, cap, or safety constraints prevent more deployment.

This does not change sizing formulas and does not introduce equal allocation across all candidates.

## Fresh Target SHADOW Role

Fresh Target SHADOW remains allowed for:

- observability
- regression comparison
- history-neutrality validation
- adversarial acceptance diagnostics

Fresh Target SHADOW remains forbidden as:

- Production target weight authority
- Production cash authority
- Production order authority
- Production quantity authority
- Production SELL / RELEASE / EXIT authority
- PM override
- PS override
- NCU replacement

Required invariant:

`fresh_target_portfolio_shadow_authoritative_consumer_count = 0`

## Minimal Code Diff Forecast

Expected implementation scale:

- Modified source modules: 2
- New modules: 0
- New permanent components: 0
- New authoritative artifacts: 0
- New schema families: 0
- New comparator instances: 0
- Expected source LOC scale: small to medium, mostly helper extraction and call ordering
- Expected tests: focused unit/contract tests in strategy test suite

Expected implementation shape:

- Add or adjust an existing-module private helper to build BUY priority over the current PIT opportunity universe.
- Call that helper before accepted-increment-gated deployment selection.
- Store or propagate priority using existing member/capital competition surfaces where possible.
- Restrict current-position/campaign/history evidence from the priority key.
- Keep current-position relationship only for post-priority `BUY_NEW` / `BUY_ADD` materialization.
- Keep existing PS, Runtime, PM, SELL, Winner, Cash, and G129 logic unchanged.

Deleted/restricted history branches:

- Do not necessarily delete on first implementation.
- Restrict history-related branches out of BUY priority.
- Preserve branches that are safety, eligibility, observability, or lifecycle authority.

## History Branch Classification

KEEP:

- current position for relationship materialization after priority
- PM lifecycle action
- ADD safety checks
- recent EXIT guard as bounded eligibility/churn control
- current holdings for current weight, baseline, and executable sizing
- average cost where needed for no-loss ADD safety

RESTRICT_TO_SAFETY:

- current campaign deterioration
- prior ADD count
- average cost
- current position sizing context
- headroom and concentration evidence

REMOVE_FROM_PRIORITY:

- current position
- prior ADD count
- prior EXIT outside recent guard
- old campaign state
- old ownership
- average cost
- realized PnL
- old campaign PnL / age

OBSERVABILITY_ONLY:

- Fresh Target SHADOW weights
- Fresh Target SHADOW cash/release/exit rows
- closed-campaign diagnostics
- historical divergence diagnostics
- winner churn comparison evidence

## Golden Cases

GOLDEN_CASE_TESTS_DEFINED: YES

Required focused tests:

1. rank1 NEW / rank2 NEW
2. rank1 ADD / rank2 NEW
3. rank1 NEW / rank2 ADD
4. same evidence flat vs held
5. higher ADD blocked -> lower NEW proceeds
6. higher NEW lot infeasible -> lower proceeds
7. recent EXIT guard skip
8. old EXIT does not skip
9. old campaign does not skip
10. prior ADD count does not change priority
11. Winner HOLD unaffected
12. PM EXIT unaffected
13. existing REDUCE unaffected
14. Cash exhaustion
15. G129 increment scope
16. no-loss ADD block

## Problem Case Mapping

PROBLEM_CASE_TESTS_DEFINED: YES

Required mappings:

- GA actual BUY divergence -> prove selected Production BUY order follows Current PIT Opportunity priority before history relationship effects.
- GJ held/flat parity -> same opportunity evidence produces same investment priority for held and flat.
- NEW-vs-ADD asymmetry -> no action-label bonus or penalty.
- `67310` -> reproduce prior suppression/path-dependence and prove priority no longer depends on historical ownership.
- prior campaign suppression -> old campaign state cannot skip or demote BUY priority.
- prior ADD suppression -> prior ADD count cannot skip or demote BUY priority.
- current-position priority path dependence -> current_position affects only relationship and sizing after priority.

## Adversarial Regression Cases

ADVERSARIAL_REGRESSION_CASES_DEFINED: YES

Attack list:

- NEW starvation
- ADD starvation
- NEW/ADD action label bias
- history penalty revival
- hidden reranking
- forced Cash deployment
- sizing drift
- SELL spillover
- Winner behavior drift
- G129 regression
- ADD safety bypass
- candidate order instability

## Production Acceptance Metrics

PRODUCTION_ACCEPTANCE_METRICS_DEFINED: YES

Required implementation acceptance metrics:

- priority order preservation rate
- history-caused priority inversion count
- held/flat parity
- NEW/ADD parity
- SELL behavior exact regression
- Sizing exact regression
- Cash semantic exact regression
- ADD Safety preservation
- G129 preservation
- Runtime mapping preservation
- Fresh Target SHADOW authoritative consumer count remains zero

PnL is not a primary acceptance criterion.

## Rollback Boundary

ROLLBACK_BOUNDARY_DEFINED: YES

Rollback must be limited to the BUY priority ordering change inside existing PC/MCV code.

Rollback must not require reverting:

- SELL / REDUCE / EXIT behavior
- PM lifecycle authority
- Winner protection
- Position Sizing formulas
- Cash semantics
- ADD safety
- G129 order increment scope
- Runtime mapping
- Fresh Target SHADOW instrumentation

Recommended implementation guard:

- isolate the new priority ordering behind one internal helper/call point
- keep old sizing and action materialization code structurally intact
- add regression tests proving rollback does not need PS/PM/SELL changes

## SoT Update Plan

SOT_UPDATE_PLAN_DEFINED: YES

Architecture SoT updates should be prepared after implementation passes focused tests.

Target documents:

- `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/02_architecture/strategy_intelligence_architecture_v1.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md`

Permanent specification to encode:

- BUY Investment Priority is Current PIT Opportunity authority.
- NEW/ADD relationship materializes after priority.
- Historical ownership/campaign history is not BUY attractiveness authority.
- Recent EXIT is only bounded churn eligibility.
- SELL authority remains PM-owned.
- Position Sizing remains lot/quantity authority.
- Fresh Target SHADOW remains non-authoritative.

## Implementation Readiness Gate

BUY_ONLY_IMPLEMENTATION_READY: YES_FOR_FOCUSED_IMPLEMENTATION

DIRECT_PRODUCTION_PROMOTION_READY: NO

ADDITIONAL_REVIEW_REQUIRED: NO_BEFORE_FOCUSED_IMPLEMENTATION; YES_BEFORE_PRODUCTION_PROMOTION

Readiness checks:

- exact boundary fixed: YES
- BUY-only scope proven: YES
- SELL isolation proven: YES_BY_BOUNDARY
- sizing freeze proven: YES_BY_BOUNDARY
- Cash freeze proven: YES_BY_BOUNDARY
- ADD/G129 freeze proven: YES_BY_BOUNDARY
- no new authority proven: YES
- rollback boundary defined: YES
- focused tests defined: YES

## Required Answers

EXACT_FUNCTION_CHANGE_SET: `portfolio_construction._reconcile_members`, `portfolio_construction._resolve_target_weight_contract`, `portfolio_construction._reconcile_incremental_budget`, `portfolio_construction.build_capital_competition_framework`, `portfolio_construction.apply_lot_aware_final_reallocation`, `marginal_capital_value.apply_marginal_capital_priority`, `marginal_capital_value.candidate_intent`, `marginal_capital_value.accepted_increment`

FIRST_SEMANTIC_CHANGE_POINT: `marginal_capital_value.apply_marginal_capital_priority` must compute canonical BUY priority before accepted-increment-gated deployment filtering

BUY_PRIORITY_CURRENT_PIT_ONLY_CONTRACT_DEFINED: YES

CURRENT_POSITION_PRIORITY_INPUT_REMOVED: YES_BY_SPEC

OLD_HISTORY_PRIORITY_INPUTS_REMOVED: YES_BY_SPEC

BUY_NEW_ADD_RELATIONSHIP_POST_PRIORITY: YES

NEW_ADD_PARITY_SPEC_COMPLETE: YES

SIZING_CODE_CHANGE_REQUIRED: NO

CASH_SEMANTIC_CHANGE_REQUIRED: NO

SELL_CODE_PATH_CHANGE_COUNT: 0

PM_AUTHORITY_CHANGE_REQUIRED: NO

WINNER_PROTECTION_CHANGE_REQUIRED: NO

ADD_SAFETY_CHANGE_REQUIRED: NO

G129_CHANGE_REQUIRED: NO

RECENT_EXIT_GUARD_CHANGE_REQUIRED: NO

NCU_COMPARATOR_INSTANCE_COUNT: 1

HIDDEN_RERANKING_ALLOWED: NO

PRIORITY_SKIP_REASON_CONTRACT_DEFINED: YES

CAPITAL_EXHAUSTION_CONTRACT_DEFINED: YES

NEW_MODULE_COUNT: 0

NEW_COMPONENT_COUNT: 0

NEW_AUTHORITATIVE_ARTIFACT_COUNT: 0

NEW_SCHEMA_FAMILY_COUNT: 0

GOLDEN_CASE_TESTS_DEFINED: YES

PROBLEM_CASE_TESTS_DEFINED: YES

ADVERSARIAL_REGRESSION_CASES_DEFINED: YES

PRODUCTION_ACCEPTANCE_METRICS_DEFINED: YES

ROLLBACK_BOUNDARY_DEFINED: YES

SOT_UPDATE_PLAN_DEFINED: YES

BUY_ONLY_IMPLEMENTATION_READY: YES_FOR_FOCUSED_IMPLEMENTATION

DIRECT_PRODUCTION_PROMOTION_READY: NO

ADDITIONAL_REVIEW_REQUIRED: NO_BEFORE_FOCUSED_IMPLEMENTATION; YES_BEFORE_PRODUCTION_PROMOTION

NEXT_STEP: implement the focused existing-PC/MCV BUY priority repair with the defined golden/problem/adversarial tests, leaving PS/Runtime/PM/SELL/Winner/Cash/ADD/G129 production logic unchanged

## Final Judgment

Yes: the specification is fixed enough to safely implement a zero-new-authority minimal Production repair that absorbs only history-neutral BUY Current Opportunity priority into existing PC/MCV, materializes NEW/ADD after priority, and preserves current SELL, Winner, Sizing, Cash, ADD Safety, G129, and Runtime responsibilities.
