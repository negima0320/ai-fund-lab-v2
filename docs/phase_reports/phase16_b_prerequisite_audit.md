# Phase16-B Historical Runtime Test Prerequisite Audit

Prefix: `Phase16-B`  
Work name: `Historical Runtime Test Prerequisite Audit`  
Audit date: `2026-07-13`  
Final judgment: `PHASE16_B_PREREQUISITES_IMPLEMENTATION_REQUIRED`

## Scope

This audit reviewed whether the current Runtime v2 can start the Phase16 Historical Runtime Test without changing Runtime code.

No Reset was executed. No Historical Runtime Test, replay, backtest, 2021 replay, 20-business-day run, one-year run, or full-period run was executed. No Runtime, CLI, AI, Historical Clock, or Historical Broker implementation was changed.

## Summary

The current Runtime v2 has several useful foundations: normal `.runtime` mainline jobs exist, `--business-date` and `--evaluation-time` exist in the daily CLI, Submit and Execution have lower-level broker seams, report/audit artifacts are generated, and candidate-level leakage checks exist.

However, Phase16 Historical Runtime Test cannot start as-is. The blocking prerequisites are full Runtime Reset/Backup/Restore, complete Historical Clock injection, CLI-selectable Historical Simulated Broker replacement, public-report optionality, and end-to-end replay readiness.

## A. Runtime Reset

Status: `IMPLEMENTATION_REQUIRED`

Evidence:

- `src/ai_fund_lab_v2/runtime_v2/asset/initializer.py:27` defines `initialize_demo_operation_current_sot(...)`, not a formal all-Runtime reset CLI.
- `src/ai_fund_lab_v2/runtime_v2/asset/initializer.py:17` lists only persistent ledger files: `state.json`, `orders.jsonl`, `executions.jsonl`, `positions.jsonl`, `cash.jsonl`, `events.jsonl`.
- `src/ai_fund_lab_v2/runtime_v2/asset/initializer.py:41` to `src/ai_fund_lab_v2/runtime_v2/asset/initializer.py:43` backs up only `runtime_root / "persistent_ledger"` before writing the fixed demo Current SoT.
- `src/ai_fund_lab_v2/runtime_v2/asset/initializer.py:91` to `src/ai_fund_lab_v2/runtime_v2/asset/initializer.py:96` overwrites ledger/current files for Phase14e8 demo initialization.

Existing:

- Partial demo Current SoT initializer.
- Partial persistent ledger file backup for the demo initializer.
- Current temporal/valuation update backups exist outside this full reset scope.

Missing:

- Formal Reset CLI for Phase16.
- Full Runtime backup and restore covering Current, Ledger, Pending, Runtime State, Approval, Execution, Idempotency, report state, broker state, manifests, and logs.
- All-or-nothing restore procedure.
- Evidence that reset initializes all required Runtime v2 state consistently.

## B. Historical Clock

Status: `IMPLEMENTATION_REQUIRED`

Evidence:

- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:93` to `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:97` uses `_utc_now()` and falls back to `date.today()` when `--business-date` is absent.
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:993` defines `--business-date`.
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:1021` defines `--evaluation-time`.
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:1252` to `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:1258` parses `--evaluation-time` as timezone-aware UTC.
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:1327` to `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:1333` records stage `created_at` from `_utc_now()`.
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:1352` to `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:1355` writes log timestamps from `_utc_now()`.
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:1417` to `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:1418` defines `_utc_now()` as `datetime.now(timezone.utc).isoformat()`.
- `src/ai_fund_lab_v2/runtime_v2/pending/lifecycle_runner.py:30` to `src/ai_fund_lab_v2/runtime_v2/pending/lifecycle_runner.py:42` accepts `now`, but the CLI call at `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:323` to `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:329` does not pass `evaluation_time`.
- `src/ai_fund_lab_v2/runtime_v2/report/markdown_writer.py:102` to `src/ai_fund_lab_v2/runtime_v2/report/markdown_writer.py:108` falls back to `date.today()` if no business date can be resolved.

Current-time dependencies identified:

| Dependency | Evidence | Impact |
|---|---|---|
| `datetime.now(timezone.utc)` | CLI `_utc_now()`, stage/log timestamps | Runtime artifacts can contain wall-clock time instead of historical evaluation time. |
| `date.today()` | CLI business-date fallback, report fallback | Historical run requires explicit `--business-date`; standalone report can drift to current date. |
| UTC current timestamp | run id, manifest finish time, logs, stages | Historical reproducibility is incomplete. |
| Current business-day dependency | `resolve_operation_date(business_date, ...)` is used, but business-date omission falls back to today | Historical mode is not fail-closed on missing business date. |

Conclusion: `business-date` and `evaluation-time` exist, but they do not make all Runtime v2 jobs historical-time-driven.

## C. Historical Simulated Broker

Status: `IMPLEMENTATION_REQUIRED`

Evidence:

- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py:44` to `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py:49` defines the `RuntimeV2SubmitAdapter` protocol.
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py:128` to `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py:137` accepts an optional `adapter`.
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py:150` to `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py:151` blocks non-demo submit mode.
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py:207` falls back to `_build_tachibana_demo_submit_adapter(settings)` when no adapter is injected.
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:672` to `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:681` calls `run_submit_pipeline(...)` without exposing adapter injection.
- `src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py:91` to `src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py:97` accepts an optional `snapshot_provider`.
- `src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py:108` to `src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py:113` blocks modes outside `demo` and `production`.
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:714` to `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:719` calls `run_execution_readonly_pipeline(...)` without exposing `snapshot_provider`.
- `src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py:187` to `src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py:196` appends normalized broker evidence into Ledger.
- `src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py:255` to `src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py:289` projects accepted runtime-owned fills to Current and Runtime State after Execution.
- `src/ai_fund_lab_v2/runtime_v2/simulation/harness.py:52` to `src/ai_fund_lab_v2/runtime_v2/simulation/harness.py:58` provides a separate simulation replay harness, but it builds simulation AI/planning/safety fixtures internally and is not the normal CLI mainline.

Conclusion: Broker-boundary seams exist in lower-level functions, and Execution-to-Ledger-to-Current can remain normal after a snapshot is accepted. But the normal Runtime CLI cannot select a Historical Simulated Broker, and mode guards block a dedicated historical/simulation mode. Broker-only replacement is therefore not ready.

## D. Public Report

Status: `IMPLEMENTATION_REQUIRED`

Evidence:

- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:996` to `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:998` defines notification mode choices, defaulting to `payload-only`.
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:1036` to `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:1037` requires `--notification-mode payload-only`.
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:818` to `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:824` unconditionally calls `generate_public_report_from_current(...)`.
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:826` to `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:829` always stages runtime report, markdown/public report, notification payload, and audit generation.
- `src/ai_fund_lab_v2/runtime_v2/report/public_report_writer.py:15` to `src/ai_fund_lab_v2/runtime_v2/report/public_report_writer.py:31` always writes markdown/public report artifacts through `write_markdown_reports(...)`.

Existing:

- Delivery is effectively disabled by requiring `payload-only`.
- Runtime/public report, notification payload artifact, and audit artifact are generated.

Missing:

- CLI/report options to generate only Runtime Report, Audit, and Performance Report while turning off Blog/Public report artifacts.
- Explicit flags to suppress Discord, LINE, Notification payload generation as Phase16 public-output OFF controls.

## E. Runtime Mainline

Status: `IMPLEMENTATION_REQUIRED`

Evidence:

- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:80` to `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:88` lists normal Runtime v2 jobs such as market refresh, safety, pending lifecycle, runtime state refresh, current refresh, broker readonly refresh.
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:460` to `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:490` runs Candidate/Opportunity BUY production and Morning planning/pending pipeline.
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:543` to `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:551` runs Sell planning into Pending.
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:672` to `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:681` runs Submit.
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:714` to `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:719` runs Execution.
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:738` to `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:769` runs Market refresh.
- `src/ai_fund_lab_v2/runtime_v2/simulation/harness.py:52` to `src/ai_fund_lab_v2/runtime_v2/simulation/harness.py:58` is a separate simulation harness and should not be used as the Phase16 acceptance shortcut.

Conclusion: The normal Runtime v2 components exist, but Historical Runtime Test cannot yet use the full mainline end-to-end because Reset, Historical Clock, Historical Broker, and Public Report optionality are not ready. The simulation harness is not acceptable as the Phase16 mainline substitute.

## Look-ahead Prevention

Status: `IMPLEMENTATION_REQUIRED`

Evidence:

- `src/ai_fund_lab_v2/candidate_ai/leakage_audit.py:10` to `src/ai_fund_lab_v2/candidate_ai/leakage_audit.py:37` audits candidate feature tables for forbidden future/label/post-as-of features.
- `tests/test_phase4bc_long_history_feature_regeneration.py:36` to `tests/test_phase4bc_long_history_feature_regeneration.py:38` verifies leakage audit status and absence of future/label columns in long-history feature regeneration.

Existing:

- Candidate-level feature leakage controls and tests.

Missing:

- Phase16 end-to-end point-in-time guard covering Historical Runtime Test inputs across Market, Feature, Candidate, Opportunity, Policy, Safety, Planning, Broker simulation, Execution, Ledger, Current, and Reports.
- Evidence that listed status, universe membership, corporate actions, quote availability, and fill availability are all cut off at historical evaluation time.

## Classification Matrix

| Target | Classification | Reason |
|---|---|---|
| Runtime Reset | `IMPLEMENTATION_REQUIRED` | Only partial demo Current initializer exists; no formal full Runtime reset. |
| Backup | `IMPLEMENTATION_REQUIRED` | Partial persistent-ledger/current backups exist; no full Runtime backup contract. |
| Restore | `IMPLEMENTATION_REQUIRED` | No all-state restore mechanism found. |
| Historical Clock | `IMPLEMENTATION_REQUIRED` | `--business-date`/`--evaluation-time` exist, but current UTC/today dependencies remain. |
| Historical Simulated Broker | `IMPLEMENTATION_REQUIRED` | Lower-level seams exist, but normal CLI cannot replace Broker boundary for historical mode. |
| Public Report Optional | `IMPLEMENTATION_REQUIRED` | Report/public/payload generation is not fully optional. |
| Runtime Mainline | `IMPLEMENTATION_REQUIRED` | Mainline components exist, but not runnable historically without missing prerequisites. |
| Look-ahead Prevention | `IMPLEMENTATION_REQUIRED` | Candidate leakage checks exist; no full Phase16 point-in-time audit exists. |
| Replay Readiness | `IMPLEMENTATION_REQUIRED` | Blocked by Reset, Clock, Broker, Public output, Mainline, and Look-ahead gaps. |

## Final Judgment

`PHASE16_B_PREREQUISITES_IMPLEMENTATION_REQUIRED`

Next Prefix: `Phase16-C`

Phase16-C should implement only the missing prerequisites. Reset and Historical Runtime Test must not start until those prerequisites pass.
