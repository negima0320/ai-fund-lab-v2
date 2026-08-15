from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.paper_trading.feature_refresh import FEATURES_READY, FEATURE_REFRESH_REQUIRED, run_feature_refresh
from ai_fund_lab_v2.runtime_v2.market_refresh.consumer_readiness import validate_feature_consumer_readiness


def _write_quotes(path: Path, *, start: str = "2026-03-02", periods: int = 75) -> None:
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


def test_phase29_l21t_ay_actual_feature_refresh_materializes_av_multi_horizon_columns(tmp_path: Path) -> None:
    quotes_path = tmp_path / "jquants/quotes.parquet"
    listed_path = tmp_path / "jquants/listed.parquet"
    operations_root = tmp_path / "operations"
    _write_quotes(quotes_path)
    _write_listed(listed_path)
    _write_ready_empty_current(tmp_path, "2026-06-11")

    result = run_feature_refresh(
        target_data_until="2026-06-11",
        dry_run=False,
        execute=True,
        daily_quotes_path=quotes_path,
        listed_info_path=listed_path,
        feature_output_root=operations_root / "feature_artifacts",
        manifest_root=operations_root / "feature_refresh_detail",
        markdown_report_path=tmp_path / "report.md",
        json_report_path=tmp_path / "report.json",
        runtime_root=tmp_path,
    )

    candidate = pd.read_parquet(operations_root / "feature_artifacts/2026-06-11/candidate_features.parquet")
    opportunity = pd.read_parquet(operations_root / "feature_artifacts/2026-06-11/opportunity_feature_input.parquet")
    source = pd.read_parquet(quotes_path)
    source = source[(source["target_date"].astype(str) <= "2026-06-11") & (source["code"].astype(str) == "10010")].sort_values(
        "target_date"
    )
    close = source["Close"].astype(float).reset_index(drop=True)
    returns_20d = [close.iloc[index] / close.iloc[index - 1] - 1.0 for index in range(len(close) - 20, len(close))]
    vol20 = pd.Series(returns_20d).std(ddof=0)
    candidate_row = candidate[(candidate["target_date"].astype(str) == "2026-06-11") & (candidate["code"].astype(str) == "10010")].iloc[0]
    opportunity_row = opportunity[
        (opportunity["target_date"].astype(str) == "2026-06-11") & (opportunity["code"].astype(str) == "10010")
    ].iloc[0]
    av_columns = [
        "price_momentum_return_1d",
        "price_momentum_return_3d",
        "price_momentum_return_10d",
        "recent_move_volatility_z_1d",
        "recent_move_volatility_z_3d",
        "momentum_5d_vs_20d_delta",
        "momentum_1d_vs_5d_delta",
    ]

    assert result.status == FEATURES_READY
    assert all(column in candidate.columns for column in av_columns)
    assert all(column in opportunity.columns for column in av_columns)
    assert candidate_row["price_momentum_return_1d"] == round(close.iloc[-1] / close.iloc[-2] - 1.0, 6)
    assert candidate_row["price_momentum_return_3d"] == round(close.iloc[-1] / close.iloc[-4] - 1.0, 6)
    assert candidate_row["price_momentum_return_10d"] == round(close.iloc[-1] / close.iloc[-11] - 1.0, 6)
    assert candidate_row["price_momentum_return_5d"] == round(close.iloc[-1] / close.iloc[-6] - 1.0, 6)
    assert candidate_row["price_momentum_return_20d"] == round(close.iloc[-1] / close.iloc[-21] - 1.0, 6)
    assert candidate_row["recent_move_volatility_z_1d"] == round((close.iloc[-1] / close.iloc[-2] - 1.0) / vol20, 6)
    assert candidate_row["recent_move_volatility_z_3d"] == round((close.iloc[-1] / close.iloc[-4] - 1.0) / (vol20 * (3.0**0.5)), 6)
    assert candidate_row["momentum_5d_vs_20d_delta"] == round(
        (close.iloc[-1] / close.iloc[-6] - 1.0) - (close.iloc[-1] / close.iloc[-21] - 1.0), 6
    )
    assert candidate_row["momentum_1d_vs_5d_delta"] == round(
        (close.iloc[-1] / close.iloc[-2] - 1.0) - (close.iloc[-1] / close.iloc[-6] - 1.0), 6
    )
    for column in av_columns:
        assert opportunity_row[column] == candidate_row[column]
    readiness = validate_feature_consumer_readiness(operations_root=operations_root, feature_date="2026-06-11")
    assert readiness.status == "READY"


def test_execute_copies_candidate_technical_features_to_position_input(tmp_path: Path) -> None:
    quotes_path = tmp_path / "jquants/quotes.parquet"
    listed_path = tmp_path / "jquants/listed.parquet"
    runtime_root = tmp_path / ".runtime"
    _write_quotes(quotes_path)
    _write_listed(listed_path)
    (runtime_root / "runtime_state").mkdir(parents=True)
    (runtime_root / "persistent_ledger").mkdir(parents=True)
    (runtime_root / "runtime_state/current_state.json").write_text(
        json.dumps({"state": "CURRENT_STATE_LOADED", "asset_state_source": "persistent_ledger/state.json"}),
        encoding="utf-8",
    )
    (runtime_root / "persistent_ledger/state.json").write_text(
        json.dumps(
            {
                "schema_version": "runtime_v2_asset_state_v1",
                "as_of": "2026-06-11",
                "position_state_as_of": "2026-06-11",
                "positions": [
                    {
                        "symbol": "10010",
                        "quantity": 100,
                        "average_price": 120.0,
                        "entry_date": "2026-06-01",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

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
        runtime_root=runtime_root,
    )
    candidate = pd.read_parquet(tmp_path / "features/2026-06-11/candidate_features.parquet")
    position = pd.read_parquet(tmp_path / "features/2026-06-11/position_feature_input.parquet")
    candidate_row = candidate[(candidate["target_date"].astype(str) == "2026-06-11") & (candidate["code"].astype(str) == "10010")].iloc[0]
    position_row = position.iloc[0]
    technical_columns = [
        "price_momentum_return_5d",
        "price_momentum_return_20d",
        "trend_close_over_ma_20d",
        "trend_ma_5_20_ratio",
        "volume_momentum_ratio_5d",
        "volatility_return_std_20d",
    ]

    assert result.status == FEATURES_READY
    assert position_row["code"] == "10010"
    assert position_row["missing_features"] == "[]"
    assert position_row["defaulted_features"] == "[]"
    assert position_row["temporal_validation_status"] == "PASS"
    assert position_row["feature_source_hash"]
    assert position_row["feature_source_artifact"].endswith("candidate_features.parquet")
    for column in technical_columns:
        assert position_row[column] == candidate_row[column]


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
    candidate = pd.read_parquet(tmp_path / "features/2026-06-12/candidate_features.parquet")
    av_columns = [
        "price_momentum_return_1d",
        "price_momentum_return_3d",
        "price_momentum_return_10d",
        "recent_move_volatility_z_1d",
        "recent_move_volatility_z_3d",
        "momentum_5d_vs_20d_delta",
        "momentum_1d_vs_5d_delta",
    ]
    assert candidate[av_columns].isna().all().all()


def test_future_rows_are_ignored_during_generation(tmp_path: Path) -> None:
    quotes_path = tmp_path / "jquants/quotes.parquet"
    listed_path = tmp_path / "jquants/listed.parquet"
    _write_quotes(quotes_path, start="2026-03-02", periods=75)
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
        for day in pd.bdate_range("2026-03-02", "2026-06-16"):
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


def _write_ready_empty_current(root: Path, business_date: str) -> None:
    (root / "runtime_state").mkdir(parents=True, exist_ok=True)
    (root / "persistent_ledger").mkdir(parents=True, exist_ok=True)
    (root / "runtime_state/current_state.json").write_text(
        json.dumps({"state": "CURRENT_STATE_LOADED", "asset_state_source": "persistent_ledger/state.json"}),
        encoding="utf-8",
    )
    (root / "persistent_ledger/state.json").write_text(
        json.dumps(
            {
                "schema_version": "runtime_v2_asset_state_v1",
                "as_of": business_date,
                "business_date": business_date,
                "position_state_as_of": business_date,
                "positions": [],
                "current_state_confirmed_empty": True,
                "current_positions_unknown": False,
                "review_required": False,
            }
        ),
        encoding="utf-8",
    )
