"""Dedup helpers for Runtime v2 append-only ledger records."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass


def compute_dedup_key(record: object) -> str:
    """Compute or return a stable dedup key for a ledger record."""

    existing_key = getattr(record, "dedup_key", None)
    if existing_key:
        return str(existing_key)
    payload = _record_payload(record)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def is_duplicate_record(existing_keys: set[str], record: object) -> bool:
    """Return whether a record's dedup key already exists."""

    return compute_dedup_key(record) in existing_keys


def _record_payload(record: object):
    if is_dataclass(record):
        return asdict(record)
    if isinstance(record, dict):
        return record
    return {"repr": repr(record)}

