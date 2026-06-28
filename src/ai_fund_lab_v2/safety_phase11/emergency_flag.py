from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.safety_phase11.event_writer import _phase11_sanitize, _write_json
from ai_fund_lab_v2.safety_phase11.models import safety_id, utc_now_iso


DEFAULT_MANUAL_EMERGENCY_FLAG_PATH = Path(".runtime") / "safety" / "phase11" / "state" / "manual_emergency_stop.json"


@dataclass(frozen=True)
class ManualEmergencyFlag:
    created_by: str
    reason: str
    active: bool = True
    created_at: str = field(default_factory=utc_now_iso)
    flag_id: str = field(default_factory=lambda: safety_id("manual_emergency_stop"))
    raw_response_saved: bool = False
    auto_trade_executed: bool = False


def create_manual_emergency_flag(
    *,
    created_by: str,
    reason: str,
    runtime_dir: Path | str = ".runtime",
) -> Path:
    flag = ManualEmergencyFlag(created_by=created_by, reason=reason, active=True)
    path = _flag_path(runtime_dir)
    _write_json(path, _safe_flag_payload(flag))
    return path


def read_manual_emergency_flag(runtime_dir: Path | str = ".runtime") -> dict[str, Any]:
    path = _flag_path(runtime_dir)
    if not path.exists():
        return {"active": False, "source": "missing", "path": str(path)}
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["path"] = str(path)
    return payload


def clear_manual_emergency_flag_candidate(
    *,
    cleared_by: str,
    reason: str,
    runtime_dir: Path | str = ".runtime",
) -> Path:
    existing = read_manual_emergency_flag(runtime_dir)
    payload = {
        **{key: value for key, value in existing.items() if key != "path"},
        "active": False,
        "clear_candidate_created_at": utc_now_iso(),
        "cleared_by": cleared_by,
        "clear_reason": reason,
        "auto_recovery_executed": False,
        "raw_response_saved": False,
        "auto_trade_executed": False,
    }
    path = _flag_path(runtime_dir)
    _write_json(path, _phase11_sanitize(payload))
    return path


def _safe_flag_payload(flag: ManualEmergencyFlag) -> dict[str, Any]:
    return _phase11_sanitize(asdict(flag))


def _flag_path(runtime_dir: Path | str) -> Path:
    return Path(runtime_dir) / "safety" / "phase11" / "state" / "manual_emergency_stop.json"
