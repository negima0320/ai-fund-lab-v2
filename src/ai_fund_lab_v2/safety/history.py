from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.broker.sanitizer import sanitize_mapping


def list_safety_reports(runtime_dir: Path | str = ".runtime") -> list[Path]:
    return _list_json_files(Path(runtime_dir) / "safety" / "reports")


def list_trading_locks(runtime_dir: Path | str = ".runtime") -> list[Path]:
    return _list_json_files(Path(runtime_dir) / "safety" / "locks")


def list_safety_audits(runtime_dir: Path | str = ".runtime") -> list[Path]:
    return _list_json_files(Path(runtime_dir) / "safety" / "audit")


def load_latest_safety_report(runtime_dir: Path | str = ".runtime") -> dict[str, Any] | None:
    reports = list_safety_reports(runtime_dir)
    if not reports:
        return None
    payload = json.loads(reports[-1].read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return None
    return sanitize_mapping(payload)


def _list_json_files(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(path for path in directory.glob("*.json") if path.is_file())
