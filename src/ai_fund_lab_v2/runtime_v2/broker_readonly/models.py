"""Broker ReadOnly snapshot models for Runtime v2."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BrokerSnapshotBase:
    snapshot_id: str
    schema_version: str
    environment: str
    source: str
    as_of: str
    broker_ref_hash: str
    review_required: bool
    production_equivalent: bool


@dataclass(frozen=True)
class BrokerOrderSnapshot(BrokerSnapshotBase):
    order_ref_hash: str
    pending_plan_id: str
    pending_item_id: str
    symbol: str
    side: str
    quantity: float
    order_status: str
    filled_quantity: float
    remaining_quantity: float
    accepted_at: str
    updated_at: str
    source_decision_id: str = ""
    source_decision_type: str = ""
    source_pm_decision_id: str = ""
    order_plan_item_id: str = ""
    position_campaign_id: str = ""
    campaign_id: str = ""
    strategy_authority_lineage: dict[str, Any] | None = None
    strategy_authority_lineage_hash: str = ""


@dataclass(frozen=True)
class BrokerExecutionSnapshot(BrokerSnapshotBase):
    execution_ref_hash: str
    order_ref_hash: str
    execution_key: str
    symbol: str
    side: str
    quantity: float
    price: float
    executed_at: str


@dataclass(frozen=True)
class BrokerPositionSnapshot(BrokerSnapshotBase):
    position_ref_hash: str
    position_key: str
    symbol: str
    quantity: float
    average_price: float
    market_value: float


@dataclass(frozen=True)
class BrokerCashSnapshot(BrokerSnapshotBase):
    cash_ref_hash: str
    cash: float
    buying_power: float
    currency: str


@dataclass(frozen=True)
class BrokerReadOnlyBundle:
    orders: tuple[BrokerOrderSnapshot, ...]
    executions: tuple[BrokerExecutionSnapshot, ...]
    positions: tuple[BrokerPositionSnapshot, ...]
    cash: BrokerCashSnapshot | None
    environment: str
    source: str
    as_of: str
    review_required: bool
    production_equivalent: bool
