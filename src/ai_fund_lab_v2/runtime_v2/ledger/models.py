"""Append-only ledger record models for Runtime v2."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class LedgerRecordBase:
    record_id: str
    record_type: str
    schema_version: str
    environment: str
    source: str
    created_at: str
    dedup_key: str
    review_required: bool = False
    production_equivalent: bool = True

    @property
    def effective_review_required(self) -> bool:
        return (
            self.review_required
            or not self.production_equivalent
            or self.source == "broker_orders_fallback"
        )


@dataclass(frozen=True)
class LedgerOrderRecord(LedgerRecordBase):
    order_id: str = ""
    business_date: str = ""
    pending_plan_id: str = ""
    pending_item_id: str = ""
    side: str = ""
    symbol: str = ""
    quantity: float = 0.0
    status: str = ""
    issue_code_normalization: dict[str, Any] = field(default_factory=dict)
    response_classification: dict[str, Any] = field(default_factory=dict)
    source_decision_id: str = ""
    source_decision_type: str = ""
    source_pm_decision_id: str = ""
    source_pm_business_date: str = ""
    source_position_symbol: str = ""
    position_campaign_id: str = ""
    add_candidate_signal: bool = False
    capital_allocation_status: str = ""
    capital_allocation_reason: str = ""
    strategy_authority_lineage: dict[str, Any] = field(default_factory=dict)
    strategy_authority_lineage_hash: str = ""


@dataclass(frozen=True)
class LedgerExecutionRecord(LedgerRecordBase):
    execution_id: str = ""
    order_id: str = ""
    execution_key: str = ""
    execution_evidence_type: str = "broker_detail_execution"
    business_date: str = ""
    mode: str = ""
    side: str = ""
    symbol: str = ""
    broker_issue_code: str = ""
    quantity: float = 0.0
    filled_quantity: float = 0.0
    remaining_quantity: float = 0.0
    order_status: str = ""
    execution_status: str = ""
    price_source: str = ""
    price: float = 0.0
    average_price: float = 0.0
    market_price: float = 0.0
    market_value: float = 0.0
    cash_effect: float | None = None
    source_order_record_id: str = ""
    source_order_hash: str = ""
    source_broker_order_hash: str = ""
    source_decision_id: str = ""
    source_pm_decision_id: str = ""
    source_decision_type: str = ""
    source_pm_business_date: str = ""
    source_position_symbol: str = ""
    position_campaign_id: str = ""
    source_position_record_id: str = ""
    source_position_hash: str = ""
    evidence_refs: tuple[str, ...] = ()
    detail_required: bool = True
    detail_status: str = ""
    executed_at: str = ""


@dataclass(frozen=True)
class LedgerPositionRecord(LedgerRecordBase):
    position_key: str = ""
    symbol: str = ""
    quantity: float = 0.0
    average_price: float = 0.0
    market_value: float = 0.0
    as_of: str = ""
    position_campaign_id: str = ""


@dataclass(frozen=True)
class LedgerCashRecord(LedgerRecordBase):
    cash_key: str = ""
    cash: float = 0.0
    buying_power: float = 0.0
    currency: str = "JPY"
    as_of: str = ""


@dataclass(frozen=True)
class LedgerEventRecord(LedgerRecordBase):
    event_id: str = ""
    event_type: str = ""
    severity: str = ""
    message: str = ""
    related_id: str = ""
