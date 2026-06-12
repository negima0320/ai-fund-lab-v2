from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any


class SafetyStatus(str, Enum):
    OK = "OK"
    WARNING = "WARNING"
    HALT = "HALT"


class ReconciliationSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    HALT = "HALT"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def decimal_or_zero(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    return Decimal(str(value).replace(",", ""))


@dataclass(frozen=True)
class PortfolioPositionState:
    symbol: str
    quantity: Decimal
    side: str = "long"
    account_type: str = "cash"
    average_price: Decimal | None = None


@dataclass(frozen=True)
class BrokerPositionState:
    symbol: str
    quantity: Decimal
    side: str = "long"
    account_type: str = "cash"
    average_price: Decimal | None = None


@dataclass(frozen=True)
class OpenOrderState:
    order_id: str
    symbol: str
    side: str
    quantity: Decimal
    status: str = "open"


@dataclass(frozen=True)
class PortfolioState:
    cash: Decimal
    buying_power: Decimal
    positions: tuple[PortfolioPositionState, ...] = ()
    open_orders: tuple[OpenOrderState, ...] = ()
    as_of: str = field(default_factory=utc_now_iso)


@dataclass(frozen=True)
class BrokerState:
    cash: Decimal
    buying_power: Decimal
    positions: tuple[BrokerPositionState, ...] = ()
    open_orders: tuple[OpenOrderState, ...] = ()
    as_of: str = field(default_factory=utc_now_iso)
    source_snapshot_id: str | None = None


@dataclass(frozen=True)
class ReconciliationIssue:
    code: str
    severity: ReconciliationSeverity
    message: str
    symbol: str | None = None
    expected: str | None = None
    actual: str | None = None


@dataclass(frozen=True)
class ReconciliationResult:
    status: SafetyStatus
    issues: tuple[ReconciliationIssue, ...] = ()
    checked_at: str = field(default_factory=utc_now_iso)


@dataclass(frozen=True)
class TradingLock:
    is_locked: bool
    reason: str
    status: SafetyStatus
    created_at: str = field(default_factory=utc_now_iso)
    issues: tuple[ReconciliationIssue, ...] = ()


@dataclass(frozen=True)
class SafetyReport:
    status: SafetyStatus
    checked_at: str
    broker_snapshot_id: str | None
    issue_count: int
    issues: tuple[ReconciliationIssue, ...]
    trading_locked: bool
