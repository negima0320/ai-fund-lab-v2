"""Pure normalizer for Broker ReadOnly payloads."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from ai_fund_lab_v2.runtime_v2.broker_readonly.models import (
    BrokerCashSnapshot,
    BrokerExecutionSnapshot,
    BrokerOrderSnapshot,
    BrokerPositionSnapshot,
    BrokerReadOnlyBundle,
)


def normalize_broker_readonly_payload(
    *,
    environment: str,
    source: str,
    as_of: str,
    orders: Sequence[Mapping[str, Any]] = (),
    executions: Sequence[Mapping[str, Any]] = (),
    positions: Sequence[Mapping[str, Any]] = (),
    cash: Mapping[str, Any] | None = None,
) -> BrokerReadOnlyBundle:
    """Normalize read-only payload fragments without preserving raw payloads."""

    if not environment:
        raise ValueError("environment is required")
    if not source:
        raise ValueError("source is required")
    if not as_of:
        raise ValueError("as_of is required")
    production_equivalent = source != "broker_orders_fallback"
    review_required = not production_equivalent
    normalized_orders = tuple(
        _normalize_order(
            payload=payload,
            environment=environment,
            source=source,
            as_of=as_of,
            review_required=review_required,
            production_equivalent=production_equivalent,
        )
        for payload in orders
    )
    normalized_executions = tuple(
        _normalize_execution(
            payload=payload,
            environment=environment,
            source=source,
            as_of=as_of,
            review_required=review_required,
            production_equivalent=production_equivalent,
        )
        for payload in executions
    )
    normalized_positions = tuple(
        _normalize_position(
            payload=payload,
            environment=environment,
            source=source,
            as_of=as_of,
            review_required=review_required,
            production_equivalent=production_equivalent,
        )
        for payload in positions
    )
    normalized_cash = (
        None
        if cash is None
        else _normalize_cash(
            payload=cash,
            environment=environment,
            source=source,
            as_of=as_of,
            review_required=review_required,
            production_equivalent=production_equivalent,
        )
    )
    return BrokerReadOnlyBundle(
        orders=normalized_orders,
        executions=normalized_executions,
        positions=normalized_positions,
        cash=normalized_cash,
        environment=environment,
        source=source,
        as_of=as_of,
        review_required=review_required,
        production_equivalent=production_equivalent,
    )


def _normalize_order(
    *,
    payload: Mapping[str, Any],
    environment: str,
    source: str,
    as_of: str,
    review_required: bool,
    production_equivalent: bool,
) -> BrokerOrderSnapshot:
    order_ref_hash = _hash_ref(payload.get("order_ref") or payload.get("order_id"))
    return BrokerOrderSnapshot(
        snapshot_id=_snapshot_id("order", order_ref_hash, as_of),
        schema_version="1",
        environment=environment,
        source=source,
        as_of=as_of,
        broker_ref_hash=order_ref_hash,
        review_required=review_required,
        production_equivalent=production_equivalent,
        order_ref_hash=order_ref_hash,
        pending_plan_id=str(payload.get("pending_plan_id", "")),
        pending_item_id=str(payload.get("pending_item_id", "")),
        symbol=str(payload.get("symbol", "")),
        side=str(payload.get("side", "")),
        quantity=float(payload.get("quantity", 0)),
        order_status=str(payload.get("order_status", "")),
        filled_quantity=float(payload.get("filled_quantity", 0)),
        remaining_quantity=float(payload.get("remaining_quantity", 0)),
        accepted_at=str(payload.get("accepted_at", "")),
        updated_at=str(payload.get("updated_at", as_of)),
    )


def _normalize_execution(
    *,
    payload: Mapping[str, Any],
    environment: str,
    source: str,
    as_of: str,
    review_required: bool,
    production_equivalent: bool,
) -> BrokerExecutionSnapshot:
    execution_ref_hash = _hash_ref(payload.get("execution_ref") or payload.get("execution_id"))
    order_ref_hash = _hash_ref(payload.get("order_ref") or payload.get("order_id"))
    return BrokerExecutionSnapshot(
        snapshot_id=_snapshot_id("execution", execution_ref_hash, as_of),
        schema_version="1",
        environment=environment,
        source=source,
        as_of=as_of,
        broker_ref_hash=execution_ref_hash,
        review_required=review_required,
        production_equivalent=production_equivalent,
        execution_ref_hash=execution_ref_hash,
        order_ref_hash=order_ref_hash,
        execution_key=str(payload.get("execution_key", execution_ref_hash)),
        symbol=str(payload.get("symbol", "")),
        side=str(payload.get("side", "")),
        quantity=float(payload.get("quantity", 0)),
        price=float(payload.get("price", 0)),
        executed_at=str(payload.get("executed_at", as_of)),
    )


def _normalize_position(
    *,
    payload: Mapping[str, Any],
    environment: str,
    source: str,
    as_of: str,
    review_required: bool,
    production_equivalent: bool,
) -> BrokerPositionSnapshot:
    position_ref_hash = _hash_ref(payload.get("position_ref") or payload.get("position_id"))
    return BrokerPositionSnapshot(
        snapshot_id=_snapshot_id("position", position_ref_hash, as_of),
        schema_version="1",
        environment=environment,
        source=source,
        as_of=as_of,
        broker_ref_hash=position_ref_hash,
        review_required=review_required,
        production_equivalent=production_equivalent,
        position_ref_hash=position_ref_hash,
        position_key=str(payload.get("position_key", payload.get("symbol", ""))),
        symbol=str(payload.get("symbol", "")),
        quantity=float(payload.get("quantity", 0)),
        average_price=float(payload.get("average_price", 0)),
        market_value=float(payload.get("market_value", 0)),
    )


def _normalize_cash(
    *,
    payload: Mapping[str, Any],
    environment: str,
    source: str,
    as_of: str,
    review_required: bool,
    production_equivalent: bool,
) -> BrokerCashSnapshot:
    cash_ref_hash = _hash_ref(payload.get("cash_ref") or f"{environment}:{as_of}:cash")
    return BrokerCashSnapshot(
        snapshot_id=_snapshot_id("cash", cash_ref_hash, as_of),
        schema_version="1",
        environment=environment,
        source=source,
        as_of=as_of,
        broker_ref_hash=cash_ref_hash,
        review_required=review_required,
        production_equivalent=production_equivalent,
        cash_ref_hash=cash_ref_hash,
        cash=float(payload.get("cash", 0)),
        buying_power=float(payload.get("buying_power", 0)),
        currency=str(payload.get("currency", "JPY")),
    )


def _hash_ref(value: object) -> str:
    encoded = json.dumps(str(value), sort_keys=True).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _snapshot_id(kind: str, ref_hash: str, as_of: str) -> str:
    return f"{kind}-{_hash_ref(ref_hash + ':' + as_of).split(':', 1)[1][:16]}"
