from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.broker.sanitizer import sanitize_mapping
from ai_fund_lab_v2.safety.models import utc_now_iso
from ai_fund_lab_v2.safety.unlock_models import UnlockApproval, UnlockAuditRecord, UnlockRequest


def write_unlock_request(request: UnlockRequest, runtime_dir: Path | str = ".runtime") -> Path:
    path = Path(runtime_dir) / "safety" / "unlock" / "requests" / f"{request.request_id}_{_file_timestamp()}.json"
    _write_json(path, _safe_payload(request))
    return path


def write_unlock_approval(approval: UnlockApproval, runtime_dir: Path | str = ".runtime") -> Path:
    path = Path(runtime_dir) / "safety" / "unlock" / "approvals" / f"{approval.request_id}_{_file_timestamp()}.json"
    _write_json(path, _safe_payload(approval))
    return path


def write_unlock_audit(record: UnlockAuditRecord, runtime_dir: Path | str = ".runtime") -> Path:
    path = Path(runtime_dir) / "safety" / "unlock" / "audit" / f"{record.request_id}_{_file_timestamp()}.json"
    _write_json(path, _safe_payload(record))
    return path


def _safe_payload(value: Any) -> dict[str, Any]:
    if not is_dataclass(value):
        raise TypeError("unlock writer expects a dataclass payload")
    return sanitize_mapping(_jsonable(asdict(value)))


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _file_timestamp() -> str:
    return utc_now_iso().replace(":", "").replace("-", "").replace(".", "_")
