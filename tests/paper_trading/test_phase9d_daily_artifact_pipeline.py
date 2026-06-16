import json
from pathlib import Path

from ai_fund_lab_v2.data_store.storage_backends import JsonlStorageBackend
from ai_fund_lab_v2.paper_trading.daily_pipeline_runner import run_daily_pipeline
from ai_fund_lab_v2.paper_trading.reporting.redaction_checker import check_public_report_redaction


def test_daily_artifact_pipeline_generates_reports_from_artifacts(tmp_path: Path) -> None:
    daily, listed = _write_market(tmp_path)
    artifact_root = _write_artifacts(tmp_path / "artifacts")
    result = run_daily_pipeline(
        run_date="2026-06-16",
        runtime_dir=tmp_path / ".runtime",
        reports_root=tmp_path / "reports",
        daily_quotes_path=daily,
        listed_info_path=listed,
        artifact_root=artifact_root,
        use_artifacts=True,
    )
    assert result.status == "OK"
    assert result.daily_result.buy_candidates
    assert result.daily_result.sell_candidates
    assert result.daily_result.hold_candidates
    assert Path(result.internal_report_md_path).exists()
    public_text = Path(result.public_report_path).read_text(encoding="utf-8")
    assert "7203" in public_text
    assert check_public_report_redaction(public_text).ready
    assert result.broker_order_api_called is False
    assert result.open_d_started is False
    assert result.unlock_trade_called is False
    assert result.paper_ledger_fill_executed is False


def test_daily_artifact_pipeline_missing_artifacts_halts_with_reports(tmp_path: Path) -> None:
    daily, listed = _write_market(tmp_path)
    result = run_daily_pipeline(
        run_date="2026-06-16",
        runtime_dir=tmp_path / ".runtime",
        reports_root=tmp_path / "reports",
        daily_quotes_path=daily,
        listed_info_path=listed,
        artifact_root=tmp_path / "missing",
        use_artifacts=True,
    )
    assert result.status == "HALT"
    assert Path(result.internal_report_md_path).exists()
    assert Path(result.public_report_path).exists()


def _write_market(root: Path) -> tuple[Path, Path]:
    backend = JsonlStorageBackend()
    daily = root / "daily.jsonl"
    listed = root / "listed.jsonl"
    backend.write_records(daily, [{"Date": "2026-06-16", "Code": "7203", "Open": 100, "High": 110, "Low": 99, "Close": 108, "Volume": 1000}])
    backend.write_records(listed, [{"Date": "2026-06-16", "Code": "7203"}])
    return daily, listed


def _write_artifacts(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    payloads = {
        "candidate_artifact.json": {"rows": [{"code": "7203", "name": "Toyota Motor", "rank": 1, "data_until": "2026-06-16", "decision_for": "2026-06-16"}]},
        "opportunity_artifact.json": {"rows": [{"code": "7203", "buy_rank": 1, "expected_edge_score": 0.81, "data_until": "2026-06-16", "decision_for": "2026-06-16"}]},
        "position_artifact.json": {"rows": [{"code": "9432", "name": "NTT", "action": "HOLD", "position_score": 0.66, "data_until": "2026-06-16", "decision_for": "2026-06-16"}]},
        "allocation_artifact.json": {"decisions": [{"code": "7203", "action": "BUY", "quantity": 100, "buy_amount": 100000}]},
        "order_plan_artifact.json": {"executable": False, "live_order_allowed": False, "requires_human_review": True, "items": [{"issue_code": "6758", "issue_name": "Sony Group", "side": "SELL"}]},
    }
    for filename, payload in payloads.items():
        (root / filename).write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")
    return root

