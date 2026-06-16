from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Mapping

from ai_fund_lab_v2.data_store import StorageBackendError, create_storage_backend
from ai_fund_lab_v2.runtime import RuntimePaths


@dataclass(frozen=True)
class BusinessDateResolution:
    run_date: str
    decision_for: str
    data_until: str
    virtual_order_date: str
    virtual_execution_date: str
    calendar_source: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def resolve_business_dates(
    *,
    run_date: str | None = None,
    data_until: str | None = None,
    runtime_dir: Path | str = ".runtime",
    calendar_records: Iterable[Mapping[str, Any]] | None = None,
) -> BusinessDateResolution:
    resolved_run_date = _normalize_date(run_date) if run_date else date.today().isoformat()
    decision_for = resolved_run_date
    records = list(calendar_records) if calendar_records is not None else _read_calendar_records(runtime_dir)
    next_day, source = _next_business_day(decision_for, records)
    return BusinessDateResolution(
        run_date=resolved_run_date,
        decision_for=decision_for,
        data_until=data_until or decision_for,
        virtual_order_date=next_day,
        virtual_execution_date=next_day,
        calendar_source=source,
    )


def _next_business_day(target_date: str, calendar_records: list[Mapping[str, Any]]) -> tuple[str, str]:
    if calendar_records:
        calendar = {_record_date(record): record for record in calendar_records if _record_date(record)}
        current = _parse_date(target_date) + timedelta(days=1)
        latest = max(_parse_date(day) for day in calendar)
        while current <= latest:
            day = current.isoformat()
            record = calendar.get(day)
            if record and _is_business_record(record):
                return day, "jquants_trading_calendar"
            current += timedelta(days=1)
    current = _parse_date(target_date) + timedelta(days=1)
    while current.weekday() >= 5:
        current += timedelta(days=1)
    return current.isoformat(), "weekday_fallback"


def _read_calendar_records(runtime_dir: Path | str) -> list[dict[str, Any]]:
    base = RuntimePaths(runtime_dir=Path(runtime_dir)).raw_data / "jquants" / "trading_calendar" / "data"
    for storage_format in ("parquet", "jsonl"):
        backend = create_storage_backend(storage_format)
        path = backend.path_for(base)
        if not path.exists():
            continue
        try:
            return backend.read_records(path)
        except (StorageBackendError, ImportError, RuntimeError):
            return []
    return []


def _record_date(record: Mapping[str, Any]) -> str:
    return str(record.get("target_date") or record.get("Date") or record.get("date") or "")


def _is_business_record(record: Mapping[str, Any]) -> bool:
    value = str(record.get("HolDiv") or record.get("HolidayDivision") or record.get("holiday_division") or "")
    return value == "1"


def _normalize_date(value: str) -> str:
    return _parse_date(value).isoformat()


def _parse_date(value: str) -> date:
    if len(value) == 8 and value.isdigit():
        return date(int(value[0:4]), int(value[4:6]), int(value[6:8]))
    return datetime.strptime(value, "%Y-%m-%d").date()

