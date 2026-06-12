from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.broker.sanitizer import sanitize_text
from ai_fund_lab_v2.safety.models import SafetyStatus
from ai_fund_lab_v2.safety.unlock_models import UnlockApproval


class UnlockReadError(RuntimeError):
    """Raised when unlock approval history cannot be read."""


def list_unlock_approvals(runtime_dir: Path | str = ".runtime") -> list[Path]:
    directory = Path(runtime_dir) / "safety" / "unlock" / "approvals"
    if not directory.exists():
        return []
    return sorted(path for path in directory.glob("*.json") if path.is_file())


def load_latest_unlock_approval(runtime_dir: Path | str = ".runtime") -> UnlockApproval | None:
    approvals = list_unlock_approvals(runtime_dir)
    if not approvals:
        return None
    return _load_unlock_approval(approvals[-1])


def _load_unlock_approval(path: Path) -> UnlockApproval:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise UnlockReadError(f"Unlock approval JSON is invalid: {sanitize_text(str(path))}") from exc
    if not isinstance(payload, dict):
        raise UnlockReadError(f"Unlock approval payload must be an object: {sanitize_text(str(path))}")
    return _approval_from_payload(payload)


def _approval_from_payload(payload: dict[str, Any]) -> UnlockApproval:
    try:
        return UnlockApproval(
            request_id=str(payload["request_id"]),
            approved_by=str(payload["approved_by"]),
            approval_reason=str(payload["approval_reason"]),
            reconciliation_status=SafetyStatus(str(payload["reconciliation_status"])),
            safety_report_path=payload.get("safety_report_path"),
            approved_at=str(payload["approved_at"]),
        )
    except KeyError as exc:
        raise UnlockReadError(f"Unlock approval is missing required field: {exc.args[0]}") from exc
    except ValueError as exc:
        raise UnlockReadError("Unlock approval has invalid reconciliation_status.") from exc
