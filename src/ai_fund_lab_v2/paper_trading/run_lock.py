from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.broker.models import utc_now_iso


class RunLockError(RuntimeError):
    pass


@dataclass(frozen=True)
class RunLock:
    pid: int
    run_id: str
    started_at: str
    date: str
    mode: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def lock_path(operation_root: Path | str = ".runtime/phase9") -> Path:
    return Path(operation_root) / "locks" / "daily_operation.lock"


def acquire_run_lock(
    *,
    run_id: str,
    run_date: str,
    mode: str,
    operation_root: Path | str = ".runtime/phase9",
    force_unlock: bool = False,
) -> RunLock:
    path = lock_path(operation_root)
    if path.exists():
        if not force_unlock:
            raise RunLockError(f"Daily operation lock already exists: {path}")
        path.unlink()
    lock = RunLock(pid=os.getpid(), run_id=run_id, started_at=utc_now_iso(), date=run_date, mode=mode)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(lock.to_dict(), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return lock


def read_run_lock(operation_root: Path | str = ".runtime/phase9") -> RunLock | None:
    path = lock_path(operation_root)
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return RunLock(
        pid=int(payload.get("pid") or 0),
        run_id=str(payload.get("run_id") or ""),
        started_at=str(payload.get("started_at") or ""),
        date=str(payload.get("date") or ""),
        mode=str(payload.get("mode") or ""),
    )


def release_run_lock(*, run_id: str, operation_root: Path | str = ".runtime/phase9") -> bool:
    path = lock_path(operation_root)
    if not path.exists():
        return False
    current = read_run_lock(operation_root)
    if current and current.run_id and current.run_id != run_id:
        raise RunLockError("Refusing to release a lock owned by another run_id.")
    path.unlink()
    return True


def force_release_run_lock(operation_root: Path | str = ".runtime/phase9") -> bool:
    path = lock_path(operation_root)
    if not path.exists():
        return False
    path.unlink()
    return True

