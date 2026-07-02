from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.broker.sanitizer import sanitize_mapping


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class OperationPaths:
    root: Path = Path(".runtime/operations")
    market_refresh: str = "market_refresh"
    feature_refresh: str = "feature_refresh"
    data_quality: str = "data_quality"
    safety_monitor: str = "safety_monitor"
    safety_events: str = "safety_events"
    human_review: str = "human_review"
    missed_jobs: str = "missed_jobs"
    positions: str = "positions"

    def __post_init__(self) -> None:
        object.__setattr__(self, "root", Path(self.root))

    def dir(self, name: str) -> Path:
        path = self.root / name
        path.mkdir(parents=True, exist_ok=True)
        return path

    def dated(self, name: str, trade_date: str, filename: str) -> Path:
        path = self.root / name / trade_date
        path.mkdir(parents=True, exist_ok=True)
        return path / filename

    def latest(self, name: str, filename: str) -> Path:
        path = self.root / name
        candidates = sorted(path.glob(f"*/{filename}")) if path.exists() else []
        if not candidates:
            raise FileNotFoundError(f"operation artifact not found: {name}/{filename}")
        return candidates[-1]

    def required_roots(self) -> tuple[str, ...]:
        return (
            self.market_refresh,
            self.feature_refresh,
            self.data_quality,
            self.safety_monitor,
            self.safety_events,
            self.human_review,
            self.missed_jobs,
            self.positions,
        )


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    sanitized = sanitize_mapping(payload)
    path.write_text(json.dumps(sanitized, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def stable_hash(payload: Any) -> str:
    import hashlib

    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True, default=str).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def jsonable(value: Any) -> Any:
    from decimal import Decimal
    from enum import Enum

    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return [jsonable(item) for item in value]
    if isinstance(value, list):
        return [jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    return value
