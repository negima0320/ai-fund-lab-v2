from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.operations.market_calendar import resolve_operation_date


def test_market_calendar_weekday_business_day_uses_fallback() -> None:
    result = resolve_operation_date("2026-06-29")

    assert result["is_business_day"] is True
    assert result["market_closed"] is False
    assert result["calendar_source"] == "fallback"


def test_market_calendar_weekend_is_market_closed() -> None:
    result = resolve_operation_date("2026-06-27")

    assert result["is_business_day"] is False
    assert result["market_closed"] is True
    assert result["market_closed_reason"] == "WEEKEND"


def test_market_calendar_known_japanese_holiday_is_market_closed() -> None:
    result = resolve_operation_date("2026-09-21")

    assert result["is_business_day"] is False
    assert result["market_closed"] is True
    assert result["market_closed_reason"] == "JP_MARKET_HOLIDAY_FALLBACK"
    assert result["calendar_source"] == "fallback"


def test_market_calendar_target_dates_use_correct_business_day_status() -> None:
    expected = {
        "2026-06-30": False,
        "2026-07-01": False,
        "2026-07-02": False,
        "2026-07-04": True,
        "2026-07-05": True,
    }

    for trade_date, market_closed in expected.items():
        result = resolve_operation_date(trade_date)
        assert result["market_closed"] is market_closed


def test_partial_jquants_calendar_missing_weekday_falls_back_to_business_day(tmp_path: Path) -> None:
    calendar_path = tmp_path / "jquants" / "raw" / "jquants" / "trading_calendar" / "data.json"
    calendar_path.parent.mkdir(parents=True, exist_ok=True)
    calendar_path.write_text(json.dumps({"records": [{"target_date": "2026-06-30", "HolDiv": "1"}]}), encoding="utf-8")

    result = resolve_operation_date("2026-07-01", root=tmp_path)

    assert result["calendar_source"] == "jquants_trading_calendar_partial_fallback"
    assert result["is_business_day"] is True
    assert result["market_closed"] is False
    assert result["market_closed_reason"] == ""
    assert result["latest_available_market_date"] == "2026-07-01"
