"""Promotion skeleton for Runtime v2 Pending Order Plans."""

from __future__ import annotations

from dataclasses import replace
from typing import Mapping, Sequence

from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import capital_deployment_policy_hash_from_context
from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import CapitalDeploymentPolicy
from ai_fund_lab_v2.runtime_v2.pending.lifecycle import validate_pending_transition
from ai_fund_lab_v2.runtime_v2.pending.models import (
    PendingApprovalLink,
    PendingConsumeInfo,
    PendingOrderItem,
    PendingOrderPlan,
    PendingPlanState,
    PendingSourceOrderPlan,
    PendingSubmitConstraints,
)
from ai_fund_lab_v2.runtime_v2.pending.safety_authority import (
    materialize_historical_pending_safety_context,
)
from ai_fund_lab_v2.runtime_v2.planning_submit_feasibility import (
    RuntimeCurrentExposure,
    evaluate_planning_submit_feasibility,
)
from ai_fund_lab_v2.runtime_v2.cash_exposure_authority import cash_exposure_authority_from_context
from ai_fund_lab_v2.runtime_v2.position_count_authority import position_count_authority_from_context


def promote_order_plan_to_pending(
    *,
    order_plan_id: str,
    source_order_plan_path: str,
    source_order_plan_hash: str,
    environment: str,
    plan_created_date: str,
    intended_submit_date: str,
    target_session_date: str,
    items: Sequence[PendingOrderItem],
    planning_lineage_context: dict | None = None,
    submit_policy_context: dict | None = None,
) -> PendingOrderPlan:
    if not order_plan_id:
        raise ValueError("order_plan_id is required")
    if not source_order_plan_path:
        raise ValueError("source_order_plan_path is required")
    if not source_order_plan_hash:
        raise ValueError("source_order_plan_hash is required")
    item_tuple = tuple(items)
    policy_context = _policy_context_from_items(item_tuple)
    planning_context = dict(planning_lineage_context or _planning_lineage_context_from_items(item_tuple))
    submit_context = dict(submit_policy_context or _submit_policy_context_from_items(item_tuple))
    accepted_generation_context = _accepted_generation_context_from_items(item_tuple)
    safety_context = _safety_context_from_items(item_tuple, target_session_date=target_session_date)
    policy_version = str(policy_context.get("policy_version") or "")
    policy_source = str(policy_context.get("policy_source") or "")
    pending_policy_hash = _policy_hash(policy_context) if policy_context else ""
    planning_authority_version = str(planning_context.get("planning_authority_version") or "")
    planning_authority_source = str(planning_context.get("planning_authority_source") or "")
    planning_authority_hash = str(planning_context.get("planning_authority_hash") or "")
    submit_policy_version = str(submit_context.get("submit_policy_version") or "")
    submit_policy_source = str(submit_context.get("submit_policy_source") or "")
    submit_policy_hash = str(submit_context.get("submit_policy_hash") or "")
    return PendingOrderPlan(
        schema_version="1",
        pending_plan_id=f"pending-{order_plan_id}",
        state=PendingPlanState.PENDING_APPROVAL,
        environment=environment,
        created_at=plan_created_date,
        updated_at=plan_created_date,
        plan_created_date=plan_created_date,
        intended_submit_date=intended_submit_date,
        target_session_date=target_session_date,
        source_order_plan=PendingSourceOrderPlan(
            order_plan_id=order_plan_id,
            path=source_order_plan_path,
            artifact_hash=source_order_plan_hash,
        ),
        approval=None,
        approved_item_ids=(),
        items=item_tuple,
        submit_constraints=PendingSubmitConstraints(),
        consume=PendingConsumeInfo(),
        raw_request_saved=False,
        raw_response_saved=False,
        secret_saved=False,
        policy_context=policy_context or None,
        policy_version=policy_version,
        policy_source=policy_source,
        pending_policy_hash=pending_policy_hash,
        planning_lineage_context=planning_context or None,
        planning_authority_version=planning_authority_version,
        planning_authority_source=planning_authority_source,
        planning_authority_hash=planning_authority_hash,
        submit_policy_context=submit_context or None,
        submit_policy_version=submit_policy_version,
        submit_policy_source=submit_policy_source,
        submit_policy_hash=submit_policy_hash,
        accepted_generation_binding=accepted_generation_context or None,
        accepted_generation_id=str(accepted_generation_context.get("accepted_generation_id") or ""),
        accepted_generation_business_date=str(accepted_generation_context.get("accepted_generation_business_date") or ""),
        accepted_generation_binding_status=str(accepted_generation_context.get("generation_binding_status") or ""),
        safety_context=safety_context or None,
        safety_decision_id=str(safety_context.get("safety_decision_id") or ""),
        safety_policy_version=str(safety_context.get("safety_policy_version") or ""),
    )


def attach_approval_link(
    plan: PendingOrderPlan,
    *,
    approval_path: str,
    approval_hash: str,
    approval_status: str,
    approved_item_ids: Sequence[str],
    approval_expires_at: str,
    approved_order_conditions: dict | None = None,
    planning_submit_feasibility_current: RuntimeCurrentExposure | None = None,
    planning_submit_feasibility_policy: CapitalDeploymentPolicy | None = None,
) -> PendingOrderPlan:
    approved_tuple = tuple(approved_item_ids)
    item_ids = {item.pending_item_id for item in plan.items}
    missing = tuple(item_id for item_id in approved_tuple if item_id not in item_ids)
    if missing:
        raise ValueError(f"approved_item_ids not in pending items: {', '.join(missing)}")
    approved_items = tuple(item for item in plan.items if item.pending_item_id in approved_tuple)
    feasibility_payload = None
    if planning_submit_feasibility_current is not None and planning_submit_feasibility_policy is not None:
        policy_context = plan.policy_context if isinstance(plan.policy_context, Mapping) else {}
        position_count_authority = (
            position_count_authority_from_context(
                policy_context,
                business_date=plan.plan_created_date,
                runtime_mode=plan.environment,
                current_position_count=len(planning_submit_feasibility_current.positions),
                configured_legacy_max_positions=planning_submit_feasibility_policy.max_positions,
                consumer="planning_submit_feasibility_pre_approved_pending",
            )
            if _has_position_count_authority_context(policy_context)
            else None
        )
        cash_exposure_authority = (
            cash_exposure_authority_from_context(
                policy_context,
                business_date=plan.plan_created_date,
                runtime_mode=plan.environment,
                current_total_equity=planning_submit_feasibility_current.current_total_equity,
                active_deployment_capital=planning_submit_feasibility_current.active_deployment_capital,
                current_cash=planning_submit_feasibility_current.cash,
                current_market_value=planning_submit_feasibility_current.current_exposure,
                consumer="planning_submit_feasibility_pre_approved_pending",
            )
            if _has_cash_exposure_authority_context(policy_context)
            else None
        )
        feasibility = evaluate_planning_submit_feasibility(
            items=approved_items,
            policy=planning_submit_feasibility_policy,
            current=planning_submit_feasibility_current,
            authority_source="planning_submit_feasibility_pre_approved_pending",
            position_count_authority=position_count_authority,
            cash_exposure_authority=cash_exposure_authority,
            business_date=plan.plan_created_date,
            runtime_mode=plan.environment,
        )
        feasibility_payload = feasibility.evidence
        if not feasibility.passed:
            scope = _review_scope_for_submit_feasibility(feasibility_payload)
            feasibility_by_id = _feasibility_items_by_pending_id(feasibility_payload)
            return replace(
                plan,
                state=PendingPlanState.REVIEW_REQUIRED,
                updated_at=approval_expires_at,
                planning_submit_feasibility=feasibility_payload,
                approved_item_ids=(),
                buy_items_status=scope["buy_items_status"],
                sell_items_status=scope["sell_items_status"],
                plan_overall_status="REVIEW_REQUIRED",
                approved_buy_item_ids=(),
                approved_sell_item_ids=(),
                review_required_buy_item_ids=scope["review_required_buy_item_ids"],
                review_required_sell_item_ids=scope["review_required_sell_item_ids"],
                review_scope=scope["review_scope"],
                review_scope_source=scope["review_scope_source"],
                review_scope_reason=scope["review_scope_reason"],
                sell_continuation_allowed=scope["sell_continuation_allowed"],
                items=tuple(
                    _materialize_item_scoped_review_state(
                        item,
                        feasibility_by_id=feasibility_by_id,
                        scope=scope,
                    )
                    if item.pending_item_id in approved_tuple
                    else item
                    for item in plan.items
                ),
            )
    next_state = plan.state
    if approval_status == "APPROVED":
        transition = validate_pending_transition(
            plan.state,
            PendingPlanState.APPROVED,
            reason="approval link attached",
        )
        if not transition.allowed:
            raise ValueError(f"approval cannot move {plan.state.value} to APPROVED")
        next_state = PendingPlanState.APPROVED
    return replace(
        plan,
        state=next_state,
        updated_at=approval_expires_at,
        approval=PendingApprovalLink(
            approval_path=approval_path,
            approval_hash=approval_hash,
            approval_status=approval_status,
            approved_item_ids=approved_tuple,
            approval_expires_at=approval_expires_at,
            policy_version=plan.policy_version,
            policy_source=plan.policy_source,
            pending_policy_hash=plan.pending_policy_hash,
            planning_authority_version=plan.planning_authority_version,
            planning_authority_source=plan.planning_authority_source,
            planning_authority_hash=plan.planning_authority_hash,
            submit_policy_version=plan.submit_policy_version,
            submit_policy_source=plan.submit_policy_source,
            submit_policy_hash=plan.submit_policy_hash,
            accepted_generation_id=plan.accepted_generation_id,
            accepted_generation_business_date=plan.accepted_generation_business_date,
            accepted_generation_binding_status=plan.accepted_generation_binding_status,
            accepted_generation_binding=plan.accepted_generation_binding,
            safety_decision_id=plan.safety_decision_id,
            safety_policy_version=plan.safety_policy_version,
            approved_order_conditions=approved_order_conditions,
        ),
        approved_item_ids=approved_tuple,
        planning_submit_feasibility=feasibility_payload or plan.planning_submit_feasibility,
        buy_items_status=_side_status(plan.items, approved_tuple, "BUY"),
        sell_items_status=_side_status(plan.items, approved_tuple, "SELL"),
        plan_overall_status=next_state.value,
        approved_buy_item_ids=tuple(item.pending_item_id for item in plan.items if item.side.upper() == "BUY" and item.pending_item_id in approved_tuple),
        approved_sell_item_ids=tuple(item.pending_item_id for item in plan.items if item.side.upper() == "SELL" and item.pending_item_id in approved_tuple),
        review_required_buy_item_ids=(),
        review_required_sell_item_ids=(),
        review_scope="",
        review_scope_source="",
        review_scope_reason="",
        sell_continuation_allowed=False,
        items=tuple(
            replace(item, approved=item.pending_item_id in approved_tuple)
            for item in plan.items
        ),
    )


def _policy_context_from_items(items: tuple[PendingOrderItem, ...]) -> dict:
    for item in items:
        if item.policy_version or item.policy_source:
            return {
                "policy_version": item.policy_version,
                "policy_source": item.policy_source,
                "evaluation_capital": item.evaluation_capital,
                "max_positions": item.max_positions,
                "max_buy_order_amount": item.max_buy_order_amount,
                "max_sell_liquidation_amount": item.max_sell_liquidation_amount,
                "min_order_amount": item.min_order_amount,
                "buy_notional_policy": item.buy_notional_policy,
                "sell_liquidation_policy": item.sell_liquidation_policy,
                "manual_review_threshold": item.manual_review_threshold,
                **_authority_context_from_item(item),
            }
    return {}


def _authority_context_from_item(item: PendingOrderItem) -> dict:
    context = item.quantity_contract if isinstance(item.quantity_contract, dict) else {}
    payload: dict = {}
    if isinstance(context.get("position_count_authority"), dict):
        payload["position_count_authority"] = context["position_count_authority"]
    if isinstance(context.get("cash_exposure_authority"), dict):
        payload["cash_exposure_authority"] = context["cash_exposure_authority"]
    for field in (
        "strategy_requested_position_count",
        "selected_dynamic_position_count",
        "strategy_requested_cash_ratio",
        "selected_dynamic_cash_ratio",
        "strategy_requested_exposure_ratio",
        "selected_dynamic_exposure_ratio",
        "selected_runtime_exposure_limit",
        "cash_exposure_authority_winner",
        "cash_exposure_binding_constraint",
        "legacy_cash_config_used",
        "legacy_exposure_config_used",
        "cash_exposure_fallback_used",
    ):
        if field in context:
            payload[field] = context[field]
    return payload


def _has_position_count_authority_context(context: Mapping[str, object]) -> bool:
    if isinstance(context.get("position_count_authority"), Mapping):
        return True
    return any(
        field in context
        for field in (
            "strategy_requested_position_count",
            "selected_dynamic_position_count",
            "position_count_authority_winner",
            "position_count_binding_constraint",
        )
    )


def _has_cash_exposure_authority_context(context: Mapping[str, object]) -> bool:
    if isinstance(context.get("cash_exposure_authority"), Mapping):
        return True
    return any(
        field in context
        for field in (
            "strategy_requested_cash_ratio",
            "selected_dynamic_cash_ratio",
            "strategy_requested_exposure_ratio",
            "selected_dynamic_exposure_ratio",
            "selected_runtime_exposure_limit",
            "cash_exposure_authority_winner",
            "cash_exposure_binding_constraint",
        )
    )


def _review_scope_for_submit_feasibility(evidence: dict) -> dict:
    items = tuple(item for item in evidence.get("items") or () if isinstance(item, dict))
    blocked = tuple(item for item in items if str(item.get("status") or "") != "PASS")
    blocked_buy_ids = tuple(
        str(item.get("pending_item_id") or "")
        for item in blocked
        if str(item.get("side") or "").upper() == "BUY" and str(item.get("pending_item_id") or "")
    )
    blocked_sell_ids = tuple(
        str(item.get("pending_item_id") or "")
        for item in blocked
        if str(item.get("side") or "").upper() == "SELL" and str(item.get("pending_item_id") or "")
    )
    sell_present = any(str(item.get("side") or "").upper() == "SELL" for item in items)
    unknown_authority = any(
        str(item.get("violated_policy") or "").endswith("_missing")
        or not str(item.get("violated_policy") or "")
        or not str(item.get("violated_policy_source") or "")
        for item in blocked
    )
    buy_item_scoped = bool(blocked_buy_ids) and not blocked_sell_ids and not unknown_authority
    review_scope = "BUY_ITEM_SCOPED_REVIEW" if buy_item_scoped else "AUTHORITY_UNKNOWN_REVIEW"
    return {
        "buy_items_status": "REVIEW_REQUIRED" if blocked_buy_ids else "PASS",
        "sell_items_status": "REVIEW_REQUIRED" if blocked_sell_ids else ("PASS" if sell_present else "NOT_PRESENT"),
        "review_required_buy_item_ids": blocked_buy_ids,
        "review_required_sell_item_ids": blocked_sell_ids,
        "review_scope": review_scope,
        "review_scope_source": str(evidence.get("contract_id") or "planning_submit_feasibility"),
        "review_scope_reason": str(evidence.get("reason") or ""),
        "sell_continuation_allowed": buy_item_scoped,
    }


def _feasibility_items_by_pending_id(evidence: dict) -> dict[str, dict]:
    return {
        str(item.get("pending_item_id") or ""): dict(item)
        for item in evidence.get("items") or ()
        if isinstance(item, dict) and str(item.get("pending_item_id") or "")
    }


def _materialize_item_scoped_review_state(
    item: PendingOrderItem,
    *,
    feasibility_by_id: dict[str, dict],
    scope: dict,
) -> PendingOrderItem:
    feasibility = feasibility_by_id.get(item.pending_item_id, {})
    feasibility_status = str(feasibility.get("status") or "")
    review_required_ids = set(scope["review_required_buy_item_ids"]) | set(scope["review_required_sell_item_ids"])
    if item.pending_item_id in review_required_ids:
        review_reason = str(feasibility.get("reason") or scope["review_scope_reason"] or "planning_submit_feasibility_review_required")
        batch_submit_status = "ITEM_REVIEW_REQUIRED"
    else:
        review_reason = "batch_submit_blocked_by_item_scoped_review"
        batch_submit_status = "BLOCKED_BY_BATCH_REVIEW"
    return replace(
        item,
        approved=False,
        state="REVIEW_REQUIRED",
        feasibility_status=feasibility_status,
        batch_submit_status=batch_submit_status,
        item_review_reason=review_reason,
    )


def _side_status(items: tuple[PendingOrderItem, ...], approved_item_ids: tuple[str, ...], side: str) -> str:
    side_items = tuple(item for item in items if item.side.upper() == side)
    if not side_items:
        return "NOT_PRESENT"
    approved = {item_id for item_id in approved_item_ids}
    return "APPROVED" if all(item.pending_item_id in approved for item in side_items) else "PENDING_APPROVAL"


def _planning_lineage_context_from_items(items: tuple[PendingOrderItem, ...]) -> dict:
    for item in items:
        if item.planning_authority_version or item.planning_authority_source or item.planning_authority_hash:
            return {
                "planning_authority_version": item.planning_authority_version,
                "planning_authority_source": item.planning_authority_source,
                "planning_authority_hash": item.planning_authority_hash,
            }
        if item.policy_version or item.policy_source:
            return {
                "planning_authority_version": item.policy_version,
                "planning_authority_source": item.policy_source,
                "planning_authority_hash": "",
                "legacy_policy_field_used": True,
            }
    return {}


def _submit_policy_context_from_items(items: tuple[PendingOrderItem, ...]) -> dict:
    for item in items:
        if item.submit_policy_version or item.submit_policy_source or item.submit_policy_hash:
            return {
                "submit_policy_version": item.submit_policy_version,
                "submit_policy_source": item.submit_policy_source,
                "submit_policy_hash": item.submit_policy_hash,
            }
    return {}


def _accepted_generation_context_from_items(items: tuple[PendingOrderItem, ...]) -> dict:
    for item in items:
        if item.accepted_generation_id or item.accepted_generation_binding:
            binding = dict(item.accepted_generation_binding or {})
            binding["accepted_generation_id"] = item.accepted_generation_id or str(binding.get("accepted_generation_id") or "")
            binding["accepted_generation_business_date"] = (
                item.accepted_generation_business_date
                or str(binding.get("accepted_generation_business_date") or binding.get("selected_business_date") or "")
            )
            binding["generation_binding_status"] = (
                item.accepted_generation_binding_status
                or str(binding.get("generation_binding_status") or "")
            )
            return binding
    return {}


def _safety_context_from_items(items: tuple[PendingOrderItem, ...], *, target_session_date: str) -> dict:
    for item in items:
        if item.safety_decision_id or item.safety_policy_version:
            historical_context = materialize_historical_pending_safety_context(
                safety_decision_id=item.safety_decision_id,
                safety_policy_version=item.safety_policy_version,
                safety_source=item.safety_source,
                safety_decision=item.safety_decision,
                safety_reason=item.safety_reason,
                safety_business_date=target_session_date,
                runtime_test_run_id=item.runtime_test_run_id,
                runtime_test_profile_id=item.runtime_test_profile_id,
                runtime_test_evidence_root=item.runtime_test_evidence_root,
            )
            if historical_context:
                return historical_context
            return {
                "safety_decision_id": item.safety_decision_id,
                "safety_policy_version": item.safety_policy_version,
                "safety_source": item.safety_source,
                "safety_decision": item.safety_decision,
                "safety_reason": item.safety_reason,
                "safety_business_date": target_session_date,
                "temporal_authority_business_date": target_session_date,
            }
    return {}


def _policy_hash(policy_context: dict) -> str:
    return capital_deployment_policy_hash_from_context(policy_context)
