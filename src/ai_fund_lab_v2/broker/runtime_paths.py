from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ai_fund_lab_v2.runtime import RuntimePaths


@dataclass(frozen=True)
class BrokerRuntimePaths:
    runtime_paths: RuntimePaths

    @property
    def broker_root(self) -> Path:
        return self.runtime_paths.runtime_dir / "broker"

    @property
    def snapshots(self) -> Path:
        return self.broker_root / "snapshots"

    @property
    def balance_snapshots(self) -> Path:
        return self.snapshots / "balance"

    @property
    def positions_snapshots(self) -> Path:
        return self.snapshots / "positions"

    @property
    def orders_snapshots(self) -> Path:
        return self.snapshots / "orders"

    @property
    def logs(self) -> Path:
        return self.broker_root / "logs"

    def iter_dirs(self) -> tuple[Path, ...]:
        return (
            self.broker_root,
            self.snapshots,
            self.balance_snapshots,
            self.positions_snapshots,
            self.orders_snapshots,
            self.logs,
        )

    def ensure_dirs(self) -> None:
        for path in self.iter_dirs():
            path.mkdir(parents=True, exist_ok=True)
