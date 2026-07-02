from __future__ import annotations

from decimal import Decimal

from ai_fund_lab_v2.broker.tachibana_codec import TACHIBANA_V4R9_COLUMNS, TachibanaV4R9Codec
from ai_fund_lab_v2.broker.tachibana_order_request import TachibanaCashStockOrderRequest, TachibanaCashStockOrderRequestBuilder
from ai_fund_lab_v2.runtime import OrderSide, PriceType


ORDER_LOGICAL_KEYS = {
    "sZyoutoekiKazeiC",
    "sIssueCode",
    "sSizyouC",
    "sBaibaiKubun",
    "sCondition",
    "sOrderPrice",
    "sOrderSuryou",
    "sGenkinShinyouKubun",
    "sOrderExpireDay",
    "sGyakusasiOrderType",
    "sGyakusasiZyouken",
    "sGyakusasiPrice",
    "sTatebiType",
    "sTategyokuZyoutoekiKazeiC",
    "sSecondPassword",
}


def _final_cash_buy_payload() -> dict[str, object]:
    request = TachibanaCashStockOrderRequest(
        issue_code="92560",
        side=OrderSide.BUY,
        quantity=Decimal("100"),
        order_price_type=PriceType.LIMIT,
        order_price=Decimal("5410"),
        second_password_present=True,
    )
    return TachibanaCashStockOrderRequestBuilder().build_final_payload_with_second_password(
        request,
        second_password_value="dummy-secret",
    )


def test_clm_kabu_new_order_required_request_fields_are_compressed() -> None:
    encoded = TachibanaV4R9Codec().encode_request(_final_cash_buy_payload())

    assert not (ORDER_LOGICAL_KEYS & set(encoded.keys()))
    assert encoded["929"] == "1"
    assert encoded["473"] == "92560"
    assert encoded["731"] == "00"
    assert encoded["323"] == "3"
    assert encoded["336"] == "0"
    assert encoded["650"] == "5410"
    assert encoded["658"] == "100"
    assert encoded["397"] == "0"
    assert encoded["624"] == "0"
    assert encoded["402"] == "0"
    assert encoded["406"] == "0"
    assert encoded["403"] == "*"
    assert encoded["793"] == "*"
    assert encoded["798"] == "*"
    assert encoded["698"] == "dummy-secret"
    assert "699" not in encoded


def test_clm_kabu_new_order_codec_contains_official_request_and_response_keys() -> None:
    expected = {
        "sZyoutoekiKazeiC": 929,
        "sBaibaiKubun": 323,
        "sCondition": 336,
        "sGenkinShinyouKubun": 397,
        "sGyakusasiOrderType": 402,
        "sGyakusasiZyouken": 406,
        "sGyakusasiPrice": 403,
        "sTatebiType": 793,
        "sTategyokuZyoutoekiKazeiC": 798,
        "sSecondPassword": 698,
        "sSecondPasswordOmit": 699,
        "sEigyouDay": 369,
        "sOrderUkewatasiKingaku": 672,
        "sOrderTesuryou": 669,
        "sOrderSyouhizei": 660,
        "sKinri": 518,
    }

    for logical_key, compressed_key in expected.items():
        assert TACHIBANA_V4R9_COLUMNS[logical_key] == compressed_key


def test_order_success_response_decodes_official_fields() -> None:
    decoded = TachibanaV4R9Codec().decode_response(
        {
            "333": "CLMKabuNewOrder",
            "688": "0",
            "689": "",
            "876": "0",
            "877": "",
            "643": "9000015",
            "369": "20221209",
            "672": "140099",
            "669": "90",
            "660": "9",
            "518": "-",
            "623": "20221209134803",
        }
    )

    assert decoded["sOrderNumber"] == "9000015"
    assert decoded["sEigyouDay"] == "20221209"
    assert decoded["sOrderUkewatasiKingaku"] == "140099"
    assert decoded["sOrderTesuryou"] == "90"
    assert decoded["sOrderSyouhizei"] == "9"
    assert decoded["sKinri"] == "-"
