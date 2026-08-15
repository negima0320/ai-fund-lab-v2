from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

from ai_fund_lab_v2.strategy import input_materialization
from ai_fund_lab_v2.strategy import portfolio_policy
from ai_fund_lab_v2.strategy.position_sizing import PositionSizingSourceSummary, _rows_with_price_volatility


BUSINESS_DATE = "2026-07-10"


def test_phase22_qe_price_volatility_materializes_pit_valid_source_hash(tmp_path: Path) -> None:
    quotes = _write_quotes(tmp_path / "quotes.parquet", days=35)
    result = input_materialization.produce_price_volatility_artifact(
        business_date=BUSINESS_DATE,
        feature_date=BUSINESS_DATE,
        source_path=quotes,
        output_path=tmp_path / "price_volatility.json",
        symbols=("1001",),
        as_of=f"{BUSINESS_DATE}T00:00:00+00:00",
    )

    payload = result.payload
    assert result.status == "PASS"
    assert payload["pit_validation"]["status"] == "PASS"
    assert payload["pit_validation"]["future_rows_consumed"] is False
    assert payload["source_content_hash"]
    assert payload["rows"][0]["volatility_value"] > 0
    assert payload["rows"][0]["reference_price"] > 0
    assert payload["rows"][0]["reference_price_authority"]["authority_type"] == "REFERENCE_PRICE_AUTHORITY"
    assert payload["rows"][0]["reference_price_authority"]["source_authority"] == "MARKET_EVIDENCE_AUTHORITY"
    assert payload["rows"][0]["reference_price_authority"]["latest_fallback_used"] is False
    assert payload["rows"][0]["reference_price_resolution"]["status"] == "PASS"
    assert payload["rows"][0]["decision_resolution"] == "RESOLVED"


def test_phase22_qe_price_volatility_insufficient_observations_is_unresolved(tmp_path: Path) -> None:
    quotes = _write_quotes(tmp_path / "quotes.parquet", days=5)
    result = input_materialization.produce_price_volatility_artifact(
        business_date=BUSINESS_DATE,
        feature_date=BUSINESS_DATE,
        source_path=quotes,
        output_path=tmp_path / "price_volatility.json",
        symbols=("1001",),
        as_of=f"{BUSINESS_DATE}T00:00:00+00:00",
    )

    payload = result.payload
    assert result.status == "REVIEW_REQUIRED"
    assert payload["decision_resolution"] == "UNRESOLVED"
    assert payload["rows"][0]["volatility_value"] is None
    assert "INSUFFICIENT_OBSERVATIONS" in payload["reason_codes"]


def test_phase22_qe_pm_technical_features_materialize_required_contract(tmp_path: Path) -> None:
    quotes = _write_quotes(tmp_path / "quotes.parquet", days=35)
    result = input_materialization.produce_pm_technical_feature_artifact(
        business_date=BUSINESS_DATE,
        feature_date=BUSINESS_DATE,
        source_path=quotes,
        output_path=tmp_path / "technical_features.json",
        symbols=("1001",),
        as_of=f"{BUSINESS_DATE}T00:00:00+00:00",
    )

    row = result.payload["rows"][0]
    assert result.status == "PASS"
    assert row["target_date"] == BUSINESS_DATE
    assert row["feature_as_of_date"] == BUSINESS_DATE
    assert row["defaulted_features"] == []
    assert row["missing_features"] == []
    assert row["rolling_median_traded_value_20"] > 0
    assert row["rolling_median_traded_value_20_authority"]["authority_type"] == "LIQUIDITY_CAPACITY_AUTHORITY"
    assert row["rolling_median_traded_value_20_authority"]["source_formula"] == "median(close * volume over last 20 PIT rows)"
    assert row["rolling_median_traded_value_20_authority"]["latest_fallback_used"] is False
    assert row["rolling_median_traded_value_20_resolution"]["status"] == "PASS"
    for column in input_materialization.PM_TECHNICAL_REQUIRED_COLUMNS:
        assert isinstance(row[column], float)


def test_phase29_l21t_av_multi_horizon_features_materialize_without_changing_5d_20d(tmp_path: Path) -> None:
    quotes = _write_quotes(tmp_path / "quotes.parquet", days=35)
    frame = pd.read_parquet(quotes)
    symbol = frame[(frame["code"] == "1001") & (frame["target_date"] <= BUSINESS_DATE)].sort_values("target_date")
    close = symbol["Close"].astype(float).reset_index(drop=True)
    result = input_materialization.produce_pm_technical_feature_artifact(
        business_date=BUSINESS_DATE,
        feature_date=BUSINESS_DATE,
        source_path=quotes,
        output_path=tmp_path / "technical_features.json",
        symbols=("1001",),
        as_of=f"{BUSINESS_DATE}T00:00:00+00:00",
    )

    row = result.payload["rows"][0]
    assert row["price_momentum_return_1d"] == pytest.approx(close.iloc[-1] / close.iloc[-2] - 1.0)
    assert row["price_momentum_return_3d"] == pytest.approx(close.iloc[-1] / close.iloc[-4] - 1.0)
    assert row["price_momentum_return_10d"] == pytest.approx(close.iloc[-1] / close.iloc[-11] - 1.0)
    assert row["price_momentum_return_5d"] == pytest.approx(close.iloc[-1] / close.iloc[-6] - 1.0)
    assert row["price_momentum_return_20d"] == pytest.approx(close.iloc[-1] / close.iloc[-21] - 1.0)
    assert isinstance(row["recent_move_volatility_z_1d"], float)
    assert isinstance(row["recent_move_volatility_z_3d"], float)
    assert isinstance(row["momentum_5d_vs_20d_delta"], float)
    assert isinstance(row["momentum_1d_vs_5d_delta"], float)


def test_phase29_l21r3_pm_technical_features_keep_capacity_unknown_when_volume_missing(tmp_path: Path) -> None:
    quotes = _write_quotes(tmp_path / "quotes.parquet", days=35)
    frame = pd.read_parquet(quotes).drop(columns=["Volume"])
    frame.to_parquet(quotes)

    result = input_materialization.produce_pm_technical_feature_artifact(
        business_date=BUSINESS_DATE,
        feature_date=BUSINESS_DATE,
        source_path=quotes,
        output_path=tmp_path / "technical_features.json",
        symbols=("1001",),
        as_of=f"{BUSINESS_DATE}T00:00:00+00:00",
    )

    row = result.payload["rows"][0]
    assert result.status == "REVIEW_REQUIRED"
    assert row["rolling_median_traded_value_20"] is None
    assert row["rolling_median_traded_value_20_resolution"]["status"] == "REVIEW_REQUIRED"
    assert row["rolling_median_traded_value_20_resolution"]["reason"] == "rolling_median_traded_value_missing_or_invalid"
    assert row["trend_close_over_ma_20d"] is not None


def test_phase22_qe_empty_portfolio_can_have_no_requested_feature_symbols(tmp_path: Path) -> None:
    quotes = _write_quotes(tmp_path / "quotes.parquet", days=35)
    result = input_materialization.produce_pm_technical_feature_artifact(
        business_date=BUSINESS_DATE,
        feature_date=BUSINESS_DATE,
        source_path=quotes,
        output_path=tmp_path / "technical_features.json",
        symbols=(),
        as_of=f"{BUSINESS_DATE}T00:00:00+00:00",
    )

    assert result.status == "PASS"
    assert result.payload["coverage_status"] == "FULL"
    assert result.payload["reason_codes"] == []


def test_phase22_qe_portfolio_policy_config_loads_real_authority() -> None:
    config = portfolio_policy.load_portfolio_policy_config("configs/strategy/portfolio_policy.json")

    assert config.config_source == "configs/strategy/portfolio_policy.json"
    assert config.intent_policy["risk_posture"] == "BALANCED"
    assert config.intent_policy["position_management_bias"] == "NEUTRAL"
    assert config.require_explicit_intent_policy is True


def test_phase22_qe_portfolio_policy_config_missing_is_not_defaulted(tmp_path: Path) -> None:
    with pytest.raises(portfolio_policy.PortfolioPolicyConfigError, match="missing_portfolio_policy_config_authority"):
        portfolio_policy.load_portfolio_policy_config(tmp_path / "missing_portfolio_policy.json")


def test_phase22_qe_position_sizing_joins_materialized_volatility_rows(tmp_path: Path) -> None:
    source = tmp_path / "price_volatility.json"
    source.write_text(json.dumps({"rows": []}), encoding="utf-8")
    summary = PositionSizingSourceSummary(
        status="PASS",
        business_date=BUSINESS_DATE,
        feature_date=BUSINESS_DATE,
        source_ref=str(source),
        source_hash="abc",
        rows=(
            {
                "symbol": "1001",
                "volatility_value": 0.018,
                "reference_price": 500.0,
                "reference_price_authority": {
                    "authority_type": "REFERENCE_PRICE_AUTHORITY",
                    "source_authority": "MARKET_EVIDENCE_AUTHORITY",
                    "latest_fallback_used": False,
                    "PIT_status": "PASS",
                    "source_field": "close",
                },
                "reference_price_resolution": {"status": "PASS", "resolved_price": 500.0, "review_reason": ""},
                "reference_price_type": "planning_reference_close",
                "reference_price_date": BUSINESS_DATE,
            },
            {"symbol": "1002", "volatility_value": 0.022},
        ),
        summary={"coverage_status": "FULL"},
    )

    rows = _rows_with_price_volatility(
        (
            {"security_code": "1001", "opportunity_score": 0.8},
            {"security_code": "1002", "opportunity_score": 0.7, "volatility": 0.03},
        ),
        summary,
    )

    assert rows[0]["volatility"] == 0.018
    assert rows[0]["volatility_source"] == str(source)
    assert rows[0]["reference_price"] == 500.0
    assert rows[0]["reference_price_authority"]["authority_type"] == "REFERENCE_PRICE_AUTHORITY"
    assert rows[1]["volatility"] == 0.03


def _write_quotes(path: Path, *, days: int) -> Path:
    start = date.fromisoformat("2026-05-25")
    dates = []
    offset = 0
    while len(dates) < days:
        day = start + timedelta(days=offset)
        offset += 1
        if day.weekday() < 5:
            dates.append(day.isoformat())
    dates.append("2026-07-13")
    rows = []
    for idx, day in enumerate(dates):
        rows.append({"target_date": day, "code": "1001", "Close": 100.0 + idx * 0.7, "Volume": 1000 + idx * 3})
        rows.append({"target_date": day, "code": "1002", "Close": 120.0 + idx * 0.4, "Volume": 2000 + idx * 2})
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(path)
    return path
