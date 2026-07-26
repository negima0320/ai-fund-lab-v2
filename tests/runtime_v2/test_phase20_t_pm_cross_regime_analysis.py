from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from scripts.analyze_pm_cross_regime import (
    analyze_runs,
    build_symbol_volatility_index,
    build_candidate_period_report,
    normalize_symbol_code,
    volatility_bucket,
    write_json,
)


def test_phase20_t_candidate_periods_are_market_data_only(tmp_path: Path) -> None:
    quotes_path = tmp_path / "quotes.parquet"
    rows = []
    dates = pd.bdate_range("2026-01-01", periods=28).strftime("%Y-%m-%d").tolist()
    for symbol, start_price, drift in (("11110", 100.0, 0.01), ("22220", 200.0, 0.008), ("33330", 300.0, 0.006)):
        price = start_price
        for date in dates:
            price *= 1.0 + drift
            rows.append({"Date": date, "Code": symbol, "Open": price * 0.99, "High": price * 1.01, "Low": price * 0.98, "Close": price, "Volume": 1000})
    pd.DataFrame(rows).to_parquet(quotes_path, index=False)

    report = build_candidate_period_report(quotes_path=quotes_path, business_days=20)

    assert report["market_proxy_method"]["outcome_leakage_policy"] == "NO_PM_OR_PORTFOLIO_OUTCOMES_USED_FOR_PERIOD_SELECTION"
    assert report["data_completeness"]["oldest_business_date"] == "2026-01-01"
    assert report["candidate_periods"]
    assert any(candidate["primary_regime"] == "BULL" for candidate in report["candidate_periods"])


def test_phase20_t_analyze_runs_uses_run_scoped_snapshots_without_mutation(tmp_path: Path) -> None:
    quotes_path = tmp_path / "quotes.parquet"
    dates = pd.bdate_range("2026-01-01", periods=8).strftime("%Y-%m-%d").tolist()
    price = 100.0
    rows = []
    for date in dates:
        price += 2.0
        rows.append({"Date": date, "Code": "11110", "Open": price, "High": price + 1, "Low": price - 1, "Close": price, "Volume": 1000})
    pd.DataFrame(rows).to_parquet(quotes_path, index=False)
    candidates = {
        "candidate_periods": [
            {
                "candidate_id": "Run-A",
                "start_date": dates[0],
                "end_date": dates[-1],
                "primary_regime": "BULL",
            }
        ]
    }
    candidate_path = tmp_path / "candidates.json"
    write_json(candidate_path, candidates)
    run_dir = tmp_path / "reports" / "runtime_tests" / "runs" / "run-1" / "daily" / dates[1] / "position_management"
    run_dir.mkdir(parents=True)
    write_json(
        run_dir / "pm_decisions.json",
        {
            "business_date": dates[1],
            "decisions": [
                {
                    "pm_decision_id": "pm-1",
                    "symbol": "11110",
                    "decision_type": "EXIT",
                    "dominant_cause": "EXIT_BY_HARD_STOP",
                    "decision_trace": {"technical_features": {"volatility_return_std_20d": 0.1}},
                }
            ],
        },
    )

    report = analyze_runs(
        run_ids=("run-1",),
        evidence_root=tmp_path / "reports" / "runtime_tests",
        quotes_path=quotes_path,
        candidate_periods_path=candidate_path,
    )

    assert report["decision_count"] == 1
    assert report["aggregates_by_dominant_cause"]["EXIT_BY_HARD_STOP"]["count"] == 1
    assert report["decisions"][0]["market_regime"] == "BULL"
    assert report["decisions"][0]["symbol_volatility_bucket"] == "HIGH_SYMBOL_VOLATILITY"


def test_phase20_x_symbol_volatility_market_data_fallback_normalizes_symbol_and_date_join(tmp_path: Path) -> None:
    quotes_path = tmp_path / "quotes.parquet"
    dates = pd.bdate_range("2026-01-01", periods=30).strftime("%Y-%m-%d").tolist()
    rows = []
    price = 100.0
    for idx, date in enumerate(dates):
        price *= 1.0 + (0.01 if idx % 2 == 0 else -0.012)
        rows.append({"Date": date, "Code": "81050", "Open": price, "High": price + 1, "Low": price - 1, "Close": price, "Volume": 1000})
    pd.DataFrame(rows).to_parquet(quotes_path, index=False)
    candidate_path = tmp_path / "candidates.json"
    write_json(candidate_path, {"candidate_periods": []})
    decision_date = dates[24]
    run_dir = tmp_path / "reports" / "runtime_tests" / "runs" / "run-1" / "daily" / decision_date / "position_management"
    run_dir.mkdir(parents=True)
    write_json(
        run_dir / "pm_decisions.json",
        {
            "business_date": decision_date,
            "decisions": [
                {
                    "pm_decision_id": "pm-1",
                    "symbol": "8105",
                    "decision_type": "HOLD",
                    "reason_codes": ["trend_continuation"],
                }
            ],
        },
    )

    report = analyze_runs(
        run_ids=("run-1",),
        evidence_root=tmp_path / "reports" / "runtime_tests",
        quotes_path=quotes_path,
        candidate_periods_path=candidate_path,
    )

    decision = report["decisions"][0]
    assert decision["symbol"] == "81050"
    assert decision["symbol_volatility"] is not None
    assert decision["symbol_volatility_lookup_status"] == "AVAILABLE"
    assert decision["symbol_volatility_source"] == "EXISTING_JQUANTS_NORMALIZED_OHLCV_CLOSE_TO_CLOSE_RETURN_STD_20D"
    assert decision["symbol_volatility_observation_count"] == 20
    assert decision["symbol_volatility_future_data_used"] is False
    assert decision["symbol_volatility_bucket"] == "LOW_SYMBOL_VOLATILITY"


def test_phase20_x_symbol_volatility_trace_value_takes_precedence(tmp_path: Path) -> None:
    quotes_path = tmp_path / "quotes.parquet"
    dates = pd.bdate_range("2026-01-01", periods=25).strftime("%Y-%m-%d").tolist()
    rows = [
        {"Date": date, "Code": "11110", "Open": 100 + idx, "High": 101 + idx, "Low": 99 + idx, "Close": 100 + idx, "Volume": 1000}
        for idx, date in enumerate(dates)
    ]
    pd.DataFrame(rows).to_parquet(quotes_path, index=False)
    candidate_path = tmp_path / "candidates.json"
    write_json(candidate_path, {"candidate_periods": []})
    run_dir = tmp_path / "reports" / "runtime_tests" / "runs" / "run-1" / "daily" / dates[-1] / "position_management"
    run_dir.mkdir(parents=True)
    write_json(
        run_dir / "pm_decisions.json",
        {
            "business_date": dates[-1],
            "decisions": [
                {
                    "pm_decision_id": "pm-1",
                    "symbol": "11110",
                    "decision_type": "EXIT",
                    "decision_trace": {"technical_features": {"volatility_return_std_20d": 0.09}},
                }
            ],
        },
    )

    report = analyze_runs(
        run_ids=("run-1",),
        evidence_root=tmp_path / "reports" / "runtime_tests",
        quotes_path=quotes_path,
        candidate_periods_path=candidate_path,
    )

    decision = report["decisions"][0]
    assert decision["symbol_volatility"] == 0.09
    assert decision["symbol_volatility_source"] == "decision_trace.technical_features.volatility_return_std_20d"
    assert decision["symbol_volatility_bucket"] == "HIGH_SYMBOL_VOLATILITY"


def test_phase20_x_symbol_volatility_missing_data_remains_unknown(tmp_path: Path) -> None:
    quotes_path = tmp_path / "quotes.parquet"
    dates = pd.bdate_range("2026-01-01", periods=25).strftime("%Y-%m-%d").tolist()
    pd.DataFrame(
        [
            {"Date": date, "Code": "11110", "Open": 100 + idx, "High": 101 + idx, "Low": 99 + idx, "Close": 100 + idx, "Volume": 1000}
            for idx, date in enumerate(dates)
        ]
    ).to_parquet(quotes_path, index=False)
    candidate_path = tmp_path / "candidates.json"
    write_json(candidate_path, {"candidate_periods": []})
    run_dir = tmp_path / "reports" / "runtime_tests" / "runs" / "run-1" / "daily" / dates[-1] / "position_management"
    run_dir.mkdir(parents=True)
    write_json(run_dir / "pm_decisions.json", {"business_date": dates[-1], "decisions": [{"symbol": "99990", "decision_type": "HOLD"}]})

    report = analyze_runs(
        run_ids=("run-1",),
        evidence_root=tmp_path / "reports" / "runtime_tests",
        quotes_path=quotes_path,
        candidate_periods_path=candidate_path,
    )

    decision = report["decisions"][0]
    assert decision["symbol_volatility"] is None
    assert decision["symbol_volatility_lookup_status"] == "MARKET_DATA_NOT_FOUND"
    assert decision["symbol_volatility_bucket"] == "UNKNOWN"


def test_phase20_x_symbol_volatility_uses_no_future_data() -> None:
    dates = pd.bdate_range("2026-01-01", periods=27).strftime("%Y-%m-%d").tolist()
    prices = [100.0]
    for idx in range(1, 26):
        prices.append(prices[-1] * (1.0 + (0.01 if idx % 2 else -0.01)))
    prices.append(prices[-1] * 2.0)
    frame = pd.DataFrame(
        [
            {"Date": date, "Code": "22220", "Open": price, "High": price + 1, "Low": price - 1, "Close": price, "Volume": 1000}
            for date, price in zip(dates, prices)
        ]
    )

    index = build_symbol_volatility_index(frame)
    decision_date = dates[-2]
    future_date = dates[-1]

    assert index[(decision_date, "22220")]["value"] < index[(future_date, "22220")]["value"]
    assert index[(decision_date, "22220")]["future_data_used"] is False


def test_phase20_x_symbol_normalization_and_bucket_classification() -> None:
    assert normalize_symbol_code("8105") == "81050"
    assert normalize_symbol_code("81050") == "81050"
    assert normalize_symbol_code("8105.T") == "81050"
    assert volatility_bucket(None) == "UNKNOWN"
    assert volatility_bucket(0.024) == "LOW_SYMBOL_VOLATILITY"
    assert volatility_bucket(0.025) == "MEDIUM_SYMBOL_VOLATILITY"
    assert volatility_bucket(0.08) == "HIGH_SYMBOL_VOLATILITY"
