"""JSON boundary helpers for Runtime v2 evidence artifacts."""

from __future__ import annotations

import json
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any


class JsonSerializationContractError(TypeError):
    """Raised when a Runtime evidence payload contains a non-contract type."""

    def __init__(self, *, field_path: str, python_type: str, value_repr: str) -> None:
        self.field_path = field_path
        self.python_type = python_type
        self.value_repr = value_repr
        super().__init__(f"JSON contract violation at {field_path}: {python_type}")

    def to_payload(self) -> dict[str, str]:
        return {
            "error_class": "RUNTIME_EVIDENCE_SERIALIZATION_ERROR",
            "error_type": type(self).__name__,
            "field_path": self.field_path,
            "python_type": self.python_type,
            "value_repr": self.value_repr,
        }


def to_json_safe(value: Any, *, field_path: str = "$") -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Enum):
        return to_json_safe(value.value, field_path=field_path)
    if isinstance(value, (tuple, list)):
        return [to_json_safe(item, field_path=f"{field_path}[{index}]") for index, item in enumerate(value)]
    if isinstance(value, set):
        safe_items = [to_json_safe(item, field_path=f"{field_path}[]") for item in value]
        return sorted(safe_items, key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True))
    if isinstance(value, dict):
        payload: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise JsonSerializationContractError(
                    field_path=f"{field_path}.{key!r}",
                    python_type=f"{type(key).__name__}_key",
                    value_repr=repr(key),
                )
            payload[key] = to_json_safe(item, field_path=f"{field_path}.{key}")
        return payload
    raise JsonSerializationContractError(
        field_path=field_path,
        python_type=type(value).__name__,
        value_repr=repr(value),
    )


def dumps_json_safe(payload: Any, **kwargs: Any) -> str:
    return json.dumps(to_json_safe(payload), **kwargs)
