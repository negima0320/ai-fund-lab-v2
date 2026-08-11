# Phase29-L10 L9 Real-Run Corporate Action Continuation Failure Audit

Status:

```text
COMPLETE
READ_ONLY AUDIT
NO PRODUCTION CODE CHANGE
NO CONFIG CHANGE
NO SCHEMA CHANGE
NO RUNTIME / PENDING / LEDGER MUTATION
NO HISTORICAL EXECUTION
```

Primary Judgment:

```text
PHASE29_L10_L9_REAL_RUN_FAILURE_ROOT_CAUSE_IDENTIFIED_SOURCE_VERSION_AND_PAYLOAD_SHAPE_MISMATCH_NO_PRODUCTION_DEFECT
```

Real Run:

```text
run_id: runtime-test-historical-smoke-20260810T232622909184Z
halt_date: 2022-10-28
halt_job: submit
runtime_cli_exit_code: 20
runtime_cli_final_state: REVIEW_REQUIRED
runtime_test_final_judgment: HALT
completed_business_day_count: 53
```

Findings:

```text
The real submit payload is an eligible Corporate Action scenario at the guard
level: symbol 76920, SELL 700, submit_item_status REVIEW_REQUIRED,
guard_decision BLOCKED, guard_reason corporate_action_event_not_resolved,
blocked_at_submit_reason corporate_action_event_not_resolved, event_status
IMPACT_DETECTED, event_type UNKNOWN_ADJFACTOR_IMPACT, AdjFactor
0.3333333333333333, adjustment authority REVIEW_REQUIRED, submit_status
effectively NOT_SUBMITTED by blocked guard, and two unrelated BUY items
submitted.

However, the run did not produce
corporate_action_symbol_quarantine_continuation.json, did not set
runtime_test_job_status=COMPLETED_WITH_SYMBOL_QUARANTINE, and did not persist a
corporate_action_quarantine registry entry.

The recorded runtime_test_source_commit is
1db2ce8b80b8356e086ce878f2a4bd3ee081f871. That commit does not contain
src/ai_fund_lab_v2/runtime_v2/historical_support/corporate_action_quarantine.py
and scripts/runtime_test.py at that commit has only the BUY-only continuation
classifier. Therefore, if the run used the committed source state, the L9
classifier was not available and could not execute.

The run also had source_dirty=true, so an uncommitted worktree may have been in
play. Replaying the current L9 classifier against the real runtime_manifest
returns None because the real submit runtime_manifest does not contain top-level
item_results. The L9 unit fixture included item_results, so the classifier
predicate is overly strict for the real Runtime submit manifest shape.
```

Exact Failed Predicate:

```text
scripts/runtime_test.py classify_historical_corporate_action_quarantine_result:

guard_items = manifest.get("submit_guard_item_evidence")
item_results = manifest.get("item_results")
if not isinstance(guard_items, list) or not isinstance(item_results, list):
    return None

Real manifest:
submit_guard_item_evidence: list[3]
item_results: missing
pending_item_count: 3
submitted_count: 2
blocked_count: 1
```

Classification:

```text
classifier_wiring_defect: YES for recorded committed source; L9 classifier was absent
predicate_defect: YES for current L9 source; real payload lacks item_results
ordering_defect: NO; current L9 code classifies after evidence collection and before HALT conversion
evidence_shape_defect: YES; real submit manifest differs from L9 unit fixture
quarantine_registry_defect: NO; registry was never reached/persisted
submit_result_classification_defect: NO production submit behavior was correct fail-closed REVIEW_REQUIRED
production_defect: NO
historical_only_defect: YES
```

Safety:

```text
Production/Demo Corporate Action behavior remains fail-closed. No evidence
shows any Strategy, PM, ADD, BUY, or SELL decision semantic change. The failure
is confined to Historical Runtime Test continuation classification after a
correct Runtime CLI submit REVIEW_REQUIRED result.
```

Resume / Fresh-Run Assessment:

```text
Do not resume this halted run as-is. It already executed the 2022-10-28 submit
job far enough to submit two historical BUY items, while run_state did not mark
the submit job as a scoped continuation. A naive resume would treat the submit
job as incomplete and could re-enter submit handling.

Resume could become conditionally safe only after a future repair provides a
retrospective evidence-only classifier/repair path that marks the existing
2022-10-28 submit job completed with symbol quarantine without re-running
submit. Without that explicit repair, fresh-run remains required.
```

Validation:

```text
PYTHONPATH=src:. python3 -m pytest -q tests/runtime_v2/test_phase29_l9_historical_ca_quarantine_continuation.py tests/runtime_v2/test_phase29_l7_sell_quantity_contract_materialization.py
14 passed
```

Recommended Next Task:

```text
Phase29-L11: Repair Historical Corporate Action continuation classifier to use
the real submit runtime_manifest shape. It should derive blocked/not-submitted
item status from submit_guard_item_evidence plus submitted_count/blocked_count
when item_results is absent, add a real-payload fixture from
runtime-test-historical-smoke-20260810T232622909184Z, and optionally provide a
read-only retrospective classification command for the halted run without
re-running submit.
```

