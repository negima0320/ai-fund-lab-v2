from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_fund_lab_v2.paper_trading.human_review_artifact import create_human_review_request, load_human_review


def test_human_review_request_generated(tmp_path: Path) -> None:
    order_plan = _write_order_plan(tmp_path)

    result = create_human_review_request(
        order_plan_path=order_plan,
        decision_for="2026-06-15",
        virtual_order_date="2026-06-16",
        output_root=tmp_path / "review",
    )

    payload = json.loads(Path(result.json_path).read_text(encoding="utf-8"))
    markdown = Path(result.markdown_path).read_text(encoding="utf-8")
    assert result.review_status == "pending"
    assert payload["review_status"] == "pending"
    assert payload["items"][0]["code"] == "10010"
    assert "review_status: approved | rejected | needs_change" in markdown
    assert load_human_review(result.json_path)["review_status"] == "pending"


def test_human_review_rejects_executable_order_plan(tmp_path: Path) -> None:
    order_plan = _write_order_plan(tmp_path, executable=True)

    with pytest.raises(ValueError, match="executable=false"):
        create_human_review_request(
            order_plan_path=order_plan,
            decision_for="2026-06-15",
            virtual_order_date="2026-06-16",
            output_root=tmp_path / "review",
        )


def _write_order_plan(tmp_path: Path, *, executable: bool = False) -> Path:
    path = tmp_path / "order_plan.json"
    path.write_text(
        json.dumps(
            {
                "run_id": "run1",
                "decision_for": "2026-06-15",
                "data_until": "2026-06-15",
                "executable": executable,
                "live_order_allowed": False,
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

