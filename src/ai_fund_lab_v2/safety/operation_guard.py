from __future__ import annotations

from pathlib import Path

from ai_fund_lab_v2.safety.models import TradingLock
from ai_fund_lab_v2.safety.lock_state_resolver import resolve_current_lock_state

HALT_ALLOWED_OPERATIONS = frozenset({"broker_sync", "read_state", "audit", "report"})
HALT_BLOCKED_OPERATIONS = frozenset(
    {
        "buy",
        "sell",
        "new_order",
        "correct_order",
        "cancel_order",
        "portfolio_update",
        "ai_trade_decision",
    }
)


def is_operation_allowed(operation: str, lock: TradingLock) -> bool:
    normalized = operation.strip().lower()
    if not lock.is_locked:
        return True
    if normalized in HALT_ALLOWED_OPERATIONS:
        return True
    if normalized in HALT_BLOCKED_OPERATIONS:
        return False
    return False


def check_operation_allowed_by_current_state(
    operation: str,
    runtime_dir: Path | str = ".runtime",
) -> dict:
    normalized = operation.strip().lower()
    state = resolve_current_lock_state(runtime_dir)
    is_locked = bool(state.get("is_locked"))
    if not is_locked:
        allowed = True
    elif normalized in HALT_ALLOWED_OPERATIONS:
        allowed = True
    else:
        allowed = False
    return {
        "operation": normalized,
        "allowed": allowed,
        "is_locked": is_locked,
        "source": state.get("source"),
        "status": state.get("status"),
        "message": state.get("message"),
        "state_path": state.get("state_path"),
    }


def is_operation_allowed_by_current_state(
    operation: str,
    runtime_dir: Path | str = ".runtime",
) -> bool:
    return bool(check_operation_allowed_by_current_state(operation, runtime_dir)["allowed"])
