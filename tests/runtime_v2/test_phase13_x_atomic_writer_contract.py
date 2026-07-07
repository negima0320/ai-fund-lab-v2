from pathlib import Path

from ai_fund_lab_v2.runtime_v2.contracts.current_state_contracts import (
    CURRENT_STATE_CONTRACTS,
)


RUNTIME_ROOT = Path("src/ai_fund_lab_v2/runtime_v2")


def test_atomic_current_update_order_is_represented_by_writer_roles():
    assert CURRENT_STATE_CONTRACTS["persistent_ledger_orders"].writer_components == (
        "Ledger Runtime",
    )
    assert CURRENT_STATE_CONTRACTS["persistent_ledger_executions"].writer_components == (
        "Ledger Runtime",
    )
    assert CURRENT_STATE_CONTRACTS["persistent_ledger_positions"].writer_components == (
        "Ledger Runtime",
    )
    assert CURRENT_STATE_CONTRACTS["persistent_ledger_cash_history"].writer_components == (
        "Ledger Runtime",
    )
    assert CURRENT_STATE_CONTRACTS["persistent_ledger_state"].writer_components == (
        "Asset Runtime",
    )


def test_report_reconcile_and_audit_do_not_import_current_writers():
    forbidden = (
        "ai_fund_lab_v2.runtime_v2.asset.writer",
        "ai_fund_lab_v2.runtime_v2.pending.writer",
    )
    checked_dirs = ("report", "reconcile", "audit")

    for dirname in checked_dirs:
        for path in (RUNTIME_ROOT / dirname).rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            for item in forbidden:
                assert item not in source, f"{path} imports {item}"


def test_reconcile_does_not_write_current_or_asset_state():
    reconcile_sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((RUNTIME_ROOT / "reconcile").rglob("*.py"))
    )

    assert "write_current_asset_state" not in reconcile_sources
    assert "write_pending_order_plan" not in reconcile_sources
    assert ".write_text(" not in reconcile_sources
    assert ".mkdir(" not in reconcile_sources


def test_report_notification_payload_and_audit_do_not_drive_current_update():
    forbidden_snippets = (
        "write_current_asset_state",
        "write_pending_order_plan",
        "append_record(",
    )
    checked_dirs = ("report", "notification", "audit")

    for dirname in checked_dirs:
        for path in (RUNTIME_ROOT / dirname).rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            for snippet in forbidden_snippets:
                assert snippet not in source, f"{path} contains {snippet}"
