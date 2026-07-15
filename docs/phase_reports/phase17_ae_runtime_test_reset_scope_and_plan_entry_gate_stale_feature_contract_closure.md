# Phase17-AE Runtime Test Reset Scope / Plan Entry Gate Stale Feature Contract Closure

## Judgment

`PHASE17_AE_RUNTIME_TEST_RESET_SCOPE_ACCEPTED`

I did not run or resume the Frozen failed Runtime Test. I also did not manually delete the stale real `.runtime` JSON files.

## Root Cause

Reset initialized Current, Pending, and Ledger, but it did not clear prior-run derived operational artifacts. The stale Day2 artifact remained:

```text
.runtime/operations/feature_date_contract/2026-07-07.json
status: REVIEW_REQUIRED
reason: consumer_schema_review_required:pm
```

The plan entry gate then loaded that stale Feature Date Contract as pre-run authority and failed before the next clean run could regenerate market refresh artifacts using the Phase17-AD fix.

This is a reset scope bug plus a plan entry authority bug. It is not a PM producer bug.

## Fix

Updated reset scope in `src/ai_fund_lab_v2/runtime_v2/historical_support/reset_plan.py`:

- `operations/feature_date_contract`
- `operations/feature_consumer_readiness`
- `operations/feature_artifacts`
- `operations/feature_refresh`
- `operations/market_refresh`
- `runtime_state/market`
- `runtime_state/morning_pipeline`

Existing resettable paths such as `runtime_state/run_manifest`, `runtime_state/historical_broker`, `runtime_state/current_valuation`, `runtime_state/broker_readonly`, `runtime_state/safety`, Current, Pending, and Ledger remain in scope.

Excluded/retained paths remain protected:

- `artifact_registry`
- `artifacts`
- `operations/jquants`
- `phase9/canonical_data`
- `data/raw`
- `candidate_ai`
- `opportunity_ai`
- `configs`

Updated `scripts/runtime_test.py`:

- `reset` now reports `clean_state_invariant` with schema `runtime_test_reset_clean_state_invariant_v1`.
- `plan` no longer reads existing `feature_date_contract/*.json` as authority.
- Plan uses `runtime_test_plan_preflight` and profile window dates to build commands.
- Feature Date Contract generation and validation remains owned by `market_refresh` during the actual run.
- This does not ignore bad `status`; it prevents stale pre-run artifacts from becoming authority.

## Clean-State Contract

After reset, the invariant requires:

```json
{
  "operational_state_reset": true,
  "stale_feature_date_contracts_remaining": [],
  "stale_feature_consumer_readiness_remaining": [],
  "stale_feature_artifacts_remaining": [],
  "stale_run_manifests_remaining": [],
  "ledger_initial_cash": 1000000,
  "ledger_positions": [],
  "pending_state": "EMPTY",
  "historical_broker_state_reset": true
}
```

## Verification

Passed:

```bash
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_ae_reset_scope_plan_gate.py
```

Result: `3 passed`

Passed:

```bash
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_ae_reset_scope_plan_gate.py tests/runtime_v2/test_phase17_ad_position_feature_current_authority.py tests/runtime_v2/test_phase17_k_runtime_test_runner.py tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py tests/runtime_v2/test_phase17_aa_historical_current_valuation_authority.py tests/runtime_v2/test_phase17_ab_current_valuation_pre_gate_authority.py
```

Result: `42 passed`

Passed:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/phase17ae_pycache python3 -m py_compile scripts/runtime_test.py src/ai_fund_lab_v2/runtime_v2/historical_support/reset_plan.py tests/runtime_v2/test_phase17_ae_reset_scope_plan_gate.py
```

## Evidence

Evidence directory:

`reports/phase17_ae_runtime_test_reset_scope_and_plan_entry_gate_stale_feature_contract_closure/`

Files:

- `frozen_failed_state_inventory.json`
- `root_cause_classification.json`
- `reset_scope_classification.json`
- `plan_entry_gate_authority_change.json`
- `reset_clean_state_invariant_contract.json`
- `retained_artifact_audit.json`
- `rollback_contract_audit.json`
- `test_results.json`
- `external_effect_audit.json`

Machine-readable summary:

`reports/phase_reports/phase17_ae_runtime_test_reset_scope_and_plan_entry_gate_stale_feature_contract_closure.json`

## External Effects

- Real `runtime_test.py run/resume`: no
- Real `runtime_test.py reset/rollback` by Codex: no
- Manual stale JSON deletion: no
- Frozen failed state modified: no
- J-Quants API fetch: no
- Broker/Demo/Production write: no
- External notification: no
- Registry update: no
- AI retraining: no

## Next Clean Rerun

Use the normal clean lifecycle from the beginning:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py backup --profile historical-smoke --confirm --yes-i-understand-this-mutates-trading-state
PYTHONPATH=src python3 scripts/runtime_test.py reset --profile historical-smoke --backup-id <backup-id> --initial-cash 1000000 --confirm --yes-i-understand-this-mutates-trading-state
PYTHONPATH=src python3 scripts/runtime_test.py plan --profile historical-smoke --business-days 5 --start-date 2026-07-06 --write-evidence
PYTHONPATH=src python3 scripts/runtime_test.py run --profile historical-smoke --run-id <exact-plan-run-id> --confirm --yes-i-understand-this-mutates-trading-state
```
