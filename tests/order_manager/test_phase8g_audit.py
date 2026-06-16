from scripts.audit_phase8g_end_to_end_no_live_order import run_audit


def test_phase8g_audit_passes() -> None:
    result = run_audit()
    assert result["status"] == "PASS"
    assert result["checks"]["end_to_end_report_generated"] is True
