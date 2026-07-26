from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from ai_fund_lab_v2.paper_trading.market_data_refresh import run_market_data_refresh
from ai_fund_lab_v2.runtime_v2.market_data_acquisition import (
    PRODUCTION_REFRESH_ADAPTER_VERSION,
    run_acquisition,
    sha256_file,
)


def _v2_row(day: str, code: str = "13010") -> dict[str, Any]:
    return {
        "Date": day,
        "Code": code,
        "Open": 100.0,
        "High": 105.0,
        "Low": 95.0,
        "Close": 102.0,
        "Volume": 1000.0,
        "AdjustmentOpen": 110.0,
        "AdjustmentHigh": 115.0,
        "AdjustmentLow": 105.0,
        "AdjustmentClose": 112.0,
        "AdjustmentVolume": 900.0,
    }


class ProductionFixtureFetcher:
    def __init__(self) -> None:
        self.daily_dates: list[str] = []

    def fetch_daily_quotes_for_date(self, *, target_date: str) -> list[dict[str, Any]]:
        self.daily_dates.append(target_date)
        return [_v2_row(target_date)]

    def fetch_daily_quotes(self, *, from_date: str, to_date: str) -> list[dict[str, Any]]:
        return [_v2_row(to_date)]

    def fetch_listed_info(self, *, date: str) -> list[dict[str, Any]]:
        return [{"Date": date, "Code": "13010", "CoName": "Fixture", "Mkt": "0111"}]

    def fetch_trading_calendar(self, *, from_date: str, to_date: str) -> list[dict[str, Any]]:
        return [{"Date": to_date, "HolDiv": "1"}]


def test_phase20_bf_production_market_refresh_core_processes_v2_aliases(tmp_path: Path) -> None:
    result = run_market_data_refresh(
        from_date="2026-07-01",
        to_date="2026-07-01",
        dry_run=False,
        allow_api_fetch=True,
        fetch_mode="per-date",
        raw_output_root=tmp_path / "raw",
        normalized_output_root=tmp_path / "raw_normalized",
        manifest_output_root=tmp_path / "manifest",
        backup_existing=False,
        fetcher=ProductionFixtureFetcher(),
        today="2026-07-01",
        markdown_report_path=tmp_path / "report.md",
        json_report_path=tmp_path / "report.json",
    )

    raw = pd.read_parquet(tmp_path / "raw/jquants/equities_bars_daily/data.parquet")
    normalized = pd.read_parquet(tmp_path / "raw_normalized/jquants/equities_bars_daily/data.parquet")
    assert result.status == "MARKET_DATA_READY_FOR_LATEST_AVAILABLE"
    assert raw.iloc[0]["O"] == 100.0
    assert raw.iloc[0]["AdjO"] == 110.0
    assert normalized.iloc[0]["Open"] == 110.0
    assert normalized.iloc[0]["PriceSource"] == "adjusted"


def test_phase20_bf_historical_adapter_uses_staging_and_preserves_production_operations(tmp_path: Path) -> None:
    runtime_root = tmp_path / ".runtime"
    production_path = runtime_root / "operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet"
    production_path.parent.mkdir(parents=True)
    pd.DataFrame(
        [
            {
                "Date": "2026-06-30",
                "Code": "13010",
                "Open": 1.0,
                "High": 1.0,
                "Low": 1.0,
                "Close": 1.0,
                "Volume": 1.0,
                "PriceSource": "adjusted",
                "SchemaVersion": 2,
            }
        ]
    ).to_parquet(production_path, index=False)
    before_hash = sha256_file(production_path)

    result = run_acquisition(
        runtime_root=runtime_root,
        start_date="2026-07-01",
        end_date="2026-07-01",
        run_id="bf-staging-isolation",
        staging_root=tmp_path / "runs",
        evidence_root=tmp_path / "evidence",
        confirm=True,
        explicit_fetch_confirm=True,
        fetcher=ProductionFixtureFetcher(),
    )

    assert result["final_judgment"] == "ACQUISITION_SOURCE_READY"
    assert result["processing_authority"] == "PRODUCTION_MARKET_REFRESH_CORE"
    assert result["production_refresh_adapter_version"] == PRODUCTION_REFRESH_ADAPTER_VERSION
    assert Path(result["raw_output_path"]).is_file()
    assert Path(result["normalized_output_path"]).is_file()
    assert sha256_file(production_path) == before_hash
