import pytest

from ai_fund_lab_v2.runtime_v2.approval.linkage import link_approval_to_pending
from ai_fund_lab_v2.runtime_v2.approval.models import ApprovalDecision, ApprovalStatus
from ai_fund_lab_v2.runtime_v2.approval.policy import (
    build_approval_artifact,
    build_approval_request,
)
from ai_fund_lab_v2.runtime_v2.pending.models import PendingPlanState
from tests.runtime_v2.pending_fixtures import make_pending_plan


def test_approved_artifact_links_pending_to_approved():
    pending = make_pending_plan()
    artifact = _artifact(pending, ApprovalStatus.APPROVED, ("item-1",))

    linked = link_approval_to_pending(pending_plan=pending, approval_artifact=artifact)

    assert linked.state == PendingPlanState.APPROVED
    assert linked.approval.approval_hash == artifact.approval_hash


def test_rejected_artifact_does_not_approve_pending():
    pending = make_pending_plan()
    artifact = _artifact(pending, ApprovalStatus.REJECTED, ())

    linked = link_approval_to_pending(pending_plan=pending, approval_artifact=artifact)

    assert linked.state == PendingPlanState.PENDING_APPROVAL
    assert linked.approval is None


def test_approved_item_ids_must_exist():
    pending = make_pending_plan()
    artifact = _artifact(pending, ApprovalStatus.APPROVED, ("missing",))

    with pytest.raises(ValueError, match="approved_item_ids"):
        link_approval_to_pending(pending_plan=pending, approval_artifact=artifact)


def test_approval_hash_is_stored_in_pending_as_evidence():
    pending = make_pending_plan()
    artifact = _artifact(pending, ApprovalStatus.APPROVED, ("item-1",))

    linked = link_approval_to_pending(pending_plan=pending, approval_artifact=artifact)

    assert linked.approval.approval_hash == artifact.approval_hash
    assert "approval_artifact" in linked.approval.approval_path


def _artifact(pending, status, approved_item_ids):
    request = build_approval_request(
        pending_plan=pending,
        business_date="2026-07-07",
        expires_at="2026-07-08T00:00:00Z",
    )
    return build_approval_artifact(
        request=request,
        decision=ApprovalDecision(
            status=status,
            approved_item_ids=approved_item_ids,
            rejected_item_ids=(),
            reason=status.value.lower(),
            operator="tester",
            decided_at="2026-07-07T01:00:00Z",
        ),
    )

