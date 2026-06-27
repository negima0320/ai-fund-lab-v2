from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
from typing import Any

from ai_fund_lab_v2.runtime.fill_event import FillEvent, FillMonitorResult, FillMonitorStatus, OrderLifecycle, runtime_state_for_lifecycle
from ai_fund_lab_v2.runtime.order_command import OrderSide
from ai_fund_lab_v2.runtime.runtime_context import RuntimeContext


TERMINAL_REVIEW_LIFECYCLES = {
    OrderLifecycle.REJECTED,
    OrderLifecycle.EXPIRED,
    OrderLifecycle.CANCELED,
    OrderLifecycle.UNKNOWN_STATUS,
    OrderLifecycle.REQUIRES_HUMAN_REVIEW,
}


@dataclass(frozen=True)
class FillMonitor:
    def classify(
        self,
        *,
        context: RuntimeContext,
        order: Mapping[str, Any] | None = None,
        detail: Mapping[str, Any] | None = None,
        position: Mapping[str, Any] | None = None,
    ) -> FillMonitorResult:
        if not order:
            return self._result(
                context=context,
                lifecycle=OrderLifecycle.REQUIRES_HUMAN_REVIEW,
                reason="ORDER_LIST_EMPTY_AFTER_SUBMISSION",
            )

        order_quantity = _decimal(_first(order, "order_quantity", "quantity", "sOrderOrderSuryou", "sOrderSuryou"))
        filled_quantity = _filled_quantity(order, detail)
        remaining_quantity = max(order_quantity - filled_quantity, Decimal("0"))
        latest_fill_price = _latest_fill_price(detail)
        average_fill_price = _average_fill_price(detail, latest_fill_price)
        lifecycle = _classify_lifecycle(order, detail, filled_quantity, order_quantity)
        reason = _reason_for_lifecycle(lifecycle)

        if lifecycle is OrderLifecycle.FILLED and position is not None and not _position_confirms(position, order, filled_quantity):
            lifecycle = OrderLifecycle.REQUIRES_HUMAN_REVIEW
            reason = "POSITION_MISMATCH"

        event = FillEvent(
            runtime_id=context.runtime_id,
            environment=context.environment,
            issue_code=str(_first(order, "issue_code", "sIssueCode", "sOrderIssueCode", default="") or ""),
            side=_side(_first(order, "side", "sOrderBaibaiKubun", default="")),
            order_quantity=order_quantity,
            filled_quantity=filled_quantity,
            remaining_quantity=remaining_quantity,
            average_fill_price=average_fill_price,
            latest_fill_price=latest_fill_price,
            order_status=str(_first(order, "order_status", "status", "sOrderStatus", "sOrderStatusCode", default="") or ""),
            lifecycle_status=lifecycle,
            order_number_hash=_hash_optional(_first(order, "order_number_hash", default="")),
            execution_id_hash=_execution_hash(detail),
            source="mock",
            raw_ids_saved=False,
        )
        return self._result(context=context, lifecycle=lifecycle, reason=reason, events=(event,))

    def _result(
        self,
        *,
        context: RuntimeContext,
        lifecycle: OrderLifecycle,
        reason: str,
        events: tuple[FillEvent, ...] = (),
    ) -> FillMonitorResult:
        requires_review = lifecycle in TERMINAL_REVIEW_LIFECYCLES
        status = FillMonitorStatus.HALT if requires_review else FillMonitorStatus.PASS
        if lifecycle is OrderLifecycle.REQUIRES_HUMAN_REVIEW:
            status = FillMonitorStatus.PASS_WITH_REVIEW
        return FillMonitorResult(
            status=status,
            lifecycle_status=lifecycle,
            runtime_next_state=runtime_state_for_lifecycle(lifecycle),
            filled=lifecycle is OrderLifecycle.FILLED,
            partially_filled=lifecycle is OrderLifecycle.PARTIALLY_FILLED,
            rejected=lifecycle is OrderLifecycle.REJECTED,
            expired=lifecycle is OrderLifecycle.EXPIRED,
            canceled=lifecycle is OrderLifecycle.CANCELED,
            requires_human_review=requires_review,
            reason=reason,
            events=events,
        )


def _classify_lifecycle(
    order: Mapping[str, Any],
    detail: Mapping[str, Any] | None,
    filled_quantity: Decimal,
    order_quantity: Decimal,
) -> OrderLifecycle:
    status_code = str(_first(order, "status_code", "sOrderStatusCode", default="") or "")
    execution_status = str(_first(order, "execution_status", "sOrderYakuzyouStatus", default="") or "")

    if status_code in {"2", "14"}:
        return OrderLifecycle.REJECTED
    if status_code in {"7"}:
        return OrderLifecycle.CANCELED
    if status_code in {"11", "12", "19"}:
        return OrderLifecycle.EXPIRED
    if status_code in {"3", "4", "5", "6", "8"}:
        return OrderLifecycle.REQUIRES_HUMAN_REVIEW
    if status_code == "9" or execution_status == "1" or (filled_quantity > 0 and filled_quantity < order_quantity):
        return OrderLifecycle.PARTIALLY_FILLED
    if status_code == "10" or execution_status == "2" or (order_quantity > 0 and filled_quantity >= order_quantity):
        return OrderLifecycle.FILLED
    if status_code in {"0"}:
        return OrderLifecycle.ACCEPTED
    if status_code in {"1", "13"} or execution_status in {"0", "3"}:
        return OrderLifecycle.WAITING_FILL
    return OrderLifecycle.UNKNOWN_STATUS


def _reason_for_lifecycle(lifecycle: OrderLifecycle) -> str:
    return {
        OrderLifecycle.ACCEPTED: "ORDER_ACCEPTED_WAITING_FILL",
        OrderLifecycle.WAITING_FILL: "ACCEPTED_WAITING_FILL",
        OrderLifecycle.PARTIALLY_FILLED: "PARTIAL_FILL",
        OrderLifecycle.FILLED: "FULL_FILL",
        OrderLifecycle.REJECTED: "ORDER_REJECTED",
        OrderLifecycle.EXPIRED: "ORDER_EXPIRED",
        OrderLifecycle.CANCELED: "ORDER_CANCELED",
        OrderLifecycle.UNKNOWN_STATUS: "UNKNOWN_ORDER_STATUS",
        OrderLifecycle.REQUIRES_HUMAN_REVIEW: "REQUIRES_HUMAN_REVIEW",
    }.get(lifecycle, lifecycle.value)


def _filled_quantity(order: Mapping[str, Any], detail: Mapping[str, Any] | None) -> Decimal:
    if detail:
        fills = _fills(detail)
        if fills:
            return sum((_decimal(_first(fill, "quantity", "sYakuzyouSuryou")) for fill in fills), Decimal("0"))
        value = _first(detail, "filled_quantity", "sYakuzyouSuryou", "sOrderYakuzyouSuryo")
        if value not in (None, ""):
            return _decimal(value)
    return _decimal(_first(order, "filled_quantity", "executed_quantity", "sOrderYakuzyouSuryo", default="0"))


def _latest_fill_price(detail: Mapping[str, Any] | None) -> Decimal:
    if not detail:
        return Decimal("0")
    fills = _fills(detail)
    if fills:
        return _decimal(_first(fills[-1], "price", "sYakuzyouPrice"))
    return _decimal(_first(detail, "latest_fill_price", "sYakuzyouPrice", default="0"))


def _average_fill_price(detail: Mapping[str, Any] | None, fallback: Decimal) -> Decimal:
    if not detail:
        return Decimal("0")
    fills = _fills(detail)
    if not fills:
        return _decimal(_first(detail, "average_fill_price", "sYakuzyouPrice", default=fallback))
    filled_quantity = sum((_decimal(_first(fill, "quantity", "sYakuzyouSuryou")) for fill in fills), Decimal("0"))
    if filled_quantity == 0:
        return Decimal("0")
    notional = sum(
        (_decimal(_first(fill, "quantity", "sYakuzyouSuryou")) * _decimal(_first(fill, "price", "sYakuzyouPrice")) for fill in fills),
        Decimal("0"),
    )
    return notional / filled_quantity


def _position_confirms(position: Mapping[str, Any], order: Mapping[str, Any], filled_quantity: Decimal) -> bool:
    position_quantity = _decimal(_first(position, "quantity", "sQuantity", "sZanKabuSuu", default="0"))
    side = _side(_first(order, "side", "sOrderBaibaiKubun", default=""))
    if side is OrderSide.BUY:
        return position_quantity >= filled_quantity
    if side is OrderSide.SELL:
        return position_quantity == Decimal("0") or position_quantity <= _decimal(_first(order, "pre_order_position", default=position_quantity))
    return False


def _execution_hash(detail: Mapping[str, Any] | None) -> str:
    if not detail:
        return ""
    if _first(detail, "execution_id_hash", default=""):
        return _hash_optional(_first(detail, "execution_id_hash", default=""))
    fills = _fills(detail)
    if not fills:
        return ""
    material = "|".join(str(_first(fill, "sYakuzyouDate", "executed_at", "quantity", "sYakuzyouSuryou", "price", "sYakuzyouPrice", default="")) for fill in fills)
    return _hash(material)


def _hash_optional(value: Any) -> str:
    text = str(value or "")
    if not text:
        return ""
    if text.startswith("sha256:"):
        return text
    if len(text) < 16:
        raise ValueError("plaintext identifier must be hashed before persistence")
    return _hash(text)


def _hash(value: str) -> str:
    return f"sha256:{sha256(value.encode('utf-8')).hexdigest()}"


def _fills(detail: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    value = _first(detail, "fills", "aYakuzyouSikkouList", default=())
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _side(value: Any) -> OrderSide:
    text = str(value or "")
    if text in {"BUY", "buy", "3", "買"}:
        return OrderSide.BUY
    if text in {"SELL", "sell", "1", "売"}:
        return OrderSide.SELL
    return OrderSide.BUY


def _decimal(value: Any) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    return Decimal(str(value).replace(",", ""))


def _first(data: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in data:
            return data[key]
    return default
