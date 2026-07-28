from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

from ai_fund_lab_v2.strategy.market_context import (
    MarketContextConsumerError,
    MarketContextInputPaths,
    MarketContextSchemaError,
    MarketContextThresholds,
    load_market_context_fixture,
    market_context_hash,
    produce_market_context_artifact,
    produced_but_not_consumed_evidence,
    sha256_file,
    validate_market_context_artifact,
    verify_source_hashes,
)


BUSINESS_DATE = "2026-07-10"


def test_phase22_a_valid_artifact_schema_hash_and_fixture_consumer(tmp_path: Path) -> None:
    inputs = _write_sources(tmp_path)
    artifact_path = tmp_path / "out" / "market_context.json"
    result = produce_market_context_artifact(
        business_date=BUSINESS_DATE,
        input_paths=inputs,
        output_path=artifact_path,
        thresholds=_thresholds(),
        as_of="2026-07-10T00:00:00+00:00",
    )

    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert result.status == "PASS"
    assert payload["schema_version"] == "strategy_market_context.v1"
    assert payload["artifact_lifecycle_status"] == "DRAFT"
    assert payload["runtime_consumer_eligibility"] == "NOT_ELIGIBLE"
    assert payload["temporal_safety"]["future_leakage_used"] is False
    assert payload["artifact_hash"] == market_context_hash(payload)
    assert validate_market_context_artifact(payload)["status"] == "PASS"
    assert load_market_context_fixture(artifact_path)["business_date"] == BUSINESS_DATE
    with pytest.raises(MarketContextConsumerError):
        load_market_context_fixture(artifact_path, for_production=True)


def test_phase22_a_schema_blocks_required_field_invalid_enum_date_and_confidence(tmp_path: Path) -> None:
    inputs = _write_sources(tmp_path)
    artifact_path = tmp_path / "market_context.json"
    result = produce_market_context_artifact(
        business_date=BUSINESS_DATE,
        input_paths=inputs,
        output_path=artifact_path,
        thresholds=_thresholds(),
        as_of="2026-07-10T00:00:00+00:00",
    )
    payload = dict(result.payload)

    for mutation in (
        lambda item: item.pop("business_date"),
        lambda item: item.update({"trend_regime": "SIDEWAYS"}),
        lambda item: item.update({"schema_version": "strategy_market_context.v999"}),
        lambda item: item.update({"feature_date": "20260710"}),
        lambda item: item.update({"confidence": 2.0}),
        lambda item: item.update({"runtime_consumer_eligibility": "ELIGIBLE"}),
    ):
        broken = dict(payload)
        mutation(broken)
        with pytest.raises(MarketContextSchemaError):
            validate_market_context_artifact(broken)


def test_phase22_a_no_leakage_deterministic_output_and_future_rows_rejected(tmp_path: Path) -> None:
    inputs = _write_sources(tmp_path)
    first = produce_market_context_artifact(
        business_date=BUSINESS_DATE,
        input_paths=inputs,
        output_path=tmp_path / "first.json",
        thresholds=_thresholds(),
        as_of="2026-07-10T00:00:00+00:00",
    )
    second = produce_market_context_artifact(
        business_date=BUSINESS_DATE,
        input_paths=inputs,
        output_path=tmp_path / "second.json",
        thresholds=_thresholds(),
        as_of="2026-07-10T00:00:00+00:00",
    )
    assert first.artifact_hash == second.artifact_hash
    assert first.payload["feature_date"] <= BUSINESS_DATE

    future_inputs = _write_sources(tmp_path / "future", include_future=True)
    mixed = produce_market_context_artifact(
        business_date=BUSINESS_DATE,
        input_paths=future_inputs,
        output_path=tmp_path / "future.json",
        thresholds=_thresholds(),
        as_of="2026-07-10T00:00:00+00:00",
    )
    assert mixed.status == "PASS"
    assert mixed.payload["feature_date"] == BUSINESS_DATE
    assert mixed.payload["metrics"]["future_source_row_count"] > 0
    assert mixed.payload["metrics"]["future_rows_used"] is False
    assert mixed.payload["temporal_safety"]["future_leakage_used"] is False

    blocked = produce_market_context_artifact(
        business_date="2026-06-01",
        input_paths=future_inputs,
        output_path=tmp_path / "only_future.json",
        thresholds=_thresholds(),
        as_of="2026-06-01T00:00:00+00:00",
    )
    assert blocked.status == "BLOCK"
    assert "future_source_row_rejected" in blocked.payload["reason_codes"]
    with pytest.raises(MarketContextConsumerError):
        load_market_context_fixture(tmp_path / "only_future.json")


def test_phase22_a_source_hash_missing_and_threshold_bootstrap_contracts(tmp_path: Path) -> None:
    missing_inputs = MarketContextInputPaths(daily_quotes_path=tmp_path / "missing.parquet")
    missing = produce_market_context_artifact(
        business_date=BUSINESS_DATE,
        input_paths=missing_inputs,
        output_path=tmp_path / "missing.json",
        as_of="2026-07-10T00:00:00+00:00",
    )
    assert missing.status == "REVIEW_REQUIRED"
    assert missing.payload["source_authority_status"] == "MISSING"
    assert "jquants_daily_quotes_missing" in missing.payload["reason_codes"]
    assert "market_context_threshold_config_required" in missing.payload["reason_codes"]

    inputs = _write_sources(tmp_path / "sources")
    review = produce_market_context_artifact(
        business_date=BUSINESS_DATE,
        input_paths=inputs,
        output_path=tmp_path / "threshold_required.json",
        as_of="2026-07-10T00:00:00+00:00",
    )
    assert review.status == "REVIEW_REQUIRED"
    assert review.payload["threshold_policy"]["status"] == "CONFIG_REQUIRED"

    mismatch = produce_market_context_artifact(
        business_date=BUSINESS_DATE,
        input_paths=inputs,
        output_path=tmp_path / "hash_mismatch.json",
        thresholds=_thresholds(),
        as_of="2026-07-10T00:00:00+00:00",
        expected_source_hashes={"jquants_daily_quotes": "0" * 64},
    )
    assert mismatch.status == "BLOCK"
    assert mismatch.payload["source_authority_status"] == "HASH_MISMATCH"
    assert verify_source_hashes(mismatch.payload)["status"] == "PASS"

    valid = produce_market_context_artifact(
        business_date=BUSINESS_DATE,
        input_paths=inputs,
        output_path=tmp_path / "valid_hash.json",
        thresholds=_thresholds(),
        as_of="2026-07-10T00:00:00+00:00",
        expected_source_hashes={"jquants_daily_quotes": sha256_file(inputs.daily_quotes_path)},
    )
    assert valid.status == "PASS"
    assert verify_source_hashes(valid.payload)["status"] == "PASS"


def test_phase22_a_produced_but_not_consumed_detection(tmp_path: Path) -> None:
    inputs = _write_sources(tmp_path)
    result = produce_market_context_artifact(
        business_date=BUSINESS_DATE,
        input_paths=inputs,
        output_path=tmp_path / "market_context.json",
        thresholds=_thresholds(),
        as_of="2026-07-10T00:00:00+00:00",
    )
    evidence = produced_but_not_consumed_evidence(result.payload)
    assert evidence == {
        "schema_version": "phase22_a_produced_but_not_consumed_validation.v1",
        "artifact_produced": True,
        "production_consumer_connected": False,
        "runtime_consumer_eligibility": "NOT_ELIGIBLE",
        "legacy_authority_active": True,
        "runtime_switch_performed": False,
        "status": "PASS",
    }


def _thresholds() -> MarketContextThresholds:
    return MarketContextThresholds(
        bull_return_20d_min=0.02,
        bear_return_20d_max=-0.02,
        strong_breadth_min=0.6,
        weak_breadth_max=0.4,
        high_volatility_min=0.04,
        low_volatility_max=0.005,
        high_sector_dispersion_min=0.03,
        low_sector_dispersion_max=0.005,
    )


def _write_sources(root: Path, *, include_future: bool = False) -> MarketContextInputPaths:
    root.mkdir(parents=True, exist_ok=True)
    start = date.fromisoformat("2026-06-10")
    dates = [(start + timedelta(days=offset)).isoformat() for offset in range(31)]
    dates = [day for day in dates if date.fromisoformat(day).weekday() < 5][:23]
    if BUSINESS_DATE not in dates:
        dates.append(BUSINESS_DATE)
    if include_future:
        dates.append("2026-07-13")
    rows = []
    for idx, day in enumerate(sorted(set(dates))):
        for code, base, drift in (("1001", 100.0, 0.4), ("1002", 90.0, -0.1), ("1003", 50.0, 0.2)):
            rows.append(
                {
                    "target_date": day,
                    "code": code,
                    "Close": base + idx * drift,
                    "Volume": 1000 + idx,
                }
            )
    quotes_path = root / "daily_quotes.parquet"
    pd.DataFrame(rows).to_parquet(quotes_path)
    listed_path = root / "listed_issues.parquet"
    pd.DataFrame(
        [
            {"code": "1001", "S33Nm": "Tech"},
            {"code": "1002", "S33Nm": "Retail"},
            {"code": "1003", "S33Nm": "Tech"},
        ]
    ).to_parquet(listed_path)
    calendar_path = root / "trading_calendar.parquet"
    pd.DataFrame([{"target_date": day, "HolDiv": "1"} for day in sorted(set(dates))]).to_parquet(calendar_path)
    return MarketContextInputPaths(
        daily_quotes_path=quotes_path,
        listed_issues_path=listed_path,
        trading_calendar_path=calendar_path,
    )
