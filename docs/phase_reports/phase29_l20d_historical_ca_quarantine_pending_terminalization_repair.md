# Phase29-L20D - Historical Corporate Action Quarantine Pending Terminalization Repair

Task ID: Phase29-L20D

Mode:

```text
DESIGN + IMPLEMENTATION + SHORT REGRESSION + CONTINUATION ASSESSMENT
NO CURRENT HALTED RUN MUTATION
NO RESUME / FRESH-RUN / RUN / REPAIR / CURRENT-RUN PENDING_LIFECYCLE COMMAND
NO LONG HISTORICAL EXECUTION
```

## Primary Judgment

```text
PHASE29_L20D_HISTORICAL_CA_QUARANTINE_PENDING_TERMINALIZATION_IMPLEMENTED_SHORT_REGRESSION_PASS_FRESH_RUN_RECOMMENDED
```

## Root Cause Carried Forward

L20C root cause remains confirmed:

```text
HISTORICAL_CA_QUARANTINE_PENDING_NOT_TERMINALIZED_AND_CARRIED_AS_STALE_APPROVED_PENDING
```

The stale 2022-09-29 Pending was the 2022-09-28 `76920 BUY 2000`
Corporate Action quarantined item. L20D repairs the missing Pending lifecycle
bridge.

## Final Design

Strict Historical CA quarantine lifecycle:

```text
APPROVED Pending
-> Submit REVIEW_REQUIRED / NOT_SUBMITTED due historical_corporate_action_symbol_quarantine
-> corporate_action_symbol_quarantine_continuation.json proves Historical-only continuation
-> no broker write / no submitted order / no unknown outcome
-> Pending lifecycle owns APPROVED -> EXPIRED
-> history retains original Pending and quarantine authority
-> current Pending slot becomes EMPTY
```

Data Readiness and Safety were not weakened.

## Selected Terminal State

Selected state:

```text
EXPIRED
```

Reason:

```text
Existing Pending lifecycle already defines APPROVED -> EXPIRED and then current slot -> EMPTY for stale/non-retryable Pending with no submit attempt.
```

No new state was introduced.

## Eligibility Conditions

The new terminalization bridge requires all of these:

```text
mode == historical
Pending state == APPROVED
Pending is unconsumed
Pending target_session_date == business_date
Pending has items
latest same-day submit manifest exists
submit manifest is Historical
continuation artifact exists
continuation status == COMPLETED_WITH_SYMBOL_QUARANTINE
scope == CORPORATE_ACTION_SYMBOL_ONLY
production_applicability == NEVER
corporate_action_run_continuation_eligibility == ALLOWED_FOR_HISTORICAL_REPLAY_ONLY
affected symbol matches Pending symbol
submitted_count == 0
blocked_count matches Pending item count
all Pending items are blocked by corporate_action_event_not_resolved
violated_policy == historical_corporate_action_symbol_quarantine
no generic REVIEW_REQUIRED mixed in
submit final_state == REVIEW_REQUIRED
submit exit_code != 0
no broker_write / external_delivery / demo submit / production submit
continuation manifest binding is valid
classifier checks all PASS
unknown_submit_risk == false
```

## Changed Files

```text
src/ai_fund_lab_v2/runtime_v2/pending/lifecycle_runner.py
src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py
tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py
tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py
docs/phase_reports/phase29_l20d_historical_ca_quarantine_pending_terminalization_repair.md
```

Pre-existing L20A/L20B/L20C report files remain untracked in this worktree.

## Quarantine-only BUY Result

Implemented and tested:

```text
76920 BUY 2000
Corporate Action REVIEW_REQUIRED preserved
NOT_SUBMITTED authority required
no broker write
no fill
Pending -> EXPIRED
history retained
current slot -> EMPTY
```

## Quarantine-only SELL Result

Implemented and tested:

```text
76920 SELL 700
same strict Historical-only terminalization
no SELL fail-open
no REDUCE / EXIT semantic change
```

## Mixed Case Result

Mixed submitted-count cases are not whole-plan terminalized.

Current architecture does not safely item-terminalize a mixed Pending plan in
this repair. If an executable item was submitted, Pending lifecycle preserves
fail-closed behavior through unknown submit risk / review instead of converting
the whole plan to `EMPTY`.

Execution L20B behavior remains:

```text
submitted_count > 0 -> EXECUTE path remains orderlist_required
```

Remaining limitation:

```text
item-scoped Pending terminalization for mixed quarantine + executable plans remains future work.
```

## Generic Stale Pending Result

Preserved:

```text
generic stale APPROVED Pending -> REVIEW_REQUIRED in Data Readiness
generic stale APPROVED Pending -> EXPIRED only via existing pending_lifecycle stale rules
```

No global Historical stale Pending ignore was added.

## Unknown Submit Outcome Result

Preserved:

```text
POST_SEND_UNKNOWN / broker request attempted / submitted_count > 0
-> REVIEW_REQUIRED
-> active slot retained
```

No automatic expiration occurs under unknown submit risk.

## Next-day Data Readiness Result

Tested with terminalized CA quarantine Pending:

```text
current slot EMPTY
pending_status READY
stale_approved_pending_exists absent
```

Historical Safety mismatch disappears because the old Pending is no longer an
active stale `APPROVED` Pending, not because Safety was weakened.

## L20B Evidence Correction

Execution no-action evidence is narrowed:

```text
genuinely empty/no-action terminal Pending -> ALREADY_TERMINAL
active APPROVED quarantine Pending with items -> PENDING_LIFECYCLE_REQUIRED
```

Execution no longer claims `ALREADY_TERMINAL` for the active quarantine Pending
case that L20C proved was not terminal.

## Production / Demo Safety

Production/Demo unresolved Corporate Action remains fail-closed:

```text
REVIEW_REQUIRED -> no Historical quarantine terminalization
```

The new terminalization bridge is guarded by `mode == historical` and by the
Historical-only continuation artifact.

## Strategy Impact

```text
NO STRATEGY SEMANTIC CHANGE
```

Explicit impact:

```text
L19 impact: NONE
ADD impact: NONE
BUY_NEW impact: NONE
BUY_ADD impact: NONE
SELL / REDUCE / EXIT impact: NONE
Portfolio Construction: unchanged
Position Sizing: unchanged
thresholds/model/scaler/calibration/Accepted Generation: unchanged
```

## Regression Results

```text
PYTHONPATH=src:. python3 -m pytest -q tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py -k 'phase29_l20d or phase15ar_stale_approved_pending_expires_to_history_and_empty_slot or phase15ar_unknown_submit_attempt_moves_to_review_required_not_empty or phase15ar_data_readiness_pending_ready_after_expiration'
8 passed, 8 deselected
```

```text
PYTHONPATH=src:. python3 -m pytest -q tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py -k 'phase29_l20b or phase17_bg_empty_no_action_execution_is_terminal_pass_without_writes or active_pending_with_missing_orderlist or real_order_with_missing_orderlist or real_order_execution_path_still_passes'
8 passed, 5 deselected
```

```text
PYTHONPATH=src:. python3 -m pytest -q tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py
16 passed
```

```text
PYTHONPATH=src:. python3 -m pytest -q tests/runtime_v2/test_phase29_l9_historical_ca_quarantine_continuation.py tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py
21 passed
```

```text
PYTHONPATH=src:. python3 -m pytest -q tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py -k phase29_l19
6 passed, 143 deselected
```

```text
PYTHONPATH=src:. PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/pending/lifecycle_runner.py src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py
PASS
```

```text
git diff --check
PASS
```

## Current Run Mutation

```text
NO
```

The current halted run was inspected read-only only.

## Long Historical Executed

```text
NO
```

No 20BD, 100BD, 1-year, 4-year, `fresh-run`, `resume`, or Historical `run`
was executed by Codex.

## Continuation Assessment

```text
FRESH_RUN_RECOMMENDED
```

Read-only current run assessment:

```text
run_id: runtime-test-historical-smoke-20260811T074704995096Z
status: HALT
halted_at: 2022-09-29:data_readiness
current Pending: 2022-09-28 76920 BUY 2000 remains APPROVED / unconsumed
```

An existing stale Pending would require explicit operator state mutation before
continuation. L20D also changes source semantics after the run halted. A fresh
run is cleaner and provenance-safe.

## User Next Step

User-operated fresh 4-year Historical validation command:

```bash
PYTHONPATH=src:. python3 scripts/runtime_test.py fresh-run --profile historical-smoke --start-date 2022-08-10 --end-date 2026-08-09 --initial-cash 1000000 --confirm --yes-i-understand-this-mutates-trading-state --json
```

Codex did not execute this command.
