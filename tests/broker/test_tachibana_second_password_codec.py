from __future__ import annotations

import json
from decimal import Decimal

import pytest

from ai_fund_lab_v2.broker.settings import DEMO_BASE_URL, PROD_BASE_URL, BrokerSettings
from ai_fund_lab_v2.broker.tachibana_codec import TACHIBANA_V4R9_COLUMNS, TachibanaV4R9Codec
from ai_fund_lab_v2.broker.tachibana_order_request import TachibanaCashStockOrderRequest, TachibanaCashStockOrderRequestBuilder
from ai_fund_lab_v2.broker.transport import DemoOrderBrokerTransport
from ai_fund_lab_v2.runtime import OrderSide, PriceType


def _cash_buy_request() -> TachibanaCashStockOrderRequest:
    return TachibanaCashStockOrderRequest(
        issue_code="92560",
        side=OrderSide.BUY,
        quantity=Decimal("100"),
        order_price_type=PriceType.LIMIT,
        order_price=Decimal("5410"),
        second_password_present=True,
    )


def test_s_second_password_request_side_codec_key_is_698() -> None:
    assert TACHIBANA_V4R9_COLUMNS["sSecondPassword"] == 698
    assert TACHIBANA_V4R9_COLUMNS["sSecondPasswordOmit"] == 699

    encoded = TachibanaV4R9Codec().encode_request({"sSecondPassword": "dummy-secret", "sSecondPasswordOmit": "0"})

    assert encoded["698"] == "dummy-secret"
    assert encoded["699"] == "0"


def test_demo_order_transport_encodes_second_password_through_codec_not_omit_key() -> None:
    request = _cash_buy_request()
    payload = TachibanaCashStockOrderRequestBuilder().build_final_payload_with_second_password(
        request,
        second_password_value="dummy-secret",
    )
    transport = DemoOrderBrokerTransport(
        endpoint_url="https://demo-kabuka.e-shiten.jp/request",
        settings=BrokerSettings(environment="demo", base_url=DEMO_BASE_URL),
        demo_order_wire_execution=True,
        codec=TachibanaV4R9Codec(),
    )

    encoded = transport._encode_order_payload(payload)

    assert encoded["698"] == "dummy-secret"
    assert "sSecondPassword" not in encoded
    assert "699" not in encoded


def test_second_password_redacted_summary_saves_presence_only() -> None:
    request = _cash_buy_request()
    builder = TachibanaCashStockOrderRequestBuilder()

    safe = builder.build_safe_summary(request)
    final = builder.build_final_payload_with_second_password(request, second_password_value="dummy-secret")
    safe_text = json.dumps(safe, sort_keys=True)

    assert final["sSecondPassword"] == "dummy-secret"
    assert safe["second_password_present"] is True
    assert safe["second_password_value_saved"] is False
    assert "dummy-secret" not in safe_text
    assert "sSecondPassword" not in safe_text
    assert "hash" not in safe_text.lower()
    assert "length" not in safe_text.lower()


def test_demo_order_transport_still_fails_closed_for_production() -> None:
    transport = DemoOrderBrokerTransport(
        endpoint_url="https://kabuka.e-shiten.jp/request",
        settings=BrokerSettings(environment="production", base_url=PROD_BASE_URL),
        demo_order_wire_execution=True,
        production_order_allowed=False,
        codec=TachibanaV4R9Codec(),
    )

    with pytest.raises(Exception, match="requires demo environment"):
        transport.request({"sCLMID": "CLMKabuNewOrder", "sSecondPassword": "dummy-secret"})
