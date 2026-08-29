"""Projection from Broker ReadOnly snapshots to Runtime v2 ledger records."""

from __future__ import annotations

from typing import Any, Mapping

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
    source_order: BrokerOrderSnapshot | None = None,
) -> LedgerExecutionRecord:
    provenance = _execution_provenance(execution=execution, source_order=source_order)
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
        source_decision_id=provenance["source_decision_id"],
        source_pm_decision_id=provenance["source_pm_decision_id"],
        source_decision_type=provenance["source_decision_type"],
        source_pm_business_date=provenance["source_pm_business_date"],
        source_position_symbol=provenance["source_position_symbol"],
        position_campaign_id=provenance["position_campaign_id"],
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
        position_campaign_id=position.position_campaign_id,
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
        source_decision_id=order.source_decision_id or order.source_pm_decision_id,
        source_decision_type=order.source_decision_type,
        source_pm_decision_id=order.source_pm_decision_id,
        source_pm_business_date=order.source_pm_business_date,
        source_position_symbol=order.source_position_symbol,
        position_campaign_id=order.position_campaign_id,
        strategy_authority_lineage=dict(order.strategy_authority_lineage or {}),
        strategy_authority_lineage_hash=order.strategy_authority_lineage_hash,
    )


def _execution_provenance(
    *,
    execution: BrokerExecutionSnapshot,
    source_order: BrokerOrderSnapshot | None,
) -> dict[str, str]:
    execution_mapping = {
        "source_decision_id": execution.source_decision_id,
        "source_pm_decision_id": execution.source_pm_decision_id,
        "source_decision_type": execution.source_decision_type,
        "source_pm_business_date": execution.source_pm_business_date,
        "source_position_symbol": execution.source_position_symbol,
        "position_campaign_id": execution.position_campaign_id,
    }
    order_mapping = _order_provenance_mapping(source_order)
    order_lineage: Mapping[str, Any] = (
        source_order.strategy_authority_lineage
        if source_order is not None and isinstance(source_order.strategy_authority_lineage, Mapping)
        else {}
    )
    mappings = (execution_mapping, order_mapping, order_lineage)
    return {
        "source_decision_id": _first_text(
            mappings,
            ("source_decision_id", "source_pm_decision_id", "pm_decision_id", "decision_id"),
        ),
        "source_pm_decision_id": _first_text(
            mappings,
            ("source_pm_decision_id", "source_decision_id", "pm_decision_id"),
        ),
        "source_decision_type": _first_text(mappings, ("source_decision_type", "decision_type", "source_decision")),
        "source_pm_business_date": _first_text(
            mappings,
            ("source_pm_business_date", "pm_business_date", "decision_business_date", "business_date"),
        ),
        "source_position_symbol": _first_text(
            mappings,
            ("source_position_symbol", "position_symbol", "symbol", "security_code"),
        ),
        "position_campaign_id": _first_text(
            mappings,
            ("position_campaign_id", "current_position_campaign_id", "pm_position_campaign_id", "campaign_id"),
        ),
    }


def _order_provenance_mapping(order: BrokerOrderSnapshot | None) -> dict[str, Any]:
    if order is None:
        return {}
    return {
        "source_decision_id": order.source_decision_id,
        "source_pm_decision_id": order.source_pm_decision_id,
        "source_decision_type": order.source_decision_type,
        "source_pm_business_date": order.source_pm_business_date,
        "source_position_symbol": order.source_position_symbol,
        "position_campaign_id": order.position_campaign_id,
    }


def _first_text(mappings: tuple[Mapping[str, Any], ...], keys: tuple[str, ...]) -> str:
    for mapping in mappings:
        for key in keys:
            value = mapping.get(key)
            if value not in (None, ""):
                return str(value)
    return ""


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
