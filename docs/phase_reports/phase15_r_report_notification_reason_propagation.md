# Phase15-R Report / Notification Reason Propagation

Date: 2026-07-09

Final judgment:

```text
PHASE15R_REPORT_NOTIFICATION_REASON_PROPAGATION_COMPLETE
```

## Purpose

Phase15-R closes the Phase15-Q critical gap around Report / Notification semantic propagation.

The goal is that an Operator can inspect the Runtime Report or Notification payload and understand:

- why BUY was allowed or stopped
- why SELL was allowed or stopped
- why Runtime became REVIEW_REQUIRED / BLOCKED / HALT
- which Policy / Safety / Submit Guard evidence produced the decision
- what the next operator action should be

## Implementation Summary

Report generation now reads Runtime Core reason evidence from the latest Runtime manifest for the business date, while preserving Report as a Derived artifact.

Added reason evidence:

- Policy evidence
- Safety evidence
- Submit Guard evidence
- REVIEW_REQUIRED / BLOCKED / HALT reasons
- Why BUY
- Why SELL
- Next Operator Action

Notification payload generation now carries the same reason summary and explicitly marks payload-only delivery.

## Changed Files

- `src/ai_fund_lab_v2/runtime_v2/report/markdown_writer.py`
- `src/ai_fund_lab_v2/runtime_v2/notification/models.py`
- `src/ai_fund_lab_v2/runtime_v2/notification/payload.py`
- `tests/runtime_v2/test_phase15r_report_notification_reason_propagation.py`
- `docs/phase_reports/phase15_r_report_notification_reason_propagation.md`
- `reports/phase_reports/phase15_r_report_notification_reason_propagation.json`

## Report Reason Sections

Runtime report now includes:

```text
Why BUY
Why SELL
Why BLOCKED / REVIEW_REQUIRED / HALT
Policy Evidence
Safety Evidence
Submit Guard Evidence
Next Operator Action
```

Public report includes a shorter `Why` summary with:

```text
Reason summary
Policy summary
Safety summary
Guard summary
Next operator action
```

## Policy Evidence

Report summary now exposes:

```text
capital_deployment_policy_source
capital_deployment_policy_version
active_policy_hash
target_investment_ratio
cash_buffer
max_exposure
max_position_weight
max_positions
```

Source priority:

```text
Runtime Manifest
Pending policy_context
```

Report does not recalculate policy.

## Safety Evidence

Report summary now exposes:

```text
safety_decision_id
safety_policy_version
safety_source
safety_decision
safety_reason
safety_status
block_buy
block_sell
block_submit
halt_runtime
emergency_stop
```

Source priority:

```text
Runtime Manifest
Pending safety_context
```

Report does not recalculate Safety.

## Submit Guard Evidence

Report summary now exposes:

```text
guard_decision
guard_reason
violated_policy
violated_policy_source
manual_review_required
policy_consistency_status
policy_mismatch_reason
broker_available_quantity_checked
broker_available_quantity_source
sell_quantity_guard_status
```

Source:

```text
Runtime Manifest submit_guard_item_evidence
Runtime Manifest submit_policy_consistency
```

Report does not rerun Submit Guard.

## Review Required / Blocked / Halt

Report summary now exposes:

```text
final_state
review_required_reasons
blocked_reasons
halt_reasons
next_operator_action
```

The reason builder reads Runtime manifest stages, warnings, errors, and Runtime events as evidence.

## Notification Payload Schema

Notification payload JSON now includes:

```text
runtime_state
severity
reason_summary
policy_summary
safety_summary
guard_summary
review_required
next_operator_action
notification_delivery_status
notification_sent
```

The dataclass `NotificationPayload` also carries:

```text
runtime_state
reason_summary
policy_summary
safety_summary
guard_summary
next_operator_action
notification_delivery_status
notification_sent
```

## Severity Classification

Implemented classification:

```text
HALT or emergency_stop=true -> HALT
BLOCKED -> BLOCKED
REVIEW_REQUIRED -> REVIEW_REQUIRED
manual_review_required=true -> ACTION_REQUIRED
normal completion -> INFO
```

## Payload-Only Handling

Phase15-R does not perform real notification send.

Notification payload explicitly records:

```text
notification_delivery_status=PAYLOAD_ONLY
notification_sent=false
```

Delivery Ledger, sender integration, and real send remain out of scope.

## Report Scope

Report remains Derived.

Confirmed constraints:

- Report does not write Current.
- Report does not make Report an input to Current.
- Report does not recalculate Policy.
- Report does not recalculate Safety.
- Report does not rerun Submit Guard.
- Runtime manifest is read-only evidence for human explanation.

## Tests

Added:

```text
tests/runtime_v2/test_phase15r_report_notification_reason_propagation.py
```

Coverage:

- Report shows policy evidence.
- Report shows safety evidence.
- Report shows submit guard evidence.
- Report shows Why BUY / Why SELL / Why BLOCKED / REVIEW_REQUIRED / HALT.
- Notification payload contains reason summary, policy summary, safety summary, guard summary, next operator action.
- Notification severity classification covers INFO / REVIEW_REQUIRED / BLOCKED / HALT.
- Notification remains payload-only.
- Report generation does not mutate Current fixed paths.

Regression run:

```text
python3 -m pytest -q tests/runtime_v2/test_phase15r_report_notification_reason_propagation.py
3 passed
```

Retention run:

```text
python3 -m pytest -q \
  tests/runtime_v2/test_phase14e6_runtime_v2_public_report_output.py \
  tests/runtime_v2/test_phase14e34_notification_component_completion.py \
  tests/runtime_v2/test_phase13_t_notification_payload.py \
  tests/runtime_v2/test_phase13_v_derived_not_current_schema_guard.py \
  tests/runtime_v2/test_phase15h_capital_deployment_policy.py \
  tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py \
  tests/runtime_v2/test_phase15k_morning_policy_propagation_hidden_policy_removal.py \
  tests/runtime_v2/test_phase15l_submit_policy_hash_consistency_guard.py \
  tests/runtime_v2/test_phase15m_sell_broker_available_quantity_evidence.py \
  tests/runtime_v2/test_phase15n_safety_operation_guard_runtime_connection.py \
  tests/runtime_v2/test_phase15p_planning_internal_safety_placeholder_removal.py
50 passed
```

## Still Not Fixed

The following remain intentionally out of scope for Phase15-R:

- Operator Review apply path
- Recovery apply path
- Position Management AI -> SELL Planning formal connection
- Candidate / Opportunity AI direct execution contract
- Notification real send
- Delivery Ledger / sender Runtime connection
- launchd autonomous readiness
- Demo Operation evidence
- Full Runtime PASS declaration

## Prohibited Actions Confirmation

This phase did not perform:

- Broker Write
- Demo order
- Production order
- Notification real send
- launchd/plist change
- Current direct edit
- Runtime bypass creation
- fake adapter Full Runtime PASS declaration
- Operator Review apply path implementation
- Recovery apply path implementation

## Final Judgment

```text
PHASE15R_REPORT_NOTIFICATION_REASON_PROPAGATION_COMPLETE
```
