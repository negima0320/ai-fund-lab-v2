from dataclasses import replace

from ai_fund_lab_v2.runtime_v2.ledger.append import append_record
from ai_fund_lab_v2.runtime_v2.ledger.dedup import (
    compute_dedup_key,
    is_duplicate_record,
)
from ai_fund_lab_v2.runtime_v2.ledger.models import LedgerOrderRecord


def test_same_dedup_key_is_not_appended_twice():
    record = _order_record("order-1", "dedup-1")
    duplicate = replace(record, record_id="order-duplicate")

    records = append_record((record,), duplicate)

    assert records == (record,)


def test_different_dedup_key_is_appended():
    record = _order_record("order-1", "dedup-1")
    second = _order_record("order-2", "dedup-2")

    records = append_record((record,), second)

    assert records == (record, second)


def test_append_record_does_not_mutate_existing_records():
    original = (_order_record("order-1", "dedup-1"),)
    second = _order_record("order-2", "dedup-2")

    appended = append_record(original, second)

    assert original == (_order_record("order-1", "dedup-1"),)
    assert appended is not original


def test_dedup_helper_is_pure_for_same_record():
    record = _order_record("order-1", "dedup-1")

    assert compute_dedup_key(record) == compute_dedup_key(record)
    assert is_duplicate_record({"dedup-1"}, record) is True
    assert is_duplicate_record(set(), record) is False


def _order_record(record_id: str, dedup_key: str) -> LedgerOrderRecord:
    return LedgerOrderRecord(
        record_id=record_id,
        record_type="order",
        schema_version="1",
        environment="demo",
        source="submit_runtime",
        created_at="2026-07-07T00:00:00Z",
        dedup_key=dedup_key,
        order_id=record_id,
        side="BUY",
        symbol="7203",
        quantity=100,
        status="accepted",
    )

