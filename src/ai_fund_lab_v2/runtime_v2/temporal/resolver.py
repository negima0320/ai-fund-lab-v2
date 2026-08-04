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
    status = "PASS"
    reason = ""
    if not _valid_date(business_date):
        status = "REVIEW_REQUIRED"
        reason = "runtime_business_date_invalid"
    elif business_date > jst_now.date().isoformat():
        status = "REVIEW_REQUIRED"
        reason = "runtime_business_date_future"
    calendar = (
        {"latest_available_market_date": business_date, "calendar_source": "runtime_business_date_invalid"}
        if status == "REVIEW_REQUIRED" and reason == "runtime_business_date_invalid"
        else resolve_operation_date(business_date, root=root)
    )
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
        temporal_authority_source="runtime_business_date",
        temporal_authority_winner="runtime_business_date",
        temporal_authority_status=status,
        temporal_authority_reason=reason,
        temporal_fallback_used=False,
    )


def _valid_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
    except (TypeError, ValueError):
        return False
    return True
