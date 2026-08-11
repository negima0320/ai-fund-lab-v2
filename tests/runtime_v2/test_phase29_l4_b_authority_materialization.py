from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.runtime_v2.historical_support.listed_issues_snapshots import (
    resolve_listed_issues_snapshot,
)
from ai_fund_lab_v2.runtime_v2.source_authority_materialization import (
    materialize_listed_issues_authority,
    materialize_trading_calendar_authority,
    reconcile_calendar_with_quotes,
)


def _load_runner():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "runtime_test.py"
    spec = importlib.util.spec_from_file_location("runtime_test_runner", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_l4_b_materializes_listed_staging_without_future_snapshot_fallback(tmp_path: Path) -> None:
    runtime_root = tmp_path / "runtime"
    staging = tmp_path / "listed.parquet"
    pd.DataFrame(
        [
            {"Date": "2026-07-31", "Code": "13010", "CoName": "A", "Mkt": "0111"},
            {"Date": "2026-08-07", "Code": "13010", "CoName": "A", "Mkt": "0111"},
        ]
    ).to_parquet(staging, index=False)

    result = materialize_listed_issues_authority(
        runtime_root=runtime_root,
        staging_path=staging,
        requested_start_date="2026-07-31",
        requested_end_date="2026-08-07",
        confirm=True,
    )
    snapshot_root = runtime_root / "operations" / "jquants" / "historical_snapshots" / "listed_issues"

    assert result["status"] == "PASS"
    assert (runtime_root / "operations" / "jquants" / "raw" / "jquants" / "listed_issues" / "data.parquet").is_file()
    assert resolve_listed_issues_snapshot(snapshot_root=snapshot_root, business_date="2026-08-07").status == "PASS"
    assert resolve_listed_issues_snapshot(snapshot_root=snapshot_root, business_date="2026-07-30").reason == "no_snapshot_not_after_business_date"


def test_l4_b_calendar_materialization_uses_validated_staging_over_stale_base_and_reconciles_quotes(tmp_path: Path) -> None:
    runtime_root = tmp_path / "runtime"
    staging = tmp_path / "calendar.parquet"
    historical_root = runtime_root / "operations" / "jquants" / "historical_snapshots" / "trading_calendar"
    historical_root.mkdir(parents=True)
    pd.DataFrame(
        [
            {"Date": "2026-04-28", "HolDiv": "1"},
            {"Date": "2026-04-29", "HolDiv": "1"},
            {"Date": "2026-04-30", "HolDiv": "1"},
        ]
    ).to_parquet(historical_root / "data.parquet", index=False)
    pd.DataFrame(
        [
            {"Date": "2026-04-28", "HolDiv": "1"},
            {"Date": "2026-04-29", "HolDiv": "3"},
            {"Date": "2026-04-30", "HolDiv": "1"},
        ]
    ).to_parquet(staging, index=False)
    quote_path = runtime_root / "operations" / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet"
    quote_path.parent.mkdir(parents=True)
    pd.DataFrame(
        [
            {"Date": "2026-04-28", "Code": "13010", "Close": 1.0},
            {"Date": "2026-04-30", "Code": "13010", "Close": 1.0},
        ]
    ).to_parquet(quote_path, index=False)

    result = materialize_trading_calendar_authority(
        runtime_root=runtime_root,
        staging_path=staging,
        requested_start_date="2026-04-28",
        requested_end_date="2026-04-30",
        confirm=True,
    )
    operations = pd.read_parquet(runtime_root / "operations" / "jquants" / "raw" / "jquants" / "trading_calendar" / "data.parquet")

    assert result["status"] == "PASS"
    assert operations.loc[operations["Date"].astype(str) == "2026-04-29", "HolDiv"].astype(str).iloc[0] == "3"
    assert result["quote_calendar_reconciliation"]["status"] == "PASS"


def test_l4_b_quote_calendar_reconciliation_blocks_open_zero_and_closed_quotes(tmp_path: Path) -> None:
    quote_path = tmp_path / "quotes.parquet"
    pd.DataFrame(
        [
            {"Date": "2026-07-06", "Code": "13010"},
            {"Date": "2026-07-08", "Code": "13010"},
        ]
    ).to_parquet(quote_path, index=False)
    calendar = pd.DataFrame(
        [
            {"Date": "2026-07-06", "HolDiv": "1"},
            {"Date": "2026-07-07", "HolDiv": "1"},
            {"Date": "2026-07-08", "HolDiv": "3"},
        ]
    )

    result = reconcile_calendar_with_quotes(
        calendar_frame=calendar,
        quote_path=quote_path,
        start_date="2026-07-06",
        end_date="2026-07-08",
    )

    assert result["status"] == "REVIEW_REQUIRED"
    assert {item["reason"] for item in result["ambiguous_dates"]} == {
        "calendar_open_quote_rows_zero",
        "calendar_closed_quote_rows_present",
    }


def test_l4_b_runtime_plan_marks_calendar_quote_ambiguity_review_required(tmp_path: Path) -> None:
    runner = _load_runner()
    runtime_root = tmp_path / "runtime"
    historical_root = runtime_root / "operations" / "jquants" / "historical_snapshots" / "trading_calendar"
    historical_root.mkdir(parents=True)
    pd.DataFrame(
            [
                {"Date": "2026-07-06", "HolDiv": "1"},
                {"Date": "2026-07-07", "HolDiv": "1"},
                {"Date": "2026-07-08", "HolDiv": "3"},
            ]
        ).to_parquet(historical_root / "data.parquet", index=False)
    quote_path = runtime_root / "operations" / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet"
    quote_path.parent.mkdir(parents=True)
    pd.DataFrame([{"Date": "2026-07-06", "Code": "13010"}, {"Date": "2026-07-08", "Code": "13010"}]).to_parquet(quote_path, index=False)

    window = runner.resolve_business_window(
        profile=runner.load_profile("historical-smoke"),
        runtime_root=runtime_root,
        business_days=2,
        start_date="2026-07-06",
        date_from=None,
        date_to=None,
    )

    assert window["window_resolution_status"] == "REVIEW_REQUIRED"
    assert window["window_resolution_reason"] == "calendar_quote_reconciliation_ambiguity"
