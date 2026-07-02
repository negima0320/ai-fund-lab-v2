from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class ExitAdapterResult:
    status: str
    sell_items: list[dict[str, Any]]
    blocked_reasons: list[str]
    exit_source: str
    runtime_position_input_used: bool = True
    ai_training_input_used: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "sell_item_count": len(self.sell_items),
            "blocked_reasons": self.blocked_reasons,
            "exit_source": self.exit_source,
            "runtime_position_input_used": self.runtime_position_input_used,
            "ai_training_input_used": self.ai_training_input_used,
            "broker_snapshot_used_for_ai_training": False,
            "paper_ledger_used_for_ai_training": False,
            "safety_result_used_for_ai_training": False,
            "audit_result_used_for_ai_training": False,
            "cash_portfolio_pnl_used_for_ai_training": False,
        }


def generate_sell_items_from_positions(
    positions: list[dict[str, Any]],
    *,
    trade_date: str,
    exit_source: str = "fallback",
) -> ExitAdapterResult:
    if not positions:
        return ExitAdapterResult(status="PASS", sell_items=[], blocked_reasons=[], exit_source=exit_source)
    blocked: list[str] = []
    sell_items: list[dict[str, Any]] = []
    for index, position in enumerate(positions, start=1):
        normalized, errors = _normalize_position(position, index=index)
        if errors:
            blocked.extend(errors)
            continue
        decision = _classify_exit(normalized)
        if decision["action"] == "HOLD":
            continue
        quantity = normalized["quantity"]
        if decision["action"] == "REDUCE":
            quantity = _round_lot_down(quantity / Decimal("2"), normalized["lot_size"])
            if quantity <= 0:
                continue
        expected_notional = (quantity * normalized["current_price"]).quantize(Decimal("1"))
        sell_items.append(
            {
                "item_id": f"sell_{trade_date}_{normalized['code']}_{index:03d}",
                "code": normalized["code"],
                "issue_code": normalized["code"],
                "side": "SELL",
                "quantity": str(quantity),
                "order_type": "CASH_EQUITY",
                "price_type": "LIMIT",
                "limit_price": str(normalized["current_price"]),
                "estimated_value": str(expected_notional),
                "expected_notional": str(expected_notional),
                "position_id": normalized["position_id"],
                "lot_reference": normalized["lot_reference"],
                "exit_source": str(position.get("exit_source") or exit_source),
                "exit_reason": decision["exit_reason"],
                "sell_reason": decision["sell_reason"],
                "position_entry_price": str(normalized["entry_price"]),
                "current_price": str(normalized["current_price"]),
                "unrealized_return": str(normalized["unrealized_return"]),
                "broker_position_quantity": str(normalized["quantity"]),
                "sell_intent": "FULL_CLOSE" if quantity == normalized["quantity"] else "PARTIAL_SELL",
                "approval_required": True,
                "production_order_allowed": False,
                "demo_order_allowed": False,
                "source": "operations_exit_adapter",
            }
        )
    return ExitAdapterResult(status="PASS" if not blocked else "BLOCK", sell_items=sell_items, blocked_reasons=blocked, exit_source=exit_source)


def _normalize_position(position: dict[str, Any], *, index: int) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    code = str(position.get("issue_code") or position.get("code") or "").strip()
    if not code:
        errors.append(f"position_{index}_code_missing")
    quantity = _decimal(position.get("quantity"))
    lot_size = int(position.get("lot_size") or 100)
    if quantity <= 0:
        errors.append(f"position_{index}_quantity_not_positive")
    if lot_size <= 0:
        errors.append(f"position_{index}_lot_size_invalid")
    current_price = _decimal(position.get("current_price") or position.get("market_price"))
    entry_price = _decimal(position.get("position_entry_price") or position.get("entry_price") or position.get("average_cost"))
    if current_price <= 0:
        errors.append(f"position_{index}_current_price_missing")
    if entry_price <= 0:
        errors.append(f"position_{index}_entry_price_missing")
    position_id = str(position.get("position_id") or "").strip()
    if not position_id:
        errors.append(f"position_{index}_position_id_missing")
    lot_reference = str(position.get("lot_reference") or position_id).strip()
    unrealized_return = _decimal(position.get("unrealized_return"))
    if unrealized_return == 0 and entry_price > 0 and current_price > 0:
        unrealized_return = (current_price / entry_price) - Decimal("1")
    return (
        {
            "code": code,
            "quantity": quantity,
            "lot_size": lot_size,
            "current_price": current_price,
            "entry_price": entry_price,
            "unrealized_return": unrealized_return,
            "position_id": position_id,
            "lot_reference": lot_reference,
            "requested_action": str(position.get("exit_action") or position.get("action") or "").upper(),
            "exit_reason": str(position.get("exit_reason") or ""),
            "sell_reason": str(position.get("sell_reason") or ""),
        },
        errors,
    )


def _classify_exit(position: dict[str, Any]) -> dict[str, str]:
    requested = position["requested_action"]
    if requested in {"EXIT", "SELL"}:
        reason = position["exit_reason"] or "explicit_exit_signal"
        return {"action": "EXIT", "exit_reason": reason, "sell_reason": position["sell_reason"] or reason}
    if requested == "REDUCE":
        reason = position["exit_reason"] or "explicit_reduce_signal"
        return {"action": "REDUCE", "exit_reason": reason, "sell_reason": position["sell_reason"] or reason}
    if position["unrealized_return"] <= Decimal("-0.08"):
        return {"action": "EXIT", "exit_reason": "fallback_hard_stop_current_return", "sell_reason": "fallback_hard_stop_current_return"}
    return {"action": "HOLD", "exit_reason": "", "sell_reason": ""}


def _round_lot_down(quantity: Decimal, lot_size: int) -> Decimal:
    lots = int(quantity // Decimal(str(lot_size)))
    return Decimal(lots * lot_size)


def _decimal(value: Any) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    return Decimal(str(value).replace(",", ""))
