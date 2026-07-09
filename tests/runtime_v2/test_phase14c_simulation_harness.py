import pytest

from ai_fund_lab_v2.runtime_v2.asset.builder import build_current_asset_state_from_orders
from ai_fund_lab_v2.runtime_v2.pending.models import PendingOrderItem
from ai_fund_lab_v2.runtime_v2.simulation.broker import SimulationBroker
from ai_fund_lab_v2.runtime_v2.simulation.harness import run_simulation_replay
from ai_fund_lab_v2.runtime_v2.simulation.models import (
    SimulationBrokerPosition,
    SimulationBrokerState,
    SimulationOrderInstruction,
)


def test_simulation_harness_replays_buy_sell_and_full_exit_across_days():
    result = run_simulation_replay(
        initial_state=SimulationBrokerState(cash=100000, buying_power=100000),
        instructions=(
            SimulationOrderInstruction("2026-07-08", "7203", "BUY", 10, 1000),
            SimulationOrderInstruction("2026-07-09", "7203", "SELL", 4, 1200),
            SimulationOrderInstruction("2026-07-10", "7203", "SELL", 6, 1100),
        ),
    )

    assert result.status == "PASS"
    assert result.broker_api_called is False
    assert result.production_order_executed is False
    assert result.notification_send_executed is False
    assert result.ledger_order_count == 3
    assert result.ledger_execution_count == 3

    buy_day, partial_sell_day, full_sell_day = result.day_results
    assert buy_day.submit_status == "ACCEPTED"
    assert buy_day.pending_state == "CONSUMED"
    assert buy_day.fill_classification == "FULL_FILL"
    assert buy_day.asset_cash == 90000
    assert _position_quantity(buy_day.asset_positions, "7203") == 10

    assert partial_sell_day.submit_status == "ACCEPTED"
    assert partial_sell_day.realized_pnl == 800
    assert partial_sell_day.asset_cash == 94800
    assert _position_quantity(partial_sell_day.asset_positions, "7203") == 6

    assert full_sell_day.submit_status == "ACCEPTED"
    assert full_sell_day.realized_pnl == 600
    assert full_sell_day.asset_cash == 101400
    assert _position_quantity(full_sell_day.asset_positions, "7203") == 0
    assert full_sell_day.report_sections == 10
    assert full_sell_day.notification_payload_created is True


def test_simulation_harness_blocks_sell_quantity_above_broker_position():
    result = run_simulation_replay(
        initial_state=SimulationBrokerState(
            cash=100000,
            buying_power=100000,
            positions=(
                SimulationBrokerPosition("6758", 5, 1000, 5000),
            ),
        ),
        instructions=(
            SimulationOrderInstruction("2026-07-08", "6758", "SELL", 6, 1100),
        ),
    )

    day = result.day_results[0]
    assert day.submit_status == "BLOCKED"
    assert day.blocked is True
    assert day.ledger_order_count == 0
    assert _position_quantity(day.asset_positions, "6758") == 5


def test_simulation_broker_blocks_duplicate_submit_and_post_send_unknown_resubmit():
    broker = SimulationBroker(SimulationBrokerState(cash=100000, buying_power=100000))
    item = PendingOrderItem(
        pending_item_id="item-1",
        symbol="7203",
        side="BUY",
        quantity=1,
        order_type="MARKET",
        estimated_price=1000,
        estimated_amount=1000,
        approved=True,
        state="APPROVED",
    )

    first = broker.submit(pending_plan_id="pending-1", item=item, business_date="2026-07-08")
    second = broker.submit(pending_plan_id="pending-1", item=item, business_date="2026-07-08")
    unknown = broker.submit(
        pending_plan_id="pending-2",
        item=PendingOrderItem(
            pending_item_id="item-2",
            symbol="7203",
            side="BUY",
            quantity=1,
            order_type="MARKET",
            estimated_price=1000,
            estimated_amount=1000,
            approved=True,
            state="POST_SEND_UNKNOWN",
        ),
        business_date="2026-07-08",
    )

    assert first.status == "ACCEPTED"
    assert second.status == "BLOCKED"
    assert second.reason == "duplicate pending item submit"
    assert unknown.status == "REVIEW_REQUIRED"
    assert unknown.post_send_unknown is True


def test_simulation_harness_supports_buy_sell_mixed_path_without_order_only_asset():
    result = run_simulation_replay(
        initial_state=SimulationBrokerState(
            cash=50000,
            buying_power=50000,
            positions=(
                SimulationBrokerPosition("6758", 5, 1000, 5000),
            ),
        ),
        instructions=(
            SimulationOrderInstruction("2026-07-08", "7203", "BUY", 1, 2000),
            SimulationOrderInstruction("2026-07-08", "6758", "SELL", 2, 1100),
        ),
    )

    assert [day.order_side for day in result.day_results] == ["BUY", "SELL"]
    assert all(day.submit_status == "ACCEPTED" for day in result.day_results)
    assert _position_quantity(result.final_positions, "7203") == 1
    assert _position_quantity(result.final_positions, "6758") == 3
    with pytest.raises(ValueError, match="orders alone cannot build CurrentAssetState"):
        build_current_asset_state_from_orders()


def _position_quantity(positions, symbol):
    for position in positions:
        if position.symbol == symbol:
            return position.quantity
    return 0
