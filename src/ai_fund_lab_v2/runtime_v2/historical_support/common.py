"""Shared read-only helpers for historical Runtime support evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_json_semantic(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def file_ref(path: Path, *, root: Path | None = None) -> dict[str, Any]:
    resolved = path
    rel = str(resolved.relative_to(root)) if root is not None and resolved.is_relative_to(root) else str(resolved)
    if not resolved.exists():
        return {"path": rel, "exists": False, "sha256": "", "size": 0}
    if resolved.is_dir():
        return {
            "path": rel,
            "exists": True,
            "kind": "directory",
            "file_count": sum(1 for child in resolved.rglob("*") if child.is_file()),
            "sha256": directory_hash(resolved),
        }
    return {
        "path": rel,
        "exists": True,
        "kind": "file",
        "size": resolved.stat().st_size,
        "sha256": sha256_file(resolved),
    }


def directory_hash(path: Path) -> str:
    entries: list[dict[str, Any]] = []
    for child in sorted(path.rglob("*")):
        if not child.is_file():
            continue
        entries.append(
            {
                "path": str(child.relative_to(path)),
                "size": child.stat().st_size,
                "sha256": sha256_file(child),
            }
        )
    return sha256_json_semantic(entries)


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload
