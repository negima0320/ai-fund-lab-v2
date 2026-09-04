# Phase32-DY - DW SHADOW Builder Failure Isolation / Morning Continuation Production Repair

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260902T060955933565Z`
- Target halt: `2023-12-11:morning`, exit code `10`
- Root-cause reference: `docs/phase_reports/phase32_dx_20231211_morning_halt_post_dw_root_cause_read_only_audit.md`
- Repair scope: isolate non-authoritative DQ/DW unified marginal-capital SHADOW builder failure from canonical Production portfolio construction.
- Runtime state mutation: none
- Target run mutation: none
- Resume/recover/replay/fresh-run/long Historical: not executed

## Root Cause Confirmation

DX found the first canonical failure at:

`reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260902T060955933565Z/daily/2023-12-11/strategy/portfolio_construction_draft.json`

The artifact was an error artifact:

- `schema_version`: `portfolio_construction_draft_shadow_error.v1`
- `producer_result_status`: `BLOCK`
- `reason_codes`: `["strategy_shadow_generation_error"]`
- `error`: `name '_two_stage_divergence_class' is not defined`

That caused:

`portfolio_construction_draft` error -> incompatible `portfolio_construction` error artifact -> `position_sizing` block -> `runtime_planning` block -> `strategy_runtime_planning_blocked` -> morning exit code `10`.

Runtime Test Command Guide maps exit code `10` to `REVIEW_REQUIRED`.

## Repair Performed

Changed:

- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `tests/strategy/test_phase32_dq_unified_marginal_capital_shadow.py`

No Strategy parameter, threshold, weight, rank, PM, BQ, BUY_NEW, REENTRY, BUY_ADD, cash allocation, position sizing, Pending, submit, execution, or broker behavior was changed.

## Canonical Repair Boundary

The narrow repair is inside `build_capital_competition_framework()`.

Before DY, `portfolio_construction.py` directly called:

`marginal_capital_value.build_unified_marginal_capital_shadow(...)`

Any exception in that non-authoritative shadow builder escaped and replaced otherwise valid PC output with `*_shadow_error.v1`, which then propagated to formal Runtime planning.

DY now routes that call through:

`_build_non_authoritative_unified_marginal_capital_shadow(...)`

If the shadow builder succeeds, the normal DW v2 SHADOW artifact is embedded unchanged.

If the shadow builder raises, the PC artifact still materializes canonical Production capital-competition output and embeds a diagnostic SHADOW error object only under `unified_marginal_capital_shadow`.

## SHADOW Diagnostic Contract

The diagnostic object includes:

- `schema_version`: `unified_marginal_capital_shadow_error.v1`
- `shadow_schema`: current DW SHADOW schema
- `component`: `unified_marginal_capital_shadow`
- `status`: `SHADOW_ERROR`
- `producer_result_status`: `SHADOW_ERROR`
- `business_date`
- `exception_type`
- `exception_message`
- `source_version`
- `source_path`
- `source_hash`
- `authoritative_consumer_count`: `0`
- `shadow_only`: `true`
- `production_allocation_consumer`: `false`
- `production_ordering_consumer`: `false`
- `production_sizing_consumer`: `false`
- `runtime_planning_consumer`: `false`
- `production_consumer_connected`: `false`
- `runtime_switch_performed`: `false`
- `broker_write_performed`: `false`
- `reason_codes`: `["NON_AUTHORITATIVE_SHADOW_GENERATION_ERROR"]`
- `canonical_production_artifact_survives_shadow_failure`: `true`

This preserves observability without promoting the SHADOW to Production authority and without weakening authoritative fail-closed behavior.

## Missing-Symbol Path

Current source contains and binds `_two_stage_divergence_class` on the normal `build_unified_marginal_capital_shadow(...)` path.

Focused normal-path test confirms:

- `schema_version = unified_marginal_capital_shadow.v2`
- Stage-A `opportunity_strength_ranking` present
- Stage-B `executable_capital_ranking` present
- `production_comparison.two_stage_divergence_class` present
- `authoritative_consumer_count = 0`

## Failure Injection Result

Added regression:

`test_phase32_dy_non_authoritative_shadow_failure_does_not_replace_pc_artifact`

It monkeypatches `build_unified_marginal_capital_shadow(...)` to raise:

`NameError("name '_two_stage_divergence_class' is not defined")`

Expected and observed:

- PC capital competition schema survives as `portfolio_construction.capital_competition.v1`
- Production competitors are identical to the non-injected normal result
- Production market/cash competition result is identical
- canonical deployment set is identical
- capital competition winner type/symbol are identical
- `unified_marginal_capital_shadow` becomes `unified_marginal_capital_shadow_error.v1`
- diagnostic status is `SHADOW_ERROR`
- all authoritative/Production/runtime-planning consumer flags remain false/zero

## 2023-12-11 Non-Mutating Reconstruction

A read-only Python reconstruction used target-run evidence and adjacent valid target-run PIT PC shape without writing to the target run.

Observed:

- pre-repair failed target artifact still records: `name '_two_stage_divergence_class' is not defined`
- current-source reconstruction schema: `portfolio_construction.capital_competition.v1`
- current-source reconstructed SHADOW schema: `unified_marginal_capital_shadow.v2`
- current-source reconstructed SHADOW status: normal/PASS
- current-source reconstructed SHADOW `authoritative_consumer_count`: `0`
- no `_two_stage_divergence_class` NameError

With injected SHADOW failure on the same reconstruction shape:

- PC schema survived: `portfolio_construction.capital_competition.v1`
- SHADOW diagnostic schema: `unified_marginal_capital_shadow_error.v1`
- SHADOW diagnostic status: `SHADOW_ERROR`
- `authoritative_consumer_count`: `0`
- Production competitors preserved: `true`

No target-run artifact was modified.

## Authority Compatibility

Inspected target-run authority evidence remains:

- `strategy_shadow_manifest.hash_validation`: `PASS`
- `historical_evaluation_authority.status`: `PASS`
- accepted generation: `phase19_aq_accepted_generation_641e6e313543f013`
- accepted aggregate hash: `b97d3ccb14448b6ac721afcd93acedbabf4275712bb07816f13c322b2045480b`
- `2023-12-11 position_management.validation_status`: `PASS`
- `2023-12-11 position_management.source_authority_status`: `VALID`
- `2023-12-11 position_management.producer_result_status`: `PASS`

No accepted-generation, producer-hash, PM authority, registry, or checkpoint repair was required.

Current inspected source hashes:

- `src/ai_fund_lab_v2/strategy/marginal_capital_value.py`: `8d8971f269a0c6a19983ca6d1c8dd9679f852cf435b26c45d97e16f7558e48e0`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`: `37a9cb6d93ce70260312138d7c5bd345a5c0e7c4ec11b23353798db0c522f5d7`
- `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py`: `661607eed78087590b06c9058fe7338f3b048711197af0737a4d7b8d5cda86a9`
- `scripts/runtime_test.py`: `bcd96455e1d9fec68d5a75ab8dc635ad6f2304adf63395e83f828f9c2f94e038`

## Focused Validation

Commands executed:

```bash
PYTHONPATH=src:. PYTHONPYCACHEPREFIX=/private/tmp/pycache-phase32-dy python3 -m py_compile src/ai_fund_lab_v2/strategy/marginal_capital_value.py src/ai_fund_lab_v2/strategy/portfolio_construction.py scripts/runtime_test.py
```

Result: `PASS`

```bash
PYTHONPATH=src:. PYTHONPYCACHEPREFIX=/private/tmp/pycache-phase32-dy python3 -m pytest -q tests/strategy/test_phase32_dq_unified_marginal_capital_shadow.py
```

Result: `7 passed`

```bash
PYTHONPATH=src:. PYTHONPYCACHEPREFIX=/private/tmp/pycache-phase32-dy python3 -m pytest -q tests/strategy/test_phase31_g115_add_marginal_authoritative_binding.py tests/strategy/test_phase31_g119_pc_final_authority_ps_consistency.py tests/strategy/test_phase31_g44_add_reentry_lot_binding_integration.py tests/strategy/test_phase31_g63_runtime_executable_binding.py
```

Result: `28 passed`

```bash
PYTHONPATH=src:. PYTHONPYCACHEPREFIX=/private/tmp/pycache-phase32-dy python3 -m pytest -q tests/runtime_v2/test_phase30_ak9r27_pending_review_scope_authority.py tests/runtime_v2/test_phase31_f1w_item_scoped_partial_submit.py tests/runtime_v2/test_phase32_dt_shadow_backfill_marginal_capital.py
```

Result: `20 passed`

```bash
PYTHONPATH=src:. PYTHONPYCACHEPREFIX=/private/tmp/pycache-phase32-dy python3 -m pytest -q tests/strategy/test_phase22_g_runtime_planning.py
```

Result: `49 passed`

```bash
PYTHONPATH=src:. PYTHONPYCACHEPREFIX=/private/tmp/pycache-phase32-dy python3 -m pytest -q tests/strategy/test_phase22_e_portfolio_construction.py
```

Result: `124 passed`

```bash
git diff --check
```

Result: `PASS`

Total focused pytest result: `228 passed`.

## Target Run Readiness

Current target run state remains unchanged:

- status: `HALT`
- next job: `2023-12-11:morning`
- halted exit code: `10`

The failed `2023-12-11` evidence has no submit/execution side effect in the inspected daily artifact set. The safe continuation point is the same current continuation point:

`2023-12-11:morning`

Because the failed job is morning and no submit/execution boundary was reached, same-run resume is expected to regenerate the failed same-day planning artifacts under repaired source. No fresh-run is required by DY evidence.

## Required Final Answers

- `DW_MISSING_SYMBOL_PATH_REPAIRED`: `PASS`
- `NON_AUTHORITATIVE_SHADOW_FAILURE_ISOLATED`: `PASS`
- `AUTHORITATIVE_FAILURE_FAIL_CLOSED_PRESERVED`: `PASS`
- `SHADOW_ERROR_OBSERVABILITY_PRESERVED`: `PASS`
- `CANONICAL_PC_ARTIFACT_SURVIVES_SHADOW_FAILURE`: `PASS`
- `SHADOW_FAILURE_DOES_NOT_BLOCK_RUNTIME_PLANNING`: `PASS` in focused unit/regression scope; actual target-run resume was intentionally not executed.
- `PRODUCTION_DECISION_EQUIVALENCE`: `PASS`
- `DW_SHADOW_NORMAL_PATH_PRESERVED`: `PASS`
- `SHADOW_FAILURE_INJECTION_TEST`: `PASS`
- `20231211_POST_REPAIR_NON_MUTATING_RECONSTRUCTION`: `PASS`
- `POST_REPAIR_AUTHORITY_COMPATIBILITY`: `PASS`
- `SAME_RUN_RESUME_READY`: `YES`
- `FRESH_RUN_REQUIRED`: `NO`
- `PRODUCTION_CHANGE_EXECUTED`: `YES - control-plane isolation repair only; no Strategy/capital-allocation semantic change`
- `TARGET_RUN_MUTATED`: `NO`
- `LONG_RUNTIME_EXECUTED`: `NO`
- `NEXT_RECOMMENDED_STEP`:

```bash
RUN_ID=runtime-test-historical-extended-smoke-20260902T060955933565Z
PYTHONPATH=src python3 scripts/runtime_test.py resume \
  --run-id "$RUN_ID" \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

## Final Judgment

`PHASE32_DY_DW_SHADOW_BUILDER_FAILURE_ISOLATED_MORNING_CONTINUATION_READY`

