from __future__ import annotations

from ai_fund_lab_v2.operations.operations import run_daily_report, run_market_refresh


def test_daily_report_includes_market_closed_message(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    trade_date = "2026-09-21"

    run_market_refresh(trade_date=trade_date, root=tmp_path)
    report = run_daily_report(trade_date=trade_date, root=tmp_path)

    refs_path = report["daily_report_refs_path"]
    text = refs_path and (tmp_path / "reports" / trade_date / "blog_draft.md").read_text(encoding="utf-8")
    assert "MARKET_CLOSED_DAY" in text
    assert "市場休場日のため" in text
    assert "## Candidate Top50" not in text
