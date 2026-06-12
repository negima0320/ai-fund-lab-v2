from ai_fund_lab_v2.safety import SafetyReport, SafetyStatus, UnlockApproval, can_apply_unlock


def test_approval_and_ok_report_can_apply() -> None:
    allowed, message = can_apply_unlock(ok_approval(), ok_report(), applied_by="operator")

    assert allowed
    assert "can be applied" in message


def test_approval_is_required() -> None:
    allowed, message = can_apply_unlock(None, ok_report(), applied_by="operator")

    assert not allowed
    assert "approval" in message


def test_latest_report_is_required() -> None:
    allowed, message = can_apply_unlock(ok_approval(), None, applied_by="operator")

    assert not allowed
    assert "latest safety report" in message


def test_halt_report_cannot_apply() -> None:
    allowed, message = can_apply_unlock(ok_approval(), report(SafetyStatus.HALT), applied_by="operator")

    assert not allowed
    assert "must be OK" in message


def test_warning_report_cannot_apply() -> None:
    allowed, message = can_apply_unlock(ok_approval(), report(SafetyStatus.WARNING), applied_by="operator")

    assert not allowed
    assert "must be OK" in message


def test_applied_by_is_required() -> None:
    allowed, message = can_apply_unlock(ok_approval(), ok_report(), applied_by="")

    assert not allowed
    assert "applied_by" in message


def test_approval_reconciliation_status_must_be_ok() -> None:
    approval = UnlockApproval(
        request_id="unlock-1",
        approved_by="reviewer",
        approval_reason="checked",
        reconciliation_status=SafetyStatus.HALT,
    )

    allowed, message = can_apply_unlock(approval, ok_report(), applied_by="operator")

    assert not allowed
    assert "reconciliation_status" in message


def test_approval_requires_approved_by_and_reason() -> None:
    missing_approver = UnlockApproval(request_id="unlock-1", approved_by="", approval_reason="checked", reconciliation_status=SafetyStatus.OK)
    missing_reason = UnlockApproval(request_id="unlock-1", approved_by="reviewer", approval_reason="", reconciliation_status=SafetyStatus.OK)

    assert not can_apply_unlock(missing_approver, ok_report(), applied_by="operator")[0]
    assert not can_apply_unlock(missing_reason, ok_report(), applied_by="operator")[0]


def ok_approval() -> UnlockApproval:
    return UnlockApproval(
        request_id="unlock-1",
        approved_by="reviewer",
        approval_reason="OK after reconciliation",
        reconciliation_status=SafetyStatus.OK,
        safety_report_path=".runtime/safety/reports/old_report.json",
    )


def ok_report() -> SafetyReport:
    return report(SafetyStatus.OK)


def report(status: SafetyStatus) -> SafetyReport:
    return SafetyReport(status=status, checked_at="2999-01-01T00:00:00+00:00", broker_snapshot_id="broker-1", issue_count=0, issues=(), trading_locked=False)
