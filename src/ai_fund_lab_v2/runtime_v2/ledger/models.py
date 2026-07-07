"""Append-only ledger record models for Runtime v2."""

from __future__ import annotations

from dataclasses import dataclass


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
    pending_plan_id: str = ""
    pending_item_id: str = ""
    side: str = ""
    symbol: str = ""
    quantity: float = 0.0
    status: str = ""


@dataclass(frozen=True)
class LedgerExecutionRecord(LedgerRecordBase):
    execution_id: str = ""
    order_id: str = ""
    execution_key: str = ""
    side: str = ""
    symbol: str = ""
    quantity: float = 0.0
    price: float = 0.0
    executed_at: str = ""


@dataclass(frozen=True)
class LedgerPositionRecord(LedgerRecordBase):
    position_key: str = ""
    symbol: str = ""
    quantity: float = 0.0
    average_price: float = 0.0
    market_value: float = 0.0
    as_of: str = ""


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
