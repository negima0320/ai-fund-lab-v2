from ai_fund_lab_v2.runtime_v2.approval.linkage import link_approval_to_pending
from ai_fund_lab_v2.runtime_v2.approval.models import ApprovalArtifact, ApprovalStatus
from ai_fund_lab_v2.runtime_v2.broker_adapter.fake_demo_submit import FakeRuntimeV2DemoSubmitAdapter
from ai_fund_lab_v2.runtime_v2.pending.models import PendingOrderItem, PendingPlanState
from ai_fund_lab_v2.runtime_v2.pending.promotion import promote_order_plan_to_pending
from ai_fund_lab_v2.runtime_v2.submit.guards import run_submit_preflight


def test_phase14d3_pure_submit_path_accepts_runtime_v2_command_without_legacy_runtime():
    pending, approval = _approved_pending()
    preflight = run_submit_preflight(
        pending_plan=pending,
        approval_artifact=approval,
        approved_item_id="item-1",
        existing_order_dedup_keys=set(),
        environment="demo",
        base_url_is_demo=True,
        base_url_is_production=False,
        live_order_allowed=True,
    )

    assert preflight.allowed is True
    assert preflight.command is not None
    assert preflight.command.source_current_path == "pending_order_plan/pending_order_plan.json"
    assert preflight.command.pending_plan_id == pending.pending_plan_id
    assert preflight.command.approval_hash == approval.approval_hash

    result = FakeRuntimeV2DemoSubmitAdapter().submit(preflight.command)

    assert result.accepted is True
    assert result.broker_api_called is False
    assert result.raw_request_saved is False
    assert result.raw_response_saved is False


def test_phase14d3_preflight_blocks_without_approval_link():
    pending, approval = _approved_pending()
    pending_without_link = promote_order_plan_to_pending(
        order_plan_id="order-plan-1",
        source_order_plan_path="order_plan/history.json",
        source_order_plan_hash="sha256:order",
        environment="demo",
        plan_created_date="2026-07-07",
        intended_submit_date="2026-07-07",
        target_session_date="2026-07-07",
        items=pending.items,
    )

    preflight = run_submit_preflight(
        pending_plan=pending_without_link,
        approval_artifact=approval,
        approved_item_id="item-1",
        existing_order_dedup_keys=set(),
        environment="demo",
        base_url_is_demo=True,
        base_url_is_production=False,
        live_order_allowed=True,
    )

    assert preflight.blocked is True
    assert preflight.reason == "pending state is not APPROVED"


def test_phase14d3_preflight_blocks_duplicate_pending_plan():
    pending, approval = _approved_pending()

    preflight = run_submit_preflight(
        pending_plan=pending,
        approval_artifact=approval,
        approved_item_id="item-1",
        existing_order_dedup_keys={pending.pending_plan_id},
        environment="demo",
        base_url_is_demo=True,
        base_url_is_production=False,
        live_order_allowed=True,
    )

    assert preflight.blocked is True
    assert preflight.reason == "duplicate submit guard or pending lifecycle blocked"


def test_phase14d3_preflight_blocks_production_endpoint_and_non_pending_source():
    pending, approval = _approved_pending()

    production = run_submit_preflight(
        pending_plan=pending,
        approval_artifact=approval,
        approved_item_id="item-1",
        existing_order_dedup_keys=set(),
        environment="production",
        base_url_is_demo=False,
        base_url_is_production=True,
        live_order_allowed=True,
    )
    history_source = run_submit_preflight(
        pending_plan=pending,
        approval_artifact=approval,
        approved_item_id="item-1",
        existing_order_dedup_keys=set(),
        environment="demo",
        base_url_is_demo=True,
        base_url_is_production=False,
        live_order_allowed=True,
        source_current_path="order_plan/2026-07-07/order_plan.json",
    )

    assert production.blocked is True
    assert production.reason == "environment guard failure"
    assert history_source.blocked is True
    assert history_source.reason == "submit source must be pending_order_plan current"


def _approved_pending():
    pending = promote_order_plan_to_pending(
        order_plan_id="order-plan-1",
        source_order_plan_path="order_plan/history.json",
        source_order_plan_hash="sha256:order",
        environment="demo",
        plan_created_date="2026-07-07",
        intended_submit_date="2026-07-07",
        target_session_date="2026-07-07",
        items=(
            PendingOrderItem(
                pending_item_id="item-1",
                symbol="7203",
                side="BUY",
                quantity=100,
                order_type="MARKET",
                estimated_price=200,
                estimated_amount=20000,
                approved=False,
                state="PENDING_APPROVAL",
            ),
        ),
    )
    approval = ApprovalArtifact(
        approval_id="approval-1",
        approval_request_id="approval-request-1",
        pending_plan_id=pending.pending_plan_id,
        order_plan_id=pending.source_order_plan.order_plan_id,
        status=ApprovalStatus.APPROVED,
        approved_item_ids=("item-1",),
        rejected_item_ids=(),
        approval_hash="sha256:approval",
        approved_at="2026-07-07",
        expires_at="2026-07-07",
        review_required=False,
        reason="test approval",
    )
    return link_approval_to_pending(pending_plan=pending, approval_artifact=approval), approval
