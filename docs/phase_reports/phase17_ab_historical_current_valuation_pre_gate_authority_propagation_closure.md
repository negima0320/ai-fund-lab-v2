# Phase17-AB Historical Current Valuation Pre-Gate Authority Propagation Closure

## Judgment

`PHASE17_AB_HISTORICAL_CURRENT_VALUATION_PRE_GATE_AUTHORITY_ACCEPTED`

Frozen Run `runtime-test-historical-smoke-20260715T013241362762Z` was read-only. I did not run, resume, reset, rollback, or modify that run.

## Root Cause

The Day1 stop was before the Current Valuation producer.

Frozen observation:

- `job`: `current_valuation_refresh`
- `business_date`: `2026-07-06`
- `exit_code`: `20`
- `final_state`: `REVIEW_REQUIRED`
- `reason`: `historical_safety_temporal_authority_missing`
- `data_readiness_scope`: `execution`
- `data_readiness_status`: `REVIEW_REQUIRED`
- `safety_status`: `SAFETY_MISSING`
- `pending_slot_status`: `CONSUMED`

Phase17-AA did not affect this real run because AA propagated Historical market/safety authority inside the Current Valuation producer. The run stopped in `runtime_data_readiness_gate` before the producer was reached.

The precise root cause was composite:

1. `current_valuation_refresh` reused `execution` readiness scope.
2. Data Readiness accepted Pending Historical safety authority only when Current was initial-empty.
3. After execution, Current correctly contained five positions, so the valid `CONSUMED` Pending authority was ignored.
4. Pre-gate evidence did not explicitly distinguish producer-not-reached from producer review.

## Fix

Updated `src/ai_fund_lab_v2/runtime_v2/data_readiness.py`:

- Added formal `current_valuation` readiness scope.
- Allowed validated Pending Historical safety authority for `APPROVED` or `CONSUMED` lifecycle states.
- Removed the incorrect initial-empty Current requirement for Pending authority propagation after execution.
- Kept fail-closed validation for run ID, profile ID, evidence root, business date, safety decision, policy version, and external-effect controls.

Updated `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`:

- Mapped `current_valuation_refresh` to `current_valuation`, not `execution`.
- Enhanced Current Valuation evidence writer with:
  - `execution_reached`
  - `blocked_before_producer`
  - `blocking_stage`
  - `blocking_reason`

Added `tests/runtime_v2/test_phase17_ab_current_valuation_pre_gate_authority.py`.

## Production Boundary

Production behavior is not weakened.

- Production still requires formal latest Safety evidence.
- Missing Production Safety remains fail-closed.
- Historical Pending authority is accepted only in Historical replay with matching runtime-test identity and disabled external effects.
- No mode-only fallback was added.
- Broker write, submit, and external delivery permissions were not relaxed.

## Verification

Passed:

```bash
python3 -m pytest tests/runtime_v2/test_phase17_ab_current_valuation_pre_gate_authority.py -q
```

Result: `10 passed`

Passed:

```bash
python3 -m pytest tests/runtime_v2/test_phase17_ab_current_valuation_pre_gate_authority.py tests/runtime_v2/test_phase17_x_historical_sell_planning_authority.py tests/runtime_v2/test_phase17_aa_historical_current_valuation_authority.py tests/runtime_v2/test_phase17_k_runtime_test_runner.py -q
```

Result: `34 passed`

Passed:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/phase17ab_pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/data_readiness.py src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py tests/runtime_v2/test_phase17_ab_current_valuation_pre_gate_authority.py scripts/runtime_test.py
```

I also checked `tests/runtime_v2/test_phase15aq_runtime_data_readiness_gate.py`; it currently fails on an existing opportunity feature schema fixture issue (`consumer_schema_review_required:opportunity` / `opportunity_pre_inference_not_ready`), unrelated to AB safety authority propagation.

## Evidence

Evidence directory:

`reports/phase17_ab_historical_current_valuation_pre_gate_authority_propagation_closure/`

Files:

- `root_cause_classification.json`
- `pre_gate_control_flow.json`
- `safety_authority_source_comparison.json`
- `readiness_scope_mapping_before_after.json`
- `historical_authority_validation_matrix.json`
- `production_fail_closed_confirmation.json`
- `focused_test_results.json`
- `external_effect_audit.json`

Machine-readable summary:

`reports/phase_reports/phase17_ab_historical_current_valuation_pre_gate_authority_propagation_closure.json`

## External Effects

- Frozen Run changed: no
- `runtime_test.py run/resume/reset/rollback`: no
- Real submit/execution/current valuation run: no
- Isolated tmp CLI test: yes
- J-Quants fetch: no
- Broker write: no
- Demo write: no
- Production access: no
- External notification: no
- Registry mutation: no
