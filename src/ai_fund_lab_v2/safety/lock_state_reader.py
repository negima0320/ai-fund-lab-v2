from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.broker.sanitizer import sanitize_mapping, sanitize_text


class LockStateReadError(RuntimeError):
    """Raised when safety lock state history cannot be read."""


def list_lock_states(runtime_dir: Path | str = ".runtime") -> list[Path]:
    directory = Path(runtime_dir) / "safety" / "locks"
    if not directory.exists():
        return []
    return sorted((path for path in directory.glob("*.json") if path.is_file()), key=lambda path: (path.stat().st_mtime, path.name))


def load_latest_lock_state(runtime_dir: Path | str = ".runtime") -> dict[str, Any] | None:
    states = list_lock_states(runtime_dir)
    if not states:
        return None
    latest = states[-1]
    try:
        payload = json.loads(latest.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LockStateReadError(f"Safety lock state JSON is invalid: {sanitize_text(str(latest))}") from exc
    if not isinstance(payload, dict):
        raise LockStateReadError(f"Safety lock state payload must be an object: {sanitize_text(str(latest))}")
    sanitized = sanitize_mapping(payload)
    sanitized["_state_path"] = str(latest)
    return sanitized
