from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from ai_fund_lab_v2.runtime import (
    DemoOrderExecutor,
    OrderCommand,
    OrderResult,
    OrderResultStatus,
    OrderSide,
    OrderType,
    PaperOrderExecutor,
    PriceType,
    ProductionOrderExecutor,
    RuntimeContext,
    RuntimeMode,
    RuntimeState,
    RuntimeStateMachine,
    explicit_demo_approval,
    explicit_production_approval,
)


def test_paper_executor_returns_paper_only_result() -> None:
    result = PaperOrderExecutor().submit(_command(RuntimeMode.PAPER, live_order_allowed=False))

    assert result.status is OrderResultStatus.PAPER_ONLY_SUBMITTED
    assert result.submitted is True
    assert result.accepted is True
    assert result.reason == "paper_only_no_broker_api"


def test_demo_executor_blocked_by_default() -> None:
    result = DemoOrderExecutor().submit(_command(RuntimeMode.DEMO, live_order_allowed=False))

    assert result.status is OrderResultStatus.BLOCKED_LIVE_ORDER_DISABLED
    assert result.submitted is False
    assert result.skipped is True


def test_production_executor_blocked_by_default() -> None:
    result = ProductionOrderExecutor().submit(_command(RuntimeMode.PRODUCTION, live_order_allowed=False))

    assert result.status is OrderResultStatus.BLOCKED_PRODUCTION_PROHIBITED
    assert result.submitted is False
    assert result.skipped is True


def test_live_order_allowed_false_blocks_even_with_demo_approval() -> None:
    result = DemoOrderExecutor().submit(
        _command(RuntimeMode.DEMO, live_order_allowed=False),
        explicit_demo_approval(approval_id="demo_approval_1", approver="operator"),
    )

    assert result.status is OrderResultStatus.BLOCKED_LIVE_ORDER_DISABLED


def test_approval_missing_blocks_when_live_flag_enabled() -> None:
    result = DemoOrderExecutor().submit(_command(RuntimeMode.DEMO, live_order_allowed=True))

    assert result.status is OrderResultStatus.BLOCKED_NO_APPROVAL
    assert result.reason == "demo_approval_missing"


def test_approved_demo_and_production_still_do_not_call_broker_api_in_phase10o() -> None:
    demo_result = DemoOrderExecutor().submit(
        _command(RuntimeMode.DEMO, live_order_allowed=True),
        explicit_demo_approval(approval_id="demo_approval_1", approver="operator"),
    )
    production_result = ProductionOrderExecutor().submit(
        _command(RuntimeMode.PRODUCTION, live_order_allowed=True),
        explicit_production_approval(approval_id="prod_approval_1", approver="operator"),
    )

    assert demo_result.status is OrderResultStatus.BLOCKED_EXECUTOR_STUB
    assert production_result.status is OrderResultStatus.BLOCKED_PRODUCTION_PROHIBITED
    assert demo_result.submitted is False
    assert production_result.submitted is False


def test_raw_broker_order_id_is_not_part_of_result_schema() -> None:
    result = PaperOrderExecutor().submit(_command(RuntimeMode.PAPER))
    payload = result.to_dict()

    assert "raw_order_id" not in payload
    assert "broker_order_id" not in payload
    assert "broker_order_id_hash" in payload
    assert payload["broker_order_id_hash"] == ""


def test_short_broker_order_hash_is_rejected() -> None:
    with pytest.raises(ValueError, match="broker_order_id_hash"):
        OrderResult(status=OrderResultStatus.PAPER_ONLY_SUBMITTED, broker_order_id_hash="plain")


def test_runtime_state_can_enter_order_submitted_from_executor_result_schema() -> None:
    context = RuntimeContext.paper(business_date="2026-06-29", evaluation_cash=Decimal("1000000"))
    machine = RuntimeStateMachine(context=context, current_state=RuntimeState.ORDER_PREPARED)
    result = PaperOrderExecutor().submit(_command(RuntimeMode.PAPER))

    next_machine, manifest = machine.transition_after_order_result(result)

    assert manifest.transition.allowed is True
    assert next_machine.current_state is RuntimeState.ORDER_SUBMITTED


def test_runtime_state_does_not_enter_order_submitted_when_executor_blocks() -> None:
    context = RuntimeContext.demo(
        business_date="2026-06-29",
        evaluation_cash=Decimal("1000000"),
        broker_actual_cash=Decimal("20000000"),
    )
    machine = RuntimeStateMachine(context=context, current_state=RuntimeState.ORDER_PREPARED)
    result = DemoOrderExecutor().submit(_command(RuntimeMode.DEMO, live_order_allowed=False))

    next_machine, manifest = machine.transition_after_order_result(result)

    assert manifest.transition.allowed is False
    assert next_machine.current_state is RuntimeState.ORDER_PREPARED


def test_order_command_schema_serializes_money_and_mode() -> None:
    payload = _command(RuntimeMode.DEMO, live_order_allowed=False).to_dict()

    assert payload["environment"] == "demo"
    assert payload["evaluation_cash_basis"] == "1000000"
    assert payload["broker_cash_upper_bound"] == "20000000"
    assert payload["live_order_allowed"] is False


def test_safety_logic_is_not_implemented_in_phase10_runtime_package() -> None:
    runtime_dir = Path("src/ai_fund_lab_v2/runtime")
    assert not (runtime_dir / "safety.py").exists()
    runtime_text = "\n".join(path.read_text() for path in runtime_dir.glob("*.py") if path.name != "__init__.py")
    assert "SafetyGuard" not in runtime_text
    assert "EMERGENCY_STOP" not in runtime_text
    assert "STOP_LOSS" not in runtime_text


def _command(environment: RuntimeMode, *, live_order_allowed: bool = False) -> OrderCommand:
    return OrderCommand(
        runtime_id="runtime_test",
        environment=environment,
        paper_test_id="paper_test2_2026-06-29",
        issue_code="7203",
        side=OrderSide.BUY,
        quantity=Decimal("100"),
        order_type=OrderType.CASH_EQUITY,
        price_type=PriceType.LIMIT,
        limit_price=Decimal("2000"),
        evaluation_cash_basis=Decimal("1000000"),
        broker_cash_upper_bound=Decimal("20000000"),
        approval_required=True,
        approval_id="",
        live_order_allowed=live_order_allowed,
    )
