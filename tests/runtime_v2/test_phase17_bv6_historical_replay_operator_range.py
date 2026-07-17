from __future__ import annotations

from pathlib import Path

import pandas as pd

from scripts.runtime_test import build_parser, load_profile, resolve_business_dates


def test_phase17_bv6_plan_accepts_end_date_alias() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            "plan",
            "--profile",
            "historical-extended-smoke",
            "--date-from",
            "2021-07-16",
            "--end-date",
            "2021-07-30",
        ]
    )

    assert args.date_from == "2021-07-16"
    assert args.date_to == "2021-07-30"


def test_phase17_bv6_range_uses_trading_calendar_authority(tmp_path: Path) -> None:
    runtime_root = tmp_path / ".runtime"
    calendar_path = runtime_root / "operations/jquants/historical_snapshots/trading_calendar/data.parquet"
    calendar_path.parent.mkdir(parents=True)
    pd.DataFrame(
        [
            {"Date": "2021-07-16", "HolDiv": "1"},
            {"Date": "2021-07-17", "HolDiv": "0"},
            {"Date": "2021-07-18", "HolDiv": "0"},
            {"Date": "2021-07-19", "HolDiv": "1"},
            {"Date": "2021-07-20", "HolDiv": "1"},
            {"Date": "2021-07-21", "HolDiv": "1"},
            {"Date": "2021-07-22", "HolDiv": "0"},
            {"Date": "2021-07-23", "HolDiv": "0"},
            {"Date": "2021-07-26", "HolDiv": "1"},
            {"Date": "2021-07-27", "HolDiv": "1"},
            {"Date": "2021-07-28", "HolDiv": "1"},
            {"Date": "2021-07-29", "HolDiv": "1"},
            {"Date": "2021-07-30", "HolDiv": "1"},
            {"Date": "2021-08-02", "HolDiv": "1"},
        ]
    ).to_parquet(calendar_path, index=False)
    profile = load_profile("historical-extended-smoke")

    assert resolve_business_dates(
        profile=profile,
        runtime_root=runtime_root,
        business_days=None,
        start_date=None,
        date_from="2021-07-16",
        date_to="2021-07-30",
    ) == [
        "2021-07-16",
        "2021-07-19",
        "2021-07-20",
        "2021-07-21",
        "2021-07-26",
        "2021-07-27",
        "2021-07-28",
        "2021-07-29",
        "2021-07-30",
    ]

    assert resolve_business_dates(
        profile=profile,
        runtime_root=runtime_root,
        business_days=10,
        start_date="2021-07-16",
        date_from=None,
        date_to=None,
    )[-1] == "2021-08-02"
