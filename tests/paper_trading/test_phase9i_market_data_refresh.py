from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from ai_fund_lab_v2.paper_trading.market_data_refresh import run_market_data_refresh


class MockFetcher:
    def __init__(self, *, fail: bool = False, fail_dates: set[str] | None = None, empty_dates: set[str] | None = None) -> None:
        self.fail = fail
        self.fail_dates = fail_dates or set()
        self.empty_dates = empty_dates or set()
        self.calls: list[str] = []

    def fetch_daily_quotes(self, *, from_date: str, to_date: str):
        self.calls.append("daily_quotes")
        if self.fail:
            raise RuntimeError("mock failure")
        return [
            {"Date": to_date, "Code": "72030", "AdjO": 100, "AdjH": 110, "AdjL": 95, "AdjC": 105, "AdjVo": 1000}
        ]

    def fetch_daily_quotes_for_date(self, *, target_date: str):
        self.calls.append(f"daily_quotes:{target_date}")
        if target_date in self.fail_dates:
            raise RuntimeError("mock date failure")
        if target_date in self.empty_dates:
            return []
        return [
            {"Date": target_date, "Code": "72030", "AdjO": 100, "AdjH": 110, "AdjL": 95, "AdjC": 105, "AdjVo": 1000}
        ]

    def fetch_listed_info(self, *, date: str):
        self.calls.append("listed_info")
        return [{"Date": date, "Code": "72030", "CompanyName": "Toyota"}]

    def fetch_trading_calendar(self, *, from_date: str, to_date: str):
        self.calls.append("trading_calendar")
        current = date.fromisoformat(from_date)
        end = date.fromisoformat(to_date)
        rows = []
        while current <= end:
            if current.weekday() < 5:
                rows.append({"Date": current.isoformat(), "HolDiv": "1"})
            current += timedelta(days=1)
        return rows


def test_dry_run_no_api_call_and_no_overwrite(tmp_path: Path) -> None:
    fetcher = MockFetcher()
    result = run_market_data_refresh(
        from_date="2026-06-02",
        to_date="2026-06-16",
        dry_run=True,
        raw_output_root=tmp_path / "raw",
        normalized_output_root=tmp_path / "raw_normalized",
        manifest_output_root=tmp_path / "manifest",
        fetcher=fetcher,
        today="2026-06-16",
        markdown_report_path=tmp_path / "report.md",
        json_report_path=tmp_path / "report.json",
    )

    assert result.status == "DRY_RUN"
    assert result.jquants_api_fetch_executed is False
    assert fetcher.calls == []
    assert not (tmp_path / "raw/jquants/equities_bars_daily/data.parquet").exists()
    assert Path(result.manifest_path).exists()


def test_allow_api_fetch_required_when_not_dry_run(tmp_path: Path) -> None:
    result = run_market_data_refresh(
        from_date="2026-06-02",
        to_date="2026-06-16",
        dry_run=False,
        allow_api_fetch=False,
        raw_output_root=tmp_path / "raw",
        normalized_output_root=tmp_path / "raw_normalized",
        manifest_output_root=tmp_path / "manifest",
        today="2026-06-16",
        markdown_report_path=tmp_path / "report.md",
        json_report_path=tmp_path / "report.json",
    )

    assert result.status == "BLOCKED"
    assert "allow_api_fetch_required" in result.blocked_reasons
    assert result.jquants_api_fetch_executed is False


def test_date_range_validation_and_future_to_date_blocked(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        run_market_data_refresh(
            from_date="2026-06-17",
            to_date="2026-06-16",
            raw_output_root=tmp_path / "raw",
            normalized_output_root=tmp_path / "raw_normalized",
            manifest_output_root=tmp_path / "manifest",
            today="2026-06-16",
            markdown_report_path=tmp_path / "report.md",
            json_report_path=tmp_path / "report.json",
        )
    with pytest.raises(ValueError):
        run_market_data_refresh(
            from_date="2026-06-16",
            to_date="2026-06-17",
            raw_output_root=tmp_path / "raw2",
            normalized_output_root=tmp_path / "raw_normalized2",
            manifest_output_root=tmp_path / "manifest2",
            today="2026-06-16",
            markdown_report_path=tmp_path / "report2.md",
            json_report_path=tmp_path / "report2.json",
        )


def test_manifest_fields_backup_readiness_and_no_secret_leakage(tmp_path: Path) -> None:
    existing_path = tmp_path / "raw/jquants/equities_bars_daily/data.parquet"
    existing_path.parent.mkdir(parents=True)
    import pandas as pd

    pd.DataFrame([{"Date": "2026-06-15", "Code": "72030", "AdjO": 90, "AdjH": 95, "AdjL": 85, "AdjC": 92, "AdjVo": 900}]).to_parquet(
        existing_path, index=False
    )

    result = run_market_data_refresh(
        from_date="2026-06-16",
        to_date="2026-06-16",
        dry_run=False,
        allow_api_fetch=True,
        raw_output_root=tmp_path / "raw",
        normalized_output_root=tmp_path / "raw_normalized",
        manifest_output_root=tmp_path / "manifest",
        backup_existing=True,
        fetcher=MockFetcher(),
        today="2026-06-16",
        markdown_report_path=tmp_path / "report.md",
        json_report_path=tmp_path / "report.json",
    )

    payload = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))
    assert payload["from_date"] == "2026-06-16"
    assert payload["to_date"] == "2026-06-16"
    assert payload["endpoints"][0]["backup_path"]
    assert payload["readiness_result"]["status"] == "READY"
    assert payload["jquants_api_fetch_executed"] is True
    manifest_text = Path(result.manifest_path).read_text(encoding="utf-8").lower()
    assert "api_key" not in manifest_text
    assert "x-api-key" not in manifest_text
    assert "authorization" not in manifest_text


def test_partial_failure_status_and_prohibited_flags(tmp_path: Path) -> None:
    result = run_market_data_refresh(
        from_date="2026-06-16",
        to_date="2026-06-16",
        dry_run=False,
        allow_api_fetch=True,
        raw_output_root=tmp_path / "raw",
        normalized_output_root=tmp_path / "raw_normalized",
        manifest_output_root=tmp_path / "manifest",
        fetcher=MockFetcher(fail=True),
        today="2026-06-16",
        markdown_report_path=tmp_path / "report.md",
        json_report_path=tmp_path / "report.json",
    )

    assert result.status == "PARTIAL"
    assert any(reason.startswith("api_fetch_failed") for reason in result.blocked_reasons)
    assert result.broker_order_api_called is False
    assert result.open_d_started is False
    assert result.unlock_trade_called is False
    assert result.virtual_fill_executed is False
    assert result.model_retraining_executed is False
    assert result.inference_executed is False


def test_per_date_fetch_records_success_and_tail_not_yet_available(tmp_path: Path) -> None:
    result = run_market_data_refresh(
        from_date="2026-06-15",
        to_date="2026-06-16",
        dry_run=False,
        allow_api_fetch=True,
        fetch_mode="per-date",
        raw_output_root=tmp_path / "raw",
        normalized_output_root=tmp_path / "raw_normalized",
        manifest_output_root=tmp_path / "manifest",
        fetcher=MockFetcher(empty_dates={"2026-06-16"}),
        today="2026-06-16",
        markdown_report_path=tmp_path / "report.md",
        json_report_path=tmp_path / "report.json",
    )

    assert result.status == "PARTIAL_AVAILABLE"
    assert result.latest_successful_daily_quotes_date == "2026-06-15"
    assert result.not_yet_available_dates == ("2026-06-16",)
    assert result.latest_normalized_daily_quotes_date == "2026-06-15"


def test_per_date_fetch_uses_trading_calendar_business_days_only(tmp_path: Path) -> None:
    import pandas as pd

    calendar_path = tmp_path / "raw/jquants/trading_calendar/data.parquet"
    calendar_path.parent.mkdir(parents=True)
    pd.DataFrame(
        [
            {"Date": "2026-06-14", "HolDiv": "0"},
            {"Date": "2026-06-15", "HolDiv": "1"},
            {"Date": "2026-06-16", "HolDiv": "1"},
        ]
    ).to_parquet(calendar_path, index=False)
    fetcher = MockFetcher(empty_dates={"2026-06-16"})

    result = run_market_data_refresh(
        from_date="2026-06-14",
        to_date="2026-06-16",
        dry_run=False,
        allow_api_fetch=True,
        fetch_mode="per-date",
        raw_output_root=tmp_path / "raw",
        normalized_output_root=tmp_path / "raw_normalized",
        manifest_output_root=tmp_path / "manifest",
        fetcher=fetcher,
        today="2026-06-16",
        markdown_report_path=tmp_path / "report.md",
        json_report_path=tmp_path / "report.json",
    )

    assert result.required_dates == ("2026-06-15", "2026-06-16")
    assert "daily_quotes:2026-06-14" not in fetcher.calls


def test_per_date_all_single_date_failures_are_api_param_error(tmp_path: Path) -> None:
    result = run_market_data_refresh(
        from_date="2026-06-15",
        to_date="2026-06-16",
        dry_run=False,
        allow_api_fetch=True,
        fetch_mode="per-date",
        raw_output_root=tmp_path / "raw",
        normalized_output_root=tmp_path / "raw_normalized",
        manifest_output_root=tmp_path / "manifest",
        fetcher=MockFetcher(fail_dates={"2026-06-15", "2026-06-16"}),
        today="2026-06-16",
        markdown_report_path=tmp_path / "report.md",
        json_report_path=tmp_path / "report.json",
    )

    assert result.status in {"API_PARAM_ERROR", "FETCH_FAILED"}
    assert result.latest_successful_daily_quotes_date == ""
    assert result.failed_dates or result.not_yet_available_dates
