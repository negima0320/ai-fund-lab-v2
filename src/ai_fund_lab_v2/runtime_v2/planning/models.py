"""Planning models for Runtime v2."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

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
    estimated_price: float = 0.0
    price_source: str = ""
    price_as_of: str = ""
    price_confidence: str = ""
    price_required: bool = True
    policy_version: str = ""
    policy_source: str = ""
    sizing_policy_reason: str = ""
    policy_context: dict[str, Any] | None = None


@dataclass(frozen=True)
class RuntimeSafetyContext:
    safety_decision_id: str
    safety_policy_version: str
    safety_source: str
    safety_decision: str
    safety_reason: str
    review_required: bool
    block_buy: bool
    block_sell: bool
    block_submit: bool
    halt_runtime: bool
    emergency_stop: bool
    generated_at: str
    expires_at: str
    source: str = "runtime_safety"


@dataclass(frozen=True)
class PlanningInput:
    mode: str
    environment: str
    business_date: str
    target_session_date: str
    asset_state: CurrentAssetState | None
    ai_signals: tuple[AIPlanningSignal, ...]
    capital_allocations: tuple[CapitalAllocationSignal, ...]
    runtime_safety: RuntimeSafetyContext


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
    safety_decision_id: str
    safety_policy_version: str
    safety_source: str
    safety_decision: str
    safety_reason: str
    status: PlanningDecisionStatus
    review_required: bool
    blocked: bool
    reason: str
    price_source: str = ""
    price_as_of: str = ""
    price_confidence: str = ""
    price_required: bool = True
    capital_allocation_amount: float = 0.0
    policy_version: str = ""
    policy_source: str = ""
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
    safety_decision_id: str
    safety_policy_version: str
    safety_source: str
    safety_decision: str
    safety_reason: str
    asset_state_id: str
    created_at: str
    review_required: bool
    blocked: bool
    policy_context: dict[str, Any] | None = None


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
