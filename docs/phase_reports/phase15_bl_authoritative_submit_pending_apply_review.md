# Phase15-BL Authoritative Submit Pending Apply Review

## Summary

Phase15-BL reviewed the boundary from `Promotion Candidate` to `Authoritative Submit Pending Apply`.

This phase did not apply to authoritative Pending, did not Submit, did not execute, and did not perform Broker Write. The authoritative Pending slot remained `EMPTY`.

Final judgment:

```text
APPLY_CONTRACT_READY_BUT_SAFETY_BLOCKED
```

## Inputs Read

- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/runtime_temporal_freshness_contract.md`
- `docs/phase_reports/phase15_bh_runtime_acceptance_step1_sell_hold_review_only_morning.md`
- `docs/phase_reports/phase15_bi_system_purpose_phase15_purpose_alignment_review.md`
- `docs/phase_reports/phase15_bj_runtime_acceptance_step2_submit_scope_review.md`
- `docs/phase_reports/phase15_bk_submit_pending_promotion_contract_closure.md`
- `docs/phase_reports/phase14_e51_sell_submit_execution_cleanup_cycle.md`
- `docs/phase_reports/phase14_e52_sell_submit_guard_contract_audit.md`
- `docs/phase_reports/phase14_e53_buy_sell_submit_guard_regression_audit.md`
- `src/ai_fund_lab_v2/runtime_v2/pending_promotion.py`
- `src/ai_fund_lab_v2/runtime_v2/pending/`
- `src/ai_fund_lab_v2/runtime_v2/approval/`
- `src/ai_fund_lab_v2/runtime_v2/submit/`

## Input Evidence

| Evidence | Artifact | Status |
| --- | --- | --- |
| Promotion Candidate | `.runtime/runtime_state/pending_promotion_candidate/2026-07-10/promotion-candidate-0e4889130e4a2d95.json` | `READY_BUT_SAFETY_BLOCKED` |
| Human Approval | `.runtime/runtime_state/human_approval/2026-07-10/human-submit-approval-deadabbad64a468c.json` | `APPROVED_FOR_PENDING_PROMOTION` |
| Authoritative Pending Slot | `.runtime/pending_order_plan/pending_order_plan.json` | `EMPTY`, `active_pending=false` |
| Runtime Safety Decision | `.runtime/runtime_state/safety/latest_safety_decision.json` | `REVIEW_REQUIRED`, `sell_submit=BLOCKED`, `broker_write=BLOCKED` |

## Apply Contract

The Apply producer is `authoritative_pending_apply_review`.

It reads a Promotion Candidate and Human Approval, validates Apply Preconditions and TOCTOU-sensitive dependencies, and writes only a no-apply candidate:

```text
.runtime/runtime_state/authoritative_pending_apply_candidate/2026-07-10/apply-candidate-a6d308ef3dac7170.json
```

It does not write:

```text
.runtime/pending_order_plan/pending_order_plan.json
```

The Apply Candidate keeps:

```text
apply_requested=false
apply_executed=false
authoritative_pending_mutated=false
submit_executed=false
execution_executed=false
broker_write_performed=false
```

## Apply Preconditions

Result: `PASS` except Safety submit/apply permission, which remains blocked by the current Safety Decision.

Validated:

- Promotion Candidate schema/status/path
- Promotion Candidate not previously requested/applied
- Human Approval schema/status/business date/expiration/revocation
- Approval not consumed
- Approval authorizes pending promotion but not automatic trade or broker write
- Promotion Candidate hash handling
- Approval hash
- Review Pending hash
- Policy hash
- Safety Decision id
- Current State id/readiness
- Broker Snapshot id/freshness
- Target Session
- Pending Slot `EMPTY`
- Selected item scope, side, quantity, review item hash
- SELL quantity <= Runtime-owned Current for 4591

Safety block means Broker available quantity validation was skipped explicitly:

```text
broker_quantity_validation=SKIPPED_DUE_SAFETY_APPLY_BLOCK
```

## Pending Item Contract

The candidate item for `4591` includes:

- `pending_item_id`
- `issue_code`
- `broker_issue_code`
- `side`
- `quantity`
- `order_type`
- `price_condition`
- `target_session`
- `source_review_item_id`
- `source_human_review_id`
- `source_safety_event_id`
- `source_pm_decision_id`
- `approval_id`
- `review_item_hash`
- `policy_hash`

Order conditions were not invented. Since the Promotion Candidate and Human Approval do not authorize concrete order conditions, the candidate records:

```text
order_type=REVIEW_REQUIRED_BEFORE_AUTHORITATIVE_APPLY
price_condition=REVIEW_REQUIRED_BEFORE_AUTHORITATIVE_APPLY
```

## TOCTOU

Future real Apply must revalidate immediately before mutation:

- Approval status/expiration/revocation/consumption
- Safety Decision and action scope
- Policy hash
- Current State id/readiness
- Broker Evidence id/freshness
- Pending Slot `EMPTY`
- Target Session
- Promotion Candidate hash
- Approval hash

Phase15-BL generated this revalidation evidence as `PASS`, with final Apply blocked only by Safety.

## Atomicity

Status: `READY`

Future real Apply must:

- Apply all approved items atomically
- Preserve the original Pending slot on partial failure
- Prohibit partial Apply
- Write success history only after complete Pending publish
- Update the current pointer only after complete publish
- Create Backup and Apply Manifest before publish

## Idempotency

Status: `READY`

Defined protections:

- Same Apply Candidate rerun cannot duplicate Pending
- Applied Candidate reuse is invalid
- Same Approval duplicate consumption is invalid
- Different Candidate cannot reuse the same `pending_plan_id`
- Retry after failure requires fresh revalidation

## Backup / History

Status: `READY`

Required future artifacts:

- Before Pending Snapshot
- After Pending Snapshot
- Apply Manifest
- Promotion Candidate reference
- Approval reference
- Terminal/failure history

Phase15-BL recorded before/after Pending hashes and confirmed they match:

```text
sha256:06030ad2d8eeecd73c287697d111a746d4a55c1bf3df1df66f63e3b344857bff
```

## Runtime State Machine

Confirmed boundary:

```text
Review Pending
↓
Human Approval
↓
Promotion Candidate
↓
Authoritative Pending Apply Candidate
```

Not performed:

```text
Authoritative Pending Apply
↓
Pending state APPROVED
↓
Submit
```

## Regression

Command:

```bash
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase15bl_authoritative_pending_apply_review.py tests/runtime_v2/test_phase15bk_submit_pending_promotion_contract.py tests/runtime_v2/test_phase15bh_sell_hold_review_only_morning.py tests/runtime_v2/test_phase13_p_pending_no_fallback.py tests/runtime_v2/test_phase13_p_pending_lifecycle.py tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py tests/runtime_v2/test_phase15m_sell_broker_available_quantity_evidence.py
```

Result:

```text
30 passed
```

Compile check:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/pycache_phase15bl PYTHONPATH=src python3 -m compileall -q src/ai_fund_lab_v2/runtime_v2/pending_apply.py src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py
```

Result: PASS

## Runtime Mutation

No prohibited mutation occurred:

- Authoritative Pending mutation: no
- Current Position mutation: no
- Submit: no
- Execution: no
- Broker Write: no
- Notification send: no

Evidence/report artifacts were generated by the review-only CLI path:

- `.runtime/runtime_state/authoritative_pending_apply_candidate/2026-07-10/apply-candidate-a6d308ef3dac7170.json`
- `.runtime/runtime_state/run_manifest/2026-07-10/runtime-v2-authoritative_pending_apply_review-2026-07-10-20260711T205343.990332+0000.json`
- `.runtime/runtime_state/current_state.json`
- `reports/runtime_v2/2026-07-10/*`
- `reports/public/runtime_v2/*`

## Remaining Blockers

- Current Safety Decision keeps `sell_submit=BLOCKED` and `broker_write=BLOCKED`.
- Concrete order conditions are not authorized by Review / Approval evidence and require explicit resolution before any future real Apply.
- Broker available quantity final validation is intentionally skipped while Safety blocks Apply/Submit.

## Final Judgment

```text
APPLY_CONTRACT_READY_BUT_SAFETY_BLOCKED
```

Meaning:

- Authoritative Pending Apply Contract is established.
- Apply Candidate can be produced with evidence.
- Safety currently prevents real Apply.
- Authoritative Pending remains `EMPTY`.

## Recommended Next Prefix

```text
Phase15-BM Runtime Acceptance Step2 Safety-Blocked Submit Path Closure
```

The next phase should close how Submit Acceptance proceeds while Safety remains `REVIEW_REQUIRED` / `BLOCKED`, without clearing Safety or performing Submit.
