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
    )

