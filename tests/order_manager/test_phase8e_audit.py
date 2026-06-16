from scripts.audit_phase8e_order_plan_generator import run_audit


def test_phase8e_audit_passes() -> None:
    result = run_audit()

    assert result["status"] == "PASS"
    assert all(result["checks"].values())

