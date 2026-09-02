# Phase32-DL Corporate Action Operator Resolution + SELL Campaign Identity Production Repair

## Scope

- Target reference run: `runtime-test-historical-extended-smoke-20260902T060955933565Z`
- Continuation boundary: `2023-10-11:sell_planning`
- Execution mode in this phase: implementation + focused validation only
- Target run mutation: NO
- Fresh-run / resume / recover / replay: NOT EXECUTED
- Strategy / parameter / threshold / weight change: NO

## Root Cause Confirmation

Phase32-DK identified two Runtime correctness gaps at the 2023-10-11 boundary.

1. Runtime had no canonical operator path to turn a per-symbol Corporate Action Adjustment Authority from `REVIEW_REQUIRED` to `PASS` when PIT market data proves an `AdjFactor` impact but does not prove event type, adjusted quantity, or already-applied state.
2. SELL_EXIT Pending materialization could lose `position_campaign_id` / `campaign_id` when Strategy Runtime Planning carried SELL intent without explicit campaign fields, even though the same-run position campaign artifact had the open campaign identity.

The current target-run 50280 authority remains unresolved:

- artifact: `.runtime/runtime_state/corporate_action_adjustments/2023-10-11/50280.json`
- schema: `runtime_v2_corporate_action_adjustment_authority_v1`
- status: `REVIEW_REQUIRED`
- event type: `UNKNOWN_ADJFACTOR_IMPACT`
- factor: `0.3333333333333333`
- source: `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260902T060955933565Z/daily/2023-10-11/market_refresh/inputs/historical_asof/2023-10-11/raw/jquants/equities_bars_daily/data.parquet`
- source hash: `7d0bd0659b76385687e5664d553ae789b606ec4425ddac9debb6a41f0c3d2a7c`
- already-applied / ledger / current / pending adjustment statuses: `UNKNOWN`

The target run remains HALT with `next_job = 2023-10-11:sell_planning`. DL did not resolve 50280 and did not mutate that run.

## Repair Performed

### Corporate Action Operator Resolution

Implemented `resolve_corporate_action_adjustment_authority` in `src/ai_fund_lab_v2/runtime_v2/corporate_action_adjustment.py`.

The repair reuses the existing canonical artifact schema:

- `runtime_v2_corporate_action_adjustment_authority_v1`

It adds an embedded audit trail:

- `runtime_v2_corporate_action_operator_resolution_v1`

The resolver may materialize `PASS` only when all required evidence is explicit:

- current run/date/symbol binding
- original unresolved authority path/hash
- PIT source artifact path/hash
- non-unknown operator-supplied event type
- effective date and adjustment factor matching the PIT impact artifact
- pre/post quantity evidence
- adjusted Runtime-owned quantity
- broker-available quantity
- pending/submit quantity reconciliation
- price-basis reconciliation
- ledger/current/pending adjustment statuses
- already-applied idempotency confirmation
- reviewer id, audit id, resolution reason, reviewed evidence sources
- `future_data_used = false`

The resolver still fails closed for:

- missing original authority
- schema/date/symbol/source mismatch
- stale cross-run source lineage
- missing or mismatched source hash
- plan-expectation-only or missing PIT source
- `UNKNOWN_*` event type
- future data
- missing reviewer/audit/reason/evidence source
- unconfirmed already-applied status
- unresolved price or quantity basis
- duplicate/double-adjustment risk
- stale Pending or Submit quantity exceeding adjusted owned/broker-available quantity

`AdjFactor` remains an impact signal only. The repair does not infer event type, quantity adjustment, or already-applied state from `AdjFactor`.

### Runtime Test Operator Command

Added:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py resolve-ca-adjustment-authority
```

The command supports `--dry-run` and requires `--confirm --yes-i-understand-this-mutates-trading-state` for actual materialization. It writes only:

```text
.runtime/runtime_state/corporate_action_adjustments/<business_date>/<symbol>.json
```

It does not submit orders, regenerate Pending, mutate Ledger/Current, resume, recover, replay, or fresh-run.

### SELL Campaign Identity Propagation

Updated `src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py`.

For SELL_EXIT / SELL_REDUCE:

- explicit upstream campaign id remains authoritative when present
- if explicit id is absent, Pending materialization reads the same-run `positions/position_campaigns.json`
- exactly one open current campaign for the symbol may be inherited
- deterministic new campaign ids are not generated for SELL
- explicit SELL campaign mismatch fails closed before Pending approval
- missing canonical SELL campaign identity fails closed instead of publishing an empty campaign id

This preserves the Phase32-C/L campaign identity contract while keeping Strategy decisions unchanged.

## Files Changed

- `src/ai_fund_lab_v2/runtime_v2/corporate_action_adjustment.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py`
- `scripts/runtime_test.py`
- `docs/02_architecture/autonomous_ai_operations_architecture.md`
- `docs/03_operations/runtime_test_command_guide.md`
- `tests/runtime_v2/test_phase32_dl_ca_operator_resolution_and_sell_campaign_identity.py`
- `docs/phase_reports/phase32_dl_corporate_action_operator_resolution_sell_campaign_identity_production_repair.md`

## Focused Validation

PASS:

- `PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase32_dl_ca_operator_resolution_and_sell_campaign_identity.py`
  - `7 passed`
- `PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_bv8_historical_submit_pit_universe_authority.py tests/runtime_v2/test_phase31_a5_executable_membership_guard.py`
  - `20 passed`
- `PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase30_ak9r27_pending_review_scope_authority.py tests/runtime_v2/test_phase30_ak9r28_historical_safety_temporal_authority.py`
  - `22 passed`
- `PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase31_g115_add_marginal_authoritative_binding.py tests/strategy/test_phase32_cw_minimal_residual_reentry.py tests/strategy/test_phase32_dg_tick_normalized_production.py`
  - `41 passed`
- `PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase31_g44_add_reentry_lot_binding_integration.py tests/strategy/test_phase31_g63_runtime_executable_binding.py tests/runtime_v2/test_phase28_d8_sell_pending_authority_merge.py`
  - `17 passed`
- `PYTHONPYCACHEPREFIX=/private/tmp/pycache_phase32_dl PYTHONPATH=src python3 -m py_compile scripts/runtime_test.py src/ai_fund_lab_v2/runtime_v2/corporate_action_adjustment.py src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py`
  - PASS
- `PYTHONPATH=src python3 scripts/runtime_test.py resolve-ca-adjustment-authority --help`
  - PASS

Additional attempted regression:

- `tests/strategy/test_phase31_g97_residual_reconsideration_authoritative_binding.py`
- `tests/strategy/test_phase31_g99_reconsideration_lot_context_propagation.py`

Result: not usable in this workspace because they require old run evidence directories that are absent (`runtime-test-historical-extended-smoke-20260824T055234719725Z`, `runtime-test-historical-extended-smoke-20260824T121719329586Z`, `runtime-test-historical-extended-smoke-20260823T140946562431Z`). Failures were `FileNotFoundError`, not assertion failures against DL code.

## Required Answers

- `EXISTING_CA_AUTHORITY_SCHEMA_REUSED`: YES
- `CANONICAL_CA_OPERATOR_RESOLUTION_PATH_IMPLEMENTED`: YES
- `CA_OPERATOR_RESOLUTION_AUDIT_TRAIL`: YES, embedded as `operator_resolution`
- `ADJFACTOR_EVENT_TYPE_AUTO_INFERENCE`: NO
- `CA_QUANTITY_RECONCILIATION_CONTRACT`: YES
- `CA_PRICE_BASIS_RECONCILIATION`: YES
- `CA_ALREADY_APPLIED_IDEMPOTENCY_GUARD`: YES
- `CA_RESOLUTION_PASS_GATE`: YES
- `CA_RESOLUTION_RESPECTS_EXISTING_PM_SELL_INTENT`: YES, it resolves authority only and does not alter PM/Strategy intent
- `SELL_CAMPAIGN_ID_PROPAGATION_REPAIRED`: YES
- `SELL_CAMPAIGN_MISMATCH_FAIL_CLOSED`: YES
- `50280_VALID_RESOLUTION_FIXTURE`: YES, focused fixture passes
- `50280_INVALID_RESOLUTION_FAIL_CLOSED_FIXTURES`: YES, unknown event type, stale cross-run lineage, stale quantity, and missing already-applied/current lineage fail closed
- `ADJUSTED_QUANTITY_REWRITE_OR_REGENERATION_CONTRACT`: YES, stale Pending/Submit quantity exceeding adjusted quantity is rejected; no silent rewrite
- `76920_QUARANTINE_BEHAVIOR_CHANGED`: NO
- `HISTORICAL_BYPASS_INTRODUCED`: NO
- `OPERATOR_RESOLUTION_EXPLICIT_CONFIRMATION_REQUIRED`: YES
- `POST_RESOLUTION_RESUME_CONTRACT`: operator resolution only; if 50280 is resolved validly, user should resume from the existing continuation point without replaying earlier jobs unless a later gate explicitly requires regeneration
- `EXISTING_CA_FAIL_CLOSED_REGRESSION`: NO
- `DG_DI_REGRESSION`: NO within focused coverage; DG production tests pass and no DI-specific test file was found
- `CW_REENTRY_REGRESSION`: NO
- `G129_BUY_ADD_REGRESSION`: NO
- `CAMPAIGN_IDENTITY_REGRESSION`: NO
- `ARCHITECTURE_SOT_UPDATED`: YES
- `FOCUSED_REGRESSION_RESULT`: PASS, except old-run-artifact-dependent tests were not executable
- `PRODUCTION_CHANGE_EXECUTED`: YES, production Runtime code path changed
- `TARGET_RUN_MUTATED`: NO
- `DL_PRODUCTION_REPAIR_ACCEPTED`: YES

## 50280 Operator Resolution Command Template

Dry-run first:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py resolve-ca-adjustment-authority \
  --profile historical-extended-smoke \
  --run-id runtime-test-historical-extended-smoke-20260902T060955933565Z \
  --business-date 2023-10-11 \
  --symbol 50280 \
  --event-type <OPERATOR_REVIEWED_EVENT_TYPE> \
  --effective-date 2023-10-11 \
  --adjustment-factor 0.3333333333333333 \
  --pre-adjustment-quantity <OPERATOR_CONFIRMED_PRE_ADJUSTMENT_QTY> \
  --post-adjustment-quantity <OPERATOR_CONFIRMED_ADJUSTED_RUNTIME_OWNED_QTY> \
  --current-quantity <OPERATOR_CONFIRMED_ADJUSTED_RUNTIME_OWNED_QTY> \
  --broker-available-quantity <OPERATOR_CONFIRMED_ADJUSTED_BROKER_AVAILABLE_QTY> \
  --pending-quantity 100 \
  --submit-quantity 100 \
  --price-series-adjusted true \
  --quantity-adjusted true \
  --adjustment-already-applied true \
  --reviewer <OPERATOR_ID> \
  --audit-id <AUDIT_ID> \
  --resolution-reason <OPERATOR_REVIEW_REASON> \
  --evidence-source reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260902T060955933565Z/daily/2023-10-11/market_refresh/inputs/historical_asof/2023-10-11/raw/jquants/equities_bars_daily/data.parquet \
  --dry-run
```

Actual materialization only after the dry-run returns PASS and the operator has confirmed the event type / adjusted quantity / already-applied state:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py resolve-ca-adjustment-authority \
  --profile historical-extended-smoke \
  --run-id runtime-test-historical-extended-smoke-20260902T060955933565Z \
  --business-date 2023-10-11 \
  --symbol 50280 \
  --event-type <OPERATOR_REVIEWED_EVENT_TYPE> \
  --effective-date 2023-10-11 \
  --adjustment-factor 0.3333333333333333 \
  --pre-adjustment-quantity <OPERATOR_CONFIRMED_PRE_ADJUSTMENT_QTY> \
  --post-adjustment-quantity <OPERATOR_CONFIRMED_ADJUSTED_RUNTIME_OWNED_QTY> \
  --current-quantity <OPERATOR_CONFIRMED_ADJUSTED_RUNTIME_OWNED_QTY> \
  --broker-available-quantity <OPERATOR_CONFIRMED_ADJUSTED_BROKER_AVAILABLE_QTY> \
  --pending-quantity 100 \
  --submit-quantity 100 \
  --price-series-adjusted true \
  --quantity-adjusted true \
  --adjustment-already-applied true \
  --reviewer <OPERATOR_ID> \
  --audit-id <AUDIT_ID> \
  --resolution-reason <OPERATOR_REVIEW_REASON> \
  --evidence-source reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260902T060955933565Z/daily/2023-10-11/market_refresh/inputs/historical_asof/2023-10-11/raw/jquants/equities_bars_daily/data.parquet \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

## Next Recommended Step

Operator should first perform external/canonical review for 50280 to determine the actual event type, pre/post quantity relationship, adjusted Runtime-owned quantity, broker-available quantity, price basis, and already-applied idempotency state. Then run the dry-run command above. Do not resolve 76920 in this phase.

## Final Judgment

`PHASE32_DL_CA_OPERATOR_RESOLUTION_AND_SELL_CAMPAIGN_IDENTITY_PRODUCTION_REPAIR_ACCEPTED_TARGET_RUN_NOT_MUTATED`
