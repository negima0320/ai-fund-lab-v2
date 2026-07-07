"""Fill classification skeleton for Runtime v2."""

from __future__ import annotations

import hashlib
from typing import Sequence

from ai_fund_lab_v2.runtime_v2.broker_readonly.models import (
    BrokerExecutionSnapshot,
    BrokerOrderSnapshot,
)
from ai_fund_lab_v2.runtime_v2.execution.models import (
    FillClassification,
    FillClassificationType,
)


def classify_fill(
    *,
    order: BrokerOrderSnapshot,
    executions: Sequence[BrokerExecutionSnapshot],
) -> FillClassification:
    related_executions = tuple(
        execution for execution in executions if execution.order_ref_hash == order.order_ref_hash
    )
    execution_quantity = sum(execution.quantity for execution in related_executions)
    filled_quantity = order.filled_quantity
    review_required = order.review_required
    classification = _status_classification(order.order_status)

    if classification is None:
        if filled_quantity < 0 or filled_quantity > order.quantity:
            classification = FillClassificationType.REVIEW_REQUIRED
            review_required = True
        elif related_executions and abs(execution_quantity - filled_quantity) > 0.000001:
            classification = FillClassificationType.REVIEW_REQUIRED
            review_required = True
        elif filled_quantity == 0:
            classification = FillClassificationType.NO_FILL
        elif not related_executions:
            classification = FillClassificationType.REVIEW_REQUIRED
            review_required = True
        elif filled_quantity < order.quantity:
            classification = FillClassificationType.PARTIAL_FILL
        elif filled_quantity == order.quantity:
            classification = FillClassificationType.FULL_FILL
        else:
            classification = FillClassificationType.UNKNOWN_FILL
            review_required = True

    return FillClassification(
        classification_id=_classification_id(order.order_ref_hash, order.as_of),
        order_ref_hash=order.order_ref_hash,
        pending_plan_id=order.pending_plan_id,
        pending_item_id=order.pending_item_id,
        symbol=order.symbol,
        side=order.side,
        ordered_quantity=order.quantity,
        filled_quantity=filled_quantity,
        remaining_quantity=order.remaining_quantity,
        classification=classification,
        review_required=review_required or classification == FillClassificationType.REVIEW_REQUIRED,
        production_equivalent=order.production_equivalent,
        source=order.source,
        as_of=order.as_of,
    )


def _status_classification(status: str) -> FillClassificationType | None:
    normalized = status.lower()
    if normalized in {"cancel", "cancelled", "canceled"}:
        return FillClassificationType.ORDER_CANCELLED
    if normalized in {"expired", "expire"}:
        return FillClassificationType.ORDER_EXPIRED
    if normalized in {"rejected", "reject"}:
        return FillClassificationType.ORDER_REJECTED
    return None


def _classification_id(order_ref_hash: str, as_of: str) -> str:
    raw = f"{order_ref_hash}:{as_of}".encode("utf-8")
    return "fill-" + hashlib.sha256(raw).hexdigest()[:16]

