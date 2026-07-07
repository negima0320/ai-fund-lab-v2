from dataclasses import fields

from ai_fund_lab_v2.runtime_v2.broker_readonly.models import (
    BrokerCashSnapshot,
    BrokerExecutionSnapshot,
    BrokerOrderSnapshot,
    BrokerPositionSnapshot,
)


SNAPSHOT_TYPES = (
    BrokerOrderSnapshot,
    BrokerExecutionSnapshot,
    BrokerPositionSnapshot,
    BrokerCashSnapshot,
)

FORBIDDEN_FIELDS = {
    "raw_request",
    "raw_response",
    "secret",
    "session",
    "url",
    "account_id",
    "account_number",
    "broker_id",
    "order_id",
    "execution_id",
}


def test_snapshots_have_environment_source_as_of_review_and_production_flags():
    for snapshot_type in SNAPSHOT_TYPES:
        field_names = {field.name for field in fields(snapshot_type)}

        assert {"environment", "source", "as_of"}.issubset(field_names)
        assert "review_required" in field_names
        assert "production_equivalent" in field_names
        assert "broker_ref_hash" in field_names


def test_snapshots_do_not_have_raw_or_unhashed_broker_fields():
    for snapshot_type in SNAPSHOT_TYPES:
        field_names = {field.name for field in fields(snapshot_type)}

        assert not (field_names & FORBIDDEN_FIELDS)


def test_broker_refs_are_hash_named_fields_only():
    assert "order_ref_hash" in {field.name for field in fields(BrokerOrderSnapshot)}
    assert "execution_ref_hash" in {field.name for field in fields(BrokerExecutionSnapshot)}
    assert "position_ref_hash" in {field.name for field in fields(BrokerPositionSnapshot)}
    assert "cash_ref_hash" in {field.name for field in fields(BrokerCashSnapshot)}

