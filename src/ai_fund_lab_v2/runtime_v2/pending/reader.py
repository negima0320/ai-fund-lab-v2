"""Pending Order Plan reader for fixed Runtime v2 current path."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from ai_fund_lab_v2.runtime_v2.pending.models import (
    PendingApprovalLink,
    PendingConsumeInfo,
    PendingOrderItem,
    PendingOrderPlan,
    PendingOrderPlanReadResult,
    PendingPlanState,
    PendingSourceOrderPlan,
    PendingSubmitConstraints,
)
from ai_fund_lab_v2.runtime_v2.storage.path_resolver import resolve_current_path


def read_pending_order_plan(
    *,
    mode: str,
    environment: str,
    base_dir: Path | None = None,
) -> PendingOrderPlanReadResult:
    relative_path = resolve_current_path(
        mode=mode,
        environment=environment,
        object_type="pending_order_plan",
    )
    path = (base_dir / relative_path) if base_dir is not None else relative_path
    if not path.exists():
        return PendingOrderPlanReadResult(
            path=path,
            exists=False,
            valid=False,
            classification="MISSING",
            plan=None,
            payload=None,
            errors=("pending order plan missing",),
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return PendingOrderPlanReadResult(
            path=path,
            exists=True,
            valid=False,
            classification="INVALID",
            plan=None,
            payload=None,
            errors=(f"json parse error: {exc.msg}",),
        )
    if not isinstance(payload, Mapping):
        return PendingOrderPlanReadResult(
            path=path,
            exists=True,
            valid=False,
            classification="INVALID",
            plan=None,
            payload=None,
            errors=("pending payload must be an object",),
        )
    if str(payload.get("status") or payload.get("state") or "").upper() == "EMPTY" and not bool(
        payload.get("active_pending", True)
    ):
        return PendingOrderPlanReadResult(
            path=path,
            exists=True,
            valid=True,
            classification="EMPTY",
            plan=None,
            payload=payload,
        )
    try:
        plan = pending_order_plan_from_payload(payload)
    except (KeyError, TypeError, ValueError) as exc:
        return PendingOrderPlanReadResult(
            path=path,
            exists=True,
            valid=False,
            classification="INVALID",
            plan=None,
            payload=payload,
            errors=(str(exc),),
        )
    if plan.environment != environment:
        return PendingOrderPlanReadResult(
            path=path,
            exists=True,
            valid=False,
            classification="UNKNOWN",
            plan=plan,
            payload=payload,
            errors=("environment mismatch",),
        )
    return PendingOrderPlanReadResult(
        path=path,
        exists=True,
        valid=True,
        classification="VALID",
        plan=plan,
        payload=payload,
    )


def read_pending_order_plan_path(*, path: Path, environment: str) -> PendingOrderPlanReadResult:
    if not path.exists():
        return PendingOrderPlanReadResult(
            path=path,
            exists=False,
            valid=False,
            classification="MISSING",
            plan=None,
            payload=None,
            errors=("pending order plan missing",),
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return PendingOrderPlanReadResult(
            path=path,
            exists=True,
            valid=False,
            classification="INVALID",
            plan=None,
            payload=None,
            errors=(f"json parse error: {exc.msg}",),
        )
    if not isinstance(payload, Mapping):
        return PendingOrderPlanReadResult(
            path=path,
            exists=True,
            valid=False,
            classification="INVALID",
            plan=None,
            payload=None,
            errors=("pending payload must be an object",),
        )
    if str(payload.get("status") or payload.get("state") or "").upper() == "EMPTY" and not bool(
        payload.get("active_pending", True)
    ):
        return PendingOrderPlanReadResult(
            path=path,
            exists=True,
            valid=True,
            classification="EMPTY",
            plan=None,
            payload=payload,
        )
    try:
        plan = pending_order_plan_from_payload(payload)
    except (KeyError, TypeError, ValueError) as exc:
        return PendingOrderPlanReadResult(
            path=path,
            exists=True,
            valid=False,
            classification="INVALID",
            plan=None,
            payload=payload,
            errors=(str(exc),),
        )
    if plan.environment != environment:
        return PendingOrderPlanReadResult(
            path=path,
            exists=True,
            valid=False,
            classification="UNKNOWN",
            plan=plan,
            payload=payload,
            errors=("environment mismatch",),
        )
    return PendingOrderPlanReadResult(
        path=path,
        exists=True,
        valid=True,
        classification="VALID",
        plan=plan,
        payload=payload,
    )


def pending_order_plan_from_payload(payload: Mapping[str, Any]) -> PendingOrderPlan:
    required = (
        "schema_version",
        "pending_plan_id",
        "state",
        "environment",
        "created_at",
        "updated_at",
        "plan_created_date",
        "intended_submit_date",
        "target_session_date",
        "source_order_plan",
        "approved_item_ids",
        "items",
        "submit_constraints",
        "consume",
        "raw_request_saved",
        "raw_response_saved",
        "secret_saved",
    )
    missing = [field for field in required if field not in payload]
    if missing:
        raise ValueError(f"missing required fields: {', '.join(missing)}")
    source = payload["source_order_plan"]
    approval = payload.get("approval")
    constraints = payload["submit_constraints"]
    consume = payload["consume"]
    return PendingOrderPlan(
        schema_version=str(payload["schema_version"]),
        pending_plan_id=str(payload["pending_plan_id"]),
        state=PendingPlanState(payload["state"]),
        environment=str(payload["environment"]),
        created_at=str(payload["created_at"]),
        updated_at=str(payload["updated_at"]),
        plan_created_date=str(payload["plan_created_date"]),
        intended_submit_date=str(payload["intended_submit_date"]),
        target_session_date=str(payload["target_session_date"]),
        source_order_plan=PendingSourceOrderPlan(
            order_plan_id=str(source["order_plan_id"]),
            path=str(source["path"]),
            artifact_hash=str(source["artifact_hash"]),
        ),
        approval=None
        if approval is None
        else PendingApprovalLink(
            approval_path=str(approval["approval_path"]),
            approval_hash=str(approval["approval_hash"]),
            approval_status=str(approval["approval_status"]),
            approved_item_ids=tuple(approval["approved_item_ids"]),
            approval_expires_at=str(approval["approval_expires_at"]),
            policy_version=str(approval.get("policy_version") or ""),
            policy_source=str(approval.get("policy_source") or ""),
            pending_policy_hash=str(approval.get("pending_policy_hash") or ""),
            planning_authority_version=str(approval.get("planning_authority_version") or ""),
            planning_authority_source=str(approval.get("planning_authority_source") or ""),
            planning_authority_hash=str(approval.get("planning_authority_hash") or ""),
            submit_policy_version=str(approval.get("submit_policy_version") or ""),
            submit_policy_source=str(approval.get("submit_policy_source") or ""),
            submit_policy_hash=str(approval.get("submit_policy_hash") or ""),
            accepted_generation_id=str(approval.get("accepted_generation_id") or ""),
            accepted_generation_business_date=str(approval.get("accepted_generation_business_date") or ""),
            accepted_generation_binding_status=str(approval.get("accepted_generation_binding_status") or ""),
            accepted_generation_binding=(
                dict(approval["accepted_generation_binding"])
                if isinstance(approval.get("accepted_generation_binding"), Mapping)
                else None
            ),
            safety_decision_id=str(approval.get("safety_decision_id") or ""),
            safety_policy_version=str(approval.get("safety_policy_version") or ""),
            approved_order_conditions=(
                dict(approval["approved_order_conditions"])
                if isinstance(approval.get("approved_order_conditions"), Mapping)
                else None
            ),
        ),
        approved_item_ids=tuple(payload["approved_item_ids"]),
        items=tuple(
            PendingOrderItem(
                pending_item_id=str(item["pending_item_id"]),
                symbol=str(item["symbol"]),
                side=str(item["side"]),
                quantity=float(item["quantity"]),
                order_type=str(item["order_type"]),
                estimated_price=float(item["estimated_price"]),
                estimated_amount=float(item["estimated_amount"]),
                approved=bool(item["approved"]),
                state=str(item["state"]),
                feasibility_status=str(item.get("feasibility_status") or ""),
                batch_submit_status=str(item.get("batch_submit_status") or ""),
                item_review_reason=str(item.get("item_review_reason") or ""),
                listed_info=dict(item["listed_info"]) if item.get("listed_info") is not None else None,
                price_source=str(item.get("price_source") or ""),
                price_as_of=str(item.get("price_as_of") or ""),
                price_confidence=str(item.get("price_confidence") or ""),
                price_required=bool(item.get("price_required", True)),
                capital_allocation_amount=float(item.get("capital_allocation_amount") or item["estimated_amount"]),
                policy_version=str(item.get("policy_version") or ""),
                policy_source=str(item.get("policy_source") or ""),
                planning_authority_version=str(item.get("planning_authority_version") or ""),
                planning_authority_source=str(item.get("planning_authority_source") or ""),
                planning_authority_hash=str(item.get("planning_authority_hash") or ""),
                submit_policy_version=str(item.get("submit_policy_version") or ""),
                submit_policy_source=str(item.get("submit_policy_source") or ""),
                submit_policy_hash=str(item.get("submit_policy_hash") or ""),
                accepted_generation_id=str(item.get("accepted_generation_id") or ""),
                accepted_generation_business_date=str(item.get("accepted_generation_business_date") or ""),
                accepted_generation_binding_status=str(item.get("accepted_generation_binding_status") or ""),
                accepted_generation_binding=(
                    dict(item["accepted_generation_binding"])
                    if isinstance(item.get("accepted_generation_binding"), Mapping)
                    else None
                ),
                evaluation_capital=_optional_float(item.get("evaluation_capital")),
                target_investment_ratio=_optional_float(item.get("target_investment_ratio")),
                cash_buffer=_optional_float(item.get("cash_buffer")),
                max_exposure=_optional_float(item.get("max_exposure")),
                max_positions=_optional_int(item.get("max_positions")),
                max_buy_order_amount=_optional_float(item.get("max_buy_order_amount")),
                max_sell_liquidation_amount=_optional_float(item.get("max_sell_liquidation_amount")),
                min_order_amount=_optional_float(item.get("min_order_amount")),
                buy_notional_policy=str(item.get("buy_notional_policy") or ""),
                sell_liquidation_policy=str(item.get("sell_liquidation_policy") or ""),
                manual_review_threshold=(
                    dict(item["manual_review_threshold"])
                    if isinstance(item.get("manual_review_threshold"), Mapping)
                    else None
                ),
                sizing_policy_reason=str(item.get("sizing_policy_reason") or ""),
                safety_decision_id=str(item.get("safety_decision_id") or ""),
                safety_policy_version=str(item.get("safety_policy_version") or ""),
                safety_source=str(item.get("safety_source") or ""),
                safety_decision=str(item.get("safety_decision") or ""),
                safety_reason=str(item.get("safety_reason") or ""),
                safety_authority=str(item.get("safety_authority") or ""),
                safety_business_date=str(item.get("safety_business_date") or ""),
                temporal_authority_business_date=str(item.get("temporal_authority_business_date") or ""),
                runtime_test_run_id=str(item.get("runtime_test_run_id") or ""),
                runtime_test_profile_id=str(item.get("runtime_test_profile_id") or ""),
                runtime_test_evidence_root=str(item.get("runtime_test_evidence_root") or ""),
                quantity_contract=(
                    dict(item["quantity_contract"])
                    if isinstance(item.get("quantity_contract"), Mapping)
                    else None
                ),
                source_decision_type=str(item.get("source_decision_type") or ""),
                source_pm_decision_id=str(item.get("source_pm_decision_id") or ""),
                source_pm_business_date=str(item.get("source_pm_business_date") or ""),
                source_position_symbol=str(item.get("source_position_symbol") or ""),
                add_candidate_signal=bool(item.get("add_candidate_signal")),
                capital_allocation_status=str(item.get("capital_allocation_status") or ""),
                capital_allocation_reason=str(item.get("capital_allocation_reason") or ""),
                requested_add_notional=_optional_float(item.get("requested_add_notional")),
                approved_add_notional=_optional_float(item.get("approved_add_notional")),
                rejected_reason=str(item.get("rejected_reason") or ""),
            )
            for item in payload["items"]
        ),
        submit_constraints=PendingSubmitConstraints(
            expires_at=str(constraints.get("expires_at", "")),
            allow_post_send_unknown_resubmit=bool(
                constraints.get("allow_post_send_unknown_resubmit", False)
            ),
        ),
        consume=PendingConsumeInfo(
            consumed=bool(consume.get("consumed", False)),
            consume_reason=str(consume.get("consume_reason", "")),
            consumed_at=str(consume.get("consumed_at", "")),
            submitted_order_ids=tuple(consume.get("submitted_order_ids", ())),
            ledger_order_record_ids=tuple(consume.get("ledger_order_record_ids", ())),
        ),
        raw_request_saved=bool(payload["raw_request_saved"]),
        raw_response_saved=bool(payload["raw_response_saved"]),
        secret_saved=bool(payload["secret_saved"]),
        feature_date_contract=dict(payload["feature_date_contract"]) if payload.get("feature_date_contract") else None,
        policy_context=dict(payload["policy_context"]) if payload.get("policy_context") else None,
        policy_version=str(payload.get("policy_version") or ""),
        policy_source=str(payload.get("policy_source") or ""),
        pending_policy_hash=str(payload.get("pending_policy_hash") or ""),
        planning_lineage_context=dict(payload["planning_lineage_context"]) if payload.get("planning_lineage_context") else None,
        planning_authority_version=str(payload.get("planning_authority_version") or ""),
        planning_authority_source=str(payload.get("planning_authority_source") or ""),
        planning_authority_hash=str(payload.get("planning_authority_hash") or ""),
        submit_policy_context=dict(payload["submit_policy_context"]) if payload.get("submit_policy_context") else None,
        submit_policy_version=str(payload.get("submit_policy_version") or ""),
        submit_policy_source=str(payload.get("submit_policy_source") or ""),
        submit_policy_hash=str(payload.get("submit_policy_hash") or ""),
        accepted_generation_id=str(payload.get("accepted_generation_id") or ""),
        accepted_generation_business_date=str(payload.get("accepted_generation_business_date") or ""),
        accepted_generation_binding_status=str(payload.get("accepted_generation_binding_status") or ""),
        accepted_generation_binding=(
            dict(payload["accepted_generation_binding"])
            if isinstance(payload.get("accepted_generation_binding"), Mapping)
            else None
        ),
        safety_context=dict(payload["safety_context"]) if payload.get("safety_context") else None,
        safety_decision_id=str(payload.get("safety_decision_id") or ""),
        safety_policy_version=str(payload.get("safety_policy_version") or ""),
        planning_submit_feasibility=(
            dict(payload["planning_submit_feasibility"])
            if isinstance(payload.get("planning_submit_feasibility"), Mapping)
            else None
        ),
        buy_items_status=str(payload.get("buy_items_status") or ""),
        sell_items_status=str(payload.get("sell_items_status") or ""),
        plan_overall_status=str(payload.get("plan_overall_status") or ""),
        approved_buy_item_ids=tuple(payload.get("approved_buy_item_ids") or ()),
        approved_sell_item_ids=tuple(payload.get("approved_sell_item_ids") or ()),
        review_required_buy_item_ids=tuple(payload.get("review_required_buy_item_ids") or ()),
        review_required_sell_item_ids=tuple(payload.get("review_required_sell_item_ids") or ()),
        review_scope=str(payload.get("review_scope") or ""),
        review_scope_source=str(payload.get("review_scope_source") or ""),
        review_scope_reason=str(payload.get("review_scope_reason") or ""),
        sell_continuation_allowed=bool(payload.get("sell_continuation_allowed")),
    )


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)
