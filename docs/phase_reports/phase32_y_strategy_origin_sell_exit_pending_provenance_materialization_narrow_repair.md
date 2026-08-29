# Phase32-Y Strategy-Origin SELL_EXIT Pending Provenance Materialization Narrow Repair

## Executive Summary

Phase32-Y repaired the narrow provenance gap identified in Phase32-X: strategy-origin full `SELL_EXIT` pending items were able to carry a nested current-position alias such as `runtime-current-83060` while the top-level pending PM/campaign provenance remained blank. The repair now resolves the same-day authoritative PM `EXIT` decision by symbol and business date, rejects `runtime-current-*` as a PM decision identity, and materializes canonical PM/campaign provenance before pending serialization and submit.

The repair does not alter REENTRY, Cash, PC/MCC, Risk Pacing, sizing, thresholds, or strategy admission behavior. `SELL_EXIT` is preserved as planning intent in `quantity_contract["planning_intent"]`; the canonical PM/execution decision type propagated to pending/order/execution provenance is `EXIT`.

Focused verification passed:

- `python3 -m pytest -q tests/runtime_v2/test_phase23_i_strategy_planning_authority.py::test_phase32_y_strategy_origin_sell_exit_materializes_pm_provenance_for_multiple_symbols tests/runtime_v2/test_phase23_i_strategy_planning_authority.py::test_phase32_y_strategy_origin_sell_exit_materializes_pm_provenance_to_ledger_and_strict_prior tests/runtime_v2/test_phase23_i_strategy_planning_authority.py::test_phase32_y_strategy_origin_sell_exit_pm_provenance_fail_closed_controls tests/runtime_v2/test_phase23_i_strategy_planning_authority.py::test_phase32_y_partial_reduce_and_legacy_pending_shape_remain_safe tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py::test_phase32_t_actual_sell_path_populates_persistent_ledger_pm_and_campaign_provenance`
- Result: `5 passed in 23.23s`
- `PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m py_compile ...`
- Result: PASS
- `git diff --check -- ...`
- Result: PASS

No fresh run, resume, replay, backtest, or long Historical run was executed.

## Defect Boundary

Inherited failing boundary:

- Source: Phase32-X pending/submit/persistent-ledger PM identity lineage audit.
- First durable loss: strategy-origin `SELL_EXIT` order-plan to serialized pending materialization.
- Symptom: nested `strategy_authority_lineage.item.pm_decision_id = runtime-current-83060` survived, while canonical top-level `source_pm_decision_id`, `source_decision_id`, and `position_campaign_id` were blank.
- Consequence: persistent order/execution ledger could not provide strict PM decision identity to the prior-exit bridge.

## Repair

Production changes:

- `src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py`
  - Added same-day PM `EXIT` provenance resolution before pending item binding.
  - Reads authoritative PM artifacts at:
    - `daily/<business_date>/position_management/pm_decisions.json`
    - `runtime_state/position_management/<business_date>/position_management_decisions.json`
  - Requires exact current business date and matching symbol.
  - Accepts only `EXIT` / `SELL_FULL_POSITION`.
  - Rejects blank PM ids and `runtime-current-*` ids.
  - Fails closed on ambiguous same-symbol identities.
  - Fails closed on explicit campaign mismatch.
  - Writes canonical provenance to pending top-level, shallow `strategy_authority_lineage`, and `quantity_contract`.

- `src/ai_fund_lab_v2/runtime_v2/pending/models.py`
  - Added optional serialized pending fields:
    - `source_decision_id`
    - `position_campaign_id`

- `src/ai_fund_lab_v2/runtime_v2/pending/reader.py`
  - Reads new fields with blank defaults, preserving legacy pending compatibility.

- `src/ai_fund_lab_v2/runtime_v2/submit/guards.py`
  - Submit command construction now resolves PM/campaign provenance from pending top-level first, then lineage/quantity contract aliases.

- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`
  - Persistent order records now preserve `source_decision_id`, `source_pm_decision_id`, `source_decision_type`, PM business date, source position symbol, and campaign from pending/command provenance.

## Runtime-Current Identity Handling

`runtime-current-*` remains a possible legacy/current-position alias inside nested strategy-authority lineage, but it is no longer accepted as canonical PM decision identity. The canonical durable PM identity path is now:

`same-day PM EXIT artifact -> strategy-origin SELL_EXIT pending top-level -> submit command/order ledger -> execution ledger -> strict prior-exit bridge`

The multi-symbol regression intentionally preserves nested `strategy_authority_lineage.item.pm_decision_id = runtime-current-<symbol>` as source lineage evidence while asserting that top-level and shallow canonical PM fields are the real `pm-...-exit` ids.

## Serialized Pending Evidence

Regression: `test_phase32_y_strategy_origin_sell_exit_materializes_pm_provenance_for_multiple_symbols`

Coverage:

- Symbols: `83060`, `37820`.
- Input pending plans use strategy-origin `SELL_EXIT`.
- Nested legacy alias is forced to `runtime-current-<symbol>`.
- Same-day PM artifacts provide real `pm-2026-07-15-<symbol>-exit` ids and campaign ids.
- Pending is actually written and read back through the production pending writer/reader.

Assertions:

- Top-level `source_decision_id == pm-...-exit`.
- Top-level `source_pm_decision_id == pm-...-exit`.
- Top-level `source_decision_type == EXIT`.
- Top-level `source_pm_business_date == 2026-07-15`.
- Top-level `source_position_symbol == <symbol>`.
- Top-level `position_campaign_id == pc-phase32-y-<symbol>-0001`.
- Shallow lineage and `quantity_contract` carry the same PM/campaign provenance.
- Nested `runtime-current-*` is not promoted to canonical PM identity.

## Persistent Ledger / Strict Prior Bridge Evidence

Regression: `test_phase32_y_strategy_origin_sell_exit_materializes_pm_provenance_to_ledger_and_strict_prior`

Coverage:

- Strategy-origin `SELL_EXIT` for `83060`.
- Serialized pending has real PM id and campaign.
- Submit pipeline writes persistent order ledger.
- Execution readonly pipeline writes persistent execution ledger.
- Strict prior-exit bridge consumes the persistent execution lineage.

Assertions:

- Persistent order has:
  - `source_decision_id == pm-2026-07-15-83060-exit`
  - `source_pm_decision_id == pm-2026-07-15-83060-exit`
  - `source_decision_type == EXIT`
  - `position_campaign_id == pc-phase32-y-83060-0001`
- Persistent execution has the same canonical PM/campaign fields.
- Prior bridge evidence has `pm_exit_reason_matched_close_count > 0`.
- Prior context authority is `STRICT_PRIOR_PM_DECISION_EVIDENCE`.
- Previous exit reason classification is non-generic.

## Negative Controls

Regression: `test_phase32_y_strategy_origin_sell_exit_pm_provenance_fail_closed_controls`

Fail-closed cases:

- Missing PM artifact decision.
- Wrong symbol.
- Wrong business date.
- Future business date.
- Ambiguous same-symbol PM identities.
- Explicit campaign mismatch.

All cases leave top-level canonical PM/campaign fields blank and do not promote `runtime-current-83060`.

## Partial REDUCE / Legacy Compatibility

Regression: `test_phase32_y_partial_reduce_and_legacy_pending_shape_remain_safe`

Coverage:

- Partial `REDUCE` remains `SELL_REDUCE`; no full EXIT PM overlay is applied.
- Legacy pending payloads without `source_decision_id` and `position_campaign_id` remain readable with blank defaults.

## Registry Authority

Targeted accepted-artifact-registry membership search was run for the touched runtime files:

`rg -n "runtime_v2/planning/strategy_authority.py|runtime_v2/pending/models.py|runtime_v2/pending/reader.py|runtime_v2/submit/guards.py|runtime_v2/submit/pipeline.py" .runtime/artifact_registry -g '*.json' -g '*.jsonl'`

Result: no matching registry member entries. Formal accepted artifact registry refresh is therefore not applicable for this Phase32-Y change.

## Changed Files

Phase32-Y touched:

- `src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py`
- `src/ai_fund_lab_v2/runtime_v2/pending/models.py`
- `src/ai_fund_lab_v2/runtime_v2/pending/reader.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/guards.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`
- `tests/runtime_v2/test_phase23_i_strategy_planning_authority.py`
- `tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py`

Repository also contains broader pre-existing modified Phase32 files; they were not part of this narrow Phase32-Y repair.

## User Fresh-Validation Recommendation

The short fresh validation is ready for user operation. The prior HALT run must not be resumed or reused as acceptance evidence. Run a new short fresh validation after this repair to confirm actual-path materialization in runtime artifacts.

## Final Judgments

PHASE32_Y_STRATEGY_ORIGIN_PENDING_PROVENANCE_DEFECT_REPAIRED = YES

PHASE32_Y_RUNTIME_CURRENT_PM_ALIAS_REMOVED = YES

PHASE32_Y_REAL_PM_ID_PENDING_TOP_LEVEL = YES

PHASE32_Y_REAL_PM_ID_PENDING_LINEAGE = YES

PHASE32_Y_CAMPAIGN_ID_PENDING = YES

PHASE32_Y_SERIALIZED_PENDING_REGRESSION = PASS

PHASE32_Y_MULTI_SYMBOL_REGRESSION = PASS

PHASE32_Y_PERSISTENT_ORDER_PM_ID = PASS

PHASE32_Y_PERSISTENT_EXECUTION_PM_ID = PASS

PHASE32_Y_STRICT_PM_MATCH = PASS

PHASE32_Y_NON_GENERIC_PRIOR_CONTEXT = PASS

PHASE32_Y_PARTIAL_REDUCE_SAFE = YES

PHASE32_Y_AMBIGUOUS_IDENTITY_FAIL_CLOSED = YES

PHASE32_Y_REGISTRY_AUTHORITY_PASS = NOT_APPLICABLE

PHASE32_Y_REENTRY_LOGIC_CHANGED = NO

PHASE32_Y_CASH_LOGIC_CHANGED = NO

PHASE32_Y_PC_MCC_CHANGED = NO

PHASE32_Y_RISK_PACING_CHANGED = NO

PHASE32_Y_REGRESSION_STATUS = PASS

PHASE32_Y_SHORT_FRESH_VALIDATION_READY = YES

PHASE32_Y_NEXT_STEP = User-operated new short fresh validation; verify 83060 strategy-origin SELL_EXIT pending/order/execution artifacts carry real PM decision id and campaign, then confirm strict prior-exit context is non-generic on later REENTRY candidates.
