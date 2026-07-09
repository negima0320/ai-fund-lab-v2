"""Projection from Broker ReadOnly snapshots to Runtime v2 ledger records."""

from __future__ import annotations

from ai_fund_lab_v2.runtime_v2.broker_readonly.models import (
    BrokerCashSnapshot,
    BrokerExecutionSnapshot,
    BrokerOrderSnapshot,
    BrokerPositionSnapshot,
)
from ai_fund_lab_v2.runtime_v2.ledger.models import (
    LedgerCashRecord,
    LedgerExecutionRecord,
    LedgerOrderRecord,
    LedgerPositionRecord,
)


def project_execution_to_ledger_record(
    execution: BrokerExecutionSnapshot,
) -> LedgerExecutionRecord:
    return LedgerExecutionRecord(
        record_id=f"ledger-execution-{_short_hash(execution.execution_ref_hash)}",
        record_type="execution",
        schema_version="1",
        environment=execution.environment,
        source=execution.source,
        created_at=execution.as_of,
        dedup_key=execution.execution_ref_hash,
        review_required=execution.review_required,
        production_equivalent=execution.production_equivalent,
        execution_id=execution.execution_ref_hash,
        order_id=execution.order_ref_hash,
        execution_key=execution.execution_key,
        execution_evidence_type="broker_detail_execution",
        business_date=execution.as_of[:10],
        mode=execution.environment,
        side=execution.side,
        symbol=execution.symbol,
        broker_issue_code=execution.symbol,
        quantity=execution.quantity,
        filled_quantity=execution.quantity,
        remaining_quantity=0.0,
        order_status="filled",
        execution_status="filled",
        price_source="orderlist_detail",
        price=execution.price,
        average_price=execution.price,
        market_price=execution.price,
        detail_required=True,
        detail_status="AVAILABLE",
        executed_at=execution.executed_at,
    )


def project_position_to_ledger_record(position: BrokerPositionSnapshot) -> LedgerPositionRecord:
    return LedgerPositionRecord(
        record_id=f"ledger-position-{_short_hash(position.position_ref_hash)}",
        record_type="position",
        schema_version="1",
        environment=position.environment,
        source=position.source,
        created_at=position.as_of,
        dedup_key=position.position_ref_hash,
        review_required=position.review_required,
        production_equivalent=position.production_equivalent,
        position_key=position.position_key,
        symbol=position.symbol,
        quantity=position.quantity,
        average_price=position.average_price,
        market_value=position.market_value,
        as_of=position.as_of,
    )


def project_cash_to_ledger_record(cash: BrokerCashSnapshot) -> LedgerCashRecord:
    return LedgerCashRecord(
        record_id=f"ledger-cash-{_short_hash(cash.cash_ref_hash)}",
        record_type="cash",
        schema_version="1",
        environment=cash.environment,
        source=cash.source,
        created_at=cash.as_of,
        dedup_key=cash.cash_ref_hash,
        review_required=cash.review_required,
        production_equivalent=cash.production_equivalent,
        cash_key=cash.cash_ref_hash,
        cash=cash.cash,
        buying_power=cash.buying_power,
        currency=cash.currency,
        as_of=cash.as_of,
    )


def project_order_to_ledger_record(order: BrokerOrderSnapshot) -> LedgerOrderRecord:
    return LedgerOrderRecord(
        record_id=f"ledger-order-{_short_hash(order.order_ref_hash)}",
        record_type="order",
        schema_version="1",
        environment=order.environment,
        source=order.source,
        created_at=order.as_of,
        dedup_key=order.order_ref_hash,
        review_required=order.review_required,
        production_equivalent=order.production_equivalent,
        order_id=order.order_ref_hash,
        pending_plan_id=order.pending_plan_id,
        pending_item_id=order.pending_item_id,
        side=order.side,
        symbol=order.symbol,
        quantity=order.quantity,
        status=order.order_status,
    )


def can_use_broker_orders_fallback(
    *,
    environment: str,
    mode: str,
    explicitly_requested: bool = False,
    production: bool = False,
) -> bool:
    if production or mode == "production" or environment == "production":
        return False
    if mode != "demo" or environment != "demo":
        return False
    return explicitly_requested


def fallback_policy_metadata(
    *,
    environment: str,
    mode: str,
    explicitly_requested: bool = False,
    production: bool = False,
) -> dict[str, object]:
    allowed = can_use_broker_orders_fallback(
        environment=environment,
        mode=mode,
        explicitly_requested=explicitly_requested,
        production=production,
    )
    return {
        "allowed": allowed,
        "source": "broker_orders_fallback",
        "review_required": True,
        "production_equivalent": False,
    }


def _short_hash(value: str) -> str:
    return value.split(":", 1)[-1][:16]
