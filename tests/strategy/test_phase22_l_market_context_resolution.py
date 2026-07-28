from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

from ai_fund_lab_v2.strategy.market_context import (
    MarketContextConfigError,
    MarketContextInputPaths,
    load_market_context_config,
    market_context_hash,
    produce_market_context_artifact,
    validate_market_context_artifact,
)


BUSINESS_DATE = "2026-07-10"
CONFIG_PATH = Path("configs/strategy/market_context.json")


def test_phase22_l_config_resolves_authority_and_explicit_thresholds(tmp_path: Path) -> None:
    config = load_market_context_config(CONFIG_PATH)
    inputs = _write_sources(tmp_path)
    result = produce_market_context_artifact(
        business_date=BUSINESS_DATE,
        input_paths=inputs,
        config=config,
        output_path=tmp_path / "market_context.json",
        as_of="2026-07-10T00:00:00+00:00",
    )

    payload = result.payload
    assert result.status == "PASS"
    assert payload["benchmark_id"] == "JQUANTS_LISTED_COMMON_EQUAL_WEIGHT_MARKET_PROXY"
    assert payload["benchmark_source_type"] == "JQUANTS_DERIVED_MARKET_PROXY"
    assert payload["benchmark_weighting"] == "EQUAL_WEIGHT"
    assert payload["trend_metric"] == "return_20d_equal_weight"
    assert payload["breadth_metric"] == "breadth_20d_positive_ratio"
    assert payload["volatility_metric"] == "volatility_20d_equal_weight"
    assert payload["regime_state"] in {"BULL", "RANGE", "BEAR", "CORRECTION", "RECOVERY", "HIGH_VOLATILITY", "UNCERTAIN"}
    assert payload["runtime_consumer_eligibility"] == "NOT_ELIGIBLE"
    assert payload["artifact_hash"] == market_context_hash(payload)
    assert validate_market_context_artifact(payload)["status"] == "PASS"


def test_phase22_l_equal_weight_benchmark_is_order_independent(tmp_path: Path) -> None:
    config = load_market_context_config(CONFIG_PATH)
    first = produce_market_context_artifact(
        business_date=BUSINESS_DATE,
        input_paths=_write_sources(tmp_path / "first"),
        config=config,
        output_path=tmp_path / "first.json",
        as_of="2026-07-10T00:00:00+00:00",
    )
    second = produce_market_context_artifact(
        business_date=BUSINESS_DATE,
        input_paths=_write_sources(tmp_path / "second", reverse_rows=True),
        config=config,
        output_path=tmp_path / "second.json",
        as_of="2026-07-10T00:00:00+00:00",
    )

    assert first.payload["trend_value"] == second.payload["trend_value"]
    assert first.payload["breadth_value"] == second.payload["breadth_value"]
    assert first.payload["volatility_value"] == second.payload["volatility_value"]


def test_phase22_l_coverage_shortfall_and_missing_sector_do_not_fallback(tmp_path: Path) -> None:
    config = load_market_context_config(CONFIG_PATH)
    coverage_review = produce_market_context_artifact(
        business_date=BUSINESS_DATE,
        input_paths=_write_sources(tmp_path / "coverage", missing_start_symbol=True),
        config=config,
        output_path=tmp_path / "coverage.json",
        as_of="2026-07-10T00:00:00+00:00",
    )
    assert coverage_review.status == "REVIEW_REQUIRED"
    assert "benchmark_coverage_insufficient" in coverage_review.payload["reason_codes"]

    no_sector = _write_sources(tmp_path / "no_sector", write_listed=False)
    sector_review = produce_market_context_artifact(
        business_date=BUSINESS_DATE,
        input_paths=no_sector,
        config=config,
        output_path=tmp_path / "sector.json",
        as_of="2026-07-10T00:00:00+00:00",
    )
    assert "sector_authority_review_required" in sector_review.payload["reason_codes"]
    assert sector_review.payload["sector_contexts"] == []
    assert sector_review.payload["authority_policy"]["sector"]["market_wide_substitution_allowed"] is False


def test_phase22_l_regime_taxonomy_includes_conflict_and_high_volatility(tmp_path: Path) -> None:
    config = load_market_context_config(CONFIG_PATH)
    conflict = produce_market_context_artifact(
        business_date=BUSINESS_DATE,
        input_paths=_write_sources(tmp_path / "conflict", mode="up_narrow"),
        config=config,
        output_path=tmp_path / "conflict.json",
        as_of="2026-07-10T00:00:00+00:00",
    )
    assert conflict.status == "REVIEW_REQUIRED"
    assert conflict.payload["trend_regime"] == "UNCERTAIN"
    assert conflict.payload["uncertainty"] == "UNCERTAIN"

    high_vol = produce_market_context_artifact(
        business_date=BUSINESS_DATE,
        input_paths=_write_sources(tmp_path / "high_vol", mode="high_vol"),
        config=config,
        output_path=tmp_path / "high_vol.json",
        as_of="2026-07-10T00:00:00+00:00",
    )
    assert high_vol.payload["volatility_regime"] == "HIGH"
    assert high_vol.payload["regime_state"] == "HIGH_VOLATILITY"


def test_phase22_l_pit_and_config_failures_block(tmp_path: Path) -> None:
    config = load_market_context_config(CONFIG_PATH)
    future = produce_market_context_artifact(
        business_date=BUSINESS_DATE,
        input_paths=_write_sources(tmp_path / "future", include_future=True),
        config=config,
        output_path=tmp_path / "future.json",
        as_of="2026-07-10T00:00:00+00:00",
    )
    assert future.status == "PASS"
    assert future.payload["metrics"]["future_source_row_count"] > 0
    assert future.payload["metrics"]["future_rows_used"] is False
    assert future.payload["temporal_safety"]["future_leakage_used"] is False

    only_future = produce_market_context_artifact(
        business_date="2026-06-01",
        input_paths=_write_sources(tmp_path / "only_future", include_future=True),
        config=config,
        output_path=tmp_path / "only_future.json",
        as_of="2026-06-01T00:00:00+00:00",
    )
    assert only_future.status == "BLOCK"
    assert "future_source_row_rejected" in only_future.payload["reason_codes"]

    bad_config_path = tmp_path / "bad_config.json"
    bad_config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    bad_config["benchmark"]["source_type"] = "TOPIX"
    bad_config_path.write_text(json.dumps(bad_config), encoding="utf-8")
    with pytest.raises(MarketContextConfigError):
        load_market_context_config(bad_config_path)


def _write_sources(
    root: Path,
    *,
    reverse_rows: bool = False,
    missing_start_symbol: bool = False,
    write_listed: bool = True,
    include_future: bool = False,
    mode: str = "balanced",
) -> MarketContextInputPaths:
    root.mkdir(parents=True, exist_ok=True)
    start = date.fromisoformat("2026-06-10")
    dates = [(start + timedelta(days=offset)).isoformat() for offset in range(40)]
    dates = [day for day in dates if date.fromisoformat(day).weekday() < 5][:23]
    if BUSINESS_DATE not in dates:
        dates.append(BUSINESS_DATE)
    if include_future:
        dates.append("2026-07-13")
    rows = []
    for idx, day in enumerate(sorted(set(dates))):
        for code, base, drift in _series(mode):
            if missing_start_symbol and code in {"1003", "1004", "1005"} and idx <= 3:
                continue
            close = max(1.0, base + idx * drift)
            if mode == "high_vol":
                close = max(1.0, base + ((-1) ** idx) * (8.0 + idx * 0.2) + idx * drift)
            rows.append({"target_date": day, "code": code, "Close": close, "Volume": 1000 + idx})
    if reverse_rows:
        rows = list(reversed(rows))
    quotes_path = root / "daily_quotes.parquet"
    pd.DataFrame(rows).to_parquet(quotes_path)

    listed_path = root / "listed_issues.parquet"
    if write_listed:
        pd.DataFrame(
            [
                {"code": "1001", "S33Nm": "Tech"},
                {"code": "1002", "S33Nm": "Tech"},
                {"code": "1003", "S33Nm": "Retail"},
                {"code": "1004", "S33Nm": "Retail"},
                {"code": "1005", "S33Nm": "Machinery"},
                {"code": "1006", "S33Nm": "Machinery"},
            ]
        ).to_parquet(listed_path)
    calendar_path = root / "trading_calendar.parquet"
    pd.DataFrame([{"target_date": day, "HolDiv": "1"} for day in sorted(set(dates))]).to_parquet(calendar_path)
    return MarketContextInputPaths(
        daily_quotes_path=quotes_path,
        listed_issues_path=listed_path if write_listed else root / "missing_listed.parquet",
        trading_calendar_path=calendar_path,
    )


def _series(mode: str) -> tuple[tuple[str, float, float], ...]:
    if mode == "up_narrow":
        return (
            ("1001", 100.0, 0.9),
            ("1002", 100.0, -0.8),
            ("1003", 100.0, -0.8),
            ("1004", 100.0, -0.8),
            ("1005", 100.0, -0.8),
            ("1006", 100.0, 12.0),
        )
    if mode == "high_vol":
        return (
            ("1001", 100.0, 5.0),
            ("1002", 100.0, -1.0),
            ("1003", 100.0, 4.0),
            ("1004", 100.0, -1.0),
            ("1005", 100.0, 3.0),
            ("1006", 100.0, -1.0),
        )
    return (
        ("1001", 100.0, 0.4),
        ("1002", 90.0, 0.3),
        ("1003", 80.0, 0.2),
        ("1004", 70.0, 0.1),
        ("1005", 60.0, -0.1),
        ("1006", 50.0, -0.1),
    )
