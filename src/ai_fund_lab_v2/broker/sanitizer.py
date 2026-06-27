from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from typing import Any

REDACTION = "[REDACTED]"
SENSITIVE_KEY_PARTS = (
    "sauthid",
    "auth_id",
    "authid",
    "request_url",
    "requesturl",
    "session_url",
    "sessionurl",
    "surlrequest",
    "surlmaster",
    "surlprice",
    "surlevent",
    "surleventwebsocket",
    "websocket_url",
    "websocketurl",
    "private_key",
    "privatekey",
    "account_id",
    "accountid",
    "password",
    "token",
    "cookie",
    "second_password",
    "secondpassword",
    "ssecondpassword",
)

URL_VALUE_PATTERN = re.compile(r"https?://[^\s\"'<>]+")
SENSITIVE_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(sauthid|auth[_ -]?id|account[_ -]?id|password|token|cookie|second[_ -]?password)\s*[:=]\s*[^\s,;\"'<>]+"
)


def sanitize_text(text: str) -> str:
    without_urls = URL_VALUE_PATTERN.sub(REDACTION, text)
    return SENSITIVE_ASSIGNMENT_PATTERN.sub(lambda match: f"{match.group(1)}={REDACTION}", without_urls)


def sanitize_mapping(data: Mapping[str, Any]) -> dict[str, Any]:
    return {key: _sanitize_value(key, value) for key, value in data.items()}


def hash_account_id(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        return ""
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def _sanitize_value(key: str, value: Any) -> Any:
    normalized_key = _normalize_key(key)
    if any(part in normalized_key for part in SENSITIVE_KEY_PARTS):
        if isinstance(value, bool):
            return value
        return REDACTION
    if isinstance(value, Mapping):
        return sanitize_mapping(value)
    if isinstance(value, list):
        return [_sanitize_sequence_value(item) for item in value]
    if isinstance(value, str):
        return sanitize_text(value)
    return value


def _sanitize_sequence_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return sanitize_mapping(value)
    if isinstance(value, list):
        return [_sanitize_sequence_value(item) for item in value]
    if isinstance(value, str):
        return sanitize_text(value)
    return value


def _normalize_key(key: str) -> str:
    return key.replace("-", "_").replace(" ", "_").lower()
