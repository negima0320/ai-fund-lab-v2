"""Pending composition helpers for the single canonical Pending authority."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.approval.linkage import link_approval_to_pending
from ai_fund_lab_v2.runtime_v2.approval.models import ApprovalDecision, ApprovalStatus
from ai_fund_lab_v2.runtime_v2.approval.policy import build_approval_artifact, build_approval_request
from ai_fund_lab_v2.runtime_v2.pending.models import PendingOrderItem, PendingOrderPlan, PendingPlanState
from ai_fund_lab_v2.runtime_v2.pending.promotion import promote_order_plan_to_pending
from ai_fund_lab_v2.runtime_v2.pending.reader import read_pending_order_plan_path


INACTIVE_PENDING_STATES = {
    PendingPlanState.CONSUMED,
    PendingPlanState.EMPTY,
    PendingPlanState.EXPIRED,
    PendingPlanState.CANCELLED,
    PendingPlanState.SUPERSEDED,
    PendingPlanState.REJECTED,
    PendingPlanState.SUBMITTED,
}


def read_active_buy_pending(
    *,
    runtime_root: Path,
    environment: str,
    business_date: str,
    target_session_date: str,
) -> tuple[PendingOrderPlan | None, str]:
    path = runtime_root / "pending_order_plan" / "pending_order_plan.json"
    read_result = read_pending_order_plan_path(path=path, environment=environment)
    if not read_result.valid or read_result.plan is None:
        return None, read_result.classification
    plan = read_result.plan
    if plan.state in INACTIVE_PENDING_STATES:
        return None, f"inactive_state:{plan.state.value}"
    if plan.consume.consumed:
        return None, "consumed"
    if plan.plan_created_date != business_date or plan.target_session_date != target_session_date:
        return None, "date_mismatch"
    approved_ids = set(plan.approved_item_ids)
    buy_items = tuple(
        item
        for item in plan.items
        if item.side.upper() == "BUY" and item.pending_item_id in approved_ids and item.quantity > 0
    )
    if not buy_items:
        return None, "active_buy_missing"
    return plan, "PASS"


def compose_with_existing_buy_pending(
    *,
    existing_buy_pending: PendingOrderPlan | None,
    pending: PendingOrderPlan,
    artifact_dir: Path,
    business_date: str,
    target_session_date: str,
    environment: str,
    reason: str,
) -> tuple[PendingOrderPlan, Path, Path, dict]:
    if existing_buy_pending is None:
        return pending, Path(pending.source_order_plan.path), Path(pending.approval.approval_path if pending.approval else ""), {
            "composition_model": "SINGLE_PENDING_NO_EXISTING_BUY",
            "composition_status": "NOT_REQUIRED",
            "preserved_existing_buy_pending": False,
            "composite_pending": False,
        }
    existing_buy_items = tuple(item for item in existing_buy_pending.items if item.side.upper() == "BUY")
    composed_items = _dedupe_items(existing_buy_items + pending.items)
    order_plan_id = f"order-plan-pending-composite-{business_date}-{_short_items_hash(composed_items)}"
    order_plan_path = artifact_dir / "pending_composition_order_plan.json"
    approval_path = artifact_dir / "pending_composition_approval_artifact.json"
    order_plan_payload = {
        "schema_version": "1",
        "order_plan_id": order_plan_id,
        "environment": environment,
        "business_date": business_date,
        "target_session_date": target_session_date,
        "status": "PASS",
        "composition_model": "COMPOSITE_PENDING_PLAN",
        "composition_reason": reason,
        "source_buy_pending_plan_id": existing_buy_pending.pending_plan_id,
        "source_buy_pending_path": "pending_order_plan/pending_order_plan.json",
        "source_sell_order_plan_id": pending.source_order_plan.order_plan_id,
        "source_sell_order_plan_path": pending.source_order_plan.path,
        "items": [asdict(item) for item in composed_items],
    }
    order_plan_path.write_text(_json_dumps(order_plan_payload), encoding="utf-8")
    composed = promote_order_plan_to_pending(
        order_plan_id=order_plan_id,
        source_order_plan_path=str(order_plan_path),
        source_order_plan_hash=_hash(order_plan_path.read_text(encoding="utf-8")),
        environment=environment,
        plan_created_date=business_date,
        intended_submit_date=target_session_date,
        target_session_date=target_session_date,
        items=composed_items,
    )
    approved_item_ids = tuple(item.pending_item_id for item in composed.items)
    request = build_approval_request(
        pending_plan=composed,
        business_date=business_date,
        expires_at=f"{business_date}T15:00:00+09:00",
    )
    approval = build_approval_artifact(
        request=request,
        decision=ApprovalDecision(
            status=ApprovalStatus.APPROVED,
            approved_item_ids=approved_item_ids,
            rejected_item_ids=(),
            reason="runtime v2 pending composition approval",
            operator="runtime_v2_pending_composition_job",
            decided_at=f"{business_date}T08:46:00+09:00",
        ),
    )
    approval_path.write_text(_json_dumps(_jsonable(approval)), encoding="utf-8")
    composed = link_approval_to_pending(pending_plan=composed, approval_artifact=approval)
    evidence = {
        "composition_model": "COMPOSITE_PENDING_PLAN",
        "composition_status": "PASS",
        "preserved_existing_buy_pending": True,
        "composite_pending": True,
        "source_buy_pending_plan_id": existing_buy_pending.pending_plan_id,
        "source_sell_pending_plan_id": pending.pending_plan_id,
        "composed_buy_item_count": sum(1 for item in composed.items if item.side.upper() == "BUY"),
        "composed_sell_item_count": sum(1 for item in composed.items if item.side.upper() == "SELL"),
        "composed_item_count": len(composed.items),
        "duplicate_pending_items_removed": len(existing_buy_items) + len(pending.items) - len(composed.items),
    }
    return composed, order_plan_path, approval_path, evidence


def _dedupe_items(items: tuple[PendingOrderItem, ...]) -> tuple[PendingOrderItem, ...]:
    seen: set[str] = set()
    deduped: list[PendingOrderItem] = []
    for item in items:
        if item.pending_item_id in seen:
            continue
        seen.add(item.pending_item_id)
        deduped.append(item)
    return tuple(deduped)


def _short_items_hash(items: tuple[PendingOrderItem, ...]) -> str:
    payload = [
        {
            "pending_item_id": item.pending_item_id,
            "symbol": item.symbol,
            "side": item.side,
            "quantity": item.quantity,
        }
        for item in items
    ]
    return hashlib.sha256(_json_dumps(payload).encode("utf-8")).hexdigest()[:12]


def _hash(payload: str) -> str:
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _json_dumps(payload) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _jsonable(value):
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "__dataclass_fields__"):
        return {key: _jsonable(getattr(value, key)) for key in value.__dataclass_fields__}
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value
