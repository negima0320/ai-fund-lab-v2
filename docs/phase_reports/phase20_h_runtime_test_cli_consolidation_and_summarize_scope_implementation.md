# Phase20-H: Runtime Test CLI Consolidation and Summarize Scope Implementation

## 1. Executive Summary

Phase20-H implemented the Phase20-G CLI consolidation decisions.

Implemented:

- Added `run-status` as the canonical Runtime Test runner-state command.
- Kept `status` as a compatibility alias using the same handler, payload, human output, authority, and exit code.
- Added `summarize --scope overview|performance|positions|lifecycle|full`.
- Kept the existing `summarize --run-id <RUN_ID>` behavior legacy-compatible by retaining existing top-level JSON fields and defaulting omitted `--scope` to full output.
- Did not add a `diagnose` command.

Final judgment:

```text
PHASE20_H_CLI_CONSOLIDATION_AND_SUMMARIZE_SCOPES_COMPLETE
```

## 2. Scope and Non-goals

Scope:

- CLI parser update.
- `run-status` compatibility implementation.
- `summarize --scope` JSON and human formatter integration.
- Summary evidence scope metadata.
- Operator Guide update.
- Short unit / regression / CLI / compile checks.

Non-goals:

- No Runtime logic change.
- No AI, Opportunity, PM, Risk, Capital Allocation, BUY, HOLD, ADD, REDUCE, or EXIT logic change.
- No Broker connection or order placement.
- No Training, Calibration, Validation rerun, long Historical Smoke, Full Backtest, or Experiment.

## 3. Reviewed Documents

- `docs/phase_reports/phase20_g_runtime_test_cli_responsibility_and_observability_integration_audit.md`
- `reports/phase_reports/phase20_g_runtime_test_cli_responsibility_and_observability_integration_audit.json`
- `docs/03_operations/runtime_test_command_guide.md`
- `docs/02_architecture/runtime_test_specification.md`
- `docs/02_architecture/performance_metric_benchmark_experiment_contract.md`
- `docs/phase_reports/phase20_a_performance_baseline_and_attribution_evidence_inventory.md`
- `docs/phase_reports/phase20_b_performance_metric_benchmark_experiment_contract.md`
- `docs/phase_reports/phase20_c_read_only_performance_baseline_extraction.md`
- `docs/phase_reports/phase20_d_trade_and_position_management_attribution_baseline.md`
- `docs/phase_reports/phase20_e_performance_diagnosis_and_attribution_report.md`
- `docs/phase_reports/phase20_f_performance_improvement_candidate_identification.md`
- `docs/phase_reports/phase19_bv_runtime_test_summarize_and_trade_attribution_command.md`
- `docs/phase_reports/phase19_by_runtime_test_summarize_run_authority_correction.md`
- `docs/02_architecture/autonomous_ai_operations_architecture.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/01_requirements/phase_roadmap.md`

## 4. Reviewed Implementation

- `scripts/runtime_test.py`
- `tests/runtime_v2/test_phase17_k_runtime_test_runner.py`
- `tests/runtime_v2/test_phase19_bv_runtime_test_summarize.py`
- `tests/runtime_v2/test_phase19_av_ai_status.py`
- `tests/runtime_v2/test_phase19_bw_system_status_scoped_output.py`

## 5. run-status Implementation

`run-status` was added to the parser as the canonical Runtime Test runner-state command:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py run-status
PYTHONPATH=src python3 scripts/runtime_test.py run-status --json
```

It dispatches to the existing `status(...)` handler. The payload intentionally continues to use the existing runner payload semantics so that `run-status` and `status` are semantically and byte-for-byte equal in tested JSON and human output.

## 6. status Compatibility Result

`status` remains available as a compatibility alias.

Compatibility guarantees verified:

- Same handler.
- Same human output.
- Same JSON payload.
- Same exit code.
- No evidence mutation.
- No trading state mutation.
- No unconditional deprecation warning in stdout.

## 7. summarize Scope Contract

Implemented scopes:

```text
overview
performance
positions
lifecycle
full
```

JSON additions are additive:

```text
scope
scope_default
available_scopes
contract_versions
authority
source_evidence
missing_evidence
warnings
overview
performance_scope
positions_scope
lifecycle_scope
summary_scope_schema_version
```

Existing top-level fields remain available, including:

```text
schema_version
run
external_effects
performance
pm_decisions
trading
reduce_exit
trade_attribution
current_positions
lifecycle_consistency
findings
runtime_judgment
performance_judgment
strategy_judgment
status
final_judgment
exit_code
```

`schema_version` remains `runtime_test_summary_v1` for backward compatibility. New scope semantics are recorded separately as `summary_scope_schema_version=runtime_test_summary_v2`.

## 8. overview Scope

Operator question:

```text
What happened in this run overall?
```

Includes:

- Run identity.
- Business dates.
- Runtime judgment.
- External effect judgment.
- Initial / final equity.
- Total return / return rate.
- BUY / SELL execution counts.
- PM counts.
- Lifecycle consistency.
- Review / block summary.
- Current positions summary.

## 9. performance Scope

Operator question:

```text
How did this run perform?
```

Includes contract-style metrics with:

```text
value
status
authority
confidence_class
limitations
warnings
contract_version
```

The producer first uses run-scoped summarize evidence and current summary values. If Phase20 baseline artifacts exist for the same `run_id`, they are used as run-matched enrichment. Missing Benchmark, Sector, and lot-level metrics are explicitly reported as `MISSING`, `DERIVABLE_PARTIAL`, or `NOT_AVAILABLE`; no zero-fill or external lookup is performed.

## 10. positions Scope

Operator question:

```text
What happened to each symbol-level Position Campaign?
```

Includes symbol-level campaign fields:

- BUY date / price / quantity.
- Capital allocated.
- Opportunity rank.
- Candidate score.
- Opportunity score.
- Confidence.
- Open / closed status.
- Final quantity and price when available.
- Available realized / unrealized PnL.
- Final or last-observed return.
- MFE / MAE as `POST_HOC_ATTRIBUTION_ONLY`.
- Evidence status and limitations.

Stable lot ID is not inferred. Rows are symbol-level Position Campaign observations.

## 11. lifecycle Scope

Operator question:

```text
How did BUY -> HOLD -> ADD -> REDUCE -> EXIT evolve?
```

Includes position lifecycle events from run-scoped evidence and, when available for the same `run_id`, Phase20-D attribution artifacts. Post-hoc values are labeled:

```text
POST_HOC_ATTRIBUTION_ONLY
```

Decision-time evidence, execution evidence, end-of-day valuation, post-hoc attribution, and missing evidence are kept distinct.

## 12. full Scope

`full` combines:

```text
overview
performance
positions
lifecycle
```

When `--scope` is omitted, `summarize` uses a legacy-compatible full default. This preserves existing top-level JSON consumers and the existing broad human summary.

## 13. Run Authority Compliance

Run event aggregation remains bounded by:

```text
reports/runtime_tests/runs/<RUN_ID>/
run_state.json
completed_business_days
Run-scoped evidence
```

Shared `.runtime` is not used as event-count authority. It is used only when the existing final-state hash guard passes, or for existing run-referenced detail rules. Existing Phase19-BY regression tests remain in place and passed in the targeted summarize suite.

## 14. JSON / Schema Compatibility

Compatibility result:

- Existing top-level fields were not removed.
- Existing `schema_version` remains `runtime_test_summary_v1`.
- New scope fields are additive.
- Explicit non-selected scopes are represented as `null`.
- `--scope full` includes all scope sections.

## 15. Evidence Output

`summarize --write-evidence` continues writing to:

```text
reports/runtime_tests/summaries/<summary_id>/
```

Evidence now records:

- `summary_id`
- `run_id`
- `generated_at`
- `scope`
- `contract_versions`
- `source_evidence`
- `authority`
- `warnings`
- selected scope sections

No Trading State, Current, Ledger, Pending, Runtime State, Registry, or Accepted Generation artifact is mutated by summary evidence writing.

## 16. Operator Guide Update

Updated:

```text
docs/03_operations/runtime_test_command_guide.md
```

The guide now documents:

- `run-status` as canonical.
- `status` as compatibility alias.
- Difference from `system-status` and `ai-status`.
- `summarize --scope` options.
- Human / JSON / write-evidence examples.
- Default legacy-compatible behavior.
- Position Lifecycle and Performance notes.
- Authority / missing evidence / post-hoc warnings.

## 17. Backward Compatibility

Preserved:

- `status`
- `summarize --run-id <RUN_ID>`
- `summarize --json`
- `summarize --write-evidence`
- Existing top-level summarize JSON fields.
- Existing summarize exit-code semantics.

Not added:

```text
diagnose
```

Not removed:

```text
system-status
ai-status
status
```

## 18. Runtime Impact

```text
NONE
```

No Runtime execution logic or Runtime state mutation was changed.

## 19. Strategy Impact

```text
NONE
```

No Strategy, AI, Opportunity, BUY, HOLD, ADD, REDUCE, EXIT, PM, Risk, or Capital Allocation logic was changed.

## 20. Authority Impact

```text
ADDITIVE_SUMMARY_OBSERVABILITY_ONLY
```

The change adds read-only summarize scope observability. It does not change Runtime judgment authority, Run Authority, Accepted Generation authority, or Performance Contract authority.

## 21. Validation

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

Passed:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py --help
PYTHONPATH=src python3 scripts/runtime_test.py run-status --help
PYTHONPATH=src python3 scripts/runtime_test.py summarize --help
PYTHONPYCACHEPREFIX=/tmp PYTHONPATH=src python3 -m py_compile scripts/runtime_test.py
```

Read-only target run spot checks:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py summarize --run-id runtime-test-historical-smoke-20260721T213848054826Z --scope overview --json
PYTHONPATH=src python3 scripts/runtime_test.py summarize --run-id runtime-test-historical-smoke-20260721T213848054826Z --scope performance --json
```

These returned existing `RUN_FINAL_STATE_HASH_MISMATCH` / `BLOCKED` because the current `.runtime` hashes differ from the target run final hashes. That is existing Run Authority guard behavior, not a Phase20-H regression.

Non-regression checks with existing local artifacts:

```bash
PYTHONPATH=src python3 -m pytest tests/runtime_v2/test_phase19_av_ai_status.py tests/runtime_v2/test_phase19_bw_system_status_scoped_output.py
```

Result:

```text
8 passed, 2 failed
```

The failures were pre-existing environment/artifact expectation differences outside Phase20-H changed files:

- `test_ai_status_json_review_required_for_statistical_drift`: expected `STATISTICAL_DRIFT_REVIEW_REQUIRED`, got `MODEL_HEALTH_REVIEW_REQUIRED`.
- `test_phase19_bw_post_run_truthfulness_json`: expected final post-run position count `2`, got `5`.

Not performed:

- 20BD Historical Smoke.
- Long Historical Test.
- Full Backtest.
- Broker connection.
- Training.
- Calibration.
- Validation rerun.
- Runtime State mutation.

## 22. Final Judgment

```text
PHASE20_H_CLI_CONSOLIDATION_AND_SUMMARIZE_SCOPES_COMPLETE
```

## User Verification Commands

```bash
cd /Users/negishi/work/ai-fund-lab-v2
export PYTHONPATH=src

python3 scripts/runtime_test.py --help
python3 scripts/runtime_test.py run-status
python3 scripts/runtime_test.py status
python3 scripts/runtime_test.py run-status --json > /tmp/run_status.json
python3 scripts/runtime_test.py status --json > /tmp/status.json
python3 scripts/runtime_test.py summarize --run-id runtime-test-historical-smoke-20260721T213848054826Z --scope overview
python3 scripts/runtime_test.py summarize --run-id runtime-test-historical-smoke-20260721T213848054826Z --scope performance
python3 scripts/runtime_test.py summarize --run-id runtime-test-historical-smoke-20260721T213848054826Z --scope positions
python3 scripts/runtime_test.py summarize --run-id runtime-test-historical-smoke-20260721T213848054826Z --scope lifecycle
python3 scripts/runtime_test.py summarize --run-id runtime-test-historical-smoke-20260721T213848054826Z --scope full
```
