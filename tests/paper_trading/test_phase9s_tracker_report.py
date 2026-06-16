from __future__ import annotations

from pathlib import Path

from ai_fund_lab_v2.paper_trading.tracker_report_writer import write_tracker_reports


def test_phase9s_tracker_report_writer_saves_markdown(tmp_path: Path) -> None:
    tracker = {
        "entries": [
            {
                "business_day_index": 1,
                "run_date": "2026-06-16",
                "status": "FIRST_VIRTUAL_FILL_DONE",
                "paper_total_equity": "1000000",
                "cash": "283330.0",
                "market_value": "716670.0",
                "unrealized_pnl": "0",
                "trade_count": 5,
                "positions": 5,
            }
        ]
    }

    tracker_path, report_path = write_tracker_reports(
        tracker=tracker,
        tracker_markdown_path=tmp_path / "tracker.md",
        report_markdown_path=tmp_path / "report.md",
    )

    assert Path(tracker_path).is_file()
    assert Path(report_path).read_text(encoding="utf-8").startswith("# Phase9 30 Business Day Tracker")
