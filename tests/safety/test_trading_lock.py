from ai_fund_lab_v2.safety import (
    ReconciliationIssue,
    ReconciliationResult,
    ReconciliationSeverity,
    SafetyStatus,
    build_trading_lock,
)


def test_ok_result_is_not_locked() -> None:
    lock = build_trading_lock(ReconciliationResult(status=SafetyStatus.OK))

    assert not lock.is_locked
    assert lock.reason == "none"


def test_warning_only_result_is_not_locked() -> None:
    result = ReconciliationResult(
        status=SafetyStatus.WARNING,
        issues=(
            ReconciliationIssue(
                code="broker_snapshot_id_missing",
                severity=ReconciliationSeverity.WARNING,
                message="missing broker snapshot id",
            ),
        ),
    )

    lock = build_trading_lock(result)

    assert not lock.is_locked
    assert lock.reason == "broker_snapshot_id_missing"


def test_halt_result_is_locked_and_reason_contains_issue_code() -> None:
    result = ReconciliationResult(
        status=SafetyStatus.HALT,
        issues=(
            ReconciliationIssue(
                code="cash_mismatch",
                severity=ReconciliationSeverity.HALT,
                message="cash mismatch",
            ),
        ),
    )

    lock = build_trading_lock(result)

    assert lock.is_locked
    assert lock.status == SafetyStatus.HALT
    assert "cash_mismatch" in lock.reason
