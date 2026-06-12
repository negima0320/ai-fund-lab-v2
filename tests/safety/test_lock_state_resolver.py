from ai_fund_lab_v2.safety import (
    SafetyStatus,
    TradingLock,
    UnlockApplyResult,
    UnlockApplyStatus,
    resolve_current_lock_state,
    write_trading_lock,
    write_unlock_applied_state,
)


def test_latest_trading_lock_locked_resolves_locked(tmp_path) -> None:
    lock_path = write_trading_lock(TradingLock(is_locked=True, reason="cash_mismatch", status=SafetyStatus.HALT), tmp_path / ".runtime")

    state = resolve_current_lock_state(tmp_path / ".runtime")

    assert state["is_locked"] is True
    assert state["source"] == "trading_lock"
    assert state["state_path"] == str(lock_path)


def test_latest_unlock_applied_resolves_unlocked(tmp_path) -> None:
    write_trading_lock(TradingLock(is_locked=True, reason="cash_mismatch", status=SafetyStatus.HALT), tmp_path / ".runtime")
    apply_path = write_unlock_applied_state(
        UnlockApplyResult(True, UnlockApplyStatus.APPLIED, "unlock-1", "operator", SafetyStatus.OK, "applied"),
        tmp_path / ".runtime",
    )

    state = resolve_current_lock_state(tmp_path / ".runtime")

    assert state["is_locked"] is False
    assert state["source"] == "unlock_apply"
    assert state["state_path"] == str(apply_path)


def test_new_trading_lock_after_unlock_relocks(tmp_path) -> None:
    write_unlock_applied_state(
        UnlockApplyResult(True, UnlockApplyStatus.APPLIED, "unlock-1", "operator", SafetyStatus.OK, "applied"),
        tmp_path / ".runtime",
    )
    lock_path = write_trading_lock(TradingLock(is_locked=True, reason="new_halt", status=SafetyStatus.HALT), tmp_path / ".runtime")

    state = resolve_current_lock_state(tmp_path / ".runtime")

    assert state["is_locked"] is True
    assert state["source"] == "trading_lock"
    assert state["state_path"] == str(lock_path)


def test_no_lock_state_resolves_unlocked_source_none(tmp_path) -> None:
    state = resolve_current_lock_state(tmp_path / ".runtime")

    assert state["is_locked"] is False
    assert state["source"] == "none"


def test_corrupt_lock_state_fail_closed_locked(tmp_path) -> None:
    directory = tmp_path / ".runtime" / "safety" / "locks"
    directory.mkdir(parents=True)
    (directory / "broken.json").write_text("{broken", encoding="utf-8")

    state = resolve_current_lock_state(tmp_path / ".runtime")

    assert state["is_locked"] is True
    assert state["source"] == "corrupt"
