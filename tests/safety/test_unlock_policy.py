from ai_fund_lab_v2.safety import (
    SafetyReport,
    SafetyStatus,
    UnlockRequest,
    can_approve_unlock,
    can_request_unlock,
)


def test_ok_report_can_request_unlock() -> None:
    allowed, message = can_request_unlock(ok_report(), requested_by="operator", reason="checked report")

    assert allowed
    assert "can be created" in message


def test_requested_by_is_required() -> None:
    allowed, message = can_request_unlock(ok_report(), requested_by="", reason="checked report")

    assert not allowed
    assert "requested_by" in message


def test_reason_is_required() -> None:
    allowed, message = can_request_unlock(ok_report(), requested_by="operator", reason="")

    assert not allowed
    assert "reason" in message


def test_halt_report_cannot_be_approved() -> None:
    request = unlock_request()

    allowed, message = can_approve_unlock(request, halt_report(), approved_by="operator", approval_reason="checked")

    assert not allowed
    assert "must be OK" in message


def test_warning_report_cannot_be_approved() -> None:
    request = unlock_request()

    allowed, message = can_approve_unlock(request, warning_report(), approved_by="operator", approval_reason="checked")

    assert not allowed
    assert "must be OK" in message


def test_ok_report_can_be_approved() -> None:
    request = unlock_request()

    allowed, message = can_approve_unlock(request, ok_report(), approved_by="operator", approval_reason="checked")

    assert allowed
    assert "can be approved" in message


def test_approved_by_is_required() -> None:
    request = unlock_request()

    allowed, message = can_approve_unlock(request, ok_report(), approved_by="", approval_reason="checked")

    assert not allowed
    assert "approved_by" in message


def test_approval_reason_is_required() -> None:
    request = unlock_request()

    allowed, message = can_approve_unlock(request, ok_report(), approved_by="operator", approval_reason="")

    assert not allowed
    assert "approval_reason" in message


def ok_report() -> SafetyReport:
    return SafetyReport(status=SafetyStatus.OK, checked_at="2999-01-01T00:00:00+00:00", broker_snapshot_id="broker-1", issue_count=0, issues=(), trading_locked=False)


def halt_report() -> SafetyReport:
    return SafetyReport(status=SafetyStatus.HALT, checked_at="2999-01-01T00:00:00+00:00", broker_snapshot_id="broker-1", issue_count=1, issues=(), trading_locked=True)


def warning_report() -> SafetyReport:
    return SafetyReport(status=SafetyStatus.WARNING, checked_at="2999-01-01T00:00:00+00:00", broker_snapshot_id="broker-1", issue_count=1, issues=(), trading_locked=False)


def unlock_request() -> UnlockRequest:
    return UnlockRequest(requested_by="operator", reason="checked report", latest_report_status=SafetyStatus.OK)
