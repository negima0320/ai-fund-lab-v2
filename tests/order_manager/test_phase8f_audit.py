from scripts.audit_phase8f_order_manager_dry_run_workflow import run_audit


def test_phase8f_audit_passes() -> None:
    result = run_audit()
    assert result["status"] == "PASS"
    assert result["checks"]["phase7_artifact_missing_fail_closed"] is True
