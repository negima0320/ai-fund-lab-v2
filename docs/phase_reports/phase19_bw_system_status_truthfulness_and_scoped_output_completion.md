# Phase19-BW System Status Truthfulness and Scoped Output Completion

## Existing Problems

Phase19-BW audited `scripts/runtime_test.py system-status` after the Phase19-BV Runtime summary work. The command had become too large for normal operation and still mixed separate authorities in a few places:

- Runtime execution was reported as `REVIEW_REQUIRED` when AI Model Health was in review, even when Runtime consumer status and BUY/SELL impacts were PASS/NONE.
- Historical post-run validation could treat non-retained transient feature artifacts as target-period data blockers even when the closed run evidence proved successful execution.
- Runtime freshness could inherit a future fixture date from lower-level AI freshness output.
- Position runtime feature row count and final post-run positions were not clearly separated.
- Accepted Generation age was shown without a complete explicit time-unit breakdown.
- There was no scoped output contract for compact daily use.

## Root Cause Analysis

Root cause was observability composition, not Runtime execution:

- `system-status` aggregated Model Health lifecycle review into Runtime status instead of preserving separate Runtime execution and AI Model Health judgments.
- Data status reused lower-level freshness fields that could include fixture-oriented dates instead of resolving target-date runtime artifacts from exact-match post-run context.
- Historical post-run data sufficiency still behaved partly like pre-run materialization validation.
- Human and JSON output lacked an operator scope layer, so the only practical output was the full inspection report.

## Inspection Context Contract

The audited target run was:

```text
runtime-test-historical-smoke-20260721T213848054826Z
```

Resolved context:

```text
inspection_mode      = HISTORICAL_POST_RUN
profile              = historical-smoke
target_business_date = 2026-07-14
runtime_stage        = EXECUTION_DONE
completed_days       = 20
run_authority        = latest_closed_runtime_test
```

## Authority Resolution

Post-run authority now uses closed-run evidence and target-date exact-match artifacts:

```text
artifact_resolution.status                  = PASS
artifact_resolution.authority               = target_business_date_exact_match
artifact_resolution.runtime_artifact_date    = 2026-07-14
artifact_resolution.fallback_used            = false
artifact_resolution.forbidden_fallbacks      = max_date, latest_directory, mtime, future_date
```

## Truthfulness Fixes

The implementation separates:

- inspection judgment
- Runtime execution judgment
- data judgment
- AI authority judgment
- AI Model Health judgment
- Runtime State judgment
- Broker configuration judgment
- Broker connectivity judgment
- Production readiness judgment

This prevents a single review signal from being rendered as a different operational fact.

## Overall Judgment Separation

Observed post-fix `system-status` overview:

```text
Inspection          : PASS
Runtime Execution   : PASS
Data                : PASS
AI Authority        : PASS
Model Health        : REVIEW_REQUIRED
Runtime State       : PASS
Broker Config       : PASS
Broker Connectivity : NOT_PERFORMED
Production Ready    : NOT_EVALUATED
Final               : SYSTEM_STATUS_PASS_WITH_MODEL_HEALTH_REVIEW
Exit Code           : 0
```

Model Health review remains visible, but it no longer makes completed Runtime execution look failed.

## Historical Post-run Semantics

For `HISTORICAL_POST_RUN`, the final completed business date is the target authority. The command must not compare final-day Runtime state to Day1 profile start date.

Post-run target-period sufficiency now uses completed-run evidence:

```text
target_period_data_sufficiency.status                         = PASS
target_period_data_sufficiency.reason                         = completed_run_evidence_is_post_run_authority
target_period_data_sufficiency.post_run_execution_evidence     = PASS
target_period_data_sufficiency.runtime_feature_status          = NOT_REQUIRED_FOR_POST_RUN_VALIDATION
```

## Target-period Data Sufficiency Fix

Missing transient per-day runtime feature artifacts after a successful closed run are reported as retention semantics, not as execution blockers:

```text
pre_run_source_sufficiency                 = NOT_APPLICABLE_POST_RUN
post_run_execution_evidence_sufficiency    = PASS
current_shared_runtime_artifact_retention  = NOT_REQUIRED_FOR_POST_RUN_VALIDATION
```

This does not weaken pre-run validation. It only changes historical post-run inspection semantics after closed-run evidence is authoritative.

## Position Feature Authority Analysis

Position runtime feature authority now distinguishes target-date feature rows from final post-run positions.

Observed evidence:

```text
position_runtime_feature.status                         = PASS
position_runtime_feature.row_count                      = 0
position_runtime_feature.position_feature_authority      = TEMPORAL_ISOLATION_PASS
position_runtime_feature.final_post_run_position_count   = 2
```

Reason: target-date feature rows for the inspected date are distinct from final ledger/current positions after the Runtime test completed.

## 2099 Fixture Artifact Analysis

The prior issue showed fixture-oriented `2099-01-01` values leaking into feature freshness. The post-fix data status resolves Runtime feature date from target-date exact-match artifact inspection:

```text
data_status.feature.feature_date                         = 2026-07-14
data_status.feature.expected_inference_feature_date       = 2026-07-14
data_status.feature.runtime_resolution_authority          = target_business_date_exact_match
data_status.feature.future_fixture_artifact_excluded      = true
```

Forbidden resolution methods are `max_date`, `latest_directory`, `mtime`, and `future_date`.

## Model Health Review Analysis

Model Health remains a review finding:

```text
reason         = MODEL_HEALTH_REVIEW_REQUIRED
severity       = REVIEW_REQUIRED
runtime_impact = NONE
buy_impact     = PASS
sell_impact    = PASS
```

This is observability for human monitoring. It is not, by itself, Runtime execution failure, BUY block, SELL block, or Production readiness.

## Scope Design

Implemented scopes:

```text
overview
data
ai
runtime
broker
readiness
lineage
components
full
```

Default scope is `overview`. `full` is available only by explicit `--scope full` or `--full`.

Multiple scopes are intentionally not implemented in Phase19-BW. A single selected scope preserves deterministic human and JSON output and avoids partial-order ambiguity.

## CLI Contract

Supported commands:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py system-status
PYTHONPATH=src python3 scripts/runtime_test.py system-status --scope data
PYTHONPATH=src python3 scripts/runtime_test.py system-status --scope full
PYTHONPATH=src python3 scripts/runtime_test.py system-status --full
PYTHONPATH=src python3 scripts/runtime_test.py system-status --json
```

`--detailed` remains unsupported.

## JSON Schema

JSON output now carries scoped v2 fields:

```text
system_status_schema_version = runtime_test_system_status_v2
scope
inspection_context
status_summary
findings
sections
```

The top-level runner `schema_version` remains `runtime_test_runner_v1` for existing Runtime Test runner compatibility.

## Backward Compatibility

The deprecated full legacy report remains available at:

```text
system_status_report
```

This preserves existing consumers while allowing new consumers to read selected-scope v2 fields.

## Human-readable Output

Default human output is now compact overview. It shows context, separated statuses, data freshness, Runtime state, Accepted Generation age, findings, final judgment, and exit code.

Full human inspection remains available through:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py system-status --scope full
```

## Command Guide Updates

Updated:

- `docs/03_operations/runtime_test_command_guide.md`
- `docs/phase_reports/runtime_test_command_guide.md`

The phase-report path is a compatibility note pointing to the canonical operations guide and documenting Phase19-BW `system-status` scope usage.

## Changed Files

Implementation:

- `scripts/runtime_test.py`
- `src/ai_fund_lab_v2/runtime_v2/system_status.py`

Tests:

- `tests/runtime_v2/test_phase19_bw_system_status_scoped_output.py`
- `tests/runtime_v2/test_phase19_ax_system_status.py`
- `tests/runtime_v2/test_phase19_az_system_status_full_inspection.py`

Documentation:

- `docs/02_architecture/autonomous_ai_operations_architecture.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/runtime_test_specification.md`
- `docs/03_operations/runtime_test_command_guide.md`
- `docs/phase_reports/runtime_test_command_guide.md`

Reports:

- `docs/phase_reports/phase19_bw_system_status_truthfulness_and_scoped_output_completion.md`
- `reports/phase_reports/phase19_bw_system_status_truthfulness_and_scoped_output_completion.json`

## Added Tests

Added BW-specific tests for:

- default compact overview output
- scoped JSON section selection
- legacy `system_status_report` preservation
- invalid `--scope` parser rejection
- Historical post-run truthfulness
- 2099 fixture exclusion / target-date exact-match evidence
- Accepted Generation age explicit units

Updated existing AX/AZ tests to request `--scope full` where full inspection is required.

## Regression Results

Executed allowed short/read-only checks only:

```text
py_compile: PASS
tests/runtime_v2/test_phase19_bw_system_status_scoped_output.py: 5 passed
tests/runtime_v2/test_phase19_bo_post_run_system_status_context.py: PASS
tests/runtime_v2/test_phase19_bk_system_status_target_date_resolution.py: PASS
tests/runtime_v2/test_phase19_ax_system_status.py: PASS
tests/runtime_v2/test_phase19_az_system_status_full_inspection.py: PASS
system-status overview read-only: exit 0
system-status full JSON read-only: exit 0
```

## Long-running Test Decision

Per user instruction, no smoke test, fresh-run, broker connectivity, broker write, or J-Quants API fetch was executed.

Historical Smoke re-run is not required for Phase19-BW because this phase changes observability, CLI output scoping, and post-run status interpretation only. It does not change Runtime trading behavior, data generation, AI inference, planning, submit, execution, or ledger mutation logic.

## Remaining Gaps

- Multiple simultaneous scopes are not implemented.
- Top-level JSON `schema_version` remains the Runtime Test runner schema; v2 status schema is exposed through `system_status_schema_version`.
- Model Health remains `REVIEW_REQUIRED`; Phase19-BW intentionally did not tune thresholds or alter Runtime behavior.

## Final Judgment

```text
PHASE19_BW_SYSTEM_STATUS_TRUTHFULNESS_AND_SCOPED_OUTPUT_COMPLETE
SYSTEM_STATUS_HISTORICAL_POST_RUN_TRUTHFULNESS_PASS
SYSTEM_STATUS_SCOPED_OUTPUT_CONTRACT_PASS
SYSTEM_STATUS_LEGACY_JSON_COMPATIBILITY_PASS
SYSTEM_STATUS_NO_RUNTIME_BEHAVIOR_CHANGE_PASS
```
