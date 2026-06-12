import pytest

from ai_fund_lab_v2.broker import BrokerAllowlistError, BrokerSessionContext, BrokerSettings, TachibanaRequestBuilder, sanitize_mapping


def builder() -> TachibanaRequestBuilder:
    return TachibanaRequestBuilder(BrokerSettings(auth_id="secret-auth-id"))


def test_login_request_contains_clmid_and_auth_id_without_repr_leak() -> None:
    request_builder = builder()

    payload = request_builder.login()

    assert payload == {"sCLMID": "CLMAuthLoginRequest", "sAuthId": "secret-auth-id"}
    assert "secret-auth-id" not in repr(request_builder)
    assert sanitize_mapping(payload) == {"sCLMID": "CLMAuthLoginRequest", "sAuthId": "[REDACTED]"}


def test_logout_request_can_be_built_with_session_context() -> None:
    payload = builder().logout(BrokerSessionContext(request_url="https://example.test/session"))

    assert payload == {"sCLMID": "CLMAuthLogoutRequest"}
    assert "https://example" not in repr(BrokerSessionContext(request_url="https://example.test/session"))


@pytest.mark.parametrize(
    ("method_name", "expected"),
    [
        ("balance_summary", {"sCLMID": "CLMZanKaiSummary"}),
        ("buying_power", {"sCLMID": "CLMZanKaiKanougaku", "sIssueCode": "", "sSizyouC": ""}),
        ("cash_positions", {"sCLMID": "CLMGenbutuKabuList", "sIssueCode": ""}),
        ("margin_positions", {"sCLMID": "CLMShinyouTategyokuList", "sIssueCode": ""}),
        ("order_list", {"sCLMID": "CLMOrderList", "sIssueCode": "", "sSikkouDay": "", "sOrderSyoukaiStatus": ""}),
        ("order_list_detail", {"sCLMID": "CLMOrderListDetail", "sIssueCode": "", "sSikkouDay": "", "sOrderSyoukaiStatus": ""}),
    ],
)
def test_read_only_payloads_are_built(method_name: str, expected: dict) -> None:
    request_builder = builder()

    payload = getattr(request_builder, method_name)()

    assert payload == expected


def test_order_list_accepts_optional_filters() -> None:
    payload = builder().order_list(issue_code="8411", execution_day="20231018", order_status="2")

    assert payload == {
        "sCLMID": "CLMOrderList",
        "sIssueCode": "8411",
        "sSikkouDay": "20231018",
        "sOrderSyoukaiStatus": "2",
    }


def test_builder_rejects_order_and_unknown_clmids() -> None:
    request_builder = builder()

    with pytest.raises(BrokerAllowlistError):
        request_builder.build("CLMKabuNewOrder")
    with pytest.raises(BrokerAllowlistError):
        request_builder.build("CLMUnknown")
