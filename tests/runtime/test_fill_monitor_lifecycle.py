from __future__ import annotations

from decimal import Decimal

import pytest

from ai_fund_lab_v2.runtime import FillEvent, FillMonitor, OrderLifecycle, RuntimeContext, RuntimeMode, RuntimeState, RuntimeStateMachine
from ai_fund_lab_v2.runtime.order_command import OrderSide


def test_accepted_waiting_fill() -> None:
    result = FillMonitor().classify(context=_context(), order=_order(status_code="1", filled="0"))

    assert result.lifecycle_status is OrderLifecycle.WAITING_FILL
    assert result.runtime_next_state is RuntimeState.WAITING_FILL
    assert result.filled is False
    assert result.events[0].remaining_quantity == Decimal("100")


def test_partial_fill() -> None:
    result = FillMonitor().classify(
        context=_context(),
        order=_order(status_code="9", filled="50"),
        detail={"fills": [{"quantity": "50", "price": "2000", "executed_at": "20260629090500"}]},
    )

    assert result.lifecycle_status is OrderLifecycle.PARTIALLY_FILLED
    assert result.runtime_next_state is RuntimeState.PARTIALLY_FILLED
    assert result.partially_filled is True
    assert result.events[0].filled_quantity == Decimal("50")
    assert result.events[0].latest_fill_price == Decimal("2000")


def test_full_fill() -> None:
    result = FillMonitor().classify(
        context=_context(),
        order=_order(status_code="10", filled="100"),
        detail={"fills": [{"quantity": "100", "price": "2010", "executed_at": "20260629090600"}]},
        position={"quantity": "100"},
    )

    assert result.lifecycle_status is OrderLifecycle.FILLED
    assert result.runtime_next_state is RuntimeState.FILLED
    assert result.filled is True
    assert result.events[0].average_fill_price == Decimal("2010")


def test_rejected() -> None:
    result = FillMonitor().classify(context=_context(), order=_order(status_code="2"))

    assert result.lifecycle_status is OrderLifecycle.REJECTED
    assert result.runtime_next_state is RuntimeState.HALT
    assert result.rejected is True
    assert result.requires_human_review is True


def test_expired() -> None:
    result = FillMonitor().classify(context=_context(), order=_order(status_code="12"))

    assert result.lifecycle_status is OrderLifecycle.EXPIRED
    assert result.runtime_next_state is RuntimeState.HALT
    assert result.expired is True


def test_canceled() -> None:
    result = FillMonitor().classify(context=_context(), order=_order(status_code="7"))

    assert result.lifecycle_status is OrderLifecycle.CANCELED
    assert result.runtime_next_state is RuntimeState.HALT
    assert result.canceled is True


def test_unknown_goes_to_halt() -> None:
    result = FillMonitor().classify(context=_context(), order=_order(status_code="999"))

    assert result.lifecycle_status is OrderLifecycle.UNKNOWN_STATUS
    assert result.runtime_next_state is RuntimeState.HALT
    assert result.requires_human_review is True


def test_order_list_empty_requires_human_review() -> None:
    result = FillMonitor().classify(context=_context(), order=None)

    assert result.lifecycle_status is OrderLifecycle.REQUIRES_HUMAN_REVIEW
    assert result.runtime_next_state is RuntimeState.HALT
    assert result.reason == "ORDER_LIST_EMPTY_AFTER_SUBMISSION"


def test_position_mismatch_requires_human_review() -> None:
    result = FillMonitor().classify(
        context=_context(),
        order=_order(status_code="10", filled="100"),
        detail={"fills": [{"quantity": "100", "price": "2010", "executed_at": "20260629090600"}]},
        position={"quantity": "0"},
    )

    assert result.lifecycle_status is OrderLifecycle.REQUIRES_HUMAN_REVIEW
    assert result.reason == "POSITION_MISMATCH"
    assert result.runtime_next_state is RuntimeState.HALT


def test_plaintext_order_id_rejected() -> None:
    with pytest.raises(ValueError, match="plaintext identifier"):
        FillMonitor().classify(context=_context(), order={**_order(status_code="1"), "order_number_hash": "12345"})


def test_plaintext_execution_id_rejected() -> None:
    with pytest.raises(ValueError, match="execution_id_hash"):
        FillEvent(
            runtime_id="runtime_test",
            environment=RuntimeMode.DEMO,
            issue_code="7203",
            side=OrderSide.BUY,
            order_quantity=Decimal("100"),
            execution_id_hash="raw-execution-id",
        )


def test_event_serialization_does_not_include_raw_ids() -> None:
    result = FillMonitor().classify(context=_context(), order=_order(status_code="1"))
    payload = result.to_dict()

    assert payload["events"][0]["raw_ids_saved"] is False
    assert "raw_order_id" not in payload["events"][0]
    assert "raw_execution_id" not in payload["events"][0]


def test_runtime_state_mapping_waiting_partial_filled_and_halt() -> None:
    context = _context()
    waiting_result = FillMonitor().classify(context=context, order=_order(status_code="1"))
    machine, _ = RuntimeStateMachine(context=context, current_state=RuntimeState.ORDER_SUBMITTED).transition_after_fill_monitor(waiting_result)
    assert machine.current_state is RuntimeState.WAITING_FILL

    partial_result = FillMonitor().classify(
        context=context,
        order=_order(status_code="9", filled="50"),
        detail={"fills": [{"quantity": "50", "price": "2000"}]},
    )
    machine, _ = machine.transition_after_fill_monitor(partial_result)
    assert machine.current_state is RuntimeState.PARTIALLY_FILLED

    filled_result = FillMonitor().classify(
        context=context,
        order=_order(status_code="10", filled="100"),
        detail={"fills": [{"quantity": "100", "price": "2000"}]},
        position={"quantity": "100"},
    )
    machine, _ = machine.transition_after_fill_monitor(filled_result)
    assert machine.current_state is RuntimeState.FILLED

    rejected_result = FillMonitor().classify(context=context, order=_order(status_code="2"))
    machine, _ = machine.transition_after_fill_monitor(rejected_result)
    assert machine.current_state is RuntimeState.HALT


def test_no_broker_api_call_flags_are_absent_from_mock_result() -> None:
    payload = FillMonitor().classify(context=_context(), order=_order(status_code="1")).to_dict()

    assert "broker_api_called" not in payload
    assert "broker_snapshot_updated" not in payload
    assert "paper_ledger_updated" not in payload


def _context() -> RuntimeContext:
    return RuntimeContext.demo(
        business_date="2026-06-29",
        evaluation_cash=Decimal("1000000"),
        broker_actual_cash=Decimal("20000000"),
    )


def _order(*, status_code: str, filled: str = "0") -> dict[str, str]:
    return {
        "issue_code": "7203",
        "side": "BUY",
        "quantity": "100",
        "filled_quantity": filled,
        "status_code": status_code,
        "order_status": status_code,
        "order_number_hash": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    }
