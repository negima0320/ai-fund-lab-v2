"""Models for Runtime v2 Pending Order Plan Runtime."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping


class PendingPlanState(str, Enum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    SUBMITTING = "SUBMITTING"
    SUBMITTED = "SUBMITTED"
    CONSUMED = "CONSUMED"
    EXPIRED = "EXPIRED"
    BLOCKED = "BLOCKED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    POST_SEND_UNKNOWN = "POST_SEND_UNKNOWN"


@dataclass(frozen=True)
class PendingSourceOrderPlan:
    order_plan_id: str
    path: str
    artifact_hash: str


@dataclass(frozen=True)
class PendingApprovalLink:
    approval_path: str
    approval_hash: str
    approval_status: str
    approved_item_ids: tuple[str, ...]
    approval_expires_at: str


@dataclass(frozen=True)
class PendingConsumeInfo:
    consumed: bool = False
    consume_reason: str = ""
    consumed_at: str = ""
    submitted_order_ids: tuple[str, ...] = ()
    ledger_order_record_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class PendingSubmitConstraints:
    expires_at: str = ""
    allow_post_send_unknown_resubmit: bool = False


@dataclass(frozen=True)
class PendingOrderItem:
    pending_item_id: str
    symbol: str
    side: str
    quantity: float
    order_type: str
    estimated_price: float
    estimated_amount: float
    approved: bool
    state: str


@dataclass(frozen=True)
class PendingOrderPlan:
    schema_version: str
    pending_plan_id: str
    state: PendingPlanState
    environment: str
    created_at: str
    updated_at: str
    plan_created_date: str
    intended_submit_date: str
    target_session_date: str
    source_order_plan: PendingSourceOrderPlan
    approval: PendingApprovalLink | None
    approved_item_ids: tuple[str, ...]
    items: tuple[PendingOrderItem, ...]
    submit_constraints: PendingSubmitConstraints
    consume: PendingConsumeInfo
    raw_request_saved: bool = False
    raw_response_saved: bool = False
    secret_saved: bool = False


@dataclass(frozen=True)
class PendingOrderPlanReadResult:
    path: Path
    exists: bool
    valid: bool
    classification: str
    plan: PendingOrderPlan | None
    payload: Mapping[str, Any] | None
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

