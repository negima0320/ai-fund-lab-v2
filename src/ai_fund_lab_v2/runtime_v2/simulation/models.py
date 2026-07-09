"""Models for the Runtime v2 simulation harness."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SimulationBrokerPosition:
    symbol: str
    quantity: float
    average_price: float
    market_value: float


@dataclass(frozen=True)
class SimulationBrokerState:
    cash: float
    buying_power: float
    positions: tuple[SimulationBrokerPosition, ...] = ()


@dataclass(frozen=True)
class SimulationOrderInstruction:
    business_date: str
    symbol: str
    side: str
    quantity: float
    price: float
    order_type: str = "MARKET"
    pending_item_id: str = ""
    fill_policy: str = "FULL_FILL"


@dataclass(frozen=True)
class SimulationSubmitResult:
    status: str
    submitted: bool
    blocked: bool
    review_required: bool
    reason: str
    order_ref: str = ""
    execution_ref: str = ""
    realized_pnl: float | None = None
    post_send_unknown: bool = False


@dataclass(frozen=True)
class SimulationDayResult:
    business_date: str
    order_side: str
    submit_status: str
    blocked: bool
    review_required: bool
    pending_state: str
    fill_classification: str
    ledger_order_count: int
    ledger_execution_count: int
    ledger_position_count: int
    ledger_cash_count: int
    asset_cash: float | None
    asset_buying_power: float | None
    asset_positions: tuple[SimulationBrokerPosition, ...]
    realized_pnl: float | None
    reconciliation_findings: int
    report_sections: int
    notification_payload_created: bool
    audit_findings: int


@dataclass(frozen=True)
class SimulationReplayResult:
    status: str
    mode: str
    environment: str
    day_results: tuple[SimulationDayResult, ...]
    ledger_order_count: int
    ledger_execution_count: int
    final_cash: float | None
    final_positions: tuple[SimulationBrokerPosition, ...]
    production_order_executed: bool = False
    broker_api_called: bool = False
    notification_send_executed: bool = False
