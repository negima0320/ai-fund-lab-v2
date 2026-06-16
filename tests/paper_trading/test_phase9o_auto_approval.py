from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.paper_trading.auto_approval import AUTO_APPROVAL_BLOCKED, AUTO_APPROVAL_CREATED, create_auto_approval_artifact


def test_auto_approval_artifact_generated_for_safe_order_plan(tmp_path: Path) -> None:
    order_plan = _write_order_plan(tmp_path)

    result = create_auto_approval_artifact(
        order_plan_path=order_plan,
        decision_for="2026-06-15",
        virtual_order_date="2026-06-16",
        output_root=tmp_path / "auto",
    )

    payload = json.loads(Path(result.json_path).read_text(encoding="utf-8"))
    markdown = Path(result.markdown_path).read_text(encoding="utf-8")
    assert result.status == AUTO_APPROVAL_CREATED
    assert payload["review_status"] == "auto_approved_for_paper_trading"
    assert payload["approval_mode"] == "auto_for_paper_trading"
    assert payload["broker_order_api_called"] is False
    assert payload["live_order_allowed"] is False
    assert payload["executable"] is False
    assert payload["virtual_fill_executed"] is False
    assert "Paper Trading only" in markdown


def test_auto_approval_blocks_invalid_order_plan(tmp_path: Path) -> None:
    order_plan = _write_order_plan(tmp_path, live_order_allowed=True)

    result = create_auto_approval_artifact(
        order_plan_path=order_plan,
        decision_for="2026-06-15",
        virtual_order_date="2026-06-16",
        output_root=tmp_path / "auto",
    )

    assert result.status == AUTO_APPROVAL_BLOCKED
    assert "order_plan_live_order_allowed_not_false" in result.blocked_reasons


def test_auto_approval_blocks_broker_mode(tmp_path: Path) -> None:
    order_plan = _write_order_plan(tmp_path)

    result = create_auto_approval_artifact(
        order_plan_path=order_plan,
        decision_for="2026-06-15",
        virtual_order_date="2026-06-16",
        output_root=tmp_path / "auto",
        execution_mode="broker",
    )

    assert result.status == AUTO_APPROVAL_BLOCKED
    assert "auto_approval_blocked_in_broker_mode" in result.blocked_reasons


def _write_order_plan(tmp_path: Path, *, live_order_allowed: bool = False) -> Path:
    path = tmp_path / "order_plan.json"
    path.write_text(
        json.dumps(
            {
                "run_id": "run1",
                "decision_for": "2026-06-15",
                "data_until": "2026-06-15",
                "virtual_execution_date": "2026-06-16",
                "executable": False,
                "live_order_allowed": live_order_allowed,
                "requires_human_review": True,
                "items": [
                    {
                        "order_id": "order1",
                        "code": "10010",
                        "side": "BUY",
                        "quantity": 100,
                        "planned_amount": "100000",
                        "reason": "test",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return path

