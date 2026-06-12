from ai_fund_lab_v2.safety import (
    SafetyStatus,
    TradingLock,
    UnlockApplyResult,
    UnlockApplyStatus,
    check_operation_allowed_by_current_state,
    is_operation_allowed_by_current_state,
    write_trading_lock,
    write_unlock_applied_state,
)


def test_locked_state_blocks_dangerous_operations(tmp_path) -> None:
    write_trading_lock(TradingLock(is_locked=True, reason="cash_mismatch", status=SafetyStatus.HALT), tmp_path / ".runtime")

    for operation in ["buy", "new_order", "portfolio_update", "ai_trade_decision"]:
        assert not is_operation_allowed_by_current_state(operation, tmp_path / ".runtime")


def test_locked_state_allows_observation_operations(tmp_path) -> None:
    write_trading_lock(TradingLock(is_locked=True, reason="cash_mismatch", status=SafetyStatus.HALT), tmp_path / ".runtime")

    for operation in ["broker_sync", "read_state", "audit", "report"]:
        assert is_operation_allowed_by_current_state(operation, tmp_path / ".runtime")


def test_unlocked_state_allows_operations_by_policy(tmp_path) -> None:
    write_unlock_applied_state(
        UnlockApplyResult(True, UnlockApplyStatus.APPLIED, "unlock-1", "operator", SafetyStatus.OK, "applied"),
        tmp_path / ".runtime",
    )

    assert is_operation_allowed_by_current_state("buy", tmp_path / ".runtime")
    assert is_operation_allowed_by_current_state("new_order", tmp_path / ".runtime")
    detail = check_operation_allowed_by_current_state("portfolio_update", tmp_path / ".runtime")
    assert detail["allowed"] is True
    assert detail["source"] == "unlock_apply"


def test_corrupt_state_blocks_dangerous_operations_fail_closed(tmp_path) -> None:
    directory = tmp_path / ".runtime" / "safety" / "locks"
    directory.mkdir(parents=True)
    (directory / "broken.json").write_text("{broken", encoding="utf-8")

    detail = check_operation_allowed_by_current_state("buy", tmp_path / ".runtime")

    assert detail["allowed"] is False
    assert detail["is_locked"] is True
    assert detail["source"] == "corrupt"


def test_no_lock_state_allows_operations_source_none(tmp_path) -> None:
    detail = check_operation_allowed_by_current_state("buy", tmp_path / ".runtime")

    assert detail["allowed"] is True
    assert detail["source"] == "none"
