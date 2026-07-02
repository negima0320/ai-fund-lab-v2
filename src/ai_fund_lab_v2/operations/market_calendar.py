from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any


FALLBACK_JP_MARKET_HOLIDAYS = frozenset(
    {
        "2025-01-01",
        "2025-01-02",
        "2025-01-03",
        "2025-01-13",
        "2025-02-11",
        "2025-02-24",
        "2025-03-20",
        "2025-04-29",
        "2025-05-03",
        "2025-05-05",
        "2025-05-06",
        "2025-07-21",
        "2025-08-11",
        "2025-09-15",
        "2025-09-23",
        "2025-10-13",
        "2025-11-03",
        "2025-11-24",
        "2025-12-31",
        "2026-01-01",
        "2026-01-02",
        "2026-01-12",
        "2026-02-11",
        "2026-02-23",
        "2026-03-20",
        "2026-04-29",
        "2026-05-04",
        "2026-05-05",
        "2026-05-06",
        "2026-07-20",
        "2026-08-11",
        "2026-09-21",
        "2026-09-22",
        "2026-09-23",
        "2026-10-12",
        "2026-11-03",
        "2026-11-23",
        "2026-12-31",
        "2027-01-01",
        "2027-01-11",
        "2027-02-11",
        "2027-02-23",
        "2027-03-22",
        "2027-04-29",
        "2027-05-03",
        "2027-05-04",
        "2027-05-05",
        "2027-07-19",
        "2027-08-11",
        "2027-09-20",
        "2027-09-23",
        "2027-10-11",
        "2027-11-03",
        "2027-11-23",
        "2027-12-31",
    }
)


def resolve_operation_date(target_date: str | date, *, root: Path | str | None = None) -> dict[str, Any]:
    day = _as_date(target_date)
    calendar = _load_jquants_calendar(Path(root)) if root is not None else {}
    source = _calendar_source(day, calendar)
    business_day = _is_business_day(day, calendar=calendar)
    reason = "" if business_day else market_closed_reason(day, calendar=calendar)
    previous_day = _resolve_adjacent_business_day(day, previous=True, calendar=calendar)
    next_day = _resolve_adjacent_business_day(day, previous=False, calendar=calendar)
    return {
        "trade_date": day.isoformat(),
        "is_business_day": business_day,
        "market_closed": not business_day,
        "market_closed_reason": reason,
        "calendar_source": source,
        "latest_available_market_date": day.isoformat() if business_day else previous_day.isoformat(),
        "previous_business_day": previous_day.isoformat(),
        "next_business_day": next_day.isoformat(),
    }


def is_business_day(target_date: str | date, *, root: Path | str | None = None) -> bool:
    return bool(resolve_operation_date(target_date, root=root)["is_business_day"])


def market_closed_reason(target_date: str | date, *, calendar: dict[str, dict[str, Any]] | None = None) -> str:
    day = _as_date(target_date)
    if day.weekday() >= 5:
        return "WEEKEND"
    if calendar:
        record = calendar.get(day.isoformat())
        if record is None:
            return "JP_MARKET_HOLIDAY_FALLBACK" if day.isoformat() in FALLBACK_JP_MARKET_HOLIDAYS else ""
        return "JQUANTS_NON_BUSINESS_DAY"
    if day.isoformat() in FALLBACK_JP_MARKET_HOLIDAYS:
        return "JP_MARKET_HOLIDAY_FALLBACK"
    return ""


def previous_business_day(target_date: str | date, *, calendar: dict[str, dict[str, Any]] | None = None) -> date:
    current = _as_date(target_date) - timedelta(days=1)
    for _ in range(370):
        if _is_business_day(current, calendar=calendar):
            return current
        current -= timedelta(days=1)
    raise RuntimeError("previous business day could not be resolved")


def next_business_day(target_date: str | date, *, calendar: dict[str, dict[str, Any]] | None = None) -> date:
    current = _as_date(target_date) + timedelta(days=1)
    for _ in range(370):
        if _is_business_day(current, calendar=calendar):
            return current
        current += timedelta(days=1)
    raise RuntimeError("next business day could not be resolved")


def _resolve_adjacent_business_day(day: date, *, previous: bool, calendar: dict[str, dict[str, Any]]) -> date:
    try:
        if previous:
            return previous_business_day(day, calendar=calendar)
        return next_business_day(day, calendar=calendar)
    except RuntimeError:
        if previous:
            return previous_business_day(day, calendar={})
        return next_business_day(day, calendar={})


def _is_business_day(day: date, *, calendar: dict[str, dict[str, Any]] | None = None) -> bool:
    if calendar:
        record = calendar.get(day.isoformat())
        if record is None:
            return day.weekday() < 5 and day.isoformat() not in FALLBACK_JP_MARKET_HOLIDAYS
        holdiv = str(record.get("HolDiv") or record.get("HolidayDivision") or "")
        return holdiv == "1"
    return day.weekday() < 5 and day.isoformat() not in FALLBACK_JP_MARKET_HOLIDAYS


def _calendar_source(day: date, calendar: dict[str, dict[str, Any]]) -> str:
    if not calendar:
        return "fallback"
    if day.isoformat() in calendar:
        return "jquants_trading_calendar"
    return "jquants_trading_calendar_partial_fallback"


def _load_jquants_calendar(root: Path | None) -> dict[str, dict[str, Any]]:
    if root is None:
        return {}
    candidates = [
        root / "jquants" / "raw" / "jquants" / "trading_calendar" / "data.parquet",
        root / "jquants" / "raw" / "jquants" / "trading_calendar" / "data.jsonl",
        root / "jquants" / "raw" / "jquants" / "trading_calendar" / "data.json",
    ]
    for path in candidates:
        if not path.exists():
            continue
        try:
            records = _read_calendar_records(path)
        except Exception:
            continue
        calendar = {}
        for record in records:
            key = str(record.get("target_date") or record.get("Date") or "")
            if key:
                calendar[key] = record
        if calendar:
            return calendar
    return {}


def _read_calendar_records(path: Path) -> list[dict[str, Any]]:
    if path.suffix == ".parquet":
        import pandas as pd

        return pd.read_parquet(path).to_dict(orient="records")
    if path.suffix == ".jsonl":
        import json

        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if path.suffix == ".json":
        import json

        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            return list(payload.get("records") or payload.get("data") or [])
    return []


def _as_date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)
