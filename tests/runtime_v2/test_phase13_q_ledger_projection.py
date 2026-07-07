import pytest

from ai_fund_lab_v2.runtime_v2.broker_readonly.normalizer import (
    normalize_broker_readonly_payload,
)
from ai_fund_lab_v2.runtime_v2.execution.ledger_projection import (
    project_cash_to_ledger_record,
    project_execution_to_ledger_record,
    project_order_to_ledger_record,
    project_position_to_ledger_record,
)
from ai_fund_lab_v2.runtime_v2.ledger.models import (
    LedgerCashRecord,
    LedgerExecutionRecord,
    LedgerOrderRecord,
    LedgerPositionRecord,
)


def test_broker_execution_projects_to_ledger_execution_record():
    execution = _bundle().executions[0]

    record = project_execution_to_ledger_record(execution)

    assert isinstance(record, LedgerExecutionRecord)
    assert record.dedup_key == execution.execution_ref_hash
    assert record.execution_id == execution.execution_ref_hash


def test_broker_position_projects_to_ledger_position_record():
    position = _bundle().positions[0]

    record = project_position_to_ledger_record(position)

    assert isinstance(record, LedgerPositionRecord)
    assert record.dedup_key == position.position_ref_hash
    assert record.symbol == "7203"


def test_broker_cash_projects_to_ledger_cash_record():
    cash = _bundle().cash

    record = project_cash_to_ledger_record(cash)

    assert isinstance(record, LedgerCashRecord)
    assert record.dedup_key == cash.cash_ref_hash
    assert record.cash == 100000


def test_broker_order_projects_only_to_ledger_order_record_not_position():
    order = _bundle().orders[0]

    record = project_order_to_ledger_record(order)

    assert isinstance(record, LedgerOrderRecord)
    assert not isinstance(record, LedgerPositionRecord)
    assert record.dedup_key == order.order_ref_hash


def test_broker_order_only_cannot_call_position_projection():
    order = _bundle().orders[0]

    with pytest.raises(AttributeError):
        project_position_to_ledger_record(order)


def test_broker_order_only_is_not_current_asset_state():
    order = _bundle().orders[0]

    assert not hasattr(order, "positions")
    assert not hasattr(order, "cash")


def _bundle():
    return normalize_broker_readonly_payload(
        environment="demo",
        source="broker_readonly",
        as_of="2026-07-07T00:00:00Z",
        orders=(
            {
                "order_ref": "ORDER-1",
                "pending_plan_id": "pending-1",
                "pending_item_id": "item-1",
                "symbol": "7203",
                "side": "BUY",
                "quantity": 100,
                "order_status": "accepted",
                "filled_quantity": 0,
                "remaining_quantity": 100,
            },
        ),
        executions=(
            {
                "execution_ref": "EXEC-1",
                "order_ref": "ORDER-1",
                "execution_key": "exec-key-1",
                "symbol": "7203",
                "side": "BUY",
                "quantity": 100,
                "price": 2500,
                "executed_at": "2026-07-07T00:01:00Z",
            },
        ),
        positions=(
            {
                "position_ref": "POS-1",
                "position_key": "7203",
                "symbol": "7203",
                "quantity": 100,
                "average_price": 2500,
                "market_value": 250000,
            },
        ),
        cash={"cash_ref": "CASH-1", "cash": 100000, "buying_power": 50000},
    )

