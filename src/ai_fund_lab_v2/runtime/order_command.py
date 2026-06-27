from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from enum import Enum
from typing import Any

from ai_fund_lab_v2.runtime.runtime_mode import RuntimeMode


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    CASH_EQUITY = "CASH_EQUITY"
    MARGIN_EQUITY = "MARGIN_EQUITY"


class PriceType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class OrderResultStatus(str, Enum):
    PAPER_ONLY_SUBMITTED = "PAPER_ONLY_SUBMITTED"
    BLOCKED_NO_APPROVAL = "BLOCKED_NO_APPROVAL"
    BLOCKED_LIVE_ORDER_DISABLED = "BLOCKED_LIVE_ORDER_DISABLED"
    BLOCKED_APPROVAL_SCOPE_MISMATCH = "BLOCKED_APPROVAL_SCOPE_MISMATCH"
    BLOCKED_SECOND_PASSWORD_MISSING = "BLOCKED_SECOND_PASSWORD_MISSING"
    BLOCKED_PRODUCTION_PROHIBITED = "BLOCKED_PRODUCTION_PROHIBITED"
    BLOCKED_EXECUTOR_STUB = "BLOCKED_EXECUTOR_STUB"
    DRY_RUN_READY = "DRY_RUN_READY"
    REJECTED_INVALID_COMMAND = "REJECTED_INVALID_COMMAND"


@dataclass(frozen=True)
class OrderCommand:
    runtime_id: str
    environment: RuntimeMode
    paper_test_id: str
    issue_code: str
    side: OrderSide
    quantity: Decimal
    order_type: OrderType
    price_type: PriceType
    limit_price: Decimal = Decimal("0")
    evaluation_cash_basis: Decimal = Decimal("0")
    broker_cash_upper_bound: Decimal = Decimal("0")
    approval_required: bool = True
    approval_id: str = ""
    live_order_allowed: bool = False

    def __post_init__(self) -> None:
        if not self.runtime_id:
            raise ValueError("OrderCommand requires runtime_id.")
        if not self.issue_code:
            raise ValueError("OrderCommand requires issue_code.")
        if self.quantity <= Decimal("0"):
            raise ValueError("OrderCommand quantity must be positive.")
        if self.limit_price < Decimal("0"):
            raise ValueError("OrderCommand limit_price must be non-negative.")
        if self.evaluation_cash_basis < Decimal("0"):
            raise ValueError("OrderCommand evaluation_cash_basis must be non-negative.")
        if self.broker_cash_upper_bound < Decimal("0"):
            raise ValueError("OrderCommand broker_cash_upper_bound must be non-negative.")

    def to_dict(self) -> dict[str, Any]:
        payload = _jsonable(asdict(self))
        payload["environment"] = self.environment.value
        payload["side"] = self.side.value
        payload["order_type"] = self.order_type.value
        payload["price_type"] = self.price_type.value
        return payload


@dataclass(frozen=True)
class OrderResult:
    status: OrderResultStatus
    submitted: bool = False
    accepted: bool = False
    rejected: bool = False
    skipped: bool = False
    reason: str = ""
    broker_order_id_hash: str = ""

    def __post_init__(self) -> None:
        if self.broker_order_id_hash and len(self.broker_order_id_hash) < 16:
            raise ValueError("broker_order_id_hash must be hashed or omitted.")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        return payload


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value
