import json
from pathlib import Path

from ai_fund_lab_v2.paper_trading.ai_artifact_adapter import AIArtifactPaths, adapt_ai_artifacts


def test_order_plan_executable_true_is_invalid(tmp_path: Path) -> None:
    path = _order_plan(tmp_path, executable=True, live_order_allowed=False, requires_human_review=True)
    result = adapt_ai_artifacts(decision_for="2026-06-16", data_until="2026-06-16", paths=AIArtifactPaths(order_plan_artifact=path))
    assert result.status == "INVALID"
    assert "order_plan_executable_true" in result.blocked_reasons


def test_order_plan_live_order_allowed_true_is_invalid(tmp_path: Path) -> None:
    path = _order_plan(tmp_path, executable=False, live_order_allowed=True, requires_human_review=True)
    result = adapt_ai_artifacts(decision_for="2026-06-16", data_until="2026-06-16", paths=AIArtifactPaths(order_plan_artifact=path))
    assert result.status == "INVALID"
    assert "order_plan_live_order_allowed_true" in result.blocked_reasons


def test_order_plan_requires_human_review_false_is_invalid(tmp_path: Path) -> None:
    path = _order_plan(tmp_path, executable=False, live_order_allowed=False, requires_human_review=False)
    result = adapt_ai_artifacts(decision_for="2026-06-16", data_until="2026-06-16", paths=AIArtifactPaths(order_plan_artifact=path))
    assert result.status == "INVALID"
    assert "order_plan_requires_human_review_false" in result.blocked_reasons


def _order_plan(tmp_path: Path, *, executable: bool, live_order_allowed: bool, requires_human_review: bool) -> Path:
    path = tmp_path / "order_plan.json"
    path.write_text(
        json.dumps(
            {
                "executable": executable,
                "live_order_allowed": live_order_allowed,
                "requires_human_review": requires_human_review,
                "items": [],
            }
        ),
        encoding="utf-8",
    )
    return path

