import pytest

from ai_fund_lab_v2.broker import BrokerAllowlistError, BrokerSessionContext, BrokerSettings, TachibanaRequestBuilder, sanitize_mapping


def builder() -> TachibanaRequestBuilder:
    return TachibanaRequestBuilder(BrokerSettings(auth_id="secret-auth-id"))


def test_login_request_contains_clmid_and_auth_id_without_repr_leak() -> None:
    request_builder = builder()

    payload = request_builder.login()

    assert payload["p_no"] == 1
    assert payload["p_sd_date"]
    assert payload["sCLMID"] == "CLMAuthLoginRequest"
    assert payload["sAuthId"] == "secret-auth-id"
    assert "secret-auth-id" not in repr(request_builder)
    assert sanitize_mapping(payload)["sAuthId"] == "[REDACTED]"


def test_logout_request_can_be_built_with_session_context() -> None:
    payload = builder().logout(BrokerSessionContext(request_url="https://example.test/session"))

    assert payload["sCLMID"] == "CLMAuthLogoutRequest"
    assert payload["p_no"] == 1
    assert "https://example" not in repr(BrokerSessionContext(request_url="https://example.test/session"))


@pytest.mark.parametrize(
    ("method_name", "expected"),
    [
        ("balance_summary", {"sCLMID": "CLMZanKaiSummary"}),
        ("buying_power", {"sCLMID": "CLMZanKaiKanougaku", "sIssueCode": "", "sSizyouC": ""}),
        ("cash_positions", {"sCLMID": "CLMGenbutuKabuList", "sIssueCode": ""}),
        ("margin_positions", {"sCLMID": "CLMShinyouTategyokuList", "sIssueCode": ""}),
        ("order_list", {"sCLMID": "CLMOrderList", "sIssueCode": "", "sSikkouDay": "", "sOrderSyoukaiStatus": ""}),
        ("order_list_detail", {"sCLMID": "CLMOrderListDetail", "sOrderNumber": ""}),
    ],
)
def test_read_only_payloads_are_built(method_name: str, expected: dict) -> None:
    request_builder = builder()

    payload = getattr(request_builder, method_name)()

    for key, value in expected.items():
        assert payload[key] == value
    assert payload["p_no"] == 1
    assert payload["p_sd_date"]


def test_order_list_accepts_optional_filters() -> None:
    payload = builder().order_list(issue_code="8411", execution_day="20231018", order_status="2")

    assert payload["sCLMID"] == "CLMOrderList"
    assert payload["sIssueCode"] == "8411"
    assert payload["sSikkouDay"] == "20231018"
    assert payload["sOrderSyoukaiStatus"] == "2"


def test_order_list_detail_uses_order_number() -> None:
    payload = builder().order_list_detail(order_number="N123")

    assert payload["sCLMID"] == "CLMOrderListDetail"
    assert payload["sOrderNumber"] == "N123"


def test_quote_payload_is_read_only_price_request() -> None:
    payload = builder().quote(["6501", "6502"])

    assert payload["sCLMID"] == "CLMMfdsGetMarketPrice"
    assert payload["sTargetIssueCode"] == "6501,6502"
    assert payload["sTargetColumn"] == "pDPP,tDPP:T,pDOP,pDHP,pDLP,pDV,pPRP"


def test_quote_payload_rejects_empty_and_too_many_symbols() -> None:
    request_builder = TachibanaRequestBuilder(BrokerSettings(auth_id="secret-auth-id", quote_symbol_limit=2))

    with pytest.raises(ValueError):
        request_builder.quote([])
    with pytest.raises(ValueError):
        request_builder.quote(["6501", "6502", "6503"])


def test_builder_rejects_order_and_unknown_clmids() -> None:
    request_builder = builder()

    with pytest.raises(BrokerAllowlistError):
        request_builder.build("CLMKabuNewOrder")
    with pytest.raises(BrokerAllowlistError):
        request_builder.build("CLMUnknown")
