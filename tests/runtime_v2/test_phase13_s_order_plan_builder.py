from ai_fund_lab_v2.runtime_v2.planning.models import PlanningDecisionStatus
from ai_fund_lab_v2.runtime_v2.planning.planner import build_order_plan
from tests.runtime_v2.planning_fixtures import (
    make_ai_signal,
    make_allocation,
    make_asset_state,
    make_planning_input,
    make_safety,
)


def test_valid_input_creates_order_plan():
    result = build_order_plan(make_planning_input())

    assert result.status == PlanningDecisionStatus.CREATED
    assert result.order_plan.items
    assert result.blocked is False
    assert result.review_required is False


def test_asset_state_missing_blocks_plan():
    input = make_planning_input(asset_state=None)
    input = input.__class__(**{**input.__dict__, "asset_state": None})

    result = build_order_plan(input)

    assert result.status == PlanningDecisionStatus.BLOCKED
    assert result.review_required is True
    assert result.blocked is True


def test_cash_unknown_blocks_buy_item():
    result = build_order_plan(
        make_planning_input(asset_state=make_asset_state(cash=None, cash_unknown=True))
    )

    assert result.order_plan.items[0].blocked is True
    assert "cash unknown" in result.order_plan.items[0].reason


def test_buying_power_unknown_blocks_buy_item():
    result = build_order_plan(
        make_planning_input(
            asset_state=make_asset_state(buying_power=None, buying_power_unknown=True)
        )
    )

    assert result.order_plan.items[0].blocked is True
    assert "buying power unknown" in result.order_plan.items[0].reason


def test_safety_blocked_item_is_blocked():
    result = build_order_plan(
        make_planning_input(safety_signals=(make_safety(allowed=False, blocked=True),))
    )

    assert result.order_plan.items[0].blocked is True


def test_safety_review_required_item_is_review_required():
    result = build_order_plan(
        make_planning_input(safety_signals=(make_safety(review_required=True),))
    )

    assert result.order_plan.items[0].review_required is True
    assert result.review_required is True


def test_cash_required_above_buying_power_blocks_item():
    result = build_order_plan(
        make_planning_input(
            asset_state=make_asset_state(buying_power=1000),
            capital_allocations=(make_allocation(cash_required=50000),),
        )
    )

    assert result.order_plan.items[0].blocked is True
    assert "cash_required exceeds buying_power" in result.order_plan.items[0].reason


def test_runtime_does_not_truncate_to_five_symbols():
    signals = tuple(make_ai_signal(symbol=f"7{i:03d}", rank=i) for i in range(1, 7))
    allocations = tuple(make_allocation(symbol=signal.symbol) for signal in signals)
    safety = tuple(make_safety(symbol=signal.symbol) for signal in signals)

    result = build_order_plan(
        make_planning_input(
            ai_signals=signals,
            capital_allocations=allocations,
            safety_signals=safety,
        )
    )

    assert len(result.order_plan.items) == 6
    assert [item.source_signal_id for item in result.order_plan.items] == [
        signal.signal_id for signal in signals
    ]

