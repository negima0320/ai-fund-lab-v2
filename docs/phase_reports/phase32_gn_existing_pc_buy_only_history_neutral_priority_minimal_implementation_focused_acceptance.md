# Phase32-GN — Existing-PC BUY-Only History-Neutral Current Opportunity Priority Minimal Implementation / Focused Acceptance

Status: IMPLEMENTED / FOCUSED ACCEPTANCE

Historical fresh-run/resume/replay/recover performed: NO

Runtime state / Pending / Ledger mutation performed: NO

## Executive Judgment

Phase32-GN implemented the Phase32-GM Option A' boundary as a minimal existing-PC/MCV repair.

The implemented semantic change is limited to BUY Investment Priority:

```text
Current PIT Opportunity rank/evidence
-> canonical BUY priority
-> current-position relationship
-> BUY_NEW / BUY_ADD
-> existing PC target/budget/safety/lot flow
-> existing PS / Runtime consumers
```

SELL, REDUCE, EXIT, PM authority, Winner Protection, Cash semantics, ADD Safety,
G129, Position Sizing formulas, Runtime Planning, and Fresh Target SHADOW
authority were not intentionally changed.

## Production Source Changes

Changed production source:

- `src/ai_fund_lab_v2/strategy/marginal_capital_value.py`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`

MCV changes:

- `sort_key()` now makes canonical Current Opportunity rank the leading BUY priority key.
- MCV quality/comparison class remains current-PIT tie/evidence after rank.
- `construction_priority` is used only as deterministic compatibility fallback when explicit opportunity rank is absent.
- `apply_marginal_capital_priority()` no longer requires positive accepted/requested increment before assigning BUY priority.
- explicit audit fields record:
  - `buy_priority_current_pit_only = true`
  - `relationship_materialized_after_priority = true`
  - `current_position_priority_input_count = 0`
  - `old_history_priority_input_count = 0`
  - `accepted_increment_required_for_priority = false`
  - `ncu_comparator_instance_count = 1`
  - `hidden_reranking_found = false`

PC changes:

- `_reconcile_incremental_budget()` now always consumes the canonical MCV priority index when ordering BUY participant requests.
- `apply_lot_aware_final_reallocation()` now always consumes the canonical MCV priority index when ordering lot-aware BUY candidates.
- The prior broad fallback from MCV priority to construction priority whenever any comparison was insufficient was removed.
- Construction priority remains only a deterministic fallback/tie key.

No Position Sizing, Runtime Planning, PM, SELL, Winner, Cash, ADD Safety, G129,
or REENTRY production logic was changed.

## Exact GM Boundary Audit

EXACT_GM_BOUNDARY_RESPECTED: YES

GM production boundary touched:

- `marginal_capital_value.apply_marginal_capital_priority`
- `marginal_capital_value.sort_key`
- `portfolio_construction._reconcile_incremental_budget`
- `portfolio_construction.apply_lot_aware_final_reallocation`

GM boundary present but not semantically changed in this phase:

- `portfolio_construction._reconcile_members`
- `portfolio_construction._resolve_target_weight_contract`
- `portfolio_construction.build_capital_competition_framework`
- `marginal_capital_value.candidate_intent`
- `marginal_capital_value.accepted_increment`

Reason: the minimal repair could be completed by changing MCV priority formation
and PC priority consumption. Relationship and sizing logic did not require
changes.

## Priority Acceptance

BUY_PRIORITY_ORDER_PRESERVATION_RATE: 100% in focused GN priority fixtures

HISTORY_CAUSED_PRIORITY_INVERSION_COUNT: 0 in focused GN priority fixtures

CURRENT_POSITION_PRIORITY_INPUT_COUNT: 0

OLD_HISTORY_PRIORITY_INPUT_COUNT: 0

NEW_ADD_PARITY_PASS: YES

RELATIONSHIP_MATERIALIZED_AFTER_PRIORITY: YES

The new tests verify:

- rank-1 NEW beats rank-10 ADD even when ADD has stronger lifecycle quality;
- candidates with zero accepted increment still receive canonical BUY priority;
- same-rank, same-quality held and flat candidates are ordered without
  current-position priority preference;
- old EXIT, old campaign, prior ADD count, average cost, and realized PnL do not
  skip or demote BUY priority.

## Freeze / Isolation Matrix

SIZING_LOGIC_CHANGED: NO

CASH_SEMANTIC_CHANGED: NO

SELL_SEMANTIC_CHANGED: NO

PM_AUTHORITY_CHANGED: NO

WINNER_PROTECTION_CHANGED: NO

ADD_SAFETY_CHANGED: NO

ADD_SAFETY_BYPASS_COUNT: 0

G129_REGRESSION_COUNT: 0 in focused acceptance

REENTRY_SEMANTIC_CHANGED: NO_INTENTIONAL_CHANGE

NCU_COMPARATOR_INSTANCE_COUNT: 1

HIDDEN_RERANKING_FOUND: NO

SELL_BEHAVIOR_REGRESSION_COUNT: 0 in focused PM/SELL regression bundle

SIZING_REGRESSION_COUNT: 0 in focused PS regression bundle

CASH_REGRESSION_COUNT: 0 in focused cash regression bundle

## New Authority Audit

NEW_MODULE_COUNT: 0

NEW_COMPONENT_COUNT: 0

NEW_AUTHORITATIVE_ARTIFACT_COUNT: 0

NEW_SCHEMA_FAMILY_COUNT: 0

NEW_COMPARATOR_COUNT: 0

Fresh Target SHADOW remains non-authoritative. It was not connected as a
Production consumer and its equal-ish target weights, Cash row, `RELEASE`, and
`EXIT_CANDIDATE` semantics remain diagnostic only.

FRESH_TARGET_SHADOW_AUTHORITY_CHANGED: NO

PRODUCTION_BEHAVIOR_CHANGED_AS_INTENDED_ONLY_ON_BUY_PRIORITY: YES_FOR_FOCUSED_SCOPE

## Focused Tests

Focused GN/MCV priority tests:

```text
python3 -m pytest tests/strategy/test_phase31_g40_opportunity_quality_continuum.py -q
11 passed
```

Focused PC / MCV / lot / ADD regression:

```text
python3 -m pytest \
  tests/strategy/test_phase31_g40_opportunity_quality_continuum.py \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase31_g27_add_competitor_can_win_and_preserves_sizing_quantity_owner \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase29_e_common_rebatch_queue_allows_add_to_win_over_buy_new \
  tests/strategy/test_phase31_b10_alternative_c_marginal_capital_priority.py \
  tests/strategy/test_phase31_g61_lot_aware_allocation_to_sizing_compatibility.py \
  tests/strategy/test_phase31_g115_add_marginal_authoritative_binding.py \
  tests/strategy/test_phase31_g117_normal_buy_scope_repair.py -q
43 passed
```

Focused no-regression matrix:

```text
python3 -m pytest \
  tests/strategy/test_phase31_g40_opportunity_quality_continuum.py \
  tests/strategy/test_phase31_b10_alternative_c_marginal_capital_priority.py \
  tests/strategy/test_phase31_g61_lot_aware_allocation_to_sizing_compatibility.py \
  tests/strategy/test_phase31_g115_add_marginal_authoritative_binding.py \
  tests/strategy/test_phase31_g117_normal_buy_scope_repair.py \
  tests/strategy/test_phase22_j_position_sizing.py \
  tests/strategy/test_phase22_g_runtime_planning.py \
  tests/strategy/test_phase22_d_position_management.py \
  tests/strategy/test_phase31_f1f_pm_canonical_sell_semantic_integration.py \
  tests/strategy/test_phase32_ej_winner_position_size_adequacy_shadow.py \
  tests/strategy/test_phase32_ew_reentry_semantic_removal_recent_exit_guard.py \
  tests/strategy/test_phase31_g42_market_candidate_cash_interaction.py \
  tests/strategy/test_phase31_g44_add_reentry_lot_binding_integration.py \
  tests/strategy/test_phase31_g62_position_sizing_g61_binding.py -q
255 passed
```

Full strategy suite observation:

```text
python3 -m pytest tests/strategy -q
882 passed, 87 failed, 2 skipped
```

The full-suite failures are not accepted as Production promotion evidence in
this dirty worktree. They are concentrated in older actual-path/reentry/capital
deployment fixtures and should be triaged separately before any Production
promotion claim.

## Golden / Problem / Regression Coverage

GOLDEN_CASES_PASS: YES_IN_FOCUSED_ACCEPTANCE_BUNDLE

PROBLEM_CASES_PASS: YES_IN_FOCUSED_PRIORITY_FIXTURES

EXISTING_REGRESSION_PASS: YES_FOR_DEFINED_FOCUSED_MATRIX; NO_FOR_FULL_STRATEGY_SUITE

Covered directly by new GN tests:

- Current Opportunity order preservation
- accepted-increment independence
- held/flat relationship non-priority
- old EXIT history non-priority
- old campaign non-priority
- prior ADD count non-priority
- average cost / realized PnL non-priority

Covered by existing focused regression bundle:

- ADD can still win when it is the ranked/priority candidate
- BUY_NEW can still win when it is the ranked/priority candidate
- lot-aware allocation compatibility
- ADD marginal authority binding
- normal BUY scope
- Position Sizing
- Runtime Planning
- PM / SELL
- Winner shadow isolation
- recent EXIT guard / REENTRY focused behavior
- cash competitor interaction
- ADD reentry lot binding
- PS mapping

## SoT Updates

SOT_UPDATED: YES

Updated Architecture SoT files:

- `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/02_architecture/runtime_architecture_v2.md`

The permanent contract now states:

- BUY Investment Priority is Current PIT Opportunity authority.
- BUY_NEW / BUY_ADD relationship materializes after Investment Priority.
- Historical ownership/campaign state is not BUY attractiveness authority.
- Recent EXIT remains bounded churn eligibility.
- SELL authority remains PM-owned.
- Position Sizing remains quantity/lot authority.
- Fresh Target SHADOW remains non-authoritative.

## Required Answers

BUY_ONLY_HISTORY_NEUTRAL_PRIORITY_IMPLEMENTED: YES

EXACT_GM_BOUNDARY_RESPECTED: YES

BUY_PRIORITY_ORDER_PRESERVATION_RATE: 100_PERCENT_IN_FOCUSED_GN_PRIORITY_FIXTURES

HISTORY_CAUSED_PRIORITY_INVERSION_COUNT: 0_IN_FOCUSED_GN_PRIORITY_FIXTURES

CURRENT_POSITION_PRIORITY_INPUT_COUNT: 0

OLD_HISTORY_PRIORITY_INPUT_COUNT: 0

NEW_ADD_PARITY_PASS: YES

RELATIONSHIP_MATERIALIZED_AFTER_PRIORITY: YES

SIZING_LOGIC_CHANGED: NO

CASH_SEMANTIC_CHANGED: NO

SELL_SEMANTIC_CHANGED: NO

PM_AUTHORITY_CHANGED: NO

WINNER_PROTECTION_CHANGED: NO

ADD_SAFETY_CHANGED: NO

ADD_SAFETY_BYPASS_COUNT: 0

G129_REGRESSION_COUNT: 0_IN_FOCUSED_ACCEPTANCE

REENTRY_SEMANTIC_CHANGED: NO_INTENTIONAL_CHANGE

NCU_COMPARATOR_INSTANCE_COUNT: 1

HIDDEN_RERANKING_FOUND: NO

SELL_BEHAVIOR_REGRESSION_COUNT: 0_IN_FOCUSED_ACCEPTANCE

SIZING_REGRESSION_COUNT: 0_IN_FOCUSED_ACCEPTANCE

CASH_REGRESSION_COUNT: 0_IN_FOCUSED_ACCEPTANCE

NEW_MODULE_COUNT: 0

NEW_COMPONENT_COUNT: 0

NEW_AUTHORITATIVE_ARTIFACT_COUNT: 0

NEW_SCHEMA_FAMILY_COUNT: 0

NEW_COMPARATOR_COUNT: 0

GOLDEN_CASES_PASS: YES_IN_FOCUSED_ACCEPTANCE_BUNDLE

PROBLEM_CASES_PASS: YES_IN_FOCUSED_PRIORITY_FIXTURES

EXISTING_REGRESSION_PASS: YES_FOR_DEFINED_FOCUSED_MATRIX; NO_FOR_FULL_STRATEGY_SUITE

FRESH_TARGET_SHADOW_AUTHORITY_CHANGED: NO

PRODUCTION_BEHAVIOR_CHANGED_AS_INTENDED_ONLY_ON_BUY_PRIORITY: YES_FOR_FOCUSED_SCOPE

SOT_UPDATED: YES

FOCUSED_IMPLEMENTATION_ACCEPTED: YES

SHORT_DYNAMIC_VALIDATION_READY: CONDITIONAL_YES_AFTER_FULL_SUITE_BASELINE_TRIAGE

LONG_HORIZON_VALIDATION_READY: NO

DIRECT_PRODUCTION_PROMOTION_READY: NO

NEXT_STEP: triage the existing full-strategy-suite failures separately, then run a short actual-path dynamic validation focused on BUY priority order preservation, history-caused inversion count, SELL exact regression, sizing exact regression, cash exact regression, ADD safety, G129, REENTRY, PS mapping, and Runtime mapping

## Final Judgment

Yes: the minimal zero-new-authority repair was implemented for BUY Investment Priority only, making it Current PIT Opportunity based and materializing NEW/ADD relationship after priority while focused tests preserve SELL, Winner, Sizing, Cash, ADD Safety, G129, REENTRY, and Runtime boundaries; direct Production promotion remains blocked until full-suite baseline triage and short dynamic validation.
