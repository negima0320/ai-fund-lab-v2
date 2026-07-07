"""Append-only helpers for Runtime v2 ledger records."""

from __future__ import annotations

from ai_fund_lab_v2.runtime_v2.ledger.dedup import (
    compute_dedup_key,
    is_duplicate_record,
)


def append_record(records: tuple[object, ...], record: object) -> tuple[object, ...]:
    """Append a record unless its dedup key already exists."""

    existing_keys = {compute_dedup_key(existing) for existing in records}
    if is_duplicate_record(existing_keys, record):
        return records
    return (*records, record)

