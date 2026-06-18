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


def _write_listed(path: Path, *, date: str = "2026-06-01", codes: tuple[str, ...] = ("10010", "10020")) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "Date": date,
                "target_date": date,
                "Code": code,
                "code": code,
                "CoName": f"普通株{code}",
                "ProdCat": "011",
                "MktNm": "プライム",
            }
            for code in codes
        ]
    ).to_parquet(path, index=False)


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


def test_candidate_universe_hard_gate_excludes_non_current_stale_missing_name_and_non_stock(tmp_path: Path) -> None:
    quotes_path = tmp_path / "jquants/quotes.parquet"
    listed_path = tmp_path / "jquants/listed.parquet"
    quotes_path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for code in ("10010", "10020", "10030", "10040", "14000"):
        for day in pd.bdate_range("2026-05-01", "2026-06-16"):
            if code == "14000" and day.strftime("%Y-%m-%d") > "2026-06-10":
                continue
            rows.append(
                {
                    "Date": day.strftime("%Y-%m-%d"),
                    "target_date": day.strftime("%Y-%m-%d"),
                    "Code": code,
                    "code": code,
                    "Close": 100.0,
                    "Volume": 1000,
                }
            )
    pd.DataFrame(rows).to_parquet(quotes_path, index=False)
    pd.DataFrame(
        [
            {"Date": "2026-06-16", "target_date": "2026-06-16", "Code": "10010", "code": "10010", "CoName": "普通株A", "ProdCat": "011", "MktNm": "プライム"},
            {"Date": "2026-06-16", "target_date": "2026-06-16", "Code": "10020", "code": "10020", "CoName": "", "ProdCat": "011", "MktNm": "プライム"},
            {"Date": "2026-06-16", "target_date": "2026-06-16", "Code": "10030", "code": "10030", "CoName": "ETF", "ProdCat": "014", "MktNm": "その他"},
            {"Date": "2026-06-16", "target_date": "2026-06-16", "Code": "10040", "code": "10040", "CoName": "REIT", "ProdCat": "013", "MktNm": "その他"},
        ]
    ).to_parquet(listed_path, index=False)

    result = run_feature_refresh(
        target_data_until="2026-06-16",
        dry_run=False,
        execute=True,
        daily_quotes_path=quotes_path,
        listed_info_path=listed_path,
        feature_output_root=tmp_path / "features",
        manifest_root=tmp_path / "manifest",
        markdown_report_path=tmp_path / "report.md",
        json_report_path=tmp_path / "report.json",
    )
    candidate = pd.read_parquet(tmp_path / "features/2026-06-16/candidate_features.parquet")
    by_code = {row["code"]: row for row in candidate.to_dict(orient="records")}

    assert result.status == FEATURES_READY
    assert bool(by_code["10010"]["universe_eligible"]) is True
    assert bool(by_code["10020"]["universe_eligible"]) is False
    assert "missing_name" in by_code["10020"]["universe_exclusion_reason"]
    assert bool(by_code["10030"]["universe_eligible"]) is False
    assert "disallowed_product" in by_code["10030"]["universe_exclusion_reason"]
    assert bool(by_code["10040"]["universe_eligible"]) is False
    assert "disallowed_product" in by_code["10040"]["universe_exclusion_reason"]
    assert bool(by_code["14000"]["universe_eligible"]) is False
    assert "not_current_listed" in by_code["14000"]["universe_exclusion_reason"]
    assert "stale_price" in by_code["14000"]["universe_exclusion_reason"]
    assert "14000" not in set(candidate[candidate["universe_eligible"].astype(bool)]["code"])
