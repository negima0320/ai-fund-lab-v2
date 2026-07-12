"""Authority metadata for Runtime v2 Current state."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


EXCLUDED_CURRENT_HASH_FIELDS = {
    "current_hash",
    "current_version",
    "runtime_state_version",
    "current_pointer",
    "execution_reference",
    "execution_references",
}


def canonical_current_payload(current: dict[str, Any]) -> dict[str, Any]:
    """Return the semantic Current payload used for Current authority hashing."""

    return {
        key: value
        for key, value in current.items()
        if key not in EXCLUDED_CURRENT_HASH_FIELDS and not key.endswith("_path")
    }


def canonical_current_hash(current: dict[str, Any]) -> str:
    raw = json.dumps(
        canonical_current_payload(current),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def current_version_from_hash(current_hash: str) -> str:
    return "current-" + current_hash.split(":", 1)[-1][:16]


def current_authority_metadata(current: dict[str, Any]) -> dict[str, str]:
    current_hash = canonical_current_hash(current)
    return {
        "current_hash": current_hash,
        "current_version": current_version_from_hash(current_hash),
    }


def read_current_authority_metadata(path: Path | str) -> dict[str, str]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("current payload must be a JSON object")
    return current_authority_metadata(payload)
