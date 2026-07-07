from ai_fund_lab_v2.runtime_v2.planning.models import PlanningDecisionStatus
from ai_fund_lab_v2.runtime_v2.planning.planner import build_order_plan
from tests.runtime_v2.planning_fixtures import (
    make_asset_state,
    make_planning_input,
    make_position,
)


def test_missing_asset_state_prevents_buy_plan():
    input = make_planning_input()
    input = input.__class__(**{**input.__dict__, "asset_state": None})

    result = build_order_plan(input)

    assert result.status == PlanningDecisionStatus.BLOCKED
    assert result.order_plan.items == ()


def test_unknown_positions_prevents_clean_plan():
    result = build_order_plan(
        make_planning_input(
            asset_state=make_asset_state(
                positions=None,
                current_positions_unknown=True,
            )
        )
    )

    assert result.order_plan.items[0].review_required is True
    assert result.status == PlanningDecisionStatus.REVIEW_REQUIRED


def test_confirmed_empty_with_cash_can_create_buy_plan():
    result = build_order_plan(
        make_planning_input(
            asset_state=make_asset_state(
                positions=(),
                confirmed_empty=True,
                cash=100000,
                buying_power=100000,
            )
        )
    )

    assert result.status == PlanningDecisionStatus.CREATED
    assert result.blocked is False


def test_orders_alone_are_not_asset_source():
    state = make_asset_state(positions=(make_position(),))

    assert not hasattr(state, "orders")

