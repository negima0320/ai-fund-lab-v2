# Phase20-V PM Runtime Adapter Behavioral Equivalence Review

## Status

```text
PHASE20_V_PM_RUNTIME_ADAPTER_BEHAVIORAL_EQUIVALENCE_COMPLETE
FORMAL_ACCEPTANCE_REFRESH_READY
```

## Scope

This phase compares the old accepted Position Management Runtime Adapter with the current working-tree adapter after Phase20-S trace observability changes.

No Accepted Generation, Artifact Registry pointer, manifest hash, PM threshold, score formula, decision order, REDUCE quantity logic, Sell Planning quantity logic, BUY logic, Risk logic, broker logic, training, calibration, fresh-run, plan, run, resume, or long Historical run was changed or executed.

## Source Identity

| Item | Value |
|---|---|
| Old accepted commit | `f4f8dbf03355106f201174f6f68b86aac707b6ed` |
| Old accepted file | `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py` |
| Old accepted hash | `93581111ae9b61facf669f8033d87e927f103d05483b4f212da4a592dbb15185` |
| Current HEAD commit | `f4f8dbf03355106f201174f6f68b86aac707b6ed` |
| Current source dirty | `true` |
| Current file hash | `ac2e7f6a3e9e184889551a8884a0e779ffb37292e8b26daf1e25e1610bba739c` |

The old accepted source was loaded from Git history with `git show` and verified by sha256. The current source is the working-tree file, so the current hash is not represented by the HEAD commit.

## Static Diff Review

Static diff categories observed:

- `TRACE_ARTIFACT_OUTPUT`
- `DECISION_FIELD_ADDITION`
- `SCHEMA_METADATA_ONLY`
- `CONTROL_FLOW_CHANGE`
- `STATUS_CHANGE`
- `AUTHORITY_CHANGE`
- `INPUT_CHANGE`
- `SCORE_CHANGE`
- `ACTION_CHANGE`
- `OBSERVABILITY_ONLY_REVIEWED_BY_BEHAVIORAL_HARNESS`

Static diff alone was not used as equivalence proof. Behavioral harness execution was required because trace construction adds code paths and output fields.

## Behavioral Harness

Added:

```text
scripts/compare_pm_runtime_adapter_equivalence.py
tests/runtime_v2/test_phase20_v_pm_runtime_adapter_equivalence.py
```

The harness:

- loads old accepted `producer.py` into a temporary module without overwriting the worktree
- uses the current producer module normally
- bypasses only adapter hash preflight inside the isolated comparison harness after separately verifying old and current source hashes
- runs both producers on identical fixture runtime roots and inputs
- compares canonical behavior fields
- classifies trace-only additions as allowed differences
- writes JSON and Markdown evidence

## Scenario Results

| Scenario | Expected | Result |
|---|---|---|
| V-A-HOLD | HOLD | PASS |
| V-B-REDUCE | REDUCE | PASS |
| V-C-EXIT | EXIT | PASS |
| V-D-ADD | ADD | PASS |
| V-E-READY-EMPTY | NO_POSITION | PASS |
| V-F-MISSING-OPTIONAL | HOLD | PASS |
| V-G-INVALID-REQUIRED | REVIEW_REQUIRED | PASS |
| V-H-DECISION-ORDER-COLLISION | EXIT | PASS |

Summary:

```text
scenario_count = 8
decision_count_old = 6
decision_count_new = 6
canonical_match_count = 8
allowed_difference_count = 12
forbidden_difference_count = 0
trace_failure_count = 0
```

## Canonical Fields Compared

Top-level behavior:

```text
status
reason
review_required
decision_count
hold_count
reduce_count
exit_count
add_count
missing_fields
missing_symbols
defaulted_fields
derived_fields
temporal_validation_status
```

Decision behavior:

```text
symbol
business_date
decision
decision_id
reason
runtime_action
runtime_sell_quantity
runtime_quantity_authority
reduce_intensity
hold_score
exit_score
reduce_score
add_score
confidence
review_required
```

Action CSV behavior:

```text
code
action
hold_score
exit_score
reduce_score
add_score
action_reason
exit_reason
```

## Allowed Differences

Only trace / observability additions were observed:

```text
decision_trace
dominant_cause
secondary_causes
decision_reason_codes
action_score
selected_action_score
confidence_semantics
decision_trace_contract_version
decision_trace_path
```

No existing `reason`, `decision`, `runtime_action`, score, status, count, or quantity authority field changed.

## Trace Validation

Current adapter trace validation:

```text
decision_trace required fields present: PASS
dominant_cause present: PASS
decision_reason_codes present: PASS
action_score present: PASS
confidence_semantics present: PASS
post_hoc/future terms absent: PASS
```

The old accepted adapter lacks these fields, which is an allowed observability-only difference.

## Runtime Test False-PASS Regression

Re-ran Phase20-U targeted regression:

```text
PM HALT -> Runtime Test HALT: PASS
PM HALT metadata preserved in snapshot: PASS
PM decision snapshot compatibility: PASS
```

## Validation

Executed:

```text
PYTHONPYCACHEPREFIX=/private/tmp/pycache PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase20_v_pm_runtime_adapter_equivalence.py
PYTHONPYCACHEPREFIX=/private/tmp/pycache PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_k_runtime_test_runner.py::test_phase20_u_run_halts_when_pm_artifact_halts_despite_cli_exit_zero tests/runtime_v2/test_phase20_j_performance_observability.py::test_phase20_u_pm_halt_metadata_is_preserved_and_blocks_validation_close tests/runtime_v2/test_phase20_j_performance_observability.py::test_phase20_j_writes_campaign_fills_realized_slices_and_pm_snapshot
PYTHONPYCACHEPREFIX=/private/tmp/pycache PYTHONPATH=src python3 scripts/compare_pm_runtime_adapter_equivalence.py
```

Results:

```text
Phase20-V pytest: 2 passed
Phase20-U regression pytest: 3 passed
Equivalence harness: PM_RUNTIME_ADAPTER_BEHAVIORALLY_EQUIVALENT
```

## Acceptance Readiness

```text
PM_RUNTIME_ADAPTER_BEHAVIORALLY_EQUIVALENT
FORMAL_ACCEPTANCE_REFRESH_READY
```

Formal acceptance refresh readiness evidence is prepared. The actual acceptance refresh remains a separate human-authorized Artifact Registry / acceptance process.

## Acceptance

- OLD_ACCEPTED_RUNTIME_ADAPTER_HASH_VERIFIED: PASS
- CURRENT_RUNTIME_ADAPTER_HASH_VERIFIED: PASS
- STATIC_DIFF_REVIEW_COMPLETE: PASS
- HOLD_EQUIVALENCE_PASS: PASS
- REDUCE_EQUIVALENCE_PASS: PASS
- EXIT_EQUIVALENCE_PASS: PASS
- ADD_EQUIVALENCE_PASS: PASS
- READY_EMPTY_EQUIVALENCE_PASS: PASS
- INVALID_INPUT_FAIL_CLOSED_EQUIVALENCE_PASS: PASS
- DECISION_ORDER_EQUIVALENCE_PASS: PASS
- SCORE_EQUIVALENCE_PASS: PASS
- REDUCE_INTENSITY_EQUIVALENCE_PASS: PASS
- TRACE_ONLY_ALLOWED_DIFFERENCES_CONFIRMED: PASS
- NO_FORBIDDEN_BEHAVIOR_DIFFERENCE: PASS
- PHASE20_U_FALSE_PASS_FIX_REGRESSION_PASS: PASS
- ACCEPTED_GENERATION_NOT_MODIFIED: PASS
- LONG_RUNNING_HISTORICAL_TEST_NOT_EXECUTED: PASS

