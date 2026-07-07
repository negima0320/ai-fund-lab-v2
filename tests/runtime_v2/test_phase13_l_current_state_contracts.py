from ai_fund_lab_v2.runtime_v2.contracts.current_state_contracts import (
    CURRENT_STATE_CONTRACTS,
)
from ai_fund_lab_v2.runtime_v2.contracts.validation import validate_required_fields


EXPECTED_CURRENT_OBJECTS = {
    "runtime_state",
    "pending_order_plan",
    "persistent_ledger_state",
    "persistent_ledger_orders",
    "persistent_ledger_executions",
    "persistent_ledger_positions",
    "persistent_ledger_cash_history",
    "persistent_ledger_events",
    "notification_delivery_ledger",
}


def test_nine_current_object_contracts_are_defined():
    assert set(CURRENT_STATE_CONTRACTS) == EXPECTED_CURRENT_OBJECTS


def test_contract_file_kind_owner_writers_readers_and_lifecycle_are_defined():
    for object_type, contract in CURRENT_STATE_CONTRACTS.items():
        assert contract.name == object_type
        assert contract.path_object_type == object_type
        assert contract.file_kind in {"json", "jsonl"}
        assert contract.owner_component
        assert contract.writer_components
        assert contract.reader_components
        assert isinstance(contract.snapshot, bool)
        assert isinstance(contract.append_only, bool)
        assert contract.snapshot != contract.append_only


def test_snapshot_and_append_only_match_file_kind():
    for contract in CURRENT_STATE_CONTRACTS.values():
        if contract.file_kind == "json":
            assert contract.snapshot is True
            assert contract.append_only is False
        if contract.file_kind == "jsonl":
            assert contract.snapshot is False
            assert contract.append_only is True


def test_validate_required_fields_catches_missing_required_fields():
    result = validate_required_fields(
        {"schema_version": "1"},
        ("schema_version", "state", "updated_at"),
    )

    assert result.ok is False
    assert "missing required field: state" in result.errors
    assert "missing required field: updated_at" in result.errors
    assert result.state == "INVALID"

