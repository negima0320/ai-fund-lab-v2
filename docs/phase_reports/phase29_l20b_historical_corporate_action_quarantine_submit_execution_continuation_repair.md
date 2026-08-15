# Phase29-L20B - Historical Corporate Action Quarantine Submit-to-Execution Continuation Repair

Task ID: Phase29-L20B

Mode:

```text
IMPLEMENTATION + SHORT REGRESSION
NO CURRENT HALTED RUN MUTATION
NO HISTORICAL EXECUTION
NO RESUME / FRESH-RUN / ABANDON / REPAIR COMMAND
```

## Primary Judgment

```text
PHASE29_L20B_HISTORICAL_CA_QUARANTINE_EXECUTION_NO_SUBMITTED_ORDERS_AUTHORITY_IMPLEMENTED_SHORT_REGRESSION_PASS_RESUME_BASELINE_NOT_READY
```

L20B repaired the Phase29-L20A Submit -> Execution propagation gap by teaching
Execution to consume the existing run-scoped
`corporate_action_symbol_quarantine_continuation.json` as a strict
Historical-only no-submitted-orders authority when, and only when, no orders
were submitted.

Corporate Action itself remains `REVIEW_REQUIRED`. Production and Demo
fail-closed semantics are unchanged.

## Root Cause Carried Forward

L20A root cause is unchanged:

```text
Submit classified 76920 BUY as COMPLETED_WITH_SYMBOL_QUARANTINE, but Execution
did not consume that scoped completion as no-submitted-orders authority and
therefore entered EXECUTE / orderlist_required.
```

L19 Strategy causality remains:

```text
UNRELATED
```

## Design

No new authority artifact was added. L20B reuses the existing formal Runtime
Test artifact:

```text
reports/runtime_tests/runs/<run_id>/daily/<business_date>/submit/corporate_action_symbol_quarantine_continuation.json
```

Execution now resolves a Historical quarantine no-submitted-orders authority
before the ordinary pending-empty no-action path:

```text
Submit scoped quarantine completion
→ Historical-only no-submitted-orders authority
→ Execution NO_ACTION
→ orderlist_required = false
→ fill_count = 0
→ no Ledger / Current mutation from imaginary fills
```

If submitted orders exist, the quarantine path is not used and Execution keeps
the normal orderlist requirement.

## Exact Acceptance Conditions

Execution accepts Historical quarantine continuation only when all of these are
true:

```text
mode / submit manifest indicates Historical
same business_date submit manifest exists
submitted_count == 0
blocked_count > 0
pending_item_count > 0
submit final_state == REVIEW_REQUIRED
submit exit_code != 0
no broker write / no external delivery / no demo or production submit
continuation artifact exists
continuation status == COMPLETED_WITH_SYMBOL_QUARANTINE
continuation business_date matches
continuation job == submit
continuation scope == CORPORATE_ACTION_SYMBOL_ONLY
production_applicability == NEVER
corporate_action_run_continuation_eligibility == ALLOWED_FOR_HISTORICAL_REPLAY_ONLY
affected_symbols is non-empty
all pending submit guard items are Corporate Action quarantine blocked
no generic REVIEW_REQUIRED is mixed in
classifier checks in continuation artifact all pass
continuation runtime_manifest_path binds to the same submit evidence path/copy
```

## Changed Files

```text
src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py
tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py
docs/phase_reports/phase29_l20b_historical_corporate_action_quarantine_submit_execution_continuation_repair.md
```

Existing prior-task report still present:

```text
docs/phase_reports/phase29_l20a_20220928_historical_corporate_action_submit_execution_halt_root_cause_audit.md
```

## Execution Behavior

Quarantine-only BUY:

```text
PASS-equivalent Execution NO_ACTION
orderlist_required = false
submitted_order_count = 0
fill_count = 0
no ledger order/execution append
no Current apply
Corporate Action remains REVIEW_REQUIRED in submit/quarantine evidence
```

Quarantine-only SELL:

```text
Same strict Historical-only NO_ACTION continuation as BUY.
SELL is not fail-opened; unresolved Corporate Action remains quarantined and not submitted.
```

Mixed quarantine + executable:

```text
Not converted to NO_ACTION.
submitted_count > 0 makes quarantine no-submitted authority NOT_APPLICABLE.
Execution keeps EXECUTE and orderlist_required = true.
```

Generic REVIEW_REQUIRED:

```text
Not converted to NO_ACTION.
Execution continues to fail closed when orderlist evidence is missing.
```

Real submitted order:

```text
Orderlist evidence remains required.
Existing normal Historical submitted-order execution test still passes.
```

Ordinary NO_ACTION:

```text
Existing NO_ACTION / NO_SUBMISSION_REQUIRED behavior preserved.
```

## Production Safety

Production/Demo unresolved Corporate Action behavior was not changed. The new
resolver is guarded by `mode == "historical"` and requires a Runtime Test
quarantine continuation artifact with:

```text
production_applicability = NEVER
corporate_action_run_continuation_eligibility = ALLOWED_FOR_HISTORICAL_REPLAY_ONLY
```

No Submit pipeline Corporate Action status was downgraded from
`REVIEW_REQUIRED` to `PASS`.

## Strategy Impact

```text
NO STRATEGY SEMANTIC CHANGE
```

Unchanged:

```text
Phase29-L19 Strategy: NONE
Portfolio Construction: unchanged
Position Sizing: unchanged
BUY_NEW / BUY_ADD / ADD: unchanged
SELL / REDUCE / EXIT: unchanged
Market Context / Portfolio Policy / thresholds: unchanged
```

## Pending / Terminalization Review

L20B does not redesign Pending lifecycle. For quarantine-only submitted-count
zero cases, Execution records no fills and no pending mutation:

```text
pending_terminalization_status = ALREADY_TERMINAL
pending_consumed = false
pending_mutated = false
```

If a stronger quarantine-specific pending terminal state is required, that is a
follow-up observability/lifecycle contract question, not necessary for the
L20B root-cause repair.

## Regression Results

Focused L20B / Execution no-action and orderlist behavior:

```text
PYTHONPATH=src:. python3 -m pytest -q tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py -k 'phase29_l20b or phase17_bg_empty_no_action_execution_is_terminal_pass_without_writes or active_pending_with_missing_orderlist or real_order_with_missing_orderlist or real_order_execution_path_still_passes'
8 passed, 5 deselected
```

Corporate Action quarantine + Execution + Historical submit regression:

```text
PYTHONPATH=src:. python3 -m pytest -q tests/runtime_v2/test_phase29_l9_historical_ca_quarantine_continuation.py tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py
31 passed
```

L19 Strategy focused regression:

```text
PYTHONPATH=src:. python3 -m pytest -q tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py -k phase29_l19
6 passed, 143 deselected
```

L7 SELL quantity + CA quarantine + Execution regression:

```text
PYTHONPATH=src:. python3 -m pytest -q tests/runtime_v2/test_phase29_l7_sell_quantity_contract_materialization.py tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py tests/runtime_v2/test_phase29_l9_historical_ca_quarantine_continuation.py
31 passed
```

Compile:

```text
PYTHONPATH=src:. PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py
PASS
```

Diff check:

```text
git diff --check
PASS
```

## Current Run Mutation

```text
NO
```

This task did not run or mutate:

```text
runtime-test-historical-smoke-20260811T055746254454Z
```

## Long Historical Executed

```text
NO
```

No `fresh-run`, `resume`, `run`, `abandon`, `repair`, `reset`, 20BD, 100BD,
1-year, or 4-year Historical command was executed.

## Resume Assessment

```text
NOT_READY
```

Execution root-cause readiness:

```text
The halted job is 2022-09-28:execution.
The 2022-09-28 submit job is already recorded as COMPLETED_WITH_SYMBOL_QUARANTINE.
L20B can consume existing submit quarantine evidence without re-running submit.
```

Runner baseline readiness:

```text
NOT READY as-is.
```

Evidence:

```text
run_state.source_baseline.source_commit = 1db2ce8b80b8356e086ce878f2a4bd3ee081f871
current source_commit = 54f91f8edb8562a40ba1d4681babf9adbfa3dec4
run_state.source_baseline.source_dirty = true
current source_dirty = true
run_state.source_baseline.registry_hash = c92ce01a6dc5562baada4d26eacdc102b49d74cc79eef9f4aebe121a0244868d
current registry_hash = c92ce01a6dc5562baada4d26eacdc102b49d74cc79eef9f4aebe121a0244868d
run_state.source_baseline.accepted_artifact_hash = 35f5d2c734196133d7b784fbc8c2f423911d9b9fe08671494898414268165461
current accepted_artifact_hash = 35f5d2c734196133d7b784fbc8c2f423911d9b9fe08671494898414268165461
```

`scripts/runtime_test.py::resume_command` rejects resume when any of
`source_commit`, `source_dirty`, or `registry_hash` differs. Therefore the
current run is not declared resume-ready as-is, even though the Execution
consumer repair itself is in place.

## User Command

Recommended first operator check, after deciding how to handle the source
baseline mismatch:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py resume --profile historical-smoke --run-id runtime-test-historical-smoke-20260811T055746254454Z --dry-run --json
```

Do not run actual resume until the dry-run result is reviewed. If dry-run
reports the expected source baseline mismatch, choose an explicit operator
decision path before continuing; do not bypass the baseline guard silently.

Actual resume command, only after dry-run is accepted:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py resume --profile historical-smoke --run-id runtime-test-historical-smoke-20260811T055746254454Z --confirm --yes-i-understand-this-mutates-trading-state
```

## Required Final Fields

```text
Primary Judgment:
PHASE29_L20B_HISTORICAL_CA_QUARANTINE_EXECUTION_NO_SUBMITTED_ORDERS_AUTHORITY_IMPLEMENTED_SHORT_REGRESSION_PASS_RESUME_BASELINE_NOT_READY

Root Cause carried forward:
YES

Submit-to-Execution propagation gap repaired:
YES

Explicit Historical scoped quarantine Execution authority:
YES

New duplicate authority artifact introduced:
NO

Existing quarantine artifact reused:
YES

Corporate Action REVIEW_REQUIRED converted to PASS:
NO

Production fail-closed weakened:
NO

Demo fail-closed weakened:
NO

Quarantine-only BUY:
PASS

Quarantine-only SELL:
PASS

Mixed quarantine + executable:
EXECUTE_PATH_PRESERVED

Generic REVIEW_REQUIRED:
FAIL_CLOSED_PRESERVED

Real submitted order + missing orderlist:
REVIEW_REQUIRED_PRESERVED

Ordinary NO_ACTION:
PASS_PRESERVED

Quarantined symbol fake fill generated:
NO

Strategy semantic change:
NO

L19 impact:
NONE

ADD weakened:
NO

SELL / REDUCE / EXIT changed:
NO

Focused regression:
PASS

Current halted run mutated:
NO

Long Historical executed:
NO

Resume assessment:
NOT_READY due source_commit baseline mismatch; execution repair itself can consume existing submit quarantine evidence
```
