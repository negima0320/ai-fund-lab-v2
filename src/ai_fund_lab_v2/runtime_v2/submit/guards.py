"""Runtime v2 Submit preflight guards."""

from __future__ import annotations

import hashlib
from datetime import date, datetime

from ai_fund_lab_v2.runtime_v2.approval.models import ApprovalArtifact, ApprovalStatus
from ai_fund_lab_v2.runtime_v2.broker_adapter.capability import (
    BrokerCapability,
    get_broker_capability,
    is_symbol_allowed_by_capability,
)
from ai_fund_lab_v2.runtime_v2.pending.consume import can_submit_pending_plan
from ai_fund_lab_v2.runtime_v2.pending.models import PendingOrderPlan, PendingPlanState
from ai_fund_lab_v2.runtime_v2.pending.review_scope_authority import (
    build_pending_review_scope_authority,
    pending_scope_allows_partial_submit,
)
from ai_fund_lab_v2.runtime_v2.submit.models import (
    RuntimeV2SubmitCommand,
    RuntimeV2SubmitPreflightResult,
    SubmitEnvironmentGuardContext,
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
    broker_position_quantity: float | None = None,
    broker_available_quantity: float | None = None,
    source_current_path: str = "pending_order_plan/pending_order_plan.json",
    broker_capability: BrokerCapability | None = None,
    environment_context: SubmitEnvironmentGuardContext | None = None,
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
        broker_position_quantity=broker_position_quantity,
        broker_available_quantity=broker_available_quantity,
        source_current_path=source_current_path,
        broker_capability=broker_capability,
        environment_context=environment_context,
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
    conditions = approval_artifact.approved_order_conditions
    item_condition = conditions.get(item.pending_item_id) if isinstance(conditions, dict) else None
    if not isinstance(item_condition, dict):
        raise ValueError("approved order condition missing")
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
        price_type=str(item_condition["price_condition"]),
        limit_price=None if item.order_type == "MARKET" else float(item_condition["limit_price"]),
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
    broker_position_quantity: float | None,
    broker_available_quantity: float | None,
    source_current_path: str,
    broker_capability: BrokerCapability | None,
    environment_context: SubmitEnvironmentGuardContext | None,
) -> str:
    capability = broker_capability or get_broker_capability(environment)
    environment_reason = _environment_matrix_block_reason(
        pending_plan=pending_plan,
        environment=environment,
        base_url_is_demo=base_url_is_demo,
        base_url_is_production=base_url_is_production,
        live_order_allowed=live_order_allowed,
        environment_context=environment_context,
    )
    if environment_reason:
        return environment_reason
    if not live_order_allowed:
        return "live order disabled"
    if source_current_path != "pending_order_plan/pending_order_plan.json":
        return "submit source must be pending_order_plan current"
    scope_authority = build_pending_review_scope_authority(pending_plan)
    if pending_plan.state != PendingPlanState.APPROVED and not pending_scope_allows_partial_submit(scope_authority):
        return "pending state is not APPROVED"
    if approval_artifact.status != ApprovalStatus.APPROVED:
        return "approval artifact is not APPROVED"
    if approval_artifact.pending_plan_id != pending_plan.pending_plan_id:
        return "approval pending_plan_id mismatch"
    if pending_plan.approval is None:
        return "pending approval link missing"
    if pending_plan.approval.approval_hash != approval_artifact.approval_hash:
        return "approval hash mismatch"
    if _approval_expired_for_target_session(approval_artifact.expires_at, pending_plan.target_session_date):
        return "approval expired"
    if approved_item_id not in pending_plan.approved_item_ids:
        return "approved item missing from pending"
    if not can_submit_pending_plan(pending_plan, existing_order_dedup_keys):
        return "duplicate submit guard or pending lifecycle blocked"
    item = next((item for item in pending_plan.items if item.pending_item_id == approved_item_id), None)
    if item is None:
        return "approved item not found"
    if item.side not in {"BUY", "SELL"}:
        return "unsupported side"
    if item.order_type not in {"MARKET", "LIMIT"}:
        return "order condition authority review required"
    condition_reason = _order_condition_block_reason(
        approval_artifact=approval_artifact,
        item=item,
        target_session_date=pending_plan.target_session_date,
    )
    if condition_reason:
        return condition_reason
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
    return ""


def _environment_matrix_block_reason(
    *,
    pending_plan: PendingOrderPlan,
    environment: str,
    base_url_is_demo: bool,
    base_url_is_production: bool,
    live_order_allowed: bool,
    environment_context: SubmitEnvironmentGuardContext | None,
) -> str:
    context = environment_context or SubmitEnvironmentGuardContext(
        runtime_environment=environment,
        pending_environment=pending_plan.environment,
        run_type=environment.upper(),
        broker_environment="tachibana_demo" if environment == "demo" else "",
        adapter_type="DemoSubmitAdapter" if environment == "demo" else "",
        broker_write=bool(live_order_allowed and environment == "demo"),
        external_delivery=False,
        business_date=pending_plan.target_session_date,
        evaluation_time=pending_plan.target_session_date,
        production_acceptance=False,
    )
    if context.runtime_environment != environment:
        return "environment matrix guard failure: runtime environment mismatch"
    if context.pending_environment != pending_plan.environment:
        return "environment matrix guard failure: pending environment mismatch"
    if environment == "demo":
        if pending_plan.environment != "demo":
            return "environment guard failure"
        if context.run_type != "DEMO":
            return "environment matrix guard failure: demo run_type mismatch"
        if context.broker_environment != "tachibana_demo":
            return "environment matrix guard failure: demo broker_environment mismatch"
        if context.adapter_type not in {"DemoSubmitAdapter", "TachibanaDemoSubmitAdapter", "RuntimeV2DemoSubmitAdapter"}:
            return "environment matrix guard failure: demo adapter mismatch"
        if not context.broker_write:
            return "environment matrix guard failure: demo broker_write must be true for submit"
        if not base_url_is_demo or base_url_is_production:
            return "demo-only guard failure"
        return ""
    if environment == "historical":
        if pending_plan.environment != "historical":
            return "environment matrix guard failure: historical pending environment mismatch"
        if context.run_type != "HISTORICAL":
            return "environment matrix guard failure: historical run_type mismatch"
        if context.broker_environment != "historical_simulated":
            return "environment matrix guard failure: historical broker_environment mismatch"
        if context.adapter_type != "HistoricalSubmitAdapter":
            return "environment matrix guard failure: historical adapter mismatch"
        if context.broker_write:
            return "environment matrix guard failure: historical broker_write must be false"
        if context.external_delivery:
            return "environment matrix guard failure: historical external_delivery must be false"
        if not context.business_date:
            return "environment matrix guard failure: historical business_date missing"
        if not context.evaluation_time:
            return "environment matrix guard failure: historical evaluation_time missing"
        return ""
    if environment == "production":
        if pending_plan.environment != "production":
            if environment_context is None:
                return "environment guard failure"
            return "environment matrix guard failure: production pending environment mismatch"
        if not context.production_acceptance:
            return "production submit requires explicit production acceptance"
        if context.run_type != "PRODUCTION":
            return "environment matrix guard failure: production run_type mismatch"
        if context.broker_environment != "tachibana_production":
            return "environment matrix guard failure: production broker_environment mismatch"
        if context.adapter_type != "ProductionSubmitAdapter":
            return "environment matrix guard failure: production adapter mismatch"
        return ""
    return "environment guard failure"


def _approval_expired_for_target_session(expires_at: str, target_session_date: str) -> bool:
    expires_date = _date_from_iso(expires_at)
    target_date = _date_from_iso(target_session_date)
    if expires_date is None or target_date is None:
        return False
    return expires_date < target_date


def _order_condition_block_reason(
    *,
    approval_artifact: ApprovalArtifact,
    item: object,
    target_session_date: str,
) -> str:
    conditions = approval_artifact.approved_order_conditions
    if conditions is None:
        return "approved order conditions missing"
    item_condition = conditions.get(item.pending_item_id) if isinstance(conditions, dict) else None
    if not isinstance(item_condition, dict):
        return "order condition not approved"
    expected_text = {
        "order_type": item.order_type,
        "target_session": target_session_date,
        "side": item.side,
        "issue_code": item.symbol,
    }
    for key, expected_value in expected_text.items():
        if str(item_condition.get(key)) != str(expected_value):
            return "approved order condition mismatch"
    try:
        if float(item_condition.get("quantity")) != float(item.quantity):
            return "approved order condition mismatch"
    except (TypeError, ValueError):
        return "approved order condition mismatch"
    if item.order_type == "MARKET" and item_condition.get("limit_price") is not None:
        return "market order limit_price must be null"
    if item.order_type == "LIMIT" and item_condition.get("limit_price") in (None, ""):
        return "limit order limit_price missing"
    if not item_condition.get("time_in_force"):
        return "time_in_force missing"
    if not item_condition.get("price_condition"):
        return "price_condition missing"
    return ""


def _date_from_iso(value: str) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None


def _command_id(pending_plan_id: str, pending_item_id: str, approval_hash: str) -> str:
    raw = "|".join((pending_plan_id, pending_item_id, approval_hash))
    return "submit-command-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
