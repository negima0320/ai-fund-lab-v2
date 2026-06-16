from pathlib import Path

from ai_fund_lab_v2.paper_trading.operation_log import build_operation_log, write_operation_log


def test_operation_log_saved_as_json_and_markdown(tmp_path: Path) -> None:
    log = build_operation_log(
        run_id="run1",
        date="2026-06-17",
        mode="dry-run",
        started_at="2026-06-17T00:00:00+00:00",
        status="OK",
        step_statuses={"data_update": "OK"},
        report_refs={"internal": "report.md"},
    )
    json_path, md_path = write_operation_log(log, tmp_path / "operation")
    assert json_path.exists()
    assert md_path.exists()
    text = md_path.read_text(encoding="utf-8")
    assert "Phase9 Daily Operation Log" in text
    assert "broker_order_api_called: false" in text

