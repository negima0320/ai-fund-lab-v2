from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from ai_fund_lab_v2.runtime import (
    DemoOrderExecutor,
    OrderApprovalGate,
    OrderApprovalScope,
    OrderAuthorizationStatus,
    OrderCommand,
    OrderResultStatus,
    OrderSide,
    OrderType,
    PriceType,
    ProductionOrderExecutor,
    RuntimeMode,
)


def test_live_order_allowed_false_blocks_before_approval() -> None:
    result = OrderApprovalGate().authorize(_command(live_order_allowed=False), _approval(), second_password_present=True, now=_now())

    assert result.status is OrderAuthorizationStatus.BLOCKED_LIVE_ORDER_DISABLED
    assert result.broker_api_called is False


def test_approval_missing_blocks() -> None:
    result = OrderApprovalGate().authorize(_command(), None, second_password_present=True, now=_now())

    assert result.status is OrderAuthorizationStatus.BLOCKED_NO_APPROVAL
    assert result.second_password_value_saved is False


def test_second_password_missing_blocks_after_scope_match() -> None:
    result = OrderApprovalGate().authorize(_command(), _approval(), second_password_present=False, now=_now())

    assert result.status is OrderAuthorizationStatus.BLOCKED_SECOND_PASSWORD_MISSING
    assert result.reason == "second_password_missing"


def test_approval_scope_mismatch_blocks() -> None:
    approval = _approval(issue_code="6758")

    result = OrderApprovalGate().authorize(_command(), approval, second_password_present=True, now=_now())

    assert result.status is OrderAuthorizationStatus.BLOCKED_APPROVAL_SCOPE_MISMATCH


def test_expired_approval_blocks() -> None:
    approval = _approval(expires_at=_now() - timedelta(minutes=1))

    result = OrderApprovalGate().authorize(_command(), approval, second_password_present=True, now=_now())

    assert result.status is OrderAuthorizationStatus.BLOCKED_APPROVAL_EXPIRED


def test_demo_executor_dry_run_ready_with_valid_authorization() -> None:
    authorization = OrderApprovalGate().authorize(_command(), _approval(), second_password_present=True, now=_now())

    result = DemoOrderExecutor().submit(_command(), authorization=authorization, dry_run=True)

    assert result.status is OrderResultStatus.DRY_RUN_READY
    assert result.submitted is False
    assert result.skipped is True
    assert result.reason == "demo_dry_run_ready_no_broker_api"


def test_demo_executor_maps_authorization_failures() -> None:
    authorization = OrderApprovalGate().authorize(_command(), _approval(), second_password_present=False, now=_now())

    result = DemoOrderExecutor().submit(_command(), authorization=authorization, dry_run=True)

    assert result.status is OrderResultStatus.BLOCKED_SECOND_PASSWORD_MISSING
    assert result.submitted is False


def test_production_authorization_and_executor_are_blocked() -> None:
    command = _command(environment=RuntimeMode.PRODUCTION)
    approval = _approval(environment=RuntimeMode.PRODUCTION)

    authorization = OrderApprovalGate().authorize(command, approval, second_password_present=True, now=_now())
    result = ProductionOrderExecutor().submit(command)

    assert authorization.status is OrderAuthorizationStatus.BLOCKED_PRODUCTION_PROHIBITED
    assert result.status is OrderResultStatus.BLOCKED_PRODUCTION_PROHIBITED
    assert result.submitted is False


def test_authorization_payload_contains_no_secret_or_plain_order_id() -> None:
    result = OrderApprovalGate().authorize(_command(), _approval(), second_password_present=True, now=_now())
    payload = result.to_dict()

    assert payload["status"] == "APPROVED"
    assert payload["second_password_value_saved"] is False
    assert payload["broker_api_called"] is False
    assert "second_password" not in payload
    assert "raw_order_id" not in payload


def _now() -> datetime:
    return datetime(2026, 6, 28, 9, 0, tzinfo=timezone.utc)


def _command(*, environment: RuntimeMode = RuntimeMode.DEMO, live_order_allowed: bool = True) -> OrderCommand:
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
        approval_id="demo_approval_1",
        live_order_allowed=live_order_allowed,
    )


def _approval(
    *,
    environment: RuntimeMode = RuntimeMode.DEMO,
    issue_code: str = "7203",
    expires_at: datetime | None = None,
) -> OrderApprovalScope:
    return OrderApprovalScope(
        approval_id="demo_approval_1",
        environment=environment,
        issue_code=issue_code,
        side=OrderSide.BUY,
        quantity=Decimal("100"),
        max_notional=Decimal("250000"),
        expires_at=expires_at or (_now() + timedelta(minutes=10)),
    )
