from __future__ import annotations

import json
import re
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.broker.sanitizer import REDACTION, sanitize_mapping, sanitize_text
from ai_fund_lab_v2.safety_phase11.models import SafetyEvent, utc_now_iso

PHASE11_FORBIDDEN_KEY_PARTS = (
    "raw_response",
    "raw_request",
    "request_body",
    "response_body",
    "account_id",
    "accountid",
    "order_id",
    "orderid",
    "order_number",
    "ordernumber",
    "execution_id",
    "executionid",
    "auth_id",
    "authid",
    "private_key",
    "privatekey",
    "virtual_url",
    "second_password",
    "secondpassword",
    "ssecondpassword",
)

PHASE11_FORBIDDEN_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(raw[_ -]?request|raw[_ -]?response|account[_ -]?id|order[_ -]?(?:id|number)|execution[_ -]?id|auth[_ -]?id|private[_ -]?key|virtual[_ -]?url|second[_ -]?password)\s*[:=]\s*[^\s,;\"'<>]+"
)


def write_safety_events(events: tuple[SafetyEvent, ...], runtime_dir: Path | str = ".runtime") -> list[Path]:
    directory = Path(runtime_dir) / "safety" / "phase11" / "events"
    paths: list[Path] = []
    for event in events:
        path = directory / f"{event.event_id}_{_file_timestamp()}.json"
        _write_json(path, safe_payload(event))
        paths.append(path)
    return paths


def safe_payload(value: Any) -> dict[str, Any]:
    if not is_dataclass(value):
        raise TypeError("phase11 safety writer expects dataclass payload")
    return _phase11_sanitize(sanitize_mapping(_jsonable(asdict(value))))


def _phase11_sanitize(value: Any, key: str = "") -> Any:
    normalized_key = key.replace("-", "_").replace(" ", "_").lower()
    if any(part in normalized_key for part in PHASE11_FORBIDDEN_KEY_PARTS):
        if isinstance(value, bool):
            return value
        return REDACTION
    if isinstance(value, dict):
        return {item_key: _phase11_sanitize(item_value, item_key) for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [_phase11_sanitize(item) for item in value]
    if isinstance(value, str):
        return PHASE11_FORBIDDEN_ASSIGNMENT_PATTERN.sub(lambda match: f"{match.group(1)}={REDACTION}", sanitize_text(value))
    return value


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
