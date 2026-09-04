# Phase32-EW — REENTRY Current-Decision Semantic Removal / Bounded Recent-Exit Guard Implementation

## Scope

Implementation phase based on Phase32-EU and Phase32-EV.

Codex did not execute fresh-run, resume, replay, recover, or long Historical. Existing artifacts and runtime state were not rewritten.

No future price, future return, MFE/MAE, later outcome, Historical PnL, or final campaign outcome was used for Production threshold/weight/rank/parameter selection.

## Root Contract Implemented

The old Production path:

```text
old EXIT -> REENTRY -> stricter recovery/eligibility branch -> target suppression
```

was replaced with:

```text
ordinary current BUY_NEW
+ retained audit lineage
+ bounded recent-exit churn guard
```

The new invariant is:

```text
PRIOR OWNERSHIP IS AUDIT LINEAGE, NOT PERMANENT CURRENT BUY AUTHORITY
RECENT EXIT CHURN PROTECTION MUST BE BOUNDED
AUDITABILITY DOES NOT REQUIRE DAILY FULL-HISTORY MATERIALIZATION
```

## Implementation Summary

### Portfolio Construction

`src/ai_fund_lab_v2/strategy/portfolio_construction.py`

- `_semantic_reentry_evidence` now returns `semantic_buy_type=BUY_NEW` for flat symbols, including symbols with prior EXIT lineage.
- A new `recent_exit_guard_state` / `recent_exit_guard_status` annotation distinguishes:
  - `NOT_APPLICABLE`
  - `ACTIVE_RECENT_EXIT_GUARD`
  - `MALFORMED_RECENT_EXIT_GUARD`
  - `EXPIRED_NOT_CURRENT_DECISION_AUTHORITY`
- Active recent-exit guard can block/review only inside the bounded guard scope.
- Sufficiently old prior EXIT lineage no longer calls the permanent REENTRY recovery/eligibility branch.
- Old unknown/generic prior context no longer creates indefinite REVIEW_REQUIRED after guard irrelevance.
- Active guard bypass protection was moved from `semantic_buy_type=REENTRY` to `recent_exit_guard_state`.

### Current Decision Prior-Exit Supply

`src/ai_fund_lab_v2/strategy/shadow_runtime.py`

- `_supply_prior_exit_state` no longer reads full `persistent_ledger/executions.jsonl` for current BUY REENTRY classification.
- It no longer scans strict-prior PM EXIT artifacts for current BUY REENTRY classification.
- It looks only for an explicit bounded recent-exit guard source, if present, and attaches minimal guard lineage.
- Offline/audit reconstruction functions remain available; they are no longer part of current BUY prior-exit hot path.

### MCV / Shadow Compatibility

`src/ai_fund_lab_v2/strategy/marginal_capital_value.py`

- Old prior-exit candidates are now ordinary `BUY_NEW_NEXT_LOT`, not independent `REENTRY_NEXT_LOT`.
- MCV completeness no longer requires `REENTRY_ELIGIBLE`.
- Active malformed/unreleased recent-exit guard remains incomplete / non-executable.
- Prior-exit lineage can still be visible as observability for BUY_NEW rows.

### Runtime Position Sizing Authority

`src/ai_fund_lab_v2/runtime_v2/position_sizing_authority.py`

- Active or malformed recent-exit guard status is treated as an explicit hard blocker for executable authority.
- Existing legacy `REENTRY` hard-blocker compatibility remains for old artifacts.

## Architecture / SoT Update

Updated:

- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/02_architecture/strategy_intelligence_architecture_v1.md`

The SoT now records:

- prior ownership is audit lineage, not permanent current BUY authority;
- recent-exit churn protection must be bounded;
- auditability does not require daily full-history materialization;
- old prior ownership receives no capital bonus or discount;
- BUY_ADD / G129 current open-campaign semantics are unchanged.

## Files Changed

EW-specific changed files:

- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `src/ai_fund_lab_v2/strategy/shadow_runtime.py`
- `src/ai_fund_lab_v2/strategy/marginal_capital_value.py`
- `src/ai_fund_lab_v2/runtime_v2/position_sizing_authority.py`
- `tests/strategy/test_phase32_ew_reentry_semantic_removal_recent_exit_guard.py`
- `tests/strategy/test_phase22_e_portfolio_construction.py`
- `tests/strategy/test_phase32_dq_unified_marginal_capital_shadow.py`
- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/02_architecture/strategy_intelligence_architecture_v1.md`

Note: the worktree already contained earlier Phase32 modified/untracked files before EW; EW did not reset or revert them.

## Focused Validation

Passed:

```text
PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase32_ew_reentry_semantic_removal_recent_exit_guard.py

8 passed
```

Passed:

```text
PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase32_ew_reentry_semantic_removal_recent_exit_guard.py \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase29_l16_semantic_reentry_cooldown_and_recovery_hurdle \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase31_g26_first_time_buy_new_has_non_reentry_semantic_contract \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase29_l21r3_reentry_capacity_authority_resolves_normal_excessive_and_missing_cases \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase31_g26_reentry_rejection_is_symbol_local_and_next_competitor_survives \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase29_l21r3_prior_exit_persists_when_buy_quality_temporarily_excludes_candidate \
  tests/strategy/test_phase31_g44_add_reentry_lot_binding_integration.py \
  tests/strategy/test_phase31_g46_refined_capital_competition_integrated_acceptance.py

25 passed
```

Passed:

```text
PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase32_dq_unified_marginal_capital_shadow.py \
  tests/strategy/test_phase32_eg_security_opportunity_evidence.py \
  tests/strategy/test_phase32_eh_pc_security_opportunity_shadow_consumer.py \
  tests/strategy/test_phase32_ej_winner_position_size_adequacy_shadow.py

20 passed
```

Passed:

```text
PYTHONPATH=src python3 -m pytest -q \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py::test_phase31_g129_buy_add_submit_uses_order_increment_not_position_scope_delta \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py::test_phase31_g129_buy_add_true_order_increment_mismatch_still_reviews \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase29_l21s_buy_add_one_lot_fallback_preserves_add_semantics \
  tests/strategy/test_phase22_j_position_sizing.py::test_phase28_d55_b_ps_final_sizing_consumes_lot_aware_pc_target_for_buy_add \
  tests/strategy/test_phase30_s_position_sizing_production_handoff.py::test_phase30_ae1_pm_pc_ps_runtime_canonical_campaign_buy_add_e2e

5 passed
```

Passed after redirecting pycache to `/private/tmp`:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache PYTHONPATH=src python3 -m py_compile \
  src/ai_fund_lab_v2/strategy/portfolio_construction.py \
  src/ai_fund_lab_v2/strategy/shadow_runtime.py \
  src/ai_fund_lab_v2/strategy/marginal_capital_value.py \
  src/ai_fund_lab_v2/runtime_v2/position_sizing_authority.py \
  tests/strategy/test_phase32_ew_reentry_semantic_removal_recent_exit_guard.py
```

Non-acceptance note:

- One broader CK command reported `9` failures because it attempted to read a historical fixture run directory that is absent from the current workspace.
- The same command's non-fixture tests passed (`17` passed). This was an evidence availability issue, not an EW logic failure.

## Validation Coverage Mapping

| Requirement | Validation |
|---|---|
| never-held + valid PIT -> ordinary BUY | `test_matched_never_held_and_old_exit_use_equivalent_current_buy_semantics` |
| recent EXIT + unresolved weakness blocks/reviews | `test_recent_exit_unresolved_weakness_remains_guard_blocked` |
| recent EXIT + PIT requalification releases | `test_recent_exit_current_pit_requalification_releases_guard` |
| sufficiently old EXIT does not suppress | `test_old_prior_exit_is_ordinary_buy_new_audit_lineage_only` |
| old unknown context does not block forever | `test_old_unknown_prior_exit_context_does_not_create_long_lived_review` |
| old hard-stop not permanent authority | same old prior EXIT test with hard-stop reason |
| never-held vs old-exit equivalent | matched equivalence test |
| active guard cannot bypass rebatch | `test_active_recent_exit_guard_cannot_rebatch_as_executable_buy_new` |
| BUY_ADD unchanged | EW BUY_ADD test and G129 focused tests |
| whole-run prior-exit scan removed | `test_current_buy_prior_exit_supply_does_not_scan_whole_run_history` |
| MCV no longer requires `REENTRY_ELIGIBLE` | DQ/EG/EH/EJ shadow tests |
| Runtime executable guard preserved | position sizing authority hard-blocker and G129 submit tests |

## Required Answers

- `REENTRY_CURRENT_DECISION_SEMANTIC_REMOVED = YES`
- `RECENT_EXIT_GUARD_IMPLEMENTED = YES`
- `RECENT_EXIT_GUARD_BOUNDED = YES`
- `OLD_EXIT_CURRENT_DECISION_AUTHORITY_REMOVED = YES`
- `UNKNOWN_OLD_CONTEXT_LONG_LIVED_BLOCK_REMOVED = YES`
- `NEVER_HELD_OLD_EXIT_EQUIVALENCE_PROVEN = YES`
- `WHOLE_RUN_REENTRY_SCAN_REMOVED_FROM_CURRENT_DECISION_HOT_PATH = YES`
- `FULL_PRIOR_PM_EVIDENCE_REMOVED_FROM_DAILY_DECISION_PAYLOAD = PARTIAL`
- `BUY_ADD_CAMPAIGN_LOCAL_SEMANTICS_PRESERVED = YES`
- `RUNTIME_IDEMPOTENCY_CONTRACT_PRESERVED = YES`
- `ARCHITECTURE_SOT_UPDATED = YES`
- `FOCUSED_REGRESSION_PASS = YES`
- `FRESH_RUN_REQUIRED = YES`
- `READY_FOR_USER_FRESH_VALIDATION = YES`

## Exact Next User Action

Run a new user-operated Historical fresh validation. Codex did not run it.

Suggested command shape:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-extended-smoke \
  --start-date 2022-10-03 \
  --business-days 650 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

## Final Judgment

`PHASE32_EW_REENTRY_CURRENT_DECISION_SEMANTIC_REMOVED_BOUNDED_RECENT_EXIT_GUARD_IMPLEMENTED_READY_FOR_USER_FRESH_VALIDATION`
