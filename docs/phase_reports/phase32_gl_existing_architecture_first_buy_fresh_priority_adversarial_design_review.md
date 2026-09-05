# Phase32-GL — Existing-Architecture-First BUY Fresh Priority Integration Adversarial Design Review

Status: DESIGN / READ-ONLY

Production implementation performed: NO

Historical simulation rerun/resume/recovery performed: NO

## Executive Judgment

The Phase32-GK Option B recommendation is not revalidated as a strict architectural requirement.

Source-level review shows that the accepted Phase32-GJ history-neutral Current Opportunity BUY priority can be realized as a Production candidate inside existing Portfolio Construction / Marginal Capital Value / NCU / Position Sizing responsibilities, without adding a new permanent module, component, authoritative artifact, or schema family.

The safer revised recommendation is Option A': an existing-architecture-only repair that separates BUY priority from weight sizing inside Portfolio Construction and MCV, while preserving NCU as the single comparison authority and Position Sizing as the lot/quantity authority.

## Source-Level Architecture Map

Reviewed production boundaries:

- `portfolio_construction.py`
  - `_reconcile_members()`
  - `_resolve_target_weight_contract()`
  - `_reconcile_incremental_budget()`
  - `build_capital_competition_framework()`
  - `apply_lot_aware_final_reallocation()`
- `marginal_capital_value.py`
  - `candidate_intent()`
  - `accepted_increment()`
  - `apply_marginal_capital_priority()`
  - `build_unified_marginal_capital_shadow()`
  - `build_fresh_target_portfolio_shadow()`
- `position_sizing.py`
  - `build_position_sizing_payload()`
  - `_apply_canonical_deployment_set_to_sizing_rows()`
  - `_raw_position()`
- `runtime_planning.py`
  - `build_runtime_planning_payload()`

Existing responsibility boundaries are already adequate:

- Portfolio Construction owns membership, target-weight contract, capital competition, and canonical deployment rows.
- Marginal Capital Value owns investment comparison semantics and NCU-backed ordering.
- NCU remains the single cross-candidate comparison authority.
- Position Sizing consumes PC-selected deployment rows and owns lot, quantity, affordability, caps, and executable deltas.
- Runtime Planning maps already decided PC/PS/PM outputs into executable plan rows and must not recompute BUY ranking.
- Position Management owns existing-position lifecycle actions, including HOLD / ADD / REDUCE / EXIT intent.

## GK Option B Rechallenge

GK Option B proposed a new Fresh BUY Priority component to avoid contaminating target weights, SELL logic, sizing authority, and PM lifecycle semantics.

That concern was directionally valid, but the source does not prove that a new component is strictly required.

The real boundary that must be fixed is narrower:

`apply_marginal_capital_priority()` currently filters priority candidates through `accepted_increment(row) > 0`. Those accepted increments are produced after Portfolio Construction has already reconciled members against current holdings, PM actions, target weights, baseline required weights, requested ADDs, requested BUY_NEW rows, and incremental budget. As a result, the Production BUY priority can become dependent on portfolio history and current-position relationship before the investment comparison is finalized.

That is a repairable existing-function ordering problem, not proof of missing architecture.

## First History-Dependent BUY Boundary

The first history-dependent BUY boundary is not Position Sizing.

It appears earlier:

1. `_reconcile_members()` creates a current-position-first member universe, attaches current-position state, PM action, campaign IDs, membership intent, weight intent, and construction priority.
2. `_resolve_target_weight_contract()` selects target members and assigns target weights under current portfolio constraints.
3. `_reconcile_incremental_budget()` builds `ADD_INCREMENT` and `BUY_NEW` participant requests from current-vs-target deltas and available incremental budget.
4. `marginal_capital_value.apply_marginal_capital_priority()` ranks only rows with a positive accepted/requested increment.

The decisive issue is step 4: the MCV priority function currently sees a deployment-shaped subset rather than a pure current-opportunity BUY comparison universe.

## Existing-Architecture-Only Repair

Option A' should repair the existing path without adding a permanent module:

1. Keep BUY priority generation inside existing `marginal_capital_value.py`.
2. Keep priority consumption inside existing `portfolio_construction.py`.
3. Rank the current point-in-time BUY opportunity universe before accepted-increment filtering.
4. Use opportunity evidence, NCU/MCV class, input opportunity rank, current quality, and deterministic symbol fallback as priority inputs.
5. Do not use current-position status, open campaign state, closed campaign history, prior ownership, or target-weight delta as priority inputs.
6. After priority is assigned, let existing Portfolio Construction translate relationship into `BUY_NEW` versus `ADD_INCREMENT`.
7. Let existing target-weight and incremental budget code decide accepted weights.
8. Let Position Sizing continue to decide lots, quantities, affordability, caps, and final executable deltas.

This can be implemented as an internal MCV/PC helper or mode on the existing MCV function. It should not create a new module, a new authoritative artifact, or a new schema family.

## Priority / Weight Separation

The redesigned path must maintain a hard separation:

- BUY priority answers: among current eligible BUY opportunities, which name has better marginal capital value now?
- Target weight answers: after PC decides membership and target allocation, how much portfolio weight should the name receive?
- Position sizing answers: after PC selects deployment rows, what lot-aware executable order is allowed?

Fresh Target SHADOW equal-ish weights are not Production target weights. They are validation evidence only and must not become a source of Production allocations.

## BUY_NEW / BUY_ADD Parity

BUY_NEW and BUY_ADD parity is feasible inside existing PC/MCV responsibilities.

The parity rule should be:

- Held eligible opportunity with PM ADD intent competes as `BUY_ADD`.
- Flat eligible opportunity competes as `BUY_NEW`.
- Both are ranked by the same current-opportunity priority key.
- Existing-position status may determine action relationship, lot path, and safety checks.
- Existing-position status must not boost or penalize investment priority.

ADD safety remains preserved because open-campaign and existing-position evidence may still constrain whether an ADD is allowed and sized. It simply cannot decide that an inferior held ADD outranks a superior flat BUY_NEW.

## SELL / PM / Winner / Cash Preservation

The repair does not require SELL path changes.

SELL, REDUCE, EXIT, HOLD, winner protection, and PM lifecycle policy remain outside BUY priority ranking. Existing PM authority is preserved because Portfolio Construction does not invent lifecycle actions; it reconciles PM actions with opportunity rows and target membership.

Cash semantics are also preserved. Cash remains buying-power / remaining-budget / affordability evidence. No Fresh Target cash weight becomes authoritative, and no new cash target allocation is introduced.

## NCU Preservation

Existing NCU single-authority semantics are preservable.

The repair should reuse existing MCV/NCU comparison fields and current opportunity evidence, not create a second comparator. Any priority annotation should be an internal PC/MCV output over the same member universe or an existing artifact extension, not a competing artifact family.

## Fresh Target SHADOW Boundary

Fresh Target SHADOW must remain validation-only.

Allowed uses:

- adversarial comparison
- observability
- freshness acceptance diagnostics
- parity validation
- regression detection

Forbidden Production uses:

- target weights
- cash weights
- order actions
- executable quantities
- BUY_NEW / BUY_ADD authority
- SELL / RELEASE / EXIT semantics
- override of PC, PM, PS, or NCU authority

## Adversarial Cases

Option A' passes the required adversarial cases if the above invariants are enforced:

- High current-opportunity flat BUY_NEW must not lose merely because it lacks ownership history.
- Lower-quality held ADD must not outrank better flat BUY_NEW through open campaign state.
- PM EXIT / REDUCE rows must not be pulled into BUY priority mutation.
- HOLD rows must not become BUY candidates without PM/PC eligibility.
- Recent EXIT guard may block or bound eligibility, but must not become a broad history penalty.
- Fresh Target SHADOW equal-weight rows must not set Production target weights.
- Lot-aware reallocation must consume PC-selected rows and not recompute investment priority.
- Position Sizing must not resurrect rejected BUY candidates.
- Existing ADD safety must remain enforced after priority selection.
- G129 sizing preservation must remain unchanged.
- Current cash must remain budget/affordability evidence.
- Winner protection must remain independent from BUY priority correction.
- Missing priority evidence must fail closed or fall back deterministically with explicit review evidence.
- No hidden action-label ranking bonus may appear between BUY_NEW and BUY_ADD.

## Simplification Candidates

Keep:

- PM lifecycle ownership for HOLD / ADD / REDUCE / EXIT.
- PC ownership of membership, target weights, capital competition, and deployment rows.
- MCV/NCU ownership of investment comparison.
- PS ownership of lots, quantities, caps, and executable deltas.
- Runtime non-recomputation of priority.
- Fresh Target SHADOW as observability and validation.

Restrict:

- current-position fields as priority inputs.
- campaign identifiers as priority inputs.
- construction priority fallback to deterministic compatibility only.
- accepted-increment filtering before canonical BUY priority is established.

Deprecate:

- any priority path where positive accepted increment is a prerequisite for investment comparison.
- Fresh Target equal-ish target weights as a possible Production bridge.
- hidden BUY_ADD or BUY_NEW action-label preference.

Remove in future cleanup if found:

- old ownership penalties outside the bounded recent EXIT guard.
- closed-campaign or prior-holding history effects in BUY priority.
- duplicate shadow-to-production bridges that imply more than one capital authority.

## Option Comparison

Option A' — Existing PC/MCV/NCU repair:

- New module count: 0
- New authoritative artifact count: 0
- New schema family count: 0
- Architecture fit: strongest
- Correctness: feasible
- Blast radius: low to medium
- Main risk: accidental priority/weight mixing unless guarded by tests and explicit field ownership comments

Option B — New Fresh BUY Priority component:

- New module/component count: at least 1
- New authority surface: likely
- Architecture fit: clean separation, but heavier than source evidence requires
- Correctness: feasible
- Blast radius: medium
- Main risk: permanent duplicate authority beside existing MCV/NCU/PC

Option C — promote Fresh Target SHADOW directly:

- Architecture fit: rejected
- Correctness: unsafe
- Main risk: imports SHADOW weights, cash semantics, and relationship labels into Production

## Required Answers

GK_OPTION_B_NEW_COMPONENT_REASON_REVALIDATED: NO_AS_STRICT_REQUIREMENT

EXISTING_PC_PRIORITY_WEIGHT_RELATIONSHIP_BOUNDARIES_MAPPED: YES

FIRST_HISTORY_DEPENDENT_BUY_BOUNDARY: `marginal_capital_value.apply_marginal_capital_priority()` ranking only rows with `accepted_increment(row) > 0` after PC current-state target/increment reconciliation

EXISTING_ARCHITECTURE_ONLY_REPAIR_FEASIBLE: YES

OPTION_A_REDESIGNED_SAFELY: YES_OPTION_A_PRIME

PRIORITY_WEIGHT_SEPARATION_WITHIN_EXISTING_PC_FEASIBLE: YES

BUY_NEW_ADD_PARITY_WITHIN_EXISTING_PC_FEASIBLE: YES

EXISTING_SIZING_FULLY_PRESERVABLE: YES

ADD_SAFETY_FULLY_PRESERVABLE: YES

G129_FULLY_PRESERVABLE: YES

CURRENT_CASH_SEMANTIC_FULLY_PRESERVABLE: YES

SELL_CODE_PATH_TOUCHED_REQUIRED: NO

PM_AUTHORITY_CHANGED_REQUIRED: NO

WINNER_PROTECTION_CHANGED_REQUIRED: NO

EXISTING_NCU_SINGLE_AUTHORITY_PRESERVED: YES

HIDDEN_RERANKING_REQUIRED: NO

FRESH_TARGET_SHADOW_PRODUCTION_AUTHORITY_REQUIRED: NO

NEW_COMPONENT_STRICTLY_REQUIRED: NO

NEW_AUTHORITATIVE_ARTIFACT_REQUIRED: NO

NEW_SCHEMA_FAMILY_REQUIRED: NO

OPTION_A_NEW_MODULE_COUNT: 0

OPTION_A_NEW_AUTHORITATIVE_ARTIFACT_COUNT: 0

OPTION_A_NEW_SCHEMA_FAMILY_COUNT: 0

OPTION_A_ADVERSARIAL_CASES_PASS: YES_BY_DESIGN_IF_INVARIANTS_ENFORCED

OPTION_A_SELL_SPILLOVER_PREVENTED: YES

OPTION_A_WEIGHT_SPILLOVER_PREVENTED: YES

LEGACY_HISTORY_AUTHORITY_SIMPLIFICATION_CANDIDATES: accepted-increment-gated priority, current-position priority inputs, campaign-history priority inputs, action-label priority bonuses, Fresh Target equal-weight bridge assumptions

RECOMMENDED_ARCHITECTURE_AFTER_REVIEW: OPTION_A_PRIME_EXISTING_PC_MCV_NCU_REPAIR

PRODUCTION_BLAST_RADIUS: LOW_TO_MEDIUM

DIRECT_PRODUCTION_IMPLEMENTATION_READY: NO

ADDITIONAL_REVIEW_REQUIRED: YES

NEXT_STEP: implement a narrow existing-PC/MCV BUY-priority repair with focused tests proving BUY_NEW/BUY_ADD parity, SELL isolation, weight separation, NCU preservation, and Position Sizing preservation

## Final Judgment

Yes: the GJ-accepted history-neutral BUY Current Opportunity priority can be realized as a Production candidate without a new permanent module, component, authoritative artifact, or schema family, using existing PC/MCV/NCU/Sizing responsibilities while preserving SELL, Winner, Sizing, Cash, and ADD Safety semantics.
