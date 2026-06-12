from decimal import Decimal

from ai_fund_lab_v2.broker import BrokerBalanceSnapshot, BrokerOrderSnapshot, BrokerPositionSnapshot


def test_balance_model_can_be_created() -> None:
    snapshot = BrokerBalanceSnapshot(
        as_of="2026-06-12T00:00:00+00:00",
        cash_available=Decimal("100000"),
        buying_power=Decimal("90000"),
        withdrawable_cash=Decimal("80000"),
        total_assets=Decimal("120000"),
        raw_clmid="CLMZanKaiSummary",
        raw_result_code="0",
    )

    assert snapshot.snapshot_id.startswith("balance_")
    assert snapshot.broker == "tachibana"
    assert snapshot.source == "mock"
    assert snapshot.currency == "JPY"


def test_position_model_can_be_created() -> None:
    snapshot = BrokerPositionSnapshot(
        as_of="2026-06-12T00:00:00+00:00",
        account_type="cash",
        issue_code="7203",
        issue_name="TOYOTA",
        quantity=Decimal("100"),
        available_quantity=Decimal("100"),
        average_price=Decimal("2500"),
        market_price=Decimal("2600"),
        market_value=Decimal("260000"),
        unrealized_pnl=Decimal("10000"),
        raw_clmid="CLMGenbutuKabuList",
        raw_result_code="0",
    )

    assert snapshot.snapshot_id.startswith("position_")
    assert snapshot.account_type == "cash"
    assert snapshot.issue_code == "7203"


def test_order_model_can_be_created() -> None:
    snapshot = BrokerOrderSnapshot(
        as_of="2026-06-12T00:00:00+00:00",
        order_id="ORD-1",
        issue_code="7203",
        issue_name="TOYOTA",
        side="buy",
        order_type="limit",
        quantity=Decimal("100"),
        executed_quantity=Decimal("40"),
        remaining_quantity=Decimal("60"),
        price=Decimal("2500"),
        status="partial",
        order_datetime="2026-06-12T09:00:00+09:00",
        expire_date="2026-06-12",
        raw_clmid="CLMOrderList",
        raw_result_code="0",
    )

    assert snapshot.snapshot_id.startswith("order_")
    assert snapshot.remaining_quantity == Decimal("60")
