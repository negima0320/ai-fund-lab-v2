from decimal import Decimal

from ai_fund_lab_v2.broker import (
    BrokerResponseEnvelope,
    normalize_balance_summary,
    normalize_cash_positions,
    normalize_margin_positions,
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
