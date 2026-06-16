from __future__ import annotations

from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.paper_trading.feature_refresh import FEATURES_READY, FEATURE_REFRESH_REQUIRED, run_feature_refresh


def _write_quotes(path: Path, *, start: str = "2026-05-01", periods: int = 30) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    dates = pd.bdate_range(start, periods=periods)
    for code in ("10010", "10020"):
        price = 100.0
        for day in dates:
            price += 1.0
            rows.append(
                {
                    "Date": day.strftime("%Y-%m-%d"),
                    "target_date": day.strftime("%Y-%m-%d"),
                    "Code": code,
                    "code": code,
                    "Open": price - 0.5,
                    "High": price + 1.0,
                    "Low": price - 1.0,
                    "Close": price,
                    "Volume": 1000,
                }
            )
    pd.DataFrame(rows).to_parquet(path, index=False)


def _write_listed(path: Path, *, date: str = "2026-06-15") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"Date": date, "target_date": date, "Code": "10010", "code": "10010"}]).to_parquet(path, index=False)


def test_dry_run_reports_refresh_required_without_generation(tmp_path: Path) -> None:
    result = run_feature_refresh(
        target_data_until="2026-06-15",
        dry_run=True,
        execute=False,
        daily_quotes_path=tmp_path / "quotes.parquet",
        listed_info_path=tmp_path / "listed.parquet",
        feature_output_root=tmp_path / "features",
        manifest_root=tmp_path / "manifest",
        markdown_report_path=tmp_path / "report.md",
        json_report_path=tmp_path / "report.json",
    )

    assert result.status == FEATURE_REFRESH_REQUIRED
    assert result.feature_generation_executed is False
    assert (tmp_path / "manifest/2026-06-15/feature_refresh_manifest.json").is_file()


def test_execute_generates_phase9_feature_artifacts(tmp_path: Path) -> None:
    quotes_path = tmp_path / "jquants/quotes.parquet"
    listed_path = tmp_path / "jquants/listed.parquet"
    _write_quotes(quotes_path)
    _write_listed(listed_path)

    result = run_feature_refresh(
        target_data_until="2026-06-11",
        dry_run=False,
        execute=True,
        daily_quotes_path=quotes_path,
        listed_info_path=listed_path,
        feature_output_root=tmp_path / "features",
        manifest_root=tmp_path / "manifest",
        markdown_report_path=tmp_path / "report.md",
        json_report_path=tmp_path / "report.json",
    )

    assert result.status == FEATURES_READY
    assert result.feature_generation_executed is True
    assert all(item.feature_schema_hash for item in result.artifacts)
    assert all(item.future_leakage_check_status == "OK" for item in result.artifacts)
    assert (tmp_path / "features/2026-06-11/candidate_features.parquet").is_file()
    assert result.model_retraining_executed is False
    assert result.inference_executed is False
    assert result.order_plan_generation_executed is False
    assert result.broker_order_api_called is False


def test_execute_detects_insufficient_lookback(tmp_path: Path) -> None:
    quotes_path = tmp_path / "jquants/quotes.parquet"
    listed_path = tmp_path / "jquants/listed.parquet"
    _write_quotes(quotes_path, start="2026-06-01", periods=10)
    _write_listed(listed_path)

    result = run_feature_refresh(
        target_data_until="2026-06-12",
        dry_run=False,
        execute=True,
        daily_quotes_path=quotes_path,
        listed_info_path=listed_path,
        feature_output_root=tmp_path / "features",
        manifest_root=tmp_path / "manifest",
        markdown_report_path=tmp_path / "report.md",
        json_report_path=tmp_path / "report.json",
    )

    assert result.status == FEATURE_REFRESH_REQUIRED
    assert "candidate_no_universe_eligible_rows" in result.blocked_reasons
    assert "opportunity_feature_values_all_null" in result.blocked_reasons


def test_future_rows_are_ignored_during_generation(tmp_path: Path) -> None:
    quotes_path = tmp_path / "jquants/quotes.parquet"
    listed_path = tmp_path / "jquants/listed.parquet"
    _write_quotes(quotes_path, start="2026-05-01", periods=35)
    _write_listed(listed_path)

    result = run_feature_refresh(
        target_data_until="2026-06-11",
        dry_run=False,
        execute=True,
        daily_quotes_path=quotes_path,
        listed_info_path=listed_path,
        feature_output_root=tmp_path / "features",
        manifest_root=tmp_path / "manifest",
        markdown_report_path=tmp_path / "report.md",
        json_report_path=tmp_path / "report.json",
    )

    assert result.status == FEATURES_READY
    assert all(item.max_date == "2026-06-11" for item in result.artifacts)
