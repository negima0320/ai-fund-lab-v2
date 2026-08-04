"""Approval models for Runtime v2."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


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
    policy_version: str = ""
    policy_source: str = ""
    pending_policy_hash: str = ""
    planning_authority_version: str = ""
    planning_authority_source: str = ""
    planning_authority_hash: str = ""
    submit_policy_version: str = ""
    submit_policy_source: str = ""
    submit_policy_hash: str = ""
    safety_decision_id: str = ""
    safety_policy_version: str = ""


@dataclass(frozen=True)
class ApprovalDecision:
    status: ApprovalStatus
    approved_item_ids: tuple[str, ...]
    rejected_item_ids: tuple[str, ...]
    reason: str
    operator: str
    decided_at: str
    approved_order_conditions: dict[str, Any] | None = None


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
    policy_version: str = ""
    policy_source: str = ""
    pending_policy_hash: str = ""
    planning_authority_version: str = ""
    planning_authority_source: str = ""
    planning_authority_hash: str = ""
    submit_policy_version: str = ""
    submit_policy_source: str = ""
    submit_policy_hash: str = ""
    safety_decision_id: str = ""
    safety_policy_version: str = ""
    approved_order_conditions: dict[str, Any] | None = None
