from ai_fund_lab_v2.runtime_v2.approval.models import (
    ApprovalDecision,
    ApprovalStatus,
)
from ai_fund_lab_v2.runtime_v2.approval.policy import (
    build_approval_artifact,
    build_approval_request,
)
from tests.runtime_v2.pending_fixtures import make_pending_plan


def test_approval_request_from_pending_plan():
    request = build_approval_request(
        pending_plan=make_pending_plan(),
        business_date="2026-07-07",
        expires_at="2026-07-08T00:00:00Z",
    )

    assert request.pending_plan_id == "pending-order-plan-1"
    assert request.requested_item_ids == ("item-1",)


def test_approval_artifact_from_decision_generates_hash():
    request = build_approval_request(
        pending_plan=make_pending_plan(),
        business_date="2026-07-07",
        expires_at="2026-07-08T00:00:00Z",
    )
    artifact = build_approval_artifact(
        request=request,
        decision=ApprovalDecision(
            status=ApprovalStatus.APPROVED,
            approved_item_ids=("item-1",),
            rejected_item_ids=(),
            reason="approved",
            operator="tester",
            decided_at="2026-07-07T01:00:00Z",
        ),
    )

    assert artifact.approval_hash.startswith("approval-hash-")
    assert artifact.approved_item_ids == ("item-1",)


def test_expired_approval_is_not_clean():
    request = build_approval_request(
        pending_plan=make_pending_plan(),
        business_date="2026-07-07",
        expires_at="2026-07-08T00:00:00Z",
    )
    artifact = build_approval_artifact(
        request=request,
        decision=ApprovalDecision(
            status=ApprovalStatus.EXPIRED,
            approved_item_ids=(),
            rejected_item_ids=("item-1",),
            reason="expired",
            operator="tester",
            decided_at="2026-07-09T00:00:00Z",
        ),
    )

    assert artifact.review_required is True
    assert artifact.status == ApprovalStatus.EXPIRED


def test_approval_artifact_is_evidence_only():
    request = build_approval_request(
        pending_plan=make_pending_plan(),
        business_date="2026-07-07",
        expires_at="2026-07-08T00:00:00Z",
    )
    artifact = build_approval_artifact(
        request=request,
        decision=ApprovalDecision(
            status=ApprovalStatus.APPROVED,
            approved_item_ids=("item-1",),
            rejected_item_ids=(),
            reason="approved",
            operator="tester",
            decided_at="2026-07-07T01:00:00Z",
        ),
    )

    assert not hasattr(artifact, "submit_target")
    assert not hasattr(artifact, "broker_order")

