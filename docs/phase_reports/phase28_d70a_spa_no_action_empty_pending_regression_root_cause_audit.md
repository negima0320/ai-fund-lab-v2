# Phase28-D70A SPA NO_ACTION / EMPTY Pending Regression Root Cause Audit

Primary Judgment:

```text
PHASE28_D70A_SPA_NO_ACTION_EMPTY_PENDING_REGRESSION_CLASSIFIED_CASE_C_STALE_TEST_FIXTURE_PRODUCTION_FAIL_CLOSED_PRESERVED
```

## Scope

This was a read-only root cause audit for one failing short regression:

```text
tests/runtime_v2/test_phase23_i_strategy_planning_authority.py::test_phase23_i_valid_no_action_remains_empty_pending_without_legacy_fallback
```

No implementation, config, schema, threshold, model, Accepted Generation, runtime state, pending artifact, resume, fresh run, or long historical command was executed.

## Reproduction

Evidence:

```text
reports/phase28_d70a_spa_no_action_empty_pending_regression_root_cause_audit/failing_test_reproduction.txt
```

The focused pytest still fails:

```text
Expected = NO_ORDER_AUTHORIZED
Observed = REVIEW_REQUIRED
```

Equivalent fixture tracing showed:

```text
RESULT_STATUS = REVIEW_REQUIRED
RESULT_REASON = strategy_planning_authority_unresolved
RESULT_REASON_CODES = ('strategy_plan_order_side_unresolved',)
PENDING_COMMIT_STATUS = NOT_COMMITTED_REVIEW_REQUIRED_EMPTY_UNSCOPED
```

The Runtime Planning plan consumed by SPA was not a valid no-action plan:

```text
security_code = 7203
source_pm_action = HOLD
planning_intent = UNRESOLVED
order_side_intent = UNRESOLVED
pending_eligibility = REVIEW_REQUIRED
```

## Direct REVIEW_REQUIRED Producer

Evidence:

```text
reports/phase28_d70a_spa_no_action_empty_pending_regression_root_cause_audit/spa_review_required_producer.json
```

Direct producer:

```text
runtime_v2.planning.strategy_authority.activate_strategy_planning_authority
```

Direct code path:

```text
src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py:436-443
src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py:228-260
src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py:364-370
src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py:386-388
```

`_pending_item_from_strategy_plan` receives `planning_intent=UNRESOLVED` and `order_side_intent=UNRESOLVED`. Since the side is neither `BUY` nor `SELL`, it returns:

```text
strategy_plan_order_side_unresolved
```

SPA then appends that reason, writes a REVIEW_REQUIRED approval artifact, skips current pending commit, and returns REVIEW_REQUIRED.

## First Loss Point

Evidence:

```text
reports/phase28_d70a_spa_no_action_empty_pending_regression_root_cause_audit/no_action_lineage.json
reports/phase28_d70a_spa_no_action_empty_pending_regression_root_cause_audit/failing_fixture_contract.json
```

The first loss point is before SPA:

```text
Runtime Planning current-position authority
```

The failing fixture passes only:

```text
current_codes = ("7203",)
current_position_rows = [{"security_code": "7203"}]
```

The current Runtime Planning authority requires valid current-position evidence. The minimal row lacks quantity, runtime-owned source, and position-state date, so authority becomes REVIEW_REQUIRED:

```text
current_position_quantity_missing_or_non_positive
current_position_ownership_authority_missing
current_position_state_as_of_missing
```

Relevant implementation:

```text
src/ai_fund_lab_v2/strategy/runtime_planning.py:1080-1087
src/ai_fund_lab_v2/strategy/runtime_planning.py:1261-1270
```

Current position + zero delta maps to `NO_ACTION` only when `current_position_membership_authority.status == PASS`.

## Contract Comparison

Evidence:

```text
reports/phase28_d70a_spa_no_action_empty_pending_regression_root_cause_audit/empty_pending_contract_comparison.json
reports/phase28_d70a_spa_no_action_empty_pending_regression_root_cause_audit/phase23i_vs_current_contract.json
```

Phase23-AB requires authorized no-order evidence before EMPTY pending can be accepted:

```text
runtime planning PASS
order plan NO_ORDER_AUTHORIZED
approval artifact NO_ORDER_AUTHORIZED
pending.state EMPTY
pending item count 0
```

The failing fixture produced:

```text
runtime planning REVIEW_REQUIRED
planning_intent UNRESOLVED
order_side_intent UNRESOLVED
approval REVIEW_REQUIRED
pending not committed
```

Therefore this is not an authorized no-order case. Fail-closed behavior is correct.

A control trace using a runtime-owned current-position row with `quantity=100`, `as_of=BUSINESS_DATE`, and `source=runtime_v2_runtime_owned_fill_projection` produced:

```text
Runtime Planning = PASS / NO_ACTION / NONE
SPA = NO_ORDER_AUTHORIZED
pending_commit_status = COMMITTED_CURRENT
```

## D69 Causality

Evidence:

```text
reports/phase28_d70a_spa_no_action_empty_pending_regression_root_cause_audit/d69_causality_assessment.json
docs/phase_reports/phase28_d69_pc_ps_add_signed_delta_contract_repair_implementation.md
```

D69 changed the Position Sizing ADD signed-delta consumption path and its focused Position Sizing tests. D69 did not directly change SPA no-action mapping or the Runtime Planning current-position authority requirement that converts this fixture to UNRESOLVED.

Judgment:

```text
D69 Causality = NOT_DIRECT
```

D69 exposed this regression during its full relevant regression run, but it is not the direct producer.

## Classification

Evidence:

```text
reports/phase28_d70a_spa_no_action_empty_pending_regression_root_cause_audit/regression_scope_summary.json
```

Classification:

```text
CASE_C_TEST_EXPECTATION_STALE
```

The stale part is not the no-order/empty-pending contract itself. The stale part is the fixture's assumption that `current_codes=("7203",)` alone is sufficient current-position authority for a current-position zero-delta no-action case.

## Gate Decision

Evidence:

```text
reports/phase28_d70a_spa_no_action_empty_pending_regression_root_cause_audit/resume_gate_decision.json
reports/phase28_d70a_spa_no_action_empty_pending_regression_root_cause_audit/open_gap_inventory.json
```

Resume remains blocked until the short regression is made green:

```text
Resume Allowed = NO
Repair Required Before Resume = YES
Fresh-run Required = NO
D66 Status = WAITING
```

Minimal next repair scope:

```text
Update the stale Phase23-I fixture/expectation to provide runtime-owned current-position authority for the valid NO_ACTION / EMPTY pending case.
Do not change production SPA, Pending Safety, Submit Guard, D61, D63, or D69 logic.
```

## Final Judgment

```text
Primary Judgment = PHASE28_D70A_SPA_NO_ACTION_EMPTY_PENDING_REGRESSION_CLASSIFIED_CASE_C_STALE_TEST_FIXTURE_PRODUCTION_FAIL_CLOSED_PRESERVED
Failing Test = tests/runtime_v2/test_phase23_i_strategy_planning_authority.py::test_phase23_i_valid_no_action_remains_empty_pending_without_legacy_fallback
Expected = NO_ORDER_AUTHORIZED / EMPTY pending
Observed = REVIEW_REQUIRED / no current pending commit
Direct REVIEW_REQUIRED Producer = runtime_v2.planning.strategy_authority.activate_strategy_planning_authority
Root Cause = fixture supplies no valid runtime-owned current-position authority, so Runtime Planning emits UNRESOLVED before SPA
Classification = CASE_C_TEST_EXPECTATION_STALE
D69 Causality = NOT_DIRECT
Production Runtime Defect = NO
Test Expectation Stale = YES
D61/D63/D69 preserved = YES
Fail-closed preserved = YES
Resume Allowed = NO
Repair Required Before Resume = YES
Fresh-run Required = NO
D66 Status = WAITING
Next Phase = Phase28-D70B
```
