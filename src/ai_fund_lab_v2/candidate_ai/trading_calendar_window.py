from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class TradingCalendarWindow:
    requested_as_of_date: str
    normalized_as_of_date: str
    window_start_date: str
    business_days: tuple[str, ...]
    source: str
    as_of_date_was_normalized: bool


def build_trading_calendar_window(
    *,
    as_of_date: str,
    lookback_business_days: int,
    calendar_records: Iterable[Mapping[str, Any]] | None = None,
) -> TradingCalendarWindow:
    if lookback_business_days <= 0:
        raise ValueError("lookback_business_days must be positive")
    records = [dict(record) for record in (calendar_records or [])]
    if records:
        return _build_from_calendar_records(
            as_of_date=as_of_date,
            lookback_business_days=lookback_business_days,
            records=records,
        )
    return _build_from_weekday_fallback(as_of_date=as_of_date, lookback_business_days=lookback_business_days)


def _build_from_calendar_records(
    *,
    as_of_date: str,
    lookback_business_days: int,
    records: list[dict[str, Any]],
) -> TradingCalendarWindow:
    business_days = sorted(
        {
            str(record.get("target_date") or record.get("Date"))
            for record in records
            if str(record.get("HolDiv") or record.get("HolidayDivision") or "") == "1"
            and (record.get("target_date") or record.get("Date"))
        }
    )
    if not business_days:
        return _build_from_weekday_fallback(as_of_date=as_of_date, lookback_business_days=lookback_business_days)
    candidates = [day for day in business_days if day <= as_of_date]
    if not candidates:
        normalized_as_of_date = business_days[0]
    else:
        normalized_as_of_date = candidates[-1]
    end_index = business_days.index(normalized_as_of_date)
    start_index = max(0, end_index - lookback_business_days + 1)
    window_days = tuple(business_days[start_index : end_index + 1])
    return TradingCalendarWindow(
        requested_as_of_date=as_of_date,
        normalized_as_of_date=normalized_as_of_date,
        window_start_date=window_days[0],
        business_days=window_days,
        source="trading_calendar_raw",
        as_of_date_was_normalized=normalized_as_of_date != as_of_date,
    )


def _build_from_weekday_fallback(*, as_of_date: str, lookback_business_days: int) -> TradingCalendarWindow:
    normalized = _previous_weekday(_parse_date(as_of_date))
    days: list[str] = []
    current = normalized
    while len(days) < lookback_business_days:
        if current.weekday() < 5:
            days.append(current.isoformat())
        current -= timedelta(days=1)
    window_days = tuple(reversed(days))
    return TradingCalendarWindow(
        requested_as_of_date=as_of_date,
        normalized_as_of_date=normalized.isoformat(),
        window_start_date=window_days[0],
        business_days=window_days,
        source="weekday_fallback",
        as_of_date_was_normalized=normalized.isoformat() != as_of_date,
    )


def _previous_weekday(value: date) -> date:
    current = value
    while current.weekday() >= 5:
        current -= timedelta(days=1)
    return current


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)
