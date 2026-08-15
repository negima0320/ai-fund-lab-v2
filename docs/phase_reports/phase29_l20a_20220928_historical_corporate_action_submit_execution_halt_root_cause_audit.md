# Phase29-L20A - 2022-09-28 Historical Corporate Action / Submit / Execution HALT Root Cause Audit

Task ID: Phase29-L20A

Mode:

```text
READ_ONLY ROOT CAUSE AUDIT
NO REPAIR
NO HISTORICAL EXECUTION
NO RUNTIME / PENDING / LEDGER / CURRENT / BROKER MUTATION
```

Run:

```text
runtime-test-historical-smoke-20260811T055746254454Z
```

Business date:

```text
2022-09-28
```

## Primary Judgment

```text
PHASE29_L20A_HISTORICAL_CA_QUARANTINE_SUBMIT_CLASSIFIED_BUT_EXECUTION_NO_ACTION_CONSUMER_PROPAGATION_MISSING_SECONDARY_ORDERLIST_HALT
```

The direct HALT occurred in `execution` with `orderlist evidence missing`.
The upstream root cause is not Phase29-L19 Strategy behavior. It is a
Historical Runtime continuation propagation gap: `submit` correctly classified
the unresolved Corporate Action as
`COMPLETED_WITH_SYMBOL_QUARANTINE` for symbol `76920`, but the following
Execution step did not consume that scoped quarantine completion as an
authoritative no-submitted-orders / no-action execution condition.

Production Corporate Action fail-closed semantics remain correct and must not
be weakened.

## Direct HALT Cause

Direct HALT:

```text
job = execution
runtime_cli_exit_code = 20
runner_final_exit_code = 30
root_reason = orderlist evidence missing
```

Evidence:

```text
reports/runtime_tests/runs/runtime-test-historical-smoke-20260811T055746254454Z/daily/2022-09-28/execution/runtime_manifest.json
reports/runtime_tests/runs/runtime-test-historical-smoke-20260811T055746254454Z/daily/2022-09-28/execution/execution_normalization_evidence.json
reports/runtime_tests/runs/runtime-test-historical-smoke-20260811T055746254454Z/daily/2022-09-28/execution/submitted_order_authority.json
reports/runtime_tests/runs/runtime-test-historical-smoke-20260811T055746254454Z/daily/2022-09-28/execution/historical_fill_authority.json
```

Observed Execution fields:

```text
execution_action = EXECUTE
orderlist_required = true
orderlist_status = MISSING
submitted_order_count = 0
status = REVIEW_REQUIRED
reason = orderlist evidence missing
```

This is the immediate Runtime CLI failure. It is not the primary upstream
business cause.

## Upstream Root Cause

Submit already reached the expected Historical symbol-scoped quarantine
classification:

```text
submit runtime_cli_exit_code = 20
runtime_test_job_status = COMPLETED_WITH_SYMBOL_QUARANTINE
quarantined_symbols = [76920]
```

Run-state evidence:

```text
reports/runtime_tests/runs/runtime-test-historical-smoke-20260811T055746254454Z/run_state.json
```

The run_state contains completed 2022-09-28 jobs:

```text
market_refresh: exit_code 0
data_readiness: exit_code 0
morning: exit_code 0
sell_planning: exit_code 0
submit: exit_code 20, runtime_test_job_status COMPLETED_WITH_SYMBOL_QUARANTINE
execution: exit_code 20, HALT
```

The missing propagation is between:

```text
Submit scoped quarantine completion
↓
Execution no-submitted-orders/no-action authority
```

Execution only recognizes ordinary `NO_ACTION` / `NO_SUBMISSION_REQUIRED`
submit authority, not a submit job completed with all submitted orders
withheld by symbol-scoped Corporate Action quarantine.

## Corporate Action Symbol

Corporate Action target symbol:

```text
76920
```

It is not `96100`.

Submit evidence:

```text
pending_item_id = strategy-5f8ac0fb93175fd7db47
symbol = 76920
side = BUY
quantity = 2000
submit_item_status = REVIEW_REQUIRED
guard_decision = BLOCKED
guard_reason = corporate_action_event_not_resolved
blocked_at_submit_reason = corporate_action_event_not_resolved
violated_policy = historical_corporate_action_symbol_quarantine
corporate_action_event_status = IMPACT_DETECTED
corporate_action_adjustment_authority_status = REVIEW_REQUIRED
corporate_action_adjustment_authority_reason = corporate_action_event_not_resolved
corporate_action_quarantine_status = QUARANTINED
submitted_count = 0
blocked_count = 1
submit_action = NO_SUBMIT_ATTEMPTED
```

Quarantine continuation evidence:

```text
status = COMPLETED_WITH_SYMBOL_QUARANTINE
scope = CORPORATE_ACTION_SYMBOL_ONLY
affected_symbols = [76920]
corporate_action_quarantine_status = QUARANTINED
corporate_action_run_continuation_eligibility = ALLOWED_FOR_HISTORICAL_REPLAY_ONLY
production_applicability = NEVER
portfolio_performance_limitation_status = REVIEW_REQUIRED
```

Artifact:

```text
reports/runtime_tests/runs/runtime-test-historical-smoke-20260811T055746254454Z/daily/2022-09-28/submit/corporate_action_symbol_quarantine_continuation.json
```

## 96100 SELL Relationship

The 2022-09-28 morning evidence contains a `96100` SELL feasibility PASS:

```text
symbol = 96100
side = SELL
quantity = 700
status = PASS
reason = sell_exposure_reducing_submit_feasibility_not_blocked_by_buy_dynamic_exposure
```

However, the submit pending plan for 2022-09-28 contains one item, and that
item is `76920` BUY. The submit guard evidence contains no `96100` item.

Therefore:

```text
96100 was not the Corporate Action quarantine target.
96100 was not the item blocked at submit.
96100 did not directly cause the execution HALT.
```

This audit does not reinterpret SELL authority. BUY/SELL independence remains:
SELL should not be blocked by BUY-side review unless a SELL-specific authority
requires it. The observed HALT is not evidence of a SELL contract failure for
`96100`.

## Quarantine Contract

The Phase29-L9/L11 contract is:

```text
Corporate Action unresolved
→ Runtime submit remains REVIEW_REQUIRED / non-zero
→ Runtime Test runner may classify the strict Historical-only submit pattern as COMPLETED_WITH_SYMBOL_QUARANTINE
→ affected symbol is QUARANTINED / NOT_SUBMITTED-equivalent
→ unrelated symbols may continue through normal submit guards
→ Production / Demo remain fail-closed
```

Sources:

```text
docs/phase_reports/phase29_l9_historical_corporate_action_symbol_quarantine_implementation.md
docs/phase_reports/phase29_l10_l9_real_run_corporate_action_continuation_failure_audit.md
docs/phase_reports/phase29_l11_historical_corporate_action_real_payload_continuation_repair.md
src/ai_fund_lab_v2/runtime_v2/historical_support/corporate_action_quarantine.py
scripts/runtime_test.py
src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py
```

Important: this is not `REVIEW_REQUIRED -> PASS` for Corporate Action. It is a
Historical Runtime Test continuation classification with explicit
`portfolio_performance_limitation_status = REVIEW_REQUIRED`.

## Authority Trace

Producer / detector:

```text
src/ai_fund_lab_v2/runtime_v2/corporate_action_adjustment.py
reason = corporate_action_event_not_resolved
status = REVIEW_REQUIRED
```

Historical quarantine registry:

```text
src/ai_fund_lab_v2/runtime_v2/historical_support/corporate_action_quarantine.py
registry = .runtime/runtime_state/corporate_action_quarantine/historical_symbol_registry.json
status = QUARANTINED
production_applicability = NEVER
```

Submit consumer:

```text
src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py
unresolved_corporate_action_quarantine_entry(runtime_root, item.symbol)
→ _blocked_guard_evidence(...)
→ violated_policy = historical_corporate_action_symbol_quarantine
→ submit item REVIEW_REQUIRED / NOT_SUBMITTED
```

Runtime Test classifier:

```text
scripts/runtime_test.py::classify_historical_corporate_action_quarantine_result
→ validates strict Historical submit REVIEW_REQUIRED pattern
→ writes corporate_action_symbol_quarantine_continuation.json when persist=True
→ job_record.runtime_test_job_status = COMPLETED_WITH_SYMBOL_QUARANTINE
```

Runner progression:

```text
scripts/runtime_test.py run/resume loop
if completed.returncode != 0 and scoped_block exists:
    do not mark run HALT for submit
    continue to next job
```

Missing consumer:

```text
src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py
_resolve_no_action_execution_authority()
_load_submit_no_action_authority()
```

Execution recognizes ordinary no-action submit authority only when the submit
manifest is internally PASS-like:

```text
exit_code = 0
pending_item_count = 0
submitted_count = 0
blocked_count = 0
review_required = false
submit_action in {NO_ACTION, NO_SUBMISSION_REQUIRED}
```

The 2022-09-28 quarantine submit manifest is intentionally not that:

```text
exit_code = 20
final_state = REVIEW_REQUIRED
pending_item_count = 1
submitted_count = 0
blocked_count = 1
review_required = true
submit_action = NO_SUBMIT_ATTEMPTED
```

So execution does not treat the day as no-submitted-orders. It enters the
normal `EXECUTE` path, requires orderlist evidence, sees none, and returns
`REVIEW_REQUIRED`.

## Execution Causality

Classification:

```text
orderlist evidence missing = SECONDARY
```

Detailed classification:

```text
A. Primary defect: NO
B. Submit REVIEW_REQUIRED expected downstream consequence: PARTIAL
C. Historical continuation defect secondary symptom: YES
D. Evidence materialization defect: PARTIAL
E. Independent Runtime defect: NO
```

Explanation:

`orderlist evidence missing` is expected for a day with no submitted orders, but
Execution did not receive an accepted no-action authority for the quarantine
case. The issue is not that a real orderlist was unexpectedly missing for a
valid submitted order; the issue is that submit-quarantine completion was not
propagated into Execution's no-submitted-orders authority.

## Strategy Causality

Phase29-L19 Strategy causal relationship:

```text
UNRELATED
```

Evidence:

```text
Strategy produced a BUY_NEW candidate for 76920 with executable quantity.
Submit blocked it because of Historical Corporate Action quarantine.
The HALT occurs after Strategy/Planning, at Submit/Execution continuation propagation.
```

This is not evidence that L19 cap-constrained lot floor or residual
reallocation is incorrect. L19 should not be rolled back for this HALT.

## Production Safety Impact

Production fail-closed should not be weakened.

Production/Demo behavior remains:

```text
Unresolved Corporate Action
→ REVIEW_REQUIRED
→ no automatic submit
```

The required repair, if accepted, should be Historical Runtime Test continuation
only: after a strict submit quarantine classification with zero submitted
orders, Execution should consume an explicit scoped no-submitted-orders
authority without requiring broker orderlist evidence. It must not turn
unresolved Corporate Action into PASS.

## Regression Assessment

```text
Regression confirmed: NOT PROVEN
Prior partial implementation: YES
Missing propagation gap: YES
Duplicate authority: NO
```

Lineage:

- Phase29-L9 implemented Historical symbol-scoped Corporate Action quarantine
  and submit classifier.
- Phase29-L10 found the first real-run classifier/payload-shape gap.
- Phase29-L11 repaired the real submit manifest classifier and added
  retrospective evidence-only repair support.
- Existing Execution no-action authority predates L9/L11 and only accepts
  ordinary no-action submit manifests.

No evidence was found that an L9/L11-equivalent execution continuation consumer
previously existed and was later removed. The evidence supports an incomplete
cross-stage propagation implementation rather than a proven regression.

## Existing Test Coverage

Covered:

```text
symbol-scoped quarantine classifier
real submit payload without item_results
generic REVIEW_REQUIRED rejection
Production context rejection
actual broker write rejection
persistent quarantine blocks same symbol
persistent quarantine does not block other symbols
SELL quarantined in submit guard fixture
ordinary empty pending + NO_ACTION execution PASS
active/real pending with missing orderlist REVIEW_REQUIRED
real submitted historical order execution PASS
run-scoped execution evidence for ordinary NO_ACTION
```

Missing:

```text
quarantine-only submit with submitted_count=0 followed by execution continuation
COMPLETED_WITH_SYMBOL_QUARANTINE consumed by execution as no-submitted-orders authority
quarantine-only pending item terminalization / empty transition before execution
mixed quarantined + executable orders followed by execution with only executable orderlist requirement
only quarantined BUY item end-to-end submit → execution
only quarantined SELL item end-to-end submit → execution
execution evidence materialization for scoped quarantine no-order day
runner run/resume test proving submit scoped quarantine does not later HALT execution
```

## Repair Required

```text
YES
```

Repair should be narrow and Historical Runtime continuation scoped.

Recommended minimal repair scope:

```text
1. Add an explicit submit-scoped quarantine no-submitted-orders authority artifact or manifest field.
2. Teach Execution no-action authority resolution to accept that strict artifact only in historical mode.
3. Keep orderlist required for real submitted orders and for generic REVIEW_REQUIRED.
4. Preserve Production/Demo fail-closed.
5. Add tests for quarantine-only BUY, quarantine-only SELL, mixed quarantine + submitted orders, and runner progression.
```

Do not repair by downgrading Corporate Action `REVIEW_REQUIRED` to `PASS`.

## Resume Assessment

```text
Resume theoretically possible after repair: YES
Fresh-run required now: NOT DETERMINED
```

Reasoning:

The submit job is already recorded in `run_state.json` as
`COMPLETED_WITH_SYMBOL_QUARANTINE`, and no broker write occurred. The halted
job is execution. A future repair may be able to resume from
`2022-09-28:execution` if it consumes the existing submit quarantine evidence
without re-running submit or mutating the existing evidence.

Actual resume was not executed in this task.

## Non-Mutation Assertion

This audit did not execute:

```text
fresh-run
resume
run
abandon
repair
reset
broker action
J-Quants fetch
long Historical
```

Changed files:

```text
docs/phase_reports/phase29_l20a_20220928_historical_corporate_action_submit_execution_halt_root_cause_audit.md
```

No Strategy, Runtime, Submit, Execution, config, schema, Pending, Ledger,
Current, Broker, Accepted Generation, model, calibration, or Historical run
state was changed.

## Required Final Fields

```text
Primary Judgment:
PHASE29_L20A_HISTORICAL_CA_QUARANTINE_SUBMIT_CLASSIFIED_BUT_EXECUTION_NO_ACTION_CONSUMER_PROPAGATION_MISSING_SECONDARY_ORDERLIST_HALT

Direct HALT Cause:
execution REVIEW_REQUIRED because orderlist evidence missing

Upstream Root Cause:
Historical Corporate Action quarantine submit completion was not propagated to Execution no-action / no-submitted-orders authority

Corporate Action Symbol:
76920

96100 causal:
NO

Quarantine status:
COMPLETED_WITH_SYMBOL_QUARANTINE / QUARANTINED / SYMBOL_ONLY

Submit status:
Runtime submit REVIEW_REQUIRED; Runtime Test submit job classified COMPLETED_WITH_SYMBOL_QUARANTINE

Expected status:
Affected symbol quarantined and not submitted; Historical run continuation allowed; Production/Demo fail-closed preserved

Actual status:
Submit continuation succeeded, then Execution HALTed on orderlist evidence missing

Execution orderlist evidence missing:
SECONDARY

Strategy L19 causality:
UNRELATED

Production fail-closed weakened:
NO

Regression confirmed:
NOT_PROVEN

Prior partial implementation:
YES

Missing propagation gap:
YES

Duplicate authority:
NO

Repair required:
YES

Recommended next task:
Phase29-L20B Historical Corporate Action Quarantine Submit-to-Execution Continuation Repair Design / Implementation

Current Historical run mutated:
NO

Historical executed:
NO

Fresh-run executed:
NO

Resume executed:
NO
```
