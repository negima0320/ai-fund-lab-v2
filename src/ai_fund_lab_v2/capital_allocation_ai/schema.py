from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class CapitalAllocationAction(str, Enum):
    BUY = "BUY"
    HOLD = "HOLD"
    NO_ACTION = "NO_ACTION"
    REPLACE_SELL = "REPLACE_SELL"
    REPLACE_BUY = "REPLACE_BUY"
    EMERGENCY_EXIT = "EMERGENCY_EXIT"
    DEFENSIVE_REVIEW = "DEFENSIVE_REVIEW"


@dataclass(frozen=True)
class Phase7AConfig:
    initial_total_assets: float = 1_000_000.0
    cash_buffer_ratio: float = 0.05
    max_position_weight: float = 0.20
    min_position_value: float = 50_000.0
    max_position_value: float | None = None
    minimum_holding_days: int = 5
    replacement_rank_degradation_threshold: int = 20
    replacement_edge_margin: float = 0.02
    confirmation_days: int = 2
    emergency_exit_pct: float = -0.15
    primary_buy_rank_cutoff: int = 3
    watch_rank_cutoff: int = 5
    high_downside_risk_threshold: float = 0.70


@dataclass(frozen=True)
class PortfolioSnapshot:
    target_date: str
    total_assets: float
    cash: float


@dataclass(frozen=True)
class DecisionRecord:
    target_date: str
    code: str
    action: str
    current_position_value: float
    target_position_value: float
    current_weight: float
    target_weight: float
    buy_amount: float
    sell_amount: float
    cash_before_action: float
    cash_after_action: float
    expected_edge_score: float
    buy_rank: int | None
    opportunity_rank: int | None
    downside_risk_score: float
    risk_guard_status: str
    position_signal: str
    holding_days: int
    unrealized_return: float
    replacement_reason: str
    defensive_reason: str
    emergency_reason: str
    validation_notes: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_date": self.target_date,
            "code": self.code,
            "action": self.action,
            "current_position_value": self.current_position_value,
            "target_position_value": self.target_position_value,
            "current_weight": self.current_weight,
            "target_weight": self.target_weight,
            "buy_amount": self.buy_amount,
            "sell_amount": self.sell_amount,
            "cash_before_action": self.cash_before_action,
            "cash_after_action": self.cash_after_action,
            "expected_edge_score": self.expected_edge_score,
            "buy_rank": self.buy_rank,
            "opportunity_rank": self.opportunity_rank,
            "downside_risk_score": self.downside_risk_score,
            "risk_guard_status": self.risk_guard_status,
            "position_signal": self.position_signal,
            "holding_days": self.holding_days,
            "unrealized_return": self.unrealized_return,
            "replacement_reason": self.replacement_reason,
            "defensive_reason": self.defensive_reason,
            "emergency_reason": self.emergency_reason,
            "validation_notes": self.validation_notes,
        }


DECISION_COLUMNS = tuple(DecisionRecord.__dataclass_fields__.keys())


REQUIRED_AUDIT_FLAGS = (
    "broker_api_executed",
    "paper_trading_executed",
    "order_executed",
    "live_order_executed",
    "tachibana_api_called",
    "fixed_take_profit_enabled",
    "phase6_single_exit_auto_sell_enabled",
    "emergency_exit_enabled",
    "replacement_requires_minimum_holding_days",
    "replacement_requires_edge_margin",
    "replacement_requires_confirmation_days",
    "replacement_same_time_live_execution_enabled",
    "replacement_requires_sell_fill_before_buy",
    "cash_buffer_applied",
    "max_position_weight_applied",
)
