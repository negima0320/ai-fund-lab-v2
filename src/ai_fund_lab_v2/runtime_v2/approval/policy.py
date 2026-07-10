"""Approval policy skeleton for Runtime v2."""

from __future__ import annotations

import hashlib

from ai_fund_lab_v2.runtime_v2.approval.models import (
    ApprovalArtifact,
    ApprovalDecision,
    ApprovalRequest,
    ApprovalStatus,
)
from ai_fund_lab_v2.runtime_v2.pending.models import PendingOrderPlan


def build_approval_request(
    *,
    pending_plan: PendingOrderPlan,
    business_date: str,
    expires_at: str,
) -> ApprovalRequest:
    requested_item_ids = tuple(item.pending_item_id for item in pending_plan.items)
    return ApprovalRequest(
        approval_request_id=_hash_id("approval-request", pending_plan.pending_plan_id, business_date),
        pending_plan_id=pending_plan.pending_plan_id,
        order_plan_id=pending_plan.source_order_plan.order_plan_id,
        environment=pending_plan.environment,
        business_date=business_date,
        target_session_date=pending_plan.target_session_date,
        requested_item_ids=requested_item_ids,
        created_at=business_date,
        expires_at=expires_at,
        review_required=pending_plan.state.value == "REVIEW_REQUIRED",
        policy_version=pending_plan.policy_version,
        policy_source=pending_plan.policy_source,
        pending_policy_hash=pending_plan.pending_policy_hash,
        safety_decision_id=pending_plan.safety_decision_id,
        safety_policy_version=pending_plan.safety_policy_version,
    )


def build_approval_artifact(
    *,
    request: ApprovalRequest,
    decision: ApprovalDecision,
) -> ApprovalArtifact:
    approval_hash = _hash_id(
        "approval-hash",
        request.approval_request_id,
        decision.status.value,
        ",".join(decision.approved_item_ids),
        request.pending_policy_hash,
        request.safety_decision_id,
        request.safety_policy_version,
        decision.decided_at,
    )
    return ApprovalArtifact(
        approval_id=_hash_id("approval", request.approval_request_id, decision.decided_at),
        approval_request_id=request.approval_request_id,
        pending_plan_id=request.pending_plan_id,
        order_plan_id=request.order_plan_id,
        status=decision.status,
        approved_item_ids=decision.approved_item_ids
        if decision.status == ApprovalStatus.APPROVED
        else (),
        rejected_item_ids=decision.rejected_item_ids,
        approval_hash=approval_hash,
        approved_at=decision.decided_at if decision.status == ApprovalStatus.APPROVED else "",
        expires_at=request.expires_at,
        review_required=(
            request.review_required
            or decision.status in {ApprovalStatus.REVIEW_REQUIRED, ApprovalStatus.EXPIRED}
        ),
        reason=decision.reason,
        policy_version=request.policy_version,
        policy_source=request.policy_source,
        pending_policy_hash=request.pending_policy_hash,
        safety_decision_id=request.safety_decision_id,
        safety_policy_version=request.safety_policy_version,
    )


def _hash_id(prefix: str, *parts: str) -> str:
    raw = "|".join(parts).encode("utf-8")
    return prefix + "-" + hashlib.sha256(raw).hexdigest()[:16]
