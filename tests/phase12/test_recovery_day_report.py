from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.operations.io import OperationPaths, write_json
from ai_fund_lab_v2.operations.operations import run_daily_report


def test_recovery_day_report_mentions_next_morning_plan_and_suppresses_candidate_sections(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    paths = OperationPaths(tmp_path)
    trade_date = "2026-07-01"
    feature = tmp_path / "candidate_features.parquet"
    feature.write_text("placeholder", encoding="utf-8")
    write_json(paths.dated("daily_manifest", trade_date, "daily_manifest.json"), {"business_date": trade_date, "recovery_day": True})
    write_json(paths.dated("market_refresh", trade_date, "market_refresh_manifest.json"), {"business_date": trade_date, "status": "PASS"})
    write_json(paths.dated("daily_plan", trade_date, "daily_plan_result.json"), {"business_date": trade_date, "status": "PASS"})
    write_json(paths.dated("order_plan", trade_date, "order_plan.json"), {"business_date": trade_date, "status": "PASS", "buy_item_count": 1, "items": [], "feature_candidate_audit": {"candidate_count": 10, "candidate_feature_path": str(feature)}})
    write_json(paths.dated("approval_artifact", trade_date, "approval_artifact.json"), {"business_date": trade_date, "status": "APPROVED"})
    write_json(paths.dated("submitted_orders", trade_date, "submitted_orders.json"), {"business_date": trade_date, "status": "PASS", "submit_run_date": trade_date, "order_plan_source_date": trade_date, "approval_source_date": trade_date, "submitted_orders": []})
    write_json(paths.dated("fill_events", trade_date, "fill_events.json"), {"business_date": trade_date, "status": "PASS", "fill_events": []})
    write_json(paths.dated("safety_monitor", trade_date, "safety_monitor_result.json"), {"business_date": trade_date, "status": "PASS", "safety_state": "ALLOW"})
    write_json(paths.dated("reconciliation_result", trade_date, "reconciliation_result.json"), {"business_date": trade_date, "status": "PASS", "classification": "PASS"})
    write_json(paths.dir("audit_result") / "audit_result.json", {"status": "PASS", "demo_production_parity_audit": {"status": "PASS", "unexpected_differences": []}})

    run_daily_report(trade_date=trade_date, root=tmp_path)

    public = (tmp_path / "reports" / trade_date / "public_report.md").read_text(encoding="utf-8")
    payload = json.loads((tmp_path / "reports" / trade_date / "line_payload.json").read_text(encoding="utf-8"))
    assert "Market Calendar誤判定からのリカバリ日" in public
    assert "明朝Submit" in public
    assert "## Candidate Top50" not in public
    assert payload["operation_day_type"] == "RECOVERY_DAY"
    assert payload["notification_mode"] == "RECOVERY_COMPLETE_NOTICE"
