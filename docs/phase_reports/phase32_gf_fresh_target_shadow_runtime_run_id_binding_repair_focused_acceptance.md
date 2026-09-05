# Phase32-GF — Fresh Target SHADOW Runtime Run-ID Binding Repair / Focused Acceptance

## Objective

Repair the Phase32-GE blocker:

```text
fresh_target_portfolio_shadow.v1.run_id_not_materialized
```

Scope is limited to non-authoritative Fresh Target SHADOW metadata/provenance
binding. Production Strategy, PM, PC target allocation, PS, Runtime Planning,
Pending, Submit, Execution, Safety, and broker semantics are unchanged.

## Current Source / Baseline Identity

- Source commit: `a8af2dacfb3c81015a069b40d53ff182cccb2542`
- Working tree: dirty with Phase32-GD/GE/GF report/test/source changes.
- Current source hashes after GF:
  - `src/ai_fund_lab_v2/strategy/marginal_capital_value.py`: `769e3d0267667b758d2416724c1cbd4bf445512b737afd0f4e57d908905d8986`
  - `src/ai_fund_lab_v2/strategy/portfolio_construction.py`: `8c33592cd63b149dbbbbd326ba6a24856f4b7fa26e45759967a7c65b51a2ccc4`
  - `src/ai_fund_lab_v2/strategy/shadow_runtime.py`: `b78208b9e985a3b9c4f9a65c8346887c079187d4b430a2ab34f2e45f2fc78f3c`

## Root Cause Confirmation

Phase32-GE correctly identified a Fresh Target SHADOW readiness blocker:
`fresh_target_portfolio_shadow.v1` was materialized with `run_id=""` and no
run/evidence-root binding contract. The canonical runtime path already had the
needed authority:

- `run_daily_operation` passes `--runtime-test-run-id` and
  `--runtime-test-evidence-root`.
- `generate_strategy_shadow_for_day(..., run_id=..., run_dir=...)` receives the
  canonical runtime-test run id and evidence root.
- Portfolio Construction did not propagate that runtime-test context into
  `build_fresh_target_portfolio_shadow`.

Direct cause: SHADOW metadata propagation gap at the
`shadow_runtime -> portfolio_construction -> marginal_capital_value` boundary.

## Canonical Authority Selected

Canonical runtime run-id authority is the existing runtime-test context passed
to `generate_strategy_shadow_for_day`, specifically:

- `run_id`
- `profile_id`
- `run_dir` / runtime-test evidence root
- `business_date`
- `feature_date`

GF does not infer run identity from latest-run filesystem discovery and does
not create a new authority source.

## Repair Performed

Files changed:

- `src/ai_fund_lab_v2/strategy/shadow_runtime.py`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `src/ai_fund_lab_v2/strategy/marginal_capital_value.py`
- `tests/strategy/test_phase32_gf_fresh_target_run_id_binding.py`
- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/02_architecture/strategy_intelligence_architecture_v1.md`
- `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`

Implementation summary:

- `generate_strategy_shadow_for_day` now passes the existing runtime-test
  context to Portfolio Construction.
- Portfolio Construction forwards `runtime_test_context` to the Fresh Target
  SHADOW builder only.
- `fresh_target_portfolio_shadow.v1` now materializes:
  - `run_id`
  - `runtime_test_run_id`
  - `run_evidence_root`
  - `run_evidence_root_binding`
- Runtime-path missing `run_id`, missing evidence root, evidence-root mismatch,
  or explicit cross-run source evidence makes the Fresh Target SHADOW
  `pit_status=FAIL_CLOSED`.
- The artifact remains non-authoritative:
  - `authoritative_consumer_count=0`
  - `action_authority=false`
  - `quantity_authority=false`
  - `order_authority=false`
  - all Production consumer flags remain false.

## Why This Is Canonical

This repair reuses the existing runtime-test run identity already supplied by
the Runtime CLI. It is not a bypass because:

- missing runtime run id fails closed in the SHADOW artifact;
- explicit stale/cross-run evidence is rejected;
- plan expectation is not accepted as authority;
- no registry, accepted generation, Pending, Ledger, Runtime state, or broker
  state is edited;
- Production consumers remain disconnected.

## Existing Active Run Assessment

READ-ONLY inspection of
`runtime-test-historical-extended-smoke-20260904T112908488385Z` found existing
Fresh Target artifacts generated before GF with:

```text
run_id = ""
run_evidence_root_binding = missing
pit_status = PASS
```

Those old artifacts were not mutated. They are insufficient for GE/GF dynamic
acceptance under the repaired contract. A new post-GF fresh validation run is
required for dynamic Fresh Target acceptance.

## Focused Validation

Passed:

```text
PYTHONPYCACHEPREFIX=/private/tmp/pycache-gf PYTHONPATH=src python3 -m py_compile \
  src/ai_fund_lab_v2/strategy/marginal_capital_value.py \
  src/ai_fund_lab_v2/strategy/portfolio_construction.py \
  src/ai_fund_lab_v2/strategy/shadow_runtime.py \
  tests/strategy/test_phase32_gf_fresh_target_run_id_binding.py
```

Passed:

```text
PYTHONPYCACHEPREFIX=/private/tmp/pycache-gf PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase32_gd_fresh_target_portfolio_shadow.py \
  tests/strategy/test_phase32_gf_fresh_target_run_id_binding.py
```

Result: `12 passed`

Passed:

```text
PYTHONPYCACHEPREFIX=/private/tmp/pycache-gf PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase32_dq_unified_marginal_capital_shadow.py \
  tests/strategy/test_phase32_ew_reentry_semantic_removal_recent_exit_guard.py \
  tests/runtime_v2/test_phase32_ez_recent_exit_guard_materialization.py
```

Result: `23 passed`

Passed:

```text
PYTHONPYCACHEPREFIX=/private/tmp/pycache-gf PYTHONPATH=src python3 -m pytest -q \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py::test_phase31_g129_buy_add_submit_uses_order_increment_not_position_scope_delta \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py::test_phase31_g129_buy_add_true_order_increment_mismatch_still_reviews
```

Result: `2 passed`

Passed:

```text
PYTHONPYCACHEPREFIX=/private/tmp/pycache-gf PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase32_eg_security_opportunity_evidence.py \
  tests/strategy/test_phase32_eh_pc_security_opportunity_shadow_consumer.py \
  tests/strategy/test_phase32_ej_winner_position_size_adequacy_shadow.py
```

Result: `9 passed`

Not run:

- fresh-run
- resume
- replay
- recover
- long Historical

## Required Answers

- `CANONICAL_RUNTIME_RUN_ID_AUTHORITY_IDENTIFIED`: YES
- `EXISTING_RUN_ID_PROPAGATION_PATTERN_REUSED`: YES
- `FRESH_TARGET_RUN_ID_BOUND`: YES
- `FRESH_TARGET_RUN_ID_NON_EMPTY_RUNTIME_PATH`: YES by focused runtime-context propagation test; dynamic actual-run acceptance still requires a post-GF fresh run.
- `RUN_EVIDENCE_ROOT_BINDING_VALID`: YES in focused same-run fixture.
- `SAME_RUN_ACCEPTANCE_PASS`: YES
- `CROSS_RUN_REJECTION_PASS`: YES
- `MISSING_RUN_ID_FAIL_CLOSED_PASS`: YES
- `AUTHORITATIVE_CONSUMER_COUNT`: 0
- `PRODUCTION_BEHAVIOR_CHANGED`: NO
- `FRESH_TARGET_LOGIC_CHANGED`: NO, metadata/provenance binding only.
- `ADD_SAFETY_BYPASS_COUNT`: 0
- `G129_REGRESSION_COUNT`: 0
- `RUNTIME_AUTHORITY_LEAK_COUNT`: 0
- `STALE_CROSS_RUN_EVIDENCE_ACCEPTED_COUNT`: 0
- `EXISTING_ACTIVE_RUN_RESUME_SAFE`: NO for Fresh Target dynamic acceptance; existing artifacts are pre-GF and remain unmodified.
- `NEW_POST_GF_FRESH_RUN_REQUIRED`: YES for GE/GF dynamic validation.
- `DYNAMIC_SHADOW_VALIDATION_READY`: YES after source repair and focused validation.
- `USER_EXECUTION_COMMAND`:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-extended-smoke \
  --start-date 2023-06-01 \
  --business-days 20 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

- `CORRECTNESS_DEFECT_FOUND`: YES, SHADOW runtime run-id materialization gap.
- `SHADOW_REPAIR_ACCEPTED`: YES
- `DIRECT_PRODUCTION_PROMOTION_READY`: NO
- `NEXT_STEP`: User should run the post-GF short fresh validation above, then audit Fresh Target dynamic artifacts for non-empty run binding and zero Production consumers.

## Mutation Confirmation

- `TARGET_RUN_MUTATED`: NO
- `RUNTIME_STATE_MUTATED`: NO
- `PENDING_MUTATED`: NO
- `LEDGER_MUTATED`: NO
- `ACCEPTED_REGISTRY_MUTATED`: NO
- `FRESH_RUN_EXECUTED_BY_CODEX`: NO
- `RESUME_EXECUTED_BY_CODEX`: NO
- `REPLAY_EXECUTED_BY_CODEX`: NO
- `RECOVER_EXECUTED_BY_CODEX`: NO

## Final Judgment

`PHASE32_GF_FRESH_TARGET_SHADOW_RUNTIME_RUN_ID_BINDING_REPAIRED_FOCUSED_ACCEPTED_DYNAMIC_VALIDATION_READY`
