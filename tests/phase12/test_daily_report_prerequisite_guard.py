from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.operations.io import OperationPaths, write_json
from ai_fund_lab_v2.operations.operations import run_daily_report


def test_incomplete_operation_day_does_not_render_normal_candidate_sections(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    paths = OperationPaths(tmp_path)
    trade_date = "2026-07-01"
    write_json(paths.dated("market_refresh", trade_date, "market_refresh_manifest.json"), {"business_date": trade_date, "status": "PASS"})
    write_json(paths.dated("daily_plan", trade_date, "daily_plan_result.json"), {"business_date": trade_date, "status": "SKIPPED_MARKET_CLOSED"})
    write_json(paths.dated("fill_events", trade_date, "fill_events.json"), {"business_date": trade_date, "status": "PASS", "fill_events": []})
    write_json(paths.dated("safety_monitor", trade_date, "safety_monitor_result.json"), {"business_date": trade_date, "status": "PASS", "safety_state": "ALLOW"})
    write_json(paths.dated("reconciliation_result", trade_date, "reconciliation_result.json"), {"business_date": trade_date, "status": "PASS", "classification": "PASS"})

    run_daily_report(trade_date=trade_date, root=tmp_path)

    public = (tmp_path / "reports" / trade_date / "public_report.md").read_text(encoding="utf-8")
    payload = json.loads((tmp_path / "reports" / trade_date / "line_payload.json").read_text(encoding="utf-8"))
    refs = json.loads((tmp_path / "daily_report_refs" / trade_date / "daily_report_refs.json").read_text(encoding="utf-8"))
    assert refs["operation_day_type"] == "INCOMPLETE_OPERATION_DAY"
    assert "## Candidate Top50" not in public
    assert "## 翌営業日の購入予定候補 Top5" not in public
    assert "通常運用が完了していません" in public
    assert payload["operation_day_type"] == "INCOMPLETE_OPERATION_DAY"
    assert payload["buy_candidates"] == []
