"""Models for Runtime v2 Pending Order Plan Runtime."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping


class PendingPlanState(str, Enum):
    CREATED = "CREATED"
    PENDING_REVIEW = "PENDING_REVIEW"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUBMITTING = "SUBMITTING"
    SUBMITTED = "SUBMITTED"
    CONSUMED = "CONSUMED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    SUPERSEDED = "SUPERSEDED"
    BLOCKED = "BLOCKED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    POST_SEND_UNKNOWN = "POST_SEND_UNKNOWN"
    EMPTY = "EMPTY"


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
    listed_info: dict[str, Any] | None = None
    price_source: str = ""
    price_as_of: str = ""
    price_confidence: str = ""
    price_required: bool = True
    capital_allocation_amount: float = 0.0
    policy_version: str = ""
    policy_source: str = ""
    planning_authority_version: str = ""
    planning_authority_source: str = ""
    planning_authority_hash: str = ""
    submit_policy_version: str = ""
    submit_policy_source: str = ""
    submit_policy_hash: str = ""
    evaluation_capital: float | None = None
    target_investment_ratio: float | None = None
    cash_buffer: float | None = None
    max_exposure: float | None = None
    max_position_weight: float | None = None
    max_positions: int | None = None
    max_buy_order_amount: float | None = None
    max_sell_liquidation_amount: float | None = None
    min_order_amount: float | None = None
    buy_notional_policy: str = ""
    sell_liquidation_policy: str = ""
    manual_review_threshold: dict[str, Any] | None = None
    sizing_policy_reason: str = ""
    safety_decision_id: str = ""
    safety_policy_version: str = ""
    safety_source: str = ""
    safety_decision: str = ""
    safety_reason: str = ""
    safety_authority: str = ""
    safety_business_date: str = ""
    temporal_authority_business_date: str = ""
    runtime_test_run_id: str = ""
    runtime_test_profile_id: str = ""
    runtime_test_evidence_root: str = ""
    quantity_contract: dict[str, Any] | None = None
    source_decision_type: str = ""
    source_pm_decision_id: str = ""
    source_pm_business_date: str = ""
    source_position_symbol: str = ""
    add_candidate_signal: bool = False
    capital_allocation_status: str = ""
    capital_allocation_reason: str = ""
    requested_add_notional: float | None = None
    approved_add_notional: float | None = None
    rejected_reason: str = ""


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
    feature_date_contract: dict[str, Any] | None = None
    policy_context: dict[str, Any] | None = None
    policy_version: str = ""
    policy_source: str = ""
    pending_policy_hash: str = ""
    planning_lineage_context: dict[str, Any] | None = None
    planning_authority_version: str = ""
    planning_authority_source: str = ""
    planning_authority_hash: str = ""
    submit_policy_context: dict[str, Any] | None = None
    submit_policy_version: str = ""
    submit_policy_source: str = ""
    submit_policy_hash: str = ""
    safety_context: dict[str, Any] | None = None
    safety_decision_id: str = ""
    safety_policy_version: str = ""


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
