"""Persistent Ledger JSONL writers for Runtime v2 Current paths."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable


def ledger_record_to_payload(record: object) -> dict[str, Any]:
    payload = asdict(record)
    payload["ledger_record_id"] = payload["record_id"]
    payload["recorded_at"] = payload["created_at"]
    if "cash_key" in payload and "cash_snapshot_key" not in payload:
        payload["cash_snapshot_key"] = payload["cash_key"]
    return payload


def write_ledger_records(path: Path, records: Iterable[object]) -> Path:
    if path is None:
        raise ValueError("path is required")
    if _is_mode_rooted_runtime_path(path):
        raise ValueError("Ledger writer does not write mode-rooted runtime paths")
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(ledger_record_to_payload(record), sort_keys=True)
        for record in records
    ]
    payload = "\n".join(lines)
    if payload:
        payload += "\n"
    path.write_text(payload, encoding="utf-8")
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
