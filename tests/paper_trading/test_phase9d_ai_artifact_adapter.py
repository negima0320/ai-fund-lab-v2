import json
from pathlib import Path

from ai_fund_lab_v2.paper_trading.ai_artifact_adapter import AIArtifactPaths, adapt_ai_artifacts


def test_valid_mock_artifacts_reflect_daily_run_result(tmp_path: Path) -> None:
    _write_artifacts(tmp_path)
    result = adapt_ai_artifacts(
        decision_for="2026-06-16",
        data_until="2026-06-16",
        paths=AIArtifactPaths(
            candidate_artifact=tmp_path / "candidate_artifact.json",
            opportunity_artifact=tmp_path / "opportunity_artifact.json",
            position_artifact=tmp_path / "position_artifact.json",
            allocation_artifact=tmp_path / "allocation_artifact.json",
            order_plan_artifact=tmp_path / "order_plan_artifact.json",
        ),
    )
    assert result.status == "READY"
    assert result.daily_result.buy_candidates
    assert result.daily_result.sell_candidates
    assert result.daily_result.hold_candidates
    assert result.daily_result.artifact_state["integration_status"] == "READY"


def test_missing_artifacts_become_blocked_with_halt_candidate() -> None:
    result = adapt_ai_artifacts(
        decision_for="2026-06-16",
        data_until="2026-06-16",
        paths=AIArtifactPaths(),
    )
    assert result.status == "BLOCKED"
    assert result.daily_result.hold_candidates[0].short_reason == "本日は判断材料不足です。"


def test_date_mismatch_is_invalid(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "opportunity_artifact.json",
        {"rows": [{"code": "7203", "buy_rank": 1, "data_until": "2026-06-15", "decision_for": "2026-06-16"}]},
    )
    result = adapt_ai_artifacts(
        decision_for="2026-06-16",
        data_until="2026-06-16",
        paths=AIArtifactPaths(opportunity_artifact=tmp_path / "opportunity_artifact.json"),
    )
    assert result.status == "INVALID"
    assert "opportunity_data_until_mismatch" in result.blocked_reasons


def test_future_data_until_is_invalid(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "candidate_artifact.json",
        {"rows": [{"code": "7203", "data_until": "2026-06-17", "decision_for": "2026-06-16"}]},
    )
    result = adapt_ai_artifacts(
        decision_for="2026-06-16",
        data_until="2026-06-16",
        paths=AIArtifactPaths(candidate_artifact=tmp_path / "candidate_artifact.json"),
    )
    assert result.status == "INVALID"
    assert "candidate_future_data_until" in result.blocked_reasons


def _write_artifacts(root: Path) -> None:
    _write_json(root / "candidate_artifact.json", {"rows": [{"code": "7203", "name": "Toyota Motor", "rank": 1, "data_until": "2026-06-16", "decision_for": "2026-06-16"}]})
    _write_json(root / "opportunity_artifact.json", {"rows": [{"code": "7203", "buy_rank": 1, "expected_edge_score": 0.81, "data_until": "2026-06-16", "decision_for": "2026-06-16"}]})
    _write_json(root / "position_artifact.json", {"rows": [{"code": "9432", "action": "HOLD", "data_until": "2026-06-16", "decision_for": "2026-06-16"}]})
    _write_json(root / "allocation_artifact.json", {"decisions": [{"code": "7203", "action": "BUY", "quantity": 100, "buy_amount": 100000}]})
    _write_json(root / "order_plan_artifact.json", {"executable": False, "live_order_allowed": False, "requires_human_review": True, "items": [{"issue_code": "6758", "side": "SELL"}]})


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")

