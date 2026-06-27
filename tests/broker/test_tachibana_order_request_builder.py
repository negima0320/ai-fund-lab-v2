from __future__ import annotations

from decimal import Decimal

import pytest

from ai_fund_lab_v2.broker.tachibana_order_request import (
    TachibanaCashStockOrderRequest,
    TachibanaCashStockOrderRequestBuilder,
    TachibanaOrderRequestError,
)
from ai_fund_lab_v2.runtime import OrderCommand, OrderSide, OrderType, PriceType, RuntimeMode


def test_cash_stock_buy_request_shape_is_mock_only() -> None:
    payload = TachibanaCashStockOrderRequestBuilder().build(
        TachibanaCashStockOrderRequest(
            issue_code="7203",
            side=OrderSide.BUY,
            quantity=Decimal("100"),
            order_price_type=PriceType.MARKET,
        )
    )

    assert payload["sCLMID"] == "CLMKabuNewOrder"
    assert payload["sBaibaiKubun"] == "3"
    assert payload["sGenkinShinyouKubun"] == "0"
    assert payload["sSizyouC"] == "00"
    assert payload["sOrderPrice"] == "0"
    assert payload["sOrderSuryou"] == "100"
    assert "sSecondPassword" not in payload


def test_cash_stock_sell_request_shape() -> None:
    payload = TachibanaCashStockOrderRequestBuilder().build(
        TachibanaCashStockOrderRequest(
            issue_code="6758",
            side=OrderSide.SELL,
            quantity=Decimal("200"),
            order_price_type=PriceType.LIMIT,
            order_price=Decimal("1234.5"),
        )
    )

    assert payload["sBaibaiKubun"] == "1"
    assert payload["sOrderPrice"] == "1234.5"
    assert payload["sOrderSuryou"] == "200"


def test_market_order_requires_zero_price_and_limit_requires_positive_price() -> None:
    with pytest.raises(TachibanaOrderRequestError, match="market order price"):
        TachibanaCashStockOrderRequest(
            issue_code="7203",
            side=OrderSide.BUY,
            quantity=Decimal("100"),
            order_price_type=PriceType.MARKET,
            order_price=Decimal("1"),
        )

    with pytest.raises(TachibanaOrderRequestError, match="limit order price"):
        TachibanaCashStockOrderRequest(
            issue_code="7203",
            side=OrderSide.BUY,
            quantity=Decimal("100"),
            order_price_type=PriceType.LIMIT,
            order_price=Decimal("0"),
        )


def test_order_request_builder_p_no_is_monotonic() -> None:
    builder = TachibanaCashStockOrderRequestBuilder()
    request = TachibanaCashStockOrderRequest(
        issue_code="7203",
        side=OrderSide.BUY,
        quantity=Decimal("100"),
        order_price_type=PriceType.MARKET,
    )

    first = builder.build(request)
    second = builder.build(request)

    assert first["p_no"] == 1
    assert second["p_no"] == 2


def test_request_can_be_created_from_order_command_without_secret_value() -> None:
    command = OrderCommand(
        runtime_id="runtime_test",
        environment=RuntimeMode.DEMO,
        paper_test_id="paper_test2_2026-06-29",
        issue_code="9984",
        side=OrderSide.BUY,
        quantity=Decimal("100"),
        order_type=OrderType.CASH_EQUITY,
        price_type=PriceType.LIMIT,
        limit_price=Decimal("8000"),
        evaluation_cash_basis=Decimal("1000000"),
        broker_cash_upper_bound=Decimal("20000000"),
        approval_id="demo_approval_1",
        live_order_allowed=True,
    )

    request = TachibanaCashStockOrderRequest.from_order_command(command, second_password_present=True)
    summary = TachibanaCashStockOrderRequestBuilder().build_safe_summary(request)

    assert summary["sCLMID"] == "CLMKabuNewOrder"
    assert summary["second_password_present"] is True
    assert summary["second_password_value_saved"] is False
    assert summary["broker_api_called"] is False
    assert "second_password_value" not in summary


def test_production_order_request_generation_is_rejected() -> None:
    with pytest.raises(TachibanaOrderRequestError, match="production"):
        TachibanaCashStockOrderRequest(
            issue_code="7203",
            side=OrderSide.BUY,
            quantity=Decimal("100"),
            order_price_type=PriceType.MARKET,
            production_allowed=True,
        )


def test_encoded_mock_does_not_add_second_password_or_call_broker_api() -> None:
    request = TachibanaCashStockOrderRequest(
        issue_code="7203",
        side=OrderSide.BUY,
        quantity=Decimal("100"),
        order_price_type=PriceType.MARKET,
        second_password_present=True,
    )

    encoded = TachibanaCashStockOrderRequestBuilder().build_encoded_mock(request)

    assert "sSecondPassword" not in encoded
    assert "699" not in encoded
    assert encoded["333"] == "CLMKabuNewOrder"
    assert encoded["288"] == "1"
