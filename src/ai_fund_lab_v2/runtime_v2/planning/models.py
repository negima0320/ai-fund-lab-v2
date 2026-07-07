"""Planning models for Runtime v2."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ai_fund_lab_v2.runtime_v2.asset.models import CurrentAssetState


class PlanningDecisionStatus(str, Enum):
    CREATED = "CREATED"
    BLOCKED = "BLOCKED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    NO_ACTION = "NO_ACTION"


@dataclass(frozen=True)
class AIPlanningSignal:
    signal_id: str
    symbol: str
    side: str
    rank: int
    score: float
    reason: str
    source_ai: str


@dataclass(frozen=True)
class CapitalAllocationSignal:
    allocation_id: str
    symbol: str
    side: str
    allocated_amount: float
    max_amount: float
    cash_required: float
    reason: str


@dataclass(frozen=True)
class SafetySignal:
    safety_id: str
    symbol: str
    side: str
    allowed: bool
    review_required: bool
    blocked: bool
    reason: str


@dataclass(frozen=True)
class PlanningInput:
    mode: str
    environment: str
    business_date: str
    target_session_date: str
    asset_state: CurrentAssetState | None
    ai_signals: tuple[AIPlanningSignal, ...]
    capital_allocations: tuple[CapitalAllocationSignal, ...]
    safety_signals: tuple[SafetySignal, ...]


@dataclass(frozen=True)
class OrderPlanItem:
    order_plan_item_id: str
    symbol: str
    side: str
    quantity: float
    estimated_price: float
    estimated_amount: float
    source_signal_id: str
    allocation_id: str
    safety_id: str
    status: PlanningDecisionStatus
    review_required: bool
    blocked: bool
    reason: str


@dataclass(frozen=True)
class OrderPlan:
    schema_version: str
    order_plan_id: str
    environment: str
    business_date: str
    target_session_date: str
    status: PlanningDecisionStatus
    items: tuple[OrderPlanItem, ...]
    source_ai_signal_ids: tuple[str, ...]
    source_allocation_ids: tuple[str, ...]
    source_safety_ids: tuple[str, ...]
    asset_state_id: str
    created_at: str
    review_required: bool
    blocked: bool


@dataclass(frozen=True)
class DailyPlan:
    daily_plan_id: str
    environment: str
    business_date: str
    target_session_date: str
    order_plan_id: str
    status: PlanningDecisionStatus
    summary: str
    created_at: str


@dataclass(frozen=True)
class PlanningResult:
    daily_plan: DailyPlan
    order_plan: OrderPlan
    status: PlanningDecisionStatus
    review_required: bool
    blocked: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

