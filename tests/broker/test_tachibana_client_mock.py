from ai_fund_lab_v2.broker import BrokerSettings, MockBrokerTransport, TachibanaReadOnlyClient, TachibanaRequestBuilder


def test_client_builds_login_and_logout_requests_without_calling_transport() -> None:
    transport = MockBrokerTransport()
    client = TachibanaReadOnlyClient(BrokerSettings(auth_id="secret-auth-id"), transport)

    login = client.build_login_request()
    logout = client.build_logout_request()

    assert login["sCLMID"] == "CLMAuthLoginRequest"
    assert login["sAuthId"] == "secret-auth-id"
    assert login["p_no"] == 1
    assert logout["sCLMID"] == "CLMAuthLogoutRequest"
    assert logout["p_no"] == 2
    assert transport.requests == []


def test_client_get_balance_summary_uses_mock_transport() -> None:
    transport = MockBrokerTransport()
    transport.register_response("CLMZanKaiSummary", {"sCLMID": "CLMZanKaiSummary", "sResultCode": "0", "sGenbutuKabuKaituke": "1000"})
    client = TachibanaReadOnlyClient(BrokerSettings(auth_id="secret-auth-id"), transport)

    response = client.get_balance_summary()

    assert response.clmid == "CLMZanKaiSummary"
    assert response.raw["sGenbutuKabuKaituke"] == "1000"
    assert transport.requests[0]["sCLMID"] == "CLMZanKaiSummary"


def test_client_get_account_summary_alias_uses_balance_summary_clmid() -> None:
    transport = MockBrokerTransport()
    transport.register_response("CLMZanKaiSummary", {"sCLMID": "CLMZanKaiSummary", "sResultCode": "0"})
    client = TachibanaReadOnlyClient(BrokerSettings(auth_id="secret-auth-id"), transport)

    response = client.get_account_summary()

    assert response.clmid == "CLMZanKaiSummary"
    assert transport.requests[0]["sCLMID"] == "CLMZanKaiSummary"


def test_client_consecutive_requests_use_monotonic_p_no() -> None:
    transport = MockBrokerTransport()
    transport.register_response("CLMZanKaiSummary", {"sCLMID": "CLMZanKaiSummary", "sResultCode": "0"})
    transport.register_response("CLMZanKaiKanougaku", {"sCLMID": "CLMZanKaiKanougaku", "sResultCode": "0"})
    client = TachibanaReadOnlyClient(BrokerSettings(auth_id="secret-auth-id"), transport)

    client.get_account_summary()
    client.get_buying_power()
    client.get_account_summary()

    assert [request["p_no"] for request in transport.requests] == [1, 2, 3]


def test_client_login_account_balance_logout_sequence_increases() -> None:
    transport = MockBrokerTransport()
    transport.register_response(
        "CLMAuthLoginRequest",
        {
            "sCLMID": "CLMAuthLoginAck",
            "sResultCode": "0",
            "sUrlRequest": "request",
            "sUrlMaster": "master",
            "sUrlPrice": "price",
            "sUrlEvent": "event",
            "sUrlEventWebSocket": "websocket",
        },
    )
    transport.register_response("CLMZanKaiSummary", {"sCLMID": "CLMZanKaiSummary", "sResultCode": "0"})
    transport.register_response("CLMZanKaiKanougaku", {"sCLMID": "CLMZanKaiKanougaku", "sResultCode": "0"})
    transport.register_response("CLMAuthLogoutRequest", {"sCLMID": "CLMAuthLogoutAck", "sResultCode": "0"})
    client = TachibanaReadOnlyClient(BrokerSettings(auth_id="secret-auth-id"), transport)

    session = client.login(decrypt_url=lambda value: f"https://demo-kabuka.e-shiten.jp/{value}")
    client.get_account_summary()
    client.get_buying_power()
    client.logout(session)

    assert [request["sCLMID"] for request in transport.requests] == [
        "CLMAuthLoginRequest",
        "CLMZanKaiSummary",
        "CLMZanKaiKanougaku",
        "CLMAuthLogoutRequest",
    ]
    assert [request["p_no"] for request in transport.requests] == [1, 2, 3, 4]


def test_client_respects_injected_builder_across_transport_clients() -> None:
    builder = TachibanaRequestBuilder(BrokerSettings(auth_id="secret-auth-id"))
    first_transport = MockBrokerTransport()
    second_transport = MockBrokerTransport()
    first_transport.register_response("CLMZanKaiSummary", {"sCLMID": "CLMZanKaiSummary", "sResultCode": "0"})
    second_transport.register_response("CLMZanKaiKanougaku", {"sCLMID": "CLMZanKaiKanougaku", "sResultCode": "0"})
    first_client = TachibanaReadOnlyClient(BrokerSettings(auth_id="secret-auth-id"), first_transport, builder=builder)
    second_client = TachibanaReadOnlyClient(BrokerSettings(auth_id="secret-auth-id"), second_transport, builder=builder)

    first_client.get_account_summary()
    second_client.get_buying_power()

    assert first_transport.requests[0]["p_no"] == 1
    assert second_transport.requests[0]["p_no"] == 2


def test_separate_clients_start_independent_sequences() -> None:
    first_transport = MockBrokerTransport()
    second_transport = MockBrokerTransport()
    first_transport.register_response("CLMZanKaiSummary", {"sCLMID": "CLMZanKaiSummary", "sResultCode": "0"})
    second_transport.register_response("CLMZanKaiSummary", {"sCLMID": "CLMZanKaiSummary", "sResultCode": "0"})
    first_client = TachibanaReadOnlyClient(BrokerSettings(auth_id="secret-auth-id"), first_transport)
    second_client = TachibanaReadOnlyClient(BrokerSettings(auth_id="secret-auth-id"), second_transport)

    first_client.get_account_summary()
    second_client.get_account_summary()

    assert first_transport.requests[0]["p_no"] == 1
    assert second_transport.requests[0]["p_no"] == 1


def test_client_read_only_methods_return_fixture_envelopes() -> None:
    transport = MockBrokerTransport()
    for clmid in [
        "CLMZanKaiKanougaku",
        "CLMGenbutuKabuList",
        "CLMShinyouTategyokuList",
        "CLMOrderList",
        "CLMOrderListDetail",
        "CLMMfdsGetMarketPrice",
    ]:
        transport.register_response(clmid, {"sCLMID": clmid, "sResultCode": "0"})
    client = TachibanaReadOnlyClient(BrokerSettings(auth_id="secret-auth-id"), transport)

    assert client.get_buying_power().clmid == "CLMZanKaiKanougaku"
    assert client.get_available_cash().clmid == "CLMZanKaiKanougaku"
    assert client.get_cash_positions().clmid == "CLMGenbutuKabuList"
    assert client.get_margin_positions().clmid == "CLMShinyouTategyokuList"
    cash_positions, margin_positions = client.get_positions()
    assert cash_positions.clmid == "CLMGenbutuKabuList"
    assert margin_positions.clmid == "CLMShinyouTategyokuList"
    assert client.get_order_list(issue_code="8411", execution_day="20231018", order_status="2").clmid == "CLMOrderList"
    assert client.get_order_list_detail().clmid == "CLMOrderListDetail"
    assert client.get_orders().clmid == "CLMOrderList"
    assert client.get_order_detail("N123").clmid == "CLMOrderListDetail"
    assert client.get_executions_history("N123").clmid == "CLMOrderListDetail"
    assert client.get_market_price(["7203"]).clmid == "CLMMfdsGetMarketPrice"
    assert client.get_quotes(["7203"]).clmid == "CLMMfdsGetMarketPrice"


def test_client_request_history_is_sanitized_for_secret_login_payload_when_fixture_registered() -> None:
    transport = MockBrokerTransport()
    transport.register_response("CLMAuthLoginRequest", {"sCLMID": "CLMAuthLoginAck", "sResultCode": "0"})
    client = TachibanaReadOnlyClient(BrokerSettings(auth_id="secret-auth-id"), transport)

    response = client._request(client.build_login_request())

    assert response.clmid == "CLMAuthLoginAck"
    assert transport.requests[0]["sCLMID"] == "CLMAuthLoginRequest"
    assert transport.requests[0]["sAuthId"] == "[REDACTED]"


def test_client_login_normalizes_session_with_mock_decryptor() -> None:
    transport = MockBrokerTransport()
    transport.register_response(
        "CLMAuthLoginRequest",
        {
            "sCLMID": "CLMAuthLoginAck",
            "sResultCode": "0",
            "sUrlRequest": "request",
            "sUrlMaster": "master",
            "sUrlPrice": "price",
            "sUrlEvent": "event",
            "sUrlEventWebSocket": "websocket",
        },
    )
    client = TachibanaReadOnlyClient(BrokerSettings(auth_id="secret-auth-id"), transport)

    session = client.login(decrypt_url=lambda value: f"https://demo-kabuka.e-shiten.jp/{value}")

    assert session.environment == "demo"
    assert session.request_url == "https://demo-kabuka.e-shiten.jp/request"
    assert "https://demo-kabuka.e-shiten.jp" not in repr(session)
