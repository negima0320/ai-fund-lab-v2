from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import uuid4

from ai_fund_lab_v2.broker.models import utc_now_iso


def order_plan_id() -> str:
    return f"order_plan_{uuid4().hex}"


def order_plan_item_id() -> str:
    return f"order_plan_item_{uuid4().hex}"


class OrderPlanItemSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    NOOP = "NOOP"


class OrderPlanStatus(str, Enum):
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    REVIEW_ONLY_LOCKED = "REVIEW_ONLY_LOCKED"
    REVIEW_ONLY_RECONCILIATION_HALT = "REVIEW_ONLY_RECONCILIATION_HALT"
    INVALID_INPUT = "INVALID_INPUT"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class OrderPlanItem:
    issue_code: str
    side: OrderPlanItemSide
    action: str
    item_id: str = field(default_factory=order_plan_item_id)
    issue_name: str = ""
    quantity: Decimal = Decimal("0")
    lot_size: int = 100
    estimated_price: Decimal = Decimal("0")
    estimated_value: Decimal = Decimal("0")
    source_decision_id: str = ""
    reason_code: str = ""
    cash_required: Decimal = Decimal("0")
    sell_first_group_id: str = ""
    depends_on_fill_item_id: str = ""
    broker_position_quantity: Decimal = Decimal("0")
    paper_position_quantity: Decimal = Decimal("0")
    status: str = "REVIEW_REQUIRED"
    executable: bool = False
    review_required: bool = True
    requires_broker_snapshot_refresh: bool = False

    def __post_init__(self) -> None:
        if self.executable:
            raise ValueError("Phase8 OrderPlanItem must not be executable.")
        if not self.review_required:
            raise ValueError("Phase8 OrderPlanItem requires human review.")

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass(frozen=True)
class OrderPlan:
    broker_snapshot_id: str
    policy_id: str
    items: tuple[OrderPlanItem, ...] = ()
    plan_id: str = field(default_factory=order_plan_id)
    created_at: str = field(default_factory=utc_now_iso)
    generated_at: str = ""
    schema_version: str = "phase8.order_plan.v1"
    broker: str = "moomoo"
    paper_ledger_id: str = ""
    safety_status: str = "OK"
    lock_state: str = "unlocked"
    executable: bool = False
    live_order_allowed: bool = False
    requires_human_review: bool = True
    plan_status: OrderPlanStatus = OrderPlanStatus.REVIEW_REQUIRED
    blocked_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    audit_refs: tuple[str, ...] = ()
    source: str = "phase8_order_plan"

    def __post_init__(self) -> None:
        if not self.plan_id or not self.schema_version or not self.source:
            raise ValueError("Phase8 OrderPlan requires plan_id, schema_version, and source.")
        if self.broker != "moomoo":
            raise ValueError("Phase8 OrderPlan broker must be moomoo.")
        if self.executable:
            raise ValueError("Phase8 OrderPlan must not be executable.")
        if self.live_order_allowed:
            raise ValueError("Phase8 OrderPlan must not allow live orders.")
        if not self.requires_human_review:
            raise ValueError("Phase8 OrderPlan requires human review.")
        if any(item.executable for item in self.items):
            raise ValueError("Phase8 OrderPlan cannot contain executable items.")

    def to_dict(self) -> dict[str, Any]:
        payload = _jsonable(asdict(self))
        payload["generated_at"] = self.generated_at or self.created_at
        payload["status"] = self.plan_status.value
        return payload


def create_order_plan(
    *,
    broker_snapshot_id: str,
    policy_id: str,
    items: list[OrderPlanItem] | tuple[OrderPlanItem, ...],
    paper_ledger_id: str = "",
    safety_status: str = "OK",
    lock_state: str = "unlocked",
    blocked_reasons: tuple[str, ...] = (),
    warnings: tuple[str, ...] = (),
    plan_status: OrderPlanStatus | None = None,
) -> OrderPlan:
    status = plan_status or (OrderPlanStatus.REVIEW_ONLY_LOCKED if lock_state == "locked" else OrderPlanStatus.READY_FOR_REVIEW)
    if blocked_reasons and lock_state != "locked":
        status = plan_status or OrderPlanStatus.BLOCKED
    return OrderPlan(
        broker_snapshot_id=broker_snapshot_id,
        policy_id=policy_id,
        paper_ledger_id=paper_ledger_id,
        items=tuple(items),
        safety_status=safety_status,
        lock_state=lock_state,
        plan_status=status,
        blocked_reasons=blocked_reasons,
        warnings=warnings,
    )


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
