from ai_fund_lab_v2.runtime_v2.contracts.current_state_contracts import (
    CURRENT_STATE_CONTRACTS,
)


EXPECTED_SINGLE_WRITERS = {
    "runtime_state": "Runtime State Runtime",
    "pending_order_plan": "Pending Runtime",
    "persistent_ledger_orders": "Ledger Runtime",
    "persistent_ledger_executions": "Ledger Runtime",
    "persistent_ledger_positions": "Ledger Runtime",
    "persistent_ledger_cash_history": "Ledger Runtime",
    "persistent_ledger_events": "Ledger Runtime",
    "persistent_ledger_state": "Asset Runtime",
    "notification_delivery_ledger": "Notification Runtime",
}


def test_each_current_contract_has_exactly_one_writer():
    assert set(CURRENT_STATE_CONTRACTS) == set(EXPECTED_SINGLE_WRITERS)

    for name, contract in CURRENT_STATE_CONTRACTS.items():
        assert contract.writer_components == (EXPECTED_SINGLE_WRITERS[name],)


def test_reconcile_report_and_audit_are_not_current_writers():
    forbidden_writers = {
        "Reconciliation Runtime",
        "Report Runtime",
        "Report Builder",
        "Audit Runtime",
    }

    for contract in CURRENT_STATE_CONTRACTS.values():
        assert forbidden_writers.isdisjoint(contract.writer_components)


def test_asset_runtime_is_only_persistent_ledger_state_writer():
    contract = CURRENT_STATE_CONTRACTS["persistent_ledger_state"]

    assert contract.path_object_type == "persistent_ledger_state"
    assert contract.writer_components == ("Asset Runtime",)
    assert contract.snapshot is True
    assert contract.append_only is False


def test_ledger_runtime_is_append_only_writer():
    append_only_contracts = (
        "persistent_ledger_orders",
        "persistent_ledger_executions",
        "persistent_ledger_positions",
        "persistent_ledger_cash_history",
        "persistent_ledger_events",
    )

    for name in append_only_contracts:
        contract = CURRENT_STATE_CONTRACTS[name]
        assert contract.writer_components == ("Ledger Runtime",)
        assert contract.append_only is True
        assert contract.snapshot is False

