from pathlib import Path

from ai_fund_lab_v2.data_quality import FetchPlanBuilder, TradingCalendarService
from tests.test_trading_calendar_service import calendar_store


def test_fetch_plan_daily_quotes_business_days_only(tmp_path: Path) -> None:
    builder = FetchPlanBuilder(TradingCalendarService(calendar_store(tmp_path)))

    plan = builder.build_fetch_plan("daily_quotes", "2026-06-01", "2026-06-07")

    assert [item.date for item in plan] == ["2026-06-01", "2026-06-02", "2026-06-03", "2026-06-04", "2026-06-05"]


def test_fetch_plan_trading_calendar_uses_range(tmp_path: Path) -> None:
    builder = FetchPlanBuilder(TradingCalendarService(calendar_store(tmp_path)))

    plan = builder.build_fetch_plan("trading_calendar", "2026-06-01", "2026-06-07")

    assert len(plan) == 1
    assert plan[0].from_date == "2026-06-01"
    assert plan[0].to_date == "2026-06-07"


def test_fetch_plan_listed_issues_uses_to_date_snapshot(tmp_path: Path) -> None:
    builder = FetchPlanBuilder(TradingCalendarService(calendar_store(tmp_path)))

    plan = builder.build_fetch_plan("listed_issues", "2026-06-01", "2026-06-07")

    assert len(plan) == 1
    assert plan[0].date == "2026-06-07"
    assert plan[0].reason == "listed_issues_to_date_snapshot"


def test_fetch_plan_fins_summary_business_days_only(tmp_path: Path) -> None:
    builder = FetchPlanBuilder(TradingCalendarService(calendar_store(tmp_path)))

    plan = builder.build_fetch_plan("fins_summary", "2026-06-01", "2026-06-07")

    assert [item.date for item in plan] == ["2026-06-01", "2026-06-02", "2026-06-03", "2026-06-04", "2026-06-05"]
