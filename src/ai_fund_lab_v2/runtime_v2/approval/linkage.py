"""Approval to Pending linkage helpers."""

from __future__ import annotations

from ai_fund_lab_v2.runtime_v2.approval.models import ApprovalArtifact, ApprovalStatus
from ai_fund_lab_v2.runtime_v2.pending.models import PendingOrderPlan
from ai_fund_lab_v2.runtime_v2.pending.promotion import attach_approval_link
from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import CapitalDeploymentPolicy
from ai_fund_lab_v2.runtime_v2.planning_submit_feasibility import RuntimeCurrentExposure


def link_approval_to_pending(
    *,
    pending_plan: PendingOrderPlan,
    approval_artifact: ApprovalArtifact,
    planning_submit_feasibility_current: RuntimeCurrentExposure | None = None,
    planning_submit_feasibility_policy: CapitalDeploymentPolicy | None = None,
) -> PendingOrderPlan:
    if approval_artifact.pending_plan_id != pending_plan.pending_plan_id:
        raise ValueError("approval pending_plan_id mismatch")
    if approval_artifact.status != ApprovalStatus.APPROVED:
        return pending_plan
    return attach_approval_link(
        pending_plan,
        approval_path=f"approval_artifact/{approval_artifact.approval_id}.json",
        approval_hash=approval_artifact.approval_hash,
        approval_status=approval_artifact.status.value,
        approved_item_ids=approval_artifact.approved_item_ids,
        approval_expires_at=approval_artifact.expires_at,
        approved_order_conditions=approval_artifact.approved_order_conditions,
        planning_submit_feasibility_current=planning_submit_feasibility_current,
        planning_submit_feasibility_policy=planning_submit_feasibility_policy,
    )
