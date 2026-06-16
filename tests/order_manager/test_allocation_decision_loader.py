import json
from decimal import Decimal
from pathlib import Path

import pytest

from ai_fund_lab_v2.order_manager.allocation_decision_loader import AllocationDecisionLoadError, load_allocation_decision_set


def test_allocation_decision_loader_normalizes_cap5_decisions(tmp_path: Path) -> None:
    path = tmp_path / "allocation.json"
    path.write_text(
        json.dumps(
            {
                "policy_id": "CAP5",
                "decisions": [
                    {"decision_id": "d1", "issue_code": "7203", "side": "BUY", "quantity": 100, "estimated_price": "2500"}
                ],
            }
        ),
        encoding="utf-8",
    )

    decision_set = load_allocation_decision_set(path)

    assert decision_set.policy_id == "CAP5"
    assert decision_set.lot_size == 100
    assert decision_set.cash_buffer_ratio == Decimal("0.05")
    assert decision_set.decisions[0].estimated_value == 250000
    assert "CAP4" in decision_set.shadow_policies


def test_allocation_decision_loader_fail_closed_on_missing_input(tmp_path: Path) -> None:
    with pytest.raises(AllocationDecisionLoadError):
        load_allocation_decision_set(tmp_path / "missing.json")


def test_allocation_decision_loader_rejects_non_lot_quantity(tmp_path: Path) -> None:
    path = tmp_path / "allocation.json"
    path.write_text(
        json.dumps({"decisions": [{"issue_code": "7203", "side": "BUY", "quantity": 10, "estimated_price": "1"}]}),
        encoding="utf-8",
    )

    with pytest.raises(AllocationDecisionLoadError, match="100-share"):
        load_allocation_decision_set(path)
