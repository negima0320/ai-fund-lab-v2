from __future__ import annotations

from decimal import Decimal

from ai_fund_lab_v2.broker.tachibana_codec import TachibanaV4R9Codec
from ai_fund_lab_v2.broker.tachibana_order_request import (
    TachibanaCashStockOrderRequest,
    TachibanaCashStockOrderRequestBuilder,
)
from ai_fund_lab_v2.operations.operations import _command_from_item
from ai_fund_lab_v2.runtime import OrderSide, PriceType


def test_order_command_uses_broker_issue_code_at_request_boundary() -> None:
    command = _command_from_item(
        {
            "item_id": "buy_2026-06-29_92560_001",
            "issue_code": "92560",
            "broker_issue_code": "9256",
            "side": "BUY",
            "quantity": "100",
            "price_type": "LIMIT",
            "limit_price": "5410",
        },
        "2026-06-29",
        "approval-1",
        live_order_allowed=True,
    )

    assert command.issue_code == "9256"


def test_encoded_dummy_request_contains_broker_issue_code_only() -> None:
    request = TachibanaCashStockOrderRequest(
        issue_code="9256",
        side=OrderSide.BUY,
        quantity=Decimal("100"),
        order_price_type=PriceType.LIMIT,
        order_price=Decimal("5410"),
        second_password_present=True,
    )

    encoded = TachibanaV4R9Codec().encode_request(
        TachibanaCashStockOrderRequestBuilder().build_final_payload_with_second_password(
            request,
            second_password_value="dummy-secret",
        )
    )

    assert encoded["473"] == "9256"
    assert "sIssueCode" not in encoded
    assert "92560" not in set(str(value) for value in encoded.values())
