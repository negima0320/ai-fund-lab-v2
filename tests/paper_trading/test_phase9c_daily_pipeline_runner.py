from pathlib import Path

from ai_fund_lab_v2.data_store.storage_backends import JsonlStorageBackend
from ai_fund_lab_v2.paper_trading.daily_pipeline_runner import run_daily_pipeline


def test_daily_pipeline_generates_manifest_and_reports(tmp_path: Path) -> None:
    daily, listed = _write_fixtures(tmp_path, day="2026-06-16")
    result = run_daily_pipeline(
        run_date="2026-06-16",
        runtime_dir=tmp_path / ".runtime",
        reports_root=tmp_path / "reports",
        daily_quotes_path=daily,
        listed_info_path=listed,
    )
    assert result.status == "OK"
    assert Path(result.manifest_path).exists()
    assert Path(result.internal_report_md_path).exists()
    assert Path(result.public_report_path).exists()
    assert Path(result.blog_draft_path).exists()
    assert result.broker_order_api_called is False
    assert result.open_d_started is False
    assert result.unlock_trade_called is False
    assert result.paper_ledger_fill_executed is False
    assert result.live_order_allowed is False


def test_daily_pipeline_halt_generates_reports_when_market_data_missing(tmp_path: Path) -> None:
    _, listed = _write_fixtures(tmp_path, day="2026-06-16")
    result = run_daily_pipeline(
        run_date="2026-06-16",
        runtime_dir=tmp_path / ".runtime",
        reports_root=tmp_path / "reports",
        daily_quotes_path=tmp_path / "missing.jsonl",
        listed_info_path=listed,
    )
    assert result.status == "HALT"
    assert result.market_data.status == "NOT_READY"
    assert Path(result.manifest_path).exists()
    assert Path(result.internal_report_md_path).exists()
    assert Path(result.public_report_path).exists()
    assert Path(result.blog_draft_path).exists()


def test_daily_pipeline_invalid_for_future_row(tmp_path: Path) -> None:
    daily, listed = _write_fixtures(tmp_path, day="2026-06-17")
    result = run_daily_pipeline(
        run_date="2026-06-16",
        runtime_dir=tmp_path / ".runtime",
        reports_root=tmp_path / "reports",
        daily_quotes_path=daily,
        listed_info_path=listed,
    )
    assert result.status == "HALT"
    assert result.market_data.status == "INVALID"
    assert "future_row_detected" in result.market_data.blocked_reasons


def _write_fixtures(tmp_path: Path, *, day: str) -> tuple[Path, Path]:
    backend = JsonlStorageBackend()
    daily = tmp_path / "daily_quotes.jsonl"
    listed = tmp_path / "listed_info.jsonl"
    backend.write_records(
        daily,
        [{"Date": day, "Code": "7203", "Open": 100, "High": 110, "Low": 99, "Close": 108, "Volume": 1000}],
    )
    backend.write_records(listed, [{"Date": "2026-06-16", "Code": "7203"}])
    return daily, listed

