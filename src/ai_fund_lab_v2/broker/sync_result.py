from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

from ai_fund_lab_v2.broker.models import utc_now_iso


def broker_sync_id() -> str:
    return f"sync_{uuid4().hex}"


@dataclass(frozen=True)
class BrokerSyncResult:
    broker: str = "tachibana"
    source: str = "mock"
    started_at: str = field(default_factory=utc_now_iso)
    finished_at: str = ""
    status: str = "success"
    balance_snapshot_count: int = 0
    position_snapshot_count: int = 0
    order_snapshot_count: int = 0
    snapshot_paths: tuple[str, ...] = ()
    manifest_paths: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    sync_id: str = field(default_factory=broker_sync_id)

    def to_dict(self) -> dict[str, object]:
        return {
            "sync_id": self.sync_id,
            "broker": self.broker,
            "source": self.source,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "status": self.status,
            "balance_snapshot_count": self.balance_snapshot_count,
            "position_snapshot_count": self.position_snapshot_count,
            "order_snapshot_count": self.order_snapshot_count,
            "snapshot_paths": list(self.snapshot_paths),
            "manifest_paths": list(self.manifest_paths),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }
