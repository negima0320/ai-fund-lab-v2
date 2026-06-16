from scripts.audit_phase8b_moomoo_order_manager_foundation import run_audit


def test_phase8b_audit_passes() -> None:
    result = run_audit()

    assert result["status"] == "PASS"
    assert all(result["checks"].values())

