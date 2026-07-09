"""Runtime State writer for Runtime v2 fixed Current paths."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


def write_runtime_state(path: Path, payload: Mapping[str, Any]) -> Path:
    if path is None:
        raise ValueError("path is required")
    if _is_mode_rooted_runtime_path(path):
        raise ValueError("Runtime state writer does not write mode-rooted runtime paths")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), sort_keys=True), encoding="utf-8")
    return path


def _is_mode_rooted_runtime_path(path: Path) -> bool:
    parts = path.parts
    runtime_modes = {"production", "demo", "simulation", "backtest"}
    return any(
        part == ".runtime"
        and index + 1 < len(parts)
        and parts[index + 1] in runtime_modes
        for index, part in enumerate(parts)
    )
