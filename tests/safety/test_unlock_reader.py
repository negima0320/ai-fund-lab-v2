from pathlib import Path

import pytest

from ai_fund_lab_v2.safety import (
    SafetyStatus,
    UnlockApproval,
    UnlockReadError,
    list_unlock_approvals,
    load_latest_unlock_approval,
    write_unlock_approval,
)


def test_latest_unlock_approval_can_be_loaded(tmp_path: Path) -> None:
    approval = UnlockApproval(
        request_id="unlock-1",
        approved_by="reviewer",
        approval_reason="OK after reconciliation",
        reconciliation_status=SafetyStatus.OK,
        safety_report_path=".runtime/safety/reports/report.json",
    )
    path = write_unlock_approval(approval, tmp_path / ".runtime")

    loaded = load_latest_unlock_approval(tmp_path / ".runtime")

    assert list_unlock_approvals(tmp_path / ".runtime") == [path]
    assert loaded is not None
    assert loaded.request_id == "unlock-1"
    assert loaded.reconciliation_status == SafetyStatus.OK


def test_latest_unlock_approval_returns_none_when_missing(tmp_path: Path) -> None:
    assert list_unlock_approvals(tmp_path / ".runtime") == []
    assert load_latest_unlock_approval(tmp_path / ".runtime") is None


def test_broken_unlock_approval_json_fails_clearly(tmp_path: Path) -> None:
    directory = tmp_path / ".runtime" / "safety" / "unlock" / "approvals"
    directory.mkdir(parents=True)
    (directory / "broken.json").write_text("{broken", encoding="utf-8")

    with pytest.raises(UnlockReadError, match="invalid"):
        load_latest_unlock_approval(tmp_path / ".runtime")
