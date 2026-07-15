"""Path resolution for Runtime v2 current, history, and derived artifacts."""

from __future__ import annotations

import re
from pathlib import Path

ALLOWED_MODES = frozenset({"production", "demo", "simulation", "backtest", "historical"})
ALLOWED_ENVIRONMENTS = frozenset({"production", "demo", "simulation", "backtest", "historical"})
MODE_ROOTED_RUNTIME_MODES = frozenset({"production", "demo", "simulation", "backtest", "historical"})
MODE_ROOTED_RUNTIME_ROOT_FORBIDDEN = "MODE_ROOTED_RUNTIME_ROOT_FORBIDDEN"

CURRENT_OBJECT_PATHS = {
    "runtime_state": Path("runtime_state/current_state.json"),
    "pending_order_plan": Path("pending_order_plan/pending_order_plan.json"),
    "persistent_ledger_state": Path("persistent_ledger/state.json"),
    "persistent_ledger_orders": Path("persistent_ledger/orders.jsonl"),
    "persistent_ledger_executions": Path("persistent_ledger/executions.jsonl"),
    "persistent_ledger_positions": Path("persistent_ledger/positions.jsonl"),
    "persistent_ledger_cash": Path("persistent_ledger/cash.jsonl"),
    "persistent_ledger_events": Path("persistent_ledger/events.jsonl"),
    "notification_delivery_ledger": Path("notification_delivery/delivery_ledger.jsonl"),
}

_OBJECT_TYPE_RE = re.compile(r"^[a-z0-9_]+$")
_BUSINESS_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def resolve_current_path(mode: str, environment: str, object_type: str) -> Path:
    """Resolve a Runtime v2 current artifact path.

    Mode and environment are validated for explicit runtime intent, but Current
    storage is intentionally not rooted by mode. Demo/production differences
    are handled by runtime mode, broker adapter, and config, not by Current path.
    """

    _validate_mode(mode)
    _validate_environment(environment)
    _validate_object_type(object_type)
    try:
        relative_path = CURRENT_OBJECT_PATHS[object_type]
    except KeyError as exc:
        raise ValueError(f"unsupported current object_type: {object_type}") from exc
    return Path(".runtime") / relative_path


def is_mode_rooted_runtime_root(path: Path | str) -> bool:
    """Return true when a runtime root points inside ``.runtime/<mode>``."""

    normalized = Path(path).expanduser().resolve(strict=False)
    parts = normalized.parts
    return any(
        part == ".runtime"
        and index + 1 < len(parts)
        and parts[index + 1] in MODE_ROOTED_RUNTIME_MODES
        for index, part in enumerate(parts)
    )


def reject_mode_rooted_runtime_root(path: Path | str) -> None:
    if is_mode_rooted_runtime_root(path):
        raise ValueError(
            f"{MODE_ROOTED_RUNTIME_ROOT_FORBIDDEN}: Runtime root must be fixed .runtime, not .runtime/<mode>"
        )


def resolve_history_path(
    mode: str,
    environment: str,
    object_type: str,
    business_date: str,
) -> Path:
    """Resolve a Runtime v2 history/evidence artifact directory path."""

    _validate_mode(mode)
    _validate_environment(environment)
    _validate_object_type(object_type)
    _validate_business_date(business_date)
    return _runtime_root(mode) / "history" / object_type / business_date


def resolve_derived_path(
    mode: str,
    environment: str,
    object_type: str,
    business_date: str,
) -> Path:
    """Resolve a Runtime v2 derived artifact directory path."""

    _validate_mode(mode)
    _validate_environment(environment)
    _validate_object_type(object_type)
    _validate_business_date(business_date)
    return _runtime_root(mode) / "derived" / object_type / business_date


def _runtime_root(mode: str) -> Path:
    return Path(".runtime") / mode


def _validate_mode(mode: str) -> None:
    if not mode:
        raise ValueError("mode is required")
    if mode not in ALLOWED_MODES:
        raise ValueError(f"unsupported mode: {mode}")


def _validate_environment(environment: str) -> None:
    if not environment:
        raise ValueError("environment is required")
    if environment not in ALLOWED_ENVIRONMENTS:
        raise ValueError(f"unsupported environment: {environment}")


def _validate_object_type(object_type: str) -> None:
    if not object_type:
        raise ValueError("object_type is required")
    if not _OBJECT_TYPE_RE.fullmatch(object_type):
        raise ValueError(f"invalid object_type: {object_type}")


def _validate_business_date(business_date: str) -> None:
    if not business_date:
        raise ValueError("business_date is required")
    if not _BUSINESS_DATE_RE.fullmatch(business_date):
        raise ValueError(f"invalid business_date: {business_date}")
