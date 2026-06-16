from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.broker.sanitizer import sanitize_mapping
from ai_fund_lab_v2.order_manager.schema import OrderPlan, OrderPlanItem, OrderPlanItemSide, OrderPlanStatus


class OrderPlanStoreError(RuntimeError):
    pass


def order_plan_directory(runtime_dir: Path | str = ".runtime") -> Path:
    return Path(runtime_dir) / "order_manager" / "plans"


def validate_order_plan_for_storage(order_plan: OrderPlan) -> None:
    if not order_plan.plan_id:
        raise OrderPlanStoreError("OrderPlan plan_id is required.")
    if not (order_plan.generated_at or order_plan.created_at):
        raise OrderPlanStoreError("OrderPlan generated_at is required.")
    if not order_plan.schema_version:
        raise OrderPlanStoreError("OrderPlan schema_version is required.")
    if not order_plan.source:
        raise OrderPlanStoreError("OrderPlan source is required.")
    if order_plan.executable is not False:
        raise OrderPlanStoreError("Phase8 OrderPlan must be non-executable.")
    if order_plan.live_order_allowed is not False:
        raise OrderPlanStoreError("Phase8 OrderPlan must not allow live orders.")
    if order_plan.requires_human_review is not True:
        raise OrderPlanStoreError("Phase8 OrderPlan requires human review.")
    if any(item.executable for item in order_plan.items):
        raise OrderPlanStoreError("Phase8 OrderPlan items must be non-executable.")


def write_order_plan(order_plan: OrderPlan, runtime_dir: Path | str = ".runtime") -> Path:
    validate_order_plan_for_storage(order_plan)
    path = order_plan_directory(runtime_dir) / f"{order_plan.plan_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = sanitize_mapping(order_plan.to_dict())
    payload["executable"] = False
    payload["live_order_allowed"] = False
    payload["requires_human_review"] = True
    payload["generated_at"] = payload.get("generated_at") or payload.get("created_at")
    payload["status"] = payload.get("status") or payload.get("plan_status")
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_order_plan(path: Path) -> OrderPlan:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise OrderPlanStoreError(f"Invalid OrderPlan JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise OrderPlanStoreError("OrderPlan payload must be an object.")
    return order_plan_from_payload(payload)


def order_plan_from_payload(payload: dict[str, Any]) -> OrderPlan:
    if payload.get("executable") is not False:
        raise OrderPlanStoreError("Stored OrderPlan executable flag is invalid.")
    if payload.get("live_order_allowed") is not False:
        raise OrderPlanStoreError("Stored OrderPlan live flag is invalid.")
    if payload.get("requires_human_review") is not True:
        raise OrderPlanStoreError("Stored OrderPlan review flag is invalid.")
    items = tuple(_item(item) for item in payload.get("items", []) if isinstance(item, dict))
    status_value = str(payload.get("status") or payload.get("plan_status") or OrderPlanStatus.INVALID_INPUT.value)
    try:
        plan_status = OrderPlanStatus(status_value)
    except ValueError:
        plan_status = OrderPlanStatus.INVALID_INPUT
    return OrderPlan(
        broker_snapshot_id=str(payload.get("broker_snapshot_id", "")),
        policy_id=str(payload.get("policy_id", "")),
        items=items,
        plan_id=str(payload.get("plan_id", "")),
        created_at=str(payload.get("created_at") or payload.get("generated_at") or ""),
        generated_at=str(payload.get("generated_at") or payload.get("created_at") or ""),
        schema_version=str(payload.get("schema_version", "")),
        broker=str(payload.get("broker", "moomoo")),
        paper_ledger_id=str(payload.get("paper_ledger_id", "")),
        safety_status=str(payload.get("safety_status", "")),
        lock_state=str(payload.get("lock_state", "")),
        executable=False,
        live_order_allowed=False,
        requires_human_review=True,
        plan_status=plan_status,
        blocked_reasons=tuple(str(value) for value in payload.get("blocked_reasons", [])),
        warnings=tuple(str(value) for value in payload.get("warnings", [])),
        audit_refs=tuple(str(value) for value in payload.get("audit_refs", [])),
        source=str(payload.get("source", "")),
    )


def _item(payload: dict[str, Any]) -> OrderPlanItem:
    side_value = str(payload.get("side") or "NOOP")
    try:
        side = OrderPlanItemSide(side_value)
    except ValueError:
        side = OrderPlanItemSide.NOOP
    return OrderPlanItem(
        issue_code=str(payload.get("issue_code", "")),
        side=side,
        action=str(payload.get("action", "")),
        item_id=str(payload.get("item_id", "")),
        issue_name=str(payload.get("issue_name", "")),
        quantity=_decimal(payload.get("quantity")),
        lot_size=int(payload.get("lot_size", 100)),
        estimated_price=_decimal(payload.get("estimated_price")),
        estimated_value=_decimal(payload.get("estimated_value")),
        source_decision_id=str(payload.get("source_decision_id", "")),
        reason_code=str(payload.get("reason_code", "")),
        cash_required=_decimal(payload.get("cash_required")),
        sell_first_group_id=str(payload.get("sell_first_group_id", "")),
        depends_on_fill_item_id=str(payload.get("depends_on_fill_item_id", "")),
        broker_position_quantity=_decimal(payload.get("broker_position_quantity")),
        paper_position_quantity=_decimal(payload.get("paper_position_quantity")),
        status=str(payload.get("status", "REVIEW_REQUIRED")),
        executable=False,
        review_required=True,
        requires_broker_snapshot_refresh=bool(payload.get("requires_broker_snapshot_refresh", False)),
    )


def _decimal(value: Any) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    return Decimal(str(value).replace(",", ""))
