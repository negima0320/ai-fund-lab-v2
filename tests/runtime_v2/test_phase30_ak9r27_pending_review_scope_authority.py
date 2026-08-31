from dataclasses import replace

from ai_fund_lab_v2.runtime_v2.pending.consume import can_submit_pending_plan
from ai_fund_lab_v2.runtime_v2.pending.models import PendingApprovalLink, PendingOrderItem, PendingPlanState
from ai_fund_lab_v2.runtime_v2.pending.review_scope_authority import (
    REVIEWED_SELL_PRESENT,
    TRUE_BATCH_CASH_FAILURE,
    build_pending_review_scope_authority,
    pending_scope_allows_current_valuation_residual,
    pending_scope_allows_partial_submit,
    pending_scope_allows_sell_continuation,
)
from tests.runtime_v2.pending_fixtures import make_pending_plan


def test_ak9r27_normal_approved_pending_exposes_executable_item():
    plan = _plan_with_items(
        state=PendingPlanState.APPROVED,
        approved_ids=("buy-pass",),
        items=(_item("buy-pass", approved=True, state="APPROVED"),),
        feasibility_status="PASS",
    )

    authority = build_pending_review_scope_authority(plan)

    assert authority.executable_item_ids == ("buy-pass",)
    assert authority.partial_submit_allowed is False
    assert authority.batch_blocked is False


def test_ak9r27_reviewed_buy_never_enters_executable_subset():
    plan = _plan_with_items(
        state=PendingPlanState.REVIEW_REQUIRED,
        approved_ids=("buy-pass",),
        approved_buy_ids=("buy-pass",),
        review_buy_ids=("buy-review",),
        review_scope="BUY_ITEM_SCOPED_REVIEW",
        sell_continuation_allowed=True,
        items=(
            _item("buy-pass", approved=True, state="APPROVED"),
            _item("buy-review", approved=False, state="REVIEW_REQUIRED"),
        ),
        feasibility_items=(
            _feasibility("buy-pass", "BUY", "PASS"),
            _feasibility("buy-review", "BUY", "REVIEW_REQUIRED", violated_policy="reserved_cash"),
        ),
    )

    authority = build_pending_review_scope_authority(plan)

    assert pending_scope_allows_partial_submit(authority) is True
    assert authority.executable_buy_item_ids == ("buy-pass",)
    assert authority.reviewed_buy_item_ids == ("buy-review",)
    assert "buy-review" not in authority.executable_item_ids
    assert can_submit_pending_plan(plan, set()) is True


def test_ak9r27_reviewed_buy_plus_approved_sell_preserves_sell_continuation():
    plan = _plan_with_items(
        state=PendingPlanState.REVIEW_REQUIRED,
        approved_ids=("sell-pass",),
        approved_sell_ids=("sell-pass",),
        review_buy_ids=("buy-review",),
        review_scope="BUY_ITEM_SCOPED_REVIEW",
        sell_continuation_allowed=True,
        items=(
            _item("sell-pass", side="SELL", approved=True, state="APPROVED"),
            _item("buy-review", approved=False, state="REVIEW_REQUIRED"),
        ),
        feasibility_items=(
            _feasibility("sell-pass", "SELL", "PASS"),
            _feasibility("buy-review", "BUY", "REVIEW_REQUIRED", violated_policy="reserved_cash"),
        ),
    )

    authority = build_pending_review_scope_authority(plan)

    assert authority.executable_sell_item_ids == ("sell-pass",)
    assert pending_scope_allows_sell_continuation(
        authority,
        business_date="2026-07-08",
        mode="demo",
        environment="demo",
        readiness_scope="sell_planning",
    )


def test_ak9r27_approved_buy_sell_reviewed_buy_is_partial_submit_allowed():
    plan = _plan_with_items(
        state=PendingPlanState.REVIEW_REQUIRED,
        approved_ids=("buy-pass", "sell-pass"),
        approved_buy_ids=("buy-pass",),
        approved_sell_ids=("sell-pass",),
        review_buy_ids=("buy-review",),
        review_scope="BUY_ITEM_SCOPED_REVIEW",
        sell_continuation_allowed=True,
        items=(
            _item("buy-pass", approved=True, state="APPROVED"),
            _item("sell-pass", side="SELL", approved=True, state="APPROVED"),
            _item("buy-review", approved=False, state="REVIEW_REQUIRED"),
        ),
        feasibility_items=(
            _feasibility("buy-pass", "BUY", "PASS"),
            _feasibility("sell-pass", "SELL", "PASS"),
            _feasibility("buy-review", "BUY", "REVIEW_REQUIRED", violated_policy="dynamic_cash"),
        ),
    )

    authority = build_pending_review_scope_authority(plan)

    assert pending_scope_allows_partial_submit(authority) is True
    assert authority.executable_item_ids == ("buy-pass", "sell-pass")
    assert authority.reviewed_items_must_not_submit is True


def test_ak9r27_reviewed_sell_is_true_batch_block():
    plan = _plan_with_items(
        state=PendingPlanState.REVIEW_REQUIRED,
        approved_ids=("buy-pass",),
        approved_buy_ids=("buy-pass",),
        review_sell_ids=("sell-review",),
        review_scope="BUY_ITEM_SCOPED_REVIEW",
        sell_continuation_allowed=True,
        items=(
            _item("buy-pass", approved=True, state="APPROVED"),
            _item("sell-review", side="SELL", approved=False, state="REVIEW_REQUIRED"),
        ),
        feasibility_items=(
            _feasibility("buy-pass", "BUY", "PASS"),
            _feasibility("sell-review", "SELL", "REVIEW_REQUIRED", violated_policy="sell_available_quantity"),
        ),
    )

    authority = build_pending_review_scope_authority(plan)

    assert authority.batch_blocked is True
    assert authority.batch_block_reason == REVIEWED_SELL_PRESENT
    assert pending_scope_allows_partial_submit(authority) is False
    assert can_submit_pending_plan(plan, set()) is False


def test_phase32_ax_mixed_sell_review_allows_independent_pass_sell_only():
    plan = _plan_with_items(
        state=PendingPlanState.REVIEW_REQUIRED,
        approved_ids=("sell-pass",),
        approved_sell_ids=("sell-pass",),
        review_buy_ids=("buy-review",),
        review_sell_ids=("sell-review",),
        review_scope="MIXED_SELL_ITEM_SCOPED_REVIEW",
        sell_continuation_allowed=True,
        items=(
            _item("sell-pass", side="SELL", approved=True, state="APPROVED"),
            _item("buy-review", side="BUY", approved=False, state="REVIEW_REQUIRED"),
            _item("sell-review", side="SELL", approved=False, state="REVIEW_REQUIRED"),
        ),
        feasibility_items=(
            _feasibility("sell-pass", "SELL", "PASS"),
            _feasibility("buy-review", "BUY", "REVIEW_REQUIRED", violated_policy="reserved_cash"),
            _feasibility(
                "sell-review",
                "SELL",
                "REVIEW_REQUIRED",
                violated_policy="corporate_action_adjustment_authority",
            ),
        ),
    )

    authority = build_pending_review_scope_authority(plan)

    assert authority.batch_blocked is False
    assert authority.executable_item_ids == ("sell-pass",)
    assert authority.executable_sell_item_ids == ("sell-pass",)
    assert authority.executable_buy_item_ids == ()
    assert authority.reviewed_buy_item_ids == ("buy-review",)
    assert authority.reviewed_sell_item_ids == ("sell-review",)
    assert pending_scope_allows_partial_submit(authority) is True
    assert pending_scope_allows_sell_continuation(
        authority,
        business_date="2026-07-08",
        mode="demo",
        environment="demo",
        readiness_scope="sell_planning",
    )
    assert can_submit_pending_plan(plan, set()) is True


def test_ak9r27_aggregate_cash_remains_batch_blocked():
    plan = _plan_with_items(
        state=PendingPlanState.REVIEW_REQUIRED,
        approved_ids=("buy-pass",),
        approved_buy_ids=("buy-pass",),
        review_buy_ids=("buy-review",),
        review_scope="BUY_ITEM_SCOPED_REVIEW",
        sell_continuation_allowed=True,
        items=(
            _item("buy-pass", approved=True, state="APPROVED"),
            _item("buy-review", approved=False, state="REVIEW_REQUIRED"),
        ),
        feasibility_items=(
            _feasibility("buy-pass", "BUY", "PASS"),
            _feasibility("buy-review", "BUY", "REVIEW_REQUIRED", violated_policy="aggregate_cash"),
        ),
    )

    authority = build_pending_review_scope_authority(plan)

    assert authority.batch_blocked is True
    assert authority.batch_block_reason == TRUE_BATCH_CASH_FAILURE
    assert pending_scope_allows_partial_submit(authority) is False


def test_ak9r27_malformed_reviewed_item_marked_approved_fails_closed():
    plan = _plan_with_items(
        state=PendingPlanState.REVIEW_REQUIRED,
        approved_ids=("buy-pass",),
        approved_buy_ids=("buy-pass",),
        review_buy_ids=("buy-review",),
        review_scope="BUY_ITEM_SCOPED_REVIEW",
        sell_continuation_allowed=True,
        items=(
            _item("buy-pass", approved=True, state="APPROVED"),
            _item("buy-review", approved=True, state="REVIEW_REQUIRED"),
        ),
        feasibility_items=(
            _feasibility("buy-pass", "BUY", "PASS"),
            _feasibility("buy-review", "BUY", "REVIEW_REQUIRED", violated_policy="reserved_cash"),
        ),
    )

    authority = build_pending_review_scope_authority(plan)

    assert authority.structural_validity == "REVIEW_REQUIRED"
    assert "reviewed_item_flag_true" in authority.malformed_reasons
    assert pending_scope_allows_partial_submit(authority) is False


def test_ak9r27_next_day_residual_review_requires_adapter_context():
    plan = _plan_with_items(
        state=PendingPlanState.REVIEW_REQUIRED,
        approved_ids=("buy-consumed",),
        approved_buy_ids=("buy-consumed",),
        review_buy_ids=("buy-review",),
        review_scope="BUY_ITEM_SCOPED_REVIEW",
        sell_continuation_allowed=True,
        items=(
            _item("buy-consumed", approved=True, state="CONSUMED"),
            _item("buy-review", approved=False, state="REVIEW_REQUIRED", batch_submit_status="ITEM_REVIEW_REQUIRED"),
        ),
        feasibility_items=(
            _feasibility("buy-consumed", "BUY", "PASS"),
            _feasibility("buy-review", "BUY", "REVIEW_REQUIRED", violated_policy="quality_review"),
        ),
    )

    authority = build_pending_review_scope_authority(plan)

    assert pending_scope_allows_current_valuation_residual(
        authority,
        business_date="2026-07-08",
        mode="demo",
        environment="demo",
    )
    assert authority.reviewed_buy_item_ids == ("buy-review",)
    assert authority.executable_item_ids == ("buy-consumed",)


def _plan_with_items(
    *,
    state: PendingPlanState,
    approved_ids: tuple[str, ...],
    items: tuple[PendingOrderItem, ...],
    approved_buy_ids: tuple[str, ...] = (),
    approved_sell_ids: tuple[str, ...] = (),
    review_buy_ids: tuple[str, ...] = (),
    review_sell_ids: tuple[str, ...] = (),
    review_scope: str = "",
    sell_continuation_allowed: bool = False,
    feasibility_status: str = "REVIEW_REQUIRED",
    feasibility_items: tuple[dict, ...] = (),
):
    return replace(
        make_pending_plan(state=state),
        environment="demo",
        target_session_date="2026-07-08",
        approval=PendingApprovalLink(
            approval_path="approval.json",
            approval_hash="approval-hash",
            approval_status="APPROVED",
            approved_item_ids=approved_ids,
            approval_expires_at="2026-07-08T00:00:00Z",
        ),
        approved_item_ids=approved_ids,
        approved_buy_item_ids=approved_buy_ids,
        approved_sell_item_ids=approved_sell_ids,
        review_required_buy_item_ids=review_buy_ids,
        review_required_sell_item_ids=review_sell_ids,
        review_scope=review_scope,
        review_scope_source="planning_submit_feasibility",
        review_scope_reason="phase30_ak9r27_test",
        sell_continuation_allowed=sell_continuation_allowed,
        planning_submit_feasibility={"status": feasibility_status, "items": list(feasibility_items)},
        items=items,
    )


def _item(
    pending_item_id: str,
    *,
    side: str = "BUY",
    approved: bool,
    state: str,
    batch_submit_status: str = "PASS_ITEM_SUBMITTABLE",
) -> PendingOrderItem:
    return PendingOrderItem(
        pending_item_id=pending_item_id,
        symbol="7203" if side == "BUY" else "6758",
        side=side,
        quantity=100,
        order_type="MARKET",
        estimated_price=1000,
        estimated_amount=100000,
        approved=approved,
        state=state,
        batch_submit_status=batch_submit_status,
    )


def _feasibility(
    pending_item_id: str,
    side: str,
    status: str,
    *,
    violated_policy: str = "",
) -> dict:
    return {
        "pending_item_id": pending_item_id,
        "side": side,
        "status": status,
        "violated_policy": violated_policy,
        "violated_policy_source": "phase30_ak9r27_test" if violated_policy else "",
    }
