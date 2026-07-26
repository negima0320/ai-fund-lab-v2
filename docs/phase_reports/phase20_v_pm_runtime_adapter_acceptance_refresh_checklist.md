# Phase20-V PM Runtime Adapter Acceptance Refresh Checklist

## Scope

This checklist prepares a formal acceptance refresh for the current Position Management Runtime Adapter source.

It does not grant acceptance by itself. Human Review / formal Artifact Registry acceptance must remain a separate explicit authority action.

## Candidate Member

```text
artifact_set_type: POSITION_MANAGEMENT_POLICY_SET
artifact_set_id: control.position_management.accepted_set
member_role: RUNTIME_ADAPTER
member_path: src/ai_fund_lab_v2/runtime_v2/position_management/producer.py
authority_mode: ACCEPTED_CURRENT_PATH
```

## Hashes

```text
old_accepted_commit: f4f8dbf03355106f201174f6f68b86aac707b6ed
old_accepted_hash: 93581111ae9b61facf669f8033d87e927f103d05483b4f212da4a592dbb15185
current_source_hash: ac2e7f6a3e9e184889551a8884a0e779ffb37292e8b26daf1e25e1610bba739c
current_source_dirty: true
```

The current source is the working-tree `producer.py` state, not a committed source snapshot.

## Required Human Review Checks

- Canonical PM behavior unchanged: PASS in Phase20-V equivalence evidence.
- HOLD behavior unchanged: PASS.
- REDUCE behavior unchanged: PASS.
- EXIT behavior unchanged: PASS.
- ADD behavior unchanged: PASS.
- READY_EMPTY / NO_POSITION behavior unchanged: PASS.
- Invalid required input fail-closed behavior unchanged: PASS.
- Decision-order collision behavior unchanged: PASS.
- PM score outputs unchanged: PASS for `hold_score`, `exit_score`, `reduce_score`, `add_score`, and `confidence`.
- REDUCE intensity unchanged: PASS.
- PM quantity authority boundary unchanged: REDUCE remains delegated to Sell Planning; EXIT remains full-position PM authority.
- Fail-closed authority hash validation preserved: PASS by Phase20-U / existing producer behavior.
- Trace-only allowed differences confirmed:
  - `decision_trace`
  - `dominant_cause`
  - `secondary_causes`
  - `decision_reason_codes`
  - `action_score`
  - `selected_action_score`
  - `confidence_semantics`
  - `decision_trace_contract_version`
  - `decision_trace_path`
- No forbidden behavior difference: PASS.
- Runtime Test false-PASS regression: PASS.
- Long Historical run not executed by Codex: PASS.
- Accepted Generation / Artifact Registry pointer not modified by Codex: PASS.

## Evidence

```text
reports/phase20_v_pm_runtime_adapter_behavioral_equivalence_review/equivalence_report.json
reports/phase20_v_pm_runtime_adapter_behavioral_equivalence_review/equivalence_report.md
reports/phase_reports/phase20_v_pm_runtime_adapter_behavioral_equivalence_review.json
```

## Procedure Boundary

Formal acceptance refresh may proceed only after a human reviewer confirms this checklist and follows the existing Artifact Registry acceptance process.

Prohibited shortcut actions:

- manual manifest hash replacement
- direct accepted pointer edit
- weakening runtime adapter hash validation
- historical-only skip
- Codex acting as Human Review authority

