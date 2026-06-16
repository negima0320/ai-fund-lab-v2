from scripts.audit_phase8d_order_manager_reconciliation import run_audit


def test_phase8d_audit_passes() -> None:
    result = run_audit()

    assert result["status"] == "PASS"
    assert all(result["checks"].values())

