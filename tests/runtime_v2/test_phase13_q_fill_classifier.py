from dataclasses import replace

from ai_fund_lab_v2.runtime_v2.broker_readonly.normalizer import (
    normalize_broker_readonly_payload,
)
from ai_fund_lab_v2.runtime_v2.execution.fill_classifier import classify_fill
from ai_fund_lab_v2.runtime_v2.execution.models import FillClassificationType


def test_filled_quantity_zero_is_no_fill():
    order = _order(filled_quantity=0, remaining_quantity=100)

    result = classify_fill(order=order, executions=())

    assert result.classification == FillClassificationType.NO_FILL


def test_partial_fill_with_execution_is_partial_fill():
    order = _order(filled_quantity=40, remaining_quantity=60)
    execution = _execution(order.order_ref_hash, quantity=40)

    result = classify_fill(order=order, executions=(execution,))

    assert result.classification == FillClassificationType.PARTIAL_FILL


def test_full_fill_with_execution_is_full_fill():
    order = _order(filled_quantity=100, remaining_quantity=0)
    execution = _execution(order.order_ref_hash, quantity=100)

    result = classify_fill(order=order, executions=(execution,))

    assert result.classification == FillClassificationType.FULL_FILL


def test_full_fill_without_execution_requires_review():
    order = _order(filled_quantity=100, remaining_quantity=0)

    result = classify_fill(order=order, executions=())

    assert result.classification == FillClassificationType.REVIEW_REQUIRED
    assert result.review_required is True


def test_cancelled_order_is_cancelled():
    order = replace(_order(filled_quantity=0, remaining_quantity=100), order_status="cancelled")

    result = classify_fill(order=order, executions=())

    assert result.classification == FillClassificationType.ORDER_CANCELLED


def test_quantity_mismatch_requires_review():
    order = _order(filled_quantity=50, remaining_quantity=50)
    execution = _execution(order.order_ref_hash, quantity=40)

    result = classify_fill(order=order, executions=(execution,))

    assert result.classification == FillClassificationType.REVIEW_REQUIRED
    assert result.review_required is True


def test_order_accepted_only_is_not_asset():
    order = _order(filled_quantity=0, remaining_quantity=100)

    result = classify_fill(order=order, executions=())

    assert result.classification == FillClassificationType.NO_FILL
    assert result.filled_quantity == 0


def _order(filled_quantity: float, remaining_quantity: float):
    return normalize_broker_readonly_payload(
        environment="demo",
        source="broker_readonly",
        as_of="2026-07-07T00:00:00Z",
        orders=(
            {
                "order_ref": "ORDER-1",
                "pending_plan_id": "pending-1",
                "pending_item_id": "item-1",
                "symbol": "7203",
                "side": "BUY",
                "quantity": 100,
                "order_status": "accepted",
                "filled_quantity": filled_quantity,
                "remaining_quantity": remaining_quantity,
            },
        ),
    ).orders[0]


def _execution(order_ref_hash: str, quantity: float):
    execution = normalize_broker_readonly_payload(
        environment="demo",
        source="broker_readonly",
        as_of="2026-07-07T00:00:00Z",
        executions=(
            {
                "execution_ref": "EXEC-1",
                "order_ref": "ORDER-1",
                "execution_key": "exec-key-1",
                "symbol": "7203",
                "side": "BUY",
                "quantity": quantity,
                "price": 2500,
                "executed_at": "2026-07-07T00:01:00Z",
            },
        ),
    ).executions[0]
    return replace(execution, order_ref_hash=order_ref_hash)

