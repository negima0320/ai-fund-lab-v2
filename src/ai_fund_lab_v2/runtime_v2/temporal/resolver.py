"""Runtime temporal context resolver."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from ai_fund_lab_v2.operations.market_calendar import resolve_operation_date
from ai_fund_lab_v2.runtime_v2.temporal.models import PublicationWindow, TemporalContext


RUNTIME_TIMEZONE = "Asia/Tokyo"


def resolve_temporal_context(
    *,
    runtime_business_date: str | date,
    runtime_mode: str = "demo",
    broker_environment: str = "demo",
    latest_available_market_date: str | None = None,
    calendar_source: str | None = None,
    publication_window: PublicationWindow | None = None,
    grace_period: timedelta | None = None,
    now: datetime | None = None,
    root: Path | str | None = None,
) -> TemporalContext:
    business_date = runtime_business_date.isoformat() if isinstance(runtime_business_date, date) else runtime_business_date
    jst_now = (now or datetime.now(ZoneInfo(RUNTIME_TIMEZONE))).astimezone(ZoneInfo(RUNTIME_TIMEZONE))
    calendar = resolve_operation_date(business_date, root=root)
    latest_expected = str(calendar.get("latest_available_market_date") or business_date)
    latest_available = latest_available_market_date or latest_expected
    effective_grace_period = grace_period
    if effective_grace_period is None and publication_window is not None:
        effective_grace_period = publication_window.grace_period
    return TemporalContext(
        runtime_business_date=business_date,
        calendar_date=jst_now.date().isoformat(),
        trading_session_date=latest_expected,
        latest_expected_trading_date=latest_expected,
        latest_available_market_date=latest_available,
        runtime_timezone=RUNTIME_TIMEZONE,
        calendar_source=calendar_source or str(calendar.get("calendar_source") or "fallback"),
        publication_window=publication_window,
        grace_period=effective_grace_period,
        runtime_mode=runtime_mode,
        broker_environment=broker_environment,
    )
