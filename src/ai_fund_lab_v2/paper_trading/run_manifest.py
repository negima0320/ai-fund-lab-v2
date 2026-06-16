from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from ai_fund_lab_v2.broker.models import utc_now_iso
from ai_fund_lab_v2.broker.sanitizer import sanitize_mapping


def daily_run_id() -> str:
    return f"phase9_run_{uuid4().hex}"


@dataclass(frozen=True)
class DailyRunManifest:
    run_date: str
    data_until: str
    train_until: str
    decision_for: str
    virtual_order_date: str
    virtual_execution_date: str
    safety_status: str
    human_review_status: str
    report_status: str
    warnings: tuple[str, ...] = ()
    blocked_reasons: tuple[str, ...] = ()
    run_id: str = field(default_factory=daily_run_id)
    created_at: str = field(default_factory=utc_now_iso)
    schema_version: str = "phase9.daily_run_manifest.v1"
    no_live_order_confirmed: bool = True
    broker_order_api_called: bool = False

    def __post_init__(self) -> None:
        required = {
            "run_date": self.run_date,
            "data_until": self.data_until,
            "train_until": self.train_until,
            "decision_for": self.decision_for,
            "virtual_order_date": self.virtual_order_date,
            "virtual_execution_date": self.virtual_execution_date,
            "safety_status": self.safety_status,
            "human_review_status": self.human_review_status,
            "report_status": self.report_status,
            "run_id": self.run_id,
        }
        missing = sorted(key for key, value in required.items() if not str(value or "").strip())
        if missing:
            raise ValueError(f"DailyRunManifest missing required fields: {missing}")
        if not self.no_live_order_confirmed:
            raise ValueError("Phase9 daily run manifest must confirm no live order.")
        if self.broker_order_api_called:
            raise ValueError("Phase9 daily run manifest must not call broker order APIs.")

    def to_dict(self) -> dict[str, Any]:
        return sanitize_mapping(asdict(self))


def daily_run_manifest_path(manifest: DailyRunManifest, runtime_dir: Path | str = ".runtime") -> Path:
    return Path(runtime_dir) / "phase9" / "daily_runs" / manifest.run_date / "run_manifest.json"


def write_daily_run_manifest(manifest: DailyRunManifest, runtime_dir: Path | str = ".runtime") -> Path:
    path = daily_run_manifest_path(manifest, runtime_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest.to_dict(), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_daily_run_manifest(path: Path | str) -> DailyRunManifest:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Daily run manifest must be a JSON object.")
    return DailyRunManifest(
        run_id=str(payload.get("run_id") or ""),
        run_date=str(payload.get("run_date") or ""),
        data_until=str(payload.get("data_until") or ""),
        train_until=str(payload.get("train_until") or ""),
        decision_for=str(payload.get("decision_for") or ""),
        virtual_order_date=str(payload.get("virtual_order_date") or ""),
        virtual_execution_date=str(payload.get("virtual_execution_date") or ""),
        safety_status=str(payload.get("safety_status") or ""),
        human_review_status=str(payload.get("human_review_status") or ""),
        report_status=str(payload.get("report_status") or ""),
        warnings=tuple(str(item) for item in payload.get("warnings", [])),
        blocked_reasons=tuple(str(item) for item in payload.get("blocked_reasons", [])),
        created_at=str(payload.get("created_at") or utc_now_iso()),
        schema_version=str(payload.get("schema_version") or "phase9.daily_run_manifest.v1"),
        no_live_order_confirmed=bool(payload.get("no_live_order_confirmed", True)),
        broker_order_api_called=bool(payload.get("broker_order_api_called", False)),
    )

