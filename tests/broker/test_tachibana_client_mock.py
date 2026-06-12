from ai_fund_lab_v2.broker import BrokerSettings, MockBrokerTransport, TachibanaReadOnlyClient


def test_client_builds_login_and_logout_requests_without_calling_transport() -> None:
    transport = MockBrokerTransport()
    client = TachibanaReadOnlyClient(BrokerSettings(auth_id="secret-auth-id"), transport)

    login = client.build_login_request()
    logout = client.build_logout_request()

    assert login == {"sCLMID": "CLMAuthLoginRequest", "sAuthId": "secret-auth-id"}
    assert logout == {"sCLMID": "CLMAuthLogoutRequest"}
    assert transport.requests == []


def test_client_get_balance_summary_uses_mock_transport() -> None:
    transport = MockBrokerTransport()
    transport.register_response("CLMZanKaiSummary", {"sCLMID": "CLMZanKaiSummary", "sResultCode": "0", "sGenbutuKabuKaituke": "1000"})
    client = TachibanaReadOnlyClient(BrokerSettings(auth_id="secret-auth-id"), transport)

    response = client.get_balance_summary()

    assert response.clmid == "CLMZanKaiSummary"
    assert response.raw["sGenbutuKabuKaituke"] == "1000"
    assert transport.requests == [{"sCLMID": "CLMZanKaiSummary"}]


def test_client_read_only_methods_return_fixture_envelopes() -> None:
    transport = MockBrokerTransport()
    for clmid in [
        "CLMZanKaiKanougaku",
        "CLMGenbutuKabuList",
        "CLMShinyouTategyokuList",
        "CLMOrderList",
        "CLMOrderListDetail",
    ]:
        transport.register_response(clmid, {"sCLMID": clmid, "sResultCode": "0"})
    client = TachibanaReadOnlyClient(BrokerSettings(auth_id="secret-auth-id"), transport)

    assert client.get_buying_power().clmid == "CLMZanKaiKanougaku"
    assert client.get_cash_positions().clmid == "CLMGenbutuKabuList"
    assert client.get_margin_positions().clmid == "CLMShinyouTategyokuList"
    assert client.get_order_list(issue_code="8411", execution_day="20231018", order_status="2").clmid == "CLMOrderList"
    assert client.get_order_list_detail().clmid == "CLMOrderListDetail"


def test_client_request_history_is_sanitized_for_secret_login_payload_when_fixture_registered() -> None:
    transport = MockBrokerTransport()
    transport.register_response("CLMAuthLoginRequest", {"sCLMID": "CLMAuthLoginAck", "sResultCode": "0"})
    client = TachibanaReadOnlyClient(BrokerSettings(auth_id="secret-auth-id"), transport)

    response = client._request(client.build_login_request())

    assert response.clmid == "CLMAuthLoginAck"
    assert transport.requests == [{"sCLMID": "CLMAuthLoginRequest", "sAuthId": "[REDACTED]"}]
