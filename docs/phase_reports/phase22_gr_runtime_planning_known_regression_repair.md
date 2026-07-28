# Phase22-GR Runtime Planning Known Regression Repair

## Primary Judgment

`PHASE22_GR_RUNTIME_PLANNING_REGRESSIONS_REPAIRED`

Both known Runtime regressions reproduced during Phase22-G are repaired with Production-common Runtime contract changes. Phase22 Strategy artifacts remain unconnected and `NOT_ELIGIBLE`; no Runtime switch or legacy retirement was performed.

## Regression GR-1 Root Cause

`test_phase14e36_morning_uses_selected_carryover_feature_date` failed with `StopIteration` because `morning_ai_planning_pending_pipeline` was absent from the manifest. The upstream reason was `consumer_schema_review_required:pm`.

Root cause:

- Data Readiness used all-consumer feature readiness for `morning`, so PM schema review blocked BUY Planning even though PM feature schema is not a BUY Planning input.
- After Data Readiness was made scope-aware, the Morning pipeline itself still treated PM-only schema review as blocking.
- The CLI only appends the Morning Planning stage when the run reaches that stage, so early `REVIEW_REQUIRED` caused a complete stage absence.

## Regression GR-2 Root Cause

`test_phase15h_cli_manifest_emits_explicit_policy_fields` failed with sell planning CLI `exit_code=20`.

Root cause:

- `sell_planning` with explicit `--pm-opportunity-path` / `--pm-feature-path` still inherited `selected_feature_date` from the default operations feature-date contract.
- In isolated/runtime test contexts, that default contract could resolve to stale `.runtime/operations` evidence, causing PM target-date mismatch.
- Phase15-H and Phase14-E50 PM fixture helpers also used old PM feature columns and no longer matched the current Production PM input contract.

## Shared / Separate Cause

Separate root causes. Both surfaced as `exit_code=20` before Planning stage execution, but GR-1 was a Morning BUY scope-readiness bug, while GR-2 was sell explicit PM input feature-date authority plus fixture contract drift.

## Call Graph

CLI `main` resolves environment, policy, safety, preflight, runtime state, Data Readiness, then job-specific producers:

- Morning: Data Readiness -> BUY AI -> Morning capability -> `run_morning_ai_planning_pending_pipeline` -> Pending -> manifest -> exit code.
- Sell Planning: Data Readiness -> SELL capability -> PM producer -> `run_sell_planning_pending_pipeline` -> Pending composition -> manifest -> exit code.

## Stage Contract

- `runtime_data_readiness_gate` is emitted before Planning.
- `morning_ai_planning_pending_pipeline` is emitted when Morning data readiness, BUY AI, and capability permit Planning.
- `sell_planning_pending_pipeline` is emitted when sell data readiness, PM producer, and capability permit Planning.
- Missing policy remains a guarded pre-Planning `REVIEW_REQUIRED`; that behavior was preserved.

## Exit Code Contract

Unchanged:

- `0`: success
- `10`: blocked
- `20`: review required
- `30`: halt
- `40`: config error
- `70`: unexpected error

## Files Changed

- `src/ai_fund_lab_v2/runtime_v2/data_readiness.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py`
- `tests/runtime_v2/test_phase15h_capital_deployment_policy.py`
- `tests/runtime_v2/test_phase14e50_sell_planning_runtime_connection.py`
- `tests/runtime_v2/test_phase22_gr_runtime_planning_regression_repair.py`
- `docs/phase_reports/phase22_gr_runtime_planning_known_regression_repair.md`
- `reports/phase22_gr_runtime_planning_known_regression_repair/`

## Fix Description

Data Readiness now evaluates feature schema readiness by scope. Morning BUY readiness requires candidate and opportunity schema readiness, not PM schema readiness. Sell Planning with explicit PM input paths now uses the business date as PM feature-date authority unless a CLI feature date is explicitly provided, avoiding stale default feature contracts.

Morning Planning now applies the same BUY-scope feature contract when PM-only schema review is present but candidate and opportunity schemas are ready.

Phase15-H and Phase14-E50 PM fixtures were updated to the current Production PM input schema.

## Why Production-common

The fixes are in Runtime Data Readiness and Morning Planning, not in test assertions. They apply to Demo, Production-compatible regular runtime, and Historical paths using the same scope and explicit-input authority rules.

## Why Not Test-specific

No test was weakened, renamed, or changed to accept `exit_code=20`. The failing tests now pass because the runtime reaches the expected Planning stages under valid inputs.

## Behavior Preservation

Candidate output, Opportunity output, PM decision logic, Capital Deployment values, REDUCE quantity authority, EXIT full-position authority, Pending composition, Submit guards, Execution, Ledger, and Current behavior were not changed.

## Tests

- `tests/runtime_v2/test_phase14e36_feature_date_contract_carryover_policy.py`: 3 passed
- `tests/runtime_v2/test_phase15h_capital_deployment_policy.py`
  plus PM/sell surrounding tests: 13 passed
- GR contract tests plus surrounding tests: 18 passed
- Phase22 A-G plus selected Runtime short suite plus GR: 123 passed
- `compileall`: PASS with `PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_v2_pycache`

## Long Tests Not Executed

No 5BD, 20BD, 200BD, 1-year, 3-year, or long runtime smoke tests were run.

## Remaining Gaps

No blocking or non-blocking gap remains for Phase22-GR.

## Phase22-H Entry Judgment

Phase22-H entry ready: `YES`.

Runtime switch ready: `NO`.

Legacy retirement ready: `NO`.
