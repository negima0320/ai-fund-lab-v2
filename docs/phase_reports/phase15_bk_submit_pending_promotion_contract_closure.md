# Phase15-BK Submit Pending Promotion Contract Closure

## 1. Executive Summary

Phase15-BK closed the dry-run contract boundary:

```text
Human Review Evidence
↓
Human Approval Artifact
↓
Promotion Validation
↓
Submit Pending Promotion Candidate
```

Final judgment:

```text
PROMOTION_CONTRACT_READY_WITH_SAFETY_BLOCK
```

Meaning:

- Human Review and Human Approval are now separated.
- Review Pending linkage is explicit.
- Human Approval is item-scoped.
- Promotion Candidate is generated as no-apply evidence.
- Authoritative Submit Pending remains unchanged and `EMPTY`.
- Submit, Broker Write, Execution, Current mutation, Notification Send, and Production Write were not executed.
- Current Safety still blocks `sell_submit` and `broker_write`, so this is not Submit-ready.

## 2. Read Documents

Read:

- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/runtime_temporal_freshness_contract.md`
- `docs/phase_reports/phase15_bg_human_safety_review_4591.md`
- `docs/phase_reports/phase15_bh_runtime_acceptance_step1_sell_hold_review_only_morning.md`
- `docs/phase_reports/phase15_bi_system_purpose_phase15_purpose_alignment_review.md`
- `docs/phase_reports/phase15_bj_runtime_acceptance_step2_submit_scope_review.md`
- `docs/phase_reports/phase14_e51_sell_submit_execution_cleanup_cycle.md`
- `docs/phase_reports/phase14_e52_sell_submit_guard_contract_audit.md`
- `docs/phase_reports/phase14_e53_buy_sell_submit_guard_regression_audit.md`

Reviewed implementation:

- `src/ai_fund_lab_v2/runtime_v2/review_only/sell_hold_morning.py`
- `src/ai_fund_lab_v2/runtime_v2/pending/`
- `src/ai_fund_lab_v2/runtime_v2/approval/`
- `src/ai_fund_lab_v2/runtime_v2/submit/`

## 3. Human Review vs Human Approval

Human Review remains:

```text
SELL/HOLD評価を生成してよいか
```

Current Human Review:

```text
SELL_HOLD_REVIEW_REQUIRED
```

This is not Submit approval.

Human Approval now means:

```text
どの具体的な銘柄・数量・Side・Review Itemを
Submit Pending Promotion Candidateへ昇格してよいか
```

BK created a separate Human Approval Artifact. It does not authorize automatic trade or Broker Write.

## 4. Review Pending Linkage

Generated linkage evidence:

```text
.runtime/runtime_state/sell_hold_review_only/2026-07-10/review_pending_linkage_evidence.json
```

Key linkage fields are now explicit per item:

- `source_human_review_id`
- `source_safety_event_id`
- `source_safety_review_id`
- `source_pm_decision_id`
- `source_review_output_id`
- `business_date`
- `issue_code`
- `side`
- `review_item_id`
- `review_item_hash`

Review Pending still preserves:

```text
submit_allowed=false
broker_write_allowed=false
authoritative_submit_pending=false
```

## 5. Human Approval Artifact

Generated:

```text
.runtime/runtime_state/human_approval/2026-07-10/human-submit-approval-deadabbad64a468c.json
```

Result:

| Field | Value |
|---|---|
| `schema_version` | `runtime_v2_human_submit_approval_v1` |
| `approval_status` | `APPROVED_FOR_PENDING_PROMOTION` |
| `approved_item_ids` | `review-item-4591` |
| `approved_side` | `SELL` |
| `approved_quantities.review-item-4591` | `5000` |
| `automatic_trade_authorized` | `false` |
| `broker_write_authorized` | `false` |
| `authoritative_pending_promotion_authorized` | `true` |
| `revoked_at` | `null` |

The 4591 selection is an Acceptance fixture for structure validation. Codex did not make an investment decision.

## 6. Promotion Producer

Added CLI job:

```text
submit_pending_promotion_review
```

Executed:

```text
PYTHONPATH=src python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation --mode demo --job submit_pending_promotion_review --business-date 2026-07-10 --runtime-root .runtime --reports-root reports/runtime_v2 --public-reports-root reports/public/runtime_v2 --manifest-root .runtime/runtime_state/run_manifest --log-root .runtime/runtime_state/logs --capital-deployment-policy configs/runtime_v2/capital_deployment.json --evaluation-time 2026-07-11T12:10:00+00:00
```

Result:

- Exit code: `0`
- Manifest: `.runtime/runtime_state/run_manifest/2026-07-10/runtime-v2-submit_pending_promotion_review-2026-07-10-20260711T120753.403077+0000.json`
- `submit_pending_promotion_review_status=PASS`
- `submit_pending_promotion_review_reason=promotion_contract_ready_with_safety_block`

## 7. Promotion Candidate

Generated:

```text
.runtime/runtime_state/pending_promotion_candidate/2026-07-10/promotion-candidate-0e4889130e4a2d95.json
```

Result:

| Field | Value |
|---|---|
| `promotion_status` | `READY_BUT_SAFETY_BLOCKED` |
| `promotion_allowed` | `false` |
| `promotion_block_reasons` | `safety_submit_blocked` |
| `safety_submit_permission` | `BLOCKED` |
| `apply_requested` | `false` |
| `apply_executed` | `false` |
| `submit_executed` | `false` |
| `broker_write_performed` | `false` |
| `authoritative_pending_mutated` | `false` |

Selected item:

| Field | Value |
|---|---|
| `issue_code` | `4591` |
| `side` | `SELL` |
| `review_item_id` | `review-item-4591` |
| `runtime_sell_quantity` | `5000` |
| `source_human_review_id` | `human_review_b15c7967207e475fb287c929a9faa20c` |
| `source_safety_event_id` | `safety_event_314f67fe2ecb43f0a90816dac53c0aeb` |

## 8. Validation

Passed:

- Review Pending schema.
- Review Pending hash.
- Human Review linkage.
- Safety event linkage.
- Approval status.
- Approval not expired.
- Approval not revoked.
- Approved item ids.
- Approved quantity.
- Side.
- Review item hash.
- Policy hash.
- Safety decision id.
- Current freshness.
- Broker freshness.
- Pending slot is `EMPTY`.

Safety:

```text
safety_submit_scope=BLOCKED
```

Broker available quantity:

```text
SKIPPED_DUE_SAFETY_SUBMIT_BLOCK
```

This does not permit Submit. Broker quantity cannot be used as a Submit allowance while Safety blocks Submit.

## 9. Pending Slot

Authoritative Submit Pending:

```text
.runtime/pending_order_plan/pending_order_plan.json
```

State after BK:

```text
state=EMPTY
active_pending=false
last_terminal_state=EXPIRED
```

No authoritative Pending mutation occurred.

## 10. Regression

Executed:

```text
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase15bk_submit_pending_promotion_contract.py tests/runtime_v2/test_phase15bh_sell_hold_review_only_morning.py tests/runtime_v2/test_phase13_p_pending_no_fallback.py tests/runtime_v2/test_phase13_p_pending_lifecycle.py tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py tests/runtime_v2/test_phase15m_sell_broker_available_quantity_evidence.py
```

Result:

```text
23 passed
```

Compile check:

```text
PYTHONPYCACHEPREFIX=/private/tmp/pycache_phase15bk PYTHONPATH=src python3 -m compileall -q src/ai_fund_lab_v2/runtime_v2/pending_promotion.py src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py
```

Result:

```text
passed
```

Coverage:

- Review Pending alone cannot promote.
- Human Approval missing blocks promotion.
- Expired approval blocks promotion.
- Missing `expires_at` blocks promotion.
- Future `approved_at` blocks promotion.
- Business date mismatch blocks promotion.
- Revoked approval blocks promotion.
- Hash mismatch blocks promotion.
- Event/review id mismatch blocks promotion.
- Out-of-scope item blocks promotion.
- Quantity tampering blocks promotion.
- Review item hash mismatch blocks promotion.
- Non-empty Pending slot blocks promotion.
- Safety blocked does not become Submit permission.
- Dry-run does not mutate authoritative Pending.
- No Submit.
- No Broker Write.

## 11. Runtime Mutation Statement

Allowed evidence writes:

- Human Approval Acceptance Artifact.
- Review Pending Linkage Evidence.
- Submit Pending Promotion Candidate.
- Run manifests / reports.
- Phase15-BK reports.

Not executed:

```text
Submit
Execution
Broker Write
Approval Apply
Authoritative Pending mutation
Pending Approve
Current mutation
Notification Send
Production Write
```

## 12. Architecture Updates

Updated:

- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/runtime_temporal_freshness_contract.md`

Added/clarified:

- Human Review and Human Approval are separate authorities.
- Review Pending is not Submit Pending.
- Promotion Candidate is no-apply evidence.
- Authoritative Submit Pending Apply is a later explicit scope.
- Safety can leave Candidate structurally ready while blocking Submit.

## 13. Remaining Blockers

- Safety remains `REVIEW_REQUIRED`.
- `sell_submit` and `broker_write` remain `BLOCKED`.
- Promotion Candidate is not Authoritative Submit Pending.
- Authoritative Submit Pending Apply is not accepted yet.
- Submit itself is not accepted or executed.

## 14. Final Judgment

```text
PROMOTION_CONTRACT_READY_WITH_SAFETY_BLOCK
```

Recommended next prefix:

```text
Phase15-BL Runtime Acceptance Step2 Authoritative Submit Pending Apply Review
```

BL should review Apply separately and still must not execute Submit or Broker Write unless a later explicit Submit Acceptance scope authorizes it.
