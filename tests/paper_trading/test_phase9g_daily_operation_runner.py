from decimal import Decimal
from pathlib import Path

from ai_fund_lab_v2.data_store.storage_backends import JsonlStorageBackend
from ai_fund_lab_v2.paper_trading.daily_operation_runner import run_daily_operation
from ai_fund_lab_v2.paper_trading.ledger import PaperTradingLedger, PendingOrderState, write_ledger


def test_daily_operation_dry_run_succeeds(tmp_path: Path) -> None:
    daily, listed, quotes, ledger_path = _fixtures(tmp_path)
    result = run_daily_operation(
        run_date="2026-06-17",
        mode="dry-run",
        operation_root=tmp_path / "operation",
        runtime_dir=tmp_path / ".runtime",
        reports_root=tmp_path / "reports",
        ledger_path=ledger_path,
        quotes_path=quotes,
        daily_quotes_path=daily,
        listed_info_path=listed,
    )
    assert result.status == "OK"
    assert Path(result.operation_log_json_path).exists()
    assert result.fill_result is not None
    assert result.fill_result.dry_run is True
    assert result.broker_order_api_called is False
    assert result.open_d_started is False
    assert result.unlock_trade_called is False


def test_daily_operation_report_only_succeeds(tmp_path: Path) -> None:
    daily, listed, _, _ = _fixtures(tmp_path)
    result = run_daily_operation(
        run_date="2026-06-17",
        mode="report-only",
        operation_root=tmp_path / "operation",
        runtime_dir=tmp_path / ".runtime_report",
        reports_root=tmp_path / "reports",
        daily_quotes_path=daily,
        listed_info_path=listed,
    )
    assert result.status == "OK"
    assert result.pipeline_result is not None
    assert result.fill_result is None


def test_daily_operation_fill_only_runs_with_mock_ledger_and_quotes(tmp_path: Path) -> None:
    _, _, quotes, ledger_path = _fixtures(tmp_path)
    result = run_daily_operation(
        run_date="2026-06-17",
        mode="fill-only",
        operation_root=tmp_path / "operation",
        runtime_dir=tmp_path / ".runtime_fill",
        reports_root=tmp_path / "reports",
        ledger_path=ledger_path,
        quotes_path=quotes,
    )
    assert result.status == "OK"
    assert result.fill_result is not None
    assert result.fill_result.executions
    assert result.broker_order_api_called is False


def _fixtures(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    backend = JsonlStorageBackend()
    daily = tmp_path / "daily_quotes.jsonl"
    listed = tmp_path / "listed_info.jsonl"
    quotes = tmp_path / "fill_quotes.jsonl"
    backend.write_records(daily, [{"Date": "2026-06-17", "Code": "7203", "Open": 2000, "High": 2100, "Low": 1990, "Close": 2050, "Volume": 1000}])
    backend.write_records(listed, [{"Date": "2026-06-17", "Code": "7203"}])
    backend.write_records(quotes, [{"Date": "2026-06-17", "Code": "7203", "Open": 2000}])
    ledger = PaperTradingLedger(
        cash=Decimal("300000"),
        pending_orders=(PendingOrderState(code="7203", side="BUY", quantity=Decimal("100"), status="APPROVED"),),
    )
    ledger_path = write_ledger(ledger, tmp_path / ".runtime_source")
    return daily, listed, quotes, ledger_path

