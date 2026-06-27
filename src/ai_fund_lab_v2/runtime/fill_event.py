from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any

from ai_fund_lab_v2.runtime.order_command import OrderSide
from ai_fund_lab_v2.runtime.runtime_mode import RuntimeMode
from ai_fund_lab_v2.runtime.states import RuntimeState


class OrderLifecycle(str, Enum):
    PREPARED = "PREPARED"
    SUBMISSION_BLOCKED = "SUBMISSION_BLOCKED"
    SUBMITTED = "SUBMITTED"
    ACCEPTED = "ACCEPTED"
    WAITING_FILL = "WAITING_FILL"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CANCELED = "CANCELED"
    UNKNOWN_STATUS = "UNKNOWN_STATUS"
    REQUIRES_HUMAN_REVIEW = "REQUIRES_HUMAN_REVIEW"


class FillMonitorStatus(str, Enum):
    PASS = "PASS"
    PASS_WITH_REVIEW = "PASS_WITH_REVIEW"
    HALT = "HALT"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class FillEvent:
    runtime_id: str
    environment: RuntimeMode
    issue_code: str
    side: OrderSide
    order_quantity: Decimal
    filled_quantity: Decimal = Decimal("0")
    remaining_quantity: Decimal = Decimal("0")
    average_fill_price: Decimal = Decimal("0")
    latest_fill_price: Decimal = Decimal("0")
    order_status: str = ""
    lifecycle_status: OrderLifecycle = OrderLifecycle.UNKNOWN_STATUS
    order_number_hash: str = ""
    execution_id_hash: str = ""
    observed_at: str = field(default_factory=utc_now_iso)
    source: str = "mock"
    raw_ids_saved: bool = False

    def __post_init__(self) -> None:
        if not self.runtime_id:
            raise ValueError("FillEvent requires runtime_id.")
        if not self.issue_code:
            raise ValueError("FillEvent requires issue_code.")
        if self.order_quantity < Decimal("0"):
            raise ValueError("FillEvent order_quantity must be non-negative.")
        if self.filled_quantity < Decimal("0"):
            raise ValueError("FillEvent filled_quantity must be non-negative.")
        if self.remaining_quantity < Decimal("0"):
            raise ValueError("FillEvent remaining_quantity must be non-negative.")
        if self.raw_ids_saved:
            raise ValueError("FillEvent must not persist raw order or execution ids.")
        _validate_hash("order_number_hash", self.order_number_hash)
        _validate_hash("execution_id_hash", self.execution_id_hash)

    def to_dict(self) -> dict[str, Any]:
        payload = _jsonable(asdict(self))
        payload["environment"] = self.environment.value
        payload["side"] = self.side.value
        payload["lifecycle_status"] = self.lifecycle_status.value
        return payload


@dataclass(frozen=True)
class FillMonitorResult:
    status: FillMonitorStatus
    lifecycle_status: OrderLifecycle
    runtime_next_state: RuntimeState
    filled: bool = False
    partially_filled: bool = False
    rejected: bool = False
    expired: bool = False
    canceled: bool = False
    requires_human_review: bool = False
    reason: str = ""
    events: tuple[FillEvent, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "lifecycle_status": self.lifecycle_status.value,
            "runtime_next_state": self.runtime_next_state.value,
            "filled": self.filled,
            "partially_filled": self.partially_filled,
            "rejected": self.rejected,
            "expired": self.expired,
            "canceled": self.canceled,
            "requires_human_review": self.requires_human_review,
            "reason": self.reason,
            "events": [event.to_dict() for event in self.events],
        }


def runtime_state_for_lifecycle(lifecycle: OrderLifecycle) -> RuntimeState:
    return {
        OrderLifecycle.PREPARED: RuntimeState.ORDER_PREPARED,
        OrderLifecycle.SUBMISSION_BLOCKED: RuntimeState.ORDER_PREPARED,
        OrderLifecycle.SUBMITTED: RuntimeState.ORDER_SUBMITTED,
        OrderLifecycle.ACCEPTED: RuntimeState.WAITING_FILL,
        OrderLifecycle.WAITING_FILL: RuntimeState.WAITING_FILL,
        OrderLifecycle.PARTIALLY_FILLED: RuntimeState.PARTIALLY_FILLED,
        OrderLifecycle.FILLED: RuntimeState.FILLED,
        OrderLifecycle.REJECTED: RuntimeState.HALT,
        OrderLifecycle.EXPIRED: RuntimeState.HALT,
        OrderLifecycle.CANCELED: RuntimeState.HALT,
        OrderLifecycle.UNKNOWN_STATUS: RuntimeState.HALT,
        OrderLifecycle.REQUIRES_HUMAN_REVIEW: RuntimeState.HALT,
    }[lifecycle]


def _validate_hash(name: str, value: str) -> None:
    if value and not value.startswith("sha256:"):
        raise ValueError(f"{name} must be a sha256 hash or omitted.")


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
