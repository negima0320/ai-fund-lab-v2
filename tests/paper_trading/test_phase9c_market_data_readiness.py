from ai_fund_lab_v2.paper_trading.market_data_readiness import INVALID, NOT_READY, READY, check_market_data_readiness


def test_market_data_ready() -> None:
    result = check_market_data_readiness(
        decision_for="2026-06-16",
        daily_quotes_records=[_quote("2026-06-16")],
        listed_info_records=[{"Date": "2026-06-16", "Code": "7203"}],
    )
    assert result.status == READY
    assert result.data_until == "2026-06-16"
    assert result.row_count == 1


def test_market_data_not_ready_when_data_until_before_decision_for() -> None:
    result = check_market_data_readiness(
        decision_for="2026-06-16",
        daily_quotes_records=[_quote("2026-06-15")],
        listed_info_records=[{"Date": "2026-06-16", "Code": "7203"}],
    )
    assert result.status == NOT_READY
    assert "data_until_before_decision_for" in result.blocked_reasons


def test_market_data_invalid_when_future_row_exists() -> None:
    result = check_market_data_readiness(
        decision_for="2026-06-16",
        daily_quotes_records=[_quote("2026-06-17")],
        listed_info_records=[{"Date": "2026-06-16", "Code": "7203"}],
    )
    assert result.status == INVALID
    assert "future_row_detected" in result.blocked_reasons


def test_market_data_not_ready_when_daily_quotes_missing() -> None:
    result = check_market_data_readiness(
        decision_for="2026-06-16",
        daily_quotes_records=[],
        listed_info_records=[{"Date": "2026-06-16", "Code": "7203"}],
    )
    assert result.status == NOT_READY


def _quote(day: str) -> dict[str, object]:
    return {"Date": day, "Code": "7203", "Open": 100, "High": 110, "Low": 99, "Close": 108, "Volume": 1000}

