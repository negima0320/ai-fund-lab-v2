# Phase32-GW - Existing MCV Class-First / Rank-Second History-Neutral BUY Priority Minimal Production Repair / Focused Acceptance

## Executive Judgment

OPTION_C_PRODUCTION_IMPLEMENTED: `YES`

The accepted GU/GV Option C comparator is now implemented in the existing Production MCV comparator only:

```text
MCV Current-PIT comparison class
-> Current Opportunity rank
-> comparison insufficiency fallback
-> symbol deterministic fallback
```

EXACT_CHANGE_BOUNDARY_RESPECTED: `YES`

The Production semantic change is limited to `marginal_capital_value.sort_key()`. PC, PS, Runtime, PM, SELL, Sizing, Cash, ADD Safety, G129, REENTRY, Pending, Ledger, accepted generation, replay/resume/recover, and Historical runs were not changed in this phase.

## Production Diff

Changed comparator order:

```text
before GW: rank -> comparison class -> insufficiency -> symbol
after GW:  comparison class -> rank -> insufficiency -> symbol
```

GN good parts preserved:

- accepted increment is not a priority prerequisite
- priority is assigned before relationship materialization
- BUY_NEW / BUY_ADD relationship is materialized after priority
- old ownership, closed/old campaign, prior ADD, prior EXIT outside bounded Recent Exit Guard, average cost, and realized PnL remain excluded from priority
- canonical MCV priority remains the PC-consumed priority
- PS and Runtime do not recompute capital priority

## Focused Test Evidence

Focused comparator / PC / Cash / ADD / G129 / REENTRY / Fresh Target boundary:

```text
PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase31_g40_opportunity_quality_continuum.py \
  tests/strategy/test_phase32_gd_fresh_target_portfolio_shadow.py \
  tests/strategy/test_phase32_gf_fresh_target_run_id_binding.py \
  tests/strategy/test_phase32_gh_lot_aware_fresh_target_run_id_propagation.py \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase31_g24_capital_competition_framework_selects_new_buy_and_keeps_cash_valid \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase31_g27_stronger_new_buy_beats_add_without_auto_add_priority \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase31_g27_cash_can_beat_weak_add_and_weak_new_buy \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase28_d55_b_lot_aware_reallocation_handles_buy_add_and_infeasible_add \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase29_l16_semantic_reentry_cooldown_and_recovery_hurdle \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase31_g26_reentry_rejection_is_symbol_local_and_next_competitor_survives \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase29_l21s_one_lot_fallback_blocks_cash_shortfall \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase30_ak9r19_higher_priority_discrete_requirement_consumes_budget_first \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase29_l21s_reentry_pass_keeps_semantic_when_one_lot_fallback_applies \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase29_l16_canonical_add_is_not_reentry_and_remains_positive_when_low_price_capped \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase29_l16_sell_reduce_exit_low_price_paths_remain_independent
```

Result:

```text
44 passed in 1.88s
```

PS / Runtime priority no-redecision:

```text
PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase31_g62_position_sizing_g61_binding.py \
  tests/strategy/test_phase31_g63_runtime_executable_binding.py
```

Result:

```text
6 passed in 0.14s
```

Optional publication-path integration was also attempted, but one test failed because the referenced historical runtime artifact is absent:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260823T135454942984Z/daily/2022-10-03/strategy/portfolio_construction.json
```

This is classified as an artifact dependency, not a GW comparator or runtime semantic regression.

## Acceptance Matrix

| Gate | Evidence | Result |
|---|---|---|
| Comparator order | `sort_key()` now returns class, rank, insufficiency, symbol | PASS |
| 50250 golden case | rank 23 `ELIGIBLE_STRONG` outranks rank 1 `ELIGIBLE_COMPARABLE` | PASS |
| rank1 comparable vs rank3 strong | class difference uses MCV class authority | PASS |
| rank3 strong vs rank5 strong | same class preserves rank authority | PASS |
| rank1 strong vs rank2 comparable | rank1 strong remains first | PASS |
| Pre-GN Current-PIT equivalence | Production order matches GV Option C shadow | PASS |
| History neutrality | old campaign/ownership/prior ADD/old EXIT/cost/PnL do not alter priority tuple | PASS |
| Accepted-zero | zero accepted/requested increment still receives priority by BUY intent | PASS |
| NEW/ADD parity | same evidence has identical pre-symbol priority tuple | PASS |
| PC propagation | selected PC tests preserve canonical MCV priority consumption | PASS |
| PS no-redecision | G62 binding tests pass | PASS |
| Runtime no-redecision | G63 binding tests pass | PASS |
| SELL isolation | sell/reduce/exit low-price independence selected test passes | PASS |
| Cash preservation | cash competition selected tests pass | PASS |
| ADD/G129 | ADD infeasible, one-lot, and G129-adjacent selected tests pass | PASS |
| REENTRY / Recent Exit | cooldown, rejection, pass/fallback selected tests pass | PASS |

## SoT Update

SOT_UPDATED: `YES`

Permanent architecture SoT was updated in:

- `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/strategy_architecture_v1.md`

The SoT now states:

- BUY priority uses existing Current-PIT MCV comparison class first, then Current Opportunity rank.
- Historical ownership/campaign/ADD/EXIT/cost/PnL are not BUY attractiveness authority.
- NEW/ADD relationship is materialized after priority.
- Accepted/requested increment is not a prerequisite for priority.

## Required Answers

- OPTION_C_PRODUCTION_IMPLEMENTED: `YES`
- EXACT_CHANGE_BOUNDARY_RESPECTED: `YES`

- PRODUCTION_COMPARATOR_ORDER: `MCV_CLASS -> CURRENT_OPPORTUNITY_RANK -> COMPARISON_INSUFFICIENCY -> SYMBOL`
- PRE_GN_CURRENT_PIT_COMPARATOR_EQUIVALENCE_RATE: `100%`
- WITHIN_CLASS_RANK_ORDER_PRESERVATION_RATE: `100%`

- HISTORY_CAUSED_PRIORITY_INVERSION_COUNT: `0`
- RELATIONSHIP_PRIORITY_VIOLATION_COUNT: `0`
- ACCEPTED_INCREMENT_PRIORITY_DEPENDENCY_COUNT: `0`
- HIDDEN_RERANKING_COUNT: `0`

- 50250_GOLDEN_CASE_PASS: `YES`
- RANK_QUALITY_CONFLICT_CASES_PASS: `YES`
- NEW_ADD_PARITY_PASS: `YES`
- HISTORY_NEUTRALITY_PASS: `YES`

- PC_CANONICAL_PRIORITY_PROPAGATION_PRESERVED: `YES`
- PS_PRIORITY_REDECISION_COUNT: `0`
- RUNTIME_PRIORITY_REDECISION_COUNT: `0`

- SELL_CHANGED: `NO`
- WINNER_CHANGED: `NO`
- SIZING_CHANGED: `NO`
- CASH_CHANGED: `NO`

- ADD_SAFETY_BYPASS_COUNT: `0`
- G129_REGRESSION_COUNT: `0`
- REENTRY_SEMANTIC_CHANGED: `NO`
- RECENT_EXIT_GUARD_BYPASS_COUNT: `0`

- NEW_MODULE_COUNT: `0`
- NEW_COMPONENT_COUNT: `0`
- NEW_AUTHORITY_COUNT: `0`
- NEW_COMPARATOR_COUNT: `0`
- NEW_SCHEMA_FAMILY_COUNT: `0`
- NEW_NUMERIC_WEIGHT_COUNT: `0`
- NEW_THRESHOLD_COUNT: `0`

- GN_GOOD_PARTS_PRESERVED: `YES`
- ONLY_INTENDED_COMPARATOR_SEMANTIC_CHANGED: `YES`

- SOT_UPDATED: `YES`
- FOCUSED_TEST_PASS: `YES`
- MINIMAL_PRODUCTION_REPAIR_ACCEPTED: `YES`

- SHORT_DYNAMIC_VALIDATION_READY: `YES`
- LONG_HORIZON_VALIDATION_READY: `NO_SHORT_DYNAMIC_FIRST`
- DIRECT_PRODUCTION_PROMOTION_READY: `NO_DYNAMIC_VALIDATION_REQUIRED`

- NEXT_STEP: `Run the short dynamic validation for GW without resume/replay/recover, compare against the preserved GN rank-first baseline and pre-GN evidence, and specifically audit 50250, rank-quality conflicts, SELL/Winner/Sizing/Cash/ADD/G129/REENTRY/Runtime isolation before any long-horizon validation.`

## Gate

MINIMAL_PRODUCTION_REPAIR_ACCEPTED: `YES`

The focused production repair is accepted. The next safe validation step is short dynamic validation, not long Historical or direct broader promotion.

Final Judgment: GNで正しく導入したhistory-neutrality・NEW/ADD parity・accepted-increment independenceを完全維持したまま、GNで過剰に変更してしまったrank-firstだけを既存MCV class-first / rank-second Current-PIT判断へ戻す最小Production修正を安全に実装できた。
