from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.broker.sanitizer import sanitize_mapping
from ai_fund_lab_v2.safety.models import SafetyReport, TradingLock, utc_now_iso


def write_safety_audit_log(
    *,
    report: SafetyReport,
    lock: TradingLock,
    report_path: Path,
    lock_path: Path,
    runtime_dir: Path | str = ".runtime",
) -> Path:
    directory = Path(runtime_dir) / "safety" / "audit"
    path = directory / f"safety_audit_{_file_timestamp()}.json"
    payload = sanitize_mapping(
        {
            "status": report.status.value,
            "issue_count": report.issue_count,
            "trading_locked": report.trading_locked,
            "checked_at": report.checked_at,
            "broker_snapshot_id": report.broker_snapshot_id,
            "report_path": str(report_path),
            "lock_path": str(lock_path),
            "lock_reason": lock.reason,
        }
    )
    directory.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _file_timestamp() -> str:
    return utc_now_iso().replace(":", "").replace("-", "").replace(".", "_")
