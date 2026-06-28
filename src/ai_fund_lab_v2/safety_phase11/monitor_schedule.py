from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time


DEFAULT_MONITOR_TIMES: tuple[str, ...] = ("09:05", "09:30", "10:30", "12:35", "14:45", "15:20")


@dataclass(frozen=True)
class MonitorSchedule:
    times: tuple[str, ...] = DEFAULT_MONITOR_TIMES

    def scheduled_times(self) -> tuple[str, ...]:
        return self.times

    def is_market_hours(self, value: datetime | time | str) -> bool:
        current = _parse_time(value)
        return time(9, 0) <= current <= time(15, 30)

    def next_monitor_time(self, value: datetime | time | str) -> str | None:
        current = _parse_time(value)
        for item in self.times:
            scheduled = _parse_time(item)
            if scheduled > current:
                return item
        return None

    def next_monitor_datetime(self, value: datetime) -> datetime | None:
        next_time = self.next_monitor_time(value)
        if next_time is None:
            return None
        parsed = _parse_time(next_time)
        return datetime.combine(value.date(), parsed, tzinfo=value.tzinfo)


def default_monitor_schedule() -> MonitorSchedule:
    return MonitorSchedule()


def _parse_time(value: datetime | date | time | str) -> time:
    if isinstance(value, datetime):
        return value.time().replace(tzinfo=None)
    if isinstance(value, time):
        return value.replace(tzinfo=None)
    if isinstance(value, str):
        hour, minute = value.split(":", 1)
        return time(int(hour), int(minute[:2]))
    raise TypeError("monitor schedule expects datetime, time, or HH:MM string")
