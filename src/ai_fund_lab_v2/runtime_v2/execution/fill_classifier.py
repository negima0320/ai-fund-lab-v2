"""Fill classification skeleton for Runtime v2."""

from __future__ import annotations

import hashlib
from typing import Sequence

from ai_fund_lab_v2.runtime_v2.broker_readonly.models import (
    BrokerCashSnapshot,
    BrokerExecutionSnapshot,
    BrokerOrderSnapshot,
    BrokerPositionSnapshot,
)
from ai_fund_lab_v2.runtime_v2.execution.models import (
    FillClassification,
    FillClassificationType,
    OrderListPositionCashEvidencePolicyResult,
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


def classify_orderlist_position_cash_fill(
    *,
    order: BrokerOrderSnapshot,
    positions: Sequence[BrokerPositionSnapshot],
    cash: BrokerCashSnapshot | None,
    executions: Sequence[BrokerExecutionSnapshot] = (),
    order_list_detail_required: bool = False,
) -> OrderListPositionCashEvidencePolicyResult:
    """Classify order-list derived fills using position/cash evidence.

    CLMOrderListDetail is optional here. A filled order can become
    execution-equivalent only when the order-list fill is corroborated by
    position and cash/buying-power evidence.
    """

    base = classify_fill(order=order, executions=executions)
    if executions:
        return OrderListPositionCashEvidencePolicyResult(
            classification=base,
            execution_equivalent=base.classification == FillClassificationType.FULL_FILL,
            detail_optional_missing=False,
            ledger_execution_allowed=base.classification == FillClassificationType.FULL_FILL,
            asset_reflection_allowed=base.classification == FillClassificationType.FULL_FILL,
            evidence_sources=(
                "CLMOrderList",
                "CLMOrderListDetail",
                "CLMGenbutuKabuList",
                "CLMZanKaiSummary",
                "CLMZanKaiKanougaku",
            ),
            reason="execution detail evidence available",
        )
    if order_list_detail_required:
        return OrderListPositionCashEvidencePolicyResult(
            classification=base,
            execution_equivalent=False,
            detail_optional_missing=True,
            ledger_execution_allowed=False,
            asset_reflection_allowed=False,
            evidence_sources=("CLMOrderList",),
            reason="order list detail required but missing",
        )
    if not _is_full_fill_from_order_list(order):
        return OrderListPositionCashEvidencePolicyResult(
            classification=base,
            execution_equivalent=False,
            detail_optional_missing=False,
            ledger_execution_allowed=False,
            asset_reflection_allowed=False,
            evidence_sources=("CLMOrderList",),
            reason="order list does not show full fill",
        )
    has_position = _has_position_evidence(order=order, positions=positions)
    has_cash = cash is not None and (cash.cash is not None or cash.buying_power is not None)
    if not has_position or not has_cash:
        return OrderListPositionCashEvidencePolicyResult(
            classification=base,
            execution_equivalent=False,
            detail_optional_missing=True,
            ledger_execution_allowed=False,
            asset_reflection_allowed=False,
            evidence_sources=tuple(
                source
                for source, present in (
                    ("CLMOrderList", True),
                    ("CLMGenbutuKabuList", has_position),
                    ("CLMZanKaiSummary", has_cash),
                    ("CLMZanKaiKanougaku", has_cash),
                )
                if present
            ),
            reason="order list fill missing position or cash corroboration",
        )
    classification = FillClassification(
        classification_id=base.classification_id,
        order_ref_hash=base.order_ref_hash,
        pending_plan_id=base.pending_plan_id,
        pending_item_id=base.pending_item_id,
        symbol=base.symbol,
        side=base.side,
        ordered_quantity=base.ordered_quantity,
        filled_quantity=base.filled_quantity,
        remaining_quantity=base.remaining_quantity,
        classification=FillClassificationType.ORDER_LIST_DERIVED_FULL_FILL,
        review_required=False,
        production_equivalent=base.production_equivalent,
        source=base.source,
        as_of=base.as_of,
    )
    return OrderListPositionCashEvidencePolicyResult(
        classification=classification,
        execution_equivalent=True,
        detail_optional_missing=True,
        ledger_execution_allowed=True,
        asset_reflection_allowed=True,
        evidence_sources=(
            "CLMOrderList",
            "CLMGenbutuKabuList",
            "CLMZanKaiSummary",
            "CLMZanKaiKanougaku",
        ),
        reason="order list full fill corroborated by position and cash evidence",
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


def _is_full_fill_from_order_list(order: BrokerOrderSnapshot) -> bool:
    normalized = order.order_status.lower()
    status_full = (
        normalized in {"filled", "full_fill", "fully_filled", "全部約定"}
        or "全部約定" in order.order_status
    )
    quantity_full = order.filled_quantity > 0 and abs(order.filled_quantity - order.quantity) < 0.000001
    no_remaining = abs(order.remaining_quantity) < 0.000001
    return status_full and quantity_full and no_remaining


def _has_position_evidence(*, order: BrokerOrderSnapshot, positions: Sequence[BrokerPositionSnapshot]) -> bool:
    if order.side.upper() == "BUY":
        return any(
            position.symbol == order.symbol and position.quantity >= order.filled_quantity
            for position in positions
        )
    if order.side.upper() == "SELL":
        return any(position.symbol == order.symbol for position in positions)
    return False


def _classification_id(order_ref_hash: str, as_of: str) -> str:
    raw = f"{order_ref_hash}:{as_of}".encode("utf-8")
    return "fill-" + hashlib.sha256(raw).hexdigest()[:16]
