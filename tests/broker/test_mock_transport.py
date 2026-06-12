import pytest

from ai_fund_lab_v2.broker import BrokerAllowlistError, BrokerTransportError, MockBrokerTransport


def test_mock_transport_returns_registered_fixture_without_network() -> None:
    transport = MockBrokerTransport()
    transport.register_response("CLMZanKaiSummary", {"sCLMID": "CLMZanKaiSummary", "sResultCode": "0"})

    response = transport.request({"sCLMID": "CLMZanKaiSummary", "sAuthId": "secret-auth"})

    assert response == {"sCLMID": "CLMZanKaiSummary", "sResultCode": "0"}
    assert transport.requests == [{"sCLMID": "CLMZanKaiSummary", "sAuthId": "[REDACTED]"}]


def test_mock_transport_rejects_order_clmid() -> None:
    transport = MockBrokerTransport()

    with pytest.raises(BrokerAllowlistError):
        transport.request({"sCLMID": "CLMKabuNewOrder"})


def test_mock_transport_rejects_unregistered_fixture() -> None:
    transport = MockBrokerTransport()

    with pytest.raises(BrokerTransportError, match="No mock response registered"):
        transport.request({"sCLMID": "CLMOrderList"})
