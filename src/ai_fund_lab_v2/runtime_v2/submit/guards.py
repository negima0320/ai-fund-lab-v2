"""Runtime v2 Submit preflight guards."""

from __future__ import annotations

import hashlib

from ai_fund_lab_v2.runtime_v2.approval.models import ApprovalArtifact, ApprovalStatus
from ai_fund_lab_v2.runtime_v2.broker_adapter.capability import (
    BrokerCapability,
    get_broker_capability,
    is_symbol_allowed_by_capability,
)
from ai_fund_lab_v2.runtime_v2.pending.consume import can_submit_pending_plan
from ai_fund_lab_v2.runtime_v2.pending.models import PendingOrderPlan, PendingPlanState
from ai_fund_lab_v2.runtime_v2.submit.models import (
    RuntimeV2SubmitCommand,
    RuntimeV2SubmitPreflightResult,
)


def run_submit_preflight(
    *,
    pending_plan: PendingOrderPlan,
    approval_artifact: ApprovalArtifact,
    approved_item_id: str,
    existing_order_dedup_keys: set[str],
    environment: str,
    base_url_is_demo: bool,
    base_url_is_production: bool,
    live_order_allowed: bool,
    max_order_amount: float | None = None,
    broker_position_quantity: float | None = None,
    broker_available_quantity: float | None = None,
    source_current_path: str = "pending_order_plan/pending_order_plan.json",
    broker_capability: BrokerCapability | None = None,
) -> RuntimeV2SubmitPreflightResult:
    """Validate Runtime v2 submit guards and build a submit command."""

    blocked_reason = _blocked_reason(
        pending_plan=pending_plan,
        approval_artifact=approval_artifact,
        approved_item_id=approved_item_id,
        existing_order_dedup_keys=existing_order_dedup_keys,
        environment=environment,
        base_url_is_demo=base_url_is_demo,
        base_url_is_production=base_url_is_production,
        live_order_allowed=live_order_allowed,
        max_order_amount=max_order_amount,
        broker_position_quantity=broker_position_quantity,
        broker_available_quantity=broker_available_quantity,
        source_current_path=source_current_path,
        broker_capability=broker_capability,
    )
    if blocked_reason:
        return RuntimeV2SubmitPreflightResult(
            allowed=False,
            blocked=True,
            review_required=False,
            reason=blocked_reason,
        )
    return RuntimeV2SubmitPreflightResult(
        allowed=True,
        blocked=False,
        review_required=False,
        reason="approved",
        command=build_runtime_v2_submit_command(
            pending_plan=pending_plan,
            approval_artifact=approval_artifact,
            approved_item_id=approved_item_id,
            live_order_allowed=live_order_allowed,
            source_current_path=source_current_path,
        ),
    )


def build_runtime_v2_submit_command(
    *,
    pending_plan: PendingOrderPlan,
    approval_artifact: ApprovalArtifact,
    approved_item_id: str,
    live_order_allowed: bool,
    source_current_path: str = "pending_order_plan/pending_order_plan.json",
) -> RuntimeV2SubmitCommand:
    item = next(item for item in pending_plan.items if item.pending_item_id == approved_item_id)
    return RuntimeV2SubmitCommand(
        command_id=_command_id(pending_plan.pending_plan_id, item.pending_item_id, approval_artifact.approval_hash),
        environment=pending_plan.environment,
        pending_plan_id=pending_plan.pending_plan_id,
        pending_item_id=item.pending_item_id,
        approval_hash=approval_artifact.approval_hash,
        symbol=item.symbol,
        side=item.side,
        quantity=item.quantity,
        order_type=item.order_type,
        price_type="MARKET" if item.order_type == "MARKET" else "LIMIT",
        limit_price=0.0 if item.order_type == "MARKET" else item.estimated_price,
        estimated_amount=item.estimated_amount,
        target_session_date=pending_plan.target_session_date,
        live_order_allowed=live_order_allowed,
        source_current_path=source_current_path,
        listed_info=item.listed_info,
    )


def _blocked_reason(
    *,
    pending_plan: PendingOrderPlan,
    approval_artifact: ApprovalArtifact,
    approved_item_id: str,
    existing_order_dedup_keys: set[str],
    environment: str,
    base_url_is_demo: bool,
    base_url_is_production: bool,
    live_order_allowed: bool,
    max_order_amount: float | None,
    broker_position_quantity: float | None,
    broker_available_quantity: float | None,
    source_current_path: str,
    broker_capability: BrokerCapability | None,
) -> str:
    capability = broker_capability or get_broker_capability(environment)
    if environment != "demo" or pending_plan.environment != "demo":
        return "environment guard failure"
    if not base_url_is_demo or base_url_is_production:
        return "demo-only guard failure"
    if not live_order_allowed:
        return "live order disabled"
    if source_current_path != "pending_order_plan/pending_order_plan.json":
        return "submit source must be pending_order_plan current"
    if pending_plan.state != PendingPlanState.APPROVED:
        return "pending state is not APPROVED"
    if approval_artifact.status != ApprovalStatus.APPROVED:
        return "approval artifact is not APPROVED"
    if approval_artifact.pending_plan_id != pending_plan.pending_plan_id:
        return "approval pending_plan_id mismatch"
    if pending_plan.approval is None:
        return "pending approval link missing"
    if pending_plan.approval.approval_hash != approval_artifact.approval_hash:
        return "approval hash mismatch"
    if approved_item_id not in pending_plan.approved_item_ids:
        return "approved item missing from pending"
    if not can_submit_pending_plan(pending_plan, existing_order_dedup_keys):
        return "duplicate submit guard or pending lifecycle blocked"
    item = next((item for item in pending_plan.items if item.pending_item_id == approved_item_id), None)
    if item is None:
        return "approved item not found"
    if item.side not in {"BUY", "SELL"}:
        return "unsupported side"
    if not is_symbol_allowed_by_capability(item.symbol, capability):
        return "symbol not supported by broker capability"
    if item.quantity <= 0:
        return "quantity must be positive"
    if item.side == "SELL":
        if broker_position_quantity is None:
            return "sell broker position quantity missing"
        if broker_available_quantity is None:
            return "sell available quantity missing"
        if item.quantity > broker_position_quantity:
            return "sell quantity exceeds broker position"
        if item.quantity > broker_available_quantity:
            return "sell quantity exceeds available quantity"
    if max_order_amount is not None and item.estimated_amount > max_order_amount:
        return "estimated amount exceeds max order amount"
    return ""


def _command_id(pending_plan_id: str, pending_item_id: str, approval_hash: str) -> str:
    raw = "|".join((pending_plan_id, pending_item_id, approval_hash))
    return "submit-command-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
