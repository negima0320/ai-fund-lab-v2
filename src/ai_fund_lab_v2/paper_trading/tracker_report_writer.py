from __future__ import annotations

from pathlib import Path
from typing import Any

from ai_fund_lab_v2.paper_trading.business_day_tracker import _render_tracker_markdown


def write_tracker_reports(
    *,
    tracker: dict[str, Any],
    tracker_markdown_path: Path | str,
    report_markdown_path: Path | str,
) -> tuple[str, str]:
    tracker_path = Path(tracker_markdown_path)
    report_path = Path(report_markdown_path)
    tracker_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    markdown = _render_tracker_markdown(tracker)
    tracker_path.write_text(markdown, encoding="utf-8")
    report_path.write_text(markdown, encoding="utf-8")
    return str(tracker_path), str(report_path)
