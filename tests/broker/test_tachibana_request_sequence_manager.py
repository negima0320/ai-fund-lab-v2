from decimal import Decimal

from ai_fund_lab_v2.broker.request_builder import TachibanaRequestBuilder
from ai_fund_lab_v2.broker.request_sequence import RequestSequenceManager
from ai_fund_lab_v2.broker.settings import BrokerSettings
from ai_fund_lab_v2.broker.tachibana_order_request import (
    TachibanaCashStockOrderRequest,
    TachibanaCashStockOrderRequestBuilder,
)
from ai_fund_lab_v2.runtime import OrderSide, PriceType


def test_login_order_logout_share_session_sequence() -> None:
    sequence = RequestSequenceManager()
    read_builder = TachibanaRequestBuilder(BrokerSettings(auth_id="secret-auth-id"), sequence_manager=sequence)
    order_builder = TachibanaCashStockOrderRequestBuilder(sequence_manager=sequence)
    order = TachibanaCashStockOrderRequest(
        issue_code="92560",
        side=OrderSide.BUY,
        quantity=Decimal("100"),
        order_price_type=PriceType.LIMIT,
        order_price=Decimal("5410"),
        second_password_present=True,
    )

    login = read_builder.login()
    new_order = order_builder.build(order)
    logout = read_builder.logout()

    assert [login["p_no"], new_order["p_no"], logout["p_no"]] == [1, 2, 3]


def test_readonly_order_share_sequence_without_resetting_to_one() -> None:
    sequence = RequestSequenceManager()
    read_builder = TachibanaRequestBuilder(BrokerSettings(auth_id="secret-auth-id"), sequence_manager=sequence)
    order_builder = TachibanaCashStockOrderRequestBuilder(sequence_manager=sequence)
    order = TachibanaCashStockOrderRequest(
        issue_code="92560",
        side=OrderSide.BUY,
        quantity=Decimal("100"),
        order_price_type=PriceType.LIMIT,
        order_price=Decimal("5410"),
        second_password_present=True,
    )

    read_builder.login()
    account = read_builder.balance_summary()
    buying_power = read_builder.buying_power()
    new_order = order_builder.build(order)

    assert [account["p_no"], buying_power["p_no"], new_order["p_no"]] == [2, 3, 4]
    assert new_order["p_no"] != 1
