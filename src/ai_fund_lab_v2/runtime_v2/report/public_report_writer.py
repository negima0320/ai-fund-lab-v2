"""Public report writer facade for Runtime v2."""

from __future__ import annotations

from pathlib import Path

from ai_fund_lab_v2.runtime_v2.report.markdown_writer import (
    build_markdown_reports,
    load_runtime_v2_report_context,
    scan_public_report,
    write_markdown_reports,
)


def generate_public_report_from_current(
    *,
    runtime_root: Path | str = Path(".runtime"),
    runtime_output_dir: Path | str,
    public_output_dir: Path | str,
    business_date: str | None = None,
    write_latest: bool = True,
) -> dict[str, object]:
    """Generate Runtime v2 Markdown/Public reports from fixed Current paths."""

    context = load_runtime_v2_report_context(runtime_root, business_date=business_date)
    return write_markdown_reports(
        context,
        runtime_output_dir=runtime_output_dir,
        public_output_dir=public_output_dir,
        write_latest=write_latest,
    )


__all__ = [
    "build_markdown_reports",
    "generate_public_report_from_current",
    "load_runtime_v2_report_context",
    "scan_public_report",
    "write_markdown_reports",
]
