from dataclasses import fields

from ai_fund_lab_v2.runtime_v2.ledger.models import (
    LedgerCashRecord,
    LedgerEventRecord,
    LedgerExecutionRecord,
    LedgerOrderRecord,
    LedgerPositionRecord,
)


LEDGER_RECORD_TYPES = (
    LedgerOrderRecord,
    LedgerExecutionRecord,
    LedgerPositionRecord,
    LedgerCashRecord,
    LedgerEventRecord,
)

COMMON_FIELDS = {
    "record_id",
    "record_type",
    "schema_version",
    "environment",
    "source",
    "created_at",
    "dedup_key",
    "review_required",
    "production_equivalent",
}

FORBIDDEN_RAW_FIELDS = {
    "raw_request",
    "raw_response",
    "secret",
    "session",
    "url",
    "account_id",
    "password",
    "token",
}


def test_ledger_records_have_required_common_fields_and_dedup_key():
    for record_type in LEDGER_RECORD_TYPES:
        field_names = {field.name for field in fields(record_type)}

        assert COMMON_FIELDS.issubset(field_names)
        assert "dedup_key" in field_names


def test_production_equivalent_false_is_review_candidate():
    record = LedgerPositionRecord(
        record_id="pos-1",
        record_type="position",
        schema_version="1",
        environment="demo",
        source="broker_orders_fallback",
        created_at="2026-07-07T00:00:00Z",
        dedup_key="pos-1",
        production_equivalent=False,
        position_key="7203",
        symbol="7203",
    )

    assert record.effective_review_required is True


def test_ledger_records_do_not_define_raw_request_response_or_secret_fields():
    for record_type in LEDGER_RECORD_TYPES:
        field_names = {field.name for field in fields(record_type)}

        assert not (field_names & FORBIDDEN_RAW_FIELDS)

