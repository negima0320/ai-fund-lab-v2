from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ManifestEntry:
    fetched_at: str
    endpoint: str
    target_date: str | None
    from_date: str | None
    to_date: str | None
    record_count: int
    storage_format: str
    storage_path: str
    status: str
    validation_status: str
    schema_version: int | None
    diff_summary: dict[str, Any]
    request_params: dict[str, Any]
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def append_manifest(manifest_path: Path, entry: ManifestEntry) -> None:
    append_manifest_record(manifest_path, entry.to_dict())


def append_manifest_record(manifest_path: Path, record: dict[str, Any]) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def read_manifest(manifest_path: Path) -> list[dict[str, Any]]:
    if not manifest_path.exists():
        return []
    with manifest_path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def manifest_path(raw_data_path: Path) -> Path:
    return raw_data_path / "jquants" / "manifest.jsonl"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sanitize_request_params(params: dict[str, Any]) -> dict[str, Any]:
    blocked = {"api_key", "token", "authorization", "x-api-key", "password", "id_token", "refresh_token"}
    return {key: value for key, value in params.items() if key.lower() not in blocked}
