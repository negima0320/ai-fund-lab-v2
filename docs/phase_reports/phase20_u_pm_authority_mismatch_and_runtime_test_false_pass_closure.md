# Phase20-U PM Authority Mismatch and Runtime Test False-PASS Closure

## Status

PHASE20_U_PM_AUTHORITY_AND_RUNTIME_TEST_FALSE_PASS_CLOSURE_COMPLETE

## Scope

This phase closes the observed Position Management authority mismatch and Runtime Test false-PASS path for:

```text
runtime-test-historical-extended-smoke-20260722T120122553309Z
```

No PM threshold, score formula, decision order, REDUCE quantity logic, BUY logic, Opportunity logic, Risk parameter, broker logic, Accepted Generation, training, calibration, validation run, or long Historical run was changed or executed.

## Root Cause

Root cause classification:

```text
STALE_ACCEPTED_GENERATION_MEMBER_HASH
ACCEPTANCE_REFRESH_REQUIRED
```

The accepted Position Management policy set uses `ACCEPTED_CURRENT_PATH` authority for the Runtime adapter member:

```text
artifact_set_type: POSITION_MANAGEMENT_POLICY_SET
artifact_set_id: control.position_management.accepted_set
accepted_event_id: event-a388a76c-8a50-4bfa-8296-4c456abce607-4051081ac44f2c2e
accepted_generation_id: phase19_aq_accepted_generation_641e6e313543f013
manifest: .runtime/artifact_registry/evidence/manifests/control_position_management_accepted_current_path_v9/artifact_set_manifest.json
member: RUNTIME_ADAPTER
member_path: src/ai_fund_lab_v2/runtime_v2/position_management/producer.py
hash_algorithm: sha256 over runtime adapter source bytes
```

Expected accepted member hash:

```text
93581111ae9b61facf669f8033d87e927f103d05483b4f212da4a592dbb15185
```

Current source hash:

```text
ac2e7f6a3e9e184889551a8884a0e779ffb37292e8b26daf1e25e1610bba739c
```

Phase20-S changed `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py` to add decision-time trace observability. That was a legitimate source change, but the accepted PM RUNTIME_ADAPTER member hash was not refreshed through the formal acceptance path before the fresh Historical run. The PM authority validation correctly failed closed.

## Target Run Evidence

For each target business date, run-scoped `sell_planning/position_management_evidence.json` showed:

| Business Date | PM Status | Input Status | Decision Count | Reason |
|---|---|---|---:|---|
| 2026-06-16 | HALT | HALT | 0 | artifact member hash mismatch: POSITION_MANAGEMENT_POLICY_SET:RUNTIME_ADAPTER |
| 2026-06-17 | HALT | HALT | 0 | artifact member hash mismatch: POSITION_MANAGEMENT_POLICY_SET:RUNTIME_ADAPTER |
| 2026-06-18 | HALT | HALT | 0 | artifact member hash mismatch: POSITION_MANAGEMENT_POLICY_SET:RUNTIME_ADAPTER |
| 2026-06-19 | HALT | HALT | 0 | artifact member hash mismatch: POSITION_MANAGEMENT_POLICY_SET:RUNTIME_ADAPTER |
| 2026-06-22 | HALT | HALT | 0 | artifact member hash mismatch: POSITION_MANAGEMENT_POLICY_SET:RUNTIME_ADAPTER |

The PM producer wrote fail-closed HALT artifacts. However, run-scoped `daily/<date>/position_management/pm_decisions.json` preserved only:

```text
source_status = AVAILABLE
decisions = []
```

and dropped the PM HALT metadata. Runtime Test close then validated only generic runtime files / run state and produced:

```text
status = PASS
test_validity_judgment = VALID
acceptance_gate_judgment = PASS
```

## False-PASS Location

The false PASS occurred after PM producer fail-closed output:

```text
PM producer HALT artifact
-> sell_planning retained position_management_evidence.json with HALT
-> Runtime Test PM snapshot treated available empty decisions as normal
-> run_command accepted CLI exit_code=0
-> validate_command did not inspect PM HALT evidence
-> close_command wrote PASS
-> fresh_run_summary inherited PASS
```

This confused abnormal HALT with normal empty PM state.

## READY_EMPTY vs HALT

Formal Runtime Test distinction:

```text
READY_EMPTY:
  no managed positions or no PM decisions after successful authority/input validation
  decision_count may be 0
  Runtime Test may continue

HALT:
  PM artifact status, PM adapter authority status, or PM input schema status is HALT
  decision_count may be 0 but is not normal empty
  Runtime Test must not final PASS
```

## Implemented Fix

Updated `scripts/runtime_test.py`:

- Preserve PM snapshot metadata:
  - `position_management_status`
  - `position_management_authority_status`
  - `position_management_input_status`
  - `position_management_reason`
  - `position_management_decision_count`
  - `position_management_trace_status`
  - compatibility aliases `pm_status`, `pm_authority_status`, `pm_input_schema_status`, `pm_reason`, `pm_decision_count`, `pm_trace_status`
- Add PM fatal evidence detection for run-scoped sell planning evidence and run-scoped PM snapshots.
- Treat `HALT` in PM status / PM authority status / PM input status as fatal for Runtime Test.
- Stop `run` / `resume` with `HALT_PM_POSITION_MANAGEMENT` even when Runtime CLI exits `0`.
- Make `validate` fail when run-scoped PM HALT evidence exists.
- Make `close` produce `REVIEW_REQUIRED` rather than `PASS` when PM HALT evidence exists.
- Expose fatal PM status counts in runtime summarize PM output.

## Not Changed

Not changed:

- PM hash validation was not weakened.
- PM HALT was not converted to READY_EMPTY.
- No fake PM decisions were generated.
- Accepted Generation / Artifact Registry hash was not manually edited.
- PM thresholds, score formulas, decision order, REDUCE quantity ratio, Sell Planning quantity authority, broker logic, and Runtime action logic were unchanged.

The correct authority-chain recovery remains a formal PM adapter acceptance refresh for the current `producer.py` hash.

## Targeted Tests

Executed:

```text
PYTHONPYCACHEPREFIX=/private/tmp/pycache PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_k_runtime_test_runner.py::test_phase20_u_run_halts_when_pm_artifact_halts_despite_cli_exit_zero tests/runtime_v2/test_phase20_j_performance_observability.py::test_phase20_u_pm_halt_metadata_is_preserved_and_blocks_validation_close tests/runtime_v2/test_phase20_j_performance_observability.py::test_phase20_j_writes_campaign_fills_realized_slices_and_pm_snapshot
```

Result:

```text
3 passed
```

Long Historical Smoke, broker access, training, calibration, validation, and J-Quants fetch were not executed.

## User Revalidation Commands

Codex did not execute these commands.

After formal PM adapter acceptance refresh, the operator can re-run a short fresh Historical check:

```bash
cd /Users/negishi/work/ai-fund-lab-v2

PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-extended-smoke \
  --business-days 5 \
  --start-date 2026-06-16 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state \
  --json
```

Then validate Phase20-T trace analysis:

```bash
PYTHONPATH=src python3 scripts/analyze_pm_cross_regime.py analyze-runs \
  --run-id <NEW_RUN_ID> \
  --output-json reports/phase_reports/phase20_t_post_u_trace_validation.json \
  --print-json
```

## Acceptance

- PM_RUNTIME_ADAPTER_HASH_MISMATCH_ROOT_CAUSE_IDENTIFIED: PASS
- PM_AUTHORITY_CHAIN_VERIFIED: PASS
- PM_AUTHORITY_FIX_CONTRACT_COMPLIANT: PASS
- PM_HASH_VALIDATION_NOT_WEAKENED: PASS
- PM_HALT_PROPAGATES_TO_RUNTIME_TEST: PASS
- PM_HALT_CANNOT_FINAL_PASS: PASS
- PM_READY_EMPTY_DISTINGUISHED_FROM_HALT: PASS
- PM_DECISION_SNAPSHOT_STATUS_PRESERVED: PASS
- PM_TRACE_FIELDS_COMPATIBILITY_PRESERVED: PASS
- PM_THRESHOLDS_UNCHANGED: PASS
- PM_SCORE_FORMULA_UNCHANGED: PASS
- PM_DECISION_ORDER_UNCHANGED: PASS
- PM_QUANTITY_LOGIC_UNCHANGED: PASS
- BROKER_LOGIC_UNCHANGED: PASS
- TARGETED_TESTS_PASS: PASS
- LONG_RUNNING_HISTORICAL_TEST_NOT_EXECUTED: PASS
- USER_REVALIDATION_COMMANDS_READY: PASS

