from __future__ import annotations

from dataclasses import dataclass

from ai_fund_lab_v2.data_quality.trading_calendar import TradingCalendarService, iter_dates


@dataclass(frozen=True)
class FetchPlanItem:
    endpoint_name: str
    date: str | None = None
    from_date: str | None = None
    to_date: str | None = None
    reason: str = ""


@dataclass(frozen=True)
class FetchPlanBuilder:
    calendar: TradingCalendarService

    def build_fetch_plan(self, endpoint_name: str, from_date: str, to_date: str) -> list[FetchPlanItem]:
        if endpoint_name == "daily_quotes":
            return self.build_daily_fetch_plan(from_date, to_date)
        if endpoint_name == "trading_calendar":
            return [FetchPlanItem(endpoint_name, from_date=from_date, to_date=to_date, reason="calendar_range")]
        if endpoint_name == "listed_issues":
            return [FetchPlanItem(endpoint_name, date=to_date, reason="listed_issues_to_date_snapshot")]
        if endpoint_name == "earnings_calendar":
            return [FetchPlanItem(endpoint_name, date=to_date, reason="earnings_calendar_snapshot")]
        if endpoint_name == "fins_summary":
            return [FetchPlanItem(endpoint_name, date=day, reason="business_day") for day in self.calendar.list_business_days(from_date, to_date)]
        if endpoint_name == "all":
            plan: list[FetchPlanItem] = []
            for name in ("daily_quotes", "listed_issues", "earnings_calendar", "trading_calendar", "fins_summary"):
                plan.extend(self.build_fetch_plan(name, from_date, to_date))
            return plan
        raise ValueError(f"Unsupported endpoint for fetch plan: {endpoint_name}")

    def build_daily_fetch_plan(self, from_date: str, to_date: str) -> list[FetchPlanItem]:
        business_days = set(self.calendar.list_business_days(from_date, to_date))
        return [
            FetchPlanItem("daily_quotes", date=day, reason="business_day")
            for day in iter_dates(from_date, to_date)
            if day in business_days
        ]
