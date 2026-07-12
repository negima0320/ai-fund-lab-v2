# Phase15-BM Safety-Blocked Submit Path Closure

## Summary

Phase15-BM accepted the 4591 Safety-blocked Apply / Submit path as a safe and expected Runtime stop.

Final judgment:

```text
SAFETY_BLOCKED_SUBMIT_PATH_ACCEPTED_WITH_CONDITIONS
```

This phase did not clear the Safety event, did not apply Authoritative Pending, did not Submit, did not call Broker, did not execute, did not mutate Current, and did not send notifications.

## Read Documents

- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/runtime_temporal_freshness_contract.md`
- `docs/phase_reports/phase15_bi_system_purpose_phase15_purpose_alignment_review.md`
- `docs/phase_reports/phase15_bj_runtime_acceptance_step2_submit_scope_review.md`
- `docs/phase_reports/phase15_bk_submit_pending_promotion_contract_closure.md`
- `docs/phase_reports/phase15_bl_authoritative_submit_pending_apply_review.md`
- `docs/phase_reports/phase15_bg_human_safety_review_4591.md`
- `docs/phase_reports/phase15_bh_runtime_acceptance_step1_sell_hold_review_only_morning.md`
- `docs/phase_reports/phase14_e51_sell_submit_execution_cleanup_cycle.md`
- `docs/phase_reports/phase14_e52_sell_submit_guard_contract_audit.md`
- `docs/phase_reports/phase14_e53_buy_sell_submit_guard_regression_audit.md`
- `src/ai_fund_lab_v2/runtime_v2/pending_promotion.py`
- `src/ai_fund_lab_v2/runtime_v2/pending_apply.py`
- `src/ai_fund_lab_v2/runtime_v2/safety_decision.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/`
- `src/ai_fund_lab_v2/runtime_v2/pending/`

## Safety-Blocked Apply Result

Input Apply Candidate:

```text
.runtime/runtime_state/authoritative_pending_apply_candidate/2026-07-10/apply-candidate-a6d308ef3dac7170.json
```

Observed:

```text
apply_status=READY_BUT_SAFETY_BLOCKED
apply_allowed=false
apply_preconditions_status=PASS
toctou_revalidation_status=PASS
safety_apply_permission=BLOCKED
apply_requested=false
apply_executed=false
authoritative_pending_mutated=false
submit_executed=false
broker_write_performed=false
```

Classification:

```text
EXPECTED_SAFETY_BLOCK
```

The block reason is Safety, not invalid Review / Approval / Promotion / Apply structure.

## Safety-Blocked Submit Guard Result

Submit Guard was verified in an isolated temporary Runtime fixture, not by mutating existing `.runtime`.

Result contract:

```text
submit_path_status=BLOCKED_BY_SAFETY
apply_status=BLOCKED_BY_SAFETY
submit_attempted=false
broker_client_called=false
broker_write_performed=false
pending_consumed=false
approval_consumed=false
execution_created=false
current_mutated=false
notification_sent=false
```

The existing submit pipeline stops before adapter preflight when Safety returns `sell_submit=BLOCKED`. Therefore no Broker client call is made and no request payload is sent.

## Fail-Closed

Regression verified fail-closed behavior for:

- Safety Decision missing
- Safety Decision stale
- Safety Decision expired
- Safety action scope missing
- `broker_write` action scope missing
- Safety BLOCKED
- unresolved order condition

Expected result in each case:

```text
Apply不可
Submit不可
Broker Write不可
REVIEW_REQUIREDまたはBLOCKED
```

Implementation note:

- `safety_decision.py` now treats explicit `freshness_status=STALE/EXPIRED` as not `PASS`.
- When `action_permissions` is explicitly present, missing requested action scope fails closed.
- Existing fixtures without `action_permissions` keep backward-compatible block flags.

## Pending / Approval Non-Consumption

Safety Block does not consume:

- Human Approval
- Promotion Candidate
- Apply Candidate
- Authoritative Pending
- Pending Item
- Review Pending

Existing `.runtime/pending_order_plan/pending_order_plan.json` remains:

```text
state=EMPTY
active_pending=false
```

Raw file hashes observed for existing runtime evidence:

```text
pending_order_plan.json: 84075f23cc6d1c5ae227de1bfe4a213221aefd131fdadb395058755601ac2c77
apply-candidate-a6d308ef3dac7170.json: f34dfa66d6f11962e8e0bc1a71cd5118cdb0f7fc8e029c371302366549005df1
human-submit-approval-deadabbad64a468c.json: 6146e86dd76940d04fa3c875e9b0e2cb6cf56cad192d46017b8c2239c0d00619
promotion-candidate-0e4889130e4a2d95.json: 1b8aeacc7c9b46178713cc42db5edec0d7d5a3d8109e49c6a0b9af90968f2d0a
```

## Retry Contract

Retry after Safety Block requires:

- Same Safety Decision cannot be retried as if it were new permission.
- Safety Decision update requires all Apply / Submit preconditions to be revalidated.
- Approval expiration requires re-approval.
- Current change requires Candidate regeneration or revalidation according to changed state.
- Broker Evidence change requires broker quantity and freshness revalidation.
- Policy change requires re-approval or fresh Candidate.
- Target Session change requires regeneration.
- Old Apply Candidate must not be reused blindly.

## Order Condition Authority

BL left:

```text
order_type=REVIEW_REQUIRED_BEFORE_AUTHORITATIVE_APPLY
price_condition=REVIEW_REQUIRED_BEFORE_AUTHORITATIVE_APPLY
```

BM classifies this as:

```text
ORDER_CONDITION_AUTHORITY_CONTRACT_REQUIRED
```

The unresolved authority is independent from Safety Block. The future contract must define whether order conditions are selected by Policy, Human Approval, Submit Pending Producer, or Broker capability evidence. Runtime scaffolding must not infer them from defaults.

Submit preflight now blocks non-`MARKET` / non-`LIMIT` order conditions before the Broker client boundary.

## Runtime State Machine

Accepted Safety-blocked state transition:

```text
Review Pending
↓
Human Approval
↓
Promotion Candidate
↓
Apply Candidate
↓
Safety Block
↓
REVIEW_REQUIRED / BLOCKED
↓
No Apply
No Submit
No Broker Write
```

This is a safe stop, not an abnormal Runtime failure.

## Regression

Command:

```bash
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase15bm_safety_blocked_submit_path.py tests/runtime_v2/test_phase15bl_authoritative_pending_apply_review.py tests/runtime_v2/test_phase15bk_submit_pending_promotion_contract.py tests/runtime_v2/test_phase15n_safety_operation_guard_runtime_connection.py tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py tests/runtime_v2/test_phase15m_sell_broker_available_quantity_evidence.py tests/runtime_v2/test_phase13_p_pending_no_fallback.py tests/runtime_v2/test_phase13_p_pending_lifecycle.py
```

Result:

```text
41 passed
```

Compile check:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/pycache_phase15bm PYTHONPATH=src python3 -m compileall -q src/ai_fund_lab_v2/runtime_v2/safety_decision.py src/ai_fund_lab_v2/runtime_v2/submit/guards.py tests/runtime_v2/test_phase15bm_safety_blocked_submit_path.py
```

Result: PASS

## Runtime Mutation

No prohibited Runtime mutation occurred.

Existing `.runtime` was only read for BM evidence. Safety was not cleared. 4591 was not excluded. Authoritative Pending stayed `EMPTY`. Submit and Broker Write were not executed.

## Remaining Conditions

- `ORDER_CONDITION_AUTHORITY_CONTRACT_REQUIRED`
- Normal Submit Acceptance must be executed later in an isolated Runtime Root or equivalent isolated fixture.

## Final Judgment

```text
SAFETY_BLOCKED_SUBMIT_PATH_ACCEPTED_WITH_CONDITIONS
```

## Recommended Next Prefix

```text
Phase15-BN Runtime Acceptance Step2 Isolated Normal Submit Scenario Preparation
```
