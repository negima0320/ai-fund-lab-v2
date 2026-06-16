import json
from pathlib import Path

import pytest

from ai_fund_lab_v2.order_manager.approval_record import HumanReviewApprovalRecord, write_approval_record


def test_approval_record_never_allows_live_order(tmp_path: Path) -> None:
    record = HumanReviewApprovalRecord(plan_id="plan1", reviewer="user", decision="approved", comment="ok")
    path = write_approval_record(record, tmp_path / ".runtime")

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["approval_does_not_allow_live_order"] is True
    assert path.parent == tmp_path / ".runtime" / "order_manager" / "review"


def test_approval_record_rejects_live_order_permission() -> None:
    with pytest.raises(ValueError):
        HumanReviewApprovalRecord(
            plan_id="plan1",
            reviewer="user",
            decision="approved",
            approval_does_not_allow_live_order=False,
        )

