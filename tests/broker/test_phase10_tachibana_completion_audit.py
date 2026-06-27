from pathlib import Path

from scripts.audit_phase10_tachibana_readonly import run_audit


def test_phase10_tachibana_completion_audit_passes_current_artifacts() -> None:
    report = run_audit(root=Path("."))

    assert report["status"] == "PASS"
    assert report["phase10_complete"] is True
    assert report["checks"]["no_live_order_audit"]["status"] == "PASS"
    assert report["checks"]["secret_redaction_canary"]["status"] == "PASS"
    assert report["checks"]["paper_trading_separation"]["status"] == "PASS"
