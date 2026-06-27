from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pandas as pd

import scripts.run_aifundlab_daily_paper_trading as cli


def test_phase9u2_resolve_jst_business_date_weekday() -> None:
    assert cli.resolve_jst_business_date(datetime(2026, 6, 16, 9, 0, tzinfo=ZoneInfo("Asia/Tokyo"))) == "2026-06-16"


def test_phase9u2_resolve_jst_business_date_weekend_to_previous_friday() -> None:
    assert cli.resolve_jst_business_date(datetime(2026, 6, 20, 9, 0, tzinfo=ZoneInfo("Asia/Tokyo"))) == "2026-06-19"
    assert cli.resolve_jst_business_date(datetime(2026, 6, 21, 9, 0, tzinfo=ZoneInfo("Asia/Tokyo"))) == "2026-06-19"


def test_phase9u2_cli_accepts_no_date_for_launchd(monkeypatch, tmp_path) -> None:
    captured: dict[str, object] = {}
    calendar_path = tmp_path / "trading_calendar.parquet"
    pd.DataFrame([{"Date": "2026-06-16", "HolDiv": "1"}]).to_parquet(calendar_path, index=False)

    def fake_resolve(now: datetime | None = None) -> str:
        return "2026-06-16"

    def fake_run(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(status="UNIFIED_DAILY_RUNNER_COMPLETED", to_dict=lambda: {"status": "UNIFIED_DAILY_RUNNER_COMPLETED", "run_date": kwargs["run_date"]})

    monkeypatch.setattr(cli, "resolve_jst_business_date", fake_resolve)
    monkeypatch.setattr(cli, "run_unified_daily_paper_trading", fake_run)

    assert cli.main(["--trading-calendar-path", str(calendar_path)], now=datetime(2026, 6, 16, 20, 0, tzinfo=ZoneInfo("Asia/Tokyo"))) == 0
    assert captured["run_date"] == "2026-06-16"


def test_phase9u2_cli_manual_date_overrides_default(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(status="UNIFIED_DAILY_RUNNER_COMPLETED", to_dict=lambda: {"status": "UNIFIED_DAILY_RUNNER_COMPLETED", "run_date": kwargs["run_date"]})

    monkeypatch.setattr(cli, "resolve_jst_business_date", lambda: "2026-06-16")
    monkeypatch.setattr(cli, "run_unified_daily_paper_trading", fake_run)

    assert cli.main(["--date", "2026-06-15"]) == 0
    assert captured["run_date"] == "2026-06-15"
