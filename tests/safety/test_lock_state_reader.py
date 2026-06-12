from pathlib import Path

import pytest

from ai_fund_lab_v2.safety import (
    LockStateReadError,
    SafetyStatus,
    TradingLock,
    UnlockApplyResult,
    UnlockApplyStatus,
    list_lock_states,
    load_latest_lock_state,
    write_trading_lock,
    write_unlock_applied_state,
)


def test_lock_state_reader_lists_and_loads_latest_state(tmp_path: Path) -> None:
    lock_path = write_trading_lock(TradingLock(is_locked=True, reason="cash_mismatch", status=SafetyStatus.HALT), tmp_path / ".runtime")
    apply_path = write_unlock_applied_state(
        UnlockApplyResult(
            applied=True,
            status=UnlockApplyStatus.APPLIED,
            approval_request_id="unlock-1",
            applied_by="operator",
            latest_report_status=SafetyStatus.OK,
            message="applied",
        ),
        tmp_path / ".runtime",
    )

    states = list_lock_states(tmp_path / ".runtime")
    latest = load_latest_lock_state(tmp_path / ".runtime")

    assert lock_path in states
    assert apply_path in states
    assert latest is not None
    assert latest["status"] == "APPLIED"
    assert latest["_state_path"] == str(apply_path)


def test_lock_state_reader_returns_none_when_missing(tmp_path: Path) -> None:
    assert list_lock_states(tmp_path / ".runtime") == []
    assert load_latest_lock_state(tmp_path / ".runtime") is None


def test_lock_state_reader_broken_json_fails_clearly_without_secret(tmp_path: Path) -> None:
    directory = tmp_path / ".runtime" / "safety" / "locks"
    directory.mkdir(parents=True)
    path = directory / "broken.json"
    path.write_text('{"token":"secret-token"', encoding="utf-8")

    with pytest.raises(LockStateReadError) as exc_info:
        load_latest_lock_state(tmp_path / ".runtime")

    message = str(exc_info.value)
    assert "invalid" in message
    assert "secret-token" not in message
