from ai_fund_lab_v2.broker.runtime_v2_demo_submit_adapter import RuntimeV2TachibanaDemoSubmitAdapter
from ai_fund_lab_v2.broker.settings import BrokerSettings
from ai_fund_lab_v2.broker.tachibana_order_request import TachibanaCashStockOrderRequest
from ai_fund_lab_v2.runtime_v2.approval.linkage import link_approval_to_pending
from ai_fund_lab_v2.runtime_v2.approval.models import ApprovalArtifact, ApprovalStatus
from ai_fund_lab_v2.runtime_v2.pending.models import PendingOrderItem
from ai_fund_lab_v2.runtime_v2.pending.promotion import promote_order_plan_to_pending
from ai_fund_lab_v2.runtime_v2.submit.guards import run_submit_preflight


def test_phase14d14_sell_preflight_allows_7203_with_position_and_available_quantity():
    pending, approval = _approved_sell_pending(quantity=100, estimated_amount=294100)

    preflight = run_submit_preflight(
        pending_plan=pending,
        approval_artifact=approval,
        approved_item_id="phase14d14-sell-7203-100",
        existing_order_dedup_keys=set(),
        environment="demo",
        base_url_is_demo=True,
        base_url_is_production=False,
        live_order_allowed=True,
        broker_position_quantity=100,
        broker_available_quantity=100,
    )

    assert preflight.allowed is True
    assert preflight.command is not None
    assert preflight.command.symbol == "7203"
    assert preflight.command.side == "SELL"
    assert preflight.command.quantity == 100
    assert preflight.command.source_current_path == "pending_order_plan/pending_order_plan.json"


def test_phase14d14_sell_quantity_guard_blocks_position_quantity_overrun():
    pending, approval = _approved_sell_pending(quantity=101, estimated_amount=297041)

    preflight = run_submit_preflight(
        pending_plan=pending,
        approval_artifact=approval,
        approved_item_id="phase14d14-sell-7203-100",
        existing_order_dedup_keys=set(),
        environment="demo",
        base_url_is_demo=True,
        base_url_is_production=False,
        live_order_allowed=True,
        broker_position_quantity=100,
        broker_available_quantity=100,
    )

    assert preflight.blocked is True
    assert preflight.reason == "sell quantity exceeds broker position"


def test_phase14d14_sell_quantity_guard_blocks_available_quantity_overrun():
    pending, approval = _approved_sell_pending(quantity=100, estimated_amount=294100)

    preflight = run_submit_preflight(
        pending_plan=pending,
        approval_artifact=approval,
        approved_item_id="phase14d14-sell-7203-100",
        existing_order_dedup_keys=set(),
        environment="demo",
        base_url_is_demo=True,
        base_url_is_production=False,
        live_order_allowed=True,
        broker_position_quantity=100,
        broker_available_quantity=99,
    )

    assert preflight.blocked is True
    assert preflight.reason == "sell quantity exceeds available quantity"


def test_phase14d14_sell_preflight_keeps_approval_and_duplicate_guards():
    pending, approval = _approved_sell_pending(quantity=100, estimated_amount=294100)

    duplicate = run_submit_preflight(
        pending_plan=pending,
        approval_artifact=approval,
        approved_item_id="phase14d14-sell-7203-100",
        existing_order_dedup_keys={pending.pending_plan_id},
        environment="demo",
        base_url_is_demo=True,
        base_url_is_production=False,
        live_order_allowed=True,
        broker_position_quantity=100,
        broker_available_quantity=100,
    )
    rejected_approval = ApprovalArtifact(
        approval_id=approval.approval_id,
        approval_request_id=approval.approval_request_id,
        pending_plan_id=approval.pending_plan_id,
        order_plan_id=approval.order_plan_id,
        status=ApprovalStatus.REJECTED,
        approved_item_ids=(),
        rejected_item_ids=("phase14d14-sell-7203-100",),
        approval_hash=approval.approval_hash,
        approved_at=approval.approved_at,
        expires_at=approval.expires_at,
        review_required=True,
        reason="operator rejected",
    )
    rejected = run_submit_preflight(
        pending_plan=pending,
        approval_artifact=rejected_approval,
        approved_item_id="phase14d14-sell-7203-100",
        existing_order_dedup_keys=set(),
        environment="demo",
        base_url_is_demo=True,
        base_url_is_production=False,
        live_order_allowed=True,
        broker_position_quantity=100,
        broker_available_quantity=100,
    )

    assert duplicate.blocked is True
    assert duplicate.reason == "duplicate submit guard or pending lifecycle blocked"
    assert rejected.blocked is True
    assert rejected.reason == "approval artifact is not APPROVED"


def test_phase14d14_adapter_dry_run_accepts_runtime_v2_sell_without_broker_api():
    pending, approval = _approved_sell_pending(quantity=100, estimated_amount=294100)
    preflight = run_submit_preflight(
        pending_plan=pending,
        approval_artifact=approval,
        approved_item_id="phase14d14-sell-7203-100",
        existing_order_dedup_keys=set(),
        environment="demo",
        base_url_is_demo=True,
        base_url_is_production=False,
        live_order_allowed=True,
        broker_position_quantity=100,
        broker_available_quantity=100,
    )

    assert preflight.command is not None
    adapter = RuntimeV2TachibanaDemoSubmitAdapter(settings=_demo_settings())
    result = adapter.submit(preflight.command)
    request = TachibanaCashStockOrderRequest.from_runtime_v2_submit_command(
        preflight.command,
        second_password_present=True,
    )

    assert result.status == "DRY_RUN_READY"
    assert result.submitted is False
    assert result.broker_api_called is False
    assert result.raw_request_saved is False
    assert result.raw_response_saved is False
    assert "CLMKabuNewOrder" in result.reason
    assert request.safe_metadata()["side"] == "SELL"


def _approved_sell_pending(quantity: float, estimated_amount: float):
    pending = promote_order_plan_to_pending(
        order_plan_id="phase14d14-order-plan",
        source_order_plan_path="order_plan/history.json",
        source_order_plan_hash="sha256:phase14d14-order",
        environment="demo",
        plan_created_date="2026-07-07",
        intended_submit_date="2026-07-07",
        target_session_date="2026-07-07",
        items=(
            PendingOrderItem(
                pending_item_id="phase14d14-sell-7203-100",
                symbol="7203",
                side="SELL",
                quantity=quantity,
                order_type="MARKET",
                estimated_price=2941,
                estimated_amount=estimated_amount,
                approved=False,
                state="PENDING_APPROVAL",
                listed_info={
                    "code": "7203",
                    "market": "プライム",
                    "product_category": "011",
                    "security_type": "011",
                    "current_listed": True,
                },
            ),
        ),
    )
    approval = ApprovalArtifact(
        approval_id="phase14d14-approval",
        approval_request_id="phase14d14-approval-request",
        pending_plan_id=pending.pending_plan_id,
        order_plan_id=pending.source_order_plan.order_plan_id,
        status=ApprovalStatus.APPROVED,
        approved_item_ids=("phase14d14-sell-7203-100",),
        rejected_item_ids=(),
        approval_hash="sha256:phase14d14-approval",
        approved_at="2026-07-07T09:00:00+09:00",
        expires_at="2026-07-07T15:00:00+09:00",
        review_required=False,
        reason="phase14d14 sell guarded preflight",
    )
    return link_approval_to_pending(pending_plan=pending, approval_artifact=approval), approval


def _demo_settings():
    return BrokerSettings(
        environment="demo",
        base_url="https://demo-kabuka.e-shiten.jp/e_api_v4r9",
        second_password_file="/tmp/phase14d14-second-password",
    )
