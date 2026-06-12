from __future__ import annotations

import json
from dataclasses import fields
from decimal import Decimal
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.broker.models import BrokerBalanceSnapshot, BrokerOrderSnapshot, BrokerPositionSnapshot
from ai_fund_lab_v2.broker.sanitizer import sanitize_mapping
from ai_fund_lab_v2.safety.broker_state_adapter import build_broker_state_from_snapshots
from ai_fund_lab_v2.safety.models import BrokerState


class SafetySnapshotLoadError(RuntimeError):
    """Raised when a broker snapshot file cannot be loaded for safety dry-run."""


def load_broker_snapshot(path: Path | str) -> dict[str, Any]:
    snapshot_path = Path(path)
    if not snapshot_path.exists():
        raise SafetySnapshotLoadError(f"Broker snapshot file does not exist: {snapshot_path}")
    try:
        payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SafetySnapshotLoadError(f"Broker snapshot file is not valid JSON: {snapshot_path}") from exc
    if not isinstance(payload, dict):
        raise SafetySnapshotLoadError(f"Broker snapshot payload must be a JSON object: {snapshot_path}")
    return sanitize_mapping(payload)


def load_broker_state_from_snapshot_files(paths: list[Path | str]) -> BrokerState:
    if not paths:
        raise SafetySnapshotLoadError("At least one broker snapshot file is required.")
    balance_snapshots: list[BrokerBalanceSnapshot] = []
    position_snapshots: list[BrokerPositionSnapshot] = []
    order_snapshots: list[BrokerOrderSnapshot] = []
    for path in paths:
        payload = load_broker_snapshot(path)
        kind = str(payload.get("kind") or "")
        records = payload.get("records")
        if not isinstance(records, list):
            raise SafetySnapshotLoadError(f"Broker snapshot records must be a list: {path}")
        if kind == "balance":
            balance_snapshots.extend(_build_records(records, BrokerBalanceSnapshot))
        elif kind == "positions":
            position_snapshots.extend(_build_records(records, BrokerPositionSnapshot))
        elif kind == "orders":
            order_snapshots.extend(_build_records(records, BrokerOrderSnapshot))
        else:
            raise SafetySnapshotLoadError(f"Unsupported broker snapshot kind: {kind or '[missing]'}")
    if not balance_snapshots:
        raise SafetySnapshotLoadError("A balance broker snapshot is required to build BrokerState.")
    return build_broker_state_from_snapshots(
        balance_snapshot=balance_snapshots[-1],
        position_snapshots=tuple(position_snapshots),
        order_snapshots=tuple(order_snapshots),
    )


def _build_records(records: list[Any], model: type[Any]) -> list[Any]:
    return [_build_record(record, model) for record in records if isinstance(record, dict)]


def _build_record(record: dict[str, Any], model: type[Any]) -> Any:
    field_names = {field.name for field in fields(model)}
    kwargs = {key: _coerce_value(key, value) for key, value in record.items() if key in field_names}
    return model(**kwargs)


def _coerce_value(key: str, value: Any) -> Any:
    decimal_fields = {
        "cash_available",
        "buying_power",
        "withdrawable_cash",
        "total_assets",
        "quantity",
        "available_quantity",
        "average_price",
        "market_price",
        "market_value",
        "unrealized_pnl",
        "executed_quantity",
        "remaining_quantity",
        "price",
    }
    if key in decimal_fields:
        return Decimal(str(value))
    if key == "warnings" and isinstance(value, list):
        return tuple(str(item) for item in value)
    return value
