from ai_fund_lab_v2.paper_trading.virtual_fill_policy import FILL_POLICY_ID, VirtualFillPolicy, resolve_open_price


def test_virtual_fill_policy_defaults() -> None:
    policy = VirtualFillPolicy()
    assert policy.fill_policy == FILL_POLICY_ID
    assert policy.buy_price_source == "virtual_execution_date_open"
    assert policy.sell_price_source == "virtual_execution_date_open"
    assert policy.partial_fill_supported is False


def test_resolve_open_price_returns_price() -> None:
    price, reason = resolve_open_price(
        code="7203",
        execution_date="2026-06-17",
        quote_rows=[{"Date": "2026-06-17", "Code": "7203", "Open": 2000}],
        side="BUY",
    )
    assert price == 2000
    assert reason == ""


def test_resolve_open_price_missing_is_no_fill_reason() -> None:
    price, reason = resolve_open_price(code="7203", execution_date="2026-06-17", quote_rows=[], side="BUY")
    assert price is None
    assert reason == "DAILY_QUOTE_MISSING"

