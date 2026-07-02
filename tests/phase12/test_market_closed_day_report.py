from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.operations.operations import run_daily_report


def test_market_closed_day_report_uses_closed_mode_without_candidate_sections(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    trade_date = "2026-09-21"

    run_daily_report(trade_date=trade_date, root=tmp_path)

    public = (tmp_path / "reports" / trade_date / "public_report.md").read_text(encoding="utf-8")
    payload = json.loads((tmp_path / "reports" / trade_date / "line_payload.json").read_text(encoding="utf-8"))
    refs = json.loads((tmp_path / "daily_report_refs" / trade_date / "daily_report_refs.json").read_text(encoding="utf-8"))
    assert refs["operation_day_type"] == "MARKET_CLOSED_DAY"
    assert "市場休場日のため" in public
    assert "## Candidate Top50" not in public
    assert "## 翌営業日の購入予定候補 Top5" not in public
    assert payload["notification_mode"] == "MARKET_CLOSED_NOTICE"
