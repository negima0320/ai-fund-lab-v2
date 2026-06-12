from pathlib import Path

import pytest

from ai_fund_lab_v2.data_quality import CalendarDataNotFoundError, TradingCalendarService
from ai_fund_lab_v2.data_store import MarketDataStore
from ai_fund_lab_v2.runtime import RuntimePaths


def test_trading_calendar_business_day_helpers(tmp_path: Path) -> None:
    store = calendar_store(tmp_path)
    service = TradingCalendarService(store)

    assert service.is_business_day("2026-06-01") is True
    assert service.is_business_day("2026-06-06") is False
    assert service.list_business_days("2026-06-01", "2026-06-07") == [
        "2026-06-01",
        "2026-06-02",
        "2026-06-03",
        "2026-06-04",
        "2026-06-05",
    ]
    assert service.previous_business_day("2026-06-08") == "2026-06-05"
    assert service.next_business_day("2026-06-05") == "2026-06-08"


def test_trading_calendar_missing_raw_raises_clear_error(tmp_path: Path) -> None:
    service = TradingCalendarService(MarketDataStore(RuntimePaths(runtime_dir=tmp_path / "runtime")))

    with pytest.raises(CalendarDataNotFoundError, match="trading_calendar raw data is missing"):
        service.is_business_day("2026-06-01")


def calendar_store(tmp_path: Path) -> MarketDataStore:
    store = MarketDataStore(RuntimePaths(runtime_dir=tmp_path / "runtime"))
    records = [
        {"Date": "2026-06-01", "HolDiv": "1"},
        {"Date": "2026-06-02", "HolDiv": "1"},
        {"Date": "2026-06-03", "HolDiv": "1"},
        {"Date": "2026-06-04", "HolDiv": "1"},
        {"Date": "2026-06-05", "HolDiv": "1"},
        {"Date": "2026-06-06", "HolDiv": "0"},
        {"Date": "2026-06-07", "HolDiv": "0"},
        {"Date": "2026-06-08", "HolDiv": "1"},
    ]
    store.save_raw(records, endpoint="/v2/markets/calendar", collection="jquants/trading_calendar")
    return store
