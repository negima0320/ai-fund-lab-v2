from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.runtime_v2.historical_support.asof import resolve_historical_market_data_asof
from ai_fund_lab_v2.runtime_v2.source_authority_materialization import materialize_raw_ohlcv_authority


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _raw_rows(days: list[str], *, source: str = "jquants") -> list[dict[str, object]]:
    return [
        {
            "Date": day,
            "Code": "13010",
            "O": 100.0,
            "H": 101.0,
            "L": 99.0,
            "C": 100.0,
            "Vo": 1000,
            "AdjFactor": 1.0,
            "target_date": day,
            "code": "13010",
            "business_key": "13010",
            "source": source,
            "endpoint": "/v2/equities/bars/daily",
            "fetched_at": "2026-08-10T00:00:00+00:00",
        }
        for day in days
    ]


def _normalized_rows(days: list[str]) -> list[dict[str, object]]:
    return [
        {
            "Date": day,
            "Code": "13010",
            "Open": 100.0,
            "High": 101.0,
            "Low": 99.0,
            "Close": 100.0,
            "Volume": 1000,
            "PriceSource": "adjusted",
            "SchemaVersion": 2,
            "source_endpoint": "/v2/equities/bars/daily",
            "target_date": day,
            "code": "13010",
            "business_key": "13010",
            "endpoint": "daily_quotes_normalized",
            "source": "jquants",
        }
        for day in days
    ]


def _write_staging(root: Path, days: list[str], *, source: str = "jquants", valid_state: bool = True) -> Path:
    run_root = root / "market_data_acquisition" / "runs" / "jquants-acquisition-test"
    raw_path = run_root / "raw" / "jquants" / "equities_bars_daily" / "data.parquet"
    normalized_path = run_root / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet"
    raw_path.parent.mkdir(parents=True)
    normalized_path.parent.mkdir(parents=True)
    pd.DataFrame(_raw_rows(days, source=source)).to_parquet(raw_path, index=False)
    pd.DataFrame(_normalized_rows(days)).to_parquet(normalized_path, index=False)
    if not valid_state:
        return raw_path
    dates = sorted(days)
    plan = {
        "status": "PASS",
        "acquisition_run_id": run_root.name,
    }
    state = {
        "status": "PASS",
        "acquisition_run_id": run_root.name,
        "final_validation": {
            "status": "PASS",
            "content_hash": _sha(normalized_path),
            "coverage_start_date": dates[0],
            "coverage_end_date": dates[-1],
            "future_date_count": 0,
            "normalized_inventory": {"duplicate_key_count": 0},
            "jquants_lineage": {"status": "PASS"},
            "schema_comparison": {"status": "PASS", "runtime_merge_compatible": True},
        },
    }
    (run_root / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
    (run_root / "state.json").write_text(json.dumps(state), encoding="utf-8")
    return raw_path


def _write_operations_authorities(root: Path, normalized_days: list[str], raw_days: list[str]) -> None:
    operations = root / "operations" / "jquants"
    normalized_path = operations / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet"
    raw_path = operations / "raw" / "jquants" / "equities_bars_daily" / "data.parquet"
    calendar_path = operations / "raw" / "jquants" / "trading_calendar" / "data.parquet"
    listed_path = operations / "raw" / "jquants" / "listed_issues" / "data.parquet"
    for path in (normalized_path, raw_path, calendar_path, listed_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(_normalized_rows(normalized_days)).to_parquet(normalized_path, index=False)
    pd.DataFrame(_raw_rows(raw_days)).to_parquet(raw_path, index=False)
    all_days = sorted(set(normalized_days + raw_days))
    pd.DataFrame([{"Date": day, "HolDiv": "1"} for day in all_days]).to_parquet(calendar_path, index=False)
    pd.DataFrame([{"Date": day, "Code": "13010"} for day in all_days]).to_parquet(listed_path, index=False)


def test_l5_materializes_validated_raw_ohlcv_and_repairs_day0_pit_authority(tmp_path: Path) -> None:
    runtime_root = tmp_path / ".runtime"
    long_days = ["2022-05-17", "2022-08-10", "2022-08-11", "2023-04-03", "2026-07-14"]
    _write_operations_authorities(runtime_root, normalized_days=long_days, raw_days=["2026-07-14"])
    staging_path = _write_staging(runtime_root, long_days)

    before = resolve_historical_market_data_asof(
        operations_root=runtime_root / "operations",
        business_date="2022-08-10",
    )
    assert before.status == "HALT"
    assert next(item for item in before.authorities if item.authority == "raw_ohlcv").reason == "logical_view_empty"

    result = materialize_raw_ohlcv_authority(
        runtime_root=runtime_root,
        staging_path=staging_path,
        requested_start_date="2022-05-17",
        requested_end_date="2026-07-14",
        confirm=True,
    )
    after = resolve_historical_market_data_asof(
        operations_root=runtime_root / "operations",
        business_date="2022-08-10",
    )
    raw = next(item for item in after.authorities if item.authority == "raw_ohlcv")

    assert result["status"] == "PASS"
    assert result["target_inventory_after"]["earliest_date"] == "2022-05-17"
    assert result["target_inventory_after"]["latest_date"] == "2026-07-14"
    assert raw.status == "PASS"
    assert raw.logical_row_count > 0
    assert raw.future_rows_excluded_count > 0
    assert after.status == "PASS"


def test_l5_raw_ohlcv_regression_dates_pass_after_materialization(tmp_path: Path) -> None:
    runtime_root = tmp_path / ".runtime"
    days = ["2022-05-17", "2022-08-10", "2023-04-03", "2026-07-14"]
    _write_operations_authorities(runtime_root, normalized_days=days, raw_days=["2026-07-14"])
    staging_path = _write_staging(runtime_root, days)
    assert materialize_raw_ohlcv_authority(
        runtime_root=runtime_root,
        staging_path=staging_path,
        requested_start_date="2022-05-17",
        requested_end_date="2026-07-14",
        confirm=True,
    )["status"] == "PASS"

    for business_date in ("2023-04-03", "2026-07-14"):
        result = resolve_historical_market_data_asof(
            operations_root=runtime_root / "operations",
            business_date=business_date,
        )
        raw = next(item for item in result.authorities if item.authority == "raw_ohlcv")
        normalized = next(item for item in result.authorities if item.authority == "normalized_ohlcv")
        assert result.status == "PASS"
        assert raw.status == "PASS"
        assert normalized.status == "PASS"
        assert raw.logical_max_date <= business_date
        assert normalized.logical_max_date <= business_date


def test_l5_raw_ohlcv_materialization_fails_closed_for_missing_source(tmp_path: Path) -> None:
    result = materialize_raw_ohlcv_authority(
        runtime_root=tmp_path / ".runtime",
        staging_path=tmp_path / "missing.parquet",
        requested_start_date="2022-05-17",
        requested_end_date="2026-07-14",
        confirm=True,
    )

    assert result["status"] == "HALT"
    assert result["reason"] == "raw_ohlcv_staging_source_missing"


def test_l5_raw_ohlcv_materialization_fails_closed_for_invalid_schema(tmp_path: Path) -> None:
    runtime_root = tmp_path / ".runtime"
    staging_path = _write_staging(runtime_root, ["2022-08-10", "2026-07-14"])
    frame = pd.read_parquet(staging_path).drop(columns=["Vo"])
    frame.to_parquet(staging_path, index=False)

    result = materialize_raw_ohlcv_authority(
        runtime_root=runtime_root,
        staging_path=staging_path,
        requested_start_date="2022-08-10",
        requested_end_date="2026-07-14",
        confirm=True,
    )

    assert result["status"] == "HALT"
    assert result["reason"] == "raw_ohlcv_required_columns_missing"


def test_l5_raw_ohlcv_materialization_fails_closed_for_lineage_mismatch(tmp_path: Path) -> None:
    runtime_root = tmp_path / ".runtime"
    staging_path = _write_staging(runtime_root, ["2022-08-10", "2026-07-14"], source="vendor-x")

    result = materialize_raw_ohlcv_authority(
        runtime_root=runtime_root,
        staging_path=staging_path,
        requested_start_date="2022-08-10",
        requested_end_date="2026-07-14",
        confirm=True,
    )

    assert result["status"] == "HALT"
    assert result["reason"] == "raw_ohlcv_jquants_lineage_not_pass"
