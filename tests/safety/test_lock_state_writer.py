import json
from pathlib import Path

from ai_fund_lab_v2.safety import SafetyStatus, UnlockApplyResult, UnlockApplyStatus, write_unlock_applied_state, write_unlock_apply_audit


def test_unlock_applied_state_and_apply_audit_are_saved(tmp_path: Path) -> None:
    result = UnlockApplyResult(
        applied=True,
        status=UnlockApplyStatus.APPLIED,
        approval_request_id="unlock-1",
        applied_by="operator",
        latest_report_status=SafetyStatus.OK,
        message="unlock can be applied",
    )

    state_path = write_unlock_applied_state(result, tmp_path / ".runtime")
    audit_path = write_unlock_apply_audit(result, tmp_path / ".runtime")

    assert state_path.parent == tmp_path / ".runtime" / "safety" / "locks"
    assert audit_path.parent == tmp_path / ".runtime" / "safety" / "unlock" / "apply_audit"
    state_payload = json.loads(state_path.read_text(encoding="utf-8"))
    audit_payload = json.loads(audit_path.read_text(encoding="utf-8"))
    assert state_payload["status"] == "APPLIED"
    assert state_payload["applied"] is True
    assert audit_payload["approval_request_id"] == "unlock-1"


def test_unlock_apply_writers_sanitize_secret_like_values(tmp_path: Path) -> None:
    result = UnlockApplyResult(
        applied=True,
        status=UnlockApplyStatus.APPLIED,
        approval_request_id="unlock-1",
        applied_by="operator",
        latest_report_status=SafetyStatus.OK,
        message="token=secret-token cookie=secret-cookie password=secret-password https://example.invalid/session",
    )

    state_path = write_unlock_applied_state(result, tmp_path / ".runtime")
    audit_path = write_unlock_apply_audit(result, tmp_path / ".runtime")

    saved = state_path.read_text(encoding="utf-8") + audit_path.read_text(encoding="utf-8")
    assert "secret-token" not in saved
    assert "secret-cookie" not in saved
    assert "secret-password" not in saved
    assert "https://example.invalid/session" not in saved
    assert "[REDACTED]" in saved
