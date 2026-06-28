from datetime import datetime, timedelta, timezone

from ai_fund_lab_v2.safety_phase11.manual_unlock import (
    approval_from_recovery_decision,
    create_manual_unlock_approval,
    read_manual_unlock_approval,
    validate_manual_unlock_approval,
    validate_normal_return_after_manual_approval,
)
from ai_fund_lab_v2.safety_phase11.models import SafetyDecision, SafetyState
from ai_fund_lab_v2.safety_phase11.recovery import RecoveryCheckInput, RecoveryEvaluator


def _recovery_decision():
    return RecoveryEvaluator().evaluate(
        RecoveryCheckInput(
            current_state=SafetyState.BUY_STOP,
            market_summary={
                "severe_crash": False,
                "stable_days": 5,
                "candidate_universe_drawdown_improved": True,
                "crash_issue_ratio_declined": True,
                "extreme_down_ratio_declined": True,
            },
            quote_freshness="fresh",
            broker_snapshot_freshness="fresh",
            broker_divergence="none",
            duplicate_active_order_risk=False,
            daily_loss_pct="0.00",
            runtime_state_valid=True,
            persistence_violation_suspected=False,
            latest_safety_report_path="reports/safety/phase11/2026-06-29_safety_report.json",
        )
    )


def test_manual_unlock_approval_can_become_manual_approved(tmp_path):
    path = approval_from_recovery_decision(
        _recovery_decision(),
        approved_by="operator",
        reason="reviewed recovery evidence",
        source_state=SafetyState.BUY_STOP,
        safety_report_path="reports/safety/phase11/2026-06-29_safety_report.json",
        runtime_dir=tmp_path,
    )
    payload = read_manual_unlock_approval(runtime_dir=tmp_path)
    assert str(path).endswith("manual_unlock_approval.json")
    validation = validate_manual_unlock_approval(payload)
    assert validation.valid is True
    assert validation.next_state is SafetyState.MANUAL_APPROVED
    assert validation.auto_recovery_executed is False


def test_approval_missing_or_invalid_does_not_unlock_normal(tmp_path):
    missing = read_manual_unlock_approval(runtime_dir=tmp_path)
    validation = validate_manual_unlock_approval(missing)
    assert validation.valid is False
    assert "approval_inactive" in validation.reason_codes

    normal_return = validate_normal_return_after_manual_approval(
        current_state=SafetyState.RECOVERY_CANDIDATE,
        latest_safety_decision=SafetyDecision.ALLOW,
    )
    assert normal_return.valid is False
    assert "state_not_manual_approved" in normal_return.reason_codes


def test_expired_approval_is_invalid(tmp_path):
    expires_at = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    create_manual_unlock_approval(
        approved_by="operator",
        reason="expired",
        source_state=SafetyState.BUY_STOP,
        safety_report_path="reports/safety/phase11/report.json",
        recovery_evidence=("manual_emergency_flag_inactive",),
        expires_at=expires_at,
        runtime_dir=tmp_path,
    )
    validation = validate_manual_unlock_approval(read_manual_unlock_approval(runtime_dir=tmp_path))
    assert validation.valid is False
    assert "approval_expired" in validation.reason_codes


def test_missing_safety_report_or_recovery_evidence_is_invalid(tmp_path):
    create_manual_unlock_approval(
        approved_by="operator",
        reason="missing fields",
        source_state=SafetyState.BUY_STOP,
        safety_report_path="",
        recovery_evidence=(),
        expires_at=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        runtime_dir=tmp_path,
    )
    validation = validate_manual_unlock_approval(read_manual_unlock_approval(runtime_dir=tmp_path))
    assert validation.valid is False
    assert "missing_safety_report_path" in validation.reason_codes
    assert "missing_recovery_evidence" in validation.reason_codes


def test_manual_approved_to_normal_requires_latest_safety_check_ok():
    blocked = validate_normal_return_after_manual_approval(
        current_state=SafetyState.MANUAL_APPROVED,
        latest_safety_decision=SafetyDecision.REVIEW_REQUIRED,
    )
    assert blocked.valid is False
    assert "latest_safety_check_not_allow" in blocked.reason_codes

    allowed = validate_normal_return_after_manual_approval(
        current_state=SafetyState.MANUAL_APPROVED,
        latest_safety_decision=SafetyDecision.ALLOW,
    )
    assert allowed.valid is True
    assert allowed.next_state is SafetyState.NORMAL


def test_manual_unlock_approval_sanitizes_forbidden_values(tmp_path):
    create_manual_unlock_approval(
        approved_by="auth_id=AUTH-PLAINTEXT",
        reason=(
            "raw_request=RAW-REQUEST raw_response=RAW-RESPONSE "
            "account_id=ACCOUNT order_id=ORDER execution_id=EXEC "
            "second_password=SECOND https://secret.example.test/path"
        ),
        source_state=SafetyState.EMERGENCY_STOP,
        safety_report_path="reports/safety/phase11/report.json",
        recovery_evidence=("manual_emergency_flag_inactive",),
        expires_at=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        runtime_dir=tmp_path,
    )
    text = read_manual_unlock_approval(runtime_dir=tmp_path)
    serialized = str(text)
    assert "AUTH-PLAINTEXT" not in serialized
    assert "RAW-REQUEST" not in serialized
    assert "RAW-RESPONSE" not in serialized
    assert "ACCOUNT" not in serialized
    assert "ORDER" not in serialized
    assert "EXEC" not in serialized
    assert "SECOND" not in serialized
    assert "secret.example.test" not in serialized
