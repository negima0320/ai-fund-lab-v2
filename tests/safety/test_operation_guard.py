from ai_fund_lab_v2.safety import (
    ReconciliationIssue,
    ReconciliationResult,
    ReconciliationSeverity,
    SafetyStatus,
    build_trading_lock,
    is_operation_allowed,
)


def test_halt_blocks_trading_and_state_mutating_operations() -> None:
    lock = build_trading_lock(
        ReconciliationResult(
            status=SafetyStatus.HALT,
            issues=(ReconciliationIssue(code="cash_mismatch", severity=ReconciliationSeverity.HALT, message="cash mismatch"),),
        )
    )

    for operation in ["buy", "sell", "new_order", "correct_order", "cancel_order", "portfolio_update", "ai_trade_decision"]:
        assert not is_operation_allowed(operation, lock)


def test_halt_allows_observation_and_audit_operations() -> None:
    lock = build_trading_lock(
        ReconciliationResult(
            status=SafetyStatus.HALT,
            issues=(ReconciliationIssue(code="cash_mismatch", severity=ReconciliationSeverity.HALT, message="cash mismatch"),),
        )
    )

    for operation in ["broker_sync", "read_state", "audit", "report"]:
        assert is_operation_allowed(operation, lock)


def test_unlocked_state_allows_operations_by_policy() -> None:
    lock = build_trading_lock(ReconciliationResult(status=SafetyStatus.OK))

    assert is_operation_allowed("buy", lock)
    assert is_operation_allowed("portfolio_update", lock)
