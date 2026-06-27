from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

import scripts.run_aifundlab_daily_paper_trading as cli
from ai_fund_lab_v2.paper_trading.human_review_artifact import create_human_review_request
from ai_fund_lab_v2.paper_trading.ledger import PaperTradingLedger, load_ledger, write_ledger
from ai_fund_lab_v2.paper_trading.pending_order_creator import PENDING_ORDERS_CREATED, PENDING_ORDERS_DEDUP_SKIPPED, create_pending_orders_from_approved_review


def test_calendar_missing_fetch_success_allows_runner(tmp_path: Path, monkeypatch, capsys) -> None:
    ledger_path = _write_ledger(tmp_path)
    calendar_path = tmp_path / "calendar.parquet"
    pd.DataFrame([{"Date": "2026-06-21", "HolDiv": "0"}]).to_parquet(calendar_path, index=False)
    calls: list[dict[str, object]] = []

    def fake_refresh(**kwargs):
        calls.append(kwargs)
        pd.DataFrame([{"Date": "2026-06-21", "HolDiv": "0"}, {"Date": "2026-06-22", "HolDiv": "1"}]).to_parquet(calendar_path, index=False)
        return {"attempted": True, "status": "COMPLETED", "hol_div": "1"}

    class FakeResult:
        status = "UNIFIED_DAILY_RUNNER_COMPLETED"

        def to_dict(self):
            return {"status": self.status, "run_date": "2026-06-22", "step_statuses": {"virtual_fill_context": {"fill_execution_dates": ["2026-06-22"]}}}

    monkeypatch.setattr(cli, "refresh_trading_calendar_for_guard", fake_refresh)
    monkeypatch.setattr(cli, "run_unified_daily_paper_trading", lambda **kwargs: FakeResult())

    rc = cli.main(
        [
            "--date",
            "2026-06-22",
            "--mode",
            "dry-run",
            "--allow-api-fetch",
            "--ledger-path",
            str(ledger_path),
            "--operation-root",
            str(tmp_path / ".runtime" / "daily_operation"),
            "--runtime-dir",
            str(tmp_path / ".runtime"),
            "--trading-calendar-path",
            str(calendar_path),
        ],
        now=datetime(2026, 6, 22, 20, 0, tzinfo=ZoneInfo("Asia/Tokyo")),
    )
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert calls and calls[0]["run_date"] == "2026-06-22"
    assert payload["status"] == "UNIFIED_DAILY_RUNNER_COMPLETED"


def test_calendar_fetch_after_missing_still_missing_blocks(tmp_path: Path, monkeypatch, capsys) -> None:
    ledger_path = _write_ledger(tmp_path)
    calendar_path = tmp_path / "calendar.parquet"
    pd.DataFrame([{"Date": "2026-06-21", "HolDiv": "0"}]).to_parquet(calendar_path, index=False)

    monkeypatch.setattr(cli, "refresh_trading_calendar_for_guard", lambda **kwargs: {"attempted": True, "status": "NO_RECORDS_RETURNED"})
    rc = cli.main(
        [
            "--date",
            "2026-06-22",
            "--mode",
            "dry-run",
            "--allow-api-fetch",
            "--ledger-path",
            str(ledger_path),
            "--operation-root",
            str(tmp_path / ".runtime" / "daily_operation"),
            "--runtime-dir",
            str(tmp_path / ".runtime"),
            "--trading-calendar-path",
            str(calendar_path),
        ],
        now=datetime(2026, 6, 22, 20, 0, tzinfo=ZoneInfo("Asia/Tokyo")),
    )
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload["status"] == cli.TRADING_CALENDAR_NOT_READY_BLOCKED
    assert payload["calendar_status"]["reason"] == "TRADING_CALENDAR_DATE_MISSING"
    assert payload["calendar_refresh_status"]["status"] == "NO_RECORDS_RETURNED"


def test_holiday_and_weekend_are_non_business_day_skipped(tmp_path: Path, capsys) -> None:
    ledger_path = _write_ledger(tmp_path)
    calendar_path = tmp_path / "calendar.parquet"
    pd.DataFrame([{"Date": "2026-06-20", "HolDiv": "0"}, {"Date": "2026-09-21", "HolDiv": "0"}]).to_parquet(calendar_path, index=False)

    for day in ("2026-06-20", "2026-09-21"):
        cli.main(
            [
                "--date",
                day,
                "--mode",
                "paper-trading",
                "--ledger-path",
                str(ledger_path),
                "--operation-root",
                str(tmp_path / ".runtime" / "daily_operation"),
                "--runtime-dir",
                str(tmp_path / ".runtime"),
                "--trading-calendar-path",
                str(calendar_path),
            ],
            now=datetime(2026, 6, 22, 20, 0, tzinfo=ZoneInfo("Asia/Tokyo")),
        )
        payload = json.loads(capsys.readouterr().out)
        assert payload["status"] == cli.NON_BUSINESS_DAY_SKIPPED


def test_calendar_fetch_failure_blocks(tmp_path: Path, monkeypatch, capsys) -> None:
    ledger_path = _write_ledger(tmp_path)
    calendar_path = tmp_path / "calendar.parquet"

    def fake_refresh(**kwargs):
        return {"attempted": True, "status": "FETCH_FAILED", "error_type": "RuntimeError"}

    monkeypatch.setattr(cli, "refresh_trading_calendar_for_guard", fake_refresh)
    rc = cli.main(
        [
            "--date",
            "2026-06-22",
            "--mode",
            "dry-run",
            "--allow-api-fetch",
            "--ledger-path",
            str(ledger_path),
            "--operation-root",
            str(tmp_path / ".runtime" / "daily_operation"),
            "--runtime-dir",
            str(tmp_path / ".runtime"),
            "--trading-calendar-path",
            str(calendar_path),
        ],
        now=datetime(2026, 6, 22, 20, 0, tzinfo=ZoneInfo("Asia/Tokyo")),
    )
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload["status"] == cli.TRADING_CALENDAR_NOT_READY_BLOCKED
    assert payload["calendar_refresh_status"]["status"] == "FETCH_FAILED"


def test_refresh_trading_calendar_for_guard_writes_target_date(tmp_path: Path) -> None:
    calendar_path = tmp_path / "calendar.parquet"
    fetcher = _FakeCalendarFetcher([{"Date": "2026-06-22", "HolDiv": "1"}])

    result = cli.refresh_trading_calendar_for_guard(
        run_date="2026-06-22",
        allow_api_fetch=True,
        runtime_dir=tmp_path / ".runtime",
        calendar_path=calendar_path,
        fetcher=fetcher,
    )
    status = cli.jquants_business_day_status(datetime(2026, 6, 22, tzinfo=ZoneInfo("Asia/Tokyo")).date(), calendar_path=calendar_path, fail_closed=True)

    assert fetcher.calls == [("2026-06-22", "2026-06-22")]
    assert result["status"] == "COMPLETED"
    assert status["is_business_day"] is True
    assert status["hol_div"] == "1"


def test_same_decision_for_rerun_still_dedups_pending_orders(tmp_path: Path) -> None:
    ledger_path = _write_ledger(tmp_path)
    order_plan = _write_order_plan(tmp_path)
    review = create_human_review_request(
        order_plan_path=order_plan,
        decision_for="2026-06-19",
        virtual_order_date="2026-06-22",
        output_root=tmp_path / "review",
    )
    approved = _with_review_status(Path(review.json_path), tmp_path / "approved.json")

    first = create_pending_orders_from_approved_review(ledger_path=ledger_path, order_plan_path=order_plan, human_review_path=approved, runtime_dir=tmp_path / ".runtime")
    second = create_pending_orders_from_approved_review(
        ledger_path=tmp_path / ".runtime" / "phase9" / "ledger" / "latest.json",
        order_plan_path=order_plan,
        human_review_path=approved,
        runtime_dir=tmp_path / ".runtime",
    )
    latest = load_ledger(tmp_path / ".runtime" / "phase9" / "ledger" / "latest.json")

    assert first.status == PENDING_ORDERS_CREATED
    assert second.status == PENDING_ORDERS_DEDUP_SKIPPED
    assert len(latest.pending_orders) == 1


class _FakeCalendarFetcher:
    def __init__(self, records):
        self.records = records
        self.calls: list[tuple[str, str]] = []

    def fetch_trading_calendar(self, *, from_date: str, to_date: str):
        self.calls.append((from_date, to_date))
        return self.records


def _write_ledger(tmp_path: Path) -> Path:
    return write_ledger(PaperTradingLedger(cash=Decimal("1000000")), runtime_dir=tmp_path / ".runtime")


def _write_order_plan(tmp_path: Path) -> Path:
    path = tmp_path / "order_plan.json"
    payload = {
        "decision_for": "2026-06-19",
        "virtual_execution_date": "2026-06-22",
        "executable": False,
        "live_order_allowed": False,
        "requires_human_review": True,
        "items": [{"order_id": "order_53670", "code": "53670", "side": "BUY", "quantity": 100, "planned_amount": 160900}],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _with_review_status(source: Path, target: Path) -> Path:
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["review_status"] = "approved"
    target.write_text(json.dumps(payload), encoding="utf-8")
    return target
