# Phase32-T - Actual-Path Persistent Ledger Provenance Population Final Repair

## Executive Summary

Phase32-T repaired the actual historical fresh-run provenance population gap found in Phase32-S. The repair is intentionally narrow: it propagates explicit PM/source/campaign provenance that already exists in PM artifacts and pending lineage into submit commands, historical broker snapshots, normalized orders/executions, persistent order ledger rows, and execution-equivalent ledger rows.

No REENTRY logic, Cash logic, PC/MCC logic, Risk Pacing, sizing economics, dedupe keys, accounting, quantity, price, valuation, or SELL decision logic was changed.

## First-Drop Boundary

Confirmed first-drop boundary:

`PM decision artifact -> SellExitDecision -> PendingOrderItem lineage`

Root cause:

- `_sell_exit_decisions_from_artifact` read only `decision_id`, while actual PM artifacts use `pm_decision_id`.
- The same PM artifact boundary did not carry `business_date` or `position_campaign_id` into `SellExitDecision`.
- `_pending_item_with_sell_decision_lineage` therefore could not populate `source_pm_decision_id`, `source_pm_business_date`, or `position_campaign_id` for actual PM-sourced SELL items.
- Downstream writers then preserved blanks faithfully.

This matches Phase32-S: daily reporting could still show PM identity from separate execution evidence, but the durable `.runtime/persistent_ledger/orders.jsonl` / `executions.jsonl` actual path had blank PM/campaign provenance.

## Exact Repair

The repair performs lossless explicit propagation only:

1. `SellExitDecision` now carries `source_business_date` and `position_campaign_id`.
2. `_sell_exit_decisions_from_artifact` now accepts `pm_decision_id` as the PM identity alias and carries explicit `business_date` / `position_campaign_id`.
3. `_pending_item_with_sell_decision_lineage` writes source id, PM id alias, PM business date, position symbol, and campaign id into pending quantity contract and `strategy_authority_lineage`.
4. Submit preflight reads explicit provenance from pending top-level fields, pending `strategy_authority_lineage`, and pending `quantity_contract`.
5. `RuntimeV2SubmitCommand` carries `position_campaign_id`.
6. Submit order ledger population reads the same explicit provenance and writes `source_decision_id`, `source_pm_decision_id`, `source_decision_type`, `source_pm_business_date`, `source_position_symbol`, and `position_campaign_id`.
7. Historical submit evidence and broker snapshot payloads carry the same fields into order/execution payloads.
8. Runtime readonly normalization and ledger projection preserve the fields.
9. Historical execution-equivalent records inherit provenance from the matched normalized order.

No fuzzy symbol/date/quantity reconstruction was added.

## Order Ledger Population

`LedgerOrderRecord` now has explicit:

- `source_decision_id`
- `position_campaign_id`

It already had:

- `source_decision_type`
- `source_pm_decision_id`
- `source_pm_business_date`
- `source_position_symbol`

The order ledger is now the durable source for equivalent execution provenance, including historical mode.

## Execution Ledger Population

Execution-equivalent ledger rows now inherit:

- `source_decision_id`
- `source_pm_decision_id`
- `source_decision_type`
- `source_pm_business_date`
- `source_position_symbol`
- `position_campaign_id`

from the normalized order. Broker-detail execution projection also accepts a matched `source_order` and falls back to order provenance only when the execution itself lacks explicit provenance. This keeps Demo/Production safe when a broker execution detail does not itself carry lineage but can be tied to a known normalized order.

## Campaign Identity

Canonical campaign source for this repair is explicit PM/pending lineage:

`PM decision.position_campaign_id -> SellExitDecision.position_campaign_id -> PendingOrderItem.strategy_authority_lineage / quantity_contract -> RuntimeV2SubmitCommand.position_campaign_id -> historical snapshot order/execution payload -> normalized order/execution -> persistent ledger`

If campaign identity is absent from the PM/pending lineage, it remains blank. No inferred campaign id is generated.

## Actual-Pipeline Regression

Added `test_phase32_t_actual_sell_path_populates_persistent_ledger_pm_and_campaign_provenance`.

The regression uses a PM artifact shaped like the actual path:

- PM row has `pm_decision_id`, not fixture-only `decision_id`.
- PM row has explicit `business_date`.
- PM row has explicit `position_campaign_id`.
- Pending starts without pre-populated source fields.

It then verifies:

- PM artifact extraction preserves the PM id/date/campaign.
- Pending lineage populates the submit path.
- Historical submit succeeds.
- Historical broker readonly ingestion succeeds.
- Persistent order ledger has PM id/date/symbol/type/campaign.
- Persistent execution ledger has PM id/date/symbol/type/campaign.
- Strict-prior bridge reports `pm_exit_reason_matched_close_count = 1`.
- Prior reason materializes as `STRICT_PRIOR_PM_DECISION_EVIDENCE`.
- The materialized reason maps to a non-GENERIC prior-exit class at PC consumption.

## Negative Controls

Covered by existing green suites:

- Missing source identity remains blank/fallback.
- Wrong symbol and wrong campaign fail closed in prior-exit bridge tests.
- Future PM evidence fails closed.
- Partial REDUCE does not create prior-exit close state.
- Legacy ledger rows remain readable.
- Dedupe/idempotency is unchanged.

The dedicated idempotency regression `test_phase32_r_historical_execution_retry_keeps_dedupe_key_unchanged_with_provenance` remains passing and asserts no duplicate execution append on retry.

## Mode Parity

Historical actual path is fixed by carrying provenance through historical submit evidence and execution-equivalent projection.

Demo/Production path remains safe:

- Broker-detail execution projection can inherit from a matched normalized order.
- If no explicit execution/order linkage exists, provenance remains blank.
- Broker fallback remains disabled for production by the existing policy.

Judgment: Demo/Production parity is safe in the sense of lossless preservation with no guessed provenance; it still depends on explicit order linkage.

## Changed Files

- `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/models.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/guards.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/historical_support/environment.py`
- `src/ai_fund_lab_v2/runtime_v2/broker_readonly/models.py`
- `src/ai_fund_lab_v2/runtime_v2/broker_readonly/normalizer.py`
- `src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/execution/ledger_projection.py`
- `src/ai_fund_lab_v2/runtime_v2/ledger/models.py`
- `tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py`

Note: Some listed broker/ledger schema/projection files already contained Phase32-R edits in the dirty worktree before Phase32-T; Phase32-T builds on them and adds actual-path population.

## Commands Executed

- `PYTHONPYCACHEPREFIX=/private/tmp/phase32t_pycache python3 -m pytest -q tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py -q` -> PASS, 20 tests
- `PYTHONPYCACHEPREFIX=/private/tmp/phase32t_pycache python3 -m pytest -q tests/runtime_v2/test_phase20_j_performance_observability.py::test_phase20_j_writes_campaign_fills_realized_slices_and_pm_snapshot -q` -> PASS
- `PYTHONPYCACHEPREFIX=/private/tmp/phase32t_pycache python3 -m pytest -q tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py -q` -> PASS, 26 tests
- `PYTHONPYCACHEPREFIX=/private/tmp/phase32t_pycache python3 -m pytest -q tests/runtime_v2/test_phase13_q_broker_readonly_models.py tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py -q` -> PASS, 21 tests
- `PYTHONPYCACHEPREFIX=/private/tmp/phase32t_pycache python3 -m pytest -q tests/strategy/test_phase29_l21k_prior_exit_materialization.py -q` -> PASS, 15 tests
- `PYTHONPYCACHEPREFIX=/private/tmp/phase32t_pycache python3 -m py_compile ...` -> PASS

## Fresh Validation Recommendation

Run a short fresh validation before any 650BD continuation. Acceptance should require:

- 83060-like PM EXIT daily artifact with `pm_decision_id` and `position_campaign_id`.
- Persistent order ledger has non-empty `source_decision_id`, `source_pm_decision_id`, and `position_campaign_id`.
- Persistent execution ledger has non-empty `source_decision_id`, `source_pm_decision_id`, and `position_campaign_id`.
- Strict-prior bridge `pm_exit_reason_matched_close_count > 0`.
- At least one semantic REENTRY row with `prior_exit_reason_authority = STRICT_PRIOR_PM_DECISION_EVIDENCE`.
- At least one semantic REENTRY row with non-GENERIC prior-exit class.

Do not use Equity/Holdings/PnL as the Phase32-T acceptance gate.

## Final Judgments

PHASE32_T_FIRST_DROP_BOUNDARY = PM decision artifact -> SellExitDecision extraction (`pm_decision_id`, `business_date`, and `position_campaign_id` were not carried into pending lineage)

PHASE32_T_ORDER_LEDGER_PM_ID_POPULATED = YES

PHASE32_T_EXECUTION_LEDGER_SOURCE_ID_POPULATED = YES

PHASE32_T_EXECUTION_LEDGER_CAMPAIGN_ID_POPULATED = YES

PHASE32_T_STRICT_PM_MATCH_ACTUAL_PIPELINE_PASS = YES

PHASE32_T_NON_GENERIC_PRIOR_CONTEXT_ACTUAL_PIPELINE_PASS = YES

PHASE32_T_DEDUPE_UNCHANGED = YES

PHASE32_T_IDEMPOTENCY_REGRESSION = PASS

PHASE32_T_PARTIAL_REDUCE_SAFE = YES

PHASE32_T_LEGACY_FALLBACK_SAFE = YES

PHASE32_T_HISTORICAL_ACTUAL_PATH_FIXED = YES

PHASE32_T_DEMO_PRODUCTION_PARITY_SAFE = PARTIAL

PHASE32_T_PROVENANCE_DEFECT_FULLY_REPAIRED = YES

PHASE32_T_REENTRY_LOGIC_CHANGED = NO

PHASE32_T_CASH_LOGIC_CHANGED = NO

PHASE32_T_PC_MCC_CHANGED = NO

PHASE32_T_RISK_PACING_CHANGED = NO

PHASE32_T_SHORT_FRESH_VALIDATION_READY = YES
