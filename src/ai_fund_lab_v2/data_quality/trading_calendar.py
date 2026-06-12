from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from ai_fund_lab_v2.data_sources.jquants.raw_ingestion import RAW_COLLECTIONS
from ai_fund_lab_v2.data_store import MarketDataStore


class CalendarDataNotFoundError(RuntimeError):
    """Raised when raw trading calendar data is not available."""


@dataclass(frozen=True)
class TradingCalendarService:
    store: MarketDataStore

    def is_business_day(self, target_date: str) -> bool:
        calendar = self._calendar_by_date()
        record = calendar.get(target_date)
        if record is None:
            return False
        return str(record.get("HolDiv") or record.get("HolidayDivision") or "") == "1"

    def list_business_days(self, from_date: str, to_date: str) -> list[str]:
        self._ensure_calendar_loaded()
        return [day for day in iter_dates(from_date, to_date) if self.is_business_day(day)]

    def previous_business_day(self, target_date: str) -> str | None:
        self._ensure_calendar_loaded()
        current = parse_date(target_date) - timedelta(days=1)
        earliest = min(parse_date(day) for day in self._calendar_by_date())
        while current >= earliest:
            day = current.isoformat()
            if self.is_business_day(day):
                return day
            current -= timedelta(days=1)
        return None

    def next_business_day(self, target_date: str) -> str | None:
        self._ensure_calendar_loaded()
        current = parse_date(target_date) + timedelta(days=1)
        latest = max(parse_date(day) for day in self._calendar_by_date())
        while current <= latest:
            day = current.isoformat()
            if self.is_business_day(day):
                return day
            current += timedelta(days=1)
        return None

    def _calendar_by_date(self) -> dict[str, dict]:
        records = self.store.read_raw_collection(RAW_COLLECTIONS["trading_calendar"])
        if not records:
            raise CalendarDataNotFoundError(
                "J-Quants trading_calendar raw data is missing. "
                "Fetch it before building calendar-based plans."
            )
        return {str(record.get("target_date") or record.get("Date")): record for record in records}

    def _ensure_calendar_loaded(self) -> None:
        self._calendar_by_date()


def iter_dates(from_date: str, to_date: str) -> list[str]:
    start = parse_date(from_date)
    end = parse_date(to_date)
    if end < start:
        raise ValueError("to_date must be greater than or equal to from_date")
    days: list[str] = []
    current = start
    while current <= end:
        days.append(current.isoformat())
        current += timedelta(days=1)
    return days


def parse_date(value: str) -> date:
    if len(value) == 8 and value.isdigit():
        return date(int(value[0:4]), int(value[4:6]), int(value[6:8]))
    return date.fromisoformat(value)
