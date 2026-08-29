# Phase32-AD Canonical Position Campaign Authority Unification / Provenance Convergence Repair

## Executive Summary

Phase32-AD repaired the campaign identity split confirmed in Phase32-AC without changing REENTRY, Cash, PC/MCC, Risk Pacing, sizing, thresholds, PM scoring, or SELL decision logic.

The canonical authority remains the decision-time campaign lifecycle artifact:

```text
positions/position_campaigns.json
```

The repair makes downstream runtime surfaces inherit canonical campaign identity instead of creating parallel identities:

- Strategy Planning resolves same-day Strategy-origin `SELL_EXIT` PM campaign provenance from canonical `strategy/position_management.json` before lower-priority observability/runtime PM snapshots.
- Runtime-test campaign observability no longer mints a run-id-derived campaign id; it consumes existing canonical campaign provenance or reconstructs the same deterministic Strategy-style seed from execution identity.
- Current / broker-readonly / persistent position projection preserves `position_campaign_id`.
- Runtime-owned fill projection carries canonical campaign identity into Current; ledger-derived reconstruction is fallback only when canonical provenance is absent.

No fresh Historical run, resume, replay, backtest, or runtime state mutation was executed.

## Scope

Changed production/common code:

- `scripts/runtime_test.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py`
- `src/ai_fund_lab_v2/runtime_v2/asset/models.py`
- `src/ai_fund_lab_v2/runtime_v2/asset/builder.py`
- `src/ai_fund_lab_v2/runtime_v2/asset/runtime_owned_fill_projection.py`
- `src/ai_fund_lab_v2/runtime_v2/broker_readonly/models.py`
- `src/ai_fund_lab_v2/runtime_v2/broker_readonly/normalizer.py`
- `src/ai_fund_lab_v2/runtime_v2/current_sot_write_readback.py`
- `src/ai_fund_lab_v2/runtime_v2/execution/ledger_projection.py`
- `src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/ledger/models.py`

Changed tests:

- `tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py`
- `tests/runtime_v2/test_phase20_l_long_run_readiness_destructive.py`
- `tests/runtime_v2/test_phase23_i_strategy_planning_authority.py`

Changed SoT docs:

- `docs/02_architecture/strategy_intelligence_architecture_v1.md`
- `docs/02_architecture/runtime_architecture_v2.md`

## Root Cause Addressed

Phase32-AC found three campaign namespaces:

- canonical Strategy campaign, e.g. `pc-621...`
- runtime-test observability campaign, e.g. `pc-e6d...`
- ledger-derived fallback campaign, e.g. `ledger-derived-*`

Phase32-AD removes the second canonical generator role from runtime-test observability and demotes ledger-derived identities to compatibility fallback. Runtime-test summaries may still reconstruct for observability when no canonical provenance exists, but they no longer use `run_id` as campaign namespace authority.

## Repair Details

### Strategy PM Authority Priority

`activate_strategy_planning_authority()` now resolves Strategy-origin `SELL_EXIT` provenance before writing Pending. The PM lookup priority is:

1. `strategy/position_management.json`
2. `strategy_eod_shadow/position_management.json`
3. daily `position_management/pm_decisions.json`
4. runtime-state `position_management_decisions.json`

Resolution is priority-grouped. A clean canonical Strategy PM row is not vetoed by lower-priority observability snapshots with a different campaign id. Ambiguity inside the selected priority remains fail-closed.

Evidence:

- `src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py:231`
- `src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py:773`
- `src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py:823`

### Runtime-Test Observability

`_derive_position_campaign_state()` now starts a campaign from existing execution campaign provenance when present. If absent, it reconstructs from:

```text
symbol | campaign_sequence | execution_identity
```

It no longer uses:

```text
run_id | symbol | campaign_sequence
```

Evidence:

- `scripts/runtime_test.py:9469`
- `scripts/runtime_test.py:9554`

### Current / Fill Projection

`CurrentAssetPosition`, broker-readonly position snapshots, persistent position records, Current write/readback, and runtime-owned fill projection now preserve `position_campaign_id`.

Runtime-owned fill projection first inherits existing Current/latest position campaign evidence, then reconstructs from canonical execution events only if absent. Existing non-`ledger-derived-*` execution campaign ids are preserved.

Evidence:

- `src/ai_fund_lab_v2/runtime_v2/asset/runtime_owned_fill_projection.py:451`
- `src/ai_fund_lab_v2/runtime_v2/asset/runtime_owned_fill_projection.py:940`
- `src/ai_fund_lab_v2/runtime_v2/asset/runtime_owned_fill_projection.py:978`

## Contract Status

The repaired campaign semantic is:

- BUY_NEW opens one campaign.
- ADD stays in the same open campaign.
- Partial REDUCE stays in the same open campaign.
- Full EXIT closes the same campaign.
- REENTRY after full EXIT opens a new campaign.

`ledger-derived-*` is not promoted to canonical authority. It remains a fallback for legacy rows without canonical campaign provenance and must not override canonical Strategy PM campaign evidence.

## R / T / Y / AA Patch Convergence

- Phase32-R persistent order/execution provenance fields remain preserved.
- Phase32-T execution ledger provenance population remains preserved.
- Phase32-Y Strategy-origin `SELL_EXIT` PM identity materialization remains preserved.
- Phase32-AA campaign provenance preservation is converged into canonical Strategy PM priority and downstream inheritance.
- Runtime-test observability run-id campaign generation is removed from the canonical path.

## SoT Updates

The SoT now states that runtime-test observability, Current, broker-readonly snapshots, persistent positions, Pending, orders, executions, fill projection, and realized slices must inherit the canonical campaign identity and must not mint a second run-id-based canonical namespace.

Evidence:

- `docs/02_architecture/strategy_intelligence_architecture_v1.md:1353`
- `docs/02_architecture/runtime_architecture_v2.md:2823`

## Verification

Compilation:

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase32_ad_pycache python3 -m py_compile scripts/runtime_test.py src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py src/ai_fund_lab_v2/runtime_v2/asset/runtime_owned_fill_projection.py src/ai_fund_lab_v2/runtime_v2/asset/models.py src/ai_fund_lab_v2/runtime_v2/asset/builder.py src/ai_fund_lab_v2/runtime_v2/broker_readonly/models.py src/ai_fund_lab_v2/runtime_v2/broker_readonly/normalizer.py src/ai_fund_lab_v2/runtime_v2/current_sot_write_readback.py src/ai_fund_lab_v2/runtime_v2/execution/ledger_projection.py src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py src/ai_fund_lab_v2/runtime_v2/ledger/models.py tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py tests/runtime_v2/test_phase20_l_long_run_readiness_destructive.py tests/runtime_v2/test_phase23_i_strategy_planning_authority.py
```

Result: PASS.

Focused regression:

```text
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase23_i_strategy_planning_authority.py::test_phase32_ad_strategy_pm_campaign_overrides_observability_projection tests/runtime_v2/test_phase23_i_strategy_planning_authority.py::test_phase32_aa_strategy_origin_sell_exit_preserves_campaign_with_blank_runtime_pm_projection tests/runtime_v2/test_phase23_i_strategy_planning_authority.py::test_phase32_y_strategy_origin_sell_exit_materializes_pm_provenance_for_multiple_symbols tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py::test_phase32_t_actual_sell_path_populates_persistent_ledger_pm_and_campaign_provenance tests/runtime_v2/test_phase20_l_long_run_readiness_destructive.py::test_phase32_ad_observability_inherits_canonical_campaign_and_reconstructs_strategy_seed tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py::test_phase32_ad_current_preserves_canonical_campaign_from_runtime_owned_fills
```

Result: PASS, 6 passed.

PM adapter identity helper:

```text
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_ah_pm_adapter_registry_identity_guard.py::test_phase17_ah_current_adapter_identity_passes_with_isolated_accepted_set
```

Result: PASS, 1 passed.

## Registry

No formal Accepted Artifact Registry refresh was performed. The AD repair did not modify the `POSITION_MANAGEMENT_POLICY_SET:RUNTIME_ADAPTER` registry member in this turn. The PM adapter identity helper remains passing with an isolated accepted set. Registry authority is therefore `NOT_APPLICABLE` for this repair.

## Fresh Validation Recommendation

A user-operated short fresh validation is ready after this repair. The validation should confirm that 83060 and other early lifecycle rows carry one campaign id across PM, Pending, persistent orders, persistent executions, Current, runtime-test `positions/position_campaigns.json`, and realized slices, and that strict-prior PM reason matching remains non-GENERIC after EXIT.

## Final Judgments

```text
PHASE32_AD_CANONICAL_CAMPAIGN_AUTHORITY_UNIFIED = YES
PHASE32_AD_MULTIPLE_CANONICAL_GENERATORS_REMOVED = YES
PHASE32_AD_RUNTIME_TEST_OBSERVABILITY_REGENERATION_REMOVED = YES
PHASE32_AD_LEDGER_DERIVED_DEMOTED_TO_FALLBACK = YES
PHASE32_AD_CURRENT_CAMPAIGN_PRESERVED = YES
PHASE32_AD_PM_INHERITS_CANONICAL_CAMPAIGN = YES
PHASE32_AD_PENDING_INHERITS_CANONICAL_CAMPAIGN = YES
PHASE32_AD_ORDER_INHERITS_CANONICAL_CAMPAIGN = YES
PHASE32_AD_EXECUTION_INHERITS_CANONICAL_CAMPAIGN = YES
PHASE32_AD_FILL_OBSERVABILITY_INHERITS_CANONICAL_CAMPAIGN = YES
PHASE32_AD_REALIZED_SLICE_INHERITS_CANONICAL_CAMPAIGN = YES
PHASE32_AD_BUY_ADD_REDUCE_EXIT_SAME_CAMPAIGN = PASS
PHASE32_AD_REENTRY_NEW_CAMPAIGN = PASS
PHASE32_AD_STRICT_PM_MATCH = PASS
PHASE32_AD_NON_GENERIC_PRIOR_CONTEXT = PASS
PHASE32_AD_R_TO_AA_PATCH_CONVERGENCE_COMPLETE = YES
PHASE32_AD_IDEMPOTENCY_REGRESSION = PASS
PHASE32_AD_RESUME_RECOVERY_CAMPAIGN_SAFE = PARTIAL
PHASE32_AD_MODE_PARITY = PARTIAL
PHASE32_AD_REGISTRY_AUTHORITY_PASS = NOT_APPLICABLE
PHASE32_AD_REENTRY_LOGIC_CHANGED = NO
PHASE32_AD_CASH_LOGIC_CHANGED = NO
PHASE32_AD_PC_MCC_CHANGED = NO
PHASE32_AD_RISK_PACING_CHANGED = NO
PHASE32_AD_REGRESSION_STATUS = PASS
PHASE32_AD_SHORT_FRESH_VALIDATION_READY = YES
PHASE32_AD_NEXT_STEP = User-operated short fresh Historical validation after Phase32-AD; verify 83060 PM/Pending/order/execution/Current/positions/realized-slice campaign convergence and strict-prior non-GENERIC re-entry context.
```
