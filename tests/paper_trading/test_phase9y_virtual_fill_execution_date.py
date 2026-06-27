from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.paper_trading.first_virtual_fill import DATA_NOT_READY, FIRST_VIRTUAL_FILL_EXECUTED, run_first_virtual_fill
from ai_fund_lab_v2.paper_trading.ledger import PaperTradingLedger, PendingOrderState, load_ledger, write_ledger
from ai_fund_lab_v2.paper_trading.unified_daily_runner import run_unified_daily_paper_trading


def test_run_date_later_uses_pending_virtual_execution_date_open(tmp_path: Path) -> None:
    ledger_path = _write_ledger(
        tmp_path,
        orders=(PendingOrderState(code="10010", side="BUY", quantity=Decimal("100"), status="APPROVED", virtual_execution_date="2026-06-22"),),
    )
    quotes_path = _write_quotes(
        tmp_path,
        rows=[
            _quote("2026-06-22", "10010", 1000),
            _quote("2026-06-23", "10010", 2000),
        ],
    )

    result = run_unified_daily_paper_trading(
        run_date="2026-06-23",
        ledger_path=ledger_path,
        mode="fill-only",
        runtime_dir=tmp_path / ".runtime",
        operation_root=tmp_path / ".runtime" / "daily_operation",
        quotes_path=quotes_path,
        reports_root=tmp_path / "reports",
        phase_report_markdown_path=tmp_path / "phase9u.md",
        phase_report_json_path=tmp_path / "phase9u.json",
        skip_feature_refresh=True,
        skip_inference=True,
        skip_tracker_update=True,
        skip_blog_report_v2=True,
    )
    latest = load_ledger(tmp_path / ".runtime" / "phase9" / "ledger" / "latest.json")

    assert result.step_statuses["virtual_fill"] == FIRST_VIRTUAL_FILL_EXECUTED
    assert result.step_statuses["virtual_fill_context"]["run_date"] == "2026-06-23"
    assert result.step_statuses["virtual_fill_context"]["fill_execution_dates"] == ["2026-06-22"]
    assert latest.cash == Decimal("900000")
    assert latest.positions[0].average_cost == Decimal("1000")


def test_missing_virtual_execution_date_quotes_keeps_pending_even_if_run_date_quotes_exist(tmp_path: Path) -> None:
    ledger_path = _write_ledger(
        tmp_path,
        orders=(PendingOrderState(code="10010", side="BUY", quantity=Decimal("100"), status="APPROVED", virtual_execution_date="2026-06-22"),),
    )
    quotes_path = _write_quotes(tmp_path, rows=[_quote("2026-06-23", "10010", 2000)])

    result = run_first_virtual_fill(
        ledger_path=ledger_path,
        quotes_path=quotes_path,
        execution_date="2026-06-22",
        run_date="2026-06-23",
        mode="execute",
        runtime_dir=tmp_path / ".runtime",
        docs_report_path=tmp_path / "fill.md",
        json_report_path=tmp_path / "fill.json",
        public_summary_path=tmp_path / "fill_public.md",
    )
    latest = load_ledger(tmp_path / ".runtime" / "phase9" / "ledger" / "latest.json")

    assert result.status == DATA_NOT_READY
    assert result.run_date == "2026-06-23"
    assert result.fill_execution_date == "2026-06-22"
    assert latest.cash == Decimal("1000000")
    assert len(latest.pending_orders) == 1
    assert latest.pending_orders[0].virtual_execution_date == "2026-06-22"


def test_processor_does_not_fill_older_order_with_run_date_open(tmp_path: Path) -> None:
    ledger_path = _write_ledger(
        tmp_path,
        orders=(PendingOrderState(code="10010", side="BUY", quantity=Decimal("100"), status="APPROVED", virtual_execution_date="2026-06-22"),),
    )
    quotes_path = _write_quotes(tmp_path, rows=[_quote("2026-06-23", "10010", 2000)])

    result = run_unified_daily_paper_trading(
        run_date="2026-06-23",
        ledger_path=ledger_path,
        mode="fill-only",
        runtime_dir=tmp_path / ".runtime",
        operation_root=tmp_path / ".runtime" / "daily_operation",
        quotes_path=quotes_path,
        reports_root=tmp_path / "reports",
        phase_report_markdown_path=tmp_path / "phase9u.md",
        phase_report_json_path=tmp_path / "phase9u.json",
        skip_feature_refresh=True,
        skip_inference=True,
        skip_tracker_update=True,
        skip_blog_report_v2=True,
    )
    latest = load_ledger(tmp_path / ".runtime" / "phase9" / "ledger" / "latest.json")

    assert result.step_statuses["virtual_fill"] == DATA_NOT_READY
    assert "virtual_fill_data_not_ready:2026-06-22" in result.blocked_reasons
    assert latest.cash == Decimal("1000000")
    assert len(latest.positions) == 0
    assert len(latest.pending_orders) == 1


def test_mixed_virtual_execution_dates_are_grouped_by_date(tmp_path: Path) -> None:
    ledger_path = _write_ledger(
        tmp_path,
        orders=(
            PendingOrderState(code="10010", side="BUY", quantity=Decimal("100"), status="APPROVED", virtual_execution_date="2026-06-22"),
            PendingOrderState(code="20020", side="BUY", quantity=Decimal("100"), status="APPROVED", virtual_execution_date="2026-06-23"),
        ),
    )
    quotes_path = _write_quotes(
        tmp_path,
        rows=[
            _quote("2026-06-22", "10010", 1000),
            _quote("2026-06-22", "20020", 9999),
            _quote("2026-06-23", "10010", 9999),
            _quote("2026-06-23", "20020", 2000),
        ],
    )

    result = run_unified_daily_paper_trading(
        run_date="2026-06-23",
        ledger_path=ledger_path,
        mode="fill-only",
        runtime_dir=tmp_path / ".runtime",
        operation_root=tmp_path / ".runtime" / "daily_operation",
        quotes_path=quotes_path,
        reports_root=tmp_path / "reports",
        phase_report_markdown_path=tmp_path / "phase9u.md",
        phase_report_json_path=tmp_path / "phase9u.json",
        skip_feature_refresh=True,
        skip_inference=True,
        skip_tracker_update=True,
        skip_blog_report_v2=True,
    )
    latest = load_ledger(tmp_path / ".runtime" / "phase9" / "ledger" / "latest.json")
    costs = {position.code: position.average_cost for position in latest.positions}

    assert result.step_statuses["virtual_fill"] == "VIRTUAL_FILL_GROUPS_PROCESSED"
    assert result.step_statuses["virtual_fill_context"]["fill_execution_dates"] == ["2026-06-22", "2026-06-23"]
    assert costs == {"10010": Decimal("1000"), "20020": Decimal("2000")}
    assert latest.cash == Decimal("700000")


def test_run_date_and_fill_execution_date_are_separated_in_manifest(tmp_path: Path) -> None:
    ledger_path = _write_ledger(
        tmp_path,
        orders=(PendingOrderState(code="10010", side="BUY", quantity=Decimal("100"), status="APPROVED", virtual_execution_date="2026-06-22"),),
    )
    quotes_path = _write_quotes(tmp_path, rows=[_quote("2026-06-22", "10010", 1000)])

    result = run_first_virtual_fill(
        ledger_path=ledger_path,
        quotes_path=quotes_path,
        execution_date="2026-06-22",
        run_date="2026-06-23",
        mode="dry-run",
        runtime_dir=tmp_path / ".runtime",
        docs_report_path=tmp_path / "fill.md",
        json_report_path=tmp_path / "fill.json",
        public_summary_path=tmp_path / "fill_public.md",
    )
    manifest = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))

    assert result.run_date == "2026-06-23"
    assert result.fill_execution_date == "2026-06-22"
    assert manifest["run_date"] == "2026-06-23"
    assert manifest["fill_execution_date"] == "2026-06-22"
    assert manifest["execution_date"] == "2026-06-22"


def _write_ledger(tmp_path: Path, *, orders: tuple[PendingOrderState, ...]) -> Path:
    ledger = PaperTradingLedger(cash=Decimal("1000000"), pending_orders=orders)
    return write_ledger(ledger, runtime_dir=tmp_path / ".runtime")


def _write_quotes(tmp_path: Path, *, rows: list[dict[str, object]]) -> Path:
    path = tmp_path / "quotes.parquet"
    pd.DataFrame(rows).to_parquet(path, index=False)
    return path


def _quote(date: str, code: str, open_price: int) -> dict[str, object]:
    return {"date": date, "code": code, "open": open_price, "high": open_price, "low": open_price, "close": open_price, "volume": 1000}
