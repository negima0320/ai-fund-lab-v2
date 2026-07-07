from collections import Counter

from ai_fund_lab_v2.runtime_v2.contracts.current_state_contracts import (
    CURRENT_STATE_CONTRACTS,
)


def test_no_current_writer_conflict_by_contract_name():
    writer_count_by_current = {
        name: len(contract.writer_components)
        for name, contract in CURRENT_STATE_CONTRACTS.items()
    }

    assert all(count == 1 for count in writer_count_by_current.values())


def test_no_duplicate_current_path_owner_contracts():
    path_object_counts = Counter(
        contract.path_object_type for contract in CURRENT_STATE_CONTRACTS.values()
    )

    assert all(count == 1 for count in path_object_counts.values())


def test_writer_owner_matches_single_writer():
    for contract in CURRENT_STATE_CONTRACTS.values():
        assert contract.owner_component == contract.writer_components[0]


def test_reconciliation_runtime_is_reader_or_evidence_only_not_writer():
    writer_contracts = [
        contract.name
        for contract in CURRENT_STATE_CONTRACTS.values()
        if "Reconciliation Runtime" in contract.writer_components
    ]

    assert writer_contracts == []

