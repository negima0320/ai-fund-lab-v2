from decimal import Decimal

from ai_fund_lab_v2.broker import (
    BrokerResponseEnvelope,
    normalize_balance_summary,
    normalize_buying_power,
    normalize_cash_positions,
    normalize_margin_positions,
    normalize_market_quotes,
    normalize_order_detail_executions,
    normalize_order_list,
)


def test_mock_response_normalizes_to_balance_snapshot() -> None:
    envelope = BrokerResponseEnvelope(
        {
            "sCLMID": "CLMZanKaiSummary",
            "sResultCode": "0",
            "as_of": "2026-06-12T00:00:00+00:00",
            "sGenkinZandaka": "100000",
            "sGenbutuKabuKaituke": "90000",
            "sSyukkinKanougaku": "80000",
            "sHyokaGakuGoukei": "120000",
            "sAuthId": "secret-auth-id",
            "request_url": "https://example.invalid/request",
        }
    )

    snapshot = normalize_balance_summary(envelope)

    assert snapshot.raw_clmid == "CLMZanKaiSummary"
    assert snapshot.raw_result_code == "0"
    assert snapshot.cash_available == Decimal("100000")
    assert snapshot.buying_power == Decimal("90000")
    assert snapshot.total_assets == Decimal("120000")
    assert not hasattr(snapshot, "raw")


def test_tachibana_summary_fields_normalize_to_balance_snapshot() -> None:
    envelope = BrokerResponseEnvelope(
        {
            "sCLMID": "CLMZanKaiSummary",
            "sResultCode": "0",
            "sSummaryGenkabuKaituke": "20000000",
            "sSyukkin": "17989000",
            "sIPOKounyu": "17989000",
            "sSinyouSinkidate": "54512121",
            "sSummaryNseityouTousiKanougaku": "123456",
        }
    )

    snapshot = normalize_balance_summary(envelope)

    assert snapshot.cash_available == Decimal("17989000")
    assert snapshot.buying_power == Decimal("20000000")
    assert snapshot.withdrawable_cash == Decimal("17989000")
    assert snapshot.ipo_buying_power == Decimal("17989000")
    assert snapshot.margin_buying_power == Decimal("54512121")
    assert snapshot.nisa_growth_capacity == Decimal("123456")


def test_tachibana_buying_power_summary_fields_normalize() -> None:
    envelope = BrokerResponseEnvelope(
        {
            "sCLMID": "CLMZanKaiKanougaku",
            "sResultCode": "0",
            "sSummaryGenkabuKaituke": "20000000",
            "sSummaryNseityouTousiKanougaku": "123456",
        }
    )

    snapshot = normalize_buying_power(envelope)

    assert snapshot.cash_available == Decimal("20000000")
    assert snapshot.buying_power == Decimal("20000000")
    assert snapshot.total_assets == Decimal("20000000")
    assert snapshot.nisa_growth_capacity == Decimal("123456")


def test_mock_response_normalizes_to_cash_positions() -> None:
    envelope = BrokerResponseEnvelope(
        {
            "sCLMID": "CLMGenbutuKabuList",
            "sResultCode": "0",
            "as_of": "2026-06-12T00:00:00+00:00",
            "positions": [
                {
                    "sIssueCode": "7203",
                    "sIssueName": "TOYOTA",
                    "sZanKabuSuu": "100",
                    "sUritukeKanouSuu": "80",
                    "sBokaTanka": "2500.5",
                    "sGenzaine": "2600",
                    "sHyokaGaku": "260000",
                    "sHyokaSoneki": "9950",
                }
            ],
        }
    )

    snapshots = normalize_cash_positions(envelope)

    assert len(snapshots) == 1
    assert snapshots[0].account_type == "cash"
    assert snapshots[0].issue_code == "7203"
    assert snapshots[0].quantity == Decimal("100")
    assert snapshots[0].average_price == Decimal("2500.5")


def test_mock_response_normalizes_to_margin_positions() -> None:
    envelope = BrokerResponseEnvelope(
        {
            "sCLMID": "CLMShinyouTategyokuList",
            "sResultCode": "0",
            "aShinyouTategyokuList": [
                {
                    "sIssueCode": "8306",
                    "sIssueName": "MUFG",
                    "sQuantity": "200",
                    "sAvailableQuantity": "100",
                    "sAveragePrice": "1500",
                    "sMarketPrice": "1510",
                    "sMarketValue": "302000",
                    "sUnrealizedPnl": "2000",
                }
            ],
        }
    )

    snapshots = normalize_margin_positions(envelope)

    assert len(snapshots) == 1
    assert snapshots[0].account_type == "margin"
    assert snapshots[0].issue_code == "8306"


def test_mock_response_normalizes_to_orders() -> None:
    envelope = BrokerResponseEnvelope(
        {
            "sCLMID": "CLMOrderList",
            "sResultCode": "0",
            "orders": [
                {
                    "sOrderNo": "ORD-001",
                    "sIssueCode": "7203",
                    "sIssueName": "TOYOTA",
                    "sBaibaiKubun": "1",
                    "sOrderPriceKubun": "limit",
                    "sOrderSuryou": "100",
                    "sYakujouSuryou": "40",
                    "sOrderZanSuryou": "60",
                    "sOrderPrice": "2500",
                    "sOrderStatus": "partial",
                    "sOrderDatetime": "2026-06-12T09:00:00+09:00",
                    "sSikkouDay": "2026-06-12",
                }
            ],
        }
    )

    snapshots = normalize_order_list(envelope)

    assert len(snapshots) == 1
    assert snapshots[0].order_id == "ORD-001"
    assert snapshots[0].side == "buy"
    assert snapshots[0].remaining_quantity == Decimal("60")


def test_mock_response_normalizes_order_detail_executions() -> None:
    envelope = BrokerResponseEnvelope(
        {
            "sCLMID": "CLMOrderListDetail",
            "sResultCode": "0",
            "sOrderIssueCode": "7203",
            "sIssueName": "TOYOTA",
            "aYakuzyouSikkouList": [
                {
                    "sYakuzyouDate": "20260627090102",
                    "sYakuzyouSuryou": "100",
                    "sYakuzyouPrice": "2500.5",
                }
            ],
        }
    )

    snapshots = normalize_order_detail_executions(envelope, order_id="ORD-001")

    assert len(snapshots) == 1
    assert snapshots[0].broker == "tachibana"
    assert snapshots[0].order_id == "ORD-001"
    assert snapshots[0].issue_code == "7203"
    assert snapshots[0].quantity == Decimal("100")
    assert snapshots[0].price == Decimal("2500.5")


def test_mock_response_normalizes_market_quotes() -> None:
    envelope = BrokerResponseEnvelope(
        {
            "sCLMID": "CLMMfdsGetMarketPrice",
            "sResultCode": "0",
            "aCLMMfdsMarketPrice": [
                {
                    "sIssueCode": "7203",
                    "pDPP": "2500.5",
                    "tDPP:T": "09:00:01",
                    "pDOP": "2490",
                    "pDHP": "2510",
                    "pDLP": "2480",
                    "pDV": "123456",
                    "pPRP": "1.23",
                }
            ],
        }
    )

    quotes = normalize_market_quotes(envelope)

    assert len(quotes) == 1
    assert quotes[0]["issue_code"] == "7203"
    assert quotes[0]["last_price"] == Decimal("2500.5")
    assert quotes[0]["quote_time"] == "09:00:01"
    assert quotes[0]["volume"] == Decimal("123456")
