from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class BusinessDayGuardResult:
    business_date: str
    is_business_day: bool
    reason: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "business_date": self.business_date,
            "is_business_day": self.is_business_day,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class BusinessDayGuard:
    holidays: frozenset[str] = frozenset()

    def check(self, business_date: str) -> BusinessDayGuardResult:
        parsed = date.fromisoformat(business_date)
        if parsed.weekday() >= 5:
            return BusinessDayGuardResult(business_date=business_date, is_business_day=False, reason="weekend")
        if business_date in self.holidays:
            return BusinessDayGuardResult(business_date=business_date, is_business_day=False, reason="holiday")
        return BusinessDayGuardResult(business_date=business_date, is_business_day=True, reason="business_day")
