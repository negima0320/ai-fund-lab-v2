from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.broker.sanitizer import sanitize_mapping
from ai_fund_lab_v2.safety.lock_apply_models import UnlockApplyResult
from ai_fund_lab_v2.safety.models import utc_now_iso


def write_unlock_apply_audit(
    result: UnlockApplyResult,
    runtime_dir: Path | str = ".runtime",
) -> Path:
    path = Path(runtime_dir) / "safety" / "unlock" / "apply_audit" / f"unlock_apply_{_request_id(result)}_{_file_timestamp()}.json"
    _write_json(path, _safe_payload(result))
    return path


def _safe_payload(value: Any) -> dict[str, Any]:
    if not is_dataclass(value):
        raise TypeError("unlock apply audit writer expects a dataclass payload")
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


def _request_id(result: UnlockApplyResult) -> str:
    return result.approval_request_id or "none"


def _file_timestamp() -> str:
    return utc_now_iso().replace(":", "").replace("-", "").replace(".", "_")
