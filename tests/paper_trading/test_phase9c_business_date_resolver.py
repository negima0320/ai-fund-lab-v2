from ai_fund_lab_v2.paper_trading.business_date_resolver import resolve_business_dates


def test_business_date_resolver_uses_weekday_fallback() -> None:
    dates = resolve_business_dates(run_date="2026-06-16", calendar_records=())
    assert dates.run_date == "2026-06-16"
    assert dates.decision_for == "2026-06-16"
    assert dates.data_until == "2026-06-16"
    assert dates.virtual_order_date == "2026-06-17"
    assert dates.virtual_execution_date == "2026-06-17"
    assert dates.calendar_source == "weekday_fallback"


def test_business_date_resolver_skips_weekend() -> None:
    dates = resolve_business_dates(run_date="2026-06-19", calendar_records=())
    assert dates.virtual_order_date == "2026-06-22"


def test_business_date_resolver_uses_calendar_records() -> None:
    records = [
        {"Date": "2026-06-17", "HolDiv": "0"},
        {"Date": "2026-06-18", "HolDiv": "1"},
    ]
    dates = resolve_business_dates(run_date="2026-06-16", calendar_records=records)
    assert dates.virtual_order_date == "2026-06-18"
    assert dates.calendar_source == "jquants_trading_calendar"

