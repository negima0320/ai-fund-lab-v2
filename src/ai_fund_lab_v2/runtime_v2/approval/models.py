"""Approval models for Runtime v2."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


@dataclass(frozen=True)
class ApprovalRequest:
    approval_request_id: str
    pending_plan_id: str
    order_plan_id: str
    environment: str
    business_date: str
    target_session_date: str
    requested_item_ids: tuple[str, ...]
    created_at: str
    expires_at: str
    review_required: bool


@dataclass(frozen=True)
class ApprovalDecision:
    status: ApprovalStatus
    approved_item_ids: tuple[str, ...]
    rejected_item_ids: tuple[str, ...]
    reason: str
    operator: str
    decided_at: str


@dataclass(frozen=True)
class ApprovalArtifact:
    approval_id: str
    approval_request_id: str
    pending_plan_id: str
    order_plan_id: str
    status: ApprovalStatus
    approved_item_ids: tuple[str, ...]
    rejected_item_ids: tuple[str, ...]
    approval_hash: str
    approved_at: str
    expires_at: str
    review_required: bool
    reason: str

