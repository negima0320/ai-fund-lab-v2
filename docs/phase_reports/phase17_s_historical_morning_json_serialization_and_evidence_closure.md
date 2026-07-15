# Phase17-S Historical Morning JSON Serialization and Evidence Closure

## Summary

Target failed run:

```text
runtime-test-historical-smoke-20260714T214218799081Z
```

Observed result:

```text
2026-07-06 market_refresh: PASS
2026-07-06 data_readiness: PASS
2026-07-06 morning: HALT
exit_code: 70
```

Direct error:

```text
Object of type PosixPath is not JSON serializable
```

Final judgement:

```text
PHASE17_S_HISTORICAL_MORNING_SERIALIZATION_ACCEPTED
```

Recommended next prefix:

```text
Phase17-T
```

## Root Cause

The failing object was:

```text
PosixPath('reports/opportunity_ai/phase5p/models/opportunity_model.pkl')
```

Field:

```text
$.metrics_validation.metrics_model_path
```

Serialization boundary:

```text
runtime_v2.buy_ai.producer._write_json
-> runtime_state/buy_ai/2026-07-06/opportunity_rankings.json
```

The object was produced while building Opportunity AI metrics validation evidence. Candidate inference completed far enough to reach the Opportunity artifact boundary, then `json.dumps` failed because a `Path` remained inside `metrics_validation`.

## Implementation

Implemented an explicit JSON-safe Runtime evidence boundary:

- `Path` -> POSIX string
- `datetime` / `date` -> ISO 8601 string
- `Enum` -> value
- `tuple` / `list` -> list
- `set` -> sorted list
- unsupported arbitrary objects -> fail-closed with `field_path` and `python_type`

No blanket `json.dump(..., default=str)` was added.

Updated:

- `src/ai_fund_lab_v2/runtime_v2/storage/json_safe.py`
- `src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py`
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`
- `tests/runtime_v2/test_phase17_s_json_serialization.py`

## Evidence Closure

Run-scoped Morning evidence is now written under:

```text
reports/runtime_tests/runs/<run_id>/daily/<business_date>/morning/morning_manifest.json
```

Serialization contract failures are classified as:

```text
RUNTIME_EVIDENCE_SERIALIZATION_ERROR
```

with:

- `error_type`
- `field_path`
- `python_type`
- `artifact_type`
- `job`
- `stage`

Detailed stack trace is internal evidence only.

## Safety Summary

Historical Morning manifest top-level Safety summary now reflects Data Readiness historical authority:

```text
safety_authority=historical_initial_no_external_effect
safety_decision=NEUTRAL
safety_reason=historical_neutral_no_event_safety_ready
safety_artifact_path=""
```

The latest Demo safety artifact is recorded only as ignored evidence, not as effective Historical safety.

## Verification

Passed:

```bash
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/phase17_s_pycache python3 -m pytest -q tests/runtime_v2/test_phase17_s_json_serialization.py
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/phase17_s_pycache python3 -m pytest -q tests/runtime_v2/test_phase17_s_json_serialization.py tests/runtime_v2/test_phase15aq_runtime_data_readiness_gate.py tests/runtime_v2/test_phase17_k_runtime_test_runner.py
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/phase17_s_pycache python3 -m pytest -q tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py tests/runtime_v2/test_phase15bv_execution_normalization_current_apply.py
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/phase17_s_pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/storage/json_safe.py src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py
```

Results:

- `4 passed`
- `25 passed`
- `11 passed`
- `py_compile` PASS

Isolated Historical Morning fixture:

- Data Readiness remained `READY`
- PosixPath serialization error did not recur
- run-scoped `morning_manifest.json` was generated
- final halt was contract-level `opportunity_metrics_model_path_mismatch`, not a technical JSON exception

## Non-Blocking Finding

Older Demo Morning fixture tests were also attempted. They stop before the serialization boundary on existing fixture readiness gaps such as `market_evidence_missing`. This is not a Phase17-S serialization regression, but should be handled separately if those legacy fixtures remain part of the active demo regression suite.

## Operations Not Performed

The following were not performed:

- 5BD Runtime execution
- failed run resume
- Trading State reset / restore / rollback
- real `.runtime` Current / Ledger / Pending manual mutation
- Feature generation or promotion
- Canonical update
- J-Quants fetch
- Submit
- Execution
- Tachibana API
- Demo submit
- Production access
- AI retraining
- Model change
- Feature schema change
- Registry mutation
- Acceptance mutation

