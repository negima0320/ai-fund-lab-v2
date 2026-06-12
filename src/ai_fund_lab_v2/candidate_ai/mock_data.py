from __future__ import annotations

from datetime import date, timedelta
from typing import Any


DEFAULT_MOCK_AS_OF_DATE = "2026-06-01"


def build_mock_daily_quotes_normalized(as_of_date: str = DEFAULT_MOCK_AS_OF_DATE) -> list[dict[str, Any]]:
    """Build a tiny daily_quotes_normalized-like fixture for Phase4-E dry-runs."""

    end_date = date.fromisoformat(as_of_date)
    rows: list[dict[str, Any]] = []

    for index, business_date in enumerate(_business_dates(end_date, 24), start=1):
        close = 100.0 + (index * 1.4)
        rows.append(
            {
                "date": business_date.isoformat(),
                "code": "7203",
                "open": round(close - 0.8, 2),
                "high": round(close + 1.3, 2),
                "low": round(close - 1.7, 2),
                "close": round(close, 2),
                "volume": 1_000_000 + (index * 15_000),
            }
        )

    for index, business_date in enumerate(_business_dates(end_date, 4), start=1):
        close = 50.0 + index
        rows.append(
            {
                "date": business_date.isoformat(),
                "code": "9999",
                "open": round(close - 0.5, 2),
                "high": round(close + 0.6, 2),
                "low": round(close - 0.7, 2),
                "close": round(close, 2),
                "volume": 100_000 + (index * 3_000),
            }
        )

    future_date = _next_business_day(end_date)
    rows.append(
        {
            "date": future_date.isoformat(),
            "code": "7203",
            "open": 9999.0,
            "high": 9999.0,
            "low": 9999.0,
            "close": 9999.0,
            "volume": 999_999_999,
        }
    )
    return rows


def _business_dates(end_date: date, count: int) -> list[date]:
    dates: list[date] = []
    current = end_date
    while len(dates) < count:
        if current.weekday() < 5:
            dates.append(current)
        current -= timedelta(days=1)
    return list(reversed(dates))


def _next_business_day(value: date) -> date:
    current = value + timedelta(days=1)
    while current.weekday() >= 5:
        current += timedelta(days=1)
    return current
