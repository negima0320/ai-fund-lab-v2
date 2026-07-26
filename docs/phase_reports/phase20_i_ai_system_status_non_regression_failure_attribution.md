# Phase20-I: AI/System Status Non-regression Failure Attribution

## 1. Executive Summary

Phase20-I investigated and resolved the two non-regression failures observed during Phase20-H:

1. `ai-status` expected `STATISTICAL_DRIFT_REVIEW_REQUIRED` but actual was `MODEL_HEALTH_REVIEW_REQUIRED`.
2. `system-status` expected final post-run position count `2` but actual was `5`.

Findings:

- The `ai-status` failure was a test expectation / fixture isolation defect. The test depended on shared `.runtime` artifacts and expected a single specific review classification even though the formal contract permits non-structural review classifications such as `MODEL_HEALTH_REVIEW_REQUIRED` when non-drift review evidence is present.
- The `system-status` failure exposed both an implementation guard gap and a stale fixed test expectation. The implementation was able to read final position count from shared `.runtime` without recording final-state hash authority. The current local `system-status` context also resolves a later compatible closed run with 5 positions, not the earlier 20BD run with 2 positions.

Corrective actions:

- `ai-status` test now verifies formal review-only semantics instead of hard-coding one classification.
- Historical post-run context now records final/current state hashes, hash match status, final position count, and final position-count authority.
- `system-status` now uses post-run context position-count authority and returns `NOT_AVAILABLE` on final-state hash mismatch instead of reading a misleading shared Current count.
- `system-status` test now validates the authority path rather than hard-coding `2`.

Final judgment:

```text
PHASE20_I_NON_REGRESSION_FAILURES_ATTRIBUTED_AND_RESOLVED
```

## 2. Scope and Non-goals

Scope:

- Reproduce and attribute the two Phase20-H non-regression failures.
- Inspect relevant tests, producers, local artifacts, and authority rules.
- Apply minimal fixes only where root cause was confirmed.
- Run targeted regression tests.

Non-goals:

- No Phase20-H CLI redesign.
- No Runtime logic change.
- No AI model, AI selection, Opportunity, PM, Risk, Capital Allocation, or Accepted Generation change.
- No Broker connection.
- No long Historical Smoke, Full Backtest, Training, Calibration, or Validation rerun.

## 3. Reviewed Documents

- `docs/phase_reports/phase20_h_runtime_test_cli_consolidation_and_summarize_scope_implementation.md`
- `reports/phase_reports/phase20_h_runtime_test_cli_consolidation_and_summarize_scope_implementation.json`
- `docs/phase_reports/phase20_g_runtime_test_cli_responsibility_and_observability_integration_audit.md`
- `docs/03_operations/runtime_test_command_guide.md`
- `docs/phase_reports/phase19_av_ai_authority_audit_command_and_runtime_readiness.md`
- `docs/phase_reports/phase19_ax_system_status_command.md`
- `docs/phase_reports/phase19_bw_system_status_truthfulness_and_scoped_output_completion.md`
- `docs/02_architecture/runtime_test_specification.md`
- `docs/02_architecture/autonomous_ai_operations_architecture.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/01_requirements/phase_roadmap.md`
- `docs/phase_reports/phase19_by_runtime_test_summarize_run_authority_correction.md`

## 4. Reviewed Implementation

- `scripts/runtime_test.py`
- `src/ai_fund_lab_v2/runtime_v2/ai_status.py`
- `src/ai_fund_lab_v2/runtime_v2/ai_lifecycle_gates.py`
- `src/ai_fund_lab_v2/runtime_v2/system_status.py`
- `tests/runtime_v2/test_phase19_av_ai_status.py`
- `tests/runtime_v2/test_phase19_bw_system_status_scoped_output.py`
- `tests/runtime_v2/test_phase17_k_runtime_test_runner.py`
- `tests/runtime_v2/test_phase19_bv_runtime_test_summarize.py`

## 5. Failure Reproduction

The Phase20-H failure was reproduced with:

```bash
PYTHONPATH=src python3 -m pytest \
  tests/runtime_v2/test_phase19_av_ai_status.py \
  tests/runtime_v2/test_phase19_bw_system_status_scoped_output.py
```

Initial result before Phase20-I correction:

```text
8 passed, 2 failed
```

Failures:

- `test_ai_status_json_review_required_for_statistical_drift`
- `test_phase19_bw_post_run_truthfulness_json`

## 6. AI Status Failure Attribution

Observed current artifact:

```text
.runtime/runtime_state/buy_ai/2026-07-14/ai_lifecycle_gate_decision.json
decision = REVIEW_REQUIRED
classification = MODEL_HEALTH_REVIEW_REQUIRED
block_buy_planning = false
runtime_integrity_status = PASS
```

The test expected:

```text
STATISTICAL_DRIFT_REVIEW_REQUIRED
```

Implementation rule in `ai_lifecycle_gates._compose_result`:

- `STATISTICAL_DRIFT_REVIEW_REQUIRED` is selected only when all non-PASS checks are statistical-drift review checks.
- If other non-structural review checks are present, classification becomes `MODEL_HEALTH_REVIEW_REQUIRED` or `INSUFFICIENT_EVIDENCE`.
- Both are review-only when `block_buy_planning=false` and runtime integrity remains `PASS`.

Attribution:

```text
TEST_FIXTURE_DEFECT
EXPECTED_CONTRACT_CHANGE
PRIORITY_RULE_UNDEFINED_IN_TEST
```

The test used shared `.runtime` and did not construct a fixture guaranteeing only statistical drift findings. Therefore the specific classification expectation was too narrow.

## 7. System Status Failure Attribution

Observed current `system-status --json` post-run context:

```text
runtime_test_run_id = runtime-test-historical-smoke-20260721T224645728185Z
target_business_date = 2026-07-14
final_state_hash_match = true
final_position_count = 5
final_position_count_authority = CURRENT_RUNTIME_ROOT_FINAL_HASH_MATCH
```

The failing test expected `2`, which corresponds to an earlier 20BD run assumption. The command correctly resolves the latest compatible closed run for the current `.runtime`, and that local run has 5 positions.

However, the implementation also had a guard gap: `data_inspection.runtime_features[].final_post_run_position_count` directly read `.runtime/persistent_ledger/state.json` without carrying final-state hash authority into the field. If the latest closed run had not matched current hashes, this would have mixed shared Current into post-run reporting.

Attribution:

```text
FINAL_STATE_HASH_GUARD_GAP
STALE_LOCAL_ARTIFACT
TEST_FIXTURE_DEFECT
EXPECTED_CONTRACT_CHANGE
```

## 8. Phase20-H Causality Assessment

Phase20-H changed:

- `run-status`
- `status` alias handling
- `summarize --scope`
- summarize tests and docs

It did not change:

- `ai-status` producer
- AI lifecycle classification logic
- `system-status` producer before this Phase20-I fix
- post-run context resolution semantics

Conclusion:

```text
NO_DIRECT_PHASE20_H_CAUSALITY
```

The failures were surfaced by Phase20-H non-regression checks but were not caused by the Phase20-H CLI consolidation.

## 9. Test Isolation Assessment

`tests/runtime_v2/test_phase19_av_ai_status.py` and `tests/runtime_v2/test_phase19_bw_system_status_scoped_output.py` execute subprocesses against repository-local shared `.runtime` and `reports/runtime_tests`. They are integration-style checks rather than isolated fixture tests.

Risk:

- Accepted Generation and lifecycle artifacts can evolve.
- Latest compatible closed run can change.
- Position count can change with subsequent local closed runs.

Corrective test change:

- AI test now checks formal review-only semantics.
- System test now checks final position count according to the reported authority rather than a stale fixed count.

## 10. Authority Assessment

AI:

- `MODEL_HEALTH_REVIEW_REQUIRED` and `STATISTICAL_DRIFT_REVIEW_REQUIRED` are both valid non-structural review states when `block_buy_planning=false`.
- Runtime integrity remains `PASS`.
- Exit code remains `10`.

System:

- Historical post-run position count must be tied to final-state hash authority.
- If current root hashes match the selected closed run final hashes, position count may come from current `.runtime`.
- If hashes do not match, position count must be `NOT_AVAILABLE` and must not be read from shared Current.

## 11. Root Cause Classification

| Failure | Root Cause |
|---|---|
| AI status classification mismatch | `TEST_FIXTURE_DEFECT`, `EXPECTED_CONTRACT_CHANGE`, `PRIORITY_RULE_UNDEFINED_IN_TEST` |
| System status position count mismatch | `FINAL_STATE_HASH_GUARD_GAP`, `STALE_LOCAL_ARTIFACT`, `TEST_FIXTURE_DEFECT` |

## 12. Corrective Action

Changed:

- `scripts/runtime_test.py`
  - Historical post-run context now records final/current state hashes, hash match status, final position count, and final position-count authority.
- `src/ai_fund_lab_v2/runtime_v2/system_status.py`
  - `final_post_run_position_count` now uses post-run context authority.
  - Hash mismatch returns `NOT_AVAILABLE` instead of reading shared `.runtime`.
- `tests/runtime_v2/test_phase19_av_ai_status.py`
  - Test validates review-only AI semantics instead of one fixed classification.
- `tests/runtime_v2/test_phase19_bw_system_status_scoped_output.py`
  - Test validates position count based on reported authority.

No hard-coded run ID or hard-coded `5 -> 2` patch was added.

## 13. Regression Coverage

Passed:

```bash
PYTHONPATH=src python3 -m pytest \
  tests/runtime_v2/test_phase19_av_ai_status.py \
  tests/runtime_v2/test_phase19_bw_system_status_scoped_output.py
```

Result:

```text
10 passed
```

Passed:

```bash
PYTHONPATH=src python3 -m pytest \
  tests/runtime_v2/test_phase17_k_runtime_test_runner.py::test_phase20_h_run_status_matches_status_json_and_exit_code \
  tests/runtime_v2/test_phase17_k_runtime_test_runner.py::test_phase20_h_run_status_human_output_matches_status \
  tests/runtime_v2/test_phase19_bv_runtime_test_summarize.py
```

Result:

```text
14 passed
```

## 14. Remaining Gaps

- The AI/System status tests still depend on repository-local `.runtime` and `reports/runtime_tests`; they are useful integration checks but not fully isolated fixtures.
- A future phase could add isolated fixture tests for AI lifecycle priority ordering and Historical post-run context resolution.

## 15. Runtime Impact

```text
NONE
```

No Runtime execution behavior changed.

## 16. Strategy Impact

```text
NONE
```

No AI model, selection, Opportunity, PM, Risk, Capital Allocation, or trading decision logic changed.

## 17. Authority Impact

```text
AUTHORITY_GUARD_STRENGTHENED
```

Historical post-run position count now carries explicit final-state hash authority and no longer fails open to shared Current when hashes do not match.

## 18. Validation

Performed:

```text
targeted pytest
Phase20-H regression pytest
```

Passed:

```text
PYTHONPYCACHEPREFIX=/tmp PYTHONPATH=src python3 -m py_compile scripts/runtime_test.py src/ai_fund_lab_v2/runtime_v2/system_status.py
python3 -m json.tool reports/phase_reports/phase20_i_ai_system_status_non_regression_failure_attribution.json
git diff --check
```

Not performed:

```text
20BD Historical Smoke
1y/3y Historical Test
Full Backtest
Broker connection
Training
Calibration
Validation rerun
Runtime State mutation
```

## 19. Final Judgment

```text
PHASE20_I_NON_REGRESSION_FAILURES_ATTRIBUTED_AND_RESOLVED
```
