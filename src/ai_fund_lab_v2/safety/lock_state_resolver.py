from __future__ import annotations

from pathlib import Path
from typing import Any

from ai_fund_lab_v2.safety.lock_state_reader import LockStateReadError, load_latest_lock_state


def resolve_current_lock_state(
    runtime_dir: Path | str = ".runtime",
) -> dict[str, Any]:
    try:
        latest = load_latest_lock_state(runtime_dir)
    except LockStateReadError as exc:
        return {
            "is_locked": True,
            "source": "corrupt",
            "status": "LOCKED",
            "message": str(exc),
            "state_path": None,
        }
    if latest is None:
        return {
            "is_locked": False,
            "source": "none",
            "status": "UNLOCKED",
            "message": "no lock state found",
            "state_path": None,
        }
    state_path = latest.get("_state_path")
    if "is_locked" in latest:
        locked = bool(latest.get("is_locked"))
        return {
            "is_locked": locked,
            "source": "trading_lock",
            "status": str(latest.get("status") or ("LOCKED" if locked else "UNLOCKED")),
            "message": str(latest.get("reason") or ""),
            "state_path": state_path,
        }
    if "applied" in latest:
        applied = bool(latest.get("applied"))
        return {
            "is_locked": not applied,
            "source": "unlock_apply",
            "status": str(latest.get("status") or ("APPLIED" if applied else "REJECTED")),
            "message": str(latest.get("message") or ""),
            "state_path": state_path,
        }
    return {
        "is_locked": True,
        "source": "unknown",
        "status": "LOCKED",
        "message": "unknown lock state shape",
        "state_path": state_path,
    }
