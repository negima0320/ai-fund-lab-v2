"""Data models for the Runtime Temporal / Freshness Contract."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any


class FreshnessStatus(str, Enum):
    READY = "READY"
    VALID_CARRYOVER = "VALID_CARRYOVER"
    DATA_NOT_YET_AVAILABLE = "DATA_NOT_YET_AVAILABLE"
    STALE = "STALE"
    MISSING = "MISSING"
    DATE_MISMATCH = "DATE_MISMATCH"
    EXPIRED = "EXPIRED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    HALT = "HALT"
    NOT_REQUIRED = "NOT_REQUIRED"


@dataclass(frozen=True)
class PublicationWindow:
    expected_available_at: datetime | None = None
    grace_period: timedelta | None = None

    def is_before_available(self, now: datetime | None) -> bool:
        if now is None or self.expected_available_at is None:
            return False
        return now < self.expected_available_at

    def is_within_grace(self, now: datetime | None) -> bool:
        if now is None or self.expected_available_at is None or self.grace_period is None:
            return False
        return self.expected_available_at <= now <= self.expected_available_at + self.grace_period

    def is_after_grace(self, now: datetime | None) -> bool:
        if now is None or self.expected_available_at is None:
            return True
        if self.grace_period is None:
            return now >= self.expected_available_at
        return now > self.expected_available_at + self.grace_period

    def to_payload(self) -> dict[str, Any]:
        return {
            "expected_available_at": _iso_or_none(self.expected_available_at),
            "grace_period_seconds": int(self.grace_period.total_seconds()) if self.grace_period else None,
        }


@dataclass(frozen=True)
class TemporalContext:
    runtime_business_date: str
    calendar_date: str
    trading_session_date: str
    latest_expected_trading_date: str
    latest_available_market_date: str
    runtime_timezone: str
    calendar_source: str
    publication_window: PublicationWindow | None
    grace_period: timedelta | None
    runtime_mode: str = "demo"
    broker_environment: str = "demo"
    temporal_authority_source: str = "runtime_business_date"
    temporal_authority_winner: str = "runtime_business_date"
    temporal_authority_status: str = "PASS"
    temporal_authority_reason: str = ""
    temporal_fallback_used: bool = False

    @property
    def is_non_trading_carryover_day(self) -> bool:
        return self.runtime_business_date != self.latest_expected_trading_date

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["publication_window"] = (
            self.publication_window.to_payload() if self.publication_window is not None else None
        )
        payload["grace_period_seconds"] = int(self.grace_period.total_seconds()) if self.grace_period else None
        return payload


@dataclass(frozen=True)
class TemporalEvidence:
    expected_date: str
    actual_date: str
    generated_at: str
    expires_at: str
    status: FreshnessStatus
    reason: str
    comparison_contract: str
    source: str
    artifact_path: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "expected_date": self.expected_date,
            "actual_date": self.actual_date,
            "generated_at": self.generated_at,
            "expires_at": self.expires_at,
            "status": self.status.value,
            "reason": self.reason,
            "comparison_contract": self.comparison_contract,
            "source": self.source,
            "artifact_path": self.artifact_path,
        }


@dataclass(frozen=True)
class CurrentTemporalState:
    position_state_as_of: str
    valuation_as_of: str
    last_execution_date: str
    last_reconciled_at: str
    source_market_date: str

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MarketTemporalState:
    market_date: str
    latest_expected_trading_date: str
    latest_available_market_date: str
    publication_status: str
    provider_status: str

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RuntimeStateTemporalState:
    runtime_state_date: str
    runtime_operation_state: str
    runtime_state_status: FreshnessStatus

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["runtime_state_status"] = self.runtime_state_status.value
        return payload


def _iso_or_none(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()
