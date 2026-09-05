# Phase32-GH — Final Lot-Aware Fresh Target Run-ID Context Propagation Repair / Focused Acceptance

## Scope

- Target blocker: Phase32-GG final lot-aware Fresh Target run-id binding gap.
- Source run used for diagnosis: `runtime-test-historical-extended-smoke-20260904T134735954368Z`.
- Execution restrictions honored: no fresh-run, resume, replay, recover, long Historical, runtime state mutation, Pending mutation, Ledger mutation, accepted-generation mutation, or Production Strategy change.

## Root Boundary Confirmed

`ROOT_BOUNDARY_CONFIRMED = YES`

Phase32-GG showed that `portfolio_construction_draft.json` and `pre_lot_capital_competition` carried the GF runtime-test binding, while final `portfolio_construction.json` lost it inside:

```text
_produce_lot_aware_final_portfolio_construction()
  -> apply_lot_aware_final_reallocation()
  -> build_capital_competition_framework()
```

The first bad boundary was the final lot-aware rebuild. The draft/pre-lot path received `runtime_test_context`, but the finalizer did not pass the same context into `apply_lot_aware_final_reallocation`, and the internal final `build_capital_competition_framework` call therefore rebuilt Fresh Target SHADOW with empty `run_id` / `run_evidence_root`.

## Repair

`RUNTIME_TEST_CONTEXT_PROPAGATED_TO_LOT_AWARE_FINAL = YES`

Files changed:

- `src/ai_fund_lab_v2/strategy/shadow_runtime.py`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `tests/strategy/test_phase32_gh_lot_aware_fresh_target_run_id_propagation.py`
- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/02_architecture/strategy_intelligence_architecture_v1.md`
- `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`

Implementation details:

- `generate_strategy_shadow_for_day` now passes the same runtime-test context to the draft PC producer and final lot-aware PC finalizer.
- `_produce_lot_aware_final_portfolio_construction` now accepts `runtime_test_context` and forwards it to `apply_lot_aware_final_reallocation`.
- If invoked without explicit context, the finalizer recovers only the already-materialized draft Fresh Target binding. It does not infer the latest run from the filesystem.
- `apply_lot_aware_final_reallocation` now accepts `runtime_test_context` and passes it to both internal `build_capital_competition_framework` rebuilds.
- Missing context still produces a SHADOW fail-closed run-id binding result instead of a silent empty binding.

## Why This Is Canonical

This repair preserves the GF authority model: runtime-test binding comes from the current runtime-test context or from already-materialized draft evidence. It does not patch hashes, bypass validation, accept plan expectation as authority, discover latest runs, or promote Fresh Target SHADOW to Production.

Fresh Target remains non-authoritative:

```text
AUTHORITATIVE_CONSUMER_COUNT = 0
SHADOW_AUTHORITY_LEAK_COUNT = 0
action_authority = false
quantity_authority = false
order_authority = false
production_consumer_connected = false
```

## Focused Validation

Commands run:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/pycache-gh PYTHONPATH=src python3 -m py_compile \
  src/ai_fund_lab_v2/strategy/shadow_runtime.py \
  src/ai_fund_lab_v2/strategy/portfolio_construction.py \
  tests/strategy/test_phase32_gh_lot_aware_fresh_target_run_id_propagation.py
```

Result: PASS.

```bash
PYTHONPYCACHEPREFIX=/private/tmp/pycache-gh PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase32_gf_fresh_target_run_id_binding.py \
  tests/strategy/test_phase32_gh_lot_aware_fresh_target_run_id_propagation.py \
  tests/strategy/test_phase32_gd_fresh_target_portfolio_shadow.py
```

Result: `17 passed`.

```bash
PYTHONPYCACHEPREFIX=/private/tmp/pycache-gh PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase32_dq_unified_marginal_capital_shadow.py \
  tests/strategy/test_phase32_ew_reentry_semantic_removal_recent_exit_guard.py \
  tests/runtime_v2/test_phase32_ez_recent_exit_guard_materialization.py
```

Result: `23 passed`.

```bash
PYTHONPYCACHEPREFIX=/private/tmp/pycache-gh PYTHONPATH=src python3 -m pytest -q \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py::test_phase31_g129_buy_add_submit_uses_order_increment_not_position_scope_delta \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py::test_phase31_g129_buy_add_true_order_increment_mismatch_still_reviews
```

Result: `2 passed`.

```bash
PYTHONPYCACHEPREFIX=/private/tmp/pycache-gh PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase32_eg_security_opportunity_evidence.py \
  tests/strategy/test_phase32_eh_pc_security_opportunity_shadow_consumer.py \
  tests/strategy/test_phase32_ej_winner_position_size_adequacy_shadow.py
```

Result: `9 passed`.

## Acceptance Matrix

- `PRE_LOT_RUN_ID_BINDING_PASS = YES`
- `LOT_FINAL_RUN_ID_BINDING_PASS = YES` in focused non-mutating tests.
- `FINAL_TOP_LEVEL_RUN_ID_BINDING_PASS = YES` in focused non-mutating tests.
- `SAME_RUN_ACCEPTANCE_PASS = UNCONFIRMED_ON_DYNAMIC_ACTUAL_ARTIFACTS`
- `CROSS_RUN_REJECTION_PASS = YES`
- `MISSING_CONTEXT_FAIL_CLOSED_PASS = YES`
- `FRESH_TARGET_LOGIC_CHANGED = NO`
- `PRODUCTION_BEHAVIOR_CHANGED = NO`
- `AUTHORITATIVE_CONSUMER_COUNT = 0`
- `SHADOW_AUTHORITY_LEAK_COUNT = 0`
- `OLD_OWNERSHIP_HISTORY_INPUT_USED = NO`
- `OLD_CLOSED_CAMPAIGN_HISTORY_INPUT_USED = NO`
- `PRIOR_ADD_COUNT_INPUT_USED = NO`
- `PRIOR_EXIT_COUNT_INPUT_USED = NO`
- `AVERAGE_COST_INPUT_USED = NO`
- `REALIZED_PNL_INPUT_USED = NO`
- `CAMPAIGN_PNL_INPUT_USED = NO`
- `FUTURE_RETURN_INPUT_USED = NO`
- `ADD_SAFETY_BYPASS_COUNT = 0`
- `G129_REGRESSION_COUNT = 0`
- `WINNER_CONFLICT_OBSERVABILITY_PRESERVED = YES`
- `NEW_POST_GH_FRESH_RUN_REQUIRED = YES`
- `DYNAMIC_SHADOW_VALIDATION_READY = YES`
- `CORRECTNESS_DEFECT_FOUND = YES`
- `REPAIR_ACCEPTED = YES_FOR_FOCUSED_ACCEPTANCE`
- `DIRECT_PRODUCTION_PROMOTION_READY = NO`

`SAME_RUN_ACCEPTANCE_PASS` is not claimed for the existing GG run because GH did not mutate existing runtime artifacts. A post-GH fresh validation run is required to confirm the dynamic actual-path final artifact.

## Next Step

User-operated dynamic validation command:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-extended-smoke \
  --start-date 2023-06-01 \
  --business-days 20 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

After that run completes, inspect the final `portfolio_construction.json` artifacts and confirm:

- draft/pre-lot Fresh Target run binding PASS
- final lot-aware Fresh Target run binding PASS
- top-level final capital competition Fresh Target run binding PASS
- `authoritative_consumer_count=0`
- no Production behavior change

## Final Judgment

`PHASE32_GH_FINAL_LOT_AWARE_FRESH_TARGET_RUN_ID_CONTEXT_PROPAGATION_REPAIRED_FOCUSED_ACCEPTED_DYNAMIC_VALIDATION_READY`
