from __future__ import annotations

import json
from dataclasses import asdict, dataclass, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.broker.models import (
    BrokerBalanceSnapshot,
    BrokerOrderSnapshot,
    BrokerPositionSnapshot,
    BrokerSnapshot,
    broker_snapshot_id,
    utc_now_iso,
)
from ai_fund_lab_v2.broker.runtime_paths import BrokerRuntimePaths
from ai_fund_lab_v2.broker.sanitizer import sanitize_mapping


@dataclass(frozen=True)
class BrokerSnapshotWriteResult:
    kind: str
    data_path: Path
    manifest_path: Path
    record_count: int


@dataclass(frozen=True)
class BrokerSnapshotWriter:
    paths: BrokerRuntimePaths

    def write_balance(self, snapshot: BrokerBalanceSnapshot) -> BrokerSnapshotWriteResult:
        return self._write("balance", [snapshot], self.paths.balance_snapshots)

    def write_positions(self, snapshots: list[BrokerPositionSnapshot]) -> BrokerSnapshotWriteResult:
        return self._write("positions", snapshots, self.paths.positions_snapshots)

    def write_orders(self, snapshots: list[BrokerOrderSnapshot]) -> BrokerSnapshotWriteResult:
        return self._write("orders", snapshots, self.paths.orders_snapshots)

    def _write(self, kind: str, snapshots: list[BrokerSnapshot], directory: Path) -> BrokerSnapshotWriteResult:
        self.paths.ensure_dirs()
        batch_id = broker_snapshot_id(kind)
        data_path = directory / f"{batch_id}.json"
        manifest_path = directory / f"{batch_id}.manifest.json"
        records = [_safe_record(snapshot) for snapshot in snapshots]
        payload = sanitize_mapping(
            {
                "kind": kind,
                "batch_id": batch_id,
                "created_at": utc_now_iso(),
                "record_count": len(records),
                "records": records,
            }
        )
        manifest = sanitize_mapping(
            {
                "kind": kind,
                "batch_id": batch_id,
                "created_at": payload["created_at"],
                "record_count": len(records),
                "data_path": str(data_path),
            }
        )
        _write_json(data_path, payload)
        _write_json(manifest_path, manifest)
        return BrokerSnapshotWriteResult(kind, data_path, manifest_path, len(records))


def _safe_record(snapshot: BrokerSnapshot) -> dict[str, Any]:
    if not is_dataclass(snapshot):
        raise TypeError("snapshot must be a broker dataclass model")
    return sanitize_mapping(_jsonable(asdict(snapshot)))


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
