from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Union
from uuid import uuid4


def broker_snapshot_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class BrokerBalanceSnapshot:
    broker: str = "tachibana"
    source: str = "mock"
    as_of: str = field(default_factory=utc_now_iso)
    currency: str = "JPY"
    cash_available: Decimal = Decimal("0")
    buying_power: Decimal = Decimal("0")
    withdrawable_cash: Decimal = Decimal("0")
    total_assets: Decimal = Decimal("0")
    raw_clmid: str = ""
    raw_result_code: str = ""
    warnings: tuple[str, ...] = ()
    snapshot_id: str = field(default_factory=lambda: broker_snapshot_id("balance"))


@dataclass(frozen=True)
class BrokerPositionSnapshot:
    broker: str = "tachibana"
    source: str = "mock"
    as_of: str = field(default_factory=utc_now_iso)
    account_type: str = "cash"
    issue_code: str = ""
    issue_name: str = ""
    quantity: Decimal = Decimal("0")
    available_quantity: Decimal = Decimal("0")
    average_price: Decimal = Decimal("0")
    market_price: Decimal = Decimal("0")
    market_value: Decimal = Decimal("0")
    unrealized_pnl: Decimal = Decimal("0")
    raw_clmid: str = ""
    raw_result_code: str = ""
    warnings: tuple[str, ...] = ()
    snapshot_id: str = field(default_factory=lambda: broker_snapshot_id("position"))


@dataclass(frozen=True)
class BrokerOrderSnapshot:
    broker: str = "tachibana"
    source: str = "mock"
    as_of: str = field(default_factory=utc_now_iso)
    order_id: str = ""
    issue_code: str = ""
    issue_name: str = ""
    side: str = ""
    order_type: str = ""
    quantity: Decimal = Decimal("0")
    executed_quantity: Decimal = Decimal("0")
    remaining_quantity: Decimal = Decimal("0")
    price: Decimal = Decimal("0")
    status: str = ""
    order_datetime: str = ""
    expire_date: str = ""
    raw_clmid: str = ""
    raw_result_code: str = ""
    warnings: tuple[str, ...] = ()
    snapshot_id: str = field(default_factory=lambda: broker_snapshot_id("order"))


BrokerSnapshot = Union[BrokerBalanceSnapshot, BrokerPositionSnapshot, BrokerOrderSnapshot]


def decimal_or_zero(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    return Decimal(str(value).replace(",", ""))
