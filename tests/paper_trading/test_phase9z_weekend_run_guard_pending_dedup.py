from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

import scripts.run_aifundlab_daily_paper_trading as cli
from ai_fund_lab_v2.paper_trading.human_review_artifact import create_human_review_request
from ai_fund_lab_v2.paper_trading.ledger import PaperTradingLedger, PendingOrderState, load_ledger, write_ledger
from ai_fund_lab_v2.paper_trading.pending_order_creator import PENDING_ORDERS_CREATED, PENDING_ORDERS_DEDUP_SKIPPED, create_pending_orders_from_approved_review
from ai_fund_lab_v2.paper_trading.pending_order_dedup import dedup_pending_orders_in_ledger_file
from ai_fund_lab_v2.paper_trading.unified_daily_runner import run_unified_daily_paper_trading


def test_saturday_no_date_paper_trading_is_skipped_without_rounding_to_friday(tmp_path: Path, capsys) -> None:
    ledger_path = _write_ledger(tmp_path, orders=())
    calendar = _write_calendar(
        tmp_path,
        [
            {"Date": "2026-06-20", "HolDiv": "0"},
        ],
    )
    rc = cli.main(
        [
            "--mode",
            "paper-trading",
            "--ledger-path",
            str(ledger_path),
            "--operation-root",
            str(tmp_path / ".runtime" / "daily_operation"),
            "--runtime-dir",
            str(tmp_path / ".runtime"),
            "--trading-calendar-path",
            str(calendar),
        ],
        now=datetime(2026, 6, 20, 20, 0, tzinfo=ZoneInfo("Asia/Tokyo")),
    )
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload["status"] == cli.NON_BUSINESS_DAY_SKIPPED
    assert payload["run_date"] == "2026-06-20"
    assert payload["calendar_status"]["hol_div"] == "0"
    assert payload["step_statuses"]["pending_order_creation"] == 0
    assert not (tmp_path / ".runtime" / "daily_operation" / "runs" / "2026-06-19").exists()
    assert (tmp_path / ".runtime" / "daily_operation" / "runs" / "2026-06-20" / "unified_daily_run_manifest.json").is_file()
    assert len(load_ledger(ledger_path).pending_orders) == 0


def test_sunday_no_date_paper_trading_is_skipped(tmp_path: Path, capsys) -> None:
    ledger_path = _write_ledger(tmp_path, orders=())
    calendar = _write_calendar(tmp_path, [{"Date": "2026-06-21", "HolDiv": "0"}])

    rc = cli.main(
        [
            "--mode",
            "paper-trading",
            "--ledger-path",
            str(ledger_path),
            "--operation-root",
            str(tmp_path / ".runtime" / "daily_operation"),
            "--runtime-dir",
            str(tmp_path / ".runtime"),
            "--trading-calendar-path",
            str(calendar),
        ],
        now=datetime(2026, 6, 21, 20, 0, tzinfo=ZoneInfo("Asia/Tokyo")),
    )
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload["status"] == cli.NON_BUSINESS_DAY_SKIPPED
    assert payload["run_date"] == "2026-06-21"
    assert payload["calendar_status"]["hol_div"] == "0"
    assert len(load_ledger(ledger_path).pending_orders) == 0


def test_calendar_missing_blocks_for_no_date_paper_trading(tmp_path: Path, capsys) -> None:
    ledger_path = _write_ledger(tmp_path, orders=())
    missing_calendar = tmp_path / "missing_calendar.parquet"

    rc = cli.main(
        [
            "--mode",
            "paper-trading",
            "--ledger-path",
            str(ledger_path),
            "--operation-root",
            str(tmp_path / ".runtime" / "daily_operation"),
            "--runtime-dir",
            str(tmp_path / ".runtime"),
            "--trading-calendar-path",
            str(missing_calendar),
        ],
        now=datetime(2026, 6, 22, 20, 0, tzinfo=ZoneInfo("Asia/Tokyo")),
    )
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload["status"] == cli.TRADING_CALENDAR_NOT_READY_BLOCKED
    assert payload["calendar_status"]["reason"] == "TRADING_CALENDAR_MISSING"
    assert payload["calendar_status"]["is_business_day"] is False


def test_trading_calendar_holiday_is_non_business_day(tmp_path: Path) -> None:
    calendar = tmp_path / "calendar.parquet"
    pd.DataFrame([{"Date": "2026-09-21", "HolDiv": "0"}, {"Date": "2026-09-24", "HolDiv": "1"}]).to_parquet(calendar, index=False)

    assert cli.is_business_day_jst(datetime(2026, 9, 21, tzinfo=ZoneInfo("Asia/Tokyo")).date(), calendar_path=calendar) is False
    assert cli.is_business_day_jst(datetime(2026, 9, 24, tzinfo=ZoneInfo("Asia/Tokyo")).date(), calendar_path=calendar) is True


def test_holiday_no_date_paper_trading_is_skipped_without_pending_creation(tmp_path: Path, capsys) -> None:
    ledger_path = _write_ledger(tmp_path, orders=())
    calendar = _write_calendar(tmp_path, [{"Date": "2026-09-21", "HolDiv": "0"}])

    rc = cli.main(
        [
            "--mode",
            "paper-trading",
            "--ledger-path",
            str(ledger_path),
            "--operation-root",
            str(tmp_path / ".runtime" / "daily_operation"),
            "--runtime-dir",
            str(tmp_path / ".runtime"),
            "--trading-calendar-path",
            str(calendar),
        ],
        now=datetime(2026, 9, 21, 20, 0, tzinfo=ZoneInfo("Asia/Tokyo")),
    )
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload["status"] == cli.NON_BUSINESS_DAY_SKIPPED
    assert payload["run_date"] == "2026-09-21"
    assert payload["step_statuses"]["daily_inference"] == "SKIPPED_NON_BUSINESS_DAY"
    assert payload["step_statuses"]["tracker_update"] == "SKIPPED_NON_BUSINESS_DAY"
    assert payload["step_statuses"]["blog_report_v2"] == "SKIPPED_NON_BUSINESS_DAY"
    assert len(load_ledger(ledger_path).pending_orders) == 0


def test_explicit_holiday_paper_trading_date_is_skipped(tmp_path: Path, capsys) -> None:
    ledger_path = _write_ledger(tmp_path, orders=())
    calendar = _write_calendar(tmp_path, [{"Date": "2026-09-21", "HolDiv": "0"}])

    rc = cli.main(
        [
            "--date",
            "2026-09-21",
            "--mode",
            "paper-trading",
            "--ledger-path",
            str(ledger_path),
            "--operation-root",
            str(tmp_path / ".runtime" / "daily_operation"),
            "--runtime-dir",
            str(tmp_path / ".runtime"),
            "--trading-calendar-path",
            str(calendar),
        ],
        now=datetime(2026, 9, 22, 20, 0, tzinfo=ZoneInfo("Asia/Tokyo")),
    )
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload["status"] == cli.NON_BUSINESS_DAY_SKIPPED
    assert payload["run_date"] == "2026-09-21"
    assert payload["calendar_status"]["hol_div"] == "0"
    assert len(load_ledger(ledger_path).pending_orders) == 0


def test_business_day_after_holiday_runs_normally(tmp_path: Path, monkeypatch, capsys) -> None:
    ledger_path = _write_ledger(tmp_path, orders=())
    calendar = _write_calendar(
        tmp_path,
        [
            {"Date": "2026-09-21", "HolDiv": "0"},
            {"Date": "2026-09-24", "HolDiv": "1"},
        ],
    )
    calls = []

    class FakeResult:
        status = "UNIFIED_DAILY_RUNNER_COMPLETED"

        def to_dict(self):
            return {"status": self.status, "run_date": "2026-09-24", "step_statuses": {"pending_order_creation": 0}}

    def fake_runner(**kwargs):
        calls.append(kwargs)
        return FakeResult()

    monkeypatch.setattr(cli, "run_unified_daily_paper_trading", fake_runner)
    rc = cli.main(
        [
            "--mode",
            "paper-trading",
            "--ledger-path",
            str(ledger_path),
            "--operation-root",
            str(tmp_path / ".runtime" / "daily_operation"),
            "--runtime-dir",
            str(tmp_path / ".runtime"),
            "--trading-calendar-path",
            str(calendar),
        ],
        now=datetime(2026, 9, 24, 20, 0, tzinfo=ZoneInfo("Asia/Tokyo")),
    )
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload["status"] == "UNIFIED_DAILY_RUNNER_COMPLETED"
    assert calls[0]["run_date"] == "2026-09-24"


def test_same_decision_for_pending_creation_is_idempotent(tmp_path: Path) -> None:
    ledger_path = _write_ledger(tmp_path, orders=())
    order_plan = _write_order_plan(tmp_path)
    review = create_human_review_request(
        order_plan_path=order_plan,
        decision_for="2026-06-19",
        virtual_order_date="2026-06-22",
        output_root=tmp_path / "review",
    )
    approved = _with_review_status(Path(review.json_path), "approved", tmp_path / "approved.json")

    first = create_pending_orders_from_approved_review(
        ledger_path=ledger_path,
        order_plan_path=order_plan,
        human_review_path=approved,
        runtime_dir=tmp_path / ".runtime",
    )
    second = create_pending_orders_from_approved_review(
        ledger_path=tmp_path / ".runtime" / "phase9" / "ledger" / "latest.json",
        order_plan_path=order_plan,
        human_review_path=approved,
        runtime_dir=tmp_path / ".runtime",
    )
    latest = load_ledger(tmp_path / ".runtime" / "phase9" / "ledger" / "latest.json")

    assert first.status == PENDING_ORDERS_CREATED
    assert first.pending_order_count == 5
    assert second.status == PENDING_ORDERS_DEDUP_SKIPPED
    assert second.pending_order_count == 0
    assert second.dedup_skipped_count == 5
    assert len(latest.pending_orders) == 5


def test_duplicate_pending_10_dedup_to_5_without_cash_positions_trade_count_change(tmp_path: Path) -> None:
    ledger_path = _write_duplicate_ledger(tmp_path)
    before = load_ledger(ledger_path)

    result = dedup_pending_orders_in_ledger_file(ledger_path=ledger_path, runtime_dir=tmp_path / ".runtime", backup=True)
    after = load_ledger(tmp_path / ".runtime" / "phase9" / "ledger" / "latest.json")

    assert result.before_pending_count == 10
    assert result.after_pending_count == 5
    assert result.removed_count == 5
    assert Path(result.backup_path).is_file()
    assert after.cash == before.cash
    assert len(after.positions) == len(before.positions)
    assert after.performance.trade_count == before.performance.trade_count
    assert len(after.pending_orders) == 5


def test_monday_due_pending_still_fills_by_virtual_execution_date_open(tmp_path: Path) -> None:
    ledger_path = _write_ledger(
        tmp_path,
        orders=(PendingOrderState(code="53670", side="BUY", quantity=Decimal("100"), status="APPROVED", virtual_execution_date="2026-06-22"),),
    )
    quotes_path = _write_quotes(tmp_path, rows=[_quote("2026-06-22", "53670", 1600), _quote("2026-06-23", "53670", 2000)])

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

    assert result.step_statuses["virtual_fill_context"]["fill_execution_dates"] == ["2026-06-22"]
    assert latest.positions[0].average_cost == Decimal("1600")


def _write_ledger(tmp_path: Path, *, orders: tuple[PendingOrderState, ...]) -> Path:
    ledger = PaperTradingLedger(cash=Decimal("1000000"), pending_orders=orders)
    return write_ledger(ledger, runtime_dir=tmp_path / ".runtime")


def _write_calendar(tmp_path: Path, rows: list[dict[str, str]]) -> Path:
    path = tmp_path / "calendar.parquet"
    pd.DataFrame(rows).to_parquet(path, index=False)
    return path


def _write_duplicate_ledger(tmp_path: Path) -> Path:
    orders = []
    for suffix in ("old", "new"):
        for code, qty, amount in (("53670", "100", "160900"), ("69660", "100", "120000"), ("63360", "100", "194800"), ("72450", "100", "149100"), ("32370", "2100", "197400")):
            orders.append(
                PendingOrderState(
                    order_id=f"{suffix}_{code}",
                    code=code,
                    side="BUY",
                    quantity=Decimal(qty),
                    planned_amount=Decimal(amount),
                    status="APPROVED",
                    created_at=f"2026-06-{'19' if suffix == 'old' else '20'}T11:00:00+00:00",
                    virtual_execution_date="2026-06-22",
                )
            )
    return _write_ledger(tmp_path, orders=tuple(orders))


def _write_order_plan(tmp_path: Path) -> Path:
    path = tmp_path / "order_plan.json"
    payload = {
        "decision_for": "2026-06-19",
        "virtual_execution_date": "2026-06-22",
        "executable": False,
        "live_order_allowed": False,
        "requires_human_review": True,
        "items": [
            {"order_id": f"order_{code}", "code": code, "side": "BUY", "quantity": qty, "planned_amount": amount, "reason": "test"}
            for code, qty, amount in (("53670", 100, 160900), ("69660", 100, 120000), ("63360", 100, 194800), ("72450", 100, 149100), ("32370", 2100, 197400))
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _with_review_status(source: Path, status: str, target: Path) -> Path:
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["review_status"] = status
    target.write_text(json.dumps(payload), encoding="utf-8")
    return target


def _write_quotes(tmp_path: Path, *, rows: list[dict[str, object]]) -> Path:
    path = tmp_path / "quotes.parquet"
    pd.DataFrame(rows).to_parquet(path, index=False)
    return path


def _quote(day: str, code: str, open_price: int) -> dict[str, object]:
    return {"date": day, "code": code, "open": open_price, "high": open_price, "low": open_price, "close": open_price, "volume": 1000}
