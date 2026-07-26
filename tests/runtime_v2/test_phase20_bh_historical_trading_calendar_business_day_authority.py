from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from ai_fund_lab_v2.paper_trading.market_data_readiness import check_market_data_readiness
from ai_fund_lab_v2.paper_trading.market_data_refresh import run_market_data_refresh
from ai_fund_lab_v2.runtime_v2.market_data_acquisition import resume_acquisition, run_acquisition, validate_staging_source


def _row(day: str, code: str = "13010") -> dict[str, Any]:
    return {
        "Date": day,
        "Code": code,
        "O": 100.0,
        "H": 105.0,
        "L": 95.0,
        "C": 102.0,
        "Vo": 1000.0,
        "AdjO": 110.0,
        "AdjH": 115.0,
        "AdjL": 105.0,
        "AdjC": 112.0,
        "AdjVo": 900.0,
    }


class DecemberCalendarFetcher:
    def __init__(self, *, missing_dates: set[str] | None = None, invalid: bool = False) -> None:
        self.missing_dates = missing_dates or set()
        self.invalid = invalid
        self.daily_dates: list[str] = []

    def fetch_daily_quotes_for_date(self, *, target_date: str) -> list[dict[str, Any]]:
        self.daily_dates.append(target_date)
        if target_date in self.missing_dates:
            return []
        row = _row(target_date)
        if self.invalid:
            row = {"Date": target_date, "Code": "13010"}
        return [row]

    def fetch_daily_quotes(self, *, from_date: str, to_date: str) -> list[dict[str, Any]]:
        return [self.fetch_daily_quotes_for_date(target_date=to_date)[0]]

    def fetch_listed_info(self, *, date: str) -> list[dict[str, Any]]:
        return [{"Date": date, "Code": "13010", "CoName": "Fixture", "Mkt": "0111"}]

    def fetch_trading_calendar(self, *, from_date: str, to_date: str) -> list[dict[str, Any]]:
        del from_date, to_date
        return [
            {"Date": "2021-12-29", "HolDiv": "1"},
            {"Date": "2021-12-30", "HolDiv": "1"},
            {"Date": "2021-12-31", "HolDiv": "0"},
        ]


def test_phase20_bh_trading_calendar_holiday_is_excluded_from_required_dates(tmp_path: Path) -> None:
    fetcher = DecemberCalendarFetcher()
    result = run_market_data_refresh(
        from_date="2021-12-29",
        to_date="2021-12-31",
        dry_run=False,
        allow_api_fetch=True,
        fetch_mode="per-date",
        raw_output_root=tmp_path / "raw",
        normalized_output_root=tmp_path / "raw_normalized",
        manifest_output_root=tmp_path / "manifest",
        backup_existing=False,
        fetcher=fetcher,
        today="2021-12-31",
        markdown_report_path=tmp_path / "report.md",
        json_report_path=tmp_path / "report.json",
    )

    assert result.latest_trading_calendar_date == "2021-12-31"
    assert result.required_dates == ("2021-12-29", "2021-12-30")
    assert result.first_required_date == "2021-12-29"
    assert result.last_required_date == "2021-12-30"
    assert fetcher.daily_dates == ["2021-12-29", "2021-12-30"]


def test_phase20_bh_historical_coverage_uses_last_business_date_not_calendar_last_date(tmp_path: Path) -> None:
    fetcher = DecemberCalendarFetcher()
    result = run_acquisition(
        runtime_root=tmp_path / ".runtime",
        start_date="2021-12-29",
        end_date="2021-12-31",
        run_id="bh-december-holiday",
        staging_root=tmp_path / "runs",
        evidence_root=tmp_path / "evidence",
        confirm=True,
        explicit_fetch_confirm=True,
        fetcher=fetcher,
    )

    assert result["final_judgment"] == "ACQUISITION_SOURCE_READY"
    assert result["final_validation"]["coverage_policy"] == "expected_business_date_range"
    assert result["final_validation"]["coverage_end_date"] == "2021-12-30"
    assert result["final_validation"]["last_expected_business_date"] == "2021-12-30"
    assert result["final_validation"]["expected_business_dates"] == ["2021-12-29", "2021-12-30"]
    assert "2021-12-31" not in fetcher.daily_dates


def test_phase20_bh_missing_real_business_day_blocks(tmp_path: Path) -> None:
    result = run_acquisition(
        runtime_root=tmp_path / ".runtime",
        start_date="2021-12-29",
        end_date="2021-12-31",
        run_id="bh-missing-business-day",
        staging_root=tmp_path / "runs",
        evidence_root=tmp_path / "evidence",
        confirm=True,
        explicit_fetch_confirm=True,
        fetcher=DecemberCalendarFetcher(missing_dates={"2021-12-30"}),
    )

    assert result["status"] == "BLOCK"
    assert result["final_validation"]["coverage_end_date"] == "2021-12-30"
    assert "requested_end_coverage_missing" in result["blocked_reasons"]


def test_phase20_bh_schema_invalid_still_blocks(tmp_path: Path) -> None:
    result = run_acquisition(
        runtime_root=tmp_path / ".runtime",
        start_date="2021-12-29",
        end_date="2021-12-31",
        run_id="bh-invalid-schema",
        staging_root=tmp_path / "runs",
        evidence_root=tmp_path / "evidence",
        confirm=True,
        explicit_fetch_confirm=True,
        fetcher=DecemberCalendarFetcher(invalid=True),
    )

    assert result["status"] == "BLOCK"
    assert "normalized_inventory_not_pass" in result["blocked_reasons"] or "normalized_required_columns_missing" in result["blocked_reasons"]


def test_phase20_bh_lineage_missing_still_blocks(tmp_path: Path) -> None:
    path = tmp_path / "normalized.parquet"
    pd.DataFrame(
        [
            {
                "Date": "2021-12-30",
                "Code": "13010",
                "Open": 1,
                "High": 1,
                "Low": 1,
                "Close": 1,
                "Volume": 1,
                "PriceSource": "adjusted",
                "SchemaVersion": 2,
                "source": "manual",
                "source_endpoint": "/v2/equities/bars/daily",
            }
        ]
    ).to_parquet(path, index=False)

    result = validate_staging_source(
        normalized_path=path,
        requested_start_date="2021-12-29",
        requested_end_date="2021-12-31",
        expected_business_dates=["2021-12-30"],
    )

    assert result["status"] == "BLOCK"
    assert "jquants_lineage_missing" in result["blocked_reasons"]


def test_phase20_bh_production_runtime_freshness_fail_closed_preserved() -> None:
    result = check_market_data_readiness(
        decision_for="2021-12-31",
        daily_quotes_records=[
            {"Date": "2021-12-30", "Code": "13010", "Open": 1, "High": 1, "Low": 1, "Close": 1, "Volume": 1}
        ],
        listed_info_records=[{"Date": "2021-12-31", "Code": "13010"}],
    )

    assert result.status == "NOT_READY"
    assert result.blocked_reasons == ("data_until_before_decision_for",)


def test_phase20_bh_resume_revalidates_failed_chunk_without_refetching_completed_chunk(tmp_path: Path) -> None:
    fetcher = DecemberCalendarFetcher()
    partial = run_acquisition(
        runtime_root=tmp_path / ".runtime",
        start_date="2021-12-29",
        end_date="2021-12-31",
        run_id="bh-resume",
        staging_root=tmp_path / "runs",
        evidence_root=tmp_path / "evidence",
        confirm=True,
        explicit_fetch_confirm=True,
        fetcher=fetcher,
        stop_after_chunks=1,
    )
    assert partial["completed_chunks"] == 1
    first_call_count = len(fetcher.daily_dates)

    state_path = tmp_path / "runs/bh-resume/state.json"
    import json

    state = json.loads(state_path.read_text())
    state["chunks"][0]["status"] = "NORMALIZATION_FAILED"
    state["chunks"][0]["error"] = "production_market_refresh_staging_validation_failed"
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")

    resumed = resume_acquisition(
        runtime_root=tmp_path / ".runtime",
        run_id="bh-resume",
        staging_root=tmp_path / "runs",
        evidence_root=tmp_path / "evidence",
        confirm=True,
        explicit_fetch_confirm=True,
        fetcher=fetcher,
    )

    assert resumed["final_judgment"] == "ACQUISITION_SOURCE_READY"
    assert len(fetcher.daily_dates) == first_call_count
    resumed_state = json.loads(state_path.read_text())
    assert resumed_state["chunks"][0]["status"] == "COMPLETED"
    assert resumed_state["chunks"][0]["historical_policy_validation"]["coverage_end_date"] == "2021-12-30"
